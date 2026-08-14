"""
Silver layer: cleans and normalizes raw player season stats from 5 seasons of real Premier League data.
Handles two challenges found during ingestion:
  1. SCHEMA EVOLUTION: expected_goals/expected_assists (xG/xA) only exist from 2022-23 onward. 
                Earlier seasons get these columns as nulls, not a crash and not a silently-wrong zero (Topic 3 §3.4).
  2. TEAM ID INSTABILITY: team `id` is reassigned every season (e.g. id=3 is Bournemouth in 2019-20, Brentford in 2021-22). 
                Team name MUST be joined using that season's OWN teams.csv, never a global id lookup. 
                This is the reason dim_team in gold.py is keyed by team name, not team id. 
"""


from __future__ import annotations

from pathlib import Path

import pandas as pd

POSITION_MAP = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

CORE_COLUMNS = [
    "code", "web_name", "first_name", "second_name", "element_type",
    "team", "minutes", "starts", "goals_scored", "assists", "clean_sheets",
    "goals_conceded", "own_goals", "yellow_cards", "red_cards", "saves",
    "penalties_missed", "penalties_saved", "bonus", "bps",
    "influence", "creativity", "threat", "ict_index",
    "now_cost", "selected_by_percent", "total_points", "points_per_game",
]
# `starts` was only added from 2022-23 onward -- discovered by actually
# running this pipeline against all 5 seasons, not assumed in advance.
XG_COLUMNS = ["expected_goals", "expected_assists", "expected_goal_involvements"]
OPTIONAL_CORE_COLUMNS = ["starts"]


def _season_to_years(season: str) -> tuple[int, int]:
    start = int("20" + season[:2])
    end = int("20" + season[-2:])
    return start, end


def load_and_clean_season(season: str, bronze_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (clean_rows, rejected_rows) for one season."""
    season_dir = bronze_root / season
    players = pd.read_csv(season_dir / "players_raw.csv")
    teams = pd.read_csv(season_dir / "teams.csv")[["id", "name"]].rename(columns={"id": "team", "name": "team_name"})

    available_xg_cols = [c for c in XG_COLUMNS if c in players.columns]
    missing_xg_cols = [c for c in XG_COLUMNS if c not in players.columns]
    for col in missing_xg_cols:
        players[col] = pd.NA  # explicit null, not a silent zero

    # Any CORE_COLUMNS entry missing from this season's schema (discovered empirically, e.g. 'starts' pre-2022-23) is added as explicit null too,
    # rather than crashing the whole season's ingestion.
    for col in CORE_COLUMNS:
        if col not in players.columns:
            players[col] = pd.NA

    keep_cols = CORE_COLUMNS + XG_COLUMNS
    df = players[keep_cols].copy()

    # Team ID instability: team `id` is reassigned every season (e.g. id=3 is Bournemouth in 2019-20, Brentford in 2021-22).
    # Team name MUST be joined using that season's OWN teams.csv, never a global id lookup. This is the reason dim_team in gold.py is keyed by team name, not team id.
    df = df.merge(teams, on="team", how="left")

    df["season"] = season
    start_year, end_year = _season_to_years(season)
    df["season_start_year"] = start_year
    df["position"] = df["element_type"].map(POSITION_MAP)

    # Filter out rows with invalid data (negative minutes, zero cost, missing position/team/code)
    valid_mask = (
        df["minutes"].ge(0)
        & df["now_cost"].gt(0)
        & df["position"].notna()
        & df["team_name"].notna()
        & df["code"].notna()
    )
    clean = df[valid_mask].copy()
    rejected = df[~valid_mask].copy()

    # Filter out duplicate rows (same player code and season) -- keep the first row, reject the rest. This is a discovered real-data gotcha, not an assumed one.
    dup_mask = clean.duplicated(subset=["code", "season"], keep="first")
    rejected = pd.concat([rejected, clean[dup_mask]], ignore_index=True)
    clean = clean[~dup_mask]

    return clean, rejected


def build_silver(bronze_root: Path, silver_root: Path, seasons: list[str]) -> dict:
    silver_root.mkdir(parents=True, exist_ok=True)
    all_clean = []
    all_rejected = []
    per_season_counts = {}

    for season in seasons:
        clean, rejected = load_and_clean_season(season, bronze_root)
        all_clean.append(clean)
        if len(rejected):
            rejected = rejected.copy()
            rejected["season"] = season
            all_rejected.append(rejected)
        per_season_counts[season] = {"clean_rows": len(clean), "rejected_rows": len(rejected)}

    combined = pd.concat(all_clean, ignore_index=True)
    combined.to_parquet(silver_root / "player_season_stats.parquet", index=False)

    if all_rejected:
        pd.concat(all_rejected, ignore_index=True).to_csv(
            silver_root / "rejected_rows.csv", index=False
        )

    return {
        "total_clean_rows": len(combined),
        "seasons_processed": len(seasons),
        "per_season": per_season_counts,
        "xg_data_available_seasons": [
            s for s in seasons if int(s[:4]) >= 2022
        ],
    }
