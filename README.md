# Football Data Intelligence Platform

[![CI](https://github.com/garethmubaiwa/football-intelligence-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/garethmubaiwa/football-intelligence-platform/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![DuckDB](https://img.shields.io/badge/warehouse-DuckDB-yellow.svg)](https://duckdb.org/)
[![Docker](https://img.shields.io/badge/container-Docker-2496ED.svg)](https://www.docker.com/)
[![Power BI](https://img.shields.io/badge/BI-Power%20BI-F2C811.svg)](https://powerbi.microsoft.com/)

An end-to-end football data intelligence platform built on **real Premier League data**, demonstrating modern data engineering, analytical warehousing, feature engineering, machine learning, business intelligence, testing, containerization, and continuous integration.

The platform processes **five real Premier League seasons (2019-20 through 2023-24)** sourced from the [Fantasy Premier League dataset maintained by vaastav](https://github.com/vaastav/Fantasy-Premier-League).

The goal is not simply to analyze football statistics. The goal is to demonstrate how to build a **reproducible, testable, production-style data platform around real-world data**.

---

## Overview

The platform implements a complete data workflow:

```text
Real FPL Data
     │
     ▼
┌───────────────┐
│    BRONZE     │
│               │
│ Raw source    │
│ data          │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│    SILVER     │
│               │
│ Schema fixes  │
│ Validation    │
│ Cleaning      │
│ Team mapping  │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│     GOLD      │
│               │
│ DuckDB        │
│ Star schema   │
└───────┬───────┘
        │
        ├───────────────┐
        │               │
        ▼               ▼
┌───────────────┐ ┌───────────────┐
│  FEATURES     │ │      ML       │
│               │ │               │
│ Trends        │ │ Clustering    │
│ Multi-season  │ │ Outliers      │
│ statistics    │ │               │
└───────┬───────┘ └───────┬───────┘
        │                 │
        └────────┬────────┘
                 ▼
        ┌──────────────────┐
        │    POWER BI      │
        │                  │
        │ CSV exports      │
        │ DAX measures     │
        └──────────────────┘

                 +

        ┌──────────────────┐
        │     TESTING      │
        │                  │
        │ pytest           │
        │ Data validation  │
        │ Real-world facts │
        └──────────────────┘
```

---

# Why this project exists

This project was built to demonstrate several areas of practical data engineering and analytics that are difficult to show using toy datasets.

The pipeline intentionally works with historical data that changes shape over time, contains real-world modelling traps, and requires downstream analytical validation.

The project therefore focuses on:

* reproducibility
* schema evolution
* dimensional modelling
* historical accuracy
* automated testing
* analytical feature engineering
* machine learning
* business intelligence
* containerization
* CI/CD

---

# Key technologies

| Area                    | Technology                            |
| ----------------------- | ------------------------------------- |
| Language                | Python 3.12+                          |
| Data processing         | pandas                                |
| Analytical storage      | Parquet                               |
| Data warehouse          | DuckDB                                |
| Machine learning        | scikit-learn                          |
| Testing                 | pytest                                |
| BI                      | Power BI                              |
| Containerization        | Docker                                |
| Container orchestration | Docker Compose                        |
| CI                      | GitHub Actions                        |
| Packaging               | setuptools / `pyproject.toml`         |
| Source data             | Fantasy Premier League GitHub dataset |

---

# Data source

Historical Fantasy Premier League data is sourced from:

**vaastav/Fantasy-Premier-League**

https://github.com/vaastav/Fantasy-Premier-League

The current pipeline processes:

* 2019-20
* 2020-21
* 2021-22
* 2022-23
* 2023-24

The project deliberately downloads and processes source data through the pipeline rather than manually curating analytical outputs.

This keeps the workflow reproducible and makes it possible to rebuild the warehouse from source data.

---

# The three real bugs discovered and fixed

One of the main purposes of the project was to work through problems that actually appear when working with historical production-like data.

These were not hypothetical examples.

They were found while running the pipeline against the real historical dataset.

---

## 1. Schema evolution: `expected_goals`

The dataset does not contain Expected Goals (`expected_goals`) consistently across all five historical seasons.

A pipeline that assumes the column exists everywhere fails as soon as it processes an older season.

### Original problem

A transformation attempted to select:

```text
expected_goals
```

for every season.

Historical seasons without that field caused the pipeline to fail.

### Solution

The Silver layer now checks the schema of each season before selecting expected columns.

If a column does not exist, it is explicitly created as a null field.

Conceptually:

```text
Column exists
    │
    ├── Yes → use source value
    │
    └── No  → create NULL column
```

This is intentionally **not converted to zero**.

Missing data means:

```text
"We do not have this measurement."
```

Zero means:

```text
"The measurement exists and its value is zero."
```

Those are analytically different meanings.

---

# 2. Schema evolution: `starts`

While executing the pipeline across all five seasons, a second historical schema difference was discovered.

The `starts` field is also unavailable in some earlier seasons.

The initial problem was specific-column handling.

The improved solution is generalized.

Instead of hard-coding special cases for only `expected_goals`, the Silver layer now checks the entire expected schema against the actual schema available for each season.

Conceptually:

```text
Expected schema
       │
       ▼
Compare against
season schema
       │
       ├── Column exists
       │      └── use source value
       │
       └── Column missing
              └── create explicit NULL
```

This makes the pipeline safer against further historical schema changes.

---

# 3. FPL team IDs are not stable historical keys

The most important modelling issue discovered was the handling of team IDs.

A raw FPL team ID should **not** automatically be treated as a permanent club key across seasons.

Historical source data can reuse team IDs for different clubs in different seasons.

That means this design is unsafe:

```text
dim_team
---------
team_id = source FPL team ID
```

as a global historical key.

If that assumption is made, player-team history can become silently corrupted.

---

## Solution

The Silver layer joins each player's team ID to the team metadata from **that same season**.

The resolved team name is then used to identify the actual club entity before the warehouse is constructed.

Conceptually:

```text
Season player data
       │
       ▼
Season-specific teams.csv
       │
       ▼
Resolve team ID → team name
       │
       ▼
Stable club identity
       │
       ▼
Gold warehouse
```

This prevents a source-system identifier from being incorrectly treated as a universal business key.

---

# Historical transfer validation

The team-key issue is protected by an automated regression test based on a real transfer.

The warehouse correctly represents:

```text
Aston Villa
     │
     │ summer 2021
     ▼
Manchester City
```

for **Jack Grealish**.

This verifies that the team-resolution logic survives the season boundary correctly.

The test is deliberately based on a real-world football event rather than merely checking that rows exist.

---

# Independent real-world validation

The platform validates calculated results against publicly known Premier League outcomes.

The warehouse-derived top scorer for each processed season matches the known league result:

| Season  | Top scorer      |
| ------- | --------------- |
| 2019-20 | Kevin De Bruyne |
| 2020-21 | Bruno Fernandes |
| 2021-22 | Mohamed Salah   |
| 2022-23 | Erling Haaland  |
| 2023-24 | Cole Palmer     |

These values are derived from the pipeline's warehouse rather than manually inserted into the dataset.

This provides an external sanity check that the transformation logic has not silently corrupted the historical records.

---

# Architecture

The platform follows a classic medallion architecture.

## Bronze

The Bronze layer preserves raw source data as downloaded.

Purpose:

* source traceability
* reproducibility
* raw-data preservation
* separation of ingestion from transformation

Location:

```text
data/bronze/<season>/
```

---

## Silver

The Silver layer performs the main historical data-quality and schema work.

Responsibilities include:

* schema validation
* schema evolution handling
* missing-column handling
* season-aware team resolution
* cleaning
* type standardization
* rejected-row handling
* validation

Primary output:

```text
data/silver/player_season_stats.parquet
```

---

## Gold

The Gold layer is the analytical warehouse.

The warehouse is stored in DuckDB:

```text
data/gold/warehouse.duckdb
```

The Gold layer contains a star schema designed for downstream analytics and BI.

---

# Gold warehouse model

## Dimensions

### `dim_player`

One record per player.

Contains the stable player attributes needed for analytical joins.

---

### `dim_team`

One record per club.

The club identity is resolved from season-specific source metadata rather than blindly using raw FPL team IDs as global keys.

---

### `dim_season`

One record per football season.

Used for season-level filtering, relationships, and historical analysis.

---

### `dim_position`

One record per position category.

Used for player segmentation and analytical grouping.

---

## Fact table

### `fact_player_season_stats`

The central analytical fact table contains player-season-level statistics.

Conceptually:

```text
fact_player_season_stats
│
├── player_key
├── team_key
├── season_key
├── position_key
├── minutes
├── appearances
├── starts
├── goals
├── assists
├── clean_sheets
├── expected_goals
├── expected_assists
└── other season-level measures
```

This creates a consistent analytical grain:

```text
one player
+
one season
=
one fact record
```

where the available historical source data supports the corresponding metric.

---

# Feature engineering

The project builds multi-season player features from the Gold warehouse.

Examples include:

* historical output
* multi-season trends
* performance changes
* scoring metrics
* creative metrics
* playing-time measurements
* season-over-season changes
* feature combinations used by the ML pipeline

The feature layer produces:

```text
data/gold/player_features.parquet
```

These features form the bridge between traditional warehouse analytics and machine learning.

---

# Machine learning

The ML layer uses scikit-learn to perform unsupervised player analysis.

The workflow includes:

```text
Gold warehouse
      │
      ▼
Feature extraction
      │
      ▼
Feature preparation
      │
      ▼
Player representations
      │
      ▼
Clustering
      │
      ▼
Player archetypes
      │
      ▼
Outlier detection
```

The purpose is not merely to demonstrate that clustering can be run.

The goal is to create football-relevant groups that can be interpreted analytically.

The resulting clusters separate different forward archetypes, including profiles resembling:

### Finishing-focused forwards

Examples include:

* Erling Haaland
* Callum Wilson
* Alexander Isak
* Chris Wood

### More creative / all-round forward profiles

Examples include:

* Ollie Watkins
* Gabriel Jesus
* Cody Gakpo
* Darwin Núñez

This provides a useful sanity check that the engineered features capture meaningful football characteristics.

---

# Hidden-talent / value-outlier detection

In addition to clustering, the ML layer identifies statistical outliers.

The intention is to surface players who may appear unusually strong or undervalued relative to the broader player population.

The output can be used as a starting point for:

* scouting-style analysis
* recruitment analysis
* transfer-value exploration
* BI reporting
* further player evaluation

The project deliberately treats the outlier score as an analytical signal rather than claiming it is a definitive recruitment model.

---

# Power BI integration

The project exports the analytical model into Power BI-ready CSV files.

Output directory:

```text
powerbi_export/
```

The Power BI layer is designed around the Gold warehouse rather than raw source files.

This provides a clean separation:

```text
Source data
     ↓
ETL / transformation
     ↓
Analytical warehouse
     ↓
Power BI export
     ↓
Dashboard
```

---

# DAX

Example DAX measures are documented in:

```text
dax/measures.md
```

The project also includes a validation script:

```text
dax/validate_dax_measures.py
```

Run it with:

```bash
python dax/validate_dax_measures.py
```

The goal is to compare BI-layer calculations against independently computed ground-truth results.

---

# Testing

Testing is a core part of the project rather than an afterthought.

The test suite is implemented with pytest.

Run:

```bash
python -m pytest tests/ -v
```

The tests cover areas such as:

* pipeline output creation
* warehouse table existence
* schema-evolution handling
* season-level scoring validation
* team-history validation
* real-world historical checks
* Jack Grealish's 2021 transfer boundary

The test suite is designed to protect against silent data-quality regressions.

---

# Reproducibility

The project supports three execution environments.

| Environment                | Purpose                |
| -------------------------- | ---------------------- |
| Python virtual environment | Local development      |
| Docker Compose             | Reproducible execution |
| GitHub Actions             | Automated CI           |

All three environments execute the same underlying Python project.

---

# Project structure

```text
football-intelligence-platform/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── data/
│   └── .gitkeep
│
├── dax/
│   ├── measures.md
│   └── validate_dax_measures.py
│
├── powerbi_export/
│   └── .gitkeep
│
├── src/
│   └── football_platform/
│       ├── __init__.py
│       ├── bronze.py
│       ├── silver.py
│       ├── gold.py
│       ├── features.py
│       └── ml.py
│
├── tests/
│   └── test_pipeline.py
│
├── .dockerignore
├── .gitignore
├── Dockerfile
├── compose.yaml
├── pyproject.toml
├── requirements.txt
├── run_pipeline.py
├── export_powerbi.py
└── README.md
```

---

# Installation

## Requirements

For local development:

* Python 3.12+
* Git

For Docker:

* Docker Desktop or Docker Engine
* Docker Compose

---

# Option 1 — Python virtual environment

This is the recommended development method.

## 1. Clone the repository

```bash
git clone https://github.com/garethmubaiwa/football-intelligence-platform.git
cd football-intelligence-platform
```

---

## 2. Create a virtual environment

### macOS / Linux

```bash
python3 -m venv .venv
```

### Windows

```powershell
py -3.12 -m venv .venv
```

---

## 3. Activate the virtual environment

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### Windows Command Prompt

```cmd
.venv\Scripts\activate
```

---

## 4. Upgrade pip

```bash
python -m pip install --upgrade pip
```

---

## 5. Install the project

```bash
pip install -e .
```

The editable installation installs the package from `src/` and avoids requiring:

```text
PYTHONPATH=src
```

---

## 6. Verify dependencies

```bash
python -c "import pandas, duckdb, sklearn, pyarrow; print('Dependencies OK')"
```

Expected output:

```text
Dependencies OK
```

---

# Running the project locally

## Step 1 — Run the complete pipeline

```bash
python run_pipeline.py
```

This runs the main Bronze → Silver → Gold → Features → ML workflow.

---

## Step 2 — Export Power BI data

```bash
python export_powerbi.py
```

---

## Step 3 — Validate DAX measures

```bash
python dax/validate_dax_measures.py
```

---

## Step 4 — Run the test suite

```bash
python -m pytest tests/ -v
```

---

# Expected generated outputs

After successful execution, generated artifacts should include files under:

```text
data/
├── raw/
├── bronze/
├── silver/
│   └── player_season_stats.parquet
└── gold/
    ├── warehouse.duckdb
    ├── player_features.parquet
    └── ML outputs
```

Power BI outputs are written under:

```text
powerbi_export/
```

Generated analytical data is intentionally excluded from Git by default.

---

# Option 2 — Docker

Docker provides a reproducible runtime environment without requiring the user to manually install the Python dependencies.

## Build the project image

```bash
docker compose build
```

---

## Run the pipeline

```bash
docker compose run --rm pipeline
```

---

## Run tests

```bash
docker compose run --rm test
```

---

## Run the Power BI export

```bash
docker compose run --rm export
```

---

## Run DAX validation

```bash
docker compose run --rm dax
```

Generated files are mounted back into the local project directories so they remain accessible after the container exits.

---

# Docker services

The Compose configuration provides four one-off services:

| Service    | Purpose                            |
| ---------- | ---------------------------------- |
| `pipeline` | Execute the full ETL / ML pipeline |
| `test`     | Run pytest                         |
| `export`   | Generate Power BI CSV exports      |
| `dax`      | Validate DAX measures              |

Examples:

```bash
docker compose run --rm pipeline
docker compose run --rm test
docker compose run --rm export
docker compose run --rm dax
```

---

# Recommended development workflow

For day-to-day development:

```text
1. Create / activate .venv
2. Install with pip install -e .
3. Modify source code
4. Run the pipeline
5. Run pytest
6. Inspect results
7. Commit changes
8. Push to GitHub
9. GitHub Actions runs automatically
```

Example:

```bash
source .venv/bin/activate

pip install -e .

python run_pipeline.py

python -m pytest tests/ -v

git status

git add .

git commit -m "Improve player feature engineering"

git push
```

---

# Continuous integration

GitHub Actions runs the project automatically on:

* pushes to `main`
* pushes to `master`
* pull requests targeting `main`
* pull requests targeting `master`
* manual workflow execution

The CI workflow performs:

```text
Checkout repository
        ↓
Install Python 3.12
        ↓
Install project
        ↓
Run pipeline
        ↓
Run pytest
        ↓
Export Power BI data
        ↓
Validate DAX
        ↓
PASS / FAIL
```

This means a successful GitHub Actions run verifies that the entire project can still execute from a clean environment.

---

# CI workflow

The workflow is stored in:

```text
.github/workflows/ci.yml
```

It is intentionally designed to execute the same commands used during local development.

---

# Data management

The repository intentionally does **not** commit large generated datasets or analytical warehouse artifacts.

Generated data is excluded through `.gitignore`.

Examples include:

```text
data/raw/
data/bronze/
data/silver/
data/gold/
powerbi_export/
```

The source code required to regenerate these outputs remains in the repository.

This keeps the Git repository:

* lightweight
* reproducible
* maintainable
* easier to clone
* easier for CI to execute

---

# Design principles

Several principles guide the implementation.

## Preserve raw data

Bronze is intentionally close to the source representation.

Transformations should happen downstream rather than overwriting the original ingestion layer.

---

## Treat schema evolution as normal

Historical data rarely remains perfectly consistent.

The pipeline therefore checks source schemas rather than assuming that every season has identical columns.

---

## Do not confuse missing with zero

Where the source lacks a historical metric, the value remains null.

This protects analytical correctness.

---

## Do not blindly trust source IDs

Source-system IDs are not automatically business keys.

Team identity is resolved through season-specific source metadata before warehouse modelling.

---

## Separate transformation layers

Bronze, Silver, and Gold have distinct responsibilities.

This improves:

* debugging
* lineage
* testing
* maintainability
* analytical trust

---

## Test external reality

The project does not stop at schema and row-count tests.

Known Premier League facts are used to validate the outputs.

---

# Potential improvements

The current architecture provides a foundation for several future extensions.

## More historical seasons

Extend the pipeline to include additional seasons where compatible data is available.

This would create longer player trend histories and improve multi-season feature engineering.

---

## Match-level data

Add fixture and match-event data.

This would allow the warehouse to evolve from primarily season-level analysis toward:

```text
player × match
```

and potentially support accumulating-snapshot and event-based fact tables.

---

## dbt

Introduce a dbt transformation layer on top of DuckDB.

Potential benefits:

* SQL transformations
* automated model testing
* documentation
* lineage
* reusable analytical models

---

## Orchestration

Introduce Airflow, Dagster, or another orchestration layer for scheduled refreshes.

Potential future workflow:

```text
Schedule
   ↓
Ingest source data
   ↓
Bronze
   ↓
Silver
   ↓
Gold
   ↓
Features
   ↓
ML
   ↓
BI export
   ↓
Data-quality checks
```

---

## Improved ML

Potential ML extensions include:

* player trend-aware outlier detection
* cluster stability analysis
* model evaluation
* feature importance analysis
* player similarity scoring
* position-specific models
* recruitment-oriented scoring

---

## Power BI dashboard

A future version can publish a full dashboard containing:

* player performance
* season trends
* club comparisons
* position analysis
* player archetypes
* hidden-talent candidates
* historical transfer analysis

---

# Reproducibility checklist

A clean local reproduction should look like:

```bash
git clone https://github.com/garethmubaiwa/football-intelligence-platform.git

cd football-intelligence-platform

python3 -m venv .venv

source .venv/bin/activate

pip install -e .

python run_pipeline.py

python export_powerbi.py

python dax/validate_dax_measures.py

python -m pytest tests/ -v
```

Docker reproduction:

```bash
git clone https://github.com/garethmubaiwa/football-intelligence-platform.git

cd football-intelligence-platform

docker compose build

docker compose run --rm pipeline

docker compose run --rm test

docker compose run --rm export

docker compose run --rm dax
```

---

# Author

**Gareth Mubaiwa**

GitHub:

https://github.com/garethmubaiwa

---

# Acknowledgements

Historical Fantasy Premier League data is sourced from:

https://github.com/vaastav/Fantasy-Premier-League

Please refer to the upstream repository for the original dataset and its applicable terms.

---

# License

MIT licence agreement.

The project code and the upstream dataset may be subject to different licensing terms. Review the upstream Fantasy Premier League repository before redistributing source data.
