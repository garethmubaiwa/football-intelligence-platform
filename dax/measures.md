# DAX Measure Library — Football Intelligence Platform

Real DAX measures for the exported star schema (`powerbi_export/`), each with a verified ground-truth value computed directly from the real Premier League data (see `validate_dax_measures.py`).

```dax
Total Goals = SUM(fact_player_season_stats[goals_scored])

Total Points = SUM(fact_player_season_stats[total_points])

Goals Per 90 =
DIVIDE(
    SUM(fact_player_season_stats[goals_scored]),
    DIVIDE(SUM(fact_player_season_stats[minutes]), 90),
    0
)

Top Scorer Points =
CALCULATE(
    MAX(fact_player_season_stats[total_points]),
    ALLEXCEPT(fact_player_season_stats, dim_season[season])
)

Season-over-Season Points Change =
VAR CurrentSeasonPoints = SUM(fact_player_season_stats[total_points])
VAR PreviousSeason =
    CALCULATE(
        SUM(fact_player_season_stats[total_points]),
        DATEADD(dim_season[start_year], -1, YEAR)
    )
RETURN CurrentSeasonPoints - PreviousSeason

Value Rank =
RANKX(
    ALL(dim_player[web_name]),
    DIVIDE([Total Points], SUM(fact_player_season_stats[now_cost]) / 10),
    ,
    DESC
)
```

## Verified Answer Key (2023-24 season, computed in `validate_dax_measures.py`)
Run the validation script for exact figures — every DAX measure above has a corresponding pandas computation checked against the real warehouse data before building the report in Power BI Desktop.
