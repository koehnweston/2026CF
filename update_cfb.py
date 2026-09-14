import os
import sys
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Active Google Apps Script Web App Endpoint
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwC1NpT8vKqmfsMFUxsPjc_23YhRPQAdMvEtz8GN05NVrm7IOtxnB9tu45ML4HgtLVD/exec"

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
    "utsa": ["utsa roadrunners", "utsa", "texas-san antonio"],
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
    "boise state": ["boise state broncos", "boise state"]
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

    if target_name.lower() in ALIASES:
        aliases = [normalize(a) for a in ALIASES[target_name.lower()]]
        if loc in aliases or disp in aliases or short_disp in aliases:
            return True
        return False

    return (t_norm == loc or t_norm == disp or t_norm == short_disp)

def get_live_espn_data():
    """Queries live ESPN scoreboard and automatically detects current active week"""
    events = []
    detected_week = 2

    try:
        base_url = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
        r = requests.get(base_url, timeout=10)
        if r.status_code == 200:
            d = r.json()
            wk = d.get("week", {}).get("number")
            if wk and isinstance(wk, int):
                detected_week = wk
    except Exception as e:
        print(f"Notice: Could not auto-detect live week: {e}")

    # Query active week and prior week to ensure complete game coverage
    weeks_to_query = [max(1, detected_week - 1), detected_week]
    for w in set(weeks_to_query):
        for grp in [80, 81]:
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=2024&week={w}&groups={grp}&limit=300"
            try:
                res = requests.get(url, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    for ev in data.get("events", []):
                        ev["_query_week"] = w
                        events.append(ev)
            except Exception as e:
                print(f"Notice: Error fetching week {w} group {grp}: {e}")

    return events, detected_week

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
            "week": ev.get("_query_week", 1),
            "home_obj": home_team.get("team", {}),
            "away_obj": away_team.get("team", {}),
            "home_loc": home_team.get("team", {}).get("location", ""),
            "away_loc": away_team.get("team", {}).get("location", ""),
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

    events, auto_week = get_live_espn_data()
    games = parse_events(events)

    current_week = data.get("current_week", auto_week)
    data["current_week"] = current_week
    data["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    all_teams = set()
    for member in data["members"].values():
        all_teams.update(member.get("teams", []))

    if "season_schedule" not in data:
        data["season_schedule"] = {}

    # -------------------------------------------------------------
    # 1. SCORE WEEK 1 MATCHUPS (Directly from verified schedule)
    # -------------------------------------------------------------
    week1_matchups = data["season_schedule"].get("1", [])
    week1_scores = {}
    for m in week1_matchups:
        if m.get("result") in ["WIN", "LOSS"]:
            week1_scores[m["team"].lower()] = m["result"]

    if week1_scores:
        print(f"Syncing {len(week1_scores)} verified Week 1 results to Google Sheet...")
        auto_score_google_sheet(week1_scores, week_num=1)

    # -------------------------------------------------------------
    # 2. REAL-TIME SCORING & FULL RESET/SYNC FOR ACTIVE WEEK (WEEK 2)
    # -------------------------------------------------------------
    week2_matchups = data["season_schedule"].get(str(current_week), [])
    week2_sync_map = {}

    for m in week2_matchups:
        team_name = m["team"]
        team_key = team_name.lower()

        # Check if team is on an actual BYE
        if m.get("is_bye") or m.get("opponent") == "BYE":
            m["status"] = "STATUS_SCHEDULED"
            m["result"] = "BYE"
            continue

        matched_game = None
        is_home = False

        for g in games:
            if matches_team(team_name, g["home_obj"]):
                matched_game = g
                is_home = True
                break
            elif matches_team(team_name, g["away_obj"]):
                matched_game = g
                is_home = False
                break

        if matched_game:
            # Sync live spread / time if available
            if matched_game.get("spread") and matched_game["spread"] != "Line TBD":
                m["spread"] = matched_game["spread"]
            if matched_game.get("game_time"):
                m["game_time"] = matched_game["game_time"]

            # CASE A: Game is complete right now!
            if "FINAL" in matched_game["status"]:
                h_score = int(matched_game["home_score"] or 0)
                a_score = int(matched_game["away_score"] or 0)
                won = (h_score > a_score) if is_home else (a_score > h_score)
                res_str = "WIN" if won else "LOSS"

                m["status"] = "STATUS_FINAL"
                m["result"] = res_str
                week2_sync_map[team_key] = res_str
                print(f"[Week {current_week} Complete] {team_name}: {res_str} ({h_score}-{a_score})")

            # CASE B: Game in progress
            elif "IN_PROGRESS" in matched_game["status"]:
                m["status"] = "STATUS_IN_PROGRESS"
                m["result"] = "PENDING"
                week2_sync_map[team_key] = "PENDING"

            # CASE C: Game not yet played
            else:
                m["status"] = "STATUS_SCHEDULED"
                # Keep verified result if already final, else set PENDING
                if m.get("status") != "STATUS_FINAL":
                    m["result"] = "PENDING"
                    week2_sync_map[team_key] = "PENDING"
                else:
                    week2_sync_map[team_key] = m.get("result", "PENDING")
        else:
            # Game not in ESPN active feed — preserve valid status or keep PENDING
            if m.get("status") == "STATUS_FINAL":
                week2_sync_map[team_key] = m.get("result", "PENDING")
            else:
                m["status"] = "STATUS_SCHEDULED"
                m["result"] = "PENDING"
                week2_sync_map[team_key] = "PENDING"

    # Save active schedule
    data["season_schedule"][str(current_week)] = week2_matchups
    data["week_matchups"] = week2_matchups

    # FULL-SYNC: Overwrites the Google Sheet for Week 2
    # Writes "WIN" or "LOSS" for finals, and overwrites all unplayed games back to "PENDING"
    if week2_sync_map:
        print(f"Syncing all {len(week2_sync_map)} Week {current_week} statuses to Google Sheet (wipes bad values back to PENDING)...")
        auto_score_google_sheet(week2_sync_map, week_num=current_week)

    with open("league_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Complete autonomous update finished.")

if __name__ == "__main__":
    run_update()
