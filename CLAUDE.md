# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a football owner simulation game inspired by Out of the Park Baseball, focusing on deep football simulation with owner-level strategic decisions and financial management. The codebase is primarily Python-based with a clean architecture approach.

Reference the `docs/game-design/football_owner_sim_spec.md` for complete game design context when developing features.

## Development Commands

### Python Environment
- Run game simulation: `python scripts/simulation/run_game.py`
- Run individual tests: `python test_run_concepts.py` or `python test_run_simple.py`
- Quick test system: `python quick_test.py`

### Database
- Initialize database: `python -c "from src.database.setup import initialize_database; initialize_database()"`
- Database location: `data/football_sim.db` (SQLite)

## Architecture Overview

### Core Components

**Game Engine** (`src/game_engine/`):
- `core/game_orchestrator.py`: Main game simulation engine with hardcoded team data
- `core/play_executor.py`: Orchestrates individual play execution using Strategy pattern
- `plays/`: Play-specific simulation logic (run, pass, kick, punt)
- `field/`: Game state management (clock, scoreboard, field position)
- `simulation/blocking/`: Detailed blocking simulation for run plays
- `personnel/`: Player selection and personnel packages

**Database Layer** (`src/database/`):
- `setup.py`: SQLite database initialization and migration handling
- `models/players/`: Player data structures and position definitions
- `generators/`: Mock data generation for testing

**Play Execution Flow**:
1. `GameOrchestrator` manages game-level simulation
2. `PlayExecutor` coordinates individual plays
3. `PlayFactory` creates appropriate play instances
4. Play-specific classes handle simulation logic
5. Results update `GameState` centrally

### Key Design Patterns

- **Strategy Pattern**: Play execution with swappable simulation strategies
- **Factory Pattern**: Play creation based on game situation
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
- Basic game simulation working with hardcoded team data
- Play-by-play execution framework implemented
- Database schema defined but not fully integrated
- Individual player modeling in progress
- Run play concepts and blocking simulation partially implemented
- I need you to be constructive when I make suggestions and provide counter-arguments.