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
    
    # Primary file path
    p_path = os.path.join(BASE_DIR, 'data', 'processed', f'epl_player_xg_{season_year}_clean.csv')
    
    # Fallback search if specific season file isn't found
    if not os.path.exists(p_path):
        fallback_path = os.path.join(BASE_DIR, 'data', 'processed', 'player_stats.csv')
        if os.path.exists(fallback_path):
            p_path = fallback_path
        else:
            for root, dirs, files in os.walk(BASE_DIR):
                for file in files:
                    if file.endswith('.csv') and ('player' in file.lower() or 'xg' in file.lower()):
                        p_path = os.path.join(root, file)
                        break

    if not os.path.exists(p_path):
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
    if not os.path.exists(t_path):
        t_fallback = os.path.join(BASE_DIR, 'data', 'processed', 'team_stats.csv')
        if os.path.exists(t_fallback):
            t_path = t_fallback

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
max_mins_2026 = int(df_2026_p['time'].max()) if 'time' in df_2026_p.columns and not df_2026_p.empty else 900
max_mins_2025 = int(df_2025_p['time'].max()) if 'time' in df_2025_p.columns and not df_2025_p.empty else 900
max_mins_combined = max(max_mins_2026, max_mins_2025)

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
    plot_xg_col = 'xG' if plot_penalties else 'npxG'
    plot_metric_label = "Goals" if plot_penalties else "Non-Penalty Goals"
    plot_xg_label = "Expected Goals (xG)" if plot_penalties else "Non-Penalty Expected Goals (npxG)"
    hover_goal_label = "Actual goals" if plot_penalties else "Non-penalty goals"
    hover_xg_label = "xG" if plot_penalties else "npxG"

    with plot_head1:
        st.subheader(f"🎯 {plot_metric_label} vs. {plot_xg_label} per player")

    all_players_in_season = sorted(df_p['player_name'].dropna().unique()) if 'player_name' in df_p else []
    selected_plot_players = st.multiselect(
        "Search or Select Specific Players to Highlight on Chart",
        options=all_players_in_season,
        default=[],
        key=f"plot_player_compare_{season_key}",
        placeholder="Type player names to isolate on graph..."
    )

    plot_filtered_df = filtered_df.copy()

    if selected_plot_players:
        plot_filtered_df = df_p[df_p['player_name'].isin(selected_plot_players)]
    else:
        if not plot_filtered_df.empty and plot_xg_col in plot_filtered_df.columns:
            top_33_cutoff = plot_filtered_df[plot_xg_col].quantile(0.67)
            plot_filtered_df = plot_filtered_df[plot_filtered_df[plot_xg_col] >= top_33_cutoff]

    fig = px.scatter(
        plot_filtered_df,
        x=plot_xg_col,
        y=plot_goal_col,
        size="time" if "time" in plot_filtered_df.columns else None,
        color="team_title",
        title=f"Actual {plot_metric_label} vs Expected ({hover_xg_label})",
        labels={plot_xg_col: f"Expected ({hover_xg_label})", plot_goal_col: f"Actual {plot_metric_label}", "team_title": "Team"},
        custom_data=["player_name", "team_title"]
    )
    fig.update_layout(showlegend=False)
    
    hovertemplate_str = (
        "<b>%{customdata[0]}</b><br>"
        "%{customdata[1]}<br><br>"
        f"{hover_goal_label} = %{{y}}<br>"
        f"{hover_xg_label} = %{{x}}<extra></extra>"
    )
    fig.update_traces(hovertemplate=hovertemplate_str)

    if plot_xg_col in plot_filtered_df.columns and not plot_filtered_df.empty:
        max_val = plot_filtered_df[plot_xg_col].max()
        fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                      line=dict(color="Gray", dash="dash"))
                      
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- SECTION 3: PLAYER DATA TABLE ---
    table_head1, table_head2 = st.columns([3, 1])
    with table_head1:
        st.subheader("📋 Player Data Table")
    with table_head2:
        table_penalties = st.toggle("Include Penalties", value=True, key=f"table_toggle_{season_key}")

    selected_players = st.multiselect(
        "Search or Select Specific Players to Compare",
        options=all_players_in_season,
        default=[],
        key=f"player_compare_{season_key}",
        placeholder="Type player names to isolate in table..."
    )

    table_filtered_df = filtered_df.copy()
    if selected_players:
        table_filtered_df = df_p[df_p['player_name'].isin(selected_players)]

    if table_penalties:
        ordered_cols = [
            ('player_name', 'Player'),
            ('team_title', 'Team'),
            ('games', 'Games'),
            ('time', 'Mins Played'),
            ('goals', 'Goals'),
            ('xG', 'xG'),
            ('xg_per_90', 'xG Per 90'),
            ('xg_overperformance', 'xG Overperformance')
        ]
        sort_col_raw