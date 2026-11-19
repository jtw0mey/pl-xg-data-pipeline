import codecs
import json
import os
import re
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def extract_embedded_json(html, var_name):
    """Decode Understat's hex-escaped JSON.parse('...') script variables."""
    pattern = rf"{var_name}\s*=\s*JSON\.parse\('([^']+)'\)"
    match = re.search(pattern, html)
    if not match:
        return None
    decoded_str = codecs.decode(match.group(1), "unicode_escape")
    return json.loads(decoded_str)

def fetch_season_data(session, season):
    """Fetch player and team metrics from Understat's league page."""
    print(f"Fetching data for {season}/{int(season)+1} season...")
    url = f"https://understat.com/league/EPL/{season}"

    response = session.get(url, headers=HEADERS, timeout=20)
    print(f"HTTP {response.status_code} | Response length: {len(response.text)} chars")

    if response.status_code != 200:
        raise ValueError(f"HTTP {response.status_code}: {response.text[:200]!r}")

    players = extract_embedded_json(response.text, "playersData")
    teams = extract_embedded_json(response.text, "teamsData")

    if not players or not teams:
        # Print snippet of the 26k HTML so we can see why variables weren't found
        snippet = re.sub(r"\s+", " ", response.text[:400])
        raise ValueError(f"Could not find playersData/teamsData in HTML. Preview: {snippet!r}")

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
