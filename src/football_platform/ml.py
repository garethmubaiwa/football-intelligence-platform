"""
Machine learning layer for player archetype clustering and hidden-gem / overperformer detection.

Input:
    DataFrame produced by build_player_season_features().

This layer does not create features. It consumes engineered features and applies clustering and position-relative scoring.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

MIN_MINUTES_FOR_CLUSTERING = 1000
DEFAULT_N_CLUSTERS = 4
MIN_CLUSTERS = 3
MAX_CLUSTERS = 5

CLUSTER_FEATURES_BY_POSITION = {
    "GK": ["saves_per_90","clean_sheets_per_90","goals_conceded_per_90","bps_per_90",],
    "DEF": ["clean_sheets_per_90","goals_per_90","assists_per_90","bps_per_90","threat_per_90",],
    "MID": ["goals_per_90","assists_per_90","creativity_per_90","threat_per_90","influence_per_90",],
    "FWD": ["goals_per_90","assists_per_90","threat_per_90","creativity_per_90","bps_per_90",],
}


def validate_cluster_count(n_clusters: int) -> None:
    """Ensure the requested number of clusters is between 3 and 5."""
    if not MIN_CLUSTERS <= n_clusters <= MAX_CLUSTERS:
        raise ValueError(f"n_clusters must be between {MIN_CLUSTERS} and " f"{MAX_CLUSTERS}. Received: {n_clusters}")


def validate_required_columns(df: pd.DataFrame,columns: list[str],) -> None:
    """Ensure required ML columns exist in the feature dataset."""
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(
            f"Feature dataset is missing required columns: {missing}"
        )

def position_zscore(series: pd.Series) -> pd.Series:
    """Calculate a z-score within a position group."""
    std = series.std(ddof=0)
    if pd.isna(std) or std == 0:
        return pd.Series(0.0, index=series.index)

    return (series - series.mean()) / std

def cluster_playing_styles(df: pd.DataFrame,season: str,n_clusters: int = DEFAULT_N_CLUSTERS,) -> pd.DataFrame:
    """
    Cluster players into position-specific playing-style archetypes.
    Players must have at least 1,000 minutes.
    """

    validate_cluster_count(n_clusters)
    validate_required_columns(df,["season", "minutes", "position"],)

    season_df = df[(df["season"] == season) & (df["minutes"] >= MIN_MINUTES_FOR_CLUSTERING)].copy()

    if season_df.empty:
        return season_df

    season_df["cluster"] = -1
    season_df["cluster_label"] = "not_clustered"

    results = []

    for position, feature_cols in CLUSTER_FEATURES_BY_POSITION.items():
        subset = season_df[season_df["position"] == position].copy()

        if len(subset) < n_clusters:
            subset["cluster_label"] = ("insufficient_players_for_clustering")
            results.append(subset)
            continue

        validate_required_columns(subset,feature_cols,)

        X = subset[feature_cols].copy()

        # Remove features that are completely unavailable for this
        # position/season. K-Means cannot learn from an all-null feature.
        usable_features = [column for column in feature_cols if X[column].notna().any()]

        if len(usable_features) < 2:
            subset["cluster_label"] = ("insufficient_feature_data")
            results.append(subset)
            continue

        X = X[usable_features]
        X = X.fillna(X.median())

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = KMeans(n_clusters=n_clusters,random_state=42,n_init=10,)
        subset["cluster"] = model.fit_predict(X_scaled)
        centers = pd.DataFrame(model.cluster_centers_,columns=usable_features,)

        for cluster_id in range(n_clusters):
            top_feature = centers.loc[cluster_id].idxmax()
            subset.loc[subset["cluster"] == cluster_id,"cluster_label",] = f"{position}_{top_feature}_profile"
        results.append(subset)

    return pd.concat(results, ignore_index=True)

def detect_value_outliers(df: pd.DataFrame,season: str,top_n: int = 15,) -> pd.DataFrame:
    """
    Detect hidden gems and overperformers.
    Hidden gem:
        high points per million + low ownership.
    Overperformer:
        positive goals-xG and/or assists-xA residual.
    All comparisons are position-relative.
    """

    validate_required_columns(
        df,
        [
            "season",
            "minutes",
            "position",
            "cost_millions",
            "points_per_million",
            "selected_by_percent",
            "goals_minus_xg_per_90",
            "assists_minus_xa_per_90",
        ],
    )

    season_df = df[(df["season"] == season) & (df["minutes"] >= MIN_MINUTES_FOR_CLUSTERING)].copy()

    if season_df.empty:
        return season_df

    # Hidden-gem score is a combination of points-per-million and ownership z-scores.

    season_df["points_per_million_zscore"] = (season_df.groupby("position")["points_per_million"].transform(position_zscore))

    season_df["ownership_zscore"] = (season_df.groupby("position")["selected_by_percent"].transform(position_zscore))

    season_df["hidden_gem_score"] = (season_df["points_per_million_zscore"] - season_df["ownership_zscore"])

    # Overperformance score is a combination of goals-xG and assists-xA z-scores.

    season_df["goals_minus_xg_zscore"] = np.nan
    season_df["assists_minus_xa_zscore"] = np.nan

    xg_available = season_df["goals_minus_xg_per_90"].notna()
    xa_available = season_df["assists_minus_xa_per_90"].notna()

    if xg_available.any():
        season_df.loc[xg_available, "goals_minus_xg_zscore"] = (season_df.loc[xg_available].groupby("position")["goals_minus_xg_per_90"].transform(position_zscore))

    if xa_available.any():
        season_df.loc[xa_available, "assists_minus_xa_zscore"] = (season_df.loc[xa_available].groupby("position")["assists_minus_xa_per_90"].transform(position_zscore))

    # Keep overperformance unavailable for seasons without xG/xA.
    xg_xa_available = (season_df["goals_minus_xg_per_90"].notna() & season_df["assists_minus_xa_per_90"].notna())
    season_df["overperformance_score"] = np.nan

    season_df.loc[xg_xa_available, "overperformance_score"] = (season_df.loc[xg_xa_available, "goals_minus_xg_zscore"] + season_df.loc[xg_xa_available, "assists_minus_xa_zscore"])

    # Discovery score is a combination of hidden-gem and overperformance scores. For seasons without xG/xA, the discovery score is just the hidden-gem score.

    season_df["discovery_score"] = season_df["hidden_gem_score"]

    season_df["discovery_score"] = season_df["hidden_gem_score"].astype(float)

    season_df.loc[xg_xa_available, "discovery_score"] = (
        0.70 * season_df.loc[xg_xa_available, "hidden_gem_score"] + 0.30 * season_df.loc[xg_xa_available, "overperformance_score"])

    result = (season_df.sort_values("discovery_score", ascending=False).head(top_n))

    output_columns = [
        "web_name",
        "team_name",
        "position",
        "minutes",
        "cost_millions",
        "total_points",
        "points_per_million",
        "selected_by_percent",
        "goals_per_90",
        "assists_per_90",
        "goals_minus_xg_per_90",
        "assists_minus_xa_per_90",
        "hidden_gem_score",
        "overperformance_score",
        "discovery_score",
    ]

    return result[[column for column in output_columns if column in result.columns]]
