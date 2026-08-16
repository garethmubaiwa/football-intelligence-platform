from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from football_platform import bronze, features, gold, ml, silver  


@pytest.fixture
def modules():
    return {
        "bronze": bronze,
        "silver": silver,
        "gold": gold,
        "features": features,
        "ml": ml,
    }


@pytest.fixture
def sample_player_columns():
    return {
        "code", "web_name", "first_name", "second_name", "element_type",
        "team", "minutes", "starts", "goals_scored", "assists",
        "clean_sheets", "goals_conceded", "own_goals", "yellow_cards",
        "red_cards", "saves", "penalties_missed", "penalties_saved",
        "bonus", "bps", "influence", "creativity", "threat", "ict_index",
        "now_cost", "selected_by_percent", "total_points", "points_per_game",
        "expected_goals", "expected_assists", "expected_goal_involvements",
        "season", "season_start_year", "position", "team_name",
    }


@pytest.fixture
def synthetic_bronze_root(tmp_path: Path) -> Path:
    """Create two tiny Bronze seasons with schema evolution and team-ID reuse."""
    bronze_root = tmp_path / "bronze"

    seasons = ["2019-20", "2023-24"]
    positions = [(1, "GK"), (2, "DEF"), (3, "MID"), (4, "FWD")]

    for season in seasons:
        season_dir = bronze_root / season
        season_dir.mkdir(parents=True)

        rows = []
        player_id = 1000

        # Same raw team ID is deliberately mapped to different names between
        # seasons to regression-test season-specific team lookup.
        team_name_by_id = {
            1: "Old Town" if season == "2019-20" else "New Town",
            2: "North FC",
            3: "South FC",
            4: "West FC",
        }

        for element_type, _position_name in positions:
            for i in range(4):
                code = 1000 + element_type * 10 + i
                team_id = element_type
                minutes = 1000 + i * 180
                goals = i + element_type
                assists = i
                clean_sheets = max(0, 10 - i)
                saves = (20 + i * 4) if element_type == 1 else 0
                row = {
                    "code": code,
                    "web_name": f"Player_{code}",
                    "first_name": "Test",
                    "second_name": f"Player_{code}",
                    "element_type": element_type,
                    "team": team_id,
                    "minutes": minutes,
                    "starts": 10 + i,
                    "goals_scored": goals,
                    "assists": assists,
                    "clean_sheets": clean_sheets,
                    "goals_conceded": 5 + i,
                    "own_goals": 0,
                    "yellow_cards": i % 2,
                    "red_cards": 0,
                    "saves": saves,
                    "penalties_missed": 0,
                    "penalties_saved": 0,
                    "bonus": 5 + i,
                    "bps": 80 + i * 10,
                    "influence": 40 + i * 3,
                    "creativity": 30 + i * 4,
                    "threat": 35 + i * 5,
                    "ict_index": 6 + i * 0.5,
                    "now_cost": 50 + i * 5,
                    "selected_by_percent": 2.0 + i,
                    "total_points": 90 + i * 15,
                    "points_per_game": 5.0 + i * 0.2,
                }

                if season == "2023-24":
                    row.update(
                        {
                            "expected_goals": goals - 0.3,
                            "expected_assists": assists + 0.1,
                            "expected_goal_involvements": goals + assists - 0.2,
                        }
                    )

                rows.append(row)

        pd.DataFrame(rows).to_csv(
            season_dir / "players_raw.csv",
            index=False,
        )

        teams = pd.DataFrame(
            {
                "id": [1, 2, 3, 4],
                "name": [
                    team_name_by_id[1],
                    team_name_by_id[2],
                    team_name_by_id[3],
                    team_name_by_id[4],
                ],
            }
        )
        teams.to_csv(season_dir / "teams.csv", index=False)

    return bronze_root


@pytest.fixture
def sample_feature_df():
    """Small deterministic ML feature dataset with all required features."""
    rows = []
    base = {
        "season": "2023-24",
        "team_name": "Test FC",
        "cost_millions": 6.0,
        "selected_by_percent": 5.0,
        "total_points": 150,
        "points_per_million": 25.0,
        "goals_minus_xg_per_90": 0.10,
        "assists_minus_xa_per_90": 0.05,
        "goals_per_90": 0.5,
        "assists_per_90": 0.2,
        "clean_sheets_per_90": 0.3,
        "goals_conceded_per_90": 0.5,
        "saves_per_90": 2.0,
        "bps_per_90": 10.0,
        "influence_per_90": 1.0,
        "creativity_per_90": 1.0,
        "threat_per_90": 1.0,
        "minutes": 1800,
        "position": "MID",
    }

    for i in range(8):
        row = base.copy()
        row["code"] = 1000 + i
        row["web_name"] = f"Player {i}"
        row["goals_per_90"] += i * 0.08
        row["assists_per_90"] += (7 - i) * 0.03
        row["creativity_per_90"] += i * 0.10
        row["threat_per_90"] += (i % 4) * 0.15
        row["influence_per_90"] += i * 0.05
        row["points_per_million"] += (i - 3) * 2
        row["selected_by_percent"] += i * 1.5
        row["goals_minus_xg_per_90"] += (i - 3) * 0.04
        row["assists_minus_xa_per_90"] += (3 - i) * 0.01
        rows.append(row)

    return pd.DataFrame(rows)
