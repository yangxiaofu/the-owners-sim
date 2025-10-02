# Quick Start Guide: Random Schedule Generator

Generate a complete 17-week NFL schedule in under 5 minutes.

## 1. Import and Setup

```python
from demo.interactive_season_sim.random_schedule_generator import create_schedule_generator

# Create generator with your database
generator = create_schedule_generator(database_path="data/my_schedule.db")
```

## 2. Generate Schedule

```python
# Generate complete 2024 season (272 games)
games = generator.generate_season(season_year=2024)
```

## 3. View Results

```python
# Get summary
summary = generator.get_schedule_summary()
print(f"Generated {summary['total_games']} games")

# View Week 1 schedule
generator.print_week_schedule(1)
```

## Complete Example

```python
from demo.interactive_season_sim.random_schedule_generator import create_schedule_generator

# Setup
generator = create_schedule_generator("data/schedule.db")

# Generate
games = generator.generate_season(season_year=2024, seed=42)

# View
generator.print_week_schedule(1)
```

## Output Format

```
================================================================================
                                WEEK 1 SCHEDULE
================================================================================

Thursday, September 05, 2024
--------------------------------------------------------------------------------
  08:00 PM - Team 6 @ Team 27

Sunday, September 08, 2024
--------------------------------------------------------------------------------
  01:00 PM - Team 11 @ Team 16
  01:00 PM - Team 26 @ Team 12
  ...

Total games: 16
================================================================================
```

## Common Tasks

### Reproducible Schedule
```python
# Same seed = same schedule every time
games = generator.generate_season(season_year=2024, seed=12345)
```

### Custom Start Date
```python
from datetime import datetime

start = datetime(2025, 9, 4, 20, 0)
games = generator.generate_season(season_year=2025, start_date=start)
```

### Regenerate Schedule
```python
generator.clear_schedule()
games = generator.generate_season(season_year=2024, seed=999)
```

### With Logging
```python
import logging
from events.event_database_api import EventDatabaseAPI
from demo.interactive_season_sim.random_schedule_generator import RandomScheduleGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("schedule")

event_db = EventDatabaseAPI("data/schedule.db")
generator = RandomScheduleGenerator(event_db, logger)
games = generator.generate_season(season_year=2024)
```

## Run Demo

```bash
# From project root
PYTHONPATH=src python demo/interactive_season_sim/random_schedule_generator.py
```

## Run Examples

```bash
# From project root
PYTHONPATH=src python demo/interactive_season_sim/schedule_generator_example.py
```

## Key Features

✅ **272 games** - Complete 17-week regular season
✅ **Realistic timing** - Thursday/Sunday/Monday NFL broadcast schedule
✅ **Validation** - Ensures every team plays exactly 17 games
✅ **Database storage** - All games stored in EventDatabaseAPI
✅ **Reproducible** - Use seeds for consistent schedules
✅ **Fast** - Generates all 272 games in under 1 second

## Need Help?

See [README.md](README.md) for detailed documentation.

## Troubleshooting

**Database errors**: Use file-based databases, not `:memory:`
```python
# ✅ Good
generator = create_schedule_generator("data/schedule.db")

# ❌ Bad
generator = create_schedule_generator(":memory:")
```

**Clear existing schedule**: If database already has games
```python
generator.clear_schedule()
games = generator.generate_season(season_year=2024)
```
