# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

**New to this codebase? Start here:**
1. Run the desktop UI: `python main.py` (requires `pip install -r requirements-ui.txt`)
2. Run the Game Cycle UI: `python main2.py` (stage-based, Madden-style)
3. Run tests: `python -m pytest tests/`
4. Database: `data/database/nfl_simulation.db` (SQLite with dynasty isolation)

**Key Test Scripts:**
- **Draft Dialog**: `python test_draft_dialog_standalone.py` (requires draft data setup)
- **Validation Scripts**: See scripts/ directory for GM behavior validation

## Current Focus: Game Cycle (Milestone 1)

**IMPORTANT**: From Nov 2024, development is focused on the new Game Cycle system (`src/game_cycle/`).

**Two Entry Points - Two Databases:**
| Entry Point | Database | Architecture |
|-------------|----------|--------------|
| `main.py` | `data/database/nfl_simulation.db` | Calendar-based (day-by-day simulation) |
| `main2.py` | `data/database/game_cycle/game_cycle.db` | **Stage-based (Madden-style, current focus)** |

**Do NOT mix game_cycle code with the calendar-based season cycle scheduler in `src/season/`.**

See `docs/01_MILESTONE_GAME_CYCLE/PLAN.md` for the full roadmap.

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
- **Production Ready**: Desktop UI (Phase 1), season simulation (single season), salary cap, calendar/events, statistics, AI offseason manager (Phase 2), NFL Draft Event integration (Phase 4)
- **In Development**: Milestone 1 (multi-year dynasty - 2/14 systems complete), Desktop UI Phase 2, Player generation
- **Stable**: Play engine, game simulation, coaching staff, playoff system, database persistence

## Development Environment

- **Python**: 3.13.5 (required, venv at `.venv/`)
- **Database**: SQLite3 at `data/database/nfl_simulation.db`
- **UI Framework**: PySide6/Qt (OOTP-inspired)

**Setup:**
```bash
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux

# Install UI dependencies
pip install -r requirements-ui.txt

# Install core dependencies
pip install pytest
```

## Core Commands

### Running the Application
```bash
python main.py                    # Desktop UI (calendar-based)
python main2.py                   # Game Cycle UI (stage-based, CURRENT FOCUS)
python test_ui.py                 # Test UI imports
```

### Running Tests
```bash
# All tests
python -m pytest tests/

# Specific modules
python -m pytest tests/calendar/ -v
python -m pytest tests/salary_cap/ -v
python -m pytest tests/statistics/ -v
python -m pytest tests/services/ -v

# Single test
python -m pytest tests/salary_cap/test_cap_calculator.py::test_cap_calculation -v

# Debug mode
python -m pytest tests/ -x --pdb
```

### Database Inspection
```bash
# View schema
sqlite3 data/database/nfl_simulation.db ".schema"

# Query stats
sqlite3 data/database/nfl_simulation.db "SELECT * FROM player_stats WHERE dynasty_id='your_dynasty' LIMIT 10;"

# Check calendar state
sqlite3 data/database/nfl_simulation.db "SELECT current_date, current_phase FROM dynasty_state WHERE dynasty_id='your_dynasty';"

# Check draft progress
sqlite3 data/database/nfl_simulation.db "SELECT draft_year, current_round, current_pick FROM dynasty_state WHERE dynasty_id='your_dynasty';"
```

### Database Migrations
```bash
# Migrations are applied automatically on app startup via main.py
# Manual application (if needed):
sqlite3 data/database/nfl_simulation.db < src/database/migrations/005_add_draft_progress_columns.sql
sqlite3 data/database/nfl_simulation.db < src/database/migrations/006_fix_team_cap_summary_view.sql
sqlite3 data/database/nfl_simulation.db < src/database/migrations/007_add_prospect_player_mapping.sql

# Run Python migrations
python scripts/migrate_add_draft_progress.py
python scripts/migrate_add_prospect_player_mapping.py
```

### Validation Scripts
```bash
# AI behavior validation (in scripts/)
python scripts/validate_fa_gm_behavior.py
python scripts/validate_roster_cuts_gm_behavior.py
python scripts/validate_draft_gm_behavior.py
python scripts/validate_full_offseason_gm.py

# Run all GM validations
python scripts/run_all_gm_validations.py
```

## NFL Draft Event Integration

**Status**: Phase 4 Complete (Nov 2025)

### Key Features
- **Auto-triggering**: Draft dialog launches automatically on April 24th during offseason simulation
- **Save/Resume**: Draft progress persists across sessions (round, pick number, selections)
- **Non-modal dialog**: Access other UI tabs during draft
- **AI picks**: All 31 AI teams make needs-based draft selections
- **User interaction**: User team can manually select prospects or auto-sim to their pick

### Commands
```bash
# Standalone draft dialog testing (requires draft data setup)
python test_draft_dialog_standalone.py

# Run UI tests
python -m pytest tests/ui/ -v
```

### Implementation Details
- **Event scheduling**: `OffseasonEventScheduler` creates DraftDayEvent on April 24
- **Detection**: `SimulationController.check_for_draft_day_event()` before each advance_day()
- **Dialog**: `ui/dialogs/draft_day_dialog.py` with `DraftDialogController`
- **Backend**: `src/offseason/draft_manager.py` handles pick execution and AI logic
- **Database**: Draft progress tracked in `dynasty_state` table (draft_year, current_round, current_pick)

### Documentation
- Implementation plan: `docs/project/nfl_draft_event/implementation_plan.md`
- Phase 4 completion: `docs/project/nfl_draft_event/PHASE_4_COMPLETE.md`
- Test infrastructure: `tests/ui/README.md`

## Architecture Overview

### Two Simulation Architectures

This project has **two distinct simulation systems** (do not mix them):

**1. Calendar-Based (main.py)** - Day-by-day simulation
```
src/season/SeasonCycleController → src/calendar/ → src/events/
Uses: data/database/nfl_simulation.db
UI: ui/
```

**2. Stage-Based (main2.py)** - Madden-style week/stage progression (**CURRENT FOCUS**)
```
src/game_cycle/StageController → StageType → StageHandler
Uses: data/database/game_cycle/game_cycle.db
UI: game_cycle_ui/
```

### Game Cycle Architecture (main2.py)

**Stage Flow:**
```
REGULAR SEASON (18 stages: Week 1-18)
    → PLAYOFFS (4 stages: Wild Card → Divisional → Conference → Super Bowl)
    → OFFSEASON (6 stages: Re-signing → Free Agency → Draft → Roster Cuts → Training Camp → Preseason)
    → NEXT SEASON (Year + 1)
```

**Key Files:**
- `src/game_cycle/stage_definitions.py` - `StageType` enum, `Stage` dataclass
- `src/game_cycle/stage_controller.py` - Main orchestrator (`StageController`)
- `src/game_cycle/handlers/` - Phase-specific handlers (regular_season, playoffs, offseason)
- `game_cycle_ui/` - Stage-based UI components

### Layered Design (Calendar-Based)

**Core Layers:**
1. **Play Engine** (`src/play_engine/`) - Play simulation with match/case routing, unified formations, coaching staff
2. **Game Management** (`src/game_management/`) - Game loop, scoreboard, scoring, box scores, play-by-play
3. **Season Management** (`src/season/`) - `SeasonCycleController` orchestrates Regular Season → Playoffs → Offseason
4. **Data Layer** (`src/database/`, `src/stores/`) - DatabaseAPI (single source of truth), in-memory stores, persistence

**Key Systems:**
- **Playoff System** (`src/playoff_system/`) - Centralized `PlayoffController`, seeding, bracket management
- **Calendar/Events** (`src/calendar/`, `src/events/`) - Database-backed calendar, event lifecycle, simulation executor
- **Salary Cap** (`src/salary_cap/`) - CBA-compliant cap calculator, contracts, tags, event integration via EventCapBridge
- **Offseason** (`src/offseason/`) - AI manager (Phase 2 complete: franchise tags, free agency, roster cuts), draft scheduling
- **Statistics** (`src/statistics/`) - StatsAPI with 25+ methods, leaderboards, rankings, filtering
- **Desktop UI** (`ui/`) - MVC architecture: View → Controller → Domain Model → Database API
- **Draft System** (`src/offseason/draft_manager.py`, `ui/dialogs/draft_day_dialog.py`) - NFL Draft with AI picks, user interaction, save/resume
- **Services** (`src/services/`) - Business logic extraction (TransactionService, DynastyInitializationService)
- **Player Generation** (`src/player_generation/`) - Archetype-based generation (in development)

### Critical Design Patterns

**Match/Case for Play Types:**
```python
match offensive_play_type:
    case OffensivePlayType.RUN:
        # Run play logic
    case OffensivePlayType.PASS | OffensivePlayType.PLAY_ACTION_PASS:
        # All pass plays together
```

**Type-Safe Formations:**
```python
class UnifiedDefensiveFormation(Enum):
    # Context-aware naming (coordinator_name, punt_name, etc.)
```

**UI Architecture (MVC with Domain Models):**
```
View → Controller (thin, ≤10-20 lines) → Domain Model (business logic) → Database API
Non-modal dialogs for complex workflows (Draft, Free Agency)
Signal-based communication between controllers and views
```

**Event-Driven Salary Cap:**
```
FranchiseTagEvent → EventCapBridge → CapCalculator → Database
All cap operations execute through event system for audit trail
```

**Transaction Context (Atomic Operations):**
```python
with TransactionContext(conn, mode=TransactionMode.IMMEDIATE) as txn:
    # Multiple operations
    txn.commit()  # Explicit commit
# Auto-rollback on exception
```

**Dynasty Isolation:**
```python
# Complete statistical separation between dynasties
simulator = FullGameSimulator(
    dynasty_id="my_dynasty",
    database_path="data/database/nfl_simulation.db",
    enable_persistence=True
)
```

## Key Implementation Details

### Team System
- Numerical IDs (1-32): `TeamIDs.DETROIT_LIONS` or `get_team_by_id(22)`
- JSON data: `src/data/teams.json`
- Player data: Individual team files (`src/data/players/team_XX_team_name.json`)

### Configuration Files
- Penalties: `src/config/penalties/*.json` (5 files)
- Coaching: `src/config/coaching_staff/`, `src/config/team_coaching_styles.json`
- Playbooks: `src/config/playbooks/*.json`
- Play configs: `src/play_engine/config/*.json`

### Persistence & Dynasty Control
```python
# Flexible database and dynasty configuration
sim = FullGameSimulator(
    away_team_id=7,
    home_team_id=9,
    dynasty_id="my_dynasty",           # Dynasty isolation
    database_path="my_dynasty.db",     # Custom database
    enable_persistence=True            # Toggle persistence
)

# Runtime changes
sim.dynasty_id = "new_dynasty"         # Auto-recreates services
sim.database_path = "new.db"           # Auto-recreates services
sim.persistence = False                # Disable for demos/testing
```

### NFL Realism
- Penalty rates: 20-30% per play (NFL realistic)
- Home field advantage: 10-15% penalty reduction
- Situational modifiers: Red zone +40%, 4th down +25%
- Coaching archetypes: ultra_conservative → ultra_aggressive

## Known Issues

### CRITICAL: Calendar Drift Bug
- **Symptom**: UI shows future date (e.g., March 2026), database shows past date (e.g., Nov 2025)
- **Root Cause**: Silent database persistence failures in `SimulationController._save_state_to_db()`
- **Detection**: Console errors `[ERROR SimulationDataModel] Failed to save dynasty state...`
- **Verification**:
  ```bash
  sqlite3 data/database/nfl_simulation.db "SELECT current_date, current_phase FROM dynasty_state WHERE dynasty_id='your_dynasty';"
  # Compare to UI date - if mismatch > 1 day, drift has occurred
  ```
- **Action**: Stop simulation immediately, investigate console errors
- **Details**: See `docs/bugs/calendar_drift_root_cause_analysis.md`

### Low Priority: Service Layer Test Failures
- 10 of 30 tests in `tests/services/` fail due to incorrect mock patch paths
- Core functionality verified by 20 passing tests
- Production code unaffected
- Fix deferred until services refactor

### Multi-Year Season Limitation (Milestone 1)
- **Current**: Can simulate 1 complete season (Regular → Playoffs → Offseason)
- **Limitation**: Cannot auto-transition to next season (12 of 14 systems missing)
- **Missing**: Season year increment, cap rollover, contract increments, player aging, draft class timing, etc.
- **Workaround**: Manual database reset between seasons
- **Status**: Milestone 1 in development - see `docs/MILESTONE_1/README.md`

## Common Issues & Troubleshooting

### Database Issues
- **Empty stats/standings**: Verify dynasty_id matches between queries
- **Transaction failures**: Check `detailed_transaction_tracking.log`, disk space, file permissions
- **Lock files**: Look for `.db-shm`, `.db-wal` files indicating active connections

### Testing Issues
- **Module not found**: Activate venv, install dependencies
- **Import errors**: Use `PYTHONPATH=src` prefix
- **Service test failures**: Expected (10/30 fail, known issue)

### Development Workflow
- Before committing: Run relevant tests
- New features: Follow existing patterns, add tests
- Database ops: Always verify success, raise exceptions on failure

## Documentation

**Planning (Active):**
- `docs/01_MILESTONE_GAME_CYCLE/PLAN.md` - **Game Cycle milestone roadmap (CURRENT FOCUS)**

**Architecture (in docs/archive/):**
- `docs/archive/architecture/play_engine.md` - Core system architecture
- `docs/archive/architecture/playoff_controller.md` - Playoff orchestration
- `docs/archive/architecture/event_cap_integration.md` - Event-cap bridge pattern
- `docs/archive/architecture/ui_layer_separation.md` - MVC with domain models

**Database:**
- `docs/archive/schema/database_schema.md` - Complete SQLite schema v2.0.0

**API Specifications (in docs/archive/):**
- `docs/archive/api/statistics_api_specification.md` - Complete Statistics API (25+ methods)
- `docs/archive/api/depth_chart_api_specification.md` - Depth chart API
- `docs/archive/api/playoff_database_api_specification.md` - Playoff data management

**How-To Guides (in docs/archive/):**
- `docs/archive/how-to/full_game_simulator_usage.md` - FullGameSimulator configuration
- `docs/archive/how-to/simulation-workflow.md` - Complete simulation workflow

## Recent Major Changes

**2024-2025 Updates:**
1. **Statistics Preservation System** (Complete) - Season year tracking with auto-recovery
2. **Offseason AI Manager Phase 2** (Complete) - AI franchise tags, free agency, roster cuts
3. **Desktop UI Phase 1** (Complete) - Foundation, tabs, MVC with domain model layer
4. **Service Layer Extraction Phase 3** (Complete) - Transaction logic separated
5. **Transaction Context System** (Complete) - Atomic database operations with nested support
6. **PlayoffDatabaseAPI** (Nov 2025) - Modular playoff data management
7. **SeasonCycleController** - Dynamic transition handlers with phase-aware season year management
8. **Event-Cap Integration** - All salary cap operations execute through event system
9. **NFL Draft Event Integration** (Phase 4 Complete, Nov 2025) - Draft dialog, auto-triggering on April 24, save/resume
10. **Database Migrations 005-007** (Nov 2025) - Draft progress tracking, cap summary fix, prospect-player mapping

**Deprecated/Removed (Nov 2025):**
- `demo/` directory - All demo scripts removed, functionality migrated to production UI and test scripts
- Interactive demos replaced by `python main.py` (production UI) and validation scripts in `scripts/`

## Testing Strategy

1. **Unit Tests** (`tests/`) - Pytest-based, organized by feature
2. **Validation Scripts** (`scripts/`) - Automated GM behavior validation and diagnostics
3. **UI Integration** (`python main.py`) - Full production UI for manual testing

**Key Test Directories:**
- `tests/calendar/` - Calendar system
- `tests/playoff_system/` - Playoff system
- `tests/salary_cap/` - Salary cap
- `tests/statistics/` - Statistics API
- `tests/services/` - Service layer (10/30 tests expected to fail)
- `tests/database/` - Database layer and transaction context
- `tests/ui/` - UI integration tests (47 tests: 25 controller, 17 integration, 5 pending)

**Test Configuration:**
- `pytest.ini` configures pythonpath to project root (no PYTHONPATH prefix needed for pytest)
- Fixtures in `tests/conftest.py` and `tests/ui/conftest.py`
- Run with `-v` for verbose output, `--pdb` for debugging
