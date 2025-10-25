# Scheduling Module

## Purpose
Generates complete NFL schedules for regular season, preseason, and playoffs.

## Components
- `schedule_generator.py`: Main schedule generation logic with dynamic date calculations

## Usage

### Regular Season Schedule
```python
from scheduling import RandomScheduleGenerator
from events.event_database_api import EventDatabaseAPI

event_db = EventDatabaseAPI("path/to/db.db")
generator = RandomScheduleGenerator(event_db, dynasty_id="my_dynasty")

# Generate 272-game regular season (17 weeks)
# Start date calculated dynamically (first Thursday after Labor Day)
regular_season_games = generator.generate_season(2025)
```

### Preseason Schedule
```python
# Generate 48-game preseason (3 weeks)
# Uses geographic proximity for realistic matchups
preseason_games = generator.generate_preseason(2025)
```

### Using Helper Function
```python
from scheduling import create_schedule_generator

generator = create_schedule_generator(database_path="path/to/db.db")
games = generator.generate_season(2025)
```

## Features

### Dynamic Date Calculation
- **Labor Day**: Automatically calculated (first Monday in September)
- **Regular Season Start**: First Thursday AFTER Labor Day (Sept 5-11 depending on year)
- **Preseason Start**: ~3.5 weeks before regular season (mid-August)

### Schedule Generation
- **Regular Season**: 17 weeks × 16 games = 272 total games
- **Preseason**: 3 weeks × 16 games = 48 total games
- **Realistic Timing**: Thursday/Sunday/Monday game slots

### Matchup Strategies
- **Regular Season**: Random pairings (future: division-based rotation)
- **Preseason**: Geographic proximity (division/conference priority)

### Dynasty Isolation
All generated games include `dynasty_id` for multi-save support.

## Technical Details

### Game Event Structure
```python
GameEvent(
    game_id="regular_2025_1_1",       # Format: {type}_{year}_{week}_{number}
    home_team_id=22,                   # Detroit Lions
    away_team_id=9,                    # Chicago Bears
    game_datetime=datetime(2025, 9, 4, 20, 0),  # Thursday 8:00 PM
    week=1,
    season_year=2025,
    season_type="regular_season",      # or "preseason"
    dynasty_id="my_dynasty"
)
```

### Stat Tracking Isolation
- Regular season games: `season_type="regular_season"`
- Preseason games: `season_type="preseason"`
- Allows separate stat tracking and filtering

## Examples

### Generate Schedule for Specific Year
```python
# 2024 season
games_2024 = generator.generate_season(2024)
# Regular season starts: Thursday, Sept 5, 2024 (Labor Day = Sept 2)

# 2025 season
games_2025 = generator.generate_season(2025)
# Regular season starts: Thursday, Sept 4, 2025 (Labor Day = Sept 1)
```

### Reproducible Schedules
```python
# Use random seed for consistent matchups
games = generator.generate_season(2025, seed=12345)
# Same seed always produces same schedule
```

### Custom Start Date
```python
from datetime import datetime

# Override automatic calculation
custom_start = datetime(2025, 9, 10, 20, 0)
games = generator.generate_season(2025, start_date=custom_start)
```

## Integration Points

### Used By
- `ui/domain_models/season_data_model.py` - UI season initialization
- `src/season/season_cycle_controller.py` - Season transitions
- `demo/interactive_season_sim/season_controller.py` - Demo simulations

### Dependencies
- `events.event_database_api.EventDatabaseAPI` - Game event storage
- `events.game_event.GameEvent` - Game event model
- `constants.team_ids.TeamIDs` - Team ID constants
- `team_management.teams.team_loader.TeamDataLoader` - Team metadata

## Future Enhancements

- [ ] Real NFL schedule rotation algorithm (division-based matchups)
- [ ] International games support
- [ ] Thursday Night Football selection logic
- [ ] Bye week scheduling (currently not implemented)
- [ ] Strength of schedule calculations
