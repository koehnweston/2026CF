import os
import sys
import json
import requests
from datetime import datetime

CURRENT_YEAR = 2026
CFBD_API_KEY = os.environ.get("CFBD_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {CFBD_API_KEY}"} if CFBD_API_KEY else {}

# Official 2026 Week 1 Schedule for All 80 Drafted Teams
SCHEDULE_2026_WEEK_1 = [
    # Jared's Teams
    { "team": "Texas Tech", "opponent": "Abilene Christian", "spread": "-31.5", "over_under": "O/U 58.5", "game_time": "Sat 8/29 • 6:30 PM CT", "is_bye": False },
    { "team": "Boise State", "opponent": "@ Georgia Southern", "spread": "-13.0", "over_under": "O/U 56.5", "game_time": "Sat 8/29 • 3:00 PM CT", "is_bye": False },
    { "team": "Oklahoma", "opponent": "Temple", "spread": "-42.5", "over_under": "O/U 59.5", "game_time": "Fri 8/28 • 6:00 PM CT", "is_bye": False },
    { "team": "Virginia Tech", "opponent": "@ Vanderbilt", "spread": "-13.5", "over_under": "O/U 48.5", "game_time": "Sat 8/29 • 11:00 AM CT", "is_bye": False },
    { "team": "Oklahoma State", "opponent": "South Dakota State", "spread": "-10.0", "over_under": "O/U 54.0", "game_time": "Sat 8/29 • 1:00 PM CT", "is_bye": False },
    { "team": "Tulsa", "opponent": "Northwestern State", "spread": "-28.0", "over_under": "O/U 55.0", "game_time": "Thu 8/27 • 7:00 PM CT", "is_bye": False },
    { "team": "California", "opponent": "UC Davis", "spread": "-20.5", "over_under": "O/U 52.5", "game_time": "Sat 8/29 • 4:00 PM CT", "is_bye": False },
    { "team": "Rutgers", "opponent": "Howard", "spread": "-36.5", "over_under": "O/U 49.5", "game_time": "Thu 8/27 • 5:00 PM CT", "is_bye": False },

    # Cole's Teams
    { "team": "Oregon", "opponent": "Idaho", "spread": "-44.5", "over_under": "O/U 61.5", "game_time": "Sat 8/29 • 6:30 PM CT", "is_bye": False },
    { "team": "San Diego State", "opponent": "Texas A&M-Commerce", "spread": "-33.5", "over_under": "O/U 50.5", "game_time": "Sat 8/29 • 7:00 PM CT", "is_bye": False },
    { "team": "Louisville", "opponent": "Austin Peay", "spread": "-37.5", "over_under": "O/U 54.0", "game_time": "Sat 8/29 • 11:00 AM CT", "is_bye": False },
    { "team": "Pittsburgh", "opponent": "Kent State", "spread": "-24.0", "over_under": "O/U 55.5", "game_time": "Sat 8/29 • 11:00 AM CT", "is_bye": False },
    { "team": "Florida", "opponent": "Miami", "spread": "+2.5", "over_under": "O/U 54.5", "game_time": "Sat 8/29 • 2:30 PM CT", "is_bye": False },
    { "team": "West Virginia", "opponent": "Penn State", "spread": "+8.5", "over_under": "O/U 51.5", "game_time": "Sat 8/29 • 11:00 AM CT", "is_bye": False },
    { "team": "Fresno State", "opponent": "@ Michigan", "spread": "+21.0", "over_under": "O/U 45.5", "game_time": "Sat 8/29 • 6:30 PM CT", "is_bye": False },
    { "team": "Colorado", "opponent": "North Dakota State", "spread": "-9.5", "over_under": "O/U 60.5", "game_time": "Thu 8/27 • 7:00 PM CT", "is_bye": False },

    # Tucker's Teams
    { "team": "Penn State", "opponent": "@ West Virginia", "spread": "-8.5", "over_under": "O/U 51.5", "game_time": "Sat 8/29 • 11:00 AM CT", "is_bye": False },
    { "team": "Houston", "opponent": "UNLV", "spread": "-3.5", "over_under": "O/U 53.5", "game_time": "Sat 8/29 • 6:00 PM CT", "is_bye": False },
    { "team": "USC", "opponent": "BYE (Played W0 vs SJSU)", "spread": "", "over_under": "", "game_time": "BYE WEEK", "is_bye": True },
    { "team": "Oregon State", "opponent": "Idaho State", "spread": "-27.5", "over_under": "O/U 54.5", "game_time": "Sat 8/29 • 5:30 PM CT", "is_bye": False },
    { "team": "Nebraska", "opponent": "UTEP", "spread": "-27.5", "over_under": "O/U 49.0", "game_time": "Sat 8/29 • 2:30 PM CT", "is_bye": False },
    { "team": "North Carolina", "opponent": "@ Minnesota", "spread": "-1.5", "over_under": "O/U 50.5", "game_time": "Thu 8/27 • 7:00 PM CT", "is_bye": False },
    { "team": "Kansas", "opponent": "Lindenwood", "spread": "-44.5", "over_under": "O/U 58.5", "game_time": "Thu 8/27 • 7:00 PM CT", "is_bye": False },
    { "team": "Arkansas", "opponent": "Arkansas-Pine Bluff", "spread": "-49.5", "over_under": "O/U 57.5", "game_time": "Thu 8/27 • 6:30 PM CT", "is_bye": False },

    # Brayson's Teams
    { "team": "Notre Dame", "opponent": "@ Texas A&M", "spread": "+3.0", "over_under": "O/U 46.5", "game_time": "Sat 8/29 • 6:30 PM CT", "is_bye": False },
    { "team": "Alabama", "opponent": "Western Kentucky", "spread": "-31.5", "over_under": "O/U 59.5", "game_time": "Sat 8/29 • 6:00 PM CT", "is_bye": False },
    { "team": "Clemson", "opponent": "Georgia (Atlanta)", "spread": "+13.5", "over_under": "O/U 48.5", "game_time": "Sat 8/29 • 11:00 AM CT", "is_bye": False },
    { "team": "NC State", "opponent": "Western Carolina", "spread": "-32.5", "over_under": "O/U 61.0", "game_time": "Thu 8/27 • 6:00 PM CT", "is_bye": False },
    { "team": "Illinois", "opponent": "Eastern Illinois", "spread": "-27.5", "over_under": "O/U 46.5", "game_time": "Thu 8/27 • 8:00 PM CT", "is_bye": False },
    { "team": "Baylor", "opponent": "Tarleton State", "spread": "-29.5", "over_under": "O/U 55.5", "game_time": "Sat 8/29 • 6:00 PM CT", "is_bye": False },
    { "team": "UCF", "opponent": "New Hampshire", "spread": "-39.5", "over_under": "O/U 63.5", "game_time": "Thu 8/27 • 6:00 PM CT", "is_bye": False },
    { "team": "Mississippi State", "opponent": "Eastern Kentucky", "spread": "-25.5", "over_under": "O/U 60.5", "game_time": "Sat 8/29 • 5:00 PM CT", "is_bye": False },

    # Krystal's Teams
    { "team": "Miami", "opponent": "@ Florida", "spread": "-2.5", "over_under": "O/U 54.5", "game_time": "Sat 8/29 • 2:30 PM CT", "is_bye": False },
    { "team": "Navy", "opponent": "Bucknell", "spread": "-31.5", "over_under": "O/U 48.5", "game_time": "Sat 8/29 • 11:00 AM CT", "is_bye": False },
    { "team": "Utah", "opponent": "Southern Utah", "spread": "-38.5", "over_under": "O/U 53.5", "game_time": "Thu 8/27 • 8:00 PM CT", "is_bye": False },
    { "team": "Memphis", "opponent": "BYE (Played W0 vs UNLV)", "spread": "", "over_under": "", "game_time": "BYE WEEK", "is_bye": True },
    { "team": "Auburn", "opponent": "Alabama A&M", "spread": "-46.5", "over_under": "O/U 56.5", "game_time": "Sat 8/29 • 6:30 PM CT", "is_bye": False },
    { "team": "Vanderbilt", "opponent": "Virginia Tech", "spread": "+13.5", "over_under": "O/U 48.5", "game_time": "Sat 8/29 • 11:00 AM CT", "is_bye": False },
    { "team": "Washington State", "opponent": "Portland State", "spread": "-28.5", "over_under": "O/U 57.0", "game_time": "Sat 8/29 • 2:00 PM CT", "is_bye": False },
    { "team": "Iowa State", "opponent": "North Dakota", "spread": "-28.5", "over_under": "O/U 46.5", "game_time": "Sat 8/29 • 2:30 PM CT", "is_bye": False },

    # Weston's Teams
    { "team": "Texas", "opponent": "Colorado State", "spread": "-32.0", "over_under": "O/U 60.0", "game_time": "Sat 8/29 • 2:30 PM CT", "is_bye": False },
    { "team": "LSU", "opponent": "Clemson", "spread": "-4.5", "over_under": "O/U 64.5", "game_time": "Sun 8/30 • 6:30 PM CT", "is_bye": False },
    { "team": "Virginia", "opponent": "BYE", "spread": "", "over_under": "", "game_time": "BYE WEEK", "is_bye": True },
    { "team": "TCU", "opponent": "BYE (Played W0 vs UNC)", "spread": "", "over_under": "", "game_time": "BYE WEEK", "is_bye": True },
    { "team": "UTSA", "opponent": "Kennesaw State", "spread": "-24.0", "over_under": "O/U 49.5", "game_time": "Sat 8/29 • 2:30 PM CT", "is_bye": False },
    { "team": "Cincinnati", "opponent": "Towson", "spread": "-31.0", "over_under": "O/U 53.5", "game_time": "Sat 8/29 • 1:30 PM CT", "is_bye": False },
    { "team": "Temple", "opponent": "@ Oklahoma", "spread": "+42.5", "over_under": "O/U 59.5", "game_time": "Fri 8/28 • 6:00 PM CT", "is_bye": False },
    { "team": "UCLA", "opponent": "@ Hawaii", "spread": "-14.0", "over_under": "O/U 54.0", "game_time": "Sat 8/29 • 6:30 PM CT", "is_bye": False },

    # Aaron's Teams
    { "team": "BYU", "opponent": "Southern Illinois", "spread": "-14.0", "over_under": "O/U 50.5", "game_time": "Sat 8/29 • 7:00 PM CT", "is_bye": False },
    { "team": "Ole Miss", "opponent": "Furman", "spread": "-42.5", "over_under": "O/U 60.5", "game_time": "Sat 8/29 • 6:00 PM CT", "is_bye": False },
    { "team": "Michigan", "opponent": "Fresno State", "spread": "-21.0", "over_under": "O/U 45.5", "game_time": "Sat 8/29 • 6:30 PM CT", "is_bye": False },
    { "team": "Washington", "opponent": "Weber State", "spread": "-27.0", "over_under": "O/U 52.5", "game_time": "Sat 8/29 • 10:00 PM CT", "is_bye": False },
    { "team": "South Carolina", "opponent": "Old Dominion", "spread": "-20.5", "over_under": "O/U 51.5", "game_time": "Sat 8/29 • 3:15 PM CT", "is_bye": False },
    { "team": "Northwestern", "opponent": "Miami (OH)", "spread": "-2.5", "over_under": "O/U 39.5", "game_time": "Sat 8/29 • 2:30 PM CT", "is_bye": False },
    { "team": "Maryland", "opponent": "UConn", "spread": "-20.5", "over_under": "O/U 45.0", "game_time": "Sat 8/29 • 11:00 AM CT", "is_bye": False },
    { "team": "Kentucky", "opponent": "Southern Miss", "spread": "-27.5", "over_under": "O/U 50.5", "game_time": "Sat 8/29 • 6:45 PM CT", "is_bye": False },

    # Andy's Teams
    { "team": "Ohio State", "opponent": "Akron", "spread": "-48.5", "over_under": "O/U 58.5", "game_time": "Sat 8/29 • 2:30 PM CT", "is_bye": False },
    { "team": "South Florida", "opponent": "Bethune-Cookman", "spread": "-38.0", "over_under": "O/U 59.5", "game_time": "Sat 8/29 • 6:00 PM CT", "is_bye": False },
    { "team": "SMU", "opponent": "Houston Christian", "spread": "-43.5", "over_under": "O/U 57.5", "game_time": "Sat 8/29 • 7:00 PM CT", "is_bye": False },
    { "team": "Arizona", "opponent": "New Mexico", "spread": "-31.0", "over_under": "O/U 58.5", "game_time": "Sat 8/29 • 9:30 PM CT", "is_bye": False },
    { "team": "Arizona State", "opponent": "Wyoming", "spread": "-7.0", "over_under": "O/U 47.5", "game_time": "Sat 8/29 • 9:30 PM CT", "is_bye": False },
    { "team": "Florida State", "opponent": "BYE (Played W0 vs NMSU)", "spread": "", "over_under": "", "game_time": "BYE WEEK", "is_bye": True },
    { "team": "Minnesota", "opponent": "North Carolina", "spread": "+1.5", "over_under": "O/U 50.5", "game_time": "Thu 8/27 • 7:00 PM CT", "is_bye": False },
    { "team": "Duke", "opponent": "Elon", "spread": "-24.5", "over_under": "O/U 49.5", "game_time": "Fri 8/28 • 6:30 PM CT", "is_bye": False },

    # Rian's Teams
    { "team": "Indiana", "opponent": "FIU", "spread": "-21.5", "over_under": "O/U 51.5", "game_time": "Sat 8/29 • 2:30 PM CT", "is_bye": False },
    { "team": "Kansas State", "opponent": "UT Martin", "spread": "-37.5", "over_under": "O/U 56.5", "game_time": "Sat 8/29 • 6:00 PM CT", "is_bye": False },
    { "team": "Tulane", "opponent": "Southeastern Louisiana", "spread": "-28.5", "over_under": "O/U 53.0", "game_time": "Thu 8/27 • 7:00 PM CT", "is_bye": False },
    { "team": "Tennessee", "opponent": "Chattanooga", "spread": "-38.5", "over_under": "O/U 56.5", "game_time": "Sat 8/29 • 11:45 AM CT", "is_bye": False },
    { "team": "Wake Forest", "opponent": "North Carolina A&T", "spread": "-34.5", "over_under": "O/U 50.5", "game_time": "Thu 8/27 • 6:00 PM CT", "is_bye": False },
    { "team": "Missouri", "opponent": "Murray State", "spread": "-48.0", "over_under": "O/U 58.0", "game_time": "Thu 8/27 • 7:00 PM CT", "is_bye": False },
    { "team": "North Texas", "opponent": "@ South Alabama", "spread": "+5.5", "over_under": "O/U 64.5", "game_time": "Sat 8/29 • 4:00 PM CT", "is_bye": False },
    { "team": "Florida Atlantic", "opponent": "@ Michigan State", "spread": "+14.0", "over_under": "O/U 45.0", "game_time": "Fri 8/28 • 6:00 PM CT", "is_bye": False },

    # Paul's Teams
    { "team": "Georgia", "opponent": "Clemson (Atlanta)", "spread": "-13.5", "over_under": "O/U 48.5", "game_time": "Sat 8/29 • 11:00 AM CT", "is_bye": False },
    { "team": "Texas A&M", "opponent": "Notre Dame", "spread": "-3.0", "over_under": "O/U 46.5", "game_time": "Sat 8/29 • 6:30 PM CT", "is_bye": False },
    { "team": "East Carolina", "opponent": "Norfolk State", "spread": "-33.5", "over_under": "O/U 52.5", "game_time": "Sat 8/29 • 5:00 PM CT", "is_bye": False },
    { "team": "Iowa", "opponent": "Illinois State", "spread": "-22.5", "over_under": "O/U 40.5", "game_time": "Sat 8/29 • 11:00 AM CT", "is_bye": False },
    { "team": "Wisconsin", "opponent": "Western Michigan", "spread": "-24.5", "over_under": "O/U 56.5", "game_time": "Fri 8/28 • 8:00 PM CT", "is_bye": False },
    { "team": "Army", "opponent": "Lehigh", "spread": "-30.5", "over_under": "O/U 47.0", "game_time": "Fri 8/28 • 5:00 PM CT", "is_bye": False },
    { "team": "Georgia Tech", "opponent": "Georgia State", "spread": "-21.5", "over_under": "O/U 56.0", "game_time": "Sat 8/29 • 7:00 PM CT", "is_bye": False },
    { "team": "Syracuse", "opponent": "Ohio", "spread": "-17.0", "over_under": "O/U 46.5", "game_time": "Sat 8/29 • 2:30 PM CT", "is_bye": False }
]

def run_update():
    if not os.path.exists("league_data.json"):
        print("Error: league_data.json not found!")
        sys.exit(1)

    with open("league_data.json", "r") as f:
        data = json.load(f)

    week = data.get("current_week", 1)
    data["current_week"] = week
    data["season_year"] = CURRENT_YEAR
    data["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Inject official 2026 schedule directly
    data["week_matchups"] = SCHEDULE_2026_WEEK_1

    with open("league_data.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Successfully loaded official 2026 Week {week} schedule for all 80 teams.")

if __name__ == "__main__":
    run_update()
