# Statistics Module

This module provides season-level statistics aggregation and analysis for player performance tracking.

## Contents

- **`season_stats_aggregator.py`**: Main aggregation engine using SQLite UPSERT
- **`aggregations.py`**: Statistical aggregation utilities
- **`filters.py`**: Data filtering and selection
- **`leaderboards.py`**: Leaderboard generation and ranking
- **`models.py`**: Data models for statistics
- **`rankings.py`**: Player and team ranking systems
- **`stats_api.py`**: Statistics API layer

## Quick Start

### Installation

The module is automatically available when you install the project:

```bash
pip install -r requirements.txt
```

### Basic Usage

```python
from statistics import SeasonStatsAggregator

# Initialize
aggregator = SeasonStatsAggregator()

# Update after each game
aggregator.update_after_game(
    game_id="game_2025_week1_chiefs_ravens",
    dynasty_id="my_dynasty",
    season=2025
)

# Get passing leaders
leaders = aggregator.get_season_leaders(
    dynasty_id="my_dynasty",
    season=2025,
    stat_category="passing_yards",
    limit=10
)

for player in leaders:
    print(f"{player['player_name']}: {player['passing_yards']} yards")
```

### Backfill Historical Data

```python
# Populate season stats for an entire season
aggregator.backfill_season(
    dynasty_id="my_dynasty",
    season=2025,
    season_type="regular_season"
)
```

## Key Features

✅ **Efficient UPSERT operations** - Minimal database overhead
✅ **All stat categories** - Passing, rushing, receiving, defense, special teams, OL
✅ **Derived metrics** - Passer rating, yards per carry, catch rate, etc.
✅ **Player movement tracking** - Handles mid-season trades
✅ **Season type separation** - Regular season vs playoffs
✅ **Dynasty isolation** - Complete data separation

## Database Table

The module creates a `player_season_stats` table with:
- **70+ stat columns** covering all position groups
- **Derived metrics** automatically calculated
- **5 indexes** for efficient querying
- **Unique constraint** on (dynasty_id, season, season_type, player_id)

## Documentation

Full API documentation: [`docs/api/season_stats_aggregator.md`](../../docs/archive/api/season_stats_aggregator.md)

## Testing

Run the test suite:

```bash
PYTHONPATH=src python test_season_aggregator.py
```

## Performance

Typical benchmarks on modern hardware:
- `update_after_game()`: 10-50ms per game
- `backfill_season()`: 200-500ms per season
- `get_season_leaders()`: 5-10ms per query

## Integration Examples

### With Game Simulator

```python
from game_management import FullGameSimulator
from statistics import SeasonStatsAggregator

simulator = FullGameSimulator(away_team_id=1, home_team_id=2)
aggregator = SeasonStatsAggregator()

# Simulate and aggregate
result = simulator.simulate_game()
aggregator.update_after_game(
    game_id=result['game_id'],
    dynasty_id="my_dynasty",
    season=2025
)
```

### With Season Simulation

```python
from calendar import CalendarManager
from statistics import SeasonStatsAggregator

calendar = CalendarManager(dynasty_id="my_dynasty")
aggregator = SeasonStatsAggregator()

# Simulate week and aggregate all games
week_results = calendar.simulate_week(week_number=1)
for game in week_results:
    aggregator.update_after_game(
        game_id=game['game_id'],
        dynasty_id="my_dynasty",
        season=2025
    )
```

## Support

For questions or issues:
1. Check the full documentation in `docs/api/season_stats_aggregator.md`
2. Review test examples in `test_season_aggregator.py`
3. See database schema in `docs/schema/database_schema.md`
