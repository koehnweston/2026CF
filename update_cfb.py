import os
import sys
import json
import requests
from datetime import datetime

# Enforce 2026 Season
CURRENT_YEAR = 2026
CFBD_API_KEY = os.environ.get("CFBD_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {CFBD_API_KEY}"} if CFBD_API_KEY else {}

def get_current_week():
    try:
        url = f"https://api.collegefootballdata.com/calendar?year={CURRENT_YEAR}"
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            calendar = res.json()
            now = datetime.utcnow().isoformat()
            for c in calendar:
                start = c.get("firstGameStart")
                end = c.get("lastGameEnd")
                # Ensure both dates are valid strings (not None) before comparison
                if start and end and isinstance(start, str) and isinstance(end, str):
                    if start <= now <= end:
                        return c.get("week", 1)
    except Exception as e:
        print(f"Notice: Calendar lookup ({e}), defaulting to Week 1.")
    return 1

def get_week_data(week):
    games = []
    lines_map = {}

    # 1. Fetch 2026 Games
    try:
        games_url = f"https://api.collegefootballdata.com/games?year={CURRENT_YEAR}&week={week}&seasonType=regular"
        res = requests.get(games_url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            games = res.json()
            print(f"Retrieved {len(games)} games for 2026 Week {week}.")
        else:
            print(f"Notice: Games endpoint returned status {res.status_code}.")
    except Exception as e:
        print(f"Games fetch notice: {e}")

    # 2. Fetch 2026 Betting Lines
    try:
        lines_url = f"https://api.collegefootballdata.com/lines?year={CURRENT_YEAR}&week={week}&seasonType=regular"
        res = requests.get(lines_url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            lines = res.json()
            for g in lines:
                game_id = g.get("id")
                game_lines = g.get("lines", [])
                if game_lines:
                    spread = game_lines[0].get("formattedSpread", "N/A")
                    over_under = game_lines[0].get("overUnder", "N/A")
                    lines_map[game_id] = {
                        "spread": spread,
                        "over_under": over_under
                    }
            print(f"Retrieved betting lines for {len(lines_map)} games.")
        else:
            print(f"Notice: Lines endpoint returned status {res.status_code}.")
    except Exception as e:
        print(f"Lines fetch notice: {e}")

    return games, lines_map

def run_update():
    if not os.path.exists("league_data.json"):
        print("Error: league_data.json not found!")
        sys.exit(1)

    with open("league_data.json", "r") as f:
        data = json.load(f)

    week = get_current_week()
    data["current_week"] = week
    data["season_year"] = CURRENT_YEAR
    data["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    all_teams = set()
    for member in data["members"].values():
        all_teams.update(member.get("teams", []))

    games, lines_map = get_week_data(week)
    updated_matchups = []

    for team in sorted(all_teams):
        matched_game = None
        is_home = False

        for g in games:
            home = (g.get("home_team") or "").lower()
            away = (g.get("away_team") or "").lower()
            if home == team.lower():
                matched_game = g
                is_home = True
                break
            elif away == team.lower():
                matched_game = g
                is_home = False
                break

        if matched_game:
            opp_name = matched_game.get("away_team") if is_home else f"@{matched_game.get('home_team')}"
            game_id = matched_game.get("id")
            line_info = lines_map.get(game_id, {"spread": "Line TBD", "over_under": "N/A"})

            raw_date = matched_game.get("start_date", "")
            time_display = "Sat • Time TBD CT"
            if raw_date:
                try:
                    dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                    time_display = dt.strftime("%a %m/%d • %I:%M %p CT")
                except:
                    time_display = raw_date

            updated_matchups.append({
                "team": team,
                "opponent": opp_name,
                "spread": line_info["spread"],
                "over_under": f"O/U {line_info['over_under']}" if line_info['over_under'] != 'N/A' else '',
                "game_time": time_display,
                "is_bye": False
            })
        else:
            # Preserve existing entry if present
            existing = next((m for m in data.get("week_matchups", []) if m.get("team") == team), None)
            if existing:
                updated_matchups.append(existing)
            else:
                updated_matchups.append({
                    "team": team,
                    "opponent": "BYE / TBD",
                    "spread": "N/A",
                    "over_under": "",
                    "game_time": "BYE WEEK",
                    "is_bye": True
                })

    data["week_matchups"] = updated_matchups

    with open("league_data.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Successfully processed 2026 Week {week} data for all {len(all_teams)} teams.")

if __name__ == "__main__":
    run_update()
