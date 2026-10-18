import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import os

# --- PAGE SETUP ---
st.set_page_config(
    page_title="Premier League xG Analytics",
    page_icon="⚽",
    layout="wide"
)

# --- LOAD DATA ---
@st.cache_data
def load_data():
    file_path = "data/processed/player_stats.csv"
    if not os.path.exists(file_path):
        for root, dirs, files in os.walk("."):
            for file in files:
                if file.endswith(".csv") and "player" in file.lower():
                    file_path = os.path.join(root, file)
                    break
                    
    df = pd.read_csv(file_path)
    
    # Standardize column mapping dynamically
    team_col = next((c for c in ['team_name', 'team', 'team_title', 'teams'] if c in df.columns), None)
    if team_col and team_col != 'team_name':
        df['team_name'] = df[team_col]
        
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# --- INITIALIZE SESSION STATE FOR FILTERS ---
if "teams_filter" not in st.session_state:
    st.session_state["teams_filter"] = []
if "player_search" not in st.session_state:
    st.session_state["player_search"] = ""
if "position_filter" not in st.session_state:
    st.session_state["position_filter"] = []
if "minutes_filter" not in st.session_state:
    st.session_state["minutes_filter"] = 300

def reset_filters():
    st.session_state["teams_filter"] = []
    st.session_state["player_search"] = ""
    st.session_state["position_filter"] = []
    st.session_state["minutes_filter"] = 300

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filters")
st.sidebar.button("Reset Filters", on_click=reset_filters, use_container_width=True)

# 1. Team Filter
teams = sorted(df['team_name'].dropna().unique().tolist()) if 'team_name' in df.columns else []
selected_teams = st.sidebar.multiselect("Select Team(s)", options=teams, key="teams_filter")

# 2. Player Search
search_player = st.sidebar.text_input("Search Player Name", placeholder="e.g. Haaland", key="player_search")

# 3. Position Filter
if 'position' in df.columns:
    positions = sorted(df['position'].dropna().unique().tolist())
    selected_positions = st.sidebar.multiselect("Select Position(s)", options=positions, key="position_filter")
else:
    selected_positions = []

# 4. Minimum Minutes Slider
max_mins = int(df['time'].max()) if 'time' in df.columns else 3800
selected_minutes = st.sidebar.slider("Minimum Minutes Played", min_value=0, max_value=max_mins, key="minutes_filter")

# --- TOGGLES & OPTIONS ---
st.sidebar.markdown("---")
st.sidebar.header("Display Settings")
exclude_penalties = st.sidebar.toggle("Exclude Penalties (npxG / Non-Penalty Goals)", value=False)

# --- DUCKDB FILTERING ---
con = duckdb.connect(database=':memory:')
con.register('players', df)

where_clauses = ["time >= ?", "time IS NOT NULL"]
params = [selected_minutes]

if selected_teams and 'team_name' in df.columns:
    placeholders = ', '.join(['?'] * len(selected_teams))
    where_clauses.append(f"team_name IN ({placeholders})")
    params.extend(selected_teams)

if search_player.strip():
    where_clauses.append("LOWER(player_name) LIKE LOWER(?)")
    params.append(f"%{search_player.strip()}%")

if selected_positions and 'position' in df.columns:
    placeholders = ', '.join(['?'] * len(selected_positions))
    where_clauses.append(f"position IN ({placeholders})")
    params.extend(selected_positions)

where_sql = " WHERE " + " AND ".join(where_clauses)
target_xg = "npxG" if exclude_penalties and "npxG" in df.columns else "xG"
query = f"SELECT * FROM players{where_sql} ORDER BY {target_xg} DESC"

filtered_df = con.execute(query, params).df()

# Set active metric columns based on toggle
goal_col = "npg" if exclude_penalties and "npg" in filtered_df.columns else "goals"
xg_col = "npxG" if exclude_penalties and "npxG" in filtered_df.columns else "xG"

# --- MAIN DASHBOARD LAYOUT ---
st.title("⚽ Premier League Expected Goals (xG) Dashboard")
st.markdown("Automated data pipeline querying Understat performance metrics with DuckDB.")

if filtered_df.empty:
    st.warning("No players match your current filter combination. Try clearing or adjusting some filters!")
else:
    # --- SUMMARY METRICS ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Players Displayed", len(filtered_df))
    m2.metric("Total Goals", int(filtered_df[goal_col].sum()) if goal_col in filtered_df.columns else "N/A")
    m3.metric(f"Total {xg_col}", round(filtered_df[xg_col].sum(), 2) if xg_col in filtered_df.columns else "N/A")
    if goal_col in filtered_df.columns and xg_col in filtered_df.columns:
        diff = round(filtered_df[goal_col].sum() - filtered_df[xg_col].sum(), 2)
        m4.metric("Over/Under Performance", f"{diff:+} {xg_col}")

    st.markdown("---")

    # --- TOP PERFORMERS HIGHLIGHT SECTION ---
    st.subheader("🌟 Category Leaders")
    top_col1, top_col2, top_col3 = st.columns(3)
    
    if goal_col in filtered_df.columns:
        top_scorer = filtered_df.sort_values(by=goal_col, ascending=False).iloc[0]
        top_col1.info(f"⚽ **Top Scorer:** {top_scorer['player_name']} ({top_scorer['team_name']}) — **{int(top_scorer[goal_col])} Goals**")
        
    if goal_col in filtered_df.columns and xg_col in filtered_df.columns:
        filtered_df['overperformance'] = filtered_df[goal_col] - filtered_df[xg_col]
        top_finisher = filtered_df.sort_values(by='overperformance', ascending=False).iloc[0]
        top_col2.success(f"🔥 **Best Finisher (vs xG):** {top_finisher['player_name']} ({top_finisher['team_name']}) — **+{top_finisher['overperformance']:.2f} over xG**")
        
    if 'key_passes' in filtered_df.columns:
        top_creator = filtered_df.sort_values(by='key_passes', ascending=False).iloc[0]
        top_col3.warning(f"🎯 **Top Playmaker:** {top_creator['player_name']} ({top_creator['team_name']}) — **{int(top_creator['key_passes'])} Key Passes**")

    st.markdown("---")

    # --- VISUALIZATION SEARCH & SCATTER PLOT ---
    st.subheader("Goals vs. Expected Goals Analysis")
    
    plot_search = st.text_input("🔍 Highlight Specific Player on Plot", placeholder="Type a player name to highlight...")
    
    filtered_df['highlight'] = False
    if plot_search.strip():
        filtered_df['highlight'] = filtered_df['player_name'].str.contains(plot_search.strip(), case=False, na=False)

    fig = px.scatter(
        filtered_df,
        x=xg_col,
        y=goal_col,
        size="time" if "time" in filtered_df.columns else None,
        color="team_name" if "team_name" in filtered_df.columns else None,
        hover_name="player_name",
        hover_data=["team_name", "position", "time"] if "position" in filtered_df.columns else ["team_name", "time"],
        labels={xg_col: f"Expected Goals ({xg_col})", goal_col: f"Actual Goals ({goal_col})", "team_name": "Team"},
        title=f"Player Finishing Performance ({goal_col} vs {xg_col})"
    )
    
    # Add 1:1 Trendline
    max_val = max(filtered_df[xg_col].max(), filtered_df[goal_col].max()) + 1
    fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="Gray", dash="dash"))
    
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- TABBED DATA TABLES (PLAYER & TEAM STATS) ---
    tab1, tab2 = st.tabs(["👤 Player Breakdown", "🛡️ Team Aggregates"])

    with tab1:
        st.subheader("Individual Player Statistics")
        player_cols = [c for c in ['player_name', 'team_name', 'position', 'time', goal_col, xg_col, 'key_passes', 'assists', 'xA'] if c in filtered_df.columns]
        st.dataframe(filtered_df[player_cols].reset_index(drop=True), use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Aggregated Team Statistics")
        if 'team_name' in filtered_df.columns:
            team_summary = filtered_df.groupby('team_name').agg({
                'player_name': 'count',
                goal_col: 'sum',
                xg_col: 'sum',
                'key_passes': 'sum' if 'key_passes' in filtered_df.columns else 'count',
                'assists': 'sum' if 'assists' in filtered_df.columns else 'count'
            }).rename(columns={'player_name': 'Active Players'}).reset_index()
            
            team_summary['xG Overperformance'] = team_summary[goal_col] - team_summary[xg_col]
            st.dataframe(team_summary.sort_values(by=xg_col, ascending=False), use_container_width=True, hide_index=True)