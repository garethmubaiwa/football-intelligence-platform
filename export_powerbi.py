"""
This script exports the gold warehouse tables to CSV files for Power BI consumption.
The exported CSV files are saved in the `powerbi_export` directory.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).parent
EXPORT_DIR = ROOT / "powerbi_export"
EXPORT_DIR.mkdir(exist_ok=True)

conn = duckdb.connect(str(ROOT / "data" / "gold" / "warehouse.duckdb"), read_only=True)

for table in ["dim_player", "dim_team", "dim_season", "dim_position", "fact_player_season_stats"]:
    df = conn.execute(f"SELECT * FROM {table}").fetchdf()
    df.to_csv(EXPORT_DIR / f"{table}.csv", index=False)
    print(f"Exported {table}: {len(df)} rows -> {EXPORT_DIR / f'{table}.csv'}")

conn.close()
