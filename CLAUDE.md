# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

**New to this codebase? Start here:**
1. Run the Game Cycle UI: `python main2.py` (stage-based, Madden-style) **← PRIMARY**
2. Run the legacy desktop UI: `python main.py`
3. Run tests: `python -m pytest tests/`
4. Database: `data/database/game_cycle/game_cycle.db` (Game Cycle) or `data/database/nfl_simulation.db` (legacy)

## Two Entry Points - Two Databases

| Entry Point | Database | Architecture |
|-------------|----------|--------------|
| **`main2.py`** | `data/database/game_cycle/game_cycle.db` | **Stage-based (Madden-style, CURRENT FOCUS)** |
| `main.py` | `data/database/nfl_simulation.db` | Calendar-based (day-by-day, legacy) |

**Database Content Split:**
- `game_cycle.db` **(PRIMARY)**: Standings, schedule, playoff bracket, box scores, player stats, awards, media headlines, progression history
- `nfl_simulation.db` **(LEGACY)**: Player data, contracts, team rosters, draft picks, transactions (some data shared via JSON files)

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
- **Service Layer Pattern**: Services should NOT make direct database calls - use dedicated API classes:
  ```python
  # Correct - use API class
  standings_api = StandingsAPI(conn, dynasty_id)
  standings = standings_api.get_standings(season)

  # Wrong - direct database call in service
  cursor.execute("SELECT * FROM standings WHERE ...")
  ```

## Project Overview

"The Owners Sim" - A comprehensive NFL football simulation engine written in Python with realistic gameplay, detailed statistics, penalty systems, team management, and formation-based play calling.

**Game Vision:** You are the **Owner**. Hire your GM and Head Coach, manage team finances, and build a dynasty. Your football decisions flow through the people you hire—choose wisely.

**Current Status:** See `docs/DEVELOPMENT_PRIORITIES.md` for complete roadmap and milestone status.

**Completed Milestones (17 of 41):**
1. Game Cycle, 2. Salary Cap & Contracts, 3. Player Progression, 4. Statistics, 5. Injuries & IR, 6. Trade System, 7. Player Personas, 8. Team Statistics, 9. Realistic Game Scenarios, 10. Awards System, 11. Schedule & Rivalries, 12. Media Coverage, 13. Owner-GM Offseason Flow, 14. Contract Valuation Engine, 15. Free Agency Depth, 16. Draft Class Variation, 17. Player Retirements

**In Progress:** Hall of Fame (T1-T5 Complete: Schema, Eligibility, Scoring, Voting, Induction Services)

**Stable Systems:** Play engine, game simulation, coaching staff, playoff system, database persistence

## Development Environment

- **Python**: 3.13.5 (required, venv at `.venv/`)
- **UI Framework**: PySide6/Qt
- **Key Dependencies**: PySide6, pytest, numpy, psutil

**Setup:**
```bash
source .venv/bin/activate  # Activate virtual environment
pip install PySide6 pytest numpy psutil  # Core dependencies
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
python -m pytest tests/ -m "not slow"                                      # Skip slow tests
python -m pytest tests/ -m "integration"                                   # Integration tests only
```

**Test Markers:**
- `@pytest.mark.slow` - Long-running tests (skip with `-m "not slow"`)
- `@pytest.mark.integration` - Integration tests (run with `-m "integration"`)

**Key Test Directories:**
- `tests/test_game_cycle/` - Game cycle services, handlers, and database tests (PRIMARY)
  - `tests/test_game_cycle/integration/` - End-to-end integration tests
  - `tests/test_game_cycle/services/` - Service layer tests
  - `tests/test_game_cycle/database/` - Database API tests
- `tests/calendar/`, `tests/playoff_system/`, `tests/salary_cap/`, `tests/statistics/` - Legacy tests
- `tests/contract_valuation/` - Valuation engine tests
- `tests/services/` - (10/30 tests fail due to mock paths, production unaffected)

### Database Inspection
```bash
# Game Cycle database (primary)
sqlite3 data/database/game_cycle/game_cycle.db ".schema"

# Legacy database
sqlite3 data/database/nfl_simulation.db ".schema"
sqlite3 data/database/nfl_simulation.db "SELECT current_date, current_phase FROM dynasty_state WHERE dynasty_id='your_dynasty';"
```

### Running Scripts (require PYTHONPATH)
```bash
PYTHONPATH=src python scripts/validate_fa_gm_behavior.py       # AI free agency behavior
PYTHONPATH=src python scripts/validate_roster_cuts_gm_behavior.py
PYTHONPATH=src python scripts/validate_draft_gm_behavior.py
PYTHONPATH=src python scripts/run_all_gm_validations.py        # Run all GM validations
```

## Architecture Overview

### Game Cycle Architecture (main2.py) - PRIMARY

**Stage Flow:**
```
REGULAR SEASON (18 weeks)
    → PLAYOFFS (Wild Card → Divisional → Conference → Super Bowl)
    → OFFSEASON (Honors → Franchise Tag → Re-signing → Free Agency → Trading → Draft → Roster Cuts → Waiver Wire → Training Camp → Preseason)
    → NEXT SEASON (Year + 1)
```

**StageType Quick Reference** (from `stage_definitions.py`):
- Regular: `REGULAR_WEEK_1` through `REGULAR_WEEK_18`
- Playoffs: `WILD_CARD`, `DIVISIONAL`, `CONFERENCE_CHAMPIONSHIP`, `SUPER_BOWL`
- Offseason: `OFFSEASON_HONORS`, `OFFSEASON_FRANCHISE_TAG`, `OFFSEASON_RESIGNING`, `OFFSEASON_FREE_AGENCY`, `OFFSEASON_TRADING`, `OFFSEASON_DRAFT`, `OFFSEASON_ROSTER_CUTS`, `OFFSEASON_WAIVER_WIRE`, `OFFSEASON_TRAINING_CAMP`, `OFFSEASON_PRESEASON`

**Key Files:**
- `src/game_cycle/stage_definitions.py` - `StageType` enum, `Stage` dataclass
- `src/game_cycle/stage_controller.py` - Main orchestrator (`StageController`)
- `src/game_cycle/handlers/` - Phase handlers (regular_season.py, playoffs.py, offseason.py)
- `src/game_cycle/services/` - Business logic (35+ services):
  - `draft_service.py` - NFL Draft with AI GM picks
  - `free_agency_service.py`, `fa_wave_service.py`, `fa_wave_executor.py` - Multi-wave FA market
  - `resigning_service.py` - Contract extensions
  - `roster_cuts_service.py` - Cut to 53-man roster
  - `waiver_service.py` - Waiver wire claims
  - `training_camp_service.py` - Player progression (age-weighted development)
  - `injury_service.py` - Injury simulation, IR management, return-to-play
  - `trade_service.py` - Player/pick trades with AI evaluation
  - `player_persona_service.py` - Player personality archetypes
  - `team_attractiveness_service.py` - FA destination scoring
  - `rivalry_service.py` - Division/historical rivalries
  - `awards_service.py` - MVP, All-Pro, weekly awards
  - `game_simulator_service.py` - Game simulation orchestration
  - `owner_service.py` - Staff management (GM/HC firing/hiring)
  - `valuation_service.py` - Contract valuation engine
  - `gm_fa_proposal_engine.py` - GM proposal generation for FA signings
  - `directive_loader.py` - Load owner offseason directives
  - `proposal_generators/` - Stage-specific proposal generators (franchise_tag, resigning, fa_signing, trade, draft, cuts, waiver)
  - `hof_eligibility_service.py`, `hof_scoring_engine.py`, `hof_voting_engine.py`, `hof_induction_service.py` - Hall of Fame system (T1-T5 complete)
- `src/contract_valuation/` - Multi-factor contract valuation system:
  - `valuation_engine.py` - Core valuation logic with factor weighting
  - `market_rates.py` - Position-specific market rates (2024 NFL calibrated)
  - `gm_personality.py` - GM archetype-driven valuation adjustments
- `src/game_cycle/database/` - Schema and dedicated API classes (22+ APIs):
  - `schema.sql`, `full_schema.sql` - Complete game cycle schemas
  - `connection.py` - Database connection management
  - `standings_api.py`, `box_scores_api.py`, `team_stats_api.py` - Core stats
  - `progression_history_api.py`, `play_grades_api.py` - Performance tracking
  - `persona_api.py`, `pending_offers_api.py` - Player preferences/FA
  - `rivalry_api.py`, `head_to_head_api.py`, `team_history_api.py` - History
  - `awards_api.py`, `analytics_api.py` - Awards and analytics
  - `schedule_api.py`, `schedule_rotation_api.py`, `game_slots_api.py`, `bye_week_api.py` - Schedule
  - `proposal_api.py` - GM proposal persistence and workflow
  - `staff_api.py` - GM and Head Coach staff records
  - `hof_api.py` - Hall of Fame inductees and voting history
- `src/game_cycle/models/` - Data models for game cycle:
  - `fa_guidance.py` - Owner FA guidance/directives
  - `gm_proposal.py`, `persistent_gm_proposal.py` - GM proposal dataclasses
  - `proposal_enums.py` - ProposalType, ProposalStatus enums
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

**Dynasty Isolation Pattern:**
Every database table that stores dynasty-specific data includes `dynasty_id` as a required field. All queries MUST filter by `dynasty_id` to prevent data leakage between saves:
```python
# Correct - always include dynasty_id
cursor.execute("SELECT * FROM players WHERE dynasty_id = ? AND team_id = ?", (dynasty_id, team_id))

# Wrong - missing dynasty isolation
cursor.execute("SELECT * FROM players WHERE team_id = ?", (team_id,))
```

**Player Progression System:**
Age-weighted development with position-specific peak ages, individual potential ceilings, and attribute-category progression rates:
- Physical attributes (speed, strength) decline fastest post-peak
- Mental attributes (awareness, vision) can improve longest (even past 35)
- Technique attributes remain most stable throughout career
- See `src/game_cycle/services/training_camp_service.py` for implementation

**Game Scenario System (Milestone 9):**
Realistic in-game behavior through interconnected systems in `src/game_management/` and `src/play_engine/`:
- `timeout_manager.py` - Strategic timeout usage based on game situation
- `momentum_tracker.py` - Recent plays affect performance (±5%)
- `game_script_modifiers.py` - Play calling adapts to score/time (control game vs. desperation)
- `execution_variance.py` - Hot/cold streaks, clutch performance
- `spike_play.py`, `play_duration.py` - Clock management mechanics

**Game Statistics Flow:**
```
Play Engine (per-play stats) → GameManager → BoxScoreStore → BoxScoresAPI → Database
                                           ↓
                              PlayerStatisticsExtractor → player_season_stats table
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
- Archetypes: `src/config/archetypes/*.json` (45 files with peak ages, development curves)

### Position System
- 25 positions total: QB, RB, FB, WR, TE, LT, LG, C, RG, RT, LE, DT, RE, LOLB, MLB, ROLB, CB, FS, SS, K, P, KR, PR, LS, EDGE
- Position abbreviations: `src/constants/position_abbreviations.py`
- Position-to-archetype mapping in config files

### Common Imports
```python
from constants.team_ids import TeamIDs
from game_cycle.stage_definitions import StageType, SeasonPhase
from database.unified_api import UnifiedDatabaseAPI
from statistics.stats_api import StatsAPI
```

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

- `docs/DEVELOPMENT_PRIORITIES.md` - **Start here** for roadmap, milestone status, and dependency flow
- `docs/XX_MILESTONE_*/` - Individual milestone plans and implementation details
- `docs/archive/architecture/` - System architecture docs (play_engine.md, playoff_controller.md)
- `docs/archive/schema/database_schema.md` - Complete SQLite schema v2.0.0
