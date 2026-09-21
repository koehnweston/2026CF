import os
import sys
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Active Google Apps Script Web App Endpoint
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwC1NpT8vKqmfsMFUxsPjc_23YhRPQAdMvEtz8GN05NVrm7IOtxnB9tu45ML4HgtLVD/exec"

# Optional: Set to an integer (e.g., 4) to force a specific week, or keep None for fully autonomous week progression
FORCE_WEEK = None

ALIASES = {
    "texas": ["texas longhorns", "texas"],
    "north texas": ["north texas mean green", "north texas", "unt"],
    "texas tech": ["texas tech red raiders", "texas tech"],
    "texas a&m": ["texas a&m aggies", "texas a&m", "tamu"],
    "washington": ["washington huskies", "washington"],
    "washington state": ["washington state cougars", "washington state", "wazzu"],
    "florida": ["florida gators", "florida"],
    "florida state": ["florida state seminoles", "florida state", "fsu"],
    "south florida": ["south florida bulls", "south florida", "usf"],
    "florida atlantic": ["florida atlantic owls", "florida atlantic", "fau"],
    "ole miss": ["ole miss rebels", "ole miss", "mississippi"],
    "mississippi state": ["mississippi state bulldogs", "mississippi state"],
    "notre dame": ["notre dame fighting irish", "notre dame"],
    "utsa": ["utsa roadrunners", "utsa", "texas-san antonio", "ut san antonio"],
    "smu": ["smu mustangs", "smu", "southern methodist"],
    "tcu": ["tcu horned frogs", "tcu", "texas christian"],
    "usc": ["usc trojans", "usc", "southern california"],
    "army": ["army black knights", "army", "army west point"],
    "navy": ["navy midshipmen", "navy"],
    "ucf": ["ucf knights", "ucf", "central florida"],
    "byu": ["byu cougars", "byu", "brigham young"],
    "penn state": ["penn state nittany lions", "penn state"],
    "ohio state": ["ohio state buckeyes", "ohio state"],
    "oklahoma state": ["oklahoma state cowboys", "oklahoma state"],
    "oklahoma": ["oklahoma sooners", "oklahoma"],
    "oregon state": ["oregon state beavers", "oregon state"],
    "oregon": ["oregon ducks", "oregon"],
    "kansas state": ["kansas state wildcats", "kansas state"],
    "kansas": ["kansas jayhawks", "kansas"],
    "arizona state": ["arizona state sun devils", "arizona state"],
    "arizona": ["arizona wildcats", "arizona"],
    "san diego state": ["san diego state aztecs", "san diego state", "sdsu"],
    "fresno state": ["fresno state bulldogs", "fresno state"],
    "boise state": ["boise state broncos", "boise state"],
    "miami": ["miami hurricanes", "miami", "miami (fl)"],
    "pittsburgh": ["pittsburgh panthers", "pittsburgh", "pitt"],
    "west virginia": ["west virginia mountaineers", "west virginia", "wvu"],
    "north carolina": ["north carolina tar heels", "north carolina", "unc"],
    "east carolina": ["east carolina pirates", "east carolina", "ecu"],
    "nc state": ["nc state wolfpack", "nc state", "north carolina state"]
}

def normalize(text):
    if not text:
        return ""
    return text.lower().replace("&", "and").replace(".", "").replace("'", "").strip()

def matches_team(target_name, espn_team_obj):
    t_norm = normalize(target_name)
    loc = normalize(espn_team_obj.get("location", ""))
    disp = normalize(espn_team_obj.get("displayName", ""))
    short_disp = normalize(espn_team_obj.get("shortDisplayName", ""))
    abbrev = normalize(espn_team_obj.get("abbreviation", ""))

    if target_name.lower() in ALIASES:
        aliases = [normalize(a) for a in ALIASES[target_name.lower()]]
        return (loc in aliases or disp in aliases or short_disp in aliases or abbrev in aliases)

    return (t_norm == loc or t_norm == disp or t_norm == short_disp or t_norm == abbrev)

def get_espn_active_info():
    """Detects current season year and current active week from ESPN root API"""
    season_year = 2024
    espn_week = 4
    try:
        base_url = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
        r = requests.get(base_url, timeout=10)
        if r.status_code == 200:
            d = r.json()
            season_year = d.get("season", {}).get("year", 2024)
            wk = d.get("week", {}).get("number")
            if wk and isinstance(wk, int):
                espn_week = wk
    except Exception as e:
        print(f"Notice: ESPN auto-detection fallback: {e}")
    return season_year, espn_week

def get_live_espn_data_for_week(target_week, season_year):
    events = []
    print(f"Fetching ESPN games for Season {season_year}, Week {target_week}...")
    for grp in [80, 81]:  # FBS & FCS
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates={season_year}&week={target_week}&groups={grp}&limit=300"
        try:
            res = requests.get(url, timeout=12)
            if res.status_code == 200:
                data = res.json()
                for ev in data.get("events", []):
                    ev["_query_week"] = target_week
                    events.append(ev)
        except Exception as e:
            print(f"Notice: Error fetching week {target_week} group {grp}: {e}")
    return events

def parse_events(events):
    parsed_games = []
    central_tz = ZoneInfo("America/Chicago")
    seen_game_ids = set()

    for ev in events:
        game_id = ev.get("id")
        if game_id in seen_game_ids:
            continue
        seen_game_ids.add(game_id)

        competitions = ev.get("competitions", [])
        if not competitions:
            continue
        comp = competitions[0]
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue

        home_team = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away_team = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

        odds_list = comp.get("odds", [])
        spread_str = "Line TBD"
        ou_str = ""
        if odds_list:
            spread_str = odds_list[0].get("details", "Line TBD")
            over_under = odds_list[0].get("overUnder")
            if over_under:
                ou_str = f"O/U {over_under}"

        raw_date = comp.get("date", "")
        time_display = "Time TBD"
        if raw_date:
            try:
                dt_utc = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                dt_ct = dt_utc.astimezone(central_tz)
                time_display = dt_ct.strftime("%a %m/%d • %I:%M %p CT")
            except:
                time_display = raw_date

        status_type = comp.get("status", {}).get("type", {}).get("name", "STATUS_SCHEDULED")
        home_score = home_team.get("score")
        away_score = away_team.get("score")

        parsed_games.append({
            "id": game_id,
            "week": ev.get("_query_week"),
            "home_obj": home_team.get("team", {}),
            "away_obj": away_team.get("team", {}),
            "home_loc": home_team.get("team", {}).get("location") or home_team.get("team", {}).get("displayName", "Home"),
            "away_loc": away_team.get("team", {}).get("location") or away_team.get("team", {}).get("displayName", "Away"),
            "spread": spread_str,
            "over_under": ou_str,
            "game_time": time_display,
            "status": status_type,
            "home_score": home_score,
            "away_score": away_score
        })

    return parsed_games

def auto_score_google_sheet(scores_map, week_num):
    if not scores_map:
        return
    try:
        payload = {
            "action": "auto_score",
            "week": week_num,
            "scores": scores_map
        }
        res = requests.post(GOOGLE_SCRIPT_URL, json=payload, timeout=15)
        print(f"Google Sheet Auto-Scoring Response (Week {week_num}): {res.text}")
    except Exception as e:
        print(f"Notice: Google Sheet webhook error: {e}")

def run_update():
    if not os.path.exists("league_data.json"):
        print("Error: league_data.json not found!")
        sys.exit(1)

    with open("league_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    if "season_schedule" not in data:
        data["season_schedule"] = {}

    all_teams = []
    for m in data["members"].values():
        all_teams.extend(m.get("teams", []))
    all_teams = sorted(list(set(all_teams)))

    season_year, espn_active_week = get_espn_active_info()
    stored_week = int(data.get("current_week", 3))

    # -------------------------------------------------------------
    # 1. SCORE AND FINALIZE THE CURRENT WEEK
    # -------------------------------------------------------------
    print(f"--- Checking & Scoring Week {stored_week} ---")
    w_events = get_live_espn_data_for_week(stored_week, season_year)
    w_games = parse_events(w_events)

    week_matchups = data["season_schedule"].get(str(stored_week), [])
    if not week_matchups:
        week_matchups = [{"team": t} for t in all_teams]

    sync_map = {}
    active_games_count = 0
    final_games_count = 0

    for m in week_matchups:
        team_name = m["team"]
        team_key = team_name.lower().strip()
        matched = None
        is_home = False

        for g in w_games:
            if g.get("week") != stored_week:
                continue
            if matches_team(team_name, g["home_obj"]):
                matched = g
                is_home = True
                break
            elif matches_team(team_name, g["away_obj"]):
                matched = g
                is_home = False
                break

        if matched:
            active_games_count += 1
            m["is_bye"] = False
            m["opponent"] = matched["away_loc"] if is_home else f"@{matched['home_loc']}"
            m["game_time"] = matched["game_time"]
            m["spread"] = matched["spread"]
            m["over_under"] = matched["over_under"]

            if "FINAL" in matched["status"]:
                final_games_count += 1
                h = int(matched["home_score"] or 0)
                a = int(matched["away_score"] or 0)
                won = (h > a) if is_home else (a > h)
                res_str = "WIN" if won else "LOSS"
                m["status"] = "STATUS_FINAL"
                m["result"] = res_str
                sync_map[team_key] = res_str
            elif "IN_PROGRESS" in matched["status"]:
                m["status"] = "STATUS_IN_PROGRESS"
                m["result"] = "PENDING"
                sync_map[team_key] = "PENDING"
            else:
                m["status"] = "STATUS_SCHEDULED"
                m["result"] = "PENDING"
                sync_map[team_key] = "PENDING"
        else:
            m["is_bye"] = True
            m["opponent"] = "BYE"
            m["game_time"] = "BYE WEEK"
            m["spread"] = "N/A"
            m["status"] = "STATUS_SCHEDULED"
            m["result"] = "BYE"

    data["season_schedule"][str(stored_week)] = week_matchups

    if sync_map:
        print(f"Syncing Week {stored_week} scores to Google Sheet ({len(sync_map)} teams)...")
        auto_score_google_sheet(sync_map, week_num=stored_week)

    # -------------------------------------------------------------
    # 2. AUTONOMOUS ROLLOVER TO NEXT WEEK
    # -------------------------------------------------------------
    # A week is considered complete when either:
    # A) All active games in that week are STATUS_FINAL
    # B) ESPN's live week has advanced past stored_week
    # C) FORCE_WEEK is explicitly specified
    is_week_finished = (active_games_count > 0 and final_games_count >= active_games_count) or (espn_active_week > stored_week)

    if FORCE_WEEK is not None:
        target_active_week = FORCE_WEEK
    elif is_week_finished:
        target_active_week = stored_week + 1
        print(f"★ All Week {stored_week} games are complete! Auto-advancing to Week {target_active_week}.")
    else:
        target_active_week = stored_week
        print(f"Week {stored_week} is still active ({final_games_count}/{active_games_count} games completed).")

    data["current_week"] = target_active_week
    data["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # -------------------------------------------------------------
    # 3. POPULATE MATCHUPS & SPREADS FOR THE ACTIVE PICKING WEEK
    # -------------------------------------------------------------
    print(f"\n--- Loading Matchups, Lines & Times for Week {target_active_week} ---")
    active_events = get_live_espn_data_for_week(target_active_week, season_year)
    active_games = parse_events(active_events)

    active_matchups = []
    active_sync_map = {}

    for team_name in all_teams:
        team_key = team_name.lower().strip()
        matched = None
        is_home = False

        for g in active_games:
            if g.get("week") != target_active_week:
                continue
            if matches_team(team_name, g["home_obj"]):
                matched = g
                is_home = True
                break
            elif matches_team(team_name, g["away_obj"]):
                matched = g
                is_home = False
                break

        if matched:
            opp_name = matched["away_loc"] if is_home else f"@{matched['home_loc']}"
            game_status = matched["status"]
            res_str = "PENDING"

            if "FINAL" in game_status:
                h = int(matched["home_score"] or 0)
                a = int(matched["away_score"] or 0)
                won = (h > a) if is_home else (a > h)
                res_str = "WIN" if won else "LOSS"
                game_status = "STATUS_FINAL"
                active_sync_map[team_key] = res_str

            active_matchups.append({
                "team": team_name,
                "opponent": opp_name,
                "spread": matched["spread"],
                "over_under": matched["over_under"],
                "game_time": matched["game_time"],
                "status": game_status,
                "result": res_str,
                "is_bye": False
            })
            print(f"[Week {target_active_week} Matchup] {team_name} vs {opp_name} | {matched['spread']} | {matched['game_time']}")
        else:
            active_matchups.append({
                "team": team_name,
                "opponent": "BYE",
                "spread": "N/A",
                "over_under": "",
                "game_time": "BYE WEEK",
                "status": "STATUS_SCHEDULED",
                "result": "BYE",
                "is_bye": True
            })

    data["season_schedule"][str(target_active_week)] = active_matchups
    data["week_matchups"] = active_matchups

    if active_sync_map:
        auto_score_google_sheet(active_sync_map, week_num=target_active_week)

    with open("league_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nCompleted! Active week is now Week {target_active_week}.")

if __name__ == "__main__":
    run_update()
