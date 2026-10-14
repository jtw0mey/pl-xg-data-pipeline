import duckdb
import os

def run_sql_queries():
    """
    Connects to DuckDB, queries the cleaned CSV file using standard SQL,
    and displays key analytical insights.
    """
    csv_path = "data/processed/epl_player_xg_2026_clean.csv"
    
    if not os.path.exists(csv_path):
        print(f"Error: Cleaned data file {csv_path} not found. Run transform_xg.py first!")
        return

    print("--- Connecting to DuckDB Analytical Engine ---\n")
    con = duckdb.connect()

    # Query 1: Top 5 Overperforming Players (Most Clinical Finishers)
    print("1. Most Clinical Finishers (Goals Scored Exceeding xG):")
    query_overperformance = f"""
        SELECT 
            player_name, 
            team_title, 
            goals, 
            xG, 
            xg_overperformance
        FROM '{csv_path}'
        WHERE goals >= 5
        ORDER BY xg_overperformance DESC
        LIMIT 5;
    """
    df_over = con.execute(query_overperformance).df()
    print(df_over.to_string(index=False))
    print("\n" + "="*60 + "\n")

    # Query 2: Top 5 Underperforming Players (Unlucky / Wasteful)
    print("2. Most Underperforming Finishers (Lowest Goals vs xG):")
    query_underperformance = f"""
        SELECT 
            player_name, 
            team_title, 
            goals, 
            xG, 
            xg_overperformance
        FROM '{csv_path}'
        WHERE xG >= 5.0
        ORDER BY xg_overperformance ASC
        LIMIT 5;
    """
    df_under = con.execute(query_underperformance).df()
    print(df_under.to_string(index=False))

if __name__ == "__main__":
    run_sql_queries()