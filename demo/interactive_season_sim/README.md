# Interactive Season Simulator

Terminal-based NFL season simulation with day/week/full season control.

## Quick Start

```bash
# 1. Initialize database
PYTHONPATH=src python demo/interactive_season_sim/initialize_season_db.py

# 2. Run simulator
PYTHONPATH=src python demo/interactive_season_sim/interactive_season_sim.py
```

## Commands

- `[1]` Advance 1 day
- `[2]` Advance 7 days (1 week)
- `[3]` Simulate to end of season
- `[4]` Show current standings
- `[5]` Show upcoming games
- `[6]` Show season summary
- `[0]` Exit

## Features

- 17-week regular season (272 games)
- Random matchups (no repeats per week)
- Live standings updates
- Full persistence to SQLite database
- Phase tracking (regular season → playoffs)

## Performance

- Single game: ~2-3 seconds
- Week (16 games): ~40-50 seconds
- Full season (272 games): ~10-15 minutes
