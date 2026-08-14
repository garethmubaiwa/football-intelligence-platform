"""Computes ground-truth values for the DAX measures in dax/measures.md,
using the real exported star schema CSVs -- same methodology as Topic 10.
"""
import pandas as pd
from pathlib import Path

EXPORT_DIR = Path(__file__).parent.parent / "powerbi_export"

fact = pd.read_csv(EXPORT_DIR / "fact_player_season_stats.csv")
dim_player = pd.read_csv(EXPORT_DIR / "dim_player.csv")
dim_season = pd.read_csv(EXPORT_DIR / "dim_season.csv")

joined = fact.merge(dim_player, on="player_key").merge(dim_season, on="season_key")

print("=" * 90)
print("[Total Goals] and [Total Points], all seasons combined")
print("=" * 90)
print(f"Total Goals = {fact['goals_scored'].sum():,}")
print(f"Total Points = {fact['total_points'].sum():,}")

print("\n" + "=" * 90)
print("[Top Scorer Points] per season")
print("=" * 90)
for season in sorted(joined["season"].unique()):
    season_df = joined[joined["season"] == season]
    top = season_df.loc[season_df["total_points"].idxmax()]
    print(f"  {season}: {top['web_name']} — {top['total_points']} points")

print("\n" + "=" * 90)
print("[Value Rank] top 5, 2023-24 (Total Points / Cost in millions)")
print("=" * 90)
s2324 = joined[joined["season"] == "2023-24"].copy()
s2324["value"] = s2324["total_points"] / (s2324["now_cost"] / 10)
top5 = s2324.nlargest(5, "value")[["web_name", "total_points", "now_cost", "value"]]
print(top5.to_string(index=False))
