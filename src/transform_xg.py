import os
import pandas as pd

def clean_season_data(season):
    os.makedirs('data/processed', exist_ok=True)
    
    # 1. Clean Players
    p_raw = f'data/raw/epl_player_xg_{season}.csv'
    if os.path.exists(p_raw):
        df_p = pd.read_csv(p_raw)
        numeric_cols = ['goals', 'xG', 'time', 'games', 'npg', 'npxG', 'assists', 'xA']
        for col in numeric_cols:
            if col in df_p.columns:
                df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0)
        df_p['xg_overperformance'] = (df_p['goals'] - df_p['xG']).round(1)
        df_p['xg_per_90'] = df_p.apply(
            lambda r: round((r['xG'] / r['time']) * 90, 1) if r['time'] > 0 else 0.0, axis=1
        )
        df_p.to_csv(f'data/processed/epl_player_xg_{season}_clean.csv', index=False)

    # 2. Clean Teams
    t_raw = f'data/raw/epl_teams_xg_{season}.csv'
    if os.path.exists(t_raw):
        df_t = pd.read_csv(t_raw)
        df_t['xg_overperformance'] = (df_t['goals_for'] - df_t['xG']).round(1)
        df_t['xga_overperformance'] = (df_t['goals_against'] - df_t['xGA']).round(1)
        df_t.to_csv(f'data/processed/epl_teams_xg_{season}_clean.csv', index=False)

    print(f"Processed season {season} data successfully.")

def main():
    for season in [2025, 2026]:
        clean_season_data(season)

if __name__ == "__main__":
    main()
