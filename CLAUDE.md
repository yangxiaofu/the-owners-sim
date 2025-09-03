# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a football owner simulation game inspired by Out of the Park Baseball, focusing on deep football simulation with owner-level strategic decisions and financial management. The codebase is primarily Python-based with a clean architecture approach.

Reference the `docs/game-design/football_owner_sim_spec.md` for complete game design context when developing features.

## Development Commands

### Python Environment  
- **Python Version**: Requires Python 3.13+
- **Virtual Environment**: `.venv/` directory contains project dependencies
- **Quick validation**: `python quick_test.py` (runs automated test suite)
- **Game simulation**: `python one_game_demo.py` (main simulation demo)

### Testing Commands
The codebase has an extensive test suite with 20+ test files in the root directory:
- **Quick validation**: `python quick_test.py`
- **Play-by-play testing**: `python play_by_play_test.py`
- **Specific system tests**: `python test_[system]_[focus].py` (e.g., `test_clock_integration.py`)
- **Debug scenarios**: `python debug_[system].py` (e.g., `debug_clock_calculation.py`)

### Database
- **Initialize database**: `python -c "from src.database.setup import initialize_database; initialize_database()"`
- **Database location**: `data/football_sim.db` (SQLite)
- **Node.js dependencies**: Uses better-sqlite3 for additional database tooling

## Architecture Overview

### Core Components

**Game Engine** (`src/game_engine/`):
- `core/game_orchestrator.py`: Main game simulation engine with hardcoded team data
- `core/game_state_manager.py`: Manages game state transitions and validation
- `core/play_executor.py`: Orchestrates individual play execution using Strategy pattern
- `plays/`: Play-specific simulation logic (run, pass, kick, punt)
- `field/`: Game state management (clock, scoreboard, field position)
- `state_transitions/`: **Critical architectural component** - handles atomic state changes
  - `data_structures/`: Core transition objects (GameStateTransition, ClockTransition, etc.)
  - `calculators/`: Logic for computing state changes (clock, field position, scores)
  - `validators/`: Rules validation before applying transitions
  - `applicators/`: Applies validated transitions to game state
- `simulation/blocking/`: Detailed blocking simulation for run plays
- `personnel/`: Player selection and personnel packages
- `coaching/`, `penalties/`: Advanced game systems

**Database Layer** (`src/database/`):
- `setup.py`: SQLite database initialization and migration handling
- `models/players/`: Player data structures and position definitions
- `generators/`: Mock data generation for testing

**State Transition Architecture**:
The game uses a sophisticated state transition system for atomic game state updates:
1. **Play Execution** generates a `GameStateTransition` containing all required changes
2. **Validators** ensure transitions follow NFL rules and game logic
3. **Applicators** atomically apply validated transitions to the game state
4. **Calculators** compute derived values (clock usage, field position, scores)

**Play Execution Flow**:
1. `GameOrchestrator` manages game-level simulation
2. `PlayExecutor` coordinates individual plays
3. `PlayFactory` creates appropriate play instances
4. Play-specific classes handle simulation logic and generate transitions
5. `GameStateManager` validates and applies transitions to update `GameState`

### Key Design Patterns

- **Strategy Pattern**: Play execution with swappable simulation strategies
- **Factory Pattern**: Play creation based on game situation
- **State Transition Pattern**: Atomic game state changes via validated transitions
- **Clean Architecture**: Separation between game logic, data, and simulation

### Database Schema

Uses SQLite with migrations in `src/database/migrations/`. Core tables include teams, players, games, and statistics tracking.

## Development Workflow

1. Review folder structure before creating new files to ensure optimal placement
2. Provide constructive feedback on all suggestions to maintain code quality
3. Reference the game design specification for context on new features
4. Test changes using the existing test files in the root directory

## Current Development State

The codebase is in active development with:
- **Complete game simulation** working with hardcoded team data
- **Sophisticated state transition system** for atomic game state management
- **Comprehensive test suite** with 20+ specialized test files for edge cases
- **Play-by-play execution framework** implemented with validation
- **Clock management system** achieving realistic 150-155 plays per game
- Database schema defined but not fully integrated
- Individual player modeling in progress

## Development Notes

- Provide constructive feedback on all suggestions and counter-arguments
- The codebase has extensive debugging and testing infrastructure for complex scenarios
- Focus on maintaining the atomic state transition architecture when making changes