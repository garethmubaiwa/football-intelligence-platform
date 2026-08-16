from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.smoke
def test_all_pipeline_modules_import(modules):
    assert set(modules) == {"bronze","silver","gold","features","ml",}


@pytest.mark.smoke
def test_pipeline_smoke(synthetic_bronze_root,tmp_path: Path,modules,):
    silver = modules["silver"]
    gold = modules["gold"]
    features = modules["features"]
    ml = modules["ml"]
    silver_root = tmp_path / "silver"
    gold_db = tmp_path / "warehouse.duckdb"

    silver.build_silver(synthetic_bronze_root,silver_root,["2019-20", "2023-24"],)
    gold.build_gold(silver_root, gold_db)
    features = features.build_player_season_features(gold_db)

    clusters = ml.cluster_playing_styles(features,season="2023-24",n_clusters=3,)
    outliers = ml.detect_value_outliers(features,season="2023-24",top_n=5,)

    assert len(features) > 0
    assert len(clusters) > 0
    assert len(outliers) > 0
