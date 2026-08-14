"""
    Bronze layer: land raw FPL season CSVs exactly as downloaded, with ingestion metadata.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

SEASONS = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]


def ingest_season(season: str, raw_root: Path, bronze_root: Path) -> dict:
    src_dir = raw_root / season
    dst_dir = bronze_root / season
    dst_dir.mkdir(parents=True, exist_ok=True)

    files_copied = []
    for fname in ["players_raw.csv", "teams.csv"]:
        src = src_dir / fname
        if not src.exists():
            raise FileNotFoundError(f"Expected raw file missing: {src}")
        dst = dst_dir / fname
        shutil.copy2(src, dst)
        files_copied.append(fname)

    manifest = {
        "season": season,
        "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": files_copied,
        "source": "https://github.com/vaastav/Fantasy-Premier-League",
    }
    return manifest


def ingest_all_seasons(raw_root: Path, bronze_root: Path) -> list[dict]:
    return [ingest_season(s, raw_root, bronze_root) for s in SEASONS]
