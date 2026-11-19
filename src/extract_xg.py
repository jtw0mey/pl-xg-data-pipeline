import json
import os
import sys
from understatapi import UnderstatClient

SEASONS = ["2025", "2026"]
RAW_DATA_DIR = "data/raw"

def fetch_season_data(client, season):
    """Fetch player and team metrics for a specific season."""
    print(f"Fetching data for {season}/{int(season)+1} season...")
    players = client.league(league="EPL").get_player_data(season=season)
    teams = client.league(league="EPL").get_team_data(season=season)

    if not players or not teams:
        raise ValueError(f"Empty payload returned for season {season}.")

    return players, teams

def main():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    failed_seasons = []

    with UnderstatClient() as client:
        for season in SEASONS:
            try:
                players, teams = fetch_season_data(client, season)

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
