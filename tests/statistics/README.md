# Statistics API Test Fixtures

Comprehensive pytest fixtures for testing the Statistics API with real database integration.

## Overview

This module provides shared test fixtures for validating statistical queries, leaderboards, and player performance metrics in The Owner's Sim NFL simulation.

## Fixtures

### Database Fixtures

#### `in_memory_db`
Creates an in-memory SQLite database with complete schema and 75 sample players.

**Schema:**
- Table: `player_game_stats`
- Columns: All stats fields matching `docs/schema/database_schema.md`
- Primary Key: `(dynasty_id, game_id, player_id)`

**Sample Data:**
- 20 QBs with realistic passing stats
- 20 RBs with rushing/receiving stats
- 20 WRs/TEs with receiving stats
- 10 Defensive players (LB, DE, CB, S) with tackles/sacks/INTs
- 5 Kickers with FG/XP stats

**Usage:**
```python
def test_query(in_memory_db):
    cursor = in_memory_db.cursor()
    cursor.execute("SELECT * FROM player_game_stats WHERE position = 'QB'")
    # ... perform assertions
```

### Position-Specific Fixtures

#### `sample_qb_stats`
Returns list of 20 QB stat dictionaries sorted by passing yards (descending).

**Fields:**
- player_id, player_name, team_id, position
- passing_yards, passing_tds, passing_completions, passing_attempts, passing_interceptions
- rushing_yards, rushing_tds

**Top 3 QBs:**
1. Perfect QB - 400 yards, 4 TDs, 20/20 completions (158.3 rating)
2. Patrick Mahomes - 384 yards, 5 TDs (122.3 rating)
3. Aaron Rodgers 2011 - 343 yards, 4 TDs (139.9 rating)

**Usage:**
```python
def test_passer_rating(sample_qb_stats):
    for qb in sample_qb_stats:
        rating = calculate_passer_rating(qb)
        assert 0 <= rating <= 158.3
```

#### `sample_rb_stats`
Returns list of 20 RB stat dictionaries sorted by rushing yards (descending).

**Fields:**
- player_id, player_name, team_id, position
- rushing_yards, rushing_tds, rushing_attempts
- receiving_yards, receiving_tds, receptions

**Top 3 RBs:**
1. Derrick Henry - 165 rush yards, 2 TDs
2. Christian McCaffrey - 142 rush yards, 85 rec yards (dual-threat)
3. Nick Chubb - 128 rush yards

**Usage:**
```python
def test_rushing_leaders(sample_rb_stats):
    top_rusher = sample_rb_stats[0]
    assert top_rusher['player_name'] == 'Derrick Henry'
    assert top_rusher['rushing_yards'] == 165
```

#### `sample_wr_stats`
Returns list of 20 WR/TE stat dictionaries sorted by receiving yards (descending).

**Fields:**
- player_id, player_name, team_id, position
- receiving_yards, receiving_tds, receptions, targets

**Top 3 WRs:**
1. Tyreek Hill - 152 yards, 10 receptions
2. CeeDee Lamb - 142 yards, 11 receptions, 2 TDs
3. Justin Jefferson - 128 yards

**Usage:**
```python
def test_receiving_leaders(sample_wr_stats):
    top_receiver = sample_wr_stats[0]
    assert top_receiver['player_name'] == 'Tyreek Hill'
    assert top_receiver['receiving_yards'] == 152
```

#### `sample_all_stats`
Returns list of all 75 player stat dictionaries (all positions).

**Fields:** All statistical fields from schema

**Usage:**
```python
def test_all_positions(sample_all_stats):
    positions = {p['position'] for p in sample_all_stats}
    assert 'QB' in positions
    assert 'RB' in positions
    assert 'WR' in positions
```

### Reference Data Fixtures

#### `known_passer_ratings`
Dictionary mapping 20 QB names to their expected NFL passer ratings.

**Rating Range:** 42.3 (Bryce Young) to 158.3 (Perfect QB)

**Notable Ratings:**
- Perfect QB: 158.3 (perfect rating)
- Aaron Rodgers 2011: 139.9
- Patrick Mahomes: 122.3
- Tua Tagovailoa: 103.4
- Bryce Young: 42.3 (lowest)

**Usage:**
```python
def test_passer_rating_calculation(sample_qb_stats, known_passer_ratings):
    for qb in sample_qb_stats:
        calculated = calculate_passer_rating(qb)
        expected = known_passer_ratings[qb['player_name']]
        assert abs(calculated - expected) < 0.5  # Allow small rounding differences
```

#### `sample_teams`
List of 32 NFL teams with (team_id, team_name, conference, division) tuples.

**Coverage:**
- 16 AFC teams (4 per division)
- 16 NFC teams (4 per division)
- All 8 divisions represented

**Usage:**
```python
def test_conference_stats(sample_all_stats, sample_teams):
    afc_teams = {t[0] for t in sample_teams if t[2] == 'AFC'}
    afc_players = [p for p in sample_all_stats if p['team_id'] in afc_teams]
    # ... perform conference-specific assertions
```

## Test Coverage

The fixtures are validated by 13 comprehensive tests in `test_conftest.py`:

1. **Schema Validation**
   - `test_in_memory_db_schema` - Verifies table and column structure
   - `test_in_memory_db_row_count` - Validates 75 total rows (20 QB, 20 RB, 20 WR/TE, 10 DEF, 5 K)

2. **Position-Specific Tests**
   - `test_sample_qb_stats_fixture` - QB data structure and sorting
   - `test_sample_rb_stats_fixture` - RB data structure and sorting
   - `test_sample_wr_stats_fixture` - WR/TE data structure and sorting
   - `test_sample_all_stats_fixture` - All positions combined

3. **Reference Data Tests**
   - `test_known_passer_ratings_fixture` - Passer rating validation
   - `test_sample_teams_fixture` - NFL team structure

4. **Specialized Position Tests**
   - `test_defensive_stats_in_db` - Defensive player stats (tackles, sacks, INTs)
   - `test_kicker_stats_in_db` - Kicker stats (FG, XP)

5. **Data Integrity Tests**
   - `test_dynasty_id_consistency` - All records use 'test_dynasty'
   - `test_season_type_consistency` - All records use 'regular_season'
   - `test_fixture_integration` - Cross-fixture validation

## Running Tests

```bash
# Run all fixture tests
PYTHONPATH=src python -m pytest tests/statistics/test_conftest.py -v

# Run specific test
PYTHONPATH=src python -m pytest tests/statistics/test_conftest.py::test_sample_qb_stats_fixture -v

# Run with coverage
PYTHONPATH=src python -m pytest tests/statistics/test_conftest.py --cov=tests.statistics.conftest
```

## Usage in Other Tests

These fixtures are automatically available to all tests in `tests/statistics/`:

```python
# tests/statistics/test_leaderboards.py
def test_qb_leaderboard(sample_qb_stats):
    leaderboard = generate_leaderboard(sample_qb_stats, stat='passing_yards')
    assert leaderboard[0]['player_name'] == 'Perfect QB'
    assert leaderboard[0]['passing_yards'] == 400
```

```python
# tests/statistics/test_stats_api.py
def test_get_passing_leaders(in_memory_db):
    api = StatsAPI(in_memory_db)
    leaders = api.get_passing_leaders(limit=10)
    assert len(leaders) == 10
    assert leaders[0]['player_name'] == 'Perfect QB'
```

## Dynasty Context

All fixtures use `dynasty_id = 'test_dynasty'` for isolation. This ensures:
- No interference with production data
- Consistent test results
- Easy cleanup (in-memory database)

## Sample Data Details

### Quarterback Distribution
- 4 Elite QBs (120+ rating)
- 8 Good/Average QBs (75-100 rating)
- 8 Below Average/Backup QBs (<75 rating)
- Mix of pocket passers and dual-threat QBs (Josh Allen, Lamar Jackson, Jalen Hurts have rushing TDs)

### Running Back Distribution
- 4 Elite RBs (120+ yards)
- 8 Good RBs (80-110 yards)
- 8 Average/Backup RBs (<80 yards)
- Mix of pure rushers and receiving backs (CMC, Saquon have significant receiving yards)

### Wide Receiver Distribution
- 4 Elite WRs (120+ yards)
- 8 Good WRs/TEs (65-100 yards)
- 8 Average TEs (<65 yards)
- Includes both volume receivers and big-play threats

### Defensive Players
- 3 Elite pass rushers (2+ sacks)
- 3 Good linebackers (10+ tackles)
- 4 Elite DBs (1-2 interceptions)

### Kickers
- 5 kickers with varying accuracy (2/3 to 4/4 FG)
- Mix of strong and average special teams units

## Notes

- All stats are single-game performances (not season totals)
- Stats are realistic but simplified for testing
- Known passer ratings calculated using official NFL formula
- Database uses `:memory:` for fast test execution
- Fixtures are recreated for each test function (isolation guaranteed)

## Future Enhancements

Potential additions for comprehensive testing:
- Multi-game season stats (aggregation testing)
- Playoff vs regular season stats
- Historical season data for trend analysis
- Team-level defensive stats
- Special teams stats beyond kickers (punters, returners)
