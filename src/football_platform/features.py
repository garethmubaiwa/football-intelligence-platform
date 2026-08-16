"""
Feature engineering layer for player-season ML.
Reads the Gold star-schema warehouse and creates ML-ready features.
Feature groups:
- Per-90 style/performance metrics
- Value and market-efficiency metrics
- Actual-vs-expected overperformance metrics
- Historical trajectory and consistency metrics
"""

from __future__ import annotations
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

def build_player_season_features(gold_db_path: Path) -> pd.DataFrame:
    """Read Gold and return one ML-ready row per player-season."""
    conn = duckdb.connect(str(gold_db_path), read_only=True)

    df = conn.execute("""
        SELECT
            p.code,
            p.web_name,
            t.team_name,
            s.season,
            s.start_year,
            pos.position_code AS position,
            f.minutes,
            f.starts,
            f.goals_scored,
            f.assists,
            f.clean_sheets,
            f.goals_conceded,
            f.own_goals,
            f.yellow_cards,
            f.red_cards,
            f.saves,
            f.penalties_missed,
            f.penalties_saved,
            f.bonus,
            f.bps,
            f.influence,
            f.creativity,
            f.threat,
            f.ict_index,
            f.now_cost,
            f.selected_by_percent,
            f.total_points,
            f.points_per_game,
            f.expected_goals,
            f.expected_assists,
            f.expected_goal_involvements
        FROM fact_player_season_stats f
        JOIN dim_player p ON f.player_key = p.player_key
        JOIN dim_team t ON f.team_key = t.team_key
        JOIN dim_season s ON f.season_key = s.season_key
        JOIN dim_position pos ON f.position_key = pos.position_key
    """).fetchdf()

    conn.close()

    df = df.sort_values(["code", "start_year"]).reset_index(drop=True)

    # Per-90 features

    nineties = df["minutes"].replace(0, np.nan) / 90.0
    df["goals_per_90"] = df["goals_scored"] / nineties
    df["assists_per_90"] = df["assists"] / nineties
    df["goal_involvements_per_90"] = ((df["goals_scored"] + df["assists"]) / nineties)
    df["clean_sheets_per_90"] = df["clean_sheets"] / nineties
    df["goals_conceded_per_90"] = df["goals_conceded"] / nineties
    df["saves_per_90"] = df["saves"] / nineties
    df["bonus_per_90"] = df["bonus"] / nineties
    df["bps_per_90"] = df["bps"] / nineties
    df["influence_per_90"] = df["influence"] / nineties
    df["creativity_per_90"] = df["creativity"] / nineties
    df["threat_per_90"] = df["threat"] / nineties
    df["ict_index_per_90"] = df["ict_index"] / nineties
    df["points_per_90"] = df["total_points"] / nineties

    # Actual-vs-expected features
    df["goals_minus_xg"] = (df["goals_scored"] - df["expected_goals"])
    df["assists_minus_xa"] = (df["assists"] - df["expected_assists"])
    df["goal_involvements_minus_xgi"] = (df["goals_scored"] + df["assists"] - df["expected_goal_involvements"])
    df["goals_minus_xg_per_90"] = (df["goals_minus_xg"] / nineties)
    df["assists_minus_xa_per_90"] = (df["assists_minus_xa"] / nineties)
    df["goal_involvements_minus_xgi_per_90"] = (df["goal_involvements_minus_xgi"] / nineties)

    # Value/market features
    df["cost_millions"] = df["now_cost"] / 10.0
    df["points_per_million"] = (df["total_points"] / df["cost_millions"].replace(0, np.nan))

    # Historical features
    grouped = df.groupby("code")
    df["points_per_game_prev_season"] = (grouped["points_per_game"].shift(1))
    df["points_per_game_yoy_change"] = (df["points_per_game"] - df["points_per_game_prev_season"])
    df["points_per_90_prev_season"] = (grouped["points_per_90"].shift(1))
    df["points_per_90_yoy_change"] = (df["points_per_90"] - df["points_per_90_prev_season"])
    df["points_consistency_std"] = grouped["points_per_game"].transform(lambda s: s.expanding(min_periods=2).std())

    # Historical trend features

    def expanding_trend(series: pd.Series) -> pd.Series:
        output = []
        for i in range(len(series)):
            window = series.iloc[:i + 1].dropna()
            if len(window) < 2:
                output.append(np.nan)
                continue

            x = np.arange(len(window), dtype=float)
            y = window.to_numpy(dtype=float)
            output.append(np.polyfit(x, y, 1)[0])

        return pd.Series(output, index=series.index)

    df["goals_per_90_trend_slope"] = (grouped["goals_per_90"].transform(expanding_trend))
    df["assists_per_90_trend_slope"] = (grouped["assists_per_90"].transform(expanding_trend))

    # Historical trajectory features
    df["seasons_of_history"] = grouped.cumcount() + 1
    df["has_previous_season"] = df["seasons_of_history"] >= 2
    df["has_xg_data"] = df["expected_goals"].notna()
    df["has_xa_data"] = df["expected_assists"].notna()

    return df.sort_values(["start_year", "position", "code"]).reset_index(drop=True)
