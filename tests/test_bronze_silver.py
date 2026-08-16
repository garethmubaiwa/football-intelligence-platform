from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


def test_bronze_ingest_copies_required_files(tmp_path: Path, modules):
    bronze = modules["bronze"]
    raw_root = tmp_path / "raw"
    bronze_root = tmp_path / "bronze"
    season_dir = raw_root / "2023-24"
    season_dir.mkdir(parents=True)

    (season_dir / "players_raw.csv").write_text("code,minutes\n1,1000\n")
    (season_dir / "teams.csv").write_text("id,name\n1,Test FC\n")

    manifest = bronze.ingest_season("2023-24", raw_root, bronze_root)

    assert (bronze_root / "2023-24" / "players_raw.csv").exists()
    assert (bronze_root / "2023-24" / "teams.csv").exists()
    assert manifest["season"] == "2023-24"
    assert set(manifest["files"]) == {"players_raw.csv", "teams.csv"}
    assert manifest["ingested_at_utc"]


def test_bronze_missing_file_fails_fast(tmp_path: Path, modules):
    bronze = modules["bronze"]
    raw_root = tmp_path / "raw"
    bronze_root = tmp_path / "bronze"
    season_dir = raw_root / "2023-24"
    season_dir.mkdir(parents=True)
    (season_dir / "players_raw.csv").write_text("code,minutes\n1,1000\n")

    with pytest.raises(FileNotFoundError):
        bronze.ingest_season("2023-24", raw_root, bronze_root)


def test_bronze_does_not_transform_raw_content(tmp_path: Path, modules):
    bronze = modules["bronze"]
    raw_root = tmp_path / "raw"
    bronze_root = tmp_path / "bronze"
    season_dir = raw_root / "2023-24"
    season_dir.mkdir(parents=True)

    players_text = "code,minutes,custom_raw_value\n1,1000,00123\n"
    (season_dir / "players_raw.csv").write_text(players_text)
    (season_dir / "teams.csv").write_text("id,name\n1,Test FC\n")

    bronze.ingest_season("2023-24", raw_root, bronze_root)

    copied = (bronze_root / "2023-24" / "players_raw.csv").read_text()
    assert copied == players_text


def test_silver_missing_xg_columns_become_null(synthetic_bronze_root, modules):
    silver = modules["silver"]
    clean, rejected = silver.load_and_clean_season(
        "2019-20",
        synthetic_bronze_root,
    )

    assert len(clean) > 0
    assert clean["expected_goals"].isna().all()
    assert clean["expected_assists"].isna().all()
    assert clean["expected_goal_involvements"].isna().all()


def test_silver_new_xg_columns_are_retained(synthetic_bronze_root, modules):
    silver = modules["silver"]
    clean, _ = silver.load_and_clean_season(
        "2023-24",
        synthetic_bronze_root,
    )

    assert clean["expected_goals"].notna().all()
    assert clean["expected_assists"].notna().all()
    assert (clean["expected_goals"] >= 0).all()


def test_silver_rejects_invalid_rows(tmp_path, modules):
    silver = modules["silver"]
    bronze_root = tmp_path / "bronze"
    season_dir = bronze_root / "2023-24"
    season_dir.mkdir(parents=True)

    players = pd.DataFrame(
        [
            {
                "code": 1, "web_name": "Valid", "first_name": "A", "second_name": "B",
                "element_type": 3, "team": 1, "minutes": 1000, "starts": 20,
                "goals_scored": 5, "assists": 5, "clean_sheets": 5,
                "goals_conceded": 5, "own_goals": 0, "yellow_cards": 0,
                "red_cards": 0, "saves": 0, "penalties_missed": 0,
                "penalties_saved": 0, "bonus": 5, "bps": 100,
                "influence": 50, "creativity": 50, "threat": 50,
                "ict_index": 8, "now_cost": 60, "selected_by_percent": 5,
                "total_points": 120, "points_per_game": 6,
            },
            {
                "code": 2, "web_name": "Invalid", "first_name": "C", "second_name": "D",
                "element_type": 99, "team": 1, "minutes": -5, "starts": 0,
                "goals_scored": 0, "assists": 0, "clean_sheets": 0,
                "goals_conceded": 0, "own_goals": 0, "yellow_cards": 0,
                "red_cards": 0, "saves": 0, "penalties_missed": 0,
                "penalties_saved": 0, "bonus": 0, "bps": 0,
                "influence": 0, "creativity": 0, "threat": 0,
                "ict_index": 0, "now_cost": 0, "selected_by_percent": 0,
                "total_points": 0, "points_per_game": 0,
            },
        ]
    )
    players.to_csv(season_dir / "players_raw.csv", index=False)
    pd.DataFrame({"id": [1], "name": ["Test FC"]}).to_csv(
        season_dir / "teams.csv",
        index=False,
    )

    clean, rejected = silver.load_and_clean_season(
        "2023-24",
        bronze_root,
    )

    assert set(clean["code"]) == {1}
    assert set(rejected["code"]) == {2}


def test_team_id_mapping_is_season_specific(synthetic_bronze_root, modules):
    silver = modules["silver"]
    clean_old, _ = silver.load_and_clean_season(
        "2019-20",
        synthetic_bronze_root,
    )
    clean_new, _ = silver.load_and_clean_season(
        "2023-24",
        synthetic_bronze_root,
    )

    assert clean_old.loc[clean_old["team"] == 1, "team_name"].iloc[0] == "Old Town"
    assert clean_new.loc[clean_new["team"] == 1, "team_name"].iloc[0] == "New Town"
