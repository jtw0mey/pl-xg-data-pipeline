import json
import os
import sys
import requests

SEASONS = ["2025", "2026"]
RAW_DATA_DIR = "data/raw"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

def fetch_season_data(session, season):
    """Fetch player and team metrics directly from Understat's JSON API."""
    print(f"Fetching data for {season}/{int(season)+1} season...")
    url = f"https://understat.com/getLeagueData/EPL/{season}"
    headers = {**HEADERS, "Referer": f"https://understat.com/league/EPL/{season}"}

    # Warm up session cookies on the league page first
    session.get(f"https://understat.com/league/EPL/{season}", headers=headers, timeout=20)

    response = session.get(url, headers=headers, timeout=20)
    print(f"HTTP {response.status_code} | Response length: {len(response.text)} chars")

    if response.status_code != 200 or not response.text.strip():
        raise ValueError(
            f"Blocked or empty response (HTTP {response.status_code}): {response.text[:200]!r}"
        )

    payload = response.json()
    players = payload.get("players")
    teams = payload.get("teams")

    if not players or not teams:
        raise ValueError(f"Missing 'players' or 'teams' keys in response: {list(payload.keys())}")

    return players, teams

def main():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    failed_seasons = []

    with requests.Session() as session:
        for season in SEASONS:
            try:
                players, teams = fetch_season_data(session, season)

                player_file = os.path.join(RAW_DATA_DIR, f"epl_players_{season}.json")
                team_file = os.path.join(RAW_DATA_DIR, f"epl_teams_{season}.json")

                with open(player_file, "w", encoding="utf-8") as f:
                    json.dump(players, f, indent=2)
                with open(team_file, "w", encoding="utf-8") as f:
                    json.dump(teams, f, indent=2)

                print(f"✅ Successfully saved data for season {season}")
            except Exception as e:
                print(f"❌ Error fetching season {season}: {e}")
                failed_seasons.append(season)

    if failed_seasons:
        print(f"❌ Pipeline failed for seasons: {failed_seasons}")
        sys.exit(1)

if __name__ == "__main__":
    main()
