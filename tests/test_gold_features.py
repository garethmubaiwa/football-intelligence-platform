from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


def test_gold_build_creates_expected_star_schema(
    synthetic_bronze_root,
    tmp_path: Path,
    modules,
):
    silver = modules["silver"]
    gold = modules["gold"]

    silver_root = tmp_path / "silver"
    gold_db = tmp_path / "warehouse.duckdb"

    gold_seasons = ["2019-20", "2023-24"]
    silver.build_silver(
        synthetic_bronze_root,
        silver_root,
        gold_seasons,
    )
    counts = gold.build_gold(
        silver_root,
        gold_db,
    )

    assert counts["orphaned_fact_rows"] == 0
    assert counts["fact_rows"] > 0
    assert counts["dim_player_rows"] > 0
    assert counts["dim_team_rows"] > 0
    assert counts["dim_season_rows"] == 2
    assert counts["dim_position_rows"] == 4

    conn = duckdb.connect(str(gold_db), read_only=True)
    tables = {
        row[0]
        for row in conn.execute(
            "SHOW TABLES"
        ).fetchall()
    }
    conn.close()

    assert {
        "dim_player",
        "dim_team",
        "dim_season",
        "dim_position",
        "fact_player_season_stats",
    }.issubset(tables)


def test_feature_engineering_creates_required_features(
    synthetic_bronze_root,
    tmp_path: Path,
    modules,
):
    silver = modules["silver"]
    gold = modules["gold"]
    features = modules["features"]

    silver_root = tmp_path / "silver"
    gold_db = tmp_path / "warehouse.duckdb"

    silver.build_silver(
        synthetic_bronze_root,
        silver_root,
        ["2019-20", "2023-24"],
    )
    gold.build_gold(silver_root, gold_db)

    features = features.build_player_season_features(gold_db)

    required = {
        "goals_per_90",
        "assists_per_90",
        "clean_sheets_per_90",
        "goals_conceded_per_90",
        "saves_per_90",
        "bps_per_90",
        "influence_per_90",
        "creativity_per_90",
        "threat_per_90",
        "cost_millions",
        "points_per_million",
        "goals_minus_xg_per_90",
        "assists_minus_xa_per_90",
        "points_per_game_yoy_change",
        "points_consistency_std",
        "goals_per_90_trend_slope",
        "seasons_of_history",
    }

    assert required.issubset(features.columns)
    assert len(features) > 0


def test_feature_engineering_per_90_calculation(
    synthetic_bronze_root,
    tmp_path: Path,
    modules,
):
    silver = modules["silver"]
    gold = modules["gold"]
    features = modules["features"]

    silver_root = tmp_path / "silver"
    gold_db = tmp_path / "warehouse.duckdb"

    silver.build_silver(
        synthetic_bronze_root,
        silver_root,
        ["2023-24"],
    )
    gold.build_gold(silver_root, gold_db)

    features = features.build_player_season_features(gold_db)
    row = features.iloc[0]

    expected = row["goals_scored"] / row["minutes"] * 90
    assert row["goals_per_90"] == expected


def test_feature_engineering_preserves_missing_xg_as_missing(
    synthetic_bronze_root,
    tmp_path: Path,
    modules,
):
    silver = modules["silver"]
    gold = modules["gold"]
    features = modules["features"]

    silver_root = tmp_path / "silver"
    gold_db = tmp_path / "warehouse.duckdb"

    silver.build_silver(
        synthetic_bronze_root,
        silver_root,
        ["2019-20"],
    )
    gold.build_gold(silver_root, gold_db)

    features = features.build_player_season_features(gold_db)

    assert features["has_xg_data"].eq(False).all()
    assert features["goals_minus_xg_per_90"].isna().all()


def test_feature_engineering_time_order_is_correct(
    synthetic_bronze_root,
    tmp_path: Path,
    modules,
):
    silver = modules["silver"]
    gold = modules["gold"]
    features = modules["features"]

    silver_root = tmp_path / "silver"
    gold_db = tmp_path / "warehouse.duckdb"

    silver.build_silver(
        synthetic_bronze_root,
        silver_root,
        ["2019-20", "2023-24"],
    )
    gold.build_gold(silver_root, gold_db)

    features = features.build_player_season_features(gold_db)

    history = features.groupby("code")["seasons_of_history"].apply(list)
    assert all(values == sorted(values) for values in history)
    assert all(values[-1] == len(values) for values in history)
