# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is "The Owners Sim" - a comprehensive NFL football simulation engine written in Python. The project simulates realistic NFL gameplay with detailed player statistics, penalty systems, team management, and formation-based play calling.

## Development Environment

- **Python Version**: 3.13.5 (required, venv configured)
- **Virtual Environment**: `.venv/` (Note: Python 3.13 binary path may need reconfiguration)
- **Dependencies**: SQLite3 support via better-sqlite3 (Node.js binding)
- **Package Manager**: npm for Node.js dependencies, pip for Python
- **Database**: SQLite3 with dynasty-based isolation support

## Core Commands

### Running Tests
```bash
# Run all tests with pytest
python -m pytest tests/

# Run a single test file
python -m pytest tests/test_penalty_system.py

# Run tests with verbose output
python -m pytest -v tests/

# Run tests matching a pattern
python -m pytest -k "penalty" tests/

# Run specific test function
python -m pytest tests/test_game_loop_controller.py::TestGameLoopController::test_full_game_simulation

# Note: Many test files have been removed. Check test availability before running.
# The following patterns show how to run tests if they exist:

# Schedule generator tests (if available in tests/test_scheduling/)
python -m pytest tests/test_scheduling/ -v

# Playoff system tests (if available)
python -m pytest tests/playoff_system/ -v

# Core functionality tests (run if files exist)
PYTHONPATH=src python tests/test_penalty_system.py
PYTHONPATH=src python tests/test_game_state_manager.py
PYTHONPATH=src python tests/test_drive_manager.py
PYTHONPATH=src python tests/test_game_loop_controller.py

# Integration tests (if available)
PYTHONPATH=src python tests/test_phase_2_integration.py
PYTHONPATH=src python tests/test_daily_persister.py

# Validation scripts (if available)
python tests/simple_penalty_validation.py

# Diagnostic scripts (run from project root)
PYTHONPATH=src python team_corruption_tracker.py
PYTHONPATH=src python simple_stats_check.py
PYTHONPATH=src python verify_player_stats_persistence.py
PYTHONPATH=src python debug_touchdown_detection.py  # Debug touchdown scoring issues
```

### Running Demos
```bash
# Primary demos
PYTHONPATH=src python cleveland_browns_vs_houston_texans_demo.py  # Complete Browns vs Texans game demo
PYTHONPATH=src python demo.py  # Main demo entry point
PYTHONPATH=src python test_full_game_simulator.py  # Full game simulator test

# Interactive Season Simulation (PRIMARY INTERFACE)
PYTHONPATH=src python demo/interactive_season_sim/interactive_season_sim.py
# Terminal-based interactive NFL season simulation with comprehensive controls:
# - Day-by-day or week-by-week simulation
# - View standings, upcoming games, season summary
# - Playoff picture tracking (Week 10+)
# - Full database persistence with dynasty support
# See demo/interactive_season_sim/QUICK_START.md for detailed usage

# Season Simulation Utilities
PYTHONPATH=src python demo/interactive_season_sim/initialize_season_db.py  # Initialize new season database
PYTHONPATH=src python demo/interactive_season_sim/schedule_generator_example.py  # Generate season schedule

# Playoff System Demo
PYTHONPATH=src python demo/playoff_seeder_demo/playoff_seeder_demo.py  # NFL playoff seeding and tiebreaker demonstration

# Legacy interactive interface (if available)
PYTHONPATH=src python src/demo/interactive_interface.py  # Older team/season management interface

# Component demos (in demo/ directory)
PYTHONPATH=src python demo/pass_play_demo.py  # Pass play simulation demonstration
PYTHONPATH=src python demo/play_engine_demo.py  # Play engine core demonstration
PYTHONPATH=src python demo/run_play_demo.py  # Run play simulation demonstration

# System demos (if available)
PYTHONPATH=src python persistence_control_example.py  # Optional persistence control (if exists)
PYTHONPATH=src python database_flexibility_demo.py  # Flexible database configuration (if exists)
PYTHONPATH=src python dynasty_context_demo.py  # Dynasty isolation and management (if exists)
```

### Diagnostic Scripts
```bash
# All diagnostic scripts require PYTHONPATH=src prefix
PYTHONPATH=src python team_corruption_tracker.py  # Track team data corruption (if exists)
PYTHONPATH=src python verify_player_stats_persistence.py  # Verify player stats (if exists)
PYTHONPATH=src python simple_stats_check.py  # Simple statistics validation (if exists)
PYTHONPATH=src python snap_tracking_diagnostic.py  # Snap count tracking diagnostics (if exists)
PYTHONPATH=src python debug_game_result_structure.py  # Debug game result issues (if exists)

# Player data migration (if migration script exists)
PYTHONPATH=src python scripts/migrate_players_to_teams.py

# Check logs for debugging
tail -f detailed_transaction_tracking.log  # If persistence logging is enabled
```

### Development Setup
```bash
# Activate virtual environment (Python 3.13.5 required)
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Note: If Python 3.13 path error occurs, reconfigure venv:
# python3.13 -m venv .venv --clear

# Install Node.js dependencies (for SQLite3 bindings)
npm install  # Installs better-sqlite3 and @types/better-sqlite3

# Install Python dependencies (minimal required)
pip install pytest  # Core testing framework

# Optional development tools (install as needed):
# pip install black  # Code formatting
# pip install mypy  # Type checking
# pip install pylint  # Code quality
# pip install pytest-benchmark  # Performance testing
```

### Code Quality Tools
```bash
# Code formatting (install black if needed: pip install black)
black src/ tests/

# Type checking (install mypy if needed: pip install mypy)
mypy src/

# Code quality analysis (install pylint if needed: pip install pylint)
pylint src/

# Note: These tools can be installed individually as needed for development
```

## Architecture Overview

### Core System Design

The simulation follows a layered architecture with clear separation of concerns:

**1. Play Engine Core (`src/play_engine/core/`)**
- `engine.py`: Main play simulation orchestrator using match/case statements
- `play_result.py`: Unified PlayResult class (single source of truth replacing result.py)
- `params.py`: Play execution parameters

**2. Play Types (`src/play_engine/play_types/`)**
- Strategy pattern implementation for different play types
- `offensive_types.py`: RUN, PASS, FIELD_GOAL, PUNT, KICKOFF, TWO_POINT_CONVERSION
- `defensive_types.py`: Defensive play type constants
- `punt_types.py`: Specialized punt play variations
- Supports 6 core play types with consolidated PASS handling (includes PLAY_ACTION_PASS and SCREEN_PASS)

**2a. Play Call System (`src/play_engine/play_calls/`)**
- `play_call_factory.py`: Factory pattern for creating structured play calls
- `offensive_play_call.py`: Offensive play call encapsulation with formations and concepts
- `defensive_play_call.py`: Defensive play call structure and logic
- `special_teams_play_call.py`: Special teams play call with formation and strategy support

**2b. Coaching Staff and Play Calling (`src/play_engine/play_calling/`)**
- `coaching_staff.py`: Complete coaching staff system with coordinator hierarchy
- `head_coach.py`, `offensive_coordinator.py`, `defensive_coordinator.py`: Position-specific coaching logic
- `special_teams_coordinator.py`: Dedicated special teams play calling and decisions
- `coach_archetype.py`: Coaching philosophy and style definitions
- `playbook_loader.py`: Dynamic playbook loading system
- `game_situation_analyzer.py`: Context-aware play selection logic
- `fourth_down_matrix.py`: Advanced fourth down decision making
- `play_caller.py`, `staff_factory.py`: Play calling orchestration and staff creation

**3. Play Mechanics (`src/play_engine/mechanics/`)**
- `formations.py`: Formation system with personnel packages
- `unified_formations.py`: Type-safe enum-based formation system with context-aware naming
- `penalties/`: Comprehensive NFL penalty system with JSON configuration

**4. Team Management (`src/team_management/`)**
- JSON-based team data system using numerical team IDs (1-32)
- `team_data_loader.py`: Team metadata management
- `players/player.py`: Player attributes including penalty-related stats
- `personnel.py`: Personnel package management

**5. Simulation Engine (`src/play_engine/simulation/`)**
- `run_plays.py`: Advanced run play simulation with formation matchups
- `pass_plays.py`: Pass play simulation with coverage analysis
- `punt.py`: Punt simulation with returner mechanics
- `field_goal.py`: Field goal attempt simulation
- `kickoff.py`: Kickoff and return simulation
- `stats.py`: Play statistics tracking

**6. Game State Management (`src/play_engine/game_state/`)**
- `game_state_manager.py`: Unified field position and down situation tracking
- `field_position.py`: Field tracking with scoring detection
- `down_situation.py`: Down and distance progression
- `drive_manager.py`: Drive lifecycle management and drive ending decisions

**7. Game Management (`src/game_management/`)**
- `game_loop_controller.py`: Complete game loop orchestration coordinating all components
- `scoreboard.py`: Game scoreboard management with quarter/game progression
- `scoring_mapper.py`: Maps play results to scoring events and point attribution
- `full_game_simulator.py`: Modular full game simulator for incremental development
- `game_manager.py`: Complete game orchestration with coin toss and game flow
- `drive_transition_manager.py`: Handles drive transitions and special teams scenarios
- `box_score_generator.py`: NFL-style box score generation from player statistics
- `play_by_play_display.py`: Real-time game commentary and formatting system
- `game_stats_reporter.py`: Comprehensive end-of-game reporting and analysis

**8. Core Utilities (root level)**
- `src/constants/team_ids.py`: Team ID constants and utilities

**9. Data Management (`src/database/`, `src/stores/`, `src/persistence/`)**
- `database/api.py`: Clean database API for data retrieval (single source of truth)
- `database/connection.py`: SQLite database connection management
- `stores/base_store.py`: In-memory data store abstraction
- `stores/standings_store.py`: NFL standings and team performance tracking
- `persistence/daily_persister.py`: Daily simulation data persistence

**10. Shared Components (`src/shared/`)**
- Common utilities and shared data structures
- Cross-system interfaces and abstractions

**11. Team Registry (`src/team_registry/`)**
- Enhanced team management and metadata system
- Team attribute and characteristic management

**12. Schedule Generator (`src/scheduling/`)**
- `data/division_structure.py`: NFL organizational structure with 32 teams
- `data/schedule_models.py`: ScheduledGame, WeekSchedule, SeasonSchedule models
- `config.py`: Comprehensive configuration for schedule generation
- `utils/date_utils.py`: NFL season date calculations and utilities
- `validators/`: Schedule validation and constraint checking (future)
- `generator/`: Schedule generation algorithms (future phases)
- `converters/`: Schedule to event conversion utilities

**13. Playoff System (`src/playoff_system/`)**
- `seeding/`: Complete NFL playoff seeding system with tiebreaker resolution
- `management/`: Playoff tournament management and bracket generation
- `constants/`: Playoff configuration and team structure definitions
- `persistence/`: Playoff data storage and retrieval
- `validation/`: Playoff bracket validation and integrity checks
- `utils/`: Playoff calculation utilities and helper functions

**14. Calendar System (`src/calendar/`)**
- `calendar_manager.py`: Database-backed calendar system for event scheduling
- `event_manager.py`: Event creation, modification, and lifecycle management
- `calendar_database_api.py`: Calendar-specific database operations and queries
- `event.py`: Event data structures and models
- `event_store.py`: In-memory event storage for fast access
- `event_factory.py`: Factory methods for creating different event types
- `simulation_executor.py`: Executes game simulations from calendar events
- `migration_helper.py`: Database migration utilities for calendar system

**15. User Team Management (`src/user_team/`)**
- `user_team_manager.py`: User team selection, preferences, and management
- Dynasty mode user interaction and team ownership simulation

**16. Season Management (`src/season/`)**
- `season_manager.py`: Season-level management and coordination
- Season progression and state management

**17. Dynasty System (`src/dynasty/`)**
- `dynasty_manager.py`: Dynasty lifecycle management, configuration, and metadata operations
- Provides separation between dynasty management and season progression
- Manages dynasty creation, team registry coordination, and validation

### Key Design Patterns

**Match/Case Play Selection**: The main play engine uses Python's match/case for clean play type routing:
```python
match offensive_play_type:
    case OffensivePlayType.RUN:
        # Run play logic
    case OffensivePlayType.PASS | OffensivePlayType.PLAY_ACTION_PASS | OffensivePlayType.SCREEN_PASS:
        # All pass plays handled together
    case _:
        raise ValueError(f"Unhandled play type: {offensive_play_type}")
```

**Unified Formation System**: Type-safe enum-based formations with context-aware naming:
```python
class UnifiedDefensiveFormation(Enum):
    # Single formation definition with different names for different contexts
    # coordinator_name="punt_return", punt_name="defensive_punt_return"
```

**Coaching Staff Architecture**: Hierarchical coaching system with realistic NFL roles:
```python
# CoachingStaff -> HeadCoach -> OffensiveCoordinator/DefensiveCoordinator/SpecialTeamsCoordinator
# Each coach has archetype-based decision making and situational logic
# Special teams coordinator handles punts, field goals, kickoffs independently
```

**JSON Configuration System**: All game data is externalized:
- `src/data/teams.json`: Complete NFL team dataset with numerical IDs
- `src/config/penalties/`: 5 JSON files for penalty configuration
- `src/config/coaching_staff/`: Individual coach profiles with realistic NFL coaching styles
- `src/config/playbooks/`: Team strategic approaches and play selection preferences
- `src/config/team_coaching_styles.json`: Maps all 32 NFL teams to coaching philosophies
- Supports designer-friendly configuration without code changes

**Two-Phase Penalty Integration**:
1. Phase 1: Base play outcome using formation matchup matrix
2. Phase 2A: Penalty determination and effects
3. Phase 2B: Player statistics attribution

**Database-Driven Persistence Architecture**:
- In-memory stores for fast access during simulation
- `DatabaseAPI` as single source of truth for data retrieval
- `DailyDataPersister` for batch persistence after each simulation day
- SQLite database for permanent storage with dynasty support

**Game Simulation Integration**:
- `GameSimulationEvent`: Standalone wrapper for individual NFL games
- `FullGameSimulator`: Core game simulation engine
- `StoreManager`: Game result persistence and statistics tracking
- Modular design for flexible game scheduling

## Data Management

### Team System
- Uses numerical team IDs (1-32) instead of team names
- Access via `TeamIDs.DETROIT_LIONS` constants or `get_team_by_id(22)`
- Rich metadata including colors, divisions, conferences
- Division rivals and random matchup generation

### Player System
- Players have penalty-related attributes: `discipline`, `composure`, `experience`, `penalty_technique`
- Team-aware player names (e.g., "Detroit Starting QB")
- Position-based roster generation
- **Team-Based Files**: Player data now stored in individual team files (`src/data/players/team_XX_team_name.json`)
- **Backward Compatibility**: `PlayerDataLoader` supports both team-based and legacy single-file formats
- **Migration Support**: Use `scripts/migrate_players_to_teams.py` for data migration between formats

### Configuration Files
- `src/config/penalties/penalty_rates.json`: Base penalty rates
- `src/config/penalties/discipline_effects.json`: Player discipline modifiers
- `src/config/penalties/situational_modifiers.json`: Field position/down effects
- `src/config/penalties/penalty_descriptions.json`: Contextual descriptions
- `src/config/penalties/home_field_settings.json`: Home field advantage
- `src/config/coaching_staff/`: Individual coach profiles (head_coaches/, offensive_coordinators/, defensive_coordinators/)
- `src/config/playbooks/`: Team playbook strategies (aggressive.json, balanced.json, conservative.json)
- `src/config/team_coaching_styles.json`: Team-specific coaching staff assignments (maps team IDs to coaching styles)
- `src/play_engine/config/`: Play-specific configuration files (run_play_config.json, pass_play_config.json, field_goal_config.json, kickoff_config.json, punt_config.json)
- `data/database/nfl_simulation.db`: SQLite database for persistent storage
- Dynasty context and season initialization configurations

## Testing Strategy

The project uses multiple testing approaches:

1. **Unit Tests** (`tests/`): Traditional pytest-based unit testing
2. **Interactive Testing**: Menu-driven play-by-play testing and validation scripts
3. **Validation Scripts** (`quick_test.py`, `simple_penalty_validation.py`): Automated validation
4. **Demo Scripts**: Full system demonstrations with realistic scenarios

## Documentation

Comprehensive documentation is available in `docs/`:

- **Architecture**: `docs/architecture/play_engine.md` - Core system architecture documentation
- **Database Schema**: `docs/schema/database_schema.md` - Complete SQLite schema v2.0.0 documentation with table definitions, indexes, and query examples
- **System Summaries**:
  - `docs/PENALTY_SYSTEM_SUMMARY.md` - Penalty system overview
  - `docs/TEAM_SYSTEM_SUMMARY.md` - Team management system details
  - `docs/TEST_GUIDE.md` - Testing guidelines and approaches
- **How-To Guides**:
  - `docs/how-to/full_game_simulator_usage.md` - FullGameSimulator configuration and usage
  - `docs/how-to/nfl_schedule_generator_usage.md` - NFL schedule generation
  - `docs/how-to/simulation-workflow.md` - Complete simulation workflow guide
- **Planning Documents**: `docs/plans/` - Architecture plans and data flow analysis
- **Interactive Season Sim**: `demo/interactive_season_sim/QUICK_START.md` - Quick start guide for interactive season simulation

## Common Issues and Troubleshooting

### Database Issues
- **Empty stats/standings**: Run diagnostic scripts like `team_corruption_tracker.py` or `simple_stats_check.py`
- **Transaction failures**: Check `detailed_transaction_tracking.log` for persistence errors
- **Data inconsistency**: Use validation scripts in tests/ directory for verification

### Testing Issues
- **Test failures**: Always run with `PYTHONPATH=src` or `PYTHONPATH=.` prefix for imports
- **Module not found**: Ensure virtual environment is activated and dependencies installed
- **Performance issues**: Install and use `pytest-benchmark` if needed for performance testing

### Development Workflow
- **Before committing**: Run relevant tests and consider using black/pylint if available
- **New features**: Follow existing patterns and add corresponding tests
- **Team ID validation**: Always use numerical IDs (1-32), never team name strings

## Key Implementation Details

### NFL Realism
- Penalty rates: 20-30% per play (NFL realistic)
- Home field advantage: 10-15% penalty reduction
- Situational modifiers: Red zone +40% penalties, 4th down +25%
- Discipline impact: Low discipline teams get 1.4x more penalties

### Formation System
- Formation-based personnel selection
- Offensive/defensive formation compatibility validation
- Personnel package management for different play types
- Type-safe enum-based formations eliminate string-based bugs
- Context-aware naming (coordinator vs simulator vs display names)

### Coaching Staff Integration
- Realistic NFL coaching hierarchies (Head Coach → Coordinators)
- Coach archetypes: ultra_conservative, conservative, balanced, aggressive, ultra_aggressive
- Position-specific specialties: pass_heavy, run_heavy, balanced offensive styles
- Situational decision making: fourth down matrix, game situation analysis
- Team-specific coaching assignments for all 32 NFL teams
- Special teams coordinator: Dedicated special teams philosophy (aggressive, conservative, balanced)

### Error Handling
- Comprehensive validation for team IDs (must be 1-32)
- Graceful handling of invalid play types with descriptive errors
- Clear migration paths for breaking changes

### Persistence Control
- **Optional Statistics Persistence**: Control whether game statistics are saved to database
- **Constructor Parameter**: `enable_persistence=False` to disable persistence at creation
- **Runtime Property**: `simulator.persistence = False` to toggle persistence on/off
- **Performance Benefits**: No database I/O overhead when persistence is disabled
- **Use Cases**: Quick demos, testing, performance benchmarks, standalone simulations
- **Default Behavior**: Persistence enabled by default for backward compatibility
- **Clear Feedback**: System provides clear messages when persistence is disabled/enabled

```python
# Disable persistence at creation
simulator = FullGameSimulator(away_team_id=7, home_team_id=9, enable_persistence=False)

# Toggle persistence via property
simulator.persistence = False  # Disable database saves
simulator.persistence = True   # Re-enable database saves

# Check persistence status
if simulator.persistence:
    print("Statistics will be saved to database")
else:
    print("Statistics will not be saved (demo mode)")
```

### Database Flexibility
- **Flexible Database Configuration**: Choose which database to persist statistics to
- **Constructor Parameter**: `database_path="custom.db"` to set database at creation
- **Runtime Property**: `simulator.database_path = "new.db"` to change database path
- **Automatic Service Recreation**: Statistics service recreated when database path changes
- **Multiple Use Cases**: Dynasty management, season isolation, testing with in-memory databases
- **Default Behavior**: Uses `"data/database/nfl_simulation.db"` if not specified
- **Error Handling**: Graceful fallback if database path change fails

```python
# Set custom database at creation
simulator = FullGameSimulator(away_team_id=7, home_team_id=9, database_path="my_dynasty.db")

# User's preferred pattern: set database, then enable persistence
simulator = FullGameSimulator(away_team_id=7, home_team_id=9, enable_persistence=False)
simulator.database_path = "season_2024.db"
simulator.persistence = True

# Runtime database switching
simulator.database_path = "playoff_games.db"  # Auto-recreates service if persistence enabled

# Testing with in-memory database
simulator = FullGameSimulator(..., database_path=":memory:")

# Dynasty management example
simulator.database_path = f"dynasty_{user_team_name}.db"
simulator.persistence = True
```

### Dynasty Context
- **Dynasty Isolation**: Complete statistical separation between different dynasties
- **Constructor Parameter**: `dynasty_id="my_dynasty"` to set dynasty context at creation
- **Runtime Property**: `simulator.dynasty_id = "new_dynasty"` to change dynasty context
- **Automatic Service Recreation**: Statistics service recreated when dynasty context changes
- **Combined Flexibility**: Works seamlessly with database path configuration
- **Default Behavior**: Uses `"default_dynasty"` if not specified
- **Multiple Dynasties**: Can run multiple dynasties in same database or separate databases

```python
# Set custom dynasty at creation
simulator = FullGameSimulator(away_team_id=7, home_team_id=9, dynasty_id="eagles_rebuild")

# User's preferred pattern: set dynasty, then enable persistence
simulator = FullGameSimulator(away_team_id=7, home_team_id=9, enable_persistence=False)
simulator.dynasty_id = "chiefs_championship_run"
simulator.persistence = True

# Combined database and dynasty flexibility
simulator.database_path = "dynasties/eagles.db"
simulator.dynasty_id = "eagles_superbowl_quest"
simulator.persistence = True

# Runtime dynasty switching
simulator.dynasty_id = "eagles_rebuild_2024"  # Auto-recreates service if persistence enabled

# Multiple dynasty management
eagles_sim = FullGameSimulator(..., dynasty_id="eagles_legacy", database_path="dynasties/eagles.db")
chiefs_sim = FullGameSimulator(..., dynasty_id="chiefs_dynasty", database_path="dynasties/chiefs.db")

# Same database, different dynasties
sim1 = FullGameSimulator(..., dynasty_id="user1_dynasty", database_path="shared.db")
sim2 = FullGameSimulator(..., dynasty_id="user2_dynasty", database_path="shared.db")
```

### Interactive Season Simulation
- Season simulation available through `src/demo/` components
- **Daily Mode**: Day-by-day simulation with detailed control via `daily_simulation_controller.py`
- **Weekly Mode**: Week-by-week simulation for faster progression via `weekly_simulation_controller.py`
- **Interactive Interface**: Comprehensive season management through `interactive_interface.py`
- **Statistics Persistence**: Automatic saving of player and team statistics to SQLite database
- **Real-time Standings**: Live tracking of division and conference standings
- **Dynasty Support**: Multi-season dynasty management with persistent data

## Recent Architecture Changes

Key architectural updates in the codebase:

1. **Dynasty System Addition**: New `src/dynasty/` module with `DynastyManager` for dynasty lifecycle management
2. **Test Suite Reorganization**: Many test files have been removed or relocated - verify test file existence before running
3. **Demo Consolidation**: Primary demos now in root directory (`cleveland_browns_vs_houston_texans_demo.py`, `demo.py`, `test_full_game_simulator.py`)
4. **Player Data Structure**: Team-based player files in `src/data/players/team_XX_team_name.json` format
5. **Database Flexibility**: Support for custom database paths and dynasty isolation in `FullGameSimulator`
6. **Persistence Control**: Optional statistics persistence via `enable_persistence` parameter
7. **Calendar System**: Database-backed calendar for event scheduling (some demos removed)
8. **Coaching Staff Integration**: All 32 NFL teams mapped to coaching philosophies in `team_coaching_styles.json`

## Key Implementation Notes

- **Team IDs**: Always use numerical IDs (1-32) via `TeamIDs` constants
- **Python Version**: Requires Python 3.13.5 (venv may need reconfiguration if path errors occur)
- **Testing**: Use `PYTHONPATH=src` prefix for most test runs
- **Database**: SQLite with dynasty-based isolation support
- **Node Dependencies**: `better-sqlite3` provides SQLite bindings for Python integration