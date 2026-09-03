import os
import sys
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# ESPN API endpoints to capture all FBS and Non-Conf matchups
ESPN_URLS = [
    "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=80&limit=300",
    "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=81&limit=300"
]

def fetch_all_espn_games():
    events = []
    current_week = 1
    
    for url in ESPN_URLS:
        try:
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                data = res.json()
                week_info = data.get("week", {})
                current_week = week_info.get("number", current_week)
                events.extend(data.get("events", []))
        except Exception as e:
            print(f"Notice: Error fetching from {url}: {e}")
            
    return current_week, events

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

def run_update():
    if not os.path.exists("league_data.json"):
        print("Error: league_data.json not found!")
        sys.exit(1)

    with open("league_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    current_week, events = fetch_all_espn_games()
    games = parse_events(events)

    data["current_week"] = current_week
    data["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    all_teams = set()
    for member in data["members"].values():
        all_teams.update(member.get("teams", []))

    updated_matchups = []

    for team in sorted(all_teams):
        matched_games = []

        # Find ALL matching games for this team in ESPN's feed
        for g in games:
            if matches_team(team, g["home_obj"]):
                matched_games.append((g, True)) # (game, is_home)
            elif matches_team(team, g["away_obj"]):
                matched_games.append((g, False))

        if matched_games:
            # PRIORITY: Pick upcoming games (STATUS_SCHEDULED or IN_PROGRESS) first.
            # If all are FINAL, pick the newest game.
            upcoming = [item for item in matched_games if "FINAL" not in item[0]["status"]]
            if upcoming:
                selected_game, is_home = upcoming[0]
            else:
                selected_game, is_home = matched_games[-1]

            opponent = selected_game["away_loc"] if is_home else f"@{selected_game['home_loc']}"
            res_str = "PENDING"
            if "FINAL" in selected_game["status"]:
                try:
                    h_score = int(selected_game["home_score"])
                    a_score = int(selected_game["away_score"])
                    if is_home:
                        res_str = "WIN" if h_score > a_score else "LOSS"
                    else:
                        res_str = "WIN" if a_score > h_score else "LOSS"
                except:
                    pass

            updated_matchups.append({
                "team": team,
                "opponent": opponent,
                "spread": selected_game["spread"],
                "over_under": selected_game["over_under"],
                "game_time": selected_game["game_time"],
                "status": selected_game["status"],
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

    print(f"Successfully processed live ESPN matchups for Week {current_week} ({len(updated_matchups)} teams).")

if __name__ == "__main__":
    run_update()
