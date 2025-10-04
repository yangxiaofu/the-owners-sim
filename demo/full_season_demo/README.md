# Full Season Simulation Demo

**Version**: 1.0
**Status**: Production Ready
**Last Updated**: October 3, 2025

A comprehensive NFL season simulation from Week 1 through the Super Bowl and into the offseason, featuring seamless phase transitions, automatic playoff seeding, and complete statistical tracking.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Project Description](#project-description)
3. [Features](#features)
4. [Installation](#installation)
5. [Usage Guide](#usage-guide)
6. [Phase Guide](#phase-guide)
7. [Database Schema](#database-schema)
8. [Query Examples](#query-examples)
9. [Command Reference](#command-reference)
10. [Troubleshooting](#troubleshooting)
11. [Advanced Topics](#advanced-topics)

---

## Quick Start

Get a complete NFL season running in 3 steps:

```bash
# 1. Navigate to demo directory
cd demo/full_season_demo

# 2. Run the simulation
PYTHONPATH=../../src python full_season_sim.py

# 3. Follow the interactive prompts
# - Advance by day or week
# - View standings and playoff bracket
# - Simulate to end or step through manually
```

**Result**: Complete simulation of 285 games (272 regular season + 13 playoff) with full statistics.

---

## Project Description

The **Full Season Simulation Demo** is a unified orchestration system that combines regular season and playoff simulations into a seamless NFL season experience. Unlike separate demos, this provides:

- **Continuous Progression**: September Week 1 → January playoffs → February Super Bowl → Offseason
- **Real Playoff Seeding**: Automatic bracket generation from actual regular season standings
- **Statistical Separation**: Clear distinction between regular season and playoff statistics
- **Dynasty Isolation**: Complete data separation for different user franchises
- **Interactive Control**: Day-by-day or week-by-week advancement with comprehensive status displays

### Architecture

```
FullSeasonController (Orchestrator)
  ├─ Phase 1: REGULAR_SEASON (272 games, Weeks 1-18)
  │  └─ Uses SeasonController
  ├─ Phase 2: PLAYOFFS (13 games, Wild Card → Super Bowl)
  │  └─ Uses PlayoffController with real seeding
  └─ Phase 3: OFFSEASON (Summary, stat leaders, champion)
```

### Key Components

- **`full_season_sim.py`**: Interactive CLI interface with phase-aware menu system
- **`full_season_controller.py`**: Core orchestration logic handling phase transitions
- **`display_utils.py`**: Terminal UI utilities for standings, brackets, and summaries
- **Database**: Unified SQLite database with `season_type` column for stat separation

---

## Features

### Regular Season (Phase 1)
- ✅ 272-game schedule generated automatically
- ✅ Day-by-day or week-by-week simulation
- ✅ Real-time standings updates (division/conference)
- ✅ Playoff picture tracking (Week 10+)
- ✅ Team statistics and performance tracking
- ✅ Interactive viewing of upcoming games

### Playoffs (Phase 2)
- ✅ Automatic seeding calculation from final standings
- ✅ 14-team playoff bracket (7 per conference)
- ✅ Complete playoff simulation:
  - Wild Card Round (6 games)
  - Divisional Round (4 games)
  - Conference Championships (2 games)
  - Super Bowl (1 game)
- ✅ Bracket visualization with live updates
- ✅ Playoff statistics tracking (separate from regular season)

### Offseason (Phase 3)
- ✅ Super Bowl champion display
- ✅ Final regular season standings
- ✅ Stat leaders (regular season and playoffs)
- ✅ Complete season summary
- ✅ Dynasty championship records

### Technical Features
- ✅ Dynasty isolation (multiple users, same database)
- ✅ Stats separation (`season_type`: 'regular_season' | 'playoffs')
- ✅ Continuous calendar (no date jumps)
- ✅ Thread-safe phase transitions
- ✅ Comprehensive error handling
- ✅ Fast simulation (full season < 30 minutes)

---

## Installation

### Prerequisites

```bash
# Python 3.13.5 required
python --version  # Should show 3.13.5

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

### Dependencies

All required dependencies are already installed in the project. The demo uses:

- **Core Simulation**: `src/game_management/`, `src/play_engine/`
- **Season Management**: `src/season/`, `src/calendar/`
- **Playoff System**: `src/playoff_system/`
- **Database**: `src/database/`, SQLite3
- **Team Data**: `src/team_management/`

No additional packages needed.

---

## Usage Guide

### Basic Usage

```bash
# From project root
cd demo/full_season_demo
PYTHONPATH=../../src python full_season_sim.py
```

### First-Time Setup

1. **Create Dynasty** (interactive prompt):
   ```
   Enter dynasty ID: my_first_dynasty
   Enter dynasty name: Road to the Super Bowl
   Enter your name: John Smith
   Select team (optional): 22 (Detroit Lions)
   ```

2. **Choose Simulation Mode**:
   - **Interactive Mode**: Step through day-by-day or week-by-week
   - **Auto Mode**: Simulate entire season automatically

### Interactive Commands

During simulation, you can:

```
Main Menu Options:
  1  - Advance 1 day
  2  - Advance 1 week
  3  - View current standings
  4  - View upcoming games
  5  - View playoff picture (Week 10+)
  6  - View playoff bracket (Playoffs only)
  7  - View season summary (Offseason only)
  8  - Simulate to end
  0  - Quit
```

---

## Phase Guide

### Phase 1: Regular Season

**Duration**: September - January (18 weeks)
**Games**: 272 games (16 games × 17 weeks schedule structure)

**What Happens**:
- Simulation starts Thursday, Week 1
- Games played throughout each week (Thursday, Sunday, Monday)
- Standings updated after each game
- Playoff picture appears starting Week 10

**Key Actions**:
```bash
# View current week standings
Select option: 3

# Advance entire week
Select option: 2

# View playoff picture (Week 10+)
Select option: 5
```

**Phase Transition**:
When all 272 regular season games complete:
```
================================================================================
                   REGULAR SEASON COMPLETE - PLAYOFFS STARTING
================================================================================
Wild Card Weekend: January 18, 2025
Playoff Seeding Calculated from Final Standings

AFC Playoff Teams:
  1. [Team] (14-3)
  2. [Team] (13-4)
  ...

NFC Playoff Teams:
  1. [Team] (15-2)
  2. [Team] (12-5)
  ...

Press Enter to continue...
```

### Phase 2: Playoffs

**Duration**: January - February (4 weeks)
**Games**: 13 games across 4 rounds

**Playoff Structure**:
- **Wild Card** (Week 19): 6 games (3 per conference)
  - #7 @ #2, #6 @ #3, #5 @ #4 (both conferences)
- **Divisional** (Week 20): 4 games (2 per conference)
  - Lowest seed @ #1, other game @ higher remaining seed
- **Conference Championships** (Week 21): 2 games
  - AFC Championship, NFC Championship
- **Super Bowl** (Week 22): 1 game
  - AFC Champion vs NFC Champion

**Key Actions**:
```bash
# View playoff bracket
Select option: 6

# Advance to next playoff round
Select option: 2

# Simulate remaining playoffs
Select option: 8
```

**Phase Transition**:
When Super Bowl completes:
```
================================================================================
                    SEASON COMPLETE - ENTERING OFFSEASON
================================================================================
🏆 Super Bowl Champion: [Team Name]
================================================================================

Final Season Statistics:
  Total Games: 285 (272 regular + 13 playoff)
  Total Days: 154
  Dynasty: [Your Dynasty Name]
  Season: 2024

Press Enter to view season summary...
```

### Phase 3: Offseason

**Duration**: Indefinite (season complete)
**Games**: None (viewing mode only)

**Available Data**:
- Final regular season standings
- Complete playoff bracket with all results
- Super Bowl champion
- Regular season stat leaders
- Playoff stat leaders
- Dynasty championship records

**Key Actions**:
```bash
# View complete season summary
Select option: 7

# Query database for detailed stats
# (See "Query Examples" section below)
```

---

## Database Schema

### Location

```
demo/full_season_demo/data/full_season_[dynasty_id].db
```

### Key Tables

#### 1. games

Stores all game results with season type separation:

```sql
CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    season_type TEXT NOT NULL DEFAULT 'regular_season',  -- NEW FIELD
    game_type TEXT DEFAULT 'regular',
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_score INTEGER NOT NULL,
    away_score INTEGER NOT NULL,
    total_plays INTEGER,
    game_duration_minutes INTEGER,
    overtime_periods INTEGER DEFAULT 0,
    created_at TEXT
);
```

**Season Type Values**:
- `'regular_season'` - Regular season games (Weeks 1-18)
- `'playoffs'` - Playoff games (Weeks 19-22)

**Game Type Values**:
- `'regular'` - Regular season game
- `'wildcard'` - Wild Card playoff game
- `'divisional'` - Divisional playoff game
- `'conference'` - Conference championship
- `'super_bowl'` - Super Bowl

#### 2. player_game_stats

Player statistics with season type separation:

```sql
CREATE TABLE player_game_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    season_type TEXT NOT NULL DEFAULT 'regular_season',  -- NEW FIELD
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    position TEXT NOT NULL,

    -- Passing stats
    passing_yards INTEGER DEFAULT 0,
    passing_tds INTEGER DEFAULT 0,
    passing_completions INTEGER DEFAULT 0,
    passing_attempts INTEGER DEFAULT 0,
    passing_interceptions INTEGER DEFAULT 0,

    -- Rushing stats
    rushing_yards INTEGER DEFAULT 0,
    rushing_tds INTEGER DEFAULT 0,
    rushing_attempts INTEGER DEFAULT 0,

    -- Receiving stats
    receiving_yards INTEGER DEFAULT 0,
    receiving_tds INTEGER DEFAULT 0,
    receptions INTEGER DEFAULT 0,
    targets INTEGER DEFAULT 0,

    -- Defense stats
    tackles_total INTEGER DEFAULT 0,
    sacks REAL DEFAULT 0,
    interceptions INTEGER DEFAULT 0,

    -- Special teams stats
    field_goals_made INTEGER DEFAULT 0,
    field_goals_attempted INTEGER DEFAULT 0,
    extra_points_made INTEGER DEFAULT 0,
    extra_points_attempted INTEGER DEFAULT 0,

    -- Snap counts
    offensive_snaps INTEGER DEFAULT 0,
    defensive_snaps INTEGER DEFAULT 0,
    total_snaps INTEGER DEFAULT 0
);
```

#### 3. standings

Team standings (regular season only):

```sql
CREATE TABLE standings (
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    ties INTEGER DEFAULT 0,
    division_wins INTEGER DEFAULT 0,
    division_losses INTEGER DEFAULT 0,
    conference_wins INTEGER DEFAULT 0,
    conference_losses INTEGER DEFAULT 0,
    PRIMARY KEY (dynasty_id, season, team_id)
);
```

---

## Query Examples

### Regular Season Statistics

#### Regular Season Passing Leaders

```sql
SELECT
    player_name,
    team_id,
    SUM(passing_yards) as total_yards,
    SUM(passing_tds) as tds,
    SUM(passing_attempts) as attempts,
    SUM(passing_completions) as completions,
    ROUND(SUM(passing_completions) * 100.0 / SUM(passing_attempts), 1) as completion_pct
FROM player_game_stats
WHERE dynasty_id = 'my_first_dynasty'
  AND season_type = 'regular_season'
  AND season = 2024
  AND passing_attempts > 0
GROUP BY player_id
ORDER BY total_yards DESC
LIMIT 10;
```

#### Regular Season Rushing Leaders

```sql
SELECT
    player_name,
    team_id,
    SUM(rushing_yards) as total_yards,
    SUM(rushing_tds) as tds,
    SUM(rushing_attempts) as attempts,
    ROUND(SUM(rushing_yards) * 1.0 / SUM(rushing_attempts), 1) as avg_per_carry
FROM player_game_stats
WHERE dynasty_id = 'my_first_dynasty'
  AND season_type = 'regular_season'
  AND season = 2024
  AND rushing_attempts > 0
GROUP BY player_id
ORDER BY total_yards DESC
LIMIT 10;
```

### Playoff Statistics

#### Playoff MVP Candidates

```sql
SELECT
    player_name,
    team_id,
    SUM(passing_yards + rushing_yards + receiving_yards) as total_yards,
    SUM(passing_tds + rushing_tds + receiving_tds) as total_tds,
    COUNT(DISTINCT game_id) as games_played
FROM player_game_stats
WHERE dynasty_id = 'my_first_dynasty'
  AND season_type = 'playoffs'
  AND season = 2024
GROUP BY player_id
HAVING total_yards > 0
ORDER BY total_yards DESC
LIMIT 5;
```

#### Playoff Passing Leaders

```sql
SELECT
    player_name,
    SUM(passing_yards) as playoff_yards,
    SUM(passing_tds) as playoff_tds,
    COUNT(DISTINCT game_id) as playoff_games
FROM player_game_stats
WHERE dynasty_id = 'my_first_dynasty'
  AND season_type = 'playoffs'
  AND season = 2024
  AND passing_attempts > 0
GROUP BY player_id
ORDER BY playoff_yards DESC
LIMIT 10;
```

### Combined Analysis

#### Regular Season vs Playoff Comparison

```sql
-- Compare player's regular season and playoff performance
SELECT
    season_type,
    COUNT(DISTINCT game_id) as games,
    SUM(passing_yards) as pass_yds,
    SUM(passing_tds) as pass_tds,
    SUM(rushing_yards) as rush_yds,
    SUM(rushing_tds) as rush_tds,
    SUM(receiving_yards) as rec_yds,
    SUM(receiving_tds) as rec_tds
FROM player_game_stats
WHERE dynasty_id = 'my_first_dynasty'
  AND player_id = 'QB_22_1'  -- Example: Detroit Lions starting QB
  AND season = 2024
GROUP BY season_type;
```

**Example Output**:
```
season_type      | games | pass_yds | pass_tds | rush_yds | rush_tds
-----------------|-------|----------|----------|----------|----------
regular_season   | 17    | 4500     | 35       | 125      | 2
playoffs         | 3     | 950      | 8        | 45       | 1
```

### Game Results

#### Super Bowl Result

```sql
SELECT
    g.game_id,
    g.home_team_id,
    g.away_team_id,
    g.home_score,
    g.away_score,
    g.overtime_periods,
    g.created_at as game_date
FROM games g
WHERE g.dynasty_id = 'my_first_dynasty'
  AND g.season = 2024
  AND g.game_type = 'super_bowl'
LIMIT 1;
```

#### All Playoff Games

```sql
SELECT
    game_type,
    week,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    CASE
        WHEN home_score > away_score THEN home_team_id
        ELSE away_team_id
    END as winner_id
FROM games
WHERE dynasty_id = 'my_first_dynasty'
  AND season = 2024
  AND season_type = 'playoffs'
ORDER BY week, game_id;
```

### Team Performance

#### Team Playoff Performance by Round

```sql
SELECT
    g.game_type,
    COUNT(*) as games,
    SUM(CASE
        WHEN g.home_team_id = 22 THEN g.home_score
        ELSE g.away_score
    END) as points_for,
    SUM(CASE
        WHEN g.home_team_id = 22 THEN g.away_score
        ELSE g.home_score
    END) as points_against
FROM games g
WHERE g.dynasty_id = 'my_first_dynasty'
  AND g.season = 2024
  AND g.season_type = 'playoffs'
  AND (g.home_team_id = 22 OR g.away_team_id = 22)  -- Team ID 22 = Detroit Lions
GROUP BY g.game_type;
```

---

## Command Reference

### Main Simulation Commands

| Command | Action | Notes |
|---------|--------|-------|
| `1` | Advance 1 day | Simulates all games on current date |
| `2` | Advance 1 week | Simulates next 7 days (typically one game week) |
| `3` | View standings | Shows division/conference standings |
| `4` | View upcoming | Lists next 10 scheduled games |
| `5` | Playoff picture | Available Week 10+, shows playoff positioning |
| `6` | Playoff bracket | Playoffs only, shows current bracket state |
| `7` | Season summary | Offseason only, complete season recap |
| `8` | Simulate to end | Auto-simulates remaining season |
| `0` | Quit | Exit simulation (progress saved) |

### Running the Demo

```bash
# Standard run (from project root)
cd demo/full_season_demo
PYTHONPATH=../../src python full_season_sim.py

# Alternative: Run from project root
PYTHONPATH=src python demo/full_season_demo/full_season_sim.py

# With custom database path
PYTHONPATH=src python demo/full_season_demo/full_season_sim.py --database custom.db

# With specific dynasty
PYTHONPATH=src python demo/full_season_demo/full_season_sim.py --dynasty my_dynasty
```

### Database Queries

```bash
# Open database for manual queries
cd demo/full_season_demo/data
sqlite3 full_season_my_dynasty.db

# Run example queries
.mode column
.headers on

SELECT * FROM games WHERE season_type = 'playoffs' LIMIT 5;
```

---

## Troubleshooting

### Common Issues

#### Issue: "No module named 'src'"

**Cause**: Incorrect PYTHONPATH

**Solution**:
```bash
# Make sure you set PYTHONPATH before running
PYTHONPATH=../../src python full_season_sim.py

# Or from project root:
PYTHONPATH=src python demo/full_season_demo/full_season_sim.py
```

#### Issue: "Database file not found"

**Cause**: Database directory doesn't exist

**Solution**:
```bash
# Create data directory if missing
mkdir -p demo/full_season_demo/data

# Or let the demo create it automatically on first run
```

#### Issue: "Phase transition failed"

**Cause**: Incomplete game data or corrupted standings

**Solution**:
```bash
# Check database for incomplete games
sqlite3 demo/full_season_demo/data/your_dynasty.db

SELECT COUNT(*) FROM games WHERE dynasty_id = 'your_dynasty' AND season_type = 'regular_season';
# Should return 272 when regular season complete

# If corrupted, start new dynasty
```

#### Issue: "Stats showing wrong season_type"

**Cause**: Database migration needed

**Solution**:
```bash
# Run migration script (if provided) or start new dynasty
# The demo automatically sets season_type for new games
```

#### Issue: "Playoff seeding seems random"

**Cause**: Using old playoff demo code

**Solution**:
Verify you're using `full_season_demo/` not `interactive_playoff_sim/`. The full season demo uses real standings-based seeding.

### Performance Issues

#### Slow Simulation

**Optimization**:
```python
# Disable verbose logging for faster simulation
controller = FullSeasonController(
    database_path="data/fast.db",
    dynasty_id="speed_test",
    verbose_logging=False  # Speeds up by ~30%
)
```

#### Database Query Slow

**Solution**: Ensure indexes exist
```sql
-- Check indexes
.indexes games
.indexes player_game_stats

-- Should see:
-- idx_games_season_type
-- idx_stats_season_type
-- (and others)
```

### Debugging

Enable detailed logging:

```bash
# Run with Python logging
PYTHONPATH=../../src python -u full_season_sim.py 2>&1 | tee simulation.log

# Check log for errors
grep -i "error\|exception" simulation.log
```

Check database integrity:

```sql
-- Verify game counts
SELECT season_type, COUNT(*) as count
FROM games
WHERE dynasty_id = 'your_dynasty'
GROUP BY season_type;

-- Expected:
-- regular_season: 272
-- playoffs: 13

-- Verify stats counts match games
SELECT season_type, COUNT(DISTINCT game_id) as games_with_stats
FROM player_game_stats
WHERE dynasty_id = 'your_dynasty'
GROUP BY season_type;
```

---

## Advanced Topics

### Dynasty Isolation

Each dynasty maintains completely separate statistics:

```python
# Create multiple dynasties in same database
dynasty1 = FullSeasonController(
    database_path="shared.db",
    dynasty_id="user1_dynasty"
)

dynasty2 = FullSeasonController(
    database_path="shared.db",
    dynasty_id="user2_dynasty"
)

# Stats never cross-contaminate
# Query always scoped by dynasty_id
```

### Custom Start Dates

```python
from calendar_system.date import Date

# Start season on different date
controller = FullSeasonController(
    database_path="data/custom.db",
    dynasty_id="late_start",
    start_date=Date(2024, 9, 12)  # Week 2 Thursday instead
)
```

### Persistence Control

```python
# Disable database persistence for testing
controller = FullSeasonController(
    database_path=":memory:",  # In-memory database
    dynasty_id="test",
    enable_persistence=False  # No database writes
)

# Useful for:
# - Performance testing
# - Quick simulations
# - Integration tests
```

### Programmatic Access

Use the controller directly without UI:

```python
from full_season_controller import FullSeasonController

# Create controller
controller = FullSeasonController(
    database_path="data/automated.db",
    dynasty_id="batch_sim",
    verbose_logging=False
)

# Simulate entire season programmatically
result = controller.simulate_to_end()

# Access results
print(f"Total games: {result['total_games']}")
print(f"Champion: {result['season_summary']['super_bowl_champion']}")

# Query stats
from database.api import DatabaseAPI
db = DatabaseAPI(controller.database_path)
leaders = db.get_stat_leaders(
    dynasty_id=controller.dynasty_id,
    season=controller.season_year,
    season_type='playoffs'
)
```

### Multi-Season Dynasty

```python
# Simulate multiple seasons (future feature)
for season in range(2024, 2027):
    controller = FullSeasonController(
        database_path=f"data/dynasty_{season}.db",
        dynasty_id="long_dynasty",
        season_year=season
    )
    controller.simulate_to_end()

# Query multi-season stats
# SELECT SUM(wins) FROM standings WHERE dynasty_id = 'long_dynasty'
```

---

## Need Help?

- **Project Documentation**: See `/docs/` directory for detailed architecture
- **Database Schema**: `/docs/schema/database_schema.md`
- **Simulation Workflow**: `/docs/how-to/simulation-workflow.md`
- **Main Project Guide**: `/CLAUDE.md`

---

**Happy Simulating!**
