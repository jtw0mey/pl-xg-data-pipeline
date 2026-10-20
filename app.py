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

# Custom CSS for Tab styling
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
st.markdown("Interactive goals vs. xG metrics extracted from Understat and powered by **DuckDB & dbt**, built by Jack Twomey.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def map_position_category(pos_str):
    if not pos_str or pd.isna(pos_str):
        return "Unknown"
    pos = str(pos_str).upper()
    if 'GK' in pos: return "Goalkeeper"
    elif 'F' in pos: return "Forward"
    elif 'M' in pos: return "Midfielder"
    elif 'D' in pos: return "Defender"
    return "Other"

@st.cache_data
def load_all_data():
    db_path = os.path.join(BASE_DIR, 'dbt_transforms', 'dev.duckdb')
    if not os.path.exists(db_path):
        db_path = os.path.join(BASE_DIR, 'dev.duckdb')

    conn = duckdb.connect(db_path, read_only=True)
    
    # Query dbt summary table specifically for current 2026 season
    try:
        df_players = conn.execute("""
            SELECT * 
            FROM fct_player_xg_summary 
            WHERE CAST(season AS VARCHAR) = '2026'
        """).df()
    except Exception:
        df_players = conn.execute("SELECT * FROM fct_player_xg_summary").df()

    conn.close()

    # Rename dbt fields to match dashboard expectations
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

    if 'position' in df_players.columns:
        df_players['position_cat'] = df_players['position'].apply(map_position_category)
    else:
        df_players['position_cat'] = "Forward"

    for col in ['xG', 'npxG']:
        if col in df_players.columns:
            df_players[col] = df_players[col].round(1)

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

    # Calculate team aggregations dynamically from player data
    if not df_players.empty and 'team_title' in df_players.columns:
        df_teams = df_players.groupby('team_title').agg(
            goals_for=('goals', 'sum'),
            xG=('xG', 'sum'),
            np_goals_for=('npg', 'sum'),
            npxG=('npxG', 'sum'),
            max_mins=('time', 'max')
        ).reset_index()
        
        # Determine games played based on max individual minutes played per team
        df_teams['matches'] = df_teams['max_mins'].apply(lambda m: max(1, round(m / 90)))
        
        df_teams['goals_against'] = 0
        df_teams['xGA'] = 0.0
        df_teams['np_goals_against'] = 0
        df_teams['npxGA'] = 0.0
        df_teams['xg_per_90'] = df_teams.apply(lambda r: round(r['xG'] / r['matches'], 1) if r['matches'] > 0 else 0.0, axis=1)
        df_teams['xga_per_90'] = 0.0
        df_teams['npxg_per_90'] = df_teams.apply(lambda r: round(r['npxG'] / r['matches'], 1) if r['matches'] > 0 else 0.0, axis=1)
        df_teams['npxga_per_90'] = 0.0
    else:
        df_teams = pd.DataFrame()

    return df_players, df_teams

df_p, df_t = load_all_data()

# --- RESET FILTERS CALLBACK ---
def reset_filters():
    st.session_state["global_team_filter"] = []
    st.session_state["global_player_search"] = ""
    st.session_state["global_position_filter"] = []
    st.session_state["global_mins_filter"] = 0

# --- UNIFIED SIDEBAR FILTERS ---
st.sidebar.header("Filters")

combined_teams = sorted(list(df_p['team_title'].dropna().unique())) if 'team_title' in df_p.columns else []
selected_team = st.sidebar.multiselect("Select Team(s)", options=combined_teams, key="global_team_filter")

search_player = st.sidebar.text_input("Search Player Name", placeholder="e.g. Haaland", key="global_player_search")

pos_options = ["Forward", "Midfielder", "Defender", "Goalkeeper"]
selected_positions = st.sidebar.multiselect("Select Position(s)", options=pos_options, key="global_position_filter")

max_mins = int(df_p['time'].max()) if 'time' in df_p.columns and not df_p.empty else 3800
minutes_filter = st.sidebar.slider("Minimum Minutes Played", 0, max_mins, value=0, step=90, key="global_mins_filter")

st.sidebar.markdown("---")
st.sidebar.button("Reset Filters", on_click=reset_filters, use_container_width=True)

def render_dashboard(df_p, df_t, season_title_label, season_key):
    st.header(f"📅 {season_title_label} Season Overview")
    
    if df_p.empty:
        st.warning("Data not available from DuckDB warehouse.")
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

    # Default to top 33% of xG performers if no player is manually searched
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
        color="team_title" if "team_title" in plot_filtered_df.columns else None,
        title=f"Actual {plot_metric_label} vs Expected ({hover_xg_label})",
        labels={plot_xg_col: f"Expected ({hover_xg_label})", plot_goal_col: f"Actual {plot_metric_label}", "team_title": "Team"},
        custom_data=["player_name", "team_title"] if "team_title" in plot_filtered_df.columns else ["player_name"]
    )
    fig.update_layout(showlegend=False)
    
    hovertemplate_str = (
        "<b>%{customdata[0]}</b><br>"
        "%{customdata[1]}<br><br>" if "team_title" in plot_filtered_df.columns else "<b>%{customdata[0]}</b><br><br>"
    ) + f"{hover_goal_label} = %{{y}}<br>{hover_xg_label} = %{{x}}<extra></extra>"
    
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

    # Position column omitted as requested
    if table_penalties:
        ordered_cols = [
            ('player_name', 'Player'),
            ('team_title', 'Team'),
            ('time', 'Mins Played'),
            ('goals', 'Goals'),
            ('xG', 'xG'),
            ('xg_per_90', 'xG Per 90'),
            ('xg_overperformance', 'xG Overperformance')
        ]
        sort_col_raw = 'goals'
    else:
        ordered_cols = [
            ('player_name', 'Player'),
            ('team_title', 'Team'),
            ('time', 'Mins Played'),
            ('npg', 'Non-Penalty Goals'),
            ('npxG', 'Non-Penalty xG'),
            ('npxg_per_90', 'Non-Penalty xG Per 90'),
            ('npxg_overperformance', 'Non-Penalty xG Overperformance')
        ]
        sort_col_raw = 'npg'
    
    existing_raw_cols = [raw for raw, clean in ordered_cols if raw in table_filtered_df.columns]
    rename_dict = {raw: clean for raw, clean in ordered_cols if raw in table_filtered_df.columns}
    
    table_df = table_filtered_df[existing_raw_cols].copy().rename(columns=rename_dict)
    sort_by_col = rename_dict.get(sort_col_raw, 'Player')
    
    st.dataframe(
        table_df.sort_values(by=sort_by_col, ascending=False),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # --- SECTION 4: TEAM DATA TABLE ---
    team_head1, team_head2 = st.columns([3, 1])
    with team_head1:
        st.subheader("📋 Team Data Table")
    with team_head2:
        team_penalties = st.toggle("Include Penalties", value=True, key=f"team_toggle_{season_key}")

    all_teams_in_season = sorted(df_t['team_title'].dropna().unique()) if not df_t.empty else []
    selected_team_table = st.multiselect(
        "Search or Select Specific Teams to Compare",
        options=all_teams_in_season,
        default=[],
        key=f"team_table_compare_{season_key}",
        placeholder="Type team names to isolate in table..."
    )

    team_filtered_df = df_t.copy() if not df_t.empty else pd.DataFrame()
    if selected_team_table:
        team_filtered_df = team_filtered_df[team_filtered_df['team_title'].isin(selected_team_table)]

    if team_penalties:
        team_cols = [
            ('team_title', 'Team'),
            ('matches', 'Games'),
            ('goals_for', 'Goals For (G)'),
            ('goals_against', 'Goals Against (GA)'),
            ('xG', 'xG'),
            ('xg_per_90', 'xG Per 90'),
            ('xGA', 'xGA'),
            ('xga_per_90', 'xGA Per 90')
        ]
        sort_team_col = 'goals_for'
    else:
        team_cols = [
            ('team_title', 'Team'),
            ('matches', 'Games'),
            ('np_goals_for', 'Non-Penalty Goals For (G)'),
            ('np_goals_against', 'Non-Penalty Goals Against (GA)'),
            ('npxG', 'Non-Penalty xG'),
            ('npxg_per_90', 'Non-Penalty xG Per 90'),
            ('npxGA', 'Non-Penalty xGA'),
            ('npxga_per_90', 'Non-Penalty xGA Per 90')
        ]
        sort_team_col = 'np_goals_for'

    existing_t_cols = [raw for raw, clean in team_cols if raw in team_filtered_df.columns]
    rename_t_dict = {raw: clean for raw, clean in team_cols if raw in team_filtered_df.columns}

    display_team_df = team_filtered_df[existing_t_cols].copy().rename(columns=rename_t_dict) if not team_filtered_df.empty else pd.DataFrame()
    sort_team_by_clean = rename_t_dict.get(sort_team_col, 'Team')

    if not display_team_df.empty:
        st.dataframe(
            display_team_df.sort_values(by=sort_team_by_clean, ascending=False),
            use_container_width=True,
            hide_index=True
        )

# Render 2026/27 season
render_dashboard(df_p, df_t, "2026/27", "2026")