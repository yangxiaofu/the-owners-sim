# Interactive Playoff Simulator

Terminal-based interactive NFL playoff simulation with day/week/round control, using the same calendar system as the regular season simulator to ensure consistency.

## Features

- **Calendar-Based Simulation**: Uses `CalendarComponent`, `SimulationExecutor`, and `EventDatabaseAPI` - the same infrastructure as regular season simulation
- **Progressive Playoff Scheduling**: Games are scheduled dynamically as previous rounds complete (can't schedule all rounds upfront)
- **Random Team Selection**: Generates realistic playoff scenarios with 14 random teams (7 per conference)
- **Interactive Control**: Advance day-by-day, week-by-week, or round-by-round
- **Rich Visualization**: Color-coded terminal display with playoff brackets, game results, and round summaries
- **Dynasty Isolation**: Multiple playoff simulations can run independently with unique dynasty IDs

## Architecture

### Core Components

1. **InteractivePlayoffSimulator** - Main UI loop and user interaction
2. **PlayoffController** - Orchestrates calendar, events, and playoff progression
3. **PlayoffManager** - Pure playoff bracket generation logic with NFL re-seeding
4. **PlayoffScheduler** - Creates GameEvent objects and stores them in EventDatabaseAPI
5. **RandomPlayoffSeeder** - Generates random but realistic playoff seeding

### Calendar System Integration

The simulator uses the **exact same calendar infrastructure** as the regular season:

```
CalendarComponent (date tracking)
    ↓
EventDatabaseAPI (event storage)
    ↓
SimulationExecutor (game execution)
    ↓
SimulationWorkflow (3-stage simulation + persistence)
    ↓
FullGameSimulator (actual game simulation)
```

This ensures:
- ✅ Consistent date handling between regular season and playoffs
- ✅ Same event storage mechanism
- ✅ Same game simulation engine
- ✅ Same persistence patterns
- ✅ Dynasty isolation works identically

## Usage

### Quick Start

```bash
# From project root
PYTHONPATH=src python demo/interactive_playoff_sim/interactive_playoff_sim.py
```

### Programmatic Usage

```python
from demo.interactive_playoff_sim import InteractivePlayoffSimulator

simulator = InteractivePlayoffSimulator(
    dynasty_id="my_playoff_run",
    season_year=2024
)
simulator.run()
```

### Custom Database Path

```python
simulator = InteractivePlayoffSimulator(
    dynasty_id="eagles_superbowl",
    database_path="custom/path/playoffs.db",
    season_year=2024
)
```

## Interactive Commands

Once running, you have these options:

- **[1] Advance 1 day** - Simulate games scheduled for the next day
- **[2] Advance 7 days (1 week)** - Simulate a full week
- **[3] Advance to next playoff round** - Simulate until current round completes
- **[4] Show current bracket** - Display playoff bracket with seeds and matchups
- **[5] Show completed games** - View all completed playoff games
- **[6] Simulate to Super Bowl** - Auto-simulate all remaining playoffs
- **[0] Exit** - Quit simulator

## Playoff Flow

### Wild Card Round (Games 1-6)
- Scheduled immediately at initialization
- 3 games per conference: (7)@(2), (6)@(3), (5)@(4)
- #1 seeds get first-round bye

### Divisional Round (Games 7-10)
- Scheduled after Wild Card completes
- Uses **NFL re-seeding rule**: #1 seed plays LOWEST remaining seed
- 2 games per conference

### Conference Championships (Games 11-12)
- Scheduled after Divisional completes
- 1 game per conference
- Winners advance to Super Bowl

### Super Bowl (Game 13)
- Scheduled after Conference Championships complete
- AFC Champion vs NFC Champion
- Determines NFL Champion

## Progressive Scheduling Example

```
Day 0 (Jan 11): Wild Card Round scheduled (6 games)
  ├─ Advance to Day 0: Simulate Wild Card games
  ├─ Wild Card completes
  └─ Divisional Round scheduled (4 games)

Day 7 (Jan 18): Divisional Round games
  ├─ Advance to Day 7: Simulate Divisional games
  ├─ Divisional completes
  └─ Conference Championships scheduled (2 games)

Day 14 (Jan 26): Conference Championship games
  ├─ Advance to Day 14: Simulate Conference games
  ├─ Conference Championships complete
  └─ Super Bowl scheduled (1 game)

Day 28 (Feb 9): Super Bowl
  ├─ Advance to Day 28: Simulate Super Bowl
  └─ Playoffs complete! 🏆
```

## Calendar System Consistency

This demo validates that the calendar system works identically for playoffs:

| Feature | Season Sim | Playoff Sim | Status |
|---------|-----------|-------------|--------|
| CalendarComponent | ✅ | ✅ | Identical |
| EventDatabaseAPI | ✅ | ✅ | Identical |
| SimulationExecutor | ✅ | ✅ | Identical |
| Day advancement | ✅ | ✅ | Identical |
| Week advancement | ✅ | ✅ | Identical |
| Event storage | ✅ | ✅ | Identical |
| Game simulation | ✅ | ✅ | Identical |
| Dynasty isolation | ✅ | ✅ | Identical |

## Random Seeding

The `RandomPlayoffSeeder` generates realistic playoff scenarios:

- **14 random teams** (7 AFC, 7 NFC)
- **Realistic records** (10-7 to 15-2 for playoff teams)
- **Complete statistics**: division/conference records, points for/against
- **Proper seeding**: Uses PlayoffSeeder's tiebreaker logic
- **Reproducible**: Optional seed parameter for consistent scenarios

## Database Schema

Playoff games are stored in EventDatabaseAPI with:
- `event_type`: "GAME"
- `season_type`: "playoffs"
- `overtime_type`: "playoffs"
- `game_id`: Format: `playoff_{dynasty_id}_{season}_{round}_{game_number}`

## Testing

### Manual Testing
```bash
# Run interactive demo
PYTHONPATH=src python demo/interactive_playoff_sim/interactive_playoff_sim.py
```

### Automated Testing
```bash
# Test imports and basic functionality
PYTHONPATH=src python -c "
from demo.interactive_playoff_sim import InteractivePlayoffSimulator, PlayoffController
print('✓ All imports successful')
"
```

## Comparison with Season Simulator

| Aspect | Season Sim | Playoff Sim |
|--------|-----------|-------------|
| Duration | 18 weeks (272 games) | 4 weeks (13 games max) |
| Scheduling | All games scheduled upfront | Progressive (round-by-round) |
| Teams | All 32 teams | 14 playoff teams |
| Phases | Regular Season | Wild Card → Divisional → Conference → Super Bowl |
| Calendar Start | Week 1 Thursday (Sept) | Wild Card Saturday (Jan) |
| Advancement | Day/Week/Season | Day/Week/Round/Super Bowl |

## Future Enhancements

Potential additions (not yet implemented):

1. **Playoff Persistence**
   - Store bracket state in database
   - Track historical playoff results
   - Playoff statistics aggregation

2. **Integration with Regular Season**
   - Automatic playoff trigger after Week 18
   - Use actual season standings for seeding
   - Seamless transition between season and playoffs

3. **Enhanced Statistics**
   - Playoff-specific player stats
   - Postseason awards
   - Championship history

4. **Phase Transition Integration**
   - Listen to REGULAR_SEASON → PLAYOFFS notification
   - Auto-initialize playoffs from season completion
   - Phase tracking for playoff sub-rounds

## Directory Structure

```
demo/interactive_playoff_sim/
├── __init__.py                    # Package initialization
├── README.md                      # This file
├── interactive_playoff_sim.py     # Main UI loop
├── playoff_controller.py          # Calendar-based orchestration
├── random_playoff_seeder.py       # Random seeding generation
├── display_utils.py               # Terminal UI formatting
└── data/                          # Playoff databases
    └── playoffs_2024.db           # Default database
```

## Dependencies

- Python 3.13+
- SQLite3
- Existing simulation components:
  - `src/calendar/` - Calendar system
  - `src/events/` - Event database
  - `src/playoff_system/` - Playoff logic
  - `src/workflows/` - Simulation workflow
  - `src/game_management/` - Game simulator

## Known Limitations

1. **No Playoff Persistence Yet**: Bracket state is not stored in database (planned for future)
2. **Random Teams Only**: Can't yet use actual season standings (integration planned)
3. **No Historical Tracking**: Previous playoff runs not stored (planned for future)

## Credits

This demo validates the calendar system consistency approach discussed in the playoff manager implementation plan (Phase 2 complete).
