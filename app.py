import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import os
import html

st.set_page_config(
    page_title="Premier League xG Dashboard",
    page_icon="⚽",
    layout="wide"
)

st.markdown("""
<style>
    button[data-baseweb="tab"] {
        font-size: 18px !important;
        font-weight: 700 !important;
        padding: 12px 24px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚽ Premier League xG Analytics Engine")
st.markdown("Interactive goals vs. xG metrics extracted from Understat and powered by **DuckDB**, built by Jack Twomey.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def load_season_data(season_year):
    conn = duckdb.connect(database=':memory:')
    
    # Load Players
    p_path = os.path.join(BASE_DIR, 'data', 'processed', f'epl_player_xg_{season_year}_clean.csv')
    if not os.path.exists(p_path):
        st.error(f"Data file not found at: {p_path}")
        return pd.DataFrame(), pd.DataFrame()
        
    df_players = conn.execute(f"SELECT * FROM '{p_path}'").df()
    
    # Clean HTML entities in player names and team titles
    if 'player_name' in df_players.columns:
        df_players['player_name'] = df_players['player_name'].astype(str).apply(html.unescape)
    
    # Standardize team column name
    team_col = next((c for c in ['team_title', 'team_name', 'team', 'teams'] if c in df_players.columns), None)
    if team_col:
        df_players['team_title'] = df_players[team_col].astype(str).apply(
            lambda x: html.unescape(x).split(',')[-1].strip() if x else x
        )
        
    for col in ['xG', 'npxG', 'xg_overperformance']:
        if col in df_players.columns:
            df_players[col] = df_players[col].round(1)
    if 'time' in df_players.columns:
        if 'npxG' in df_players.columns:
            df_players['npxg_per_90'] = df_players.apply(
                lambda row: round((row['npxG'] / row['time']) * 90, 1) if row['time'] > 0 else 0.0, 
                axis=1
            )
        if 'npg' in df_players.columns and 'npxG' in df_players.columns:
            df_players['npxg_overperformance'] = df_players.apply(
                lambda row: round(row['npg'] - row['npxG'], 1), axis=1
            )
    if 'xg_per_90' in df_players.columns:
        df_players['xg_per_90'] = df_players['xg_per_90'].round(1)

    # Load Teams
    t_path = os.path.join(BASE_DIR, 'data', 'processed', f'epl_teams_xg_{season_year}_clean.csv')
    df_teams = conn.execute(f"SELECT * FROM '{t_path}'").df() if os.path.exists(t_path) else pd.DataFrame()

    if not df_teams.empty:
        t_team_col = next((c for c in ['team_title', 'team_name', 'team', 'teams'] if c in df_teams.columns), None)
        if t_team_col:
            df_teams['team_title'] = df_teams[t_team_col].astype(str).apply(html.unescape)
            
        if 'matches' in df_teams.columns:
            df_teams['xg_per_90'] = df_teams.apply(
                lambda r: round(r['xG'] / r['matches'], 1) if r['matches'] > 0 else 0.0, axis=1
            )
            df_teams['npxg_per_90'] = df_teams.apply(
                lambda r: round(r['npxG'] / r['matches'], 1) if r['matches'] > 0 else 0.0, axis=1
            )
            df_teams['xga_per_90'] = df_teams.apply(
                lambda r: round(r['xGA'] / r['matches'], 1) if r['matches'] > 0 else 0.0, axis=1
            )
            df_teams['npxga_per_90'] = df_teams.apply(
                lambda r: round(r['npxGA'] / r['matches'], 1) if r['matches'] > 0 else 0.0, axis=1
            )

    return df_players, df_teams

df_2026_p, df_2026_t = load_season_data(2026)
df_2025_p, df_2025_t = load_season_data(2025)

# --- RESET FILTERS CALLBACK ---
def reset_filters():
    st.session_state["global_team_filter"] = []
    st.session_state["global_player_search"] = ""
    st.session_state["global_position_filter"] = []
    st.session_state["global_mins_filter"] = 300

# --- UNIFIED SIDEBAR FILTERS ---
st.sidebar.header("Filters")

# 1. Team Filter
combined_teams = sorted(list(set(df_2026_p['team_title'].dropna().unique() if 'team_title' in df_2026_p else []).union(set(df_2025_p['team_title'].dropna().unique() if 'team_title' in df_2025_p else []))))
selected_team = st.sidebar.multiselect("Select Team(s)", options=combined_teams, key="global_team_filter")

# 2. Player Name Search
search_player = st.sidebar.text_input("Search Player Name", placeholder="e.g. Haaland", key="global_player_search")

# 3. Position Filter
combined_positions = sorted(list(set(df_2026_p['position'].dropna().unique() if 'position' in df_2026_p else []).union(set(df_2025_p['position'].dropna().unique() if 'position' in df_2025_p else []))))
selected_positions = st.sidebar.multiselect("Select Position(s)", options=combined_positions, key="global_position_filter")

# 4. Minimum Minutes Slider
max_mins_combined = max(int(df_2026_p['time'].max() if 'time' in df_2026_p.columns else 900), int(df_2025_p['time'].max() if 'time' in df_2025_p.columns else 900))
minutes_filter = st.sidebar.slider("Minimum Minutes Played", 0, max_mins_combined, value=300, step=90, key="global_mins_filter")

# 5. Reset Filters Button at the Bottom
st.sidebar.markdown("---")
st.sidebar.button("Reset Filters", on_click=reset_filters, use_container_width=True)


def render_dashboard(df_p, df_t, season_title_label, season_key):
    st.header(f"📅 {season_title_label} Season Overview")
    
    if df_p.empty:
        st.warning("Data not available for this season.")
        return

    filtered_df = df_p.copy()
    
    # Apply Sidebar Filters
    if selected_team:
        filtered_df = filtered_df[filtered_df['team_title'].isin(selected_team)]
    if search_player.strip() and 'player_name' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['player_name'].str.contains(search_player.strip(), case=False, na=False)]
    if selected_positions and 'position' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['position'].isin(selected_positions)]
    if 'time' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['time'] >= minutes_filter]

    st.markdown("---")

    # --- SECTION 1: TOP PERFORMERS ---
    kpi_head1, kpi_head2 = st.columns([3, 1])
    with kpi_head1:
        st.subheader("📊 Top Performers")
    with kpi_head2:
        kpi_penalties = st.toggle("Include Penalties", value=True, key=f"kpi_toggle_{season_key}")

    kpi_goal_col = 'goals' if kpi_penalties else 'npg'
    kpi_xg_col = 'xG' if kpi_penalties else 'npxG'
    kpi_over_col = 'xg_overperformance' if kpi_penalties else 'npxg_overperformance'
    kpi_metric_label = "Goals" if kpi_penalties else "Non-Penalty Goals"
    kpi_xg_label = "xG" if kpi_penalties else "npxG"

    col1, col2, col3 = st.columns(3)
    with col1:
        top_scorer = filtered_df.loc[filtered_df[kpi_goal_col].idxmax()] if not filtered_df.empty and kpi_goal_col in filtered_df.columns else None
        st.metric(f"Top Scorer ({kpi_metric_label})", f"{top_scorer['player_name']}" if top_scorer is not None else "N/A", f"{top_scorer[kpi_goal_col]} goals" if top_scorer is not None else "")
    with col2:
        top_xg = filtered_df.loc[filtered_df[kpi_xg_col].idxmax()] if not filtered_df.empty and kpi_xg_col in filtered_df.columns else None
        st.metric(f"Highest {kpi_xg_label}", f"{top_xg['player_name']}" if top_xg is not None else "N/A", f"{round(top_xg[kpi_xg_col], 1)} {kpi_xg_label}" if top_xg is not None else "")
    with col3:
        top_over = filtered_df.loc[filtered_df[kpi_over_col].idxmax()] if not filtered_df.empty and kpi_over_col in filtered_df.columns else None
        st.metric("Best Finishing Overperformance", f"{top_over['player_name']}" if top_over is not None else "N/A", f"+{round(top_over[kpi_over_col], 1)}" if top_over is not None else "")

    st.markdown("---")

    # --- SECTION 2: SCATTER PLOT ---
    plot_head1, plot_head2 = st.columns([3, 1])
    with plot_head2:
        plot_penalties = st.toggle("Include Penalties", value=True, key=f"plot_toggle_{season_key}")

    plot_goal_col = 'goals' if plot_penalties else 'npg'
    plot