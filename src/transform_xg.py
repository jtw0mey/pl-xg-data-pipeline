import json
import os
import pandas as pd

def transform_player_data(season="2026"):
    """
    Reads raw JSON player xG data, cleans data types, computes analytical 
    metrics (xG difference), and saves cleaned CSV output.
    """
    input_file = f"data/raw/epl_player_xg_{season}.json"
    
    if not os.path.exists(input_file):
        print(f"Error: Raw file {input_file} not found. Run extract_xg.py first!")
        return

    print(f"Loading raw JSON from {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Convert list of dictionaries into a Pandas DataFrame
    df = pd.DataFrame(raw_data)

    # Select core columns relevant for performance analysis
    selected_cols = [
        "id", "player_name", "team_title", "games", "time", 
        "goals", "xG", "assists", "xA", "shots", "key_passes", "npg", "npxG"
    ]
    df = df[selected_cols].copy()

    # Cast fields to numeric data types
    numeric_cols = ["games", "time", "goals", "xG", "assists", "xA", "shots", "key_passes", "npg", "npxG"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Round float columns for clean reporting
    float_cols = ["xG", "xA", "npxG"]
    df[float_cols] = df[float_cols].round(2)

    # Feature Engineering: Compute metrics
    # 1. Goal Difference vs xG (Positive = Overperforming, Negative = Underperforming)
    df["xg_overperformance"] = (df["goals"] - df["xG"]).round(2)
    
    # 2. xG per 90 Minutes
    df["xg_per_90"] = ((df["xG"] / df["time"]) * 90).round(2)
    df["xg_per_90"] = df["xg_per_90"].fillna(0)

    # Sort table by highest expected goals
    df = df.sort_values(by="xG", ascending=False).reset_index(drop=True)

    # Ensure processed output directory exists
    os.makedirs("data/processed", exist_ok=True)

    # Save clean CSV output
    csv_output = f"data/processed/epl_player_xg_{season}_clean.csv"
    df.to_csv(csv_output, index=False)

    print(f"\n--- Data Transformation Complete ---")
    print(f"Processed {len(df)} players.")
    print(f"Saved clean CSV to: {csv_output}\n")
    print("Top 5 Players by xG:")
    print(df[["player_name", "team_title", "goals", "xG", "xg_overperformance"]].head(5))

if __name__ == "__main__":
    transform_player_data()