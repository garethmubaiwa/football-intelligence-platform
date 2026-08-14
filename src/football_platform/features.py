
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


def build_player_season_features(gold_db_path: Path) -> pd.DataFrame:
    conn = duckdb.connect(str(gold_db_path), read_only=True)
    df = conn.execute("""
        SELECT
            p.code, p.web_name, t.team_name, s.season, s.start_year,
            pos.position_code AS position,
            f.minutes, f.starts, f.goals_scored, f.assists, f.clean_sheets,
            f.goals_conceded, f.yellow_cards, f.red_cards, f.bonus, f.bps,
            f.influence, f.creativity, f.threat, f.ict_index, f.saves,
            f.now_cost, f.selected_by_percent, f.total_points, f.points_per_game,
            f.expected_goals, f.expected_assists
        FROM fact_player_season_stats f
        JOIN dim_player p ON f.player_key = p.player_key
        JOIN dim_team t ON f.team_key = t.team_key
        JOIN dim_season s ON f.season_key = s.season_key
        JOIN dim_position pos ON f.position_key = pos.position_key
    """).fetchdf()
    conn.close()

    # Per-90 rate stats (fair comparison regardless of minutes played)
    nineties = (df["minutes"] / 90).replace(0, np.nan)
    df["goals_per_90"] = df["goals_scored"] / nineties
    df["assists_per_90"] = df["assists"] / nineties
    df["goal_involvements_per_90"] = (df["goals_scored"] + df["assists"]) / nineties
    df["bps_per_90"] = df["bps"] / nineties

    # Value / market-efficiency score (real FPL cost as market-value proxy) 
    df["cost_millions"] = df["now_cost"] / 10.0
    df["points_per_million"] = df["total_points"] / df["cost_millions"]

    df = df.sort_values(["code", "start_year"])

    # Group by player code
    grouped = df.groupby("code")

    # Year-over-year change in points_per_game (requires >= 2 seasons of history to be meaningful)
    df["points_per_game_prev_season"] = grouped["points_per_game"].shift(1)
    df["points_per_game_yoy_change"] = df["points_per_game"] - df["points_per_game_prev_season"]

    # Consistency: rolling std dev of points_per_game across all seasons played so far (requires >= 2 seasons of history to be meaningful)
    df["points_consistency_std"] = grouped["points_per_game"].transform(
        lambda s: s.expanding(min_periods=2).std()
    )

    # Career trajectory: linear trend (slope) of goals_per_90 across all seasons played so far (requires multiple seasons).
    def _trend_slope(series: pd.Series) -> pd.Series:
        out = []
        for i in range(len(series)):
            window = series.iloc[: i + 1].dropna()
            if len(window) < 2:
                out.append(np.nan)
            else:
                x = np.arange(len(window))
                slope = np.polyfit(x, window.values, 1)[0]
                out.append(slope)
        return pd.Series(out, index=series.index)

    df["goals_per_90_trend_slope"] = grouped["goals_per_90"].transform(_trend_slope)

    # Seasons of history available AS OF this row (for filtering trend features to only meaningful, multi-season-backed rows downstream)
    df["seasons_of_history"] = grouped.cumcount() + 1

    return df.reset_index(drop=True)
