from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def test_validate_cluster_count_accepts_3_to_5(modules):
    ml = modules["ml"]

    for n_clusters in (3, 4, 5):
        ml.validate_cluster_count(n_clusters)


def test_validate_cluster_count_rejects_outside_range(modules):
    ml = modules["ml"]

    with pytest.raises(ValueError):
        ml.validate_cluster_count(2)

    with pytest.raises(ValueError):
        ml.validate_cluster_count(6)


def test_position_zscore_is_zero_for_constant_series(modules):
    ml = modules["ml"]
    series = pd.Series([5.0, 5.0, 5.0])

    result = ml.position_zscore(series)

    assert result.tolist() == [0.0, 0.0, 0.0]


def test_position_zscore_has_zero_mean(modules):
    ml = modules["ml"]
    series = pd.Series([1.0, 2.0, 3.0, 4.0])

    result = ml.position_zscore(series)

    assert np.isclose(result.mean(), 0.0)
    assert result.max() > 0
    assert result.min() < 0


def test_validate_required_columns_fails_clearly(modules):
    ml = modules["ml"]

    with pytest.raises(ValueError, match="missing"):
        ml.validate_required_columns(
            pd.DataFrame({"season": ["2023-24"]}),
            ["season", "minutes"],
        )


def test_cluster_output_contains_cluster_columns(sample_feature_df, modules):
    ml = modules["ml"]

    result = ml.cluster_playing_styles(
        sample_feature_df,
        season="2023-24",
        n_clusters=4,
    )

    assert "cluster" in result.columns
    assert "cluster_label" in result.columns
    assert result["cluster"].between(0, 3).all()
    assert result["cluster_label"].notna().all()
    assert len(result) == len(sample_feature_df)


def test_cluster_count_is_respected(sample_feature_df, modules):
    ml = modules["ml"]

    result = ml.cluster_playing_styles(sample_feature_df,season="2023-24",n_clusters=3,)
    clustered = result[result["cluster"] >= 0]
    assert set(clustered["cluster"].unique()) == {0, 1, 2}
    
    for position in clustered["position"].unique():
        position_clusters = clustered.loc[clustered["position"] == position,"cluster",]
        assert position_clusters.nunique() == 3


def test_clustering_respects_minimum_minutes(sample_feature_df, modules):
    ml = modules["ml"]
    df = sample_feature_df.copy()
    df.loc[:2, "minutes"] = 500

    result = ml.cluster_playing_styles(
        df,
        season="2023-24",
        n_clusters=3,
    )

    assert len(result) == 5
    assert (result["minutes"] >= 1000).all()


def test_clustering_requires_feature_columns(sample_feature_df, modules):
    ml = modules["ml"]
    df = sample_feature_df.drop(columns=["creativity_per_90"])

    with pytest.raises(ValueError, match="missing"):
        ml.cluster_playing_styles(
            df,
            season="2023-24",
            n_clusters=3,
        )


def test_outlier_output_contains_scores(sample_feature_df, modules):
    ml = modules["ml"]

    result = ml.detect_value_outliers(
        sample_feature_df,
        season="2023-24",
        top_n=5,
    )

    assert len(result) == 5
    assert "hidden_gem_score" in result.columns
    assert "overperformance_score" in result.columns
    assert "discovery_score" in result.columns
    assert result["discovery_score"].is_monotonic_decreasing


def test_hidden_gem_score_rewards_low_ownership(sample_feature_df, modules):
    ml = modules["ml"]
    df = sample_feature_df.copy()

    # Make player 0 clearly high value and low ownership.
    df.loc[0, "points_per_million"] = 100
    df.loc[0, "selected_by_percent"] = 0.1

    result = ml.detect_value_outliers(
        df,
        season="2023-24",
        top_n=8,
    )

    assert result.iloc[0]["web_name"] == "Player 0"


def test_pre_xg_seasons_do_not_get_false_overperformance(sample_feature_df, modules):
    ml = modules["ml"]
    df = sample_feature_df.copy()
    df["goals_minus_xg_per_90"] = np.nan
    df["assists_minus_xa_per_90"] = np.nan

    result = ml.detect_value_outliers(
        df,
        season="2023-24",
        top_n=5,
    )

    assert result["overperformance_score"].isna().all()
    assert result["discovery_score"].notna().all()


def test_outlier_detection_is_position_relative(sample_feature_df, modules):
    ml = modules["ml"]
    df = pd.concat(
        [
            sample_feature_df,
            sample_feature_df.assign(
                position="FWD",
                code=lambda x: x["code"] + 1000,
                web_name=lambda x: "FWD " + x["web_name"],
            ),
        ],
        ignore_index=True,
    )

    result = ml.detect_value_outliers(
        df,
        season="2023-24",
        top_n=16,
    )

    assert set(result["position"]) == {"MID", "FWD"}
