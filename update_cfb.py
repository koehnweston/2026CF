import os
import sys
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwC1NpT8vKqmfsMFUxsPjc_23YhRPQAdMvEtz8GN05NVrm7IOtxnB9tu45ML4HgtLVD/exec"

def fetch_espn_data_for_weeks(current_week):
    events = []
    weeks_to_query = [max(1, current_week - 1), current_week]
    
    for w in set(weeks_to_query):
        for grp in [80, 81]:
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=2026&week={w}&groups={grp}&limit=300"
            try:
                res = requests.get(url, timeout=15)
                if res.status_code == 200:
                    data = res.json()
                    events.extend(data.get("events", []))
            except Exception as e:
                print(f"Notice: Error fetching week {w} group {grp}: {e}")
                
    return events

def normalize(text):
    if not text:
        return ""
    return text.lower().replace("&", "and").replace(".", "").replace("'", "").strip()

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

    if t_norm == loc or t_norm == disp or t_norm == short_disp:
        return True

    return False

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
    try:
        payload = {
            "action": "auto_score",
            "week": week_num,
            "scores": scores_map
        }
        res = requests.post(GOOGLE_SCRIPT_URL, json=payload, timeout=15)
        print(f"Google Sheet Auto-Scoring Response (Week {week_num}): {res.text}")
    except Exception as e:
        print(f"Notice: Google Sheet auto-scoring webhook error: {e}")

def run_update():
    if not os.path.exists("league_data.json"):
        print("Error: league_data.json not found!")
        sys.exit(1)

    with open("league_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    current_week = 2
    data["current_week"] = current_week
    data["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    events = fetch_espn_data_for_weeks(current_week)
    games = parse_events(events)

    all_teams = set()
    for member in data["members"].values():
        all_teams.update(member.get("teams", []))

    if "season_schedule" not in data:
        data["season_schedule"] = {}

    # 1. PROCESS AND ARCHIVE WEEK 1 FINAL SCORES
    week1_matchups = []
    week1_scores = {}

    for team in sorted(all_teams):
        matched_final = None
        is_home = False
        for g in games:
            if "FINAL" in g["status"]:
                if matches_team(team, g["home_obj"]):
                    matched_final = g
                    is_home = True
                    break
                elif matches_team(team, g["away_obj"]):
                    matched_final = g
                    is_home = False
                    break

        if matched_final:
            opponent = matched_final["away_loc"] if is_home else f"@{matched_final['home_loc']}"
            h_score = int(matched_final["home_score"] or 0)
            a_score = int(matched_final["away_score"] or 0)
            won = (h_score > a_score) if is_home else (a_score > h_score)
            res_str = "WIN" if won else "LOSS"
            week1_scores[team.lower()] = res_str

            week1_matchups.append({
                "team": team,
                "opponent": opponent,
                "spread": matched_final["spread"],
                "over_under": matched_final["over_under"],
                "game_time": matched_final["game_time"],
                "status": "STATUS_FINAL",
                "result": res_str,
                "is_bye": False
            })
        else:
            week1_matchups.append({
                "team": team,
                "opponent": "BYE",
                "spread": "N/A",
                "over_under": "",
                "game_time": "BYE WEEK",
                "status": "STATUS_FINAL",
                "result": "BYE",
                "is_bye": True
            })

    data["season_schedule"]["1"] = week1_matchups

    # 2. PROCESS AND STORE WEEK 2 UPCOMING MATCHUPS
    week2_matchups = []
    for team in sorted(all_teams):
        matched_upcoming = None
        is_home = False
        for g in games:
            if "FINAL" not in g["status"]:
                if matches_team(team, g["home_obj"]):
                    matched_upcoming = g
                    is_home = True
                    break
                elif matches_team(team, g["away_obj"]):
                    matched_upcoming = g
                    is_home = False
                    break

        if matched_upcoming:
            opponent = matched_upcoming["away_loc"] if is_home else f"@{matched_upcoming['home_loc']}"
            week2_matchups.append({
                "team": team,
                "opponent": opponent,
                "spread": matched_upcoming["spread"],
                "over_under": matched_upcoming["over_under"],
                "game_time": matched_upcoming["game_time"],
                "status": matched_upcoming["status"],
                "result": "PENDING",
                "is_bye": False
            })
        else:
            week2_matchups.append({
                "team": team,
                "opponent": "BYE / TBD",
                "spread": "N/A",
                "over_under": "",
                "game_time": "BYE WEEK",
                "status": "STATUS_SCHEDULED",
                "result": "BYE",
                "is_bye": True
            })

    data["season_schedule"]["2"] = week2_matchups
    data["week_matchups"] = week2_matchups # Active week default

    # Score Week 1 in Google Sheets
    if week1_scores:
        print(f"Scoring {len(week1_scores)} Week 1 picks in Google Sheet...")
        auto_score_google_sheet(week1_scores, week_num=1)

    with open("league_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Successfully updated both Week 1 archive and Week 2 active schedule.")

if __name__ == "__main__":
    run_update()
