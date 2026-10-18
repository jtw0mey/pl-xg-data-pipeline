import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import os

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Premier League xG Dashboard",
    page_icon="⚽",
    layout="wide"
)

# Load Data Function
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
    
    # Standardize column names dynamically
    team_col = None
    for col in ['team_name', 'team', 'team_title', 'teams']:
        if col in df.columns:
            team_col = col
            break
            
    if team_col and team_col != 'team_name':
        df['team_name'] = df[team_col]
        
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Error loading dataset: {e}")
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

# --- RESET BUTTON CALLBACK ---
def reset_filters():
    st.session_state["teams_filter"] = []
    st.session_state["player_search"] = ""
    st.session_state["position_filter"] = []
    st.session_state["minutes_filter"] = 300

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filters")

# Reset Button
st.sidebar.button("Reset Filters", on_click=reset_filters, use_container_width=True)

# 1. Team Filter
teams = sorted(df['team_name'].dropna().unique().tolist()) if 'team_name' in df.columns else []
selected_teams = st.sidebar.multiselect(
    "Select Team(s)",
    options=teams,
    key="teams_filter"
)

# 2. Player Name Search
search_player = st.sidebar.text_input(
    "Search Player Name",
    placeholder="e.g. Haaland",
    key="player_search"
)

# 3. Position Filter
if 'position' in df.columns:
    positions = sorted(df['position'].dropna().unique().tolist())
    selected_positions = st.sidebar.multiselect(
        "Select Position(s)",
        options=positions,
        key="position_filter"
    )
else:
    selected_positions = []

# 4. Minimum Minutes Played Slider
max_mins = int(df['time'].max()) if 'time' in df.columns else 3800
selected_minutes = st.sidebar.slider(
    "Minimum Minutes Played",
    min_value=0,
    max_value=max_mins,
    key="minutes_filter"
)

# --- DUCKDB IN-MEMORY QUERYING & FILTERING ---
con = duckdb.connect(database=':memory:')
con.register('players', df)

where_clauses = ["time >= ?", "time IS NOT NULL"]
params = [selected_minutes]

if selected_teams and 'team_name' in df.columns:
    team_placeholders = ', '.join(['?'] * len(selected_teams))
    where_clauses.append(f"team_name IN ({team_placeholders})")
    params.extend(selected_teams)

if search_player.strip():
    where_clauses.append("LOWER(player_name) LIKE LOWER(?)")
    params.append(f"%{search_player.strip()}%")

if selected_positions and 'position' in df.columns:
    pos_placeholders = ', '.join(['?'] * len(selected_positions))
    where_clauses.append(f"position IN ({pos_placeholders})")
    params.extend(selected_positions)

where_sql = " WHERE " + " AND ".join(where_clauses)
query = f"SELECT * FROM players{where_sql} ORDER BY xG DESC"

filtered_df = con.execute(query, params).df()

# --- MAIN DASHBOARD LAYOUT ---
st.title("⚽ Premier League Expected Goals (xG) Dashboard")
st.markdown("Automated data pipeline querying Understat performance metrics with DuckDB.")

if filtered_df.empty:
    st.warning("No players match your current filter combination. Try clearing or adjusting some filters!")
else:
    # Summary Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Players Displayed", len(filtered_df))
    m2.metric("Total Goals Scored", int(filtered_df['goals'].sum()) if 'goals' in filtered_df.columns else "N/A")
    m3.metric("Total Expected Goals (xG)", round(filtered_df['xG'].sum(), 2) if 'xG' in filtered_df.columns else "N/A")
    
    if 'goals' in filtered_df.columns and 'xG' in filtered_df.columns:
        diff = round(filtered_df['goals'].sum() - filtered_df['xG'].sum(), 2)
        m4.metric("Over/Under Performance", f"{diff:+} xG")

    st.markdown("---")

    # Scatter Plot: Goals vs Expected Goals (xG)
    if 'xG' in filtered_df.columns and 'goals' in filtered_df.columns:
        st.subheader("Goals vs. Expected Goals (xG)")
        
        fig = px.scatter(
            filtered_df,
            x="xG",
            y="goals",
            size="time" if "time" in filtered_df.columns else None,
            color="team_name" if "team_name" in filtered_df.columns else None,
            hover_name="player_name",
            hover_data=["team_name", "position", "time"] if "position" in filtered_df.columns else ["team_name", "time"],
            labels={"xG": "Expected Goals (xG)", "goals": "Actual Goals", "team_name": "Team"},
            title="Player Finishing Performance (Size = Minutes Played)"
        )
        
        max_val = max(filtered_df['xG'].max(), filtered_df['goals'].max()) + 1
        fig.add_shape(
            type="line",
            x0=0, y0=0, x1=max_val, y1=max_val,
            line=dict(color="Gray", dash="dash")
        )
        
        st.plotly_chart(fig, use_container_width=True)

    # Data Table View
    st.subheader("Player Statistics Breakdown")
    
    display_cols = [c for c in ['player_name', 'team_name', 'position', 'time', 'goals', 'xG', 'npg', 'npxG', 'key_passes', 'assists', 'xA'] if c in filtered_df.columns]
    
    st.dataframe(
        filtered_df[display_cols].reset_index(drop=True),
        use_container_width=True,
        hide_index=True
    )