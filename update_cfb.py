import os
import sys
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"

def fetch_espn_data():
    try:
        res = requests.get(ESPN_URL, timeout=15)
        if res.status_code == 200:
            return res.json()
        print(f"ESPN API returned status code {res.status_code}")
    except Exception as e:
        print(f"Error connecting to ESPN API: {e}")
    return None

def parse_espn_events(espn_json):
    if not espn_json:
        return 1, []

    week_info = espn_json.get("week", {})
    current_week = week_info.get("number", 1)
    events = espn_json.get("events", [])
    
    parsed_games = []
    central_tz = ZoneInfo("America/Chicago")

    for ev in events:
        competitions = ev.get("competitions", [])
        if not competitions:
            continue
        
        comp = competitions[0]
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue

        home_team = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away_team = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

        home_name = home_team.get("team", {}).get("location", "")
        away_name = away_team.get("team", {}).get("location", "")

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
            "home": home_name,
            "away": away_name,
            "spread": spread_str,
            "over_under": ou_str,
            "game_time": time_display,
            "status": status_type,
            "home_score": home_score,
            "away_score": away_score
        })

    return current_week, parsed_games

def run_update():
    if not os.path.exists("league_data.json"):
        print("Error: league_data.json not found!")
        sys.exit(1)

    with open("league_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    espn_json = fetch_espn_data()
    current_week, espn_games = parse_espn_events(espn_json)

    data["current_week"] = current_week
    data["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    all_teams = set()
    for member in data["members"].values():
        all_teams.update(member.get("teams", []))

    updated_matchups = []

    for team in sorted(all_teams):
        matched = None
        is_home = False

        for g in espn_games:
            if g["home"].lower() == team.lower() or team.lower() in g["home"].lower():
                matched = g
                is_home = True
                break
            elif g["away"].lower() == team.lower() or team.lower() in g["away"].lower():
                matched = g
                is_home = False
                break

        if matched:
            opponent = matched["away"] if is_home else f"@{matched['home']}"
            res_str = "PENDING"
            if "FINAL" in matched["status"]:
                try:
                    h_score = int(matched["home_score"])
                    a_score = int(matched["away_score"])
                    if is_home:
                        res_str = "WIN" if h_score > a_score else "LOSS"
                    else:
                        res_str = "WIN" if a_score > h_score else "LOSS"
                except:
                    pass

            updated_matchups.append({
                "team": team,
                "opponent": opponent,
                "spread": matched["spread"],
                "over_under": matched["over_under"],
                "game_time": matched["game_time"],
                "status": matched["status"],
                "result": res_str,
                "is_bye": False
            })
        else:
            updated_matchups.append({
                "team": team,
                "opponent": "BYE / TBD",
                "spread": "N/A",
                "over_under": "",
                "game_time": "BYE WEEK",
                "status": "STATUS_SCHEDULED",
                "result": "BYE",
                "is_bye": True
            })

    data["week_matchups"] = updated_matchups

    with open("league_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Successfully updated ESPN live matchups for Week {current_week} ({len(updated_matchups)} teams processed).")

if __name__ == "__main__":
    run_update()
