from __future__ import annotations

import pytest

from pathlib import Path

import duckdb


@pytest.mark.integration
def test_end_to_end_pipeline(
    synthetic_bronze_root,
    tmp_path: Path,
    modules,
):
    bronze = modules["bronze"]
    silver = modules["silver"]
    gold = modules["gold"]
    features = modules["features"]
    ml = modules["ml"]

    raw_root = tmp_path / "raw"
    bronze_root = tmp_path / "bronze"
    silver_root = tmp_path / "silver"
    gold_db = tmp_path / "warehouse.duckdb"

    # Copy synthetic Bronze data into the raw layout expected by ingestion.
    for season in ("2019-20", "2023-24"):
        source = synthetic_bronze_root / season
        destination = raw_root / season
        destination.mkdir(parents=True)
        for filename in ("players_raw.csv", "teams.csv"):
            (destination / filename).write_bytes(
                (source / filename).read_bytes()
            )

    # The production ingest_all_seasons() uses the five configured seasons,
    # so populate all five source partitions before invoking it.
    for season in ("2020-21", "2021-22", "2022-23"):
        source = synthetic_bronze_root / "2023-24"
        destination = raw_root / season
        destination.mkdir(parents=True)
        for filename in ("players_raw.csv", "teams.csv"):
            (destination / filename).write_bytes(
                (source / filename).read_bytes()
            )

    manifests = bronze.ingest_all_seasons(
        raw_root,
        bronze_root,
    )

    assert len(manifests) == 5

    metrics = silver.build_silver(
        bronze_root,
        silver_root,
        ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"],
    )

    assert metrics["seasons_processed"] == 5
    assert metrics["total_clean_rows"] > 0

    gold_metrics = gold.build_gold(
        silver_root,
        gold_db,
    )

    assert gold_metrics["fact_rows"] == metrics["total_clean_rows"]
    assert gold_metrics["orphaned_fact_rows"] == 0

    features = features.build_player_season_features(
        gold_db,
    )

    assert len(features) == metrics["total_clean_rows"]

    clusters = ml.cluster_playing_styles(
        features,
        season="2023-24",
        n_clusters=3,
    )

    assert len(clusters) > 0
    assert "cluster" in clusters.columns

    hidden_gems = ml.detect_value_outliers(
        features,
        season="2023-24",
        top_n=10,
    )

    assert len(hidden_gems) > 0
    assert "discovery_score" in hidden_gems.columns

    conn = duckdb.connect(str(gold_db), read_only=True)
    try:
        row = conn.execute("""
            SELECT COUNT(*)
            FROM fact_player_season_stats f
            LEFT JOIN dim_player p ON f.player_key = p.player_key
            WHERE p.player_key IS NULL
        """).fetchone()
        orphan_count = row[0] if row is not None else 0
    finally:
        conn.close()

    assert orphan_count == 0


@pytest.mark.integration
def test_gold_rebuild_is_idempotent(
    synthetic_bronze_root,
    tmp_path: Path,
    modules,
):
    silver = modules["silver"]
    gold = modules["gold"]

    silver_root = tmp_path / "silver"
    gold_db = tmp_path / "warehouse.duckdb"

    silver.build_silver(
        synthetic_bronze_root,
        silver_root,
        ["2019-20", "2023-24"],
    )

    first = gold.build_gold(silver_root, gold_db)
    second = gold.build_gold(silver_root, gold_db)

    assert first == second
