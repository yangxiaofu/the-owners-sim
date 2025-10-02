# Calendar Events Demo

This demo demonstrates simulating NFL games on a day-by-day basis using the calendar and events API.

## Overview

The demo shows the integration of four key components:

1. **CalendarComponent** - Manages date/time state and season phase tracking
2. **EventDatabaseAPI** - Stores and retrieves scheduled game events
3. **SimulationExecutor** - Orchestrates the daily simulation workflow
4. **GameEvent** - Wraps FullGameSimulator for individual game execution

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User/Demo Script                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
          ┌───────────────────────────┐
          │   SimulationExecutor      │
          └───────────┬─────┬─────────┘
                      │     │
        ┌─────────────┘     └──────────────┐
        ▼                                   ▼
┌────────────────┐                  ┌──────────────┐
│ CalendarComponent │                │ EventDatabaseAPI │
│ - Date management│                │ - Event storage │
│ - Phase tracking │                │ - Event queries │
└────────────────┘                  └──────┬──────┘
                                           │
                                           ▼
                                   ┌──────────────┐
                                   │  GameEvent   │
                                   │ (wraps       │
                                   │ FullGame-    │
                                   │ Simulator)   │
                                   └──────────────┘
```

## Components

### SimulationExecutor (`src/calendar/simulation_executor.py`)

**Note:** This component has been moved to `src/calendar/` as it's production-ready code used by SeasonManager.

Orchestrates the daily simulation workflow:
- Gets current date from calendar
- Retrieves events scheduled for that date
- Executes each game event
- Records game completions for phase tracking
- Returns comprehensive results

**Key Methods:**
- `simulate_day(target_date)` - Simulate all games for a specific day
- `advance_calendar(days)` - Move calendar forward
- `get_phase_info()` - Get current season phase information

### SchedulePopulator (`schedule_populator.py`)

Helper utility for creating test schedules:
- `create_week_1_schedule()` - Creates realistic Week 1 NFL schedule
- `create_simple_test_schedule()` - Creates basic test games
- `create_single_game()` - Creates individual game events
- `clear_all_events()` - Removes all events from database

### Main Demo (`calendar_events_demo.py`)

Demonstrates complete workflow:
1. Initialize calendar and events database
2. Populate Week 1 schedule (16 games)
3. Simulate Thursday Night Football
4. Advance to Sunday
5. Simulate Sunday games (13+ games)
6. Display results and phase information

## Running the Demo

```bash
# From project root
PYTHONPATH=src python demo/calendar_events_demo/calendar_events_demo.py
```

## Demo Workflow

### Step 1: Setup
- Initialize CalendarComponent at Sept 5, 2024 (Thursday before Week 1)
- Create EventDatabaseAPI with test database
- Initialize SimulationExecutor

### Step 2: Populate Schedule
- Clear any existing events
- Create Week 1 NFL schedule:
  - 1 Thursday Night game
  - 13 Sunday games (early/late slots)
  - 2 Monday Night games

### Step 3: Simulate Thursday
- Simulate Thursday Night Football (Sept 5)
- Display game results
- Check for phase transitions (offseason → regular season)

### Step 4: Advance to Sunday
- Move calendar forward 3 days to Sept 8
- Verify calendar state

### Step 5: Simulate Sunday
- Simulate all Sunday games
- Display results for each game
- Track phase progression

### Step 6: Summary
- Show total games simulated
- Display season phase information
- Show calendar statistics

## Output

The demo provides detailed output including:

- **Game Results**: Scores, winners, play counts for each game
- **Phase Information**: Current phase, games completed, progress percentage
- **Phase Transitions**: Automatic transitions based on game completions
- **Calendar Statistics**: Days advanced, advancement count, etc.

## Key Features Demonstrated

1. **Database-First Scheduling**: All games stored as events before simulation
2. **Event-Driven Phase Tracking**: Automatic phase transitions based on game completions
3. **Polymorphic Event System**: GameEvents stored alongside other event types
4. **Day-by-Day Simulation**: Realistic progression through the season
5. **Result Caching**: Game results stored back to event records

## Customization

### Create Custom Schedule

```python
from schedule_populator import SchedulePopulator
from datetime import datetime

populator = SchedulePopulator(event_db)

# Create specific games
populator.create_single_game(
    away_team_id=TeamIDs.DETROIT_LIONS,
    home_team_id=TeamIDs.GREEN_BAY_PACKERS,
    game_date=datetime(2024, 9, 8, 13, 0),
    week=1,
    season=2024
)
```

### Simulate Specific Date

```python
from calendar.date_models import Date

# Simulate games on a specific date
results = executor.simulate_day(target_date=Date(2024, 9, 8))
```

### Query Events

```python
# Get all games scheduled
all_games = event_db.get_events_by_type("GAME")

# Get summary
summary = populator.get_schedule_summary()
print(f"Total games: {summary['total_games']}")
```

## Database

Events are stored in: `data/database/calendar_demo_events.db`

The database persists:
- Scheduled game parameters (teams, date, week)
- Game results after simulation (scores, stats)
- Event metadata (matchup description, phase info)

## Next Steps

This demo can be extended to:
- Simulate entire weeks or seasons
- Add playoff scheduling
- Integrate with dynasty management
- Add user team focus and filtering
- Generate weekly/season reports
- Handle bye weeks and scheduling complexity

## Related Components

- `src/calendar/` - Calendar management system
- `src/events/` - Polymorphic event system
- `src/game_management/full_game_simulator.py` - Core game simulation
- `src/season/season_manager.py` - Season-level coordination
