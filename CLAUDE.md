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
# Run all tests
python -m pytest tests/

# Run specific test files
python tests/test_penalty_system.py
python tests/test_run_play.py
python tests/simple_penalty_validation.py
python tests/test_punt_system.py
python tests/test_game_state_manager.py
python tests/test_field_tracker.py
python tests/test_down_tracker.py
python tests/test_drive_manager.py
python tests/test_scoreboard.py
python tests/test_scoring_mapper.py

# Quick validation test
python quick_test.py

# Interactive testing
python test_play_execution.py
```

### Running Demos
```bash
# Main play engine demonstration
python demo/play_engine_demo.py

# Run play simulation demo
python demo/run_play_demo.py

# Pass play simulation demo
python demo/pass_play_demo.py

# Ten play comprehensive demo
python ten_play_demo.py

# Field position tracking demo
python field_position_demo.py

# Game state management demo  
python game_state_demo.py

# Simple possession demo
python simple_possession_demo.py

# Scoreboard system demo
python scoreboard_demo.py
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
```

## Architecture Overview

### Core System Design

The simulation follows a layered architecture with clear separation of concerns:

**1. Play Engine Core (`src/play_engine/core/`)**
- `engine.py`: Main play simulation orchestrator using match/case statements
- `result.py`: Play result data structures
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

**3. Play Mechanics (`src/play_engine/mechanics/`)**
- `formations.py`: Formation system with personnel packages
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
- `scoreboard.py`: Game scoreboard management with quarter/game progression
- `scoring_mapper.py`: Maps play results to scoring events and point attribution

**8. Core Utilities (root level)**
- `src/playcall.py`: High-level play calling interface
- `src/play_call_params.py`: Parameter structures for play calls
- `src/constants/team_ids.py`: Team ID constants and utilities

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

**JSON Configuration System**: All game data is externalized:
- `src/data/teams.json`: Complete NFL team dataset with numerical IDs
- `src/config/penalties/`: 5 JSON files for penalty configuration
- Supports designer-friendly configuration without code changes

**Two-Phase Penalty Integration**:
1. Phase 1: Base play outcome using formation matchup matrix
2. Phase 2A: Penalty determination and effects
3. Phase 2B: Player statistics attribution

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
- `src/play_engine/config/`: Play-specific configuration files (run_play_config.json, pass_play_config.json, field_goal_config.json, kickoff_config.json, punt_config.json)

## Testing Strategy

The project uses multiple testing approaches:

1. **Unit Tests** (`tests/`): Traditional pytest-based unit testing
2. **Interactive Testing** (`test_play_execution.py`): Menu-driven play-by-play testing
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

### Error Handling
- Comprehensive validation for team IDs (must be 1-32)
- Graceful handling of invalid play types with descriptive errors
- Clear migration paths for breaking changes

## Migration Notes

Recent major changes to be aware of:

1. **Team Names → Numerical IDs**: `TeamRosterGenerator.generate_sample_roster()` now requires integer team_id instead of string team_name
2. **Play Type Consolidation**: PLAY_ACTION_PASS and SCREEN_PASS now handled under PASS case
3. **Match/Case Conversion**: Main play engine converted from if/elif to match/case pattern

When working with legacy code, check for hardcoded team names and convert to numerical IDs using the constants in `src/constants/team_ids.py`.