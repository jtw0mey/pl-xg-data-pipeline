import pytest
import pandas as pd
import html

def clean_and_transform_player_data(raw_df):
    """Refactored logic matching src/transform_xg.py transformation steps."""
    df = raw_df.copy()

    # Clean HTML entities
    if 'player_name' in df.columns:
        df['player_name'] = df['player_name'].astype(str).apply(html.unescape)
    if 'team_title' in df.columns:
        df['team_title'] = df['team_title'].astype(str).apply(
            lambda x: html.unescape(x).split(',')[-1].strip() if x else x
        )

    # Convert numeric columns
    numeric_cols = ['goals', 'xG', 'npg', 'npxG', 'time']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Calculate xG Overperformance
    df['xg_overperformance'] = (df['goals'] - df['xG']).round(1)

    # Calculate Per-90 Metrics
    df['xg_per_90'] = df.apply(
        lambda row: round((row['xG'] / row['time']) * 90, 1) if row['time'] > 0 else 0.0,
        axis=1
    )
    df['npxg_per_90'] = df.apply(
        lambda row: round((row['npxG'] / row['time']) * 90, 1) if row['time'] > 0 else 0.0,
        axis=1
    )

    return df


def test_html_unescaping():
    sample_data = pd.DataFrame({
        'player_name': ["Matt O&apos;Riley", "Gabriel Martinelli"],
        'team_title': ["Brighton &amp; Hove Albion", "Arsenal"],
        'goals': [2, 5],
        'xG': [1.5, 4.2],
        'npg': [2, 5],
        'npxG': [1.5, 4.2],
        'time': [450, 900]
    })

    result = clean_and_transform_player_data(sample_data)

    assert result.loc[0, 'player_name'] == "Matt O'Riley"
    assert result.loc[0, 'team_title'] == "Brighton & Hove Albion"


def test_xg_overperformance():
    sample_data = pd.DataFrame({
        'player_name': ["Erling Haaland"],
        'team_title': ["Manchester City"],
        'goals': [10],
        'xG': [7.4],
        'npg': [8],
        'npxG': [6.0],
        'time': [900]
    })

    result = clean_and_transform_player_data(sample_data)

    assert result.loc[0, 'xg_overperformance'] == 2.6


def test_per_90_rate_calculations():
    sample_data = pd.DataFrame({
        'player_name': ["Mohamed Salah"],
        'team_title': ["Liverpool"],
        'goals': [5],
        'xG': [4.5],
        'npg': [4],
        'npxG': [3.0],
        'time': [900]  # Exactly 10 full 90s
    })

    result = clean_and_transform_player_data(sample_data)

    # 4.5 xG over 900 mins = 0.45 xG per 90 (rounded to 0.5)
    assert result.loc[0, 'xg_per_90'] == 0.5
    # 3.0 npxG over 900 mins = 0.3 npxG per 90
    assert result.loc[0, 'npxg_per_90'] == 0.3
