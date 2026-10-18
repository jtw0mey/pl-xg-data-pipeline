import asyncio
import json
import os
import sys
import aiohttp
from understat import Understat

SEASONS = ["2024", "2025"]
RAW_DATA_DIR = "data/raw"

async def fetch_season_data(understat, season):
    """Fetch player and team metrics for a specific season with error handling."""
    print(f"Fetching data for {season}/{int(season)+1} season...")
    try:
        players = await understat.get_league_players("epl", int(season))
        teams = await understat.get_teams("epl", int(season))
        
        if not players or not teams:
            raise ValueError(f"Empty payload returned for season {season}.")
            
        return players, teams
    except Exception as e:
        print(f"❌ Error fetching season {season}: {e}")
        return None, None

async def main():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        
        for season in SEASONS:
            try:
                players, teams = await fetch_season_data(understat, season)
                
                if players and teams:
                    player_file = os.path.join(RAW_DATA_DIR, f"epl_players_{season}.json")
                    team_file = os.path.join(RAW_DATA_DIR, f"epl_teams_{season}.json")
                    
                    with open(player_file, "w", encoding="utf-8") as f:
                        json.dump(players, f, indent=2)
                    with open(team_file, "w", encoding="utf-8") as f:
                        json.dump(teams, f, indent=2)
                        
                    print(f"✅ Successfully saved data for season {season}")
                else:
                    print(f"⚠️ Skipping write for season {season} due to missing data.")
            except Exception as e:
                print(f"❌ Unexpected error processing season {season}: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Critical Pipeline Failure: {e}")
        sys.exit(1)
