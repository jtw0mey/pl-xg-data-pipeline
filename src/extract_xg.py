import json
import os
from understatapi import UnderstatClient

def fetch_epl_player_xg(season="2026"):
    """
    Fetches Premier League player statistics (including xG) from Understat
    and saves the raw JSON output to data/raw.
    """
    print(f"Fetching Premier League player xG data for season {season}...")
    
    with UnderstatClient() as understat:
        player_data = understat.league(league="EPL").get_player_data(season=season)
    
    os.makedirs("data/raw", exist_ok=True)
    
    output_path = f"data/raw/epl_player_xg_{season}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(player_data, f, indent=4)
        
    print(f"Successfully downloaded {len(player_data)} player records!")
    print(f"File saved to: {output_path}")

if __name__ == "__main__":
    fetch_epl_player_xg()
