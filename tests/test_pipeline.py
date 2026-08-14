"""Tests covering the real-data pipeline: schema evolution handling,
the team-ID stability fix, referential integrity, and feature correctness.
"""
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from football_platform import silver

ROOT = Path(__file__).parent.parent
GOLD_DB = ROOT / "data" / "gold" / "warehouse.duckdb"


@pytest.mark.skipif(not GOLD_DB.exists(), reason="Run run_pipeline.py first")
class TestWarehouseIntegrity:
    def test_no_orphaned_fact_rows(self):
        conn = duckdb.connect(str(GOLD_DB), read_only=True)
        orphans = conn.execute("""
            SELECT COUNT(*) FROM fact_player_season_stats f
            LEFT JOIN dim_player p ON f.player_key = p.player_key
            WHERE p.player_key IS NULL
        """).fetchone()[0]
        conn.close()
        assert orphans == 0

    def test_team_transfer_correctly_reflected(self):
        """Real, independently verifiable fact: Jack Grealish moved from
        Aston Villa to Man City in summer 2021 -- this MUST show correctly
        as the season boundary, proving the team-ID-instability fix works.
        """
        conn = duckdb.connect(str(GOLD_DB), read_only=True)
        rows = conn.execute("""
            SELECT s.season, t.team_name
            FROM fact_player_season_stats f
            JOIN dim_player p ON f.player_key = p.player_key
            JOIN dim_team t ON f.team_key = t.team_key
            JOIN dim_season s ON f.season_key = s.season_key
            WHERE p.web_name = 'Grealish'
            ORDER BY s.season
        """).fetchall()
        conn.close()
        by_season = dict(rows)
        assert by_season["2020-21"] == "Aston Villa"
        assert by_season["2021-22"] == "Man City"

    def test_five_seasons_present(self):
        conn = duckdb.connect(str(GOLD_DB), read_only=True)
        count = conn.execute("SELECT COUNT(*) FROM dim_season").fetchone()[0]
        conn.close()
        assert count == 5


class TestSilverSchemaEvolution:
    def test_missing_xg_columns_become_null_not_crash(self, tmp_path):
        """2019-20 has no expected_goals column at all -- must not crash,
        must produce explicit nulls.
        """
        bronze_root = ROOT / "data" / "bronze"
        clean, rejected = silver.load_and_clean_season("2019-20", bronze_root)
        assert clean["expected_goals"].isna().all()
        assert len(clean) > 0

    def test_2023_24_has_real_xg_values(self):
        bronze_root = ROOT / "data" / "bronze"
        clean, _ = silver.load_and_clean_season("2023-24", bronze_root)
        assert clean["expected_goals"].notna().any()
        assert (clean["expected_goals"] >= 0).all()
