WITH raw_2025 AS (
    SELECT *, 2025 AS season FROM {{ ref('epl_player_xg_2025') }}
),
raw_2026 AS (
    SELECT *, 2026 AS season FROM {{ ref('epl_player_xg_2026') }}
),
combined_raw AS (
    SELECT * FROM raw_2025
    UNION ALL
    SELECT * FROM raw_2026
)

SELECT
    id AS player_id,
    player_name,
    team_title AS team_name,
    CAST(games AS INTEGER) AS games_played,
    CAST(goals AS INTEGER) AS goals,
    CAST("xG" AS FLOAT) AS xg,
    CAST(npg AS INTEGER) AS non_penalty_goals,
    CAST("npxG" AS FLOAT) AS non_penalty_xg,
    CAST(time AS INTEGER) AS minutes_played,
    season
FROM combined_raw
WHERE player_name IS NOT NULL
