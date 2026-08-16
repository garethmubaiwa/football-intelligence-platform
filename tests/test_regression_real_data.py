from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
GOLD_DB = ROOT / "data" / "gold" / "warehouse.duckdb"
BRONZE_ROOT = ROOT / "data" / "bronze"

pytestmark = pytest.mark.regression


@pytest.mark.skipif(
    not GOLD_DB.exists(),
    reason="Run the real-data pipeline first",
)
class TestRealDataRegression:
    def test_five_seasons_present(self):
        conn = duckdb.connect(str(GOLD_DB), read_only=True)
        result = conn.execute("SELECT COUNT(*) FROM dim_season").fetchone()
        count = result[0] if result is not None else 0
        conn.close()
        assert count == 5

    def test_no_orphaned_fact_rows(self):
        conn = duckdb.connect(str(GOLD_DB), read_only=True)
        result = conn.execute("""
            SELECT COUNT(*)
            FROM fact_player_season_stats f
            LEFT JOIN dim_player p
                ON f.player_key = p.player_key
            WHERE p.player_key IS NULL
        """).fetchone()
        orphans = result[0] if result is not None else 0
        conn.close()
        assert orphans == 0

    def test_all_fact_foreign_keys_resolve(self):
        conn = duckdb.connect(str(GOLD_DB), read_only=True)

        checks = {
            "player": """
                SELECT COUNT(*)
                FROM fact_player_season_stats f
                LEFT JOIN dim_player d ON f.player_key = d.player_key
                WHERE d.player_key IS NULL
            """,
            "team": """
                SELECT COUNT(*)
                FROM fact_player_season_stats f
                LEFT JOIN dim_team d ON f.team_key = d.team_key
                WHERE d.team_key IS NULL
            """,
            "season": """
                SELECT COUNT(*)
                FROM fact_player_season_stats f
                LEFT JOIN dim_season d ON f.season_key = d.season_key
                WHERE d.season_key IS NULL
            """,
            "position": """
                SELECT COUNT(*)
                FROM fact_player_season_stats f
                LEFT JOIN dim_position d ON f.position_key = d.position_key
                WHERE d.position_key IS NULL
            """,
        }

        results = {}
        for name, query in checks.items():
            row = conn.execute(query).fetchone()
            results[name] = row[0] if row is not None else 0
        conn.close()

        assert results == {
            "player": 0,
            "team": 0,
            "season": 0,
            "position": 0,
        }

    def test_team_transfer_boundary(self):
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

    def test_known_xg_schema_evolution(self):
        if not BRONZE_ROOT.exists():
            pytest.skip("Bronze data not available")

        from football_platform import silver

        clean_old, _ = silver.load_and_clean_season(
            "2019-20",
            BRONZE_ROOT,
        )
        clean_new, _ = silver.load_and_clean_season(
            "2023-24",
            BRONZE_ROOT,
        )

        assert clean_old["expected_goals"].isna().all()
        assert clean_old["expected_assists"].isna().all()
        assert clean_new["expected_goals"].notna().any()
        assert clean_new["expected_assists"].notna().any()
