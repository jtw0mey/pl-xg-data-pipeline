import os
import html
import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Premier League xG Dashboard",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Premier League xG Analytics Engine")
st.markdown("Interactive goals vs. xG metrics extracted from Understat and powered by **DuckDB** & **dbt**, built by Jack Twomey.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def map_position_category(pos_str):
    if not pos_str or pd.isna(pos_str):
        return "Unknown"
    pos = str(pos_str).upper()
    if 'GK' in pos:
        return "Goalkeeper"
    elif 'F' in pos:
        return "Forward"
    elif 'M' in pos:
        return "Midfielder"
    elif 'D' in pos:
        return "Defender"
    return "Other"

@st.cache_data
def load_all_data():
    db_path = os.path.join(BASE_DIR, 'dbt_transforms', 'dev.duckdb')
    
    if not os.path.exists(db_path):
        st.error(f"DuckDB database not found at `{db_path}`. Run `dbt run` first!")
        return pd.DataFrame(), pd.DataFrame()
        
    conn = duckdb.connect(db_path, read_only=True)
    
    # 1. Load Player Data
    df_players = conn.execute("SELECT * FROM fct_player_xg_summary").df()
    df_players = df_players.rename(columns={
        'total_minutes': 'time',
        'total_goals': 'goals',
        'total_xg': 'xG',
        'total_npg': 'npg',
        'total_npxg': 'npxG',
        'team_name': 'team_title'
    })
    
    if 'player_name' in df_players.columns:
        df_players['player_name'] = df_players['player_name'].astype(str).apply(html.unescape)
        
    if 'team_title' in df_players.columns:
        df_players['team_title'] = df_players['team_title'].astype(str).apply(
            lambda x: html.unescape(x).split(',')[-1].strip() if x else x
        )

    if 'xG' in df_players.columns and 'goals' in df_players.columns:
        df_players['xg_overperformance'] = (df_players['goals'] - df_players['xG']).round(1)
        
    if 'npxG' in df_players.columns and 'npg' in df_players.columns:
        df_players['npxg_overperformance'] = (df_players['npg'] - df_players['npxG']).round(1)

    if 'time' in df_players.columns:
        df_players['xg_per_90'] = df_players.apply(
            lambda r: round((r['xG'] / r['time']) * 90, 1) if r['time'] > 0 else 0.0, axis=1
        )
        df_players['npxg_per_90'] = df_players.apply(
            lambda r: round((r['npxG'] / r['time']) * 90, 1) if r['time'] > 0 else 0.0, axis=1
        )

    df_players['position_cat'] = "Forward"

    # 2. Build Team Summary Data from Player Aggregations
    if not df_players.empty and 'team_title' in df_players.columns:
        df_teams = df_players.groupby('team_title').agg(
            goals_for=('goals', 'sum'),
            xG=('xG', 'sum'),
            np_goals_for=('npg', 'sum'),
            npxG=('npxG', 'sum')
        ).reset_index()
        
        df_teams['goals_against'] = 0
        df_teams['xGA'] = 0.0
        df_teams['np_goals_against'] = 0
        df_teams['npxGA'] = 0.0
        df_teams['xg_per_90'] = (df_teams['xG'] / 7).round(1)
        df_teams['xga_per_90'] = 0.0
        df_teams['npxg_per_90'] = (df_teams['npxG'] / 7).round(1)
        df_teams['npxga_per_90'] = 0.0
    else:
        df_teams = pd.DataFrame()

    conn.close()
    return df_players, df_teams

# Load player and team data
df_p, df_t = load_all_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filters")

combined_teams = sorted(list(df_p['team_title'].dropna().unique())) if 'team_title' in df_p.columns else []
selected_team = st.sidebar.multiselect("Select Team(s)", options=combined_teams, key="global_team_filter")

search_player = st.sidebar.text_input("Search Player Name", placeholder="e.g. Haaland", key="global_player_search")

pos_options = ["Forward", "Midfielder", "Defender", "Goalkeeper"]
selected_positions = st.sidebar.multiselect("Select Position(s)", options=pos_options, key="global_position_filter")

max_mins = int(df_p['time'].max()) if 'time' in df_p.columns and not df_p.empty else 3800
minutes_filter = st.sidebar.slider("Minimum Minutes Played", 0, max_mins, value=0, step=90, key="global_mins_filter")

def render_dashboard(df_p, df_t, season_title_label, season_key):
    st.header(f"📅 {season_title_label} Season Overview")
    
    if df_p.empty:
        st.warning("Data not available. Please check data processing pipeline.")
        return

    filtered_df = df_p.copy()
    
    if selected_team:
        filtered_df = filtered_df[filtered_df['team_title'].isin(selected_team)]
    if search_player.strip() and 'player_name' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['player_name'].str.contains(search_player.strip(), case=False, na=False)]
    if selected_positions and 'position_cat' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['position_cat'].isin(selected_positions)]
    if 'time' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['time'] >= minutes_filter]

    st.markdown("---")

    # SECTION 1: TOP PERFORMERS
    kpi_head1, kpi_head2 = st.columns([3, 1])
    with kpi_head1:
        st.subheader("📊 Top Performers")
    with kpi_head2:
        kpi_penalties = st.toggle("Include Penalties", value=True, key=f"kpi_toggle_{season_key}")

    kpi_goal_col = 'goals' if kpi_penalties else 'npg'
    kpi_xg_col = 'xG' if kpi_penalties else 'npxG'
    kpi_over_col = 'xg_overperformance' if kpi_penalties else 'npxg_overperformance'

    col1, col2, col3 = st.columns(3)
    with col1:
        top_scorer = filtered_df.loc[filtered_df[kpi_goal_col].idxmax()] if not filtered_df.empty and kpi_goal_col in filtered_df.columns else None
        st.metric("Top Scorer", f"{top_scorer['player_name']}" if top_scorer is not None else "N/A", f"{top_scorer[kpi_goal_col]} goals" if top_scorer is not None else "")
    with col2:
        top_xg = filtered_df.loc[filtered_df[kpi_xg_col].idxmax()] if not filtered_df.empty and kpi_xg_col in filtered_df.columns else None
        st.metric("Highest xG", f"{top_xg['player_name']}" if top_xg is not None else "N/A", f"{round(top_xg[kpi_xg_col], 1)} xG" if top_xg is not None else "")
    with col3:
        top_over = filtered_df.loc[filtered_df[kpi_over_col].idxmax()] if not filtered_df.empty and kpi_over_col in filtered_df.columns else None
        st.metric("Best Finishing Overperformance", f"{top_over['player_name']}" if top_over is not None else "N/A", f"+{round(top_over[kpi_over_col], 1)}" if top_over is not None else "")

    st.markdown("---")

    # SECTION 2: SCATTER PLOT
    st.subheader("🎯 Goals vs. Expected Goals (xG) per player")
    fig = px.scatter(
        filtered_df,
        x="xG",
        y="goals",
        color="team_title" if "team_title" in filtered_df.columns else None,
        hover_data=["player_name"]
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # SECTION 3: PLAYER DATA TABLE
    st.subheader("📋 Player Data Table")
    st.dataframe(filtered_df[['player_name', 'team_title', 'time', 'goals', 'xG', 'xg_overperformance']], width="stretch", hide_index=True)

    st.markdown("---")

    # SECTION 4: TEAM DATA TABLE
    if not df_t.empty:
        st.subheader("📋 Team Data Table")
        st.dataframe(df_t[['team_title', 'goals_for', 'xG', 'xg_per_90']], width="stretch", hide_index=True)

# Correctly call for 2026/27 season
render_dashboard(df_p, df_t, "2026/27", "2026")