"""
Overall pipeline orchestration script. This script runs the entire ETL pipeline from raw data ingestion to feature engineering and ML analysis.
The pipeline consists of the following stages:
1. BRONZE: Ingest raw Premier League data for multiple seasons into the bronze layer
2. SILVER: Clean and normalize the data, handling schema evolution and team ID instability
3. GOLD: Build a star schema warehouse in DuckDB
4. FEATURES: Compute per-90 stats, value scores, and multi-season trends
5. ML: Perform playing-style clustering and hidden-talent detection for the 2023-24 season
"""

from __future__ import annotations

import json
from pathlib import Path

from football_platform import bronze, silver, gold, features, ml

SEASONS = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]
ROOT = Path(__file__).parent


def run() -> None:
    print("=" * 90)
    print("BRONZE: landing 5 real Premier League seasons")
    print("=" * 90)
    manifests = bronze.ingest_all_seasons(ROOT / "data" / "raw", ROOT / "data" / "bronze")
    for m in manifests:
        print(f"  {m['season']}: {m['files']}")

    print("\n" + "=" * 90)
    print("SILVER: cleaning, validating, handling real schema evolution")
    print("=" * 90)
    silver_result = silver.build_silver(ROOT / "data" / "bronze", ROOT / "data" / "silver", SEASONS)
    print(json.dumps(silver_result, indent=2))

    print("\n" + "=" * 90)
    print("GOLD: building star schema warehouse")
    print("=" * 90)
    gold_result = gold.build_gold(ROOT / "data" / "silver", ROOT / "data" / "gold" / "warehouse.duckdb")
    print(json.dumps(gold_result, indent=2))
    assert gold_result["orphaned_fact_rows"] == 0, "Referential integrity check failed!"

    print("\n" + "=" * 90)
    print("FEATURES: per-90 stats, value scores, multi-season trends")
    print("=" * 90)
    features_df = features.build_player_season_features(ROOT / "data" / "gold" / "warehouse.duckdb")
    features_df.to_parquet(ROOT / "data" / "gold" / "player_features.parquet", index=False)
    print(f"Built {len(features_df)} feature rows for {features_df['code'].nunique()} unique players")

    print("\n" + "=" * 90)
    print("ML: playing-style clustering + hidden-talent detection (2023-24)")
    print("=" * 90)
    clustered = ml.cluster_playing_styles(features_df, season="2023-24")
    clustered.to_csv(ROOT / "data" / "gold" / "player_style_clusters_2023-24.csv", index=False)
    print(f"Clustered {len(clustered[clustered['cluster'] >= 0])} players into style archetypes")

    outliers = ml.detect_value_outliers(features_df, season="2023-24")
    outliers.to_csv(ROOT / "data" / "gold" / "hidden_talent_2023-24.csv", index=False)
    print(f"\nTop 5 hidden talent / value outliers (2023-24):")
    print(outliers.head(5).to_string(index=False))

    print("\n" + "=" * 90)
    print("PIPELINE COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    run()
