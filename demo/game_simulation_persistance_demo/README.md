# Game Simulation Persistence Demo

A comprehensive demonstration of the **3-Stage Simulation Workflow** system for NFL game simulations, showcasing reusable workflow orchestration with toggleable persistence.

## Overview

This demo simulates an NFL game (Cleveland Browns @ Minnesota Vikings) and demonstrates:
- **3-Stage Workflow Pattern** (Simulation → Statistics → Persistence)
- Event-based game simulation with the SimulationWorkflow system
- Complete game data persistence to SQLite (toggleable)
- Player statistics tracking and management
- Team standings updates
- Comprehensive box score generation

## Features

### ✨ What This Demo Shows

1. **Event Storage & Retrieval**
   - Store game events in isolated database
   - Retrieve events using the Events API
   - Reconstruct game objects from database

2. **Game Simulation**
   - Full NFL game simulation with realistic play-by-play
   - Quarter-by-quarter progression
   - Drive and possession tracking

3. **3-Stage Workflow System** (NEW)
   - **Stage 1**: Game simulation execution
   - **Stage 2**: Comprehensive player statistics gathering
   - **Stage 3**: Complete data persistence (toggleable)
   - Standardized workflow results and error handling

4. **Detailed Statistics**
   - Passing stats (completions, yards, TDs, INTs, rating)
   - Rushing stats (attempts, yards, TDs, YPC)
   - Receiving stats (receptions, targets, yards, TDs)
   - Defensive stats (tackles, sacks, INTs, pass deflections)
   - Snap counts (offensive/defensive/special teams)

5. **Box Scores**
   - NFL-style box score generation
   - Team and individual player statistics
   - Comprehensive performance metrics

## Architecture

### 3-Stage Simulation Workflow

The demo uses the **SimulationWorkflow system** for standardized game simulation execution:

```
SimulationWorkflow
    ↓ Stage 1: Simulation
GameEvent.simulate() → EventResult
    ↓ Stage 2: Statistics
PlayerStatsQueryService.get_live_stats() → List[PlayerStats]
    ↓ Stage 3: Persistence (optional)
GamePersistenceOrchestrator → CompositePersistenceResult
```

**Benefits:**
- ✅ **Reusable**: Same workflow pattern across demos, testing, and season simulation
- ✅ **Toggleable**: Enable/disable persistence for different use cases
- ✅ **Configurable**: Custom database paths and dynasty isolation
- ✅ **Standardized**: Consistent result objects and error handling
- ✅ **Extensible**: Factory methods for common scenarios

See `docs/how-to/simulation-workflow.md` for comprehensive documentation.

## Running the Demo

### Prerequisites

```bash
# Ensure Python 3.13.5 and dependencies are installed
source .venv/bin/activate  # Activate virtual environment

# Install required Node.js dependencies (for SQLite bindings)
npm install
```

### Quick Start

```bash
# Run the complete demo
PYTHONPATH=src python demo/game_simulation_persistance_demo/game_simulation_persistance_demo.py
```

The demo will:
1. Initialize isolated database with automatic schema creation
2. Create and store a game event
3. Execute **3-Stage Simulation Workflow**:
   - **Stage 1**: Simulate the game (Browns @ Vikings, Week 13)
   - **Stage 2**: Gather comprehensive player statistics
   - **Stage 3**: Persist all game data (game result, player stats, standings)
4. Display workflow results and success metrics
5. Show complete box scores for both teams
6. Demonstrate workflow result management

### Query Persisted Data

After running the demo, you can query the persisted data:

```bash
# View persisted games, stats, and standings
PYTHONPATH=src python demo/game_simulation_persistance_demo/query_persisted_data.py
```

This shows:
- All simulated games
- Top performers (passing, rushing, receiving)
- Current standings
- Detailed game statistics

### Initialize Database (Optional)

The demo automatically creates tables, but you can also manually initialize:

```bash
# Create database schema
PYTHONPATH=src python demo/game_simulation_persistance_demo/initialize_demo_db.py
```

## Output Example

### 3-Stage Workflow Results

```
================================================================================
                        EXECUTING 3-STAGE SIMULATION WORKFLOW
================================================================================
Matchup: Cleveland Browns @ Minnesota Vikings

🔧 Workflow Configuration:
   Persistence: ENABLED
   Database: demo/game_simulation_persistance_demo/data/demo_events.db
   Dynasty: demo_dynasty

================================================================================
🔄 SIMULATION WORKFLOW EXECUTION
================================================================================
Persistence: ENABLED
Database: demo/game_simulation_persistance_demo/data/demo_events.db
Dynasty: demo_dynasty

🎮 Stage 1: Running Simulation...
   Teams: 7 @ 16
   ✅ Simulation complete (2.34s)
   Final Score: 21-17
   Total Plays: 142

📊 Stage 2: Gathering Statistics...
   ✅ Statistics gathered for 87 players
   Home team players: 44
   Away team players: 43

💾 Stage 3: Persisting Data...
   Database: demo/game_simulation_persistance_demo/data/demo_events.db
   Dynasty: demo_dynasty
   Game ID: 7_16_20251002_145147
   Persisting: Game result + 87 player stats
   ✅ Persistence complete
   Status: success

================================================================================
✅ WORKFLOW COMPLETE
================================================================================
Total Duration: 2.89s
Simulation Success: True
Player Stats Count: 87
Persistence Status: success
Final Score: 21-17 (Winner: away)
================================================================================
```

### Box Score Example

```
================================================================================
                           Cleveland Browns - PASSING
================================================================================
Player               C/Att      Yards   TD    INT   Sacks   Rate   Cmp%
--------------------------------------------------------------------------------
Joe Flacco           28/50      336     0     1     4       68.4   56.0%

================================================================================
                           Cleveland Browns - RUSHING
================================================================================
Player                    Att    Yards    Avg    TD
--------------------------------------------------------------------------------
Jerome Ford               20     60       3.0    0

================================================================================
                          Cleveland Browns - RECEIVING
================================================================================
Player                    Rec/Tgt    Yards    Avg    TD
--------------------------------------------------------------------------------
David Njoku               4/5        47       11.8   0
Blake Whiteheart          4/5        60       15.0   0
Isaiah Bond               3/4        43       14.3   0
```

## Database Schema

The demo uses three main tables:

### games
Stores game results and metadata
```sql
CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_score INTEGER NOT NULL,
    away_score INTEGER NOT NULL,
    total_plays INTEGER,
    game_duration_minutes INTEGER,
    ...
);
```

### player_game_stats
Tracks individual player performance
```sql
CREATE TABLE player_game_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    position TEXT NOT NULL,
    passing_yards INTEGER DEFAULT 0,
    rushing_yards INTEGER DEFAULT 0,
    receiving_yards INTEGER DEFAULT 0,
    tackles_total INTEGER DEFAULT 0,
    ...
);
```

### standings
Maintains team records and standings
```sql
CREATE TABLE standings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    points_for INTEGER DEFAULT 0,
    points_against INTEGER DEFAULT 0,
    ...
);
```

## Files

```
demo/game_simulation_persistance_demo/
├── README.md                              # This file
├── game_simulation_persistance_demo.py    # Main demo (with persistence)
├── query_persisted_data.py                # Query tool for persisted data
├── initialize_demo_db.py                  # Manual database initialization
└── data/
    └── demo_events.db                     # Isolated demo database
```

## Database Isolation

The demo uses its own isolated database (`data/demo_events.db`) that:
- ✅ Does not affect production databases
- ✅ Can be safely deleted and recreated
- ✅ Demonstrates dynasty-based data separation
- ✅ Shows realistic multi-game persistence patterns

## Extending the Demo

### Use in Other Demos

The SimulationWorkflow system is designed for reusability:

```python
from workflows import SimulationWorkflow

# Demo with persistence
workflow = SimulationWorkflow.for_demo("your_demo.db", "your_dynasty")
result = workflow.execute(game_event)

if result.was_successful():
    scores = result.get_game_score()
    print(f"Final Score: {scores['away_score']}-{scores['home_score']}")
    print(f"Winner: {result.get_game_winner()}")

# Testing without persistence
test_workflow = SimulationWorkflow.for_testing()
test_result = test_workflow.execute(game_event)

# Season simulation with performance optimizations
season_workflow = SimulationWorkflow.for_season("season.db", "dynasty")
for game in season_games:
    result = season_workflow.execute(game)
```

### Add Custom Persistence Strategies

The workflow system supports custom persistence strategies:

```python
from persistence.demo import CustomDemoPersister

# Custom persistence strategy
custom_persister = CustomDemoPersister(your_config)

# Use with workflow
workflow = SimulationWorkflow(
    enable_persistence=True,
    persister_strategy=custom_persister,
    dynasty_id="custom_dynasty"
)

result = workflow.execute(game_event)
```

## Performance

Typical 3-stage workflow performance metrics:
- **Stage 1 (Simulation)**: ~2-3 seconds for full game
- **Stage 2 (Statistics)**: ~0.1ms for 90 players
- **Stage 3 (Persistence)**: ~0.6ms for complete game data
- **Total Workflow**: ~2.5-3.5 seconds end-to-end

The workflow system is optimized for both development visibility and production performance.

## Troubleshooting

### Database Errors

If you see "no such table" errors:
1. The demo automatically creates tables on first run
2. If issues persist, manually run: `python initialize_demo_db.py`
3. Delete `data/demo_events.db` and let the demo recreate it

### Import Errors

Ensure you run with proper Python path:
```bash
PYTHONPATH=src python demo/game_simulation_persistance_demo/game_simulation_persistance_demo.py
```

### Player Stats Not Showing

This is expected if:
- Player had no touches in the game (0 stats)
- Position-specific stats filters apply (e.g., QBs with no pass attempts)

## Next Steps

1. **Run the demo** to see the 3-stage simulation workflow in action
2. **Query the data** using `query_persisted_data.py`
3. **Review the workflow documentation** in `docs/how-to/simulation-workflow.md`
4. **Integrate into your demos** using the same workflow pattern

## Support

For questions or issues:
- Review workflow documentation: `docs/how-to/simulation-workflow.md`
- Check main project README: `CLAUDE.md`
- Examine code examples in this demo

---

**Part of The Owners Sim - NFL Football Simulation Engine**
