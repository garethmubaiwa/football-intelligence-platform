"""
ML layer: clustering and outlier detection for player archetypes and hidden talent.

"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

CLUSTER_FEATURES_BY_POSITION = {
    "FWD": ["goals_per_90", "assists_per_90", "threat", "creativity", "bps_per_90"],
    "MID": ["goals_per_90", "assists_per_90", "creativity", "threat", "influence"],
    "DEF": ["clean_sheets", "goals_per_90", "assists_per_90", "influence", "bps_per_90"],
    "GK": ["clean_sheets", "saves", "bps_per_90", "influence"],
}

MIN_MINUTES_FOR_CLUSTERING = 900  # minimum minutes played in a season to be included in clustering or outlier detection


def cluster_playing_styles(df: pd.DataFrame, season: str, n_clusters: int = 3) -> pd.DataFrame:
    """Clusters players within each position into playing-style archetypes,
    using only the given season's data with a minimum-minutes filter.
    """
    season_df = df[(df["season"] == season) & (df["minutes"] >= MIN_MINUTES_FOR_CLUSTERING)].copy()
    season_df["cluster"] = -1
    season_df["cluster_label"] = "insufficient_minutes"

    results = []
    for position, feature_cols in CLUSTER_FEATURES_BY_POSITION.items():
        subset = season_df[season_df["position"] == position].copy()
        if len(subset) < n_clusters:
            results.append(subset)
            continue

        X = subset[feature_cols].fillna(0)
        X_scaled = StandardScaler().fit_transform(X)

        km = KMeans(n_clusters=n_clusters, random_state=7, n_init=10)
        subset["cluster"] = km.fit_predict(X_scaled)

        # Label clusters by their dominant characteristic (highest z-scored feature)
        centers = pd.DataFrame(km.cluster_centers_, columns=feature_cols)
        for cluster_id in range(n_clusters):
            top_feature = centers.loc[cluster_id].idxmax()
            subset.loc[subset["cluster"] == cluster_id, "cluster_label"] = (
                f"{position}_{top_feature}_profile"
            )
        results.append(subset)

    return pd.concat(results, ignore_index=True)


def detect_value_outliers(df: pd.DataFrame, season: str, top_n: int = 15) -> pd.DataFrame:
    """Identifies real value outliers: high output relative to cost AND low
    ownership (genuinely under-the-radar), computed position-relatively so
    a cheap defender isn't unfairly compared to an expensive forward.
    """
    season_df = df[(df["season"] == season) & (df["minutes"] >= MIN_MINUTES_FOR_CLUSTERING)].copy()

    # Position-relative z-scores -- fair comparison within each position group
    for col in ["points_per_million", "selected_by_percent"]:
        season_df[f"{col}_zscore"] = season_df.groupby("position")[col].transform(
            lambda s: (s - s.mean()) / s.std(ddof=0)
        )

    # High value_score = high output-per-cost AND low ownership (genuinely under-the-radar)
    season_df["hidden_talent_score"] = (
        season_df["points_per_million_zscore"] - season_df["selected_by_percent_zscore"]
    )

    result = season_df.sort_values("hidden_talent_score", ascending=False).head(top_n)
    return result[[
        "web_name", "team_name", "position", "cost_millions", "total_points",
        "points_per_million", "selected_by_percent", "hidden_talent_score",
    ]]
