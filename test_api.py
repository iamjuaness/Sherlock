import urllib.request
import json
import sys

url = 'http://localhost:8000/api/v1/compare/football'
data = {
    "home": {
        "name": "Team A", "goals_per_game": 2.0, "goals_conceded_per_game": 1.0,
        "goal_conversion_pct": 15.0, "big_chances_per_game": 3.0, "big_chances_missed_per_game": 1.5,
        "shots_per_game": 12.0, "shots_on_target_per_game": 5.0, "shots_off_target_per_game": 4.0, "corners_per_game": 6.0, "possession_pct": 55.0,
        "clean_sheets": 8.0, "balls_recovered_per_game": 45.0, "yellow_cards_per_game": 2.0,
        "fouls_per_game": 11.0, "offsides_per_game": 2.0, "wins": 12.0, "draws": 4.0, "losses": 4.0
    },
    "away": {
        "name": "Team B", "goals_per_game": 1.2, "goals_conceded_per_game": 1.5,
        "goal_conversion_pct": 12.0, "big_chances_per_game": 2.0, "big_chances_missed_per_game": 1.0,
        "shots_per_game": 10.0, "shots_on_target_per_game": 4.0, "shots_off_target_per_game": 4.0, "corners_per_game": 4.0, "possession_pct": 45.0,
        "clean_sheets": 5.0, "balls_recovered_per_game": 40.0, "yellow_cards_per_game": 2.5,
        "fouls_per_game": 13.0, "offsides_per_game": 1.5, "wins": 8.0, "draws": 6.0, "losses": 6.0
    },
    "odds": {
        "home": 1.80, "draw": 3.60, "away": 4.20,
        "over_25": 1.95, "under_25": 1.85, "btts_yes": 1.70, "btts_no": 2.10, "bookmaker": "Test"
    }
}

req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
