# Season Statistics Aggregator API

**Module**: `src/statistics/season_stats_aggregator.py`
**Version**: 1.0.0
**Author**: The Owners Sim Team

## Overview

The `SeasonStatsAggregator` provides efficient season-level statistics aggregation from game-by-game player statistics. It uses SQLite UPSERT operations to maintain up-to-date season totals with minimal overhead.

## Features

✅ **Efficient UPSERT Operations**: Uses `INSERT ... ON CONFLICT DO UPDATE` for optimal performance
✅ **All Stat Categories**: Passing, rushing, receiving, defense, special teams, offensive line
✅ **Derived Metrics**: Passer rating, yards per carry, catch rate, field goal percentage
✅ **Player Movement Tracking**: Uses `MAX(team_id)` to track most recent team
✅ **Duplicate Prevention**: Groups by `player_id` to avoid duplicate entries
✅ **Transaction Management**: Automatic rollback on errors
✅ **Historical Backfill**: Populate season stats from existing game data

---

## Class: `SeasonStatsAggregator`

### Constructor

```python
def __init__(self, database_path: str = "data/database/nfl_simulation.db")
```

**Parameters**:
- `database_path` (str): Path to SQLite database

**Creates**:
- `player_season_stats` table if it doesn't exist
- 5 indexes for efficient querying

**Example**:
```python
from statistics import SeasonStatsAggregator

aggregator = SeasonStatsAggregator("data/database/nfl_simulation.db")
```

---

## Methods

### `update_after_game()`

Update season stats after a game is completed.

```python
def update_after_game(
    self,
    game_id: str,
    dynasty_id: str,
    season: int,
    season_type: str = "regular_season"
) -> int
```

**Parameters**:
- `game_id` (str): Game identifier to process
- `dynasty_id` (str): Dynasty identifier for isolation
- `season` (int): Season year
- `season_type` (str): `"regular_season"` or `"playoffs"` (default: `"regular_season"`)

**Returns**:
- `int`: Number of player season records updated

**Raises**:
- `sqlite3.Error`: If database operation fails

**Usage**:
```python
# After simulating a game
game_id = "game_2025_week1_chiefs_ravens"
rows_updated = aggregator.update_after_game(
    game_id=game_id,
    dynasty_id="my_dynasty",
    season=2025
)
print(f"Updated {rows_updated} player records")
```

**How It Works**:
1. Queries `player_game_stats` for all players in the specified game
2. Joins with `games` table to filter by season and season_type
3. Aggregates all stats for each player across ALL games in season
4. Uses UPSERT to insert new records or update existing ones
5. Calculates derived metrics (passer rating, yards per carry, etc.)
6. Tracks most recent team using `MAX(team_id)`

---

### `backfill_season()`

Populate season stats for an entire season from scratch.

```python
def backfill_season(
    self,
    dynasty_id: str,
    season: int,
    season_type: str = "regular_season"
) -> int
```

**Parameters**:
- `dynasty_id` (str): Dynasty identifier
- `season` (int): Season year to backfill
- `season_type` (str): `"regular_season"` or `"playoffs"` (default: `"regular_season"`)

**Returns**:
- `int`: Number of player season records created/updated

**Raises**:
- `sqlite3.Error`: If database operation fails

**Usage**:
```python
# Backfill regular season stats for 2025
rows_created = aggregator.backfill_season(
    dynasty_id="my_dynasty",
    season=2025,
    season_type="regular_season"
)
print(f"Created {rows_created} season records")

# Backfill playoff stats separately
playoff_rows = aggregator.backfill_season(
    dynasty_id="my_dynasty",
    season=2025,
    season_type="playoffs"
)
```

**Use Cases**:
- Initial migration to season stats system
- Populating historical data
- Recovering from data corruption
- Adding season stats to existing games

---

### `get_season_leaders()`

Query season stat leaders for a specific category.

```python
def get_season_leaders(
    self,
    dynasty_id: str,
    season: int,
    stat_category: str,
    season_type: str = "regular_season",
    limit: int = 10,
    min_attempts: Optional[int] = None
) -> List[Dict[str, Any]]
```

**Parameters**:
- `dynasty_id` (str): Dynasty identifier
- `season` (int): Season year
- `stat_category` (str): Stat column name (see valid categories below)
- `season_type` (str): `"regular_season"` or `"playoffs"` (default: `"regular_season"`)
- `limit` (int): Number of leaders to return (default: 10)
- `min_attempts` (int, optional): Minimum attempts for rate stats (e.g., 100 pass attempts for passer rating)

**Returns**:
- `List[Dict[str, Any]]`: List of player stat dictionaries sorted by the category

**Raises**:
- `ValueError`: If stat_category is invalid

**Valid Stat Categories**:
```python
# Passing
'passing_yards', 'passing_tds', 'passer_rating', 'completion_percentage'

# Rushing
'rushing_yards', 'rushing_tds', 'yards_per_carry'

# Receiving
'receiving_yards', 'receiving_tds', 'receptions', 'catch_rate'

# Defense
'tackles_total', 'sacks', 'interceptions'

# Special Teams
'field_goals_made', 'field_goal_percentage'
```

**Usage**:
```python
# Get top 10 passing yards leaders
passing_leaders = aggregator.get_season_leaders(
    dynasty_id="my_dynasty",
    season=2025,
    stat_category="passing_yards",
    limit=10
)

for player in passing_leaders:
    print(f"{player['player_name']}: {player['passing_yards']} yards")

# Get top 5 passer ratings (min 100 attempts)
rating_leaders = aggregator.get_season_leaders(
    dynasty_id="my_dynasty",
    season=2025,
    stat_category="passer_rating",
    limit=5,
    min_attempts=100
)

# Get playoff rushing leaders
playoff_rushers = aggregator.get_season_leaders(
    dynasty_id="my_dynasty",
    season=2025,
    stat_category="rushing_yards",
    season_type="playoffs",
    limit=5
)
```

---

## Database Schema

### Table: `player_season_stats`

**Primary Key**: `id` (INTEGER AUTOINCREMENT)
**Unique Constraint**: `(dynasty_id, season, season_type, player_id)`

#### Core Fields

| Column | Type | Description |
|--------|------|-------------|
| `dynasty_id` | TEXT | Dynasty identifier (FK to dynasties) |
| `season` | INTEGER | Season year |
| `season_type` | TEXT | `"regular_season"` or `"playoffs"` |
| `player_id` | TEXT | Player identifier |
| `player_name` | TEXT | Player name (most recent) |
| `position` | TEXT | Position (most recent) |
| `team_id` | INTEGER | Team ID (most recent, for player movement) |
| `games_played` | INTEGER | Number of games played |

#### Passing Stats (Counting)

| Column | Type | Description |
|--------|------|-------------|
| `passing_attempts` | INTEGER | Total pass attempts |
| `passing_completions` | INTEGER | Total completions |
| `passing_yards` | INTEGER | Total passing yards |
| `passing_tds` | INTEGER | Total passing touchdowns |
| `passing_interceptions` | INTEGER | Total interceptions thrown |
| `passing_sacks` | INTEGER | Total sacks taken |
| `passing_sack_yards` | INTEGER | Total sack yards lost |

#### Passing Stats (Derived)

| Column | Type | Formula |
|--------|------|---------|
| `completion_percentage` | REAL | (completions / attempts) × 100 |
| `yards_per_attempt` | REAL | yards / attempts |
| `passer_rating` | REAL | NFL passer rating formula |

#### Rushing Stats (Counting)

| Column | Type | Description |
|--------|------|-------------|
| `rushing_attempts` | INTEGER | Total rush attempts |
| `rushing_yards` | INTEGER | Total rushing yards |
| `rushing_tds` | INTEGER | Total rushing touchdowns |
| `rushing_long` | INTEGER | Longest rush (MAX across games) |
| `rushing_fumbles` | INTEGER | Total rushing fumbles |

#### Rushing Stats (Derived)

| Column | Type | Formula |
|--------|------|---------|
| `yards_per_carry` | REAL | rushing_yards / rushing_attempts |
| `rushing_yards_per_game` | REAL | rushing_yards / games_played |

#### Receiving Stats (Counting)

| Column | Type | Description |
|--------|------|-------------|
| `targets` | INTEGER | Total targets |
| `receptions` | INTEGER | Total receptions |
| `receiving_yards` | INTEGER | Total receiving yards |
| `receiving_tds` | INTEGER | Total receiving touchdowns |
| `receiving_long` | INTEGER | Longest reception (MAX) |
| `receiving_drops` | INTEGER | Total drops |

#### Receiving Stats (Derived)

| Column | Type | Formula |
|--------|------|---------|
| `catch_rate` | REAL | (receptions / targets) × 100 |
| `yards_per_reception` | REAL | receiving_yards / receptions |
| `yards_per_target` | REAL | receiving_yards / targets |
| `receiving_yards_per_game` | REAL | receiving_yards / games_played |

#### Defensive Stats

| Column | Type | Description |
|--------|------|-------------|
| `tackles_total` | INTEGER | Total tackles |
| `tackles_solo` | INTEGER | Solo tackles |
| `tackles_assist` | INTEGER | Assisted tackles |
| `sacks` | REAL | Total sacks |
| `interceptions` | INTEGER | Total interceptions |
| `forced_fumbles` | INTEGER | Total forced fumbles |
| `fumbles_recovered` | INTEGER | Total fumbles recovered |
| `passes_defended` | INTEGER | Total passes defended |
| `tackles_per_game` | REAL | tackles_total / games_played |
| `sacks_per_game` | REAL | sacks / games_played |

#### Special Teams Stats

| Column | Type | Description |
|--------|------|-------------|
| `field_goals_made` | INTEGER | Total field goals made |
| `field_goals_attempted` | INTEGER | Total field goals attempted |
| `extra_points_made` | INTEGER | Total extra points made |
| `extra_points_attempted` | INTEGER | Total extra points attempted |
| `punts` | INTEGER | Total punts |
| `punt_yards` | INTEGER | Total punt yards |
| `field_goal_percentage` | REAL | (FG made / FG attempted) × 100 |
| `extra_point_percentage` | REAL | (XP made / XP attempted) × 100 |
| `punt_average` | REAL | punt_yards / punts |

#### Offensive Line Stats

| Column | Type | Description |
|--------|------|-------------|
| `pancakes` | INTEGER | Total pancake blocks |
| `sacks_allowed` | INTEGER | Total sacks allowed |
| `hurries_allowed` | INTEGER | Total hurries allowed |
| `pressures_allowed` | INTEGER | Total pressures allowed |
| `missed_assignments` | INTEGER | Total missed assignments |
| `holding_penalties` | INTEGER | Total holding penalties |
| `false_start_penalties` | INTEGER | Total false start penalties |
| `downfield_blocks` | INTEGER | Total downfield blocks |
| `double_team_blocks` | INTEGER | Total double team blocks |
| `chip_blocks` | INTEGER | Total chip blocks |
| `run_blocking_grade` | REAL | Average run blocking grade |
| `pass_blocking_efficiency` | REAL | Average pass blocking efficiency |

#### Other Stats

| Column | Type | Description |
|--------|------|-------------|
| `snap_counts_offense` | INTEGER | Total offensive snaps |
| `snap_counts_defense` | INTEGER | Total defensive snaps |
| `snap_counts_special_teams` | INTEGER | Total special teams snaps |
| `total_snaps` | INTEGER | Sum of all snap types |
| `fantasy_points` | REAL | Total fantasy points |
| `last_updated` | TIMESTAMP | Last update timestamp |

---

## Indexes

Efficient querying is supported by these indexes:

1. **`idx_season_stats_dynasty`**: `(dynasty_id, season)`
   - Fast dynasty/season filtering
2. **`idx_season_stats_player`**: `(player_id, dynasty_id)`
   - Player history across seasons
3. **`idx_season_stats_team`**: `(team_id, season)`
   - Team roster queries
4. **`idx_season_stats_position`**: `(position, season)`
   - Position group analysis
5. **`idx_season_stats_season_type`**: `(dynasty_id, season, season_type)`
   - Regular season vs playoffs separation

---

## Integration Examples

### Example 1: Game Simulation Integration

```python
from game_management import FullGameSimulator
from statistics import SeasonStatsAggregator

# Initialize
simulator = FullGameSimulator(away_team_id=1, home_team_id=2)
aggregator = SeasonStatsAggregator()

# Simulate game
game_result = simulator.simulate_game()

# Update season stats
aggregator.update_after_game(
    game_id=game_result['game_id'],
    dynasty_id="my_dynasty",
    season=2025
)
```

### Example 2: Season Simulation Integration

```python
from calendar import CalendarManager
from statistics import SeasonStatsAggregator

calendar = CalendarManager(dynasty_id="my_dynasty")
aggregator = SeasonStatsAggregator()

# Simulate week
week_results = calendar.simulate_week(week_number=1)

# Update stats for all games
for game in week_results:
    aggregator.update_after_game(
        game_id=game['game_id'],
        dynasty_id="my_dynasty",
        season=2025
    )
```

### Example 3: Leaderboard Display

```python
from statistics import SeasonStatsAggregator

aggregator = SeasonStatsAggregator()

# Get multiple leaderboards
passing = aggregator.get_season_leaders(
    dynasty_id="my_dynasty",
    season=2025,
    stat_category="passing_yards",
    limit=10
)

rushing = aggregator.get_season_leaders(
    dynasty_id="my_dynasty",
    season=2025,
    stat_category="rushing_yards",
    limit=10
)

receiving = aggregator.get_season_leaders(
    dynasty_id="my_dynasty",
    season=2025,
    stat_category="receiving_yards",
    limit=10
)

# Display
print("PASSING LEADERS")
for player in passing:
    print(f"{player['player_name']:30} {player['passing_yards']:>5} yards")

print("\nRUSHING LEADERS")
for player in rushing:
    print(f"{player['player_name']:30} {player['rushing_yards']:>5} yards")

print("\nRECEIVING LEADERS")
for player in receiving:
    print(f"{player['player_name']:30} {player['receiving_yards']:>5} yards")
```

### Example 4: Historical Data Migration

```python
from statistics import SeasonStatsAggregator
import sqlite3

aggregator = SeasonStatsAggregator()

# Get all dynasty/season combinations
conn = sqlite3.connect("data/database/nfl_simulation.db")
cursor = conn.cursor()
cursor.execute("""
    SELECT DISTINCT dynasty_id, season
    FROM games
    ORDER BY season
""")

combinations = cursor.fetchall()
conn.close()

# Backfill all seasons
for dynasty_id, season in combinations:
    print(f"Backfilling {dynasty_id} - {season}...")

    # Regular season
    regular_count = aggregator.backfill_season(
        dynasty_id=dynasty_id,
        season=season,
        season_type="regular_season"
    )
    print(f"  Regular season: {regular_count} records")

    # Playoffs
    playoff_count = aggregator.backfill_season(
        dynasty_id=dynasty_id,
        season=season,
        season_type="playoffs"
    )
    print(f"  Playoffs: {playoff_count} records")

print("Migration complete!")
```

---

## Performance Considerations

### UPSERT Efficiency

The aggregator uses SQLite's UPSERT for optimal performance:
- **Single query** aggregates all stats for players in a game
- **No additional queries** to check if record exists
- **Atomic operation** ensures consistency
- **Minimal locking** for concurrent access

### Benchmarks

Typical performance on modern hardware:
- `update_after_game()`: ~10-50ms (depends on players in game)
- `backfill_season()`: ~200-500ms (17 weeks × 32 teams)
- `get_season_leaders()`: ~5-10ms (indexed queries)

### Best Practices

1. **Call after each game**: Use `update_after_game()` for incremental updates
2. **Batch backfills**: Use `backfill_season()` for historical data migration
3. **Index usage**: Always filter by `dynasty_id` first for optimal performance
4. **Transaction handling**: Use context managers (`with` statements) for safety

---

## Error Handling

### Common Errors

**`sqlite3.Error`**: Database operation failed
```python
try:
    aggregator.update_after_game(game_id, dynasty_id, season)
except sqlite3.Error as e:
    logger.error(f"Database error: {e}")
    # Handle error (retry, alert user, etc.)
```

**`ValueError`**: Invalid stat category
```python
try:
    leaders = aggregator.get_season_leaders(
        dynasty_id="test",
        season=2025,
        stat_category="invalid_stat"
    )
except ValueError as e:
    print(f"Invalid stat category: {e}")
```

### Transaction Safety

All methods use automatic transactions:
- **Commit on success**: Changes are saved
- **Rollback on error**: Database remains consistent
- **No partial updates**: All-or-nothing guarantee

---

## Logging

The aggregator uses Python's `logging` module:

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Aggregator will log:
# - Table creation/verification
# - Update operations (rows affected)
# - Backfill operations (records created)
# - Errors with details
```

**Example log output**:
```
INFO:SeasonStatsAggregator:player_season_stats table and indexes created/verified
INFO:SeasonStatsAggregator:Updated 75 player season stats for game game_2025_week1 (dynasty: my_dynasty, season: 2025, type: regular_season)
INFO:SeasonStatsAggregator:Backfilled 2290 player season stats for dynasty my_dynasty, season 2025, type regular_season
```

---

## Testing

### Unit Tests

Run the test script:
```bash
PYTHONPATH=src python test_season_aggregator.py
```

### Manual Testing

```python
from statistics import SeasonStatsAggregator

# Initialize
aggregator = SeasonStatsAggregator(":memory:")  # Use in-memory DB for testing

# Test backfill
rows = aggregator.backfill_season("test_dynasty", 2025)
assert rows > 0

# Test leaders
leaders = aggregator.get_season_leaders("test_dynasty", 2025, "passing_yards")
assert len(leaders) > 0
```

---

## FAQ

**Q: How often should I call `update_after_game()`?**
A: After each game simulation. It's designed for incremental updates.

**Q: When should I use `backfill_season()` instead?**
A: For initial setup, historical data migration, or recovery from corruption.

**Q: Does it handle player trades mid-season?**
A: Yes! It uses `MAX(team_id)` to track the most recent team.

**Q: Can I query both regular season and playoff stats?**
A: Yes, use the `season_type` parameter. Each season type is tracked separately.

**Q: What if a game has no stats (simulation error)?**
A: The method will still succeed but update 0 records. Check logs for details.

**Q: How do I delete season stats?**
A: Use SQL: `DELETE FROM player_season_stats WHERE dynasty_id = ? AND season = ?`

**Q: Can multiple processes update simultaneously?**
A: SQLite handles basic concurrency, but for heavy loads consider WAL mode:
```python
conn = sqlite3.connect(db_path)
conn.execute("PRAGMA journal_mode=WAL")
```

---

## Version History

### 1.0.0 (2025-10-15)
- Initial release
- Full stat category support
- UPSERT-based aggregation
- Historical backfill
- Season leaders queries
- Comprehensive documentation

---

## See Also

- **Database Schema**: `docs/schema/database_schema.md`
- **Statistics API**: `src/database/api.py`
- **Player Stats Fields**: `src/constants/player_stats_fields.py`
- **Game Simulation**: `src/game_management/full_game_simulator.py`
