# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

**New to this codebase? Start here:**
1. Run the Game Cycle UI: `python main2.py` (stage-based, Madden-style) **← PRIMARY**
2. Run the legacy desktop UI: `python main.py` (requires `pip install -r requirements-ui.txt`)
3. Run tests: `python -m pytest tests/`
4. Database: `data/database/game_cycle/game_cycle.db` (Game Cycle) or `data/database/nfl_simulation.db` (legacy)

## Two Entry Points - Two Databases

| Entry Point | Database | Architecture |
|-------------|----------|--------------|
| **`main2.py`** | `data/database/game_cycle/game_cycle.db` | **Stage-based (Madden-style, CURRENT FOCUS)** |
| `main.py` | `data/database/nfl_simulation.db` | Calendar-based (day-by-day, legacy) |

**Do NOT mix `src/game_cycle/` code with the calendar-based season cycle scheduler in `src/season/`.**

## Critical Constraints

**ALWAYS follow these rules:**
- **Team IDs**: Use numerical IDs (1-32) via `TeamIDs` constants, NEVER team name strings
- **PYTHONPATH**: Use `PYTHONPATH=src` prefix for commands that need it (pytest handles this automatically)
- **Enums over Strings**: Default to enums to avoid magic strings
- **DRY Principles**: Search for existing APIs before creating new ones
- **Certainty Score**: On a scale of 1-100, provide level of certainty for any fix
- **Database Operations**: MUST raise exceptions on failure - never fail silently
- **Plan Mode**: Provide file paths (linkable), group by backend/frontend, write pseudo code with architecture adherence
- **Dynasty Isolation**: For any new methods or classes, always consider how to utilize the SSOT for dynasty_id to maintain dynasty isolation

## Project Overview

"The Owners Sim" - A comprehensive NFL football simulation engine written in Python with realistic gameplay, detailed statistics, penalty systems, team management, and formation-based play calling.

**Current Status:**
- **Complete**: Game Cycle Milestone 1 (full season loop with multi-year dynasty)
- **Production Ready**: Desktop UI (Phase 1), salary cap, calendar/events, statistics, AI offseason manager, NFL Draft
- **Stable**: Play engine, game simulation, coaching staff, playoff system, database persistence
- **In Development**: Desktop UI Phase 2, Player generation, advanced features (trades, franchise tags, injuries)

## Development Environment

- **Python**: 3.13.5 (required, venv at `.venv/`)
- **UI Framework**: PySide6/Qt

**Setup:**
```bash
source .venv/bin/activate  # Activate virtual environment
pip install -r requirements-ui.txt  # Install dependencies
```

## Core Commands

### Running the Application
```bash
python main2.py                   # Game Cycle UI (stage-based, PRIMARY)
python main.py                    # Legacy Desktop UI (calendar-based)
```

### Running Tests
```bash
python -m pytest tests/                                                    # All tests
python -m pytest tests/calendar/ -v                                        # Specific module
python -m pytest tests/salary_cap/test_cap_calculator.py::test_cap_calculation -v  # Single test
python -m pytest tests/ -x --pdb                                           # Debug mode
```

### Database Inspection
```bash
# Game Cycle database (primary)
sqlite3 data/database/game_cycle/game_cycle.db ".schema"

# Legacy database
sqlite3 data/database/nfl_simulation.db ".schema"
sqlite3 data/database/nfl_simulation.db "SELECT current_date, current_phase FROM dynasty_state WHERE dynasty_id='your_dynasty';"
```

### Validation Scripts
```bash
python scripts/validate_fa_gm_behavior.py       # AI free agency behavior
python scripts/validate_roster_cuts_gm_behavior.py
python scripts/validate_draft_gm_behavior.py
python scripts/run_all_gm_validations.py        # Run all GM validations
```

## Architecture Overview

### Game Cycle Architecture (main2.py) - PRIMARY

**Stage Flow:**
```
REGULAR SEASON (18 weeks)
    → PLAYOFFS (Wild Card → Divisional → Conference → Super Bowl)
    → OFFSEASON (Re-signing → Free Agency → Draft → Roster Cuts → Waiver Wire → Training Camp → Preseason)
    → NEXT SEASON (Year + 1)
```

**Key Files:**
- `src/game_cycle/stage_definitions.py` - `StageType` enum, `Stage` dataclass
- `src/game_cycle/stage_controller.py` - Main orchestrator (`StageController`)
- `src/game_cycle/handlers/` - Phase handlers (regular_season.py, playoffs.py, offseason.py)
- `src/game_cycle/services/` - Business logic (draft, free agency, roster cuts, waiver wire, training camp)
- `game_cycle_ui/` - Stage-based UI views

### Calendar-Based Architecture (main.py) - Legacy

**Core Layers:**
1. **Play Engine** (`src/play_engine/`) - Play simulation with match/case routing, unified formations
2. **Game Management** (`src/game_management/`) - Game loop, scoreboard, box scores
3. **Season Management** (`src/season/`) - `SeasonCycleController` orchestrates season phases
4. **Data Layer** (`src/database/`, `src/stores/`) - DatabaseAPI (single source of truth)

**Key Systems:**
- **Playoff System** (`src/playoff_system/`) - `PlayoffController`, seeding, bracket management
- **Calendar/Events** (`src/calendar/`, `src/events/`) - Database-backed calendar, event lifecycle
- **Salary Cap** (`src/salary_cap/`) - CBA-compliant cap calculator, contracts, tags
- **Statistics** (`src/statistics/`) - StatsAPI with 25+ methods
- **Services** (`src/services/`) - TransactionService, DynastyInitializationService

### Critical Design Patterns

**Transaction Context (Atomic Operations):**
```python
with TransactionContext(conn, mode=TransactionMode.IMMEDIATE) as txn:
    # Multiple operations
    txn.commit()  # Explicit commit
# Auto-rollback on exception
```

**UI Architecture (MVC with Domain Models):**
```
View → Controller (thin) → Domain Model (business logic) → Database API
Signal-based communication between controllers and views
```

## Key Implementation Details

### Team System
- Numerical IDs (1-32): `TeamIDs.DETROIT_LIONS` or `get_team_by_id(22)`
- JSON data: `src/data/teams.json`
- Player data: Individual team files (`src/data/players/team_XX_team_name.json`)

### Configuration Files
- Penalties: `src/config/penalties/*.json`
- Coaching: `src/config/coaching_staff/`, `src/config/team_coaching_styles.json`
- Playbooks: `src/config/playbooks/*.json`

## Known Issues

### CRITICAL: Calendar Drift Bug (Legacy main.py only)
- **Symptom**: UI shows future date, database shows past date
- **Root Cause**: Silent database persistence failures in `SimulationController._save_state_to_db()`
- **Detection**: Console errors `[ERROR SimulationDataModel] Failed to save dynasty state...`
- **Details**: See `docs/bugs/calendar_drift_root_cause_analysis.md`

### Low Priority: Service Layer Test Failures
- 10 of 30 tests in `tests/services/` fail due to incorrect mock patch paths
- Production code unaffected, fix deferred

## Common Issues & Troubleshooting

- **Empty stats/standings**: Verify dynasty_id matches between queries
- **Transaction failures**: Check `detailed_transaction_tracking.log`, disk space, file permissions
- **Lock files**: `.db-shm`, `.db-wal` files indicate active connections
- **Module not found**: Activate venv, install dependencies
- **Import errors**: Use `PYTHONPATH=src` prefix (pytest handles automatically)

## Documentation

**Planning:**
- `docs/01_MILESTONE_GAME_CYCLE/PLAN.md` - Game Cycle milestone (COMPLETE)

**Architecture (in docs/archive/):**
- `docs/archive/architecture/play_engine.md` - Core system architecture
- `docs/archive/architecture/playoff_controller.md` - Playoff orchestration
- `docs/archive/architecture/event_cap_integration.md` - Event-cap bridge pattern
- `docs/archive/schema/database_schema.md` - Complete SQLite schema v2.0.0

## Testing

```bash
python -m pytest tests/                    # All tests
python -m pytest tests/<module>/ -v        # Specific module
python -m pytest tests/file.py::test -v    # Single test
python -m pytest tests/ -x --pdb           # Debug mode
```

**Key Test Directories:**
- `tests/calendar/`, `tests/playoff_system/`, `tests/salary_cap/`, `tests/statistics/`
- `tests/services/` - (10/30 tests expected to fail, known issue)
- `tests/game_cycle/` - Game cycle tests

**Configuration:** `pytest.ini` sets pythonpath to project root
