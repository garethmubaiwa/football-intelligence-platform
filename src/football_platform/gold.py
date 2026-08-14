"""
Gold layer: star schema warehouse built from 5 seasons of real Premier League data.
    dim_team is keyed by TEAM NAME (the canonical, stable entity) precisely because raw team `id` is reassigned every season.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


def build_gold(silver_root: Path, gold_db_path: Path) -> dict:
    df = pd.read_parquet(silver_root / "player_season_stats.parquet")

    conn = duckdb.connect(str(gold_db_path))
    conn.execute("DROP TABLE IF EXISTS fact_player_season_stats")
    conn.execute("DROP TABLE IF EXISTS dim_player")
    conn.execute("DROP TABLE IF EXISTS dim_team")
    conn.execute("DROP TABLE IF EXISTS dim_season")
    conn.execute("DROP TABLE IF EXISTS dim_position")

    # ---- dim_position ----
    dim_position = pd.DataFrame(
        [(1, "GK", "Goalkeeper"), (2, "DEF", "Defender"),
         (3, "MID", "Midfielder"), (4, "FWD", "Forward")],
        columns=["position_key", "position_code", "position_name"],
    )
    conn.execute("CREATE TABLE dim_position AS SELECT * FROM dim_position")

    # dim_season: keyed by SEASON (canonical), not the season-relative id
    seasons = sorted(df["season"].unique())
    dim_season = pd.DataFrame({
        "season_key": range(1, len(seasons) + 1),
        "season": seasons,
        "start_year": [int(s[:4]) for s in seasons],
    })
    conn.execute("CREATE TABLE dim_season AS SELECT * FROM dim_season")

    # dim_team: one row per unique team name (canonical, stable entity)
    team_names = sorted(df["team_name"].unique())
    dim_team = pd.DataFrame({
        "team_key": range(1, len(team_names) + 1),
        "team_name": team_names,
    })
    conn.execute("CREATE TABLE dim_team AS SELECT * FROM dim_team")

    # dim_player: one row per unique player code, latest known name
    player_names = (
        df.sort_values("season")
        .groupby("code")
        .agg(web_name=("web_name", "last"), first_name=("first_name", "last"),
             second_name=("second_name", "last"))
        .reset_index()
    )
    player_names["player_key"] = range(1, len(player_names) + 1)
    dim_player = player_names[["player_key", "code", "web_name", "first_name", "second_name"]]
    conn.execute("CREATE TABLE dim_player AS SELECT * FROM dim_player")

    # fact_player_season_stats: fact table with foreign keys to all dims, plus all raw stats
    fact = df.merge(dim_player[["code", "player_key"]], on="code", how="left")
    fact = fact.merge(dim_team, on="team_name", how="left")
    fact = fact.merge(dim_season[["season", "season_key"]], on="season", how="left")
    fact = fact.merge(
        dim_position.rename(columns={"position_code": "position"})[["position", "position_key"]],
        on="position", how="left",
    )

    fact_cols = [
        "player_key", "team_key", "season_key", "position_key",
        "minutes", "starts", "goals_scored", "assists", "clean_sheets",
        "goals_conceded", "own_goals", "yellow_cards", "red_cards", "saves",
        "penalties_missed", "penalties_saved", "bonus", "bps",
        "influence", "creativity", "threat", "ict_index",
        "now_cost", "selected_by_percent", "total_points", "points_per_game",
        "expected_goals", "expected_assists", "expected_goal_involvements",
    ]
    fact_table = fact[fact_cols].reset_index(drop=True)
    fact_table.insert(0, "fact_id", range(1, len(fact_table) + 1))
    conn.execute("CREATE TABLE fact_player_season_stats AS SELECT * FROM fact_table")

    # report counts of rows in each table, and orphaned fact rows (no matching player)
    orphans = conn.execute("""
        SELECT COUNT(*) FROM fact_player_season_stats f
        LEFT JOIN dim_player p ON f.player_key = p.player_key
        WHERE p.player_key IS NULL
    """).fetchone()[0]

    counts = {
        "dim_player_rows": len(dim_player),
        "dim_team_rows": len(dim_team),
        "dim_season_rows": len(dim_season),
        "fact_rows": len(fact_table),
        "orphaned_fact_rows": orphans,
    }
    conn.close()
    return counts
