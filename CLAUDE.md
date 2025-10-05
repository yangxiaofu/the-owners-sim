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

### Running the UI Application
```bash
# Install UI dependencies (first time only)
pip install -r requirements-ui.txt

# Launch desktop application (PySide6/Qt)
python main.py

# Test UI imports
python test_ui.py
```

### Running Tests
```bash
# Current test structure (organized by feature):
# tests/calendar/ - Calendar system tests
# tests/playoff_system/ - Playoff system tests
# tests/salary_cap/ - Salary cap system tests
# tests/conftest.py - Shared pytest fixtures

# Run all tests with pytest
python -m pytest tests/

# Run tests for specific modules
python -m pytest tests/calendar/ -v         # Calendar system tests
python -m pytest tests/playoff_system/ -v   # Playoff system tests
python -m pytest tests/salary_cap/ -v       # Salary cap tests

# Run tests with verbose output
python -m pytest -v tests/

# Run tests matching a pattern
python -m pytest -k "calendar" tests/
python -m pytest -k "playoff" tests/

# Run specific test file
python -m pytest tests/salary_cap/test_cap_calculator.py -v

# Note: Legacy test files have been reorganized into feature-specific directories.
# If you need to test core play engine or game management components, use demos instead.
```

### Running Demos
```bash
# Full Season Simulation (PRIMARY - Complete Season Cycle)
PYTHONPATH=src python demo/full_season_demo/full_season_sim.py
# Interactive NFL season simulation from Week 1 → Super Bowl → Offseason
# Uses SeasonCycleController (src/season/season_cycle_controller.py)
# - All 3 phases: Regular Season, Playoffs, Offseason
# - Automatic phase transitions
# - Real playoff seeding from standings
# - Dynasty isolation with database persistence
# See docs/plans/full_season_simulation_plan.md for architecture details

# Interactive Season Simulation (Regular Season Only)
PYTHONPATH=src python demo/interactive_season_sim/interactive_season_sim.py
# Terminal-based interactive NFL regular season simulation:
# - Day-by-day or week-by-week simulation
# - View standings, upcoming games, season summary
# - Playoff picture tracking (Week 10+)
# - Full database persistence with dynasty support
# - Stops after Week 18 (use full_season_sim.py for playoffs)
# See demo/interactive_season_sim/README.md for detailed usage

# Interactive Playoff Simulation (Playoffs Only)
PYTHONPATH=src python demo/interactive_playoff_sim/interactive_playoff_sim.py
# Terminal-based interactive NFL playoff simulation:
# - Uses centralized PlayoffController (src/playoff_system/playoff_controller.py)
# - Day/week/round advancement controls
# - Wild Card → Divisional → Conference → Super Bowl
# - Complete playoff bracket display
# - Supports random OR real seeding from regular season
# See demo/interactive_playoff_sim/README.md for usage

# Season Simulation Utilities
PYTHONPATH=src python demo/interactive_season_sim/initialize_season_db.py  # Initialize new season database
PYTHONPATH=src python demo/interactive_season_sim/schedule_generator_example.py  # Generate season schedule

# Playoff System Demos
PYTHONPATH=src python demo/playoff_seeder_demo/playoff_seeder_demo.py  # NFL playoff seeding and tiebreaker demonstration

# Salary Cap Demos
PYTHONPATH=src python demo/cap_calculator_demo/cap_calculator_demo.py  # Salary cap calculations and contract management
# See demo/cap_calculator_demo/README.md for detailed usage

# Play Demos (Individual Play Mechanics)
PYTHONPATH=src python demo/play_demos/pass_play_demo.py  # Pass play mechanics with real NFL players
PYTHONPATH=src python demo/play_demos/run_play_demo.py  # Run play mechanics with formation matchups
PYTHONPATH=src python demo/play_demos/play_engine_demo.py  # Player roster and personnel package management

# Root-level test scripts (Event system testing)
PYTHONPATH=src python test_event_system.py  # Event system testing
PYTHONPATH=src python test_hybrid_event_storage.py  # Hybrid event storage testing
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

# Install UI dependencies (for desktop application)
pip install -r requirements-ui.txt  # Installs PySide6, matplotlib, pyqtgraph

# Install core Python dependencies (minimal required)
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
- `database/dynasty_state_api.py`: Dynasty state management and persistence
- `database/migrations/`: Database schema migrations (dynasty_id to events, game_date to games)
- `stores/base_store.py`: In-memory data store abstraction
- `stores/standings_store.py`: NFL standings and team performance tracking
- `persistence/daily_persister.py`: Daily simulation data persistence

**10. Shared Components (`src/shared/`)**
- Common utilities and shared data structures
- Cross-system interfaces and abstractions

**11. Playoff System (`src/playoff_system/`)**
- `playoff_controller.py`: **Centralized playoff orchestration** (moved from demo/)
  - Calendar advancement, bracket management, round progression
  - Supports random OR real seeding from regular season standings
  - Dynasty isolation and flexible simulation control (day/week/round)
  - See `docs/architecture/playoff_controller.md` for details
- `seeding/`: Complete NFL playoff seeding system with tiebreaker resolution
- `management/`: Playoff tournament management and bracket generation
- `constants/`: Playoff configuration and team structure definitions
- `persistence/`: Playoff data storage and retrieval
- `validation/`: Playoff bracket validation and integrity checks
- `utils/`: Playoff calculation utilities and helper functions

**12. Calendar System (`src/calendar/`)**
- `calendar_manager.py`: Database-backed calendar system for event scheduling
- `event_manager.py`: Event creation, modification, and lifecycle management
- `calendar_database_api.py`: Calendar-specific database operations and queries
- `event.py`: Event data structures and models
- `event_store.py`: In-memory event storage for fast access
- `event_factory.py`: Factory methods for creating different event types
- `simulation_executor.py`: Executes game simulations from calendar events
- `migration_helper.py`: Database migration utilities for calendar system

**13. Season Management (`src/season/`)**
- `season_manager.py`: Basic API layer for season management (legacy)
- `season_cycle_controller.py`: **Production-ready complete season cycle orchestrator**
  - Manages all 3 phases: Regular Season → Playoffs → Offseason
  - Automatic phase transitions with calendar continuity
  - Integrates SeasonController (regular season) + PlayoffController (playoffs)
  - Real playoff seeding from regular season standings
  - Dynasty isolation and flexible persistence control
  - **Recommended for full season simulations**

**14. Offseason System (`src/offseason/`)**
- Offseason event scheduling and management
- Integration with calendar system for offseason timeline
- Support for NFL offseason phases and deadlines

**15. Workflow System (`src/workflows/`)**
- `simulation_workflow.py`: Reusable 3-stage workflow orchestrator (Simulation → Statistics → Persistence)
- `workflow_result.py`: Standardized result objects for consistent API
- Toggleable persistence, flexible configuration, and dynasty isolation support
- Used across demos, testing, and production season simulation

**16. Events System (`src/events/`)**
- `base_event.py`: Base event class and event result structures
- `game_event.py`: GameEvent for NFL game simulation with metadata
- `scouting_event.py`: Scouting and player evaluation events
- `contract_events.py`: Contract-related events (franchise tags, releases, restructures) with full cap integration
- `free_agency_events.py`: Free agency events (UFA signings, RFA offer sheets) with cap validation
- `deadline_event.py`: NFL offseason deadline events with salary cap compliance checks
- `window_event.py`: Time-bounded window events (legal tampering, OTAs, etc.)
- `milestone_event.py`: Informational milestone events (schedule release, combine, etc.)
- `draft_events.py`: Draft-related events
- `roster_events.py`: Roster management events
- `event_database_api.py`: Event storage and retrieval API
- Complete event lifecycle management and execution framework with offseason support
- **Cap Integration**: All contract/free agency events execute real salary cap operations through EventCapBridge

**17. Salary Cap System (`src/salary_cap/`)**
- `cap_calculator.py`: Core mathematical operations for all cap calculations
- `cap_validator.py`: Contract validation and compliance checking
- `contract_manager.py`: Contract lifecycle management and modifications
- `cap_database_api.py`: Database operations for contract and cap data
- `cap_utils.py`: Utility functions for cap-related operations
- `tag_manager.py`: Franchise tag, transition tag, and RFA tender management
- `event_integration.py`: Event-cap bridge connecting event system to cap operations
- Follows 2024-2025 NFL CBA rules (signing bonus proration, dead money, June 1 designations)
- Supports top-51 roster (offseason) and 53-man roster (regular season) calculations
- **Event Integration Complete**: All cap operations (franchise tags, UFA signings, releases, restructures) execute through event system
- See `docs/plans/salary_cap_plan.md` for architecture details and `docs/architecture/event_cap_integration.md` for event integration

**18. Desktop UI (`ui/`)**
- **OOTP-inspired PySide6/Qt desktop application** (Phase 1 complete)
- `main_window.py`: Main application window with tab-based navigation
- `views/`: 6 primary view modules (Season, Team, Player, Offseason, League, Game)
- `widgets/`: Reusable custom widgets (stats tables, depth charts, calendars)
- `dialogs/`: Modal dialogs for user interactions (franchise tag, free agency, draft)
- `models/`: Qt Model/View data models for efficient data display (QAbstractTableModel adapters)
- `controllers/`: **Thin** UI controllers (≤10-20 lines per method, pure orchestration)
- `domain_models/`: **NEW** Domain model layer for business logic and data access
  - CalendarDataModel, SeasonDataModel, SimulationDataModel
  - Owns database API instances (EventDatabaseAPI, DatabaseAPI, DynastyStateAPI, etc.)
  - Controllers delegate ALL business logic to domain models
  - Follows proper MVC pattern: View → Controller → Domain Model → Database API
- `resources/styles/`: QSS stylesheets (OOTP-inspired professional theme)
- **Clean separation**: UI layer completely independent of simulation engine
- **Proper MVC**: Controllers are thin orchestrators, domain models own data access
- See `docs/plans/ui_development_plan.md` and `docs/architecture/ui_layer_separation.md`

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
   - `tests/calendar/` - Calendar system tests
   - `tests/playoff_system/` - Playoff system tests
   - `tests/salary_cap/` - Salary cap system tests
   - `tests/event_system/` - Event system tests
   - `tests/conftest.py` - Shared pytest fixtures
2. **Interactive Testing**: Menu-driven play-by-play testing and validation scripts
3. **Validation Scripts** (`quick_test.py`, `simple_penalty_validation.py`): Automated validation
4. **Demo Scripts**: Full system demonstrations with realistic scenarios

## Documentation

Comprehensive documentation is available in `docs/`:

- **Architecture**:
  - `docs/architecture/play_engine.md` - Core system architecture documentation
  - `docs/architecture/playoff_controller.md` - Playoff controller centralization and architecture
  - `docs/architecture/event_cap_integration.md` - Event-salary cap integration bridge pattern
  - `docs/architecture/ui_layer_separation.md` - **UI MVC architecture with domain model layer** (View → Controller → Domain Model → Database API)
- **Database Schema**: `docs/schema/database_schema.md` - Complete SQLite schema v2.0.0 documentation with table definitions, indexes, and query examples
- **System Summaries**:
  - `docs/PENALTY_SYSTEM_SUMMARY.md` - Penalty system overview
  - `docs/TEAM_SYSTEM_SUMMARY.md` - Team management system details
  - `docs/TEST_GUIDE.md` - Testing guidelines and approaches
- **How-To Guides**:
  - `docs/how-to/full_game_simulator_usage.md` - FullGameSimulator configuration and usage
  - `docs/how-to/nfl_schedule_generator_usage.md` - NFL schedule generation
  - `docs/how-to/simulation-workflow.md` - Complete simulation workflow guide
- **Planning Documents**:
  - `docs/plans/full_season_simulation_plan.md` - **ACTIVE**: Unified season simulation (regular season → playoffs → offseason)
  - `docs/plans/ui_development_plan.md` - **ACTIVE**: Desktop UI development roadmap (Phase 1 complete, Phase 2 in progress)
  - `docs/plans/events_dynasty_isolation_plan.md` - **PENDING**: Migration plan for adding dynasty_id column to events table
  - `docs/plans/offseason_plan.md` - Offseason system implementation (complete)
  - `docs/plans/salary_cap_plan.md` - Salary cap system design
  - `docs/plans/playoff_manager_plan.md` - Playoff system architecture and design
  - `docs/plans/calendar_manager_plan.md` - Calendar system design
- **Specifications**:
  - `docs/specifications/player_generator_system.md` - Player generation system design
- **Interactive Demos**:
  - `demo/interactive_season_sim/QUICK_START.md` - Quick start guide for interactive season simulation
  - `demo/interactive_playoff_sim/` - Interactive playoff simulator documentation

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

### Salary Cap System Integration
- **Event-Driven Operations**: All cap operations execute through event system via EventCapBridge pattern
- **Supported Events**:
  - FranchiseTagEvent/TransitionTagEvent: Create 1-year contracts with tag salaries
  - UFASigningEvent: Validate cap space and create veteran contracts
  - PlayerReleaseEvent: Calculate dead money (standard or June 1 designation)
  - ContractRestructureEvent: Convert base salary to bonus for cap relief
  - RFAOfferSheetEvent: Handle RFA tender matching and contract creation
  - DeadlineEvent: Check salary cap compliance for all 32 teams at March 12 deadline
- **Pre-execution Validation**: ValidationMiddleware checks cap space before all transactions
- **Transaction Logging**: Complete audit trail of all cap operations in database
- **Dynasty Isolation**: All cap operations respect dynasty context for multi-save support
- **Database Flexibility**: Support for custom database paths and in-memory testing databases

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

1. **PlayoffController Centralization** (Oct 2025): Moved from `demo/` to `src/playoff_system/playoff_controller.py`
   - Now accepts real playoff seeding from regular season standings (via `initial_seeding` parameter)
   - Maintains backward compatibility with random seeding
   - See `GAP1_IMPLEMENTATION_SUMMARY.md` and `docs/architecture/playoff_controller.md`

2. **Full Season Simulation Plan** (Oct 2025): Active development of unified season simulation
   - Target: Seamless regular season → playoffs → offseason progression
   - See `docs/plans/full_season_simulation_plan.md` for implementation status
   - Integrates `SeasonController` + `PlayoffController` + calendar system

3. **Workflow System Addition**: New `src/workflows/` module with reusable simulation patterns
   - `SimulationWorkflow`: 3-stage orchestrator (Simulation → Statistics → Persistence)
   - Toggleable persistence, flexible configuration, standardized results

4. **Test Suite Reorganization**: Many test files have been removed or relocated - verify test file existence before running

5. **Player Data Structure**: Team-based player files in `src/data/players/team_XX_team_name.json` format

6. **Database Flexibility**: Support for custom database paths and dynasty isolation in `FullGameSimulator`

7. **Persistence Control**: Optional statistics persistence via `enable_persistence` parameter

8. **Calendar System**: Database-backed calendar for event scheduling

9. **Coaching Staff Integration**: All 32 NFL teams mapped to coaching philosophies in `team_coaching_styles.json`

10. **Offseason Event System** (Oct 2025): Complete offseason event infrastructure implemented
   - New event types: `DeadlineEvent`, `WindowEvent`, `MilestoneEvent` in `src/events/`
   - Support for NFL offseason timeline (franchise tags, free agency, draft, roster cuts)
   - Date-driven event triggering via existing `SimulationExecutor`
   - See `docs/plans/offseason_plan.md` for complete architecture and implementation details

11. **Desktop UI Development** (Oct 2025): OOTP-inspired PySide6/Qt desktop application (Phase 1 complete)
   - Complete `ui/` package with tab-based navigation (6 primary tabs)
   - Main window with menu bar, toolbar, and status bar
   - OOTP-inspired QSS stylesheet with professional theme
   - Clean UI/engine separation via controller pattern
   - Phase 1 delivered: Foundation complete, Phase 2 (Season/Team views) ready to start
   - See `docs/plans/ui_development_plan.md` and `PHASE_1_COMPLETE.md` for details

12. **Salary Cap System** (Oct 2025): NFL salary cap management system implementation
   - New `src/salary_cap/` module with complete cap calculation engine
   - Follows 2024-2025 NFL CBA rules (proration, dead money, June 1 designations)
   - Support for top-51 (offseason) and 53-man (regular season) roster calculations
   - Contract validation, cap compliance checking, and transaction management
   - Franchise tags, transition tags, RFA tenders with consecutive tag escalators
   - **Event Integration Complete**: All cap operations execute through event system via EventCapBridge
   - Interactive demo available: `demo/cap_calculator_demo/`
   - See `docs/plans/salary_cap_plan.md` for architecture and `docs/architecture/event_cap_integration.md` for event integration details

## Key Implementation Notes

- **Team IDs**: Always use numerical IDs (1-32) via `TeamIDs` constants
- **Python Version**: Requires Python 3.13.5 (venv may need reconfiguration if path errors occur)
- **Testing**: Use `PYTHONPATH=src` prefix for most test runs
- **Database**: SQLite with dynasty-based isolation support
- **UI Dependencies**: PySide6 (Qt for Python) installed via `requirements-ui.txt` for desktop application