# Football Data Intelligence Platform

[![CI](https://github.com/garethmubaiwa/football-intelligence-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/garethmubaiwa/football-intelligence-platform/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![DuckDB](https://img.shields.io/badge/warehouse-DuckDB-yellow.svg)](https://duckdb.org/)
[![Docker](https://img.shields.io/badge/container-Docker-2496ED.svg)](https://www.docker.com/)
[![Power BI](https://img.shields.io/badge/BI-Power%20BI-F2C811.svg)](https://powerbi.microsoft.com/)

An end-to-end football data intelligence platform built on **real Premier League data**, demonstrating modern data engineering, analytical warehousing, feature engineering, machine learning, business intelligence, automated testing, containerization, and continuous integration.

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
│ Ingestion     │
│ metadata      │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│    SILVER     │
│               │
│ Schema        │
│ evolution     │
│ Cleaning      │
│ Validation    │
│ Team mapping  │
│ Rejected rows │
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
        ▼
┌───────────────┐
│   FEATURES    │
│               │
│ Per-90 rates  │
│ Value metrics │
│ xG/xA residual│
│ Trends        │
│ Consistency   │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│      ML       │
│               │
│ K-Means       │
│ Archetypes    │
│ Hidden gems   │
│ Overperformers│
└───────┬───────┘
        │
        ▼
┌──────────────────┐
│    POWER BI      │
│                  │
│ CSV exports      │
│ DAX measures     │
│ Dashboards       │
└──────────────────┘

            +

┌──────────────────┐
│     TESTING      │
│                  │
│ Unit tests       │
│ Integration      │
│ Regression       │
│ Smoke tests      │
│ Real-world facts │
└──────────────────┘
```

The important architectural boundary is:

```text
Bronze → Silver → Gold → Features → ML → BI
```

Each layer has a distinct responsibility.

---

# Why this project exists

This project was built to demonstrate practical data engineering and analytics using a real historical dataset rather than a clean toy dataset.

The pipeline deliberately works with data that:

* changes schema over time
* contains season-relative identifiers
* requires historical validation
* needs analytical feature engineering
* supports machine-learning analysis
* must remain reproducible and testable

The project therefore focuses on:

* reproducibility
* schema evolution
* dimensional modelling
* historical accuracy
* automated testing
* feature engineering
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

The source data is processed through the pipeline rather than manually curating analytical outputs.

This keeps the workflow reproducible and makes it possible to rebuild the warehouse from source data.

---

# Real-world data problems discovered

The project intentionally protects against several problems discovered while working with the historical source data.

---

## 1. Schema evolution: `expected_goals`, `expected_assists`, and related xG fields

Expected-goals fields are not available consistently across all five seasons.

A pipeline that assumes those columns exist everywhere would fail when processing older data.

### Solution

The Silver layer checks each season's schema before selecting the expected fields.

If a column is unavailable, it is explicitly created as a null column.

Conceptually:

```text
Column exists
    │
    ├── Yes → use source value
    │
    └── No  → create NULL column
```

The missing value is deliberately **not converted to zero**.

```text
NULL
=
"The source did not provide this measurement."

0
=
"The measurement exists and its value is zero."
```

Those meanings are analytically different.

The Feature Engineering and ML layers preserve this distinction. Older seasons without xG/xA do not receive fabricated overperformance scores.

---

## 2. Schema evolution: `starts`

The `starts` field also differs across historical seasons.

The Silver layer therefore treats missing expected columns consistently rather than hard-coding a separate transformation for every known historical change.

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

This provides a more resilient Silver layer as the historical source schema changes.

---

## 3. FPL team IDs are not stable historical keys

A raw FPL team ID should not automatically be treated as a permanent club identifier across seasons.

The same source ID can represent different clubs in different seasons.

Therefore, this is unsafe as a global historical model:

```text
dim_team
---------
team_id = raw FPL team ID
```

### Solution

The Silver layer resolves the team ID using the **teams.csv belonging to that same season**.

The resolved team name is then used as the canonical club identity for Gold modelling.

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
Gold team dimension
```

This prevents a season-relative source identifier from becoming a permanently incorrect historical key.

---

# Historical transfer regression test

The team-key issue is protected by an automated regression test using a real transfer.

The warehouse correctly represents:

```text
2020-21
Aston Villa

        ↓
    Summer 2021

2021-22
Manchester City
```

for **Jack Grealish**.

This verifies that the season-specific team resolution survives the season boundary correctly.

The regression test is based on a real football event rather than simply checking that rows exist.

---

# Independent historical validation

The project also validates warehouse-derived results against known Premier League outcomes.

The official Premier League records list the following Golden Boot winners for the processed seasons:

| Season  | Golden Boot                     |
| ------- | ------------------------------- |
| 2019-20 | Jamie Vardy                     |
| 2020-21 | Harry Kane                      |
| 2021-22 | Mohamed Salah and Son Heung-min |
| 2022-23 | Erling Haaland                  |
| 2023-24 | Erling Haaland                  |

These are used as external sanity checks rather than being inserted into the analytical dataset.

---

# Architecture

The platform follows a medallion-style architecture followed by feature engineering and machine learning.

```text
Bronze
  ↓
Silver
  ↓
Gold
  ↓
Feature Engineering
  ↓
Machine Learning
  ↓
Power BI / downstream analysis
```

---

# Bronze

The Bronze layer preserves raw source data as downloaded.

### Responsibilities

* source traceability
* raw-data preservation
* reproducibility
* ingestion metadata
* basic arrival/readability checks
* ingestion logging

Bronze does not perform analytical transformations.

Typical location:

```text
data/bronze/<season>/
```

---

# Silver

The Silver layer produces clean, conforming player-season data.

### Responsibilities

* schema validation
* schema evolution handling
* missing-column handling
* season-specific team resolution
* data-quality validation
* duplicate detection
* rejected-row handling
* standardized structure

Primary output:

```text
data/silver/player_season_stats.parquet
```

The Silver dataset represents a consistent player-season structure across the five historical seasons.

---

# Gold

The Gold layer is the analytical warehouse.

The warehouse is stored in:

```text
data/gold/warehouse.duckdb
```

The Gold layer contains a star schema designed for analytical queries, BI, and downstream feature engineering.

---

# Gold warehouse model

## Dimensions

### `dim_player`

One row per unique player code.

Contains the player attributes used by analytical joins.

---

### `dim_team`

One row per canonical club identity.

The team entity is resolved from season-specific source metadata rather than blindly treating the raw FPL team ID as a global historical key.

---

### `dim_season`

One row per football season.

Used for historical filtering and relationships.

---

### `dim_position`

One row per position category:

```text
GK
DEF
MID
FWD
```

---

## Fact table

### `fact_player_season_stats`

The central analytical fact table contains player-season statistics.

Conceptually:

```text
fact_player_season_stats
│
├── fact_id
├── player_key
├── team_key
├── season_key
├── position_key
├── minutes
├── starts
├── goals_scored
├── assists
├── clean_sheets
├── goals_conceded
├── saves
├── bonus
├── bps
├── influence
├── creativity
├── threat
├── ict_index
├── now_cost
├── selected_by_percent
├── total_points
├── points_per_game
├── expected_goals
├── expected_assists
└── expected_goal_involvements
```

The analytical grain is:

```text
one player
+
one season
=
one fact record
```

---

# Feature engineering

Feature Engineering reads from the Gold warehouse and creates the variables required by the ML layer.

It does **not** create fictitious metrics that are unavailable in the source data.

The feature layer produces four main categories.

## 1. Per-90 / rate features

Examples:

```text
goals_per_90
assists_per_90
clean_sheets_per_90
saves_per_90
bps_per_90
influence_per_90
creativity_per_90
threat_per_90
points_per_90
```

These reduce the impact of different playing times when comparing players.

---

## 2. Value and market features

Examples:

```text
cost_millions
points_per_million
```

These are primarily used for hidden-gem analysis rather than playing-style clustering.

---

## 3. Actual-vs-expected features

Where xG/xA is available:

```text
goals_minus_xg
assists_minus_xa
goals_minus_xg_per_90
assists_minus_xa_per_90
```

Positive values indicate actual output above the relevant expected metric.

Where xG/xA is unavailable historically, the corresponding features remain null rather than being fabricated as zero.

---

## 4. Historical trajectory and consistency

Examples:

```text
points_per_game_prev_season
points_per_game_yoy_change
points_per_90_prev_season
points_per_90_yoy_change
points_consistency_std
goals_per_90_trend_slope
assists_per_90_trend_slope
seasons_of_history
```

These features are calculated in chronological player order so that historical features only use information available up to that season.

---

# Machine learning

The ML layer consumes the Feature Engineering output.

It does not recalculate the feature definitions.

The architecture is:

```text
Gold
  ↓
Feature Engineering
  ↓
ML feature DataFrame
  ├── K-Means clustering
  └── hidden-gem / overperformance scoring
```

---

## Player archetype clustering

The project uses **K-Means** to identify position-specific player archetypes.

Clustering is performed separately for:

```text
GK
DEF
MID
FWD
```

This is important because the statistical definition of a useful goalkeeper feature is different from that of a forward.

Players must have at least:

```text
1,000 minutes
```

to participate in clustering.

The model supports:

```text
3 to 5 clusters
```

with:

```text
4 clusters
```

as the default.

The clustering features are based on the engineered features actually available from the Gold warehouse.

Examples include:

### Goalkeepers

```text
saves_per_90
clean_sheets_per_90
goals_conceded_per_90
bps_per_90
```

### Defenders

```text
clean_sheets_per_90
goals_per_90
assists_per_90
bps_per_90
threat_per_90
```

### Midfielders

```text
goals_per_90
assists_per_90
creativity_per_90
threat_per_90
influence_per_90
```

### Forwards

```text
goals_per_90
assists_per_90
threat_per_90
creativity_per_90
bps_per_90
```

Before K-Means, the features are standardized using `StandardScaler`.

---

# Hidden-gem and overperformer detection

The project also produces position-relative analytical scores.

## Hidden gem

A hidden gem is defined as a player combining:

```text
High points per million
+
Low relative ownership
```

The score is calculated using position-relative z-scores.

This prevents a cheap defender from being directly compared with an expensive forward.

---

## Overperformer

Where xG/xA exists, overperformance is measured using:

```text
Goals - xG
Assists - xA
```

The values are converted into position-relative z-scores.

Players who significantly outperform their expected output receive stronger overperformance signals.

For seasons without xG/xA data, no artificial overperformance value is assigned.

---

# Power BI integration

The project provides Power BI-ready analytical outputs.

The intended flow is:

```text
Source
  ↓
Bronze
  ↓
Silver
  ↓
Gold
  ↓
Features / ML
  ↓
Power BI export
  ↓
Dashboard
```

Power BI outputs are written to:

```text
powerbi_export/
```

The BI layer consumes processed analytical outputs rather than raw source files.

---

# DAX

Example DAX measures are documented in:

```text
dax/measures.md
```

The project also includes:

```text
dax/validate_dax_measures.py
```

Run:

```bash
python dax/validate_dax_measures.py
```

The validation script compares BI calculations against independently derived ground-truth results where applicable.

---

# Testing

Testing is a core part of the project.

The suite uses pytest and includes several test levels.

### Unit tests

Test individual functions and rules such as:

* cluster-count validation
* z-score calculations
* Bronze file handling
* Silver validation
* feature calculations

### Integration tests

Validate the interaction between:

```text
Bronze → Silver → Gold → Features → ML
```

### Regression tests

Protect known historical facts and previously fixed problems such as:

* schema evolution
* team-ID reuse
* Jack Grealish's team transition
* Gold referential integrity
* known five-season outputs

### Smoke tests

Verify that the pipeline can be executed successfully at a high level.

### Run the complete suite

The project provides a single entry point:

```bash
python test_pipeline.py
```

Equivalent direct pytest usage:

```bash
python -m pytest tests/ -v
```

The test suite is designed to protect against silent data-quality and modelling regressions.

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
│   ├── conftest.py
│   ├── test_bronze_silver.py
│   ├── test_gold_features.py
│   ├── test_ml.py
│   ├── test_integration.py
│   ├── test_regression_real_data.py
│   └── test_smoke.py
│
├── .dockerignore
├── .gitignore
├── Dockerfile
├── compose.yaml
├── pyproject.toml
├── requirements.txt
├── run_pipeline.py
├── export_powerbi.py
├── test_pipeline.py
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

## 2. Create a virtual environment

### macOS / Linux

```bash
python3 -m venv .venv
```

### Windows

```powershell
py -3.12 -m venv .venv
```

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

## 4. Upgrade pip

```bash
python -m pip install --upgrade pip
```

## 5. Install the project

```bash
pip install -e .
```

The editable installation installs the package from `src/`.

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

## Run the complete pipeline

```bash
python run_pipeline.py
```

This executes the main:

```text
Bronze
→ Silver
→ Gold
→ Feature Engineering
→ ML
```

workflow.

## Export Power BI data

```bash
python export_powerbi.py
```

## Validate DAX measures

```bash
python dax/validate_dax_measures.py
```

## Run the entire test suite

```bash
python test_pipeline.py
```

---

# Expected generated outputs

Generated artifacts are written under the project data directories.

Typical outputs include:

```text
data/
├── raw/
├── bronze/
├── silver/
│   ├── player_season_stats.parquet
│   └── rejected_rows.csv
└── gold/
    └── warehouse.duckdb
```

Feature and ML outputs depend on the current pipeline/orchestration implementation.

Power BI exports are written under:

```text
powerbi_export/
```

Generated analytical data is intentionally excluded from Git by default.

---

# Option 2 — Docker

Docker provides a reproducible runtime environment without requiring manual installation of the Python dependencies.

## Build the project image

```bash
docker compose build
```

## Run the pipeline

```bash
docker compose run --rm pipeline
```

## Run tests

```bash
docker compose run --rm test
```

## Run the Power BI export

```bash
docker compose run --rm export
```

## Run DAX validation

```bash
docker compose run --rm dax
```

Generated files are mounted back into the local project directories so they remain accessible after the container exits.

---

# Docker services

The Compose configuration provides the following one-off services:

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
1. Activate .venv
2. Install with pip install -e .
3. Modify source code
4. Run the pipeline
5. Run python test_pipeline.py
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

python test_pipeline.py

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

The CI workflow is designed to verify the same core project behavior as local development.

Typical CI flow:

```text
Checkout repository
        ↓
Install Python
        ↓
Install project
        ↓
Run pipeline
        ↓
Run tests
        ↓
Export Power BI data
        ↓
Validate DAX
        ↓
PASS / FAIL
```

---

# CI workflow

The workflow is stored in:

```text
.github/workflows/ci.yml
```

The goal is to detect broken transformations, failed tests, invalid warehouse relationships, and other regressions before changes are merged.

---

# Data management

The repository intentionally does not commit large generated datasets or warehouse artifacts.

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

## Preserve raw data

Bronze remains as close as possible to the original source representation.

Transformations happen downstream rather than overwriting the ingestion layer.

---

## Treat schema evolution as normal

Historical datasets rarely remain perfectly consistent.

The pipeline therefore checks source schemas and explicitly handles missing historical columns.

---

## Do not confuse missing with zero

Where the source lacks a metric, the analytical value remains null.

This protects the semantic meaning of the data.

---

## Do not blindly trust source IDs

Source-system identifiers are not automatically business keys.

Team identity is resolved through season-specific source metadata before warehouse modelling.

---

## Define the grain explicitly

The Gold fact table has a player-season grain:

```text
one player
+
one season
=
one fact row
```

This grain is also the basis for deduplication and downstream ML analysis.

---

## Separate feature engineering from modelling

Feature Engineering creates the ML variables.

The ML layer consumes those variables.

```text
Gold
  ↓
Feature Engineering
  ↓
ML
```

This keeps the analytical features reusable and allows the ML algorithm to change without rewriting the feature layer.

---

## Use position-relative analysis

Football roles differ substantially by position.

The clustering and outlier calculations therefore compare players within:

```text
GK
DEF
MID
FWD
```

rather than treating all players as one homogeneous population.

---

## Preserve unavailable information

The project does not fabricate unavailable historical metrics.

For example, if xG/xA is not present in an older season:

```text
xG/xA = NULL
```

rather than:

```text
xG/xA = 0
```

---

## Test against external reality

The project does not rely solely on row counts and schema checks.

Known historical Premier League facts are also used as regression tests.

---

# Potential improvements

The current architecture provides a foundation for several future extensions.

## More historical seasons

Extend the pipeline to compatible additional seasons.

This would provide longer player histories and improve trend-based analysis.

---

## Match-level data

Add fixture and event-level data.

This could introduce a:

```text
player × match
```

fact table and support more detailed event analysis.

---

## More advanced ML

Potential extensions include:

* cluster stability analysis
* silhouette scoring
* alternative clustering algorithms
* Isolation Forest
* player similarity scoring
* predictive performance models
* feature-importance analysis
* position-specific predictive models
* recruitment-oriented scoring

---

## dbt

Introduce dbt transformations on top of DuckDB.

Potential benefits include:

* SQL transformations
* automated model testing
* documentation
* lineage
* reusable analytical models

---

## Orchestration

Introduce Airflow, Dagster, or another orchestration system for scheduled execution.

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

## Power BI dashboard

A future dashboard can provide:

* player performance
* season trends
* club comparisons
* position analysis
* player archetypes
* hidden-talent candidates
* historical transfer analysis

---

# Reproducibility checklist

Local reproduction:

```bash
git clone https://github.com/garethmubaiwa/football-intelligence-platform.git

cd football-intelligence-platform

python3 -m venv .venv

source .venv/bin/activate

pip install -e .

python run_pipeline.py

python export_powerbi.py

python dax/validate_dax_measures.py

python test_pipeline.py
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
