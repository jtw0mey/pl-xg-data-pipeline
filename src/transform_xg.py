import html
import json
import os

import pandas as pd

SEASONS = [2025, 2026]
RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
DBT_SEEDS_DIR = "dbt_transforms/seeds"

# Columns kept for the dbt seed files (same layout dbt already expects)
PLAYER_COLUMNS = [
    "id", "player_name", "games", "time", "goals", "xG", "assists", "xA",
    "shots", "key_passes", "yellow_cards", "red_cards", "position",
    "team_title", "npg", "npxG", "xGChain", "xGBuildup",
]
NUMERIC_PLAYER_COLUMNS = [
    "games", "time", "goals", "xG", "assists", "xA", "shots", "key_passes",
    "yellow_cards", "red_cards", "npg", "npxG", "xGChain", "xGBuildup",
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clean_players(season):
    """Turn the raw player JSON from extract_xg.py into clean CSVs."""
    raw_path = os.path.join(RAW_DIR, f"epl_players_{season}.json")
    if not os.path.exists(raw_path):
        print(f"⚠️ No player data found for {season} ({raw_path}), skipping.")
        return

    df = pd.DataFrame(load_json(raw_path))
    df = df[[c for c in PLAYER_COLUMNS if c in df.columns]]

    # Fix HTML characters such as &apos; in names
    df["player_name"] = df["player_name"].astype(str).apply(html.unescape)
    df["team_title"] = df["team_title"].astype(str).apply(html.unescape)

    for col in NUMERIC_PLAYER_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Seed file for dbt (raw columns only)
    df.to_csv(os.path.join(DBT_SEEDS_DIR, f"epl_player_xg_{season}.csv"), index=False)

    # Processed file with extra metrics
    df["xg_overperformance"] = (df["goals"] - df["xG"]).round(1)
    df["xg_per_90"] = df.apply(
        lambda r: round((r["xG"] / r["time"]) * 90, 1) if r["time"] > 0 else 0.0, axis=1
    )
    df.to_csv(os.path.join(PROCESSED_DIR, f"epl_player_xg_{season}_clean.csv"), index=False)
    print(f"✅ Players {season}: {len(df)} rows, up to {int(df['games'].max())} games")


def clean_teams(season):
    """Add up each team's match-by-match history into one row per team."""
    raw_path = os.path.join(RAW_DIR, f"epl_teams_{season}.json")
    if not os.path.exists(raw_path):
        print(f"⚠️ No team data found for {season} ({raw_path}), skipping.")
        return

    rows = []
    for team in load_json(raw_path):
        matches = team.get("history", [])
        rows.append({
            "team_title": html.unescape(team["title"]),
            "matches": len(matches),
            "wins": sum(m["wins"] for m in matches),
            "draws": sum(m["draws"] for m in matches),
            "losses": sum(m["loses"] for m in matches),
            "goals_for": sum(m["scored"] for m in matches),
            "goals_against": sum(m["missed"] for m in matches),
            "points": sum(m["pts"] for m in matches),
            "xG": round(sum(m["xG"] for m in matches), 2),
            "npxG": round(sum(m["npxG"] for m in matches), 2),
            "xGA": round(sum(m["xGA"] for m in matches), 2),
            "npxGA": round(sum(m["npxGA"] for m in matches), 2),
            "xPTS": round(sum(m["xpts"] for m in matches), 2),
        })

    df = pd.DataFrame(rows).sort_values("points", ascending=False)
    df["xg_overperformance"] = (df["goals_for"] - df["xG"]).round(1)
    df["xga_overperformance"] = (df["goals_against"] - df["xGA"]).round(1)
    df.to_csv(os.path.join(PROCESSED_DIR, f"epl_teams_xg_{season}_clean.csv"), index=False)
    print(f"✅ Teams {season}: {len(df)} teams, up to {int(df['matches'].max())} games")


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(DBT_SEEDS_DIR, exist_ok=True)
    for season in SEASONS:
        clean_players(season)
        clean_teams(season)


if __name__ == "__main__":
    main()
