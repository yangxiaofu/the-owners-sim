# SeasonController Documentation

Core orchestration system for NFL season simulation with daily and weekly progression.

## Overview

The `SeasonController` is the central component for managing NFL season simulation. It coordinates calendar advancement, event execution, and standings tracking through a clean, unified interface.

## Architecture

### Components

```
SeasonController
├── CalendarComponent          # Date/time management
├── EventDatabaseAPI          # Event storage/retrieval
├── SimulationExecutor        # Day simulation orchestration
├── RandomScheduleGenerator   # Schedule generation
└── DatabaseAPI              # Standings and statistics
```

### Key Features

- **Daily/Weekly Simulation**: Advance by day or week with automatic game execution
- **Schedule Generation**: Automatic 272-game NFL season schedule creation
- **Standings Tracking**: Real-time standings by division and conference
- **Phase Management**: Automatic season phase tracking (regular season, playoffs, etc.)
- **Dynasty Support**: Multi-dynasty isolation for separate save files
- **Flexible Persistence**: Toggle database persistence on/off for testing

## Usage

### Basic Setup

```python
from calendar.date_models import Date
from season_controller import SeasonController

# Create controller
controller = SeasonController(
    database_path="season_2024.db",
    start_date=Date(2024, 9, 5),  # Week 1 Thursday
    season_year=2024,
    dynasty_id="my_dynasty",
    enable_persistence=True,
    verbose_logging=True
)
```

### Daily Simulation

```python
# Advance one day
result = controller.advance_day()

print(f"Date: {result['date']}")
print(f"Games Played: {result['games_played']}")
print(f"Current Phase: {result['current_phase']}")

# Check results
for game in result['results']:
    if game['success']:
        print(f"{game['away_team_id']} @ {game['home_team_id']}: "
              f"{game['away_score']}-{game['home_score']}")
```

### Weekly Simulation

```python
# Advance one week
week_result = controller.advance_week()

print(f"Week {week_result['week_number']} Complete")
print(f"Games Played: {week_result['total_games_played']}")
print(f"Date Range: {week_result['start_date']} to {week_result['end_date']}")
```

### Full Season Simulation

```python
# Simulate to end of regular season
summary = controller.simulate_to_end()

print(f"Total Games: {summary['total_games']}")
print(f"Total Days: {summary['total_days']}")
print(f"Final Phase: {summary['final_phase']}")
```

### Standings Queries

```python
# Get current standings
standings = controller.get_current_standings()

# Access by division
for division_name, teams in standings['divisions'].items():
    print(f"\n{division_name}")
    for team_data in teams:
        team_id = team_data['team_id']
        standing = team_data['standing']
        print(f"  {team_id}: {standing.record_string} ({standing.win_percentage:.3f})")

# Access by conference
afc_teams = standings['conferences']['AFC']
nfc_teams = standings['conferences']['NFC']
```

### Upcoming Games

```python
# Get games in next 7 days
upcoming = controller.get_upcoming_games(days=7)

for game in upcoming:
    print(f"{game['date']}: Team {game['away_team_id']} @ Team {game['home_team_id']}")
```

### Current State

```python
# Get comprehensive state
state = controller.get_current_state()

print(f"Current Date: {state['current_date']}")
print(f"Week Number: {state['week_number']}")
print(f"Games Played: {state['games_played']}")
print(f"Phase: {state['phase']}")
print(f"Days Simulated: {state['days_simulated']}")
```

## API Reference

### SeasonController

#### Constructor

```python
SeasonController(
    database_path: str,
    start_date: Date,
    season_year: int,
    dynasty_id: str = "default",
    enable_persistence: bool = True,
    verbose_logging: bool = True
)
```

**Parameters:**
- `database_path`: Path to SQLite database for events and game data
- `start_date`: Starting date for the season (typically Week 1 Thursday)
- `season_year`: NFL season year (e.g., 2024 for 2024-25 season)
- `dynasty_id`: Dynasty context for data isolation
- `enable_persistence`: Whether to persist game results to database
- `verbose_logging`: Whether to print detailed progress messages

#### Methods

##### `advance_day() -> Dict[str, Any]`

Advance calendar by 1 day and simulate all scheduled games.

**Returns:**
```python
{
    "date": str,                    # Current date
    "games_played": int,            # Number of games played
    "results": List[Dict],          # Game results
    "standings_updated": bool,      # Whether standings changed
    "current_phase": str,           # Current season phase
    "phase_transitions": List[Dict],# Any phase changes
    "success": bool,                # Overall success
    "errors": List[str]             # Any errors
}
```

##### `advance_week() -> Dict[str, Any]`

Advance calendar by 7 days, simulating all scheduled games.

**Returns:**
```python
{
    "week_number": int,             # Week that just completed
    "start_date": str,              # Week start date
    "end_date": str,                # Week end date
    "total_games_played": int,      # Games in this week
    "daily_results": List[Dict],    # Results for each day
    "standings_updated": bool,      # Whether standings changed
    "success": bool                 # Overall success
}
```

##### `simulate_to_end() -> Dict[str, Any]`

Simulate remaining season until all games are complete.

**Returns:**
```python
{
    "total_games": int,             # Total games simulated
    "total_days": int,              # Days simulated
    "final_date": str,              # Final simulation date
    "final_phase": str,             # Final season phase
    "final_standings": Dict,        # Final standings
    "success": bool                 # Overall success
}
```

##### `get_current_standings() -> Dict[str, Any]`

Get current standings from database.

**Returns:**
```python
{
    "divisions": {
        "AFC East": [...],
        "NFC North": [...],
        # ... all 8 divisions
    },
    "conferences": {
        "AFC": [...],
        "NFC": [...]
    }
}
```

##### `get_upcoming_games(days: int = 7) -> List[Dict[str, Any]]`

Get games scheduled in the next N days.

**Parameters:**
- `days`: Number of days ahead to look (default: 7)

**Returns:**
```python
[
    {
        "date": str,
        "away_team_id": int,
        "home_team_id": int,
        "week": int,
        "game_id": str
    },
    # ... more games
]
```

##### `get_current_state() -> Dict[str, Any]`

Get comprehensive current state of the season.

**Returns:**
```python
{
    "current_date": str,
    "week_number": int,
    "games_played": int,
    "phase": str,
    "days_simulated": int,
    "phase_info": Dict
}
```

##### `reset_season(new_start_date: Optional[Date] = None)`

Reset the season to a new starting point.

**Parameters:**
- `new_start_date`: New starting date (uses original if None)

## Testing

Run the test script to verify functionality:

```bash
# From the demo/interactive_season_sim directory
PYTHONPATH=../../src python test_season_controller.py
```

## Implementation Notes

### Schedule Generation

The `RandomScheduleGenerator` creates a simplified random schedule:
- 17 weeks of regular season
- 16 games per week (all 32 teams play)
- Realistic game timing (Thursday/Sunday/Monday)
- Each team plays 17 games total

**Note:** This is a simplified generator. For NFL-realistic schedules with division/conference constraints, use the full scheduling system in `src/scheduling/`.

### Database Structure

The controller uses two database systems:
1. **Event Database** (`EventDatabaseAPI`): Stores scheduled games as events
2. **Game Database** (`DatabaseAPI`): Stores game results and standings

### Phase Tracking

Season phases are automatically tracked:
- `PRESEASON`: Before regular season starts
- `REGULAR_SEASON`: Weeks 1-17
- `PLAYOFFS`: Wild card through Super Bowl
- `OFFSEASON`: After season completion

Phase transitions trigger automatically based on game completions.

### Dynasty Isolation

Each dynasty has completely separate data:
- Game results stored with `dynasty_id`
- Standings tracked per dynasty
- Multiple dynasties can use the same database

## Examples

### Example 1: Simulate Week 1

```python
from calendar.date_models import Date
from season_controller import SeasonController

# Create controller starting at Week 1
controller = SeasonController(
    database_path="week1_test.db",
    start_date=Date(2024, 9, 5),
    season_year=2024,
    dynasty_id="week1_demo"
)

# Simulate entire Week 1
week1_result = controller.advance_week()

print(f"Week 1 Complete!")
print(f"Games Played: {week1_result['total_games_played']}")

# Show standings
standings = controller.get_current_standings()
for division, teams in standings['divisions'].items():
    print(f"\n{division}")
    for team in teams[:3]:  # Top 3
        print(f"  {team['standing'].record_string}")
```

### Example 2: Day-by-Day Simulation

```python
# Advance day-by-day for a week
for day in range(7):
    result = controller.advance_day()

    if result['games_played'] > 0:
        print(f"\n{result['date']}: {result['games_played']} games")

        for game in result['results']:
            if game['success']:
                print(f"  {game['matchup']}: {game['away_score']}-{game['home_score']}")
```

### Example 3: Full Season Automation

```python
# Run entire season automatically
print("Starting full season simulation...")

summary = controller.simulate_to_end()

print(f"\nSeason Complete!")
print(f"Total Games: {summary['total_games']}")
print(f"Duration: {summary['total_days']} days")
print(f"Final Phase: {summary['final_phase']}")

# Show final standings
standings = summary['final_standings']
# ... display standings
```

## Integration

The `SeasonController` is designed to integrate with:

- **Interactive UI**: Use as backend for user-driven season simulation
- **Batch Processing**: Automate full season simulations
- **Testing**: Verify game simulation accuracy across full seasons
- **Dynasty Mode**: Manage multi-season franchises with persistent data

## Performance

- **Daily Simulation**: ~0.5-2 seconds per day (depends on games scheduled)
- **Weekly Simulation**: ~5-15 seconds per week (16 games)
- **Full Season**: ~2-5 minutes for 272 games (17 weeks)

Performance varies based on:
- Persistence enabled/disabled
- Database location (SSD vs HDD)
- Logging verbosity
- Game complexity

## Future Enhancements

Potential improvements:
- Realistic NFL schedule generation with division/conference constraints
- Multi-week simulation (advance by N weeks)
- Pause/resume season simulation
- Real-time standings updates during simulation
- Playoff bracket generation and simulation
- Season summary reports and analytics
