import os
import json
import requests
from datetime import datetime

CFBD_API_KEY = os.environ.get("CFBD_API_KEY")
HEADERS = {"Authorization": f"Bearer {CFBD_API_KEY}"}
CURRENT_YEAR = datetime.now().year

def get_current_week():
    url = f"https://api.collegefootballdata.com/calendar?year={CURRENT_YEAR}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        calendar = res.json()
        now = datetime.utcnow().isoformat()
        for c in calendar:
            if c.get("firstGameStart") <= now <= c.get("lastGameEnd"):
                return c.get("week", 1)
    return 1  # Default to week 1 if pre-season

def get_week_data(week):
    # 1. Fetch Games for the week
    games_url = f"https://api.collegefootballdata.com/games?year={CURRENT_YEAR}&week={week}&seasonType=regular"
    games_res = requests.get(games_url, headers=HEADERS)
    games = games_res.json() if games_res.status_code == 200 else []

    # 2. Fetch Betting Lines for the week
    lines_url = f"https://api.collegefootballdata.com/lines?year={CURRENT_YEAR}&week={week}&seasonType=regular"
    lines_res = requests.get(lines_url, headers=HEADERS)
    lines = lines_res.json() if lines_res.status_code == 200 else []

    # Map lines by game ID (consensus/preferred provider)
    lines_map = {}
    for g in lines:
        game_id = g.get("id")
        game_lines = g.get("lines", [])
        if game_lines:
            # Use consensus or draftkings/bovada if available
            spread = game_lines[0].get("formattedSpread", "N/A")
            over_under = game_lines[0].get("overUnder", "N/A")
            lines_map[game_id] = {
                "spread": spread,
                "over_under": over_under
            }

    return games, lines_map

def run_update():
    if not os.path.exists("league_data.json"):
        print("league_data.json not found!")
        return

    with open("league_data.json", "r") as f:
        data = json.load(f)

    week = get_current_week()
    data["current_week"] = week
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Collect all unique drafted teams
    all_teams = set()
    for member in data["members"].values():
        all_teams.update(member.get("teams", []))

    games, lines_map = get_week_data(week)
    updated_matchups = []

    for team in sorted(all_teams):
        # Match game where team is home or away
        matched_game = None
        is_home = False

        for g in games:
            if g.get("home_team", "").lower() == team.lower():
                matched_game = g
                is_home = True
                break
            elif g.get("away_team", "").lower() == team.lower():
                matched_game = g
                is_home = False
                break

        if matched_game:
            opponent = matched_game.get("away_team") if is_home else f"@{matched_game.get('home_team')}"
            game_id = matched_game.get("id")
            line_info = lines_map.get(game_id, {"spread": "Line N/A", "over_under": "N/A"})
            
            # Check for completed scores
            home_points = matched_game.get("home_points")
            away_points = matched_game.get("away_points")
            status = "PENDING"
            if home_points is not None and away_points is not None:
                if is_home:
                    status = "WIN" if home_points > away_points else "LOSS"
                else:
                    status = "WIN" if away_points > home_points else "LOSS"

            updated_matchups.append({
                "team": team,
                "opponent": opponent,
                "spread": line_info["spread"],
                "over_under": f"O/U {line_info['over_under']}" if line_info['over_under'] != 'N/A' else '',
                "start_time": matched_game.get("start_date", "TBD"),
                "result": status
            })
        else:
            updated_matchups.append({
                "team": team,
                "opponent": "BYE / TBD",
                "spread": "N/A",
                "over_under": "",
                "start_time": "N/A",
                "result": "BYE"
            })

    data["week_matchups"] = updated_matchups

    with open("league_data.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Successfully updated Week {week} matchups & lines for all {len(all_teams)} teams.")

if __name__ == "__main__":
    run_update()
