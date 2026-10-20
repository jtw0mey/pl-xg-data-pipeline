SELECT
    season,
    player_id,
    player_name,
    team_name,
    SUM(minutes_played) AS total_minutes,
    SUM(goals) AS total_goals,
    ROUND(SUM(xg), 2) AS total_xg,
    SUM(non_penalty_goals) AS total_npg,
    ROUND(SUM(non_penalty_xg), 2) AS total_npxg,
    ROUND(SUM(goals) - SUM(xg), 2) AS xg_difference
FROM {{ ref('stg_understat_matches') }}
GROUP BY 1, 2, 3, 4