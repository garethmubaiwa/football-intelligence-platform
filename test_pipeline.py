"""
Single-command test runner for the football data pipeline.
Run from the project root:
    python test_pipeline.py

This delegates to pytest so all unit, regression, integration, and smoke checks run through the same test suite.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent
TESTS_DIR = PROJECT_ROOT / "tests"


if __name__ == "__main__":
    exit_code = pytest.main(["-v",str(TESTS_DIR),])
    sys.exit(exit_code)
