# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is "The Owners Sim" - a comprehensive NFL football simulation engine written in Python. The project simulates realistic NFL gameplay with detailed player statistics, penalty systems, team management, and formation-based play calling.

## Development Environment

- **Python Version**: 3.13.5
- **Virtual Environment**: `.venv/` (already configured)
- **Dependencies**: SQLite3 support via better-sqlite3 (Node.js binding)
- **Package Manager**: npm for Node.js dependencies, pip for Python

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

# Schedule generator tests (Phase 0-3 available)
python -m pytest tests/test_scheduling/

# Key test files for core functionality
PYTHONPATH=src python tests/test_penalty_system.py
PYTHONPATH=src python tests/test_game_state_manager.py
PYTHONPATH=src python tests/test_drive_manager.py
PYTHONPATH=src python tests/test_game_loop_controller.py
PYTHONPATH=. python tests/test_phase_4_comprehensive.py

# Season simulation and progression tests
PYTHONPATH=src python tests/test_phase_2_integration.py
PYTHONPATH=src python tests/test_phase_3_season_progression.py
PYTHONPATH=src python tests/test_daily_persister.py
PYTHONPATH=src python tests/test_season_init_perfect.py

# Interactive validation scripts
python tests/simple_penalty_validation.py

# Diagnostic scripts (run from project root)
PYTHONPATH=src python team_corruption_tracker.py
PYTHONPATH=src python simple_stats_check.py
PYTHONPATH=src python verify_player_stats_persistence.py
```

### Running Demos
```bash
# Full game simulation demonstration
python full_game_demo.py

# Phase 4 comprehensive system demonstration
python phase_4_demo.py

# Result processing system demo
python result_processing_demo.py

# Interactive NFL season simulation (terminal-based)
python interactive_season_demo.py
```

### Diagnostic Scripts
```bash
# All diagnostic scripts require PYTHONPATH=src prefix
PYTHONPATH=src python team_corruption_tracker.py
PYTHONPATH=src python verify_player_stats_persistence.py
PYTHONPATH=src python final_persistence_verification.py
PYTHONPATH=src python track_transaction_failures.py
PYTHONPATH=src python test_index_mismatch_issue.py
PYTHONPATH=src python simulate_interactive_demo_issue.py

# Check detailed_transaction_tracking.log for persistence debugging
tail -f detailed_transaction_tracking.log
```

### Development Setup
```bash
# Activate virtual environment (required for Python 3.13.5)
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install Node.js dependencies (for SQLite3 bindings)
npm install

# Install Python dependencies (if needed)
pip install pytest

# For advanced season simulation features (includes linting/formatting tools)
pip install -r requirements_scheduling.txt
```

### Code Quality Tools
```bash
# Code formatting (if requirements_scheduling.txt is installed)
black src/ tests/

# Type checking
mypy src/

# Code quality analysis
pylint src/

# Note: These tools are included in requirements_scheduling.txt but not required for basic functionality
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
- `src/playcall.py`: High-level play calling interface
- `src/play_call_params.py`: Parameter structures for play calls
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
- `loaders/calendar_adapter.py`: Integration with CalendarManager system
- `config.py`: Comprehensive configuration for schedule generation
- `utils/date_utils.py`: NFL season date calculations and utilities
- `validators/`: Schedule validation and constraint checking (future)
- `generator/`: Schedule generation algorithms (future phases)

**13. Simulation System (`src/simulation/`)**
- `calendar_manager.py`: Day-by-day simulation orchestration
- `season_progression_controller.py`: High-level season simulation orchestrator
- `season_initializer.py`: Season setup and initialization system
- `dynasty_context.py`: Dynasty-level context and management
- `events/`: Polymorphic event system for games, training, scouting, etc.
- `processors/`: Result processing strategies for different event types
- `results/`: Enhanced result types with metadata
- `season_state_manager.py`: Season-wide state tracking
- `mock_store_manager.py`: Mock store implementation for testing

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

**Season Progression Architecture**:
- `SeasonProgressionController`: High-level season orchestrator
- `SeasonInitializer`: Dynasty and season setup
- `CalendarManager`: Day-by-day event processing
- Dynasty-scoped data with multi-season support

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
- `requirements_scheduling.txt`: Dependencies for schedule generator module
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
- **System Summaries**: 
  - `docs/PENALTY_SYSTEM_SUMMARY.md` - Penalty system overview
  - `docs/TEAM_SYSTEM_SUMMARY.md` - Team management system details
  - `docs/TEST_GUIDE.md` - Testing guidelines and approaches
- **Planning Documents**: `docs/plans/` - Architecture plans and data flow analysis

## Common Issues and Troubleshooting

### Database Issues
- **Empty stats/standings**: Run diagnostic scripts like `team_corruption_tracker.py` or `simple_stats_check.py`
- **Transaction failures**: Check `detailed_transaction_tracking.log` for persistence errors
- **Data inconsistency**: Use validation scripts in tests/ directory for verification

### Testing Issues
- **Test failures**: Always run with `PYTHONPATH=src` or `PYTHONPATH=.` prefix for imports
- **Module not found**: Ensure virtual environment is activated and dependencies installed
- **Performance issues**: Use `pytest-benchmark` (included in requirements_scheduling.txt)

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

### Interactive Season Simulation
- `interactive_season_demo.py`: Terminal-based NFL season simulator
- **Daily Mode**: Day-by-day simulation with detailed control
- **Weekly Mode**: Week-by-week simulation for faster progression
- **Statistics Persistence**: Automatic saving of player and team statistics to SQLite database
- **Real-time Standings**: Live tracking of division and conference standings
- **Dynasty Support**: Multi-season dynasty management with persistent data

## Migration Notes

Recent major changes to be aware of:

1. **Team Names → Numerical IDs**: `TeamRosterGenerator.generate_sample_roster()` now requires integer team_id instead of string team_name
2. **Play Type Consolidation**: PLAY_ACTION_PASS and SCREEN_PASS now handled under PASS case
3. **Match/Case Conversion**: Main play engine converted from if/elif to match/case pattern
4. **Unified PlayResult**: Single PlayResult class replaces multiple result classes, eliminates import conflicts
5. **Coaching Staff System**: New hierarchical coaching system with realistic NFL coaching philosophies
6. **Type-Safe Formations**: String-based formation names replaced with enum-based system
7. **Special Teams Coordinator**: New dedicated special teams coordinator with independent play calling for punts, field goals, and kickoffs
8. **Schedule Generator**: New NFL schedule generation system with CalendarManager integration for season simulation
9. **Simulation Events**: Enhanced event system with polymorphic processing for games, training, scouting, and administrative events
10. **Database Architecture**: New SQLite-based persistence with `DatabaseAPI` for retrieval and `DailyDataPersister` for persistence
11. **Season Progression**: `SeasonProgressionController` for complete season simulation orchestration
12. **Dynasty System**: Multi-season dynasty support with dynasty context management
13. **File Cleanup**: Several demo files removed - only `full_game_demo.py`, `phase_4_demo.py`, and `result_processing_demo.py` remain as root-level demos
14. **Interactive Season Demo**: New `interactive_season_demo.py` provides terminal-based season simulation with daily/weekly modes

When working with legacy code, check for hardcoded team names and convert to numerical IDs using the constants in `src/constants/team_ids.py`.