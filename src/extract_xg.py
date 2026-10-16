import os
import pandas as pd
from understat import Understat
import aiohttp
import asyncio

async def fetch_data(season):
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        
        # 1. Fetch Players
        players = await understat.get_league_players("EPL", season)
        df_players = pd.DataFrame(players)
        
        # 2. Fetch Team Table Data
        teams_data = await understat.get_teams("EPL", season)
        team_rows = []
        
        for team_info in teams_data:
            title = team_info.get('title')
            history = team_info.get('history', [])
            
            # Understat uses 'scored' for goals_for, 'missed' for goals_against
            m = len(history)
            w = sum(int(x.get('wins', 0) if 'wins' in x else (1 if x.get('pts') == 3 else 0)) for x in history)
            d = sum(int(x.get('draws', 0) if 'draws' in x else (1 if x.get('pts') == 1 else 0)) for x in history)
            l = sum(int(x.get('loses', 0) if 'loses' in x else (1 if x.get('pts') == 0 else 0)) for x in history)
            g = sum(int(x.get('scored', 0)) for x in history)
            ga = sum(int(x.get('missed', 0)) for x in history)
            pts = sum(int(x.get('pts', 0)) for x in history)
            xg = sum(float(x.get('xG', 0)) for x in history)
            npxg = sum(float(x.get('npxG', 0)) for x in history)
            xga = sum(float(x.get('xGA', 0)) for x in history)
            npxga = sum(float(x.get('npxGA', 0)) for x in history)
            xpts = sum(float(x.get('xpts', 0)) for x in history)
            
            team_rows.append({
                'team_title': title,
                'matches': m, 'wins': w, 'draws': d, 'losses': l,
                'goals_for': g, 'goals_against': ga, 'points': pts,
                'xG': round(xg, 1), 'npxG': round(npxg, 1),
                'xGA': round(xga, 1), 'npxGA': round(npxga, 1),
                'xPTS': round(xpts, 1)
            })
        
        df_teams = pd.DataFrame(team_rows)
        return df_players, df_teams

def main():
    os.makedirs('data/raw', exist_ok=True)
    seasons = [2025, 2026]
    
    for season in seasons:
        print(f"Fetching Premier League data (players + teams) for {season} season...")
        df_p, df_t = asyncio.run(fetch_data(season))
        
        df_p.to_csv(f'data/raw/epl_player_xg_{season}.csv', index=False)
        df_t.to_csv(f'data/raw/epl_teams_xg_{season}.csv', index=False)
        print(f"Saved raw data for {season}")

if __name__ == "__main__":
    main()
