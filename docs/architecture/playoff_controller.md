# Playoff Controller Architecture

## Overview

The **PlayoffController** is the central orchestration component for NFL playoff simulation. It coordinates calendar advancement, playoff bracket generation, game execution, and round-by-round progression through the entire playoff tournament (Wild Card → Divisional → Conference → Super Bowl).

### Purpose

- **Orchestrate playoff simulation**: Manage the complete playoff workflow from seeding to Super Bowl
- **Coordinate system components**: Bridge calendar, events, simulation, and playoff-specific logic
- **Track playoff state**: Maintain bracket state, completed games, and round progression
- **Provide flexible control**: Support day-by-day, week-by-week, or full playoff simulation

### Core Responsibilities

1. **Playoff Bracket Management**: Generate initial brackets with seeding, schedule subsequent rounds based on results
2. **Calendar Advancement**: Control simulation pace (daily, weekly, or complete playoffs)
3. **Game Execution**: Coordinate with SimulationExecutor to run playoff games
4. **Round Progression**: Detect round completion and automatically schedule next round
5. **State Tracking**: Monitor current round, completed games, and playoff progress
6. **Dynasty Isolation**: Ensure playoff data is properly separated by dynasty context

## Architecture

### Component Dependencies

```
PlayoffController
├── CalendarComponent          # Date/time management
├── EventDatabaseAPI           # Event storage/retrieval
├── SimulationExecutor         # Game execution orchestration
├── PlayoffSeeder              # Playoff seeding calculation
├── PlayoffManager             # Bracket generation
├── PlayoffScheduler           # GameEvent creation
└── DatabaseConnection         # Dynasty management
```

### Data Flow

```
1. Initialization
   ┌─────────────────────┐
   │ Generate Seeding    │ (Random or from standings)
   └──────────┬──────────┘
              ↓
   ┌─────────────────────┐
   │ Create Wild Card    │
   │ Bracket & Schedule  │
   └──────────┬──────────┘
              ↓
   ┌─────────────────────┐
   │ Store Events in DB  │
   └─────────────────────┘

2. Game Simulation
   ┌─────────────────────┐
   │ Advance Calendar    │
   └──────────┬──────────┘
              ↓
   ┌─────────────────────┐
   │ Simulate Day's      │
   │ Scheduled Games     │
   └──────────┬──────────┘
              ↓
   ┌─────────────────────┐
   │ Track Completed     │
   │ Games by Round      │
   └──────────┬──────────┘
              ↓
   ┌─────────────────────┐
   │ Check Round         │
   │ Completion          │
   └─────────────────────┘

3. Round Progression
   ┌─────────────────────┐
   │ Round Complete?     │
   └──────────┬──────────┘
              ↓
   ┌─────────────────────┐
   │ Generate Next       │
   │ Bracket from        │
   │ Winners             │
   └──────────┬──────────┘
              ↓
   ┌─────────────────────┐
   │ Schedule Next       │
   │ Round Games         │
   └──────────┬──────────┘
              ↓
   ┌─────────────────────┐
   │ Continue Simulation │
   └─────────────────────┘
```

### Round Progression Logic

The controller follows the standard NFL playoff bracket:

```
Wild Card Round (6 games)
├── AFC: #2 vs #7, #3 vs #6, #4 vs #5
└── NFC: #2 vs #7, #3 vs #6, #4 vs #5
    ↓
Divisional Round (4 games)
├── AFC: #1 vs lowest seed, higher seed vs lower seed
└── NFC: #1 vs lowest seed, higher seed vs lower seed
    ↓
Conference Championships (2 games)
├── AFC Championship
└── NFC Championship
    ↓
Super Bowl (1 game)
└── AFC Champion vs NFC Champion
```

**Key Scheduling Constraints**:
- Wild Card: Day 0 (typically Jan 11)
- Divisional: Day 7 (Wild Card + 7 days)
- Conference: Day 14 (Wild Card + 14 days)
- Super Bowl: Day 28 (Wild Card + 28 days)

## Public API

### Constructor

```python
controller = PlayoffController(
    database_path: str,
    dynasty_id: str = "default",
    season_year: int = 2024,
    wild_card_start_date: Optional[Date] = None,
    enable_persistence: bool = True,
    verbose_logging: bool = True
)
```

**Parameters**:
- `database_path`: Path to SQLite database for event and game storage
- `dynasty_id`: Dynasty context for data isolation (allows multiple concurrent playoffs)
- `season_year`: NFL season year (e.g., 2024 for 2024-25 season)
- `wild_card_start_date`: Starting date for Wild Card round (defaults to Jan 11, 2025)
- `enable_persistence`: Whether to persist game results to database
- `verbose_logging`: Whether to print detailed progress messages

### Core Methods

#### 1. Daily Advancement

```python
result = controller.advance_day()
```

Simulates games scheduled for the current date, then advances calendar by 1 day.

**Returns**:
```python
{
    "date": "2025-01-11",
    "games_played": 2,
    "results": [
        {
            "game_id": "playoff_dynasty_2024_wild_card_1",
            "home_team_id": 14,
            "away_team_id": 28,
            "home_score": 24,
            "away_score": 21,
            "winner_id": 14,
            "success": True
        },
        # ... more games
    ],
    "current_round": "wild_card",
    "round_complete": False,
    "success": True,
    "errors": []
}
```

#### 2. Weekly Advancement

```python
result = controller.advance_week()
```

Advances calendar by 7 days, simulating all scheduled games.

**Returns**:
```python
{
    "start_date": "2025-01-11",
    "end_date": "2025-01-18",
    "total_games_played": 6,
    "daily_results": [
        # Array of daily results (7 entries)
    ],
    "current_round": "wild_card",
    "rounds_completed": ["wild_card"],
    "success": True
}
```

#### 3. Round-by-Round Advancement

```python
result = controller.advance_to_next_round()
```

Advances calendar until the active round completes, then schedules the next round.

**Important**: This completes **only the current round**. After completion, the next round is scheduled but **not simulated**. Call this method again to simulate the next round.

**Returns**:
```python
{
    "completed_round": "wild_card",
    "round_name": "wild_card",
    "games_played": 6,
    "days_simulated": 3,
    "results": [
        # Array of completed games
    ],
    "next_round": "divisional",
    "next_round_scheduled": True,
    "success": True
}
```

#### 4. Simulate to Super Bowl

```python
result = controller.simulate_to_super_bowl()
```

Simulates all remaining playoff rounds until Super Bowl completes.

**Returns**:
```python
{
    "total_games": 13,
    "total_days": 35,
    "rounds_completed": ["wild_card", "divisional", "conference", "super_bowl"],
    "super_bowl_winner": 14,
    "final_date": "2025-02-15",
    "success": True
}
```

### State Inspection Methods

#### Get Current Bracket

```python
bracket = controller.get_current_bracket()
```

Returns the current playoff bracket state including all rounds.

**Returns**:
```python
{
    "current_round": "divisional",
    "original_seeding": PlayoffSeeding(...),
    "wild_card": PlayoffBracket(...),      # Bracket object
    "divisional": PlayoffBracket(...),     # Bracket object
    "conference": None,                     # Not yet scheduled
    "super_bowl": None                      # Not yet scheduled
}
```

#### Get Round Games

```python
games = controller.get_round_games("wild_card")
```

Returns all completed games for a specific round.

**Parameters**:
- `round_name`: `'wild_card'`, `'divisional'`, `'conference'`, or `'super_bowl'`

**Returns**: List of game dictionaries with results

#### Get Current State

```python
state = controller.get_current_state()
```

Returns comprehensive current state of the playoffs.

**Returns**:
```python
{
    "current_date": "2025-01-18",
    "current_round": "wild_card",         # Last round with games simulated
    "active_round": "divisional",         # First incomplete round
    "games_played": 6,
    "days_simulated": 7,
    "round_progress": {
        "wild_card": {
            "games_completed": 6,
            "games_expected": 6,
            "complete": True
        },
        "divisional": {
            "games_completed": 0,
            "games_expected": 4,
            "complete": False
        },
        # ... other rounds
    }
}
```

#### Get Active Round

```python
active_round = controller.get_active_round()
```

Returns the current "active" playoff round based on completion status.

**Important Distinction**:
- `current_round`: Last round with games simulated (only updates when games from next round play)
- `active_round`: First incomplete round (accurate even when scheduled but not yet simulated)

**Returns**: Round name (`'wild_card'`, `'divisional'`, `'conference'`, `'super_bowl'`)

## Round Management

### Round Detection Logic

The controller uses **two different round tracking concepts**:

1. **`current_round`**: The round of the last simulated game
   - Only updates when a game from a new round is simulated
   - Can be "stale" after a round completes but before next round games play

2. **`active_round`**: The first incomplete round
   - Calculated dynamically based on game completion
   - Always accurate, even when rounds are scheduled but not simulated

**Example Scenario**:
```python
# After Wild Card completes and Divisional is scheduled:
state = controller.get_current_state()
print(state['current_round'])  # "wild_card" (last games simulated)
print(state['active_round'])   # "divisional" (first incomplete round)
```

### Scheduling Logic

Rounds are scheduled **progressively** - each round is scheduled only after the previous round completes:

1. **Initialization**: Wild Card round is scheduled immediately with original seeding
2. **After Wild Card**: Divisional round is scheduled using Wild Card winners
3. **After Divisional**: Conference round is scheduled using Divisional winners
4. **After Conference**: Super Bowl is scheduled using Conference winners

**Important**: Rounds cannot be pre-scheduled because matchups depend on actual game results (re-seeding applies).

### Completion Detection

A round is considered complete when:
```python
completed_games >= expected_games

Expected game counts:
- Wild Card: 6 games
- Divisional: 4 games
- Conference: 2 games
- Super Bowl: 1 game
```

## State Management

### Bracket Tracking

The controller maintains bracket state in two structures:

1. **`self.brackets`**: Stores actual `PlayoffBracket` objects
   ```python
   {
       'wild_card': PlayoffBracket(...),
       'divisional': PlayoffBracket(...),
       'conference': None,  # Not yet scheduled
       'super_bowl': None
   }
   ```

2. **`self.completed_games`**: Stores game result dictionaries by round
   ```python
   {
       'wild_card': [
           {'game_id': '...', 'winner_id': 14, ...},
           {'game_id': '...', 'winner_id': 7, ...},
           # ... 6 games total
       ],
       'divisional': [],
       'conference': [],
       'super_bowl': []
   }
   ```

### Game Tracking

Each simulated game is:
1. **Detected** by round using game_id pattern matching
2. **Tracked** in the appropriate round's completed_games list
3. **Checked** for duplicates (dynasty isolation validation)

**Game ID Format**: `playoff_{dynasty_id}_{season}_{round}_{game_number}`

Example: `playoff_my_dynasty_2024_wild_card_1`

### Round Transition

Round transitions happen automatically when:
1. A game from a new round is simulated
2. The game_id indicates a different round than `current_round`
3. `current_round` is updated to the new round

**Important**: Round transition is **game-driven**, not schedule-driven.

## Integration Guide

### Basic Usage - Main Application

```python
from playoff_system.playoff_controller import PlayoffController

# Create controller for user's dynasty
controller = PlayoffController(
    database_path="dynasties/user_dynasty.db",
    dynasty_id="user_eagles_dynasty",
    season_year=2024,
    enable_persistence=True,
    verbose_logging=False  # Disable for GUI applications
)

# Day-by-day simulation (for interactive UI)
while not playoff_complete:
    result = controller.advance_day()

    if result['games_played'] > 0:
        display_games(result['results'])

    if result['round_complete']:
        display_round_complete(result['current_round'])

# Or simulate entire playoffs at once
result = controller.simulate_to_super_bowl()
display_champion(result['super_bowl_winner'])
```

### Dynasty Isolation

Multiple dynasties can run concurrent playoffs in the same database:

```python
# Dynasty 1: User's Eagles franchise
eagles_controller = PlayoffController(
    database_path="shared.db",
    dynasty_id="eagles_dynasty_2024",
    season_year=2024
)

# Dynasty 2: AI simulation
ai_controller = PlayoffController(
    database_path="shared.db",
    dynasty_id="ai_simulation_2024",
    season_year=2024
)

# Each dynasty has completely isolated playoff events and results
eagles_controller.simulate_to_super_bowl()  # Eagles playoffs
ai_controller.simulate_to_super_bowl()      # AI playoffs
```

### Persistence Configuration

Control whether game results are saved to the database:

```python
# Disable persistence for quick demos/tests
demo_controller = PlayoffController(
    database_path=":memory:",           # In-memory database
    dynasty_id="demo",
    enable_persistence=False            # No database saves
)

# Enable persistence for dynasty mode
dynasty_controller = PlayoffController(
    database_path="dynasty_2024.db",
    dynasty_id="my_franchise",
    enable_persistence=True             # Save all results
)
```

### Custom Scheduling

Start playoffs from a specific date:

```python
from calendar.date_models import Date

# Start Wild Card on a custom date
controller = PlayoffController(
    database_path="playoffs.db",
    dynasty_id="custom_schedule",
    season_year=2024,
    wild_card_start_date=Date(2025, 1, 13)  # Custom date
)

# Round dates will be calculated from this start date:
# Wild Card: Jan 13
# Divisional: Jan 20 (start + 7)
# Conference: Jan 27 (start + 14)
# Super Bowl: Feb 10 (start + 28)
```

### Existing Playoff Detection

The controller automatically detects and resumes existing playoffs:

```python
# First run - creates new playoff bracket
controller1 = PlayoffController(
    database_path="playoffs.db",
    dynasty_id="my_playoffs",
    season_year=2024
)
# → Schedules new Wild Card games

# Second run - detects existing playoff
controller2 = PlayoffController(
    database_path="playoffs.db",
    dynasty_id="my_playoffs",  # Same dynasty_id
    season_year=2024            # Same season
)
# → Reuses existing playoff schedule, no duplicates created
```

## Internal Architecture

### Private Helper Methods

#### `_initialize_playoff_bracket()`
- Generates random playoff seeding (for testing/demos)
- Checks for existing playoff events to avoid duplicates
- Schedules Wild Card round

#### `_schedule_next_round()`
- Determines the last completed round
- Calculates next round name and start date
- Prevents duplicate scheduling
- Converts completed games to GameResult objects
- Calls PlayoffScheduler to create next round events

#### `_detect_game_round(game_id: str) -> str`
- Parses game_id to determine which round it belongs to
- Uses regex pattern matching to handle dynasty IDs with underscores
- Pattern: `_{round_name}_\d+$`

#### `_convert_games_to_results(games: List[Dict]) -> List[GameResult]`
- Converts completed game dictionaries to GameResult objects
- Required by PlayoffScheduler for bracket generation
- Loads team objects and constructs proper result structures

#### `_is_round_complete(round_name: str) -> bool`
- Checks if a specific round has all expected games complete
- Used by both `advance_to_next_round()` and `advance_day()`

#### `_get_expected_game_count(round_name: str) -> int`
- Returns expected game count for each round
- Wild Card: 6, Divisional: 4, Conference: 2, Super Bowl: 1

### Game ID Parsing

Game IDs follow the pattern: `playoff_{dynasty_id}_{season}_{round}_{number}`

**Challenge**: Both `dynasty_id` and `round_name` can contain underscores.

**Solution**: Regex pattern matching from the end of the string:
```python
def _detect_game_round(self, game_id: str) -> Optional[str]:
    for round_name in ['wild_card', 'divisional', 'conference', 'super_bowl']:
        pattern = f"_{round_name}_\\d+$"
        if re.search(pattern, game_id):
            return round_name
    return None
```

**Examples**:
- `playoff_my_dynasty_2024_wild_card_1` → `wild_card`
- `playoff_debug_dynasty_2024_divisional_2` → `divisional`
- `playoff_user_2024_conference_1` → `conference`

### Result Conversion

The PlayoffScheduler requires `GameResult` objects, but simulated games return dictionaries:

```python
def _convert_games_to_results(self, games: List[Dict]) -> List[GameResult]:
    results = []

    for game in games:
        home_team = get_team_by_id(game['home_team_id'])
        away_team = get_team_by_id(game['away_team_id'])

        final_score = {
            home_team.team_id: game['home_score'],
            away_team.team_id: game['away_score']
        }

        winner = home_team if game['winner_id'] == home_team.team_id else away_team

        result = GameResult(
            home_team=home_team,
            away_team=away_team,
            final_score=final_score,
            winner=winner,
            total_plays=game['total_plays'],
            season_type="playoffs"
        )

        results.append(result)

    return results
```

## Error Handling & Edge Cases

### Duplicate Game Detection

The controller includes **critical duplicate detection** to validate dynasty isolation:

```python
# When tracking a completed game:
game_id = game.get('game_id', '')
existing_game_ids = [g.get('game_id', '') for g in self.completed_games[round]]

if game_id in existing_game_ids:
    error_msg = (
        f"CRITICAL: Duplicate game detected: {game_id}. "
        f"This indicates a bug in dynasty isolation or event scheduling."
    )
    self.logger.error(error_msg)
    raise RuntimeError(error_msg)
```

**Why This Matters**: If duplicate games appear, it means:
- Dynasty isolation is broken
- Event scheduling is creating duplicates
- Database queries aren't filtering by dynasty_id properly

### Dynasty Isolation Validation

Each controller instance ensures its dynasty exists:

```python
from database.connection import DatabaseConnection
db_conn = DatabaseConnection(database_path)
db_conn.ensure_dynasty_exists(dynasty_id)
```

This creates the dynasty record if it doesn't exist, ensuring proper data separation.

### Round Scheduling Safety

Prevents duplicate round scheduling:

```python
# Check if round already scheduled
existing_events = self.event_db.get_events_by_game_id_prefix(
    f"playoff_{self.dynasty_id}_{self.season_year}_{next_round}_",
    event_type="GAME"
)

if existing_events:
    print(f"✅ {next_round} already scheduled, skipping duplicate")
    return
```

### Safety Limits

All advancement methods include safety limits to prevent infinite loops:

```python
# advance_to_next_round(): max 30 days
max_days = 30
while not self._is_round_complete(round_name) and days < max_days:
    self.advance_day()

# simulate_to_super_bowl(): max 60 days
max_days = 60
while days < max_days:
    # ... simulation logic
```

These limits protect against:
- Scheduling errors (round never completes)
- Missing game events
- Logic bugs causing infinite loops

## Constants Reference

### Round Order
```python
ROUND_ORDER = ['wild_card', 'divisional', 'conference', 'super_bowl']
```

### Scheduling Offsets
```python
WILD_CARD_OFFSET = 0      # Day 0
DIVISIONAL_OFFSET = 7     # Day 7
CONFERENCE_OFFSET = 14    # Day 14
SUPER_BOWL_OFFSET = 28    # Day 28
```

All offsets are relative to the Wild Card start date.

## Testing & Debugging

### Reset Playoffs

For testing purposes, you can reset the playoffs:

```python
controller.reset_playoffs(new_wild_card_date=Date(2025, 1, 15))
```

This:
- Resets current_round to 'wild_card'
- Clears all completed_games
- Resets statistics
- Reinitializes playoff bracket

### Verbose Logging

Enable detailed console output for debugging:

```python
controller = PlayoffController(
    database_path="debug.db",
    dynasty_id="debug_session",
    verbose_logging=True  # Prints detailed progress
)
```

Output includes:
- Initialization details
- Daily simulation progress
- Round completion notifications
- Scheduling operations
- Error details

### String Representations

```python
str(controller)
# → "PlayoffController(season=2024, round=wild_card, games=6)"

repr(controller)
# → "PlayoffController(database_path='playoffs.db', season_year=2024, dynasty_id='my_dynasty')"
```

## Related Components

### Dependencies
- **CalendarComponent** (`src/calendar/calendar_component.py`): Date management
- **EventDatabaseAPI** (`src/events/`): Event storage and retrieval
- **SimulationExecutor** (`src/calendar/simulation_executor.py`): Game execution
- **PlayoffSeeder** (`src/playoff_system/playoff_seeder.py`): Seeding calculation
- **PlayoffManager** (`src/playoff_system/playoff_manager.py`): Bracket generation
- **PlayoffScheduler** (`src/playoff_system/playoff_scheduler.py`): Event creation

### Used By
- **Interactive Playoff Simulator** (`demo/interactive_playoff_sim/`): Terminal UI demo
- **Main Application**: GUI playoff simulation
- **Season Manager**: Integration with season progression
- **Dynasty Manager**: Multi-season playoff tracking

## Future Enhancements

Potential improvements for the playoff controller:

1. **Bracket Reconstruction**: Rebuild bracket structure from existing events when resuming playoffs
2. **Custom Seeding Input**: Accept pre-calculated seeding instead of random generation
3. **Flexible Scheduling**: Configure custom round dates instead of fixed offsets
4. **Parallel Dynasty Support**: Optimize for concurrent playoff simulations
5. **Replay Support**: Save/load playoff state for replay functionality
6. **Analytics Integration**: Enhanced statistics tracking and analysis
7. **Event Streaming**: Real-time playoff event notifications
