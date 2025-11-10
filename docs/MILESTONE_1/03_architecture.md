# Milestone 1 Architecture: System Design for Multi-Year Season Cycles

**Last Updated:** 2025-11-09
**Status:** 🔵 Planning
**Target:** Production-ready architecture for repeatable multi-year season cycles

---

## Executive Summary

This document defines the architectural design for implementing the 12 missing systems (~1,650 LOC) needed to enable complete offseason-to-preseason transitions and repeatable multi-year season cycles.

### Architectural Vision

**Goal:** Enable simulation of 10+ consecutive NFL seasons without manual intervention through clean service-oriented architecture.

**Key Principles:**
1. **Service Extraction:** Avoid bloating SeasonCycleController (already 2,825 lines)
2. **Single Responsibility:** Each service owns one domain (cap, players, stats, etc.)
3. **Testability:** Dependency injection for unit testing without database
4. **Idempotency:** Safe to call multiple times without side effects
5. **Transaction Safety:** Atomic multi-table operations using TransactionContext
6. **Dynasty Isolation:** All operations scoped by dynasty_id

### Integration with Existing Systems

**Builds On:**
- ✅ Statistics Preservation System (Phases 1-5 complete)
- ✅ Season Year Synchronizer (auto-recovery, drift protection)
- ✅ Salary Cap System (full CBA compliance)
- ✅ Transaction Context (atomic database operations)
- ✅ Service Extraction Pattern (TransactionService in src/services/)

**Integrates With:**
- SeasonCycleController (phase orchestration)
- PlayoffController (playoff-to-offseason transition)
- Calendar system (event scheduling)
- Database API (unified data access)

---

## Current Architecture Overview

### SeasonCycleController Today

**File:** `src/season/season_cycle_controller.py` (2,825 lines)

**Responsibilities:**
- Phase orchestration (Regular Season, Playoffs, Offseason)
- Calendar management
- Phase transition coordination
- Database state synchronization
- Active controller delegation

**Phase Transition Handler Pattern:**
```python
# Example: Regular Season → Playoffs
class RegularToPlayoffsHandler:
    def __init__(self, get_standings, seed_playoffs, create_playoff_controller, ...):
        self.get_standings = get_standings  # Dependency injection
        self.seed_playoffs = seed_playoffs
        # ...

    def execute(self, context: TransitionContext) -> TransitionResult:
        # 1. Get final standings
        standings = self.get_standings(self.dynasty_id, self.season_year)

        # 2. Seed playoffs from standings
        seeding = self.seed_playoffs(standings)

        # 3. Create playoff controller with seeding
        playoff_controller = self.create_playoff_controller(seeding)

        # 4. Update database phase
        self.update_database_phase("PLAYOFFS", self.season_year)

        return TransitionResult(success=True, next_phase="PLAYOFFS")
```

### Current OffseasonToPreseasonHandler

**File:** `src/season/phase_transition/transition_handlers/offseason_to_preseason_handler.py`

**Implementation Status:** 2/14 systems (14% complete)

**What Exists:**
1. ✅ Schedule validation (48 preseason + 272 regular season games)
2. ✅ Standings reset (all 32 teams to 0-0-0)

**What's Missing:**
3. ❌ Season year increment
4. ❌ Draft class generation timing
5. ❌ Salary cap year rollover
6. ❌ Contract year increments
7. ❌ Player retirements
8. ❌ Player aging
9. ❌ Free agent pool updates
10. ❌ Rookie contract generation
11. ⚠️ Statistics archival
12. ❌ Event cleanup
13. ❌ Depth chart initialization
14. ❌ Team needs re-analysis

---

## Proposed Architecture

### Service-Oriented Design

**Why Extract Services?**

SeasonCycleController is already 2,825 lines. Adding ~1,650 LOC directly would:
- ❌ Create 4,475-line monolith
- ❌ Reduce testability (requires full database setup)
- ❌ Mix orchestration with domain logic
- ❌ Violate Single Responsibility Principle

**Service Extraction Pattern** (proven in Phase 3):
- ✅ Extracted TransactionService from SeasonCycleController
- ✅ Reduced coupling, improved testability
- ✅ Enabled dependency injection for testing
- ✅ Delivered 77% faster than estimated

### Proposed Service Architecture

```
OffseasonToPreseasonHandler (Orchestrator - 150 LOC)
├── SeasonYearService (50 LOC)
├── SalaryCapYearService (250 LOC)
│   ├── Cap rollover logic
│   └── Contract year increments
├── PlayerLifecycleService (450 LOC)
│   ├── Retirements
│   ├── Aging
│   └── Free agent pool updates
├── RookieContractService (150 LOC)
├── StatisticsArchivalService (500 LOC) [P2 - Optional]
├── EventCleanupService (100 LOC) [P2 - Optional]
├── DepthChartService (150 LOC) [P2 - Optional]
└── TeamNeedsService (100 LOC) [P2 - Optional]
```

---

## Service Design Specifications

### 1. SeasonYearService (P0 - Critical)

**Location:** `src/season/services/season_year_service.py`

**Responsibilities:**
- Increment season_year across all components
- Synchronize controller, database, calendar
- Prevent drift using SeasonYearSynchronizer

**Public API:**
```python
class SeasonYearService:
    """Centralized season year increment service."""

    def __init__(self, db: UnifiedDatabaseAPI, dynasty_id: str):
        self.db = db
        self.dynasty_id = dynasty_id

    def increment_season_year(
        self,
        current_year: int,
        synchronizer: SeasonYearSynchronizer
    ) -> int:
        """
        Increment season year atomically across all components.

        Args:
            current_year: Current season year
            synchronizer: SeasonYearSynchronizer instance

        Returns:
            New season year (current_year + 1)

        Raises:
            SeasonYearDriftError: If synchronization fails
        """
        new_year = current_year + 1

        # Use synchronizer to update atomically
        synchronizer.increment_year()

        # Update database dynasty state
        self.db.dynasty_update_state(
            season=new_year,
            current_phase="PRESEASON",
            current_week=0
        )

        return new_year
```

**Database Changes:** None (uses existing dynasty_state table)

**Dependencies:**
- SeasonYearSynchronizer (existing)
- UnifiedDatabaseAPI (existing)

**Estimated LOC:** 50

---

### 2. SalaryCapYearService (P0 - Critical)

**Location:** `src/salary_cap/cap_year_service.py`

**Responsibilities:**
- Roll over salary cap to new league year
- Calculate carryover from previous year
- Increment contract years for all players
- Detect contract expirations
- Update free agency status

**Public API:**
```python
class SalaryCapYearService:
    """Salary cap year rollover and contract year increment service."""

    def __init__(
        self,
        db: UnifiedDatabaseAPI,
        cap_calculator: CapCalculator,
        dynasty_id: str
    ):
        self.db = db
        self.cap_calculator = cap_calculator
        self.dynasty_id = dynasty_id

    def rollover_cap_year(
        self,
        old_year: int,
        new_year: int
    ) -> Dict[int, CapRolloverResult]:
        """
        Roll over salary cap for all 32 teams to new league year.

        Args:
            old_year: Previous season year
            new_year: New season year

        Returns:
            Dict mapping team_id to CapRolloverResult with:
                - new_cap_space
                - carryover_amount
                - dead_money
                - top_51_total
        """
        results = {}

        for team_id in range(1, 33):  # All 32 teams
            # Get previous year cap state
            old_cap = self.db.cap_get_team_summary(team_id, old_year)

            # Calculate carryover (unused cap space)
            carryover = max(0, old_cap['cap_space'])

            # Get dead money carrying over
            dead_money = self._calculate_carryover_dead_money(team_id, new_year)

            # Create new cap record
            new_cap_space = self.cap_calculator.calculate_cap_space(
                team_id=team_id,
                season_year=new_year,
                carryover=carryover,
                dead_money=dead_money
            )

            results[team_id] = CapRolloverResult(
                new_cap_space=new_cap_space,
                carryover_amount=carryover,
                dead_money=dead_money
            )

        return results

    def increment_contract_years(
        self,
        season_year: int
    ) -> ContractIncrementResult:
        """
        Increment contract years for all players, detect expirations.

        Args:
            season_year: New season year

        Returns:
            ContractIncrementResult with:
                - total_contracts: Total contracts processed
                - expired_contracts: List of expired contracts
                - updated_contracts: Contracts with years incremented
        """
        all_contracts = self.db.cap_get_all_active_contracts(self.dynasty_id)

        expired = []
        updated = []

        for contract in all_contracts:
            current_year = contract['current_year']
            total_years = contract['total_years']

            if current_year >= total_years:
                # Contract expired
                self._expire_contract(contract['contract_id'], season_year)
                expired.append(contract)
            else:
                # Increment year
                self._increment_contract_year(contract['contract_id'])
                updated.append(contract)

        return ContractIncrementResult(
            total_contracts=len(all_contracts),
            expired_contracts=expired,
            updated_contracts=updated
        )
```

**Database Changes:**
```sql
-- Add carryover tracking
ALTER TABLE salary_cap_summary ADD COLUMN carryover_amount INTEGER DEFAULT 0;

-- Add contract history table
CREATE TABLE IF NOT EXISTS contract_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    season_year INTEGER NOT NULL,
    action TEXT NOT NULL,  -- 'SIGNED', 'EXPIRED', 'YEAR_INCREMENT'
    timestamp INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL
);
```

**Dependencies:**
- CapCalculator (existing)
- UnifiedDatabaseAPI (existing)

**Estimated LOC:** 250 (150 rollover + 100 contract increments)

---

### 3. PlayerLifecycleService (P1 - High Priority)

**Location:** `src/player_generation/player_lifecycle_service.py`

**Responsibilities:**
- Detect and process player retirements
- Age all active players (+1 year)
- Update free agent pool with expired contracts
- Apply aging effects to attributes

**Public API:**
```python
class PlayerLifecycleService:
    """Player retirement, aging, and free agent pool management."""

    def __init__(self, db: UnifiedDatabaseAPI, dynasty_id: str):
        self.db = db
        self.dynasty_id = dynasty_id

    def process_retirements(
        self,
        season_year: int
    ) -> RetirementResult:
        """
        Process retirements for all eligible players.

        Retirement Logic:
        - Age 35+: 10% base retirement chance
        - Age 37+: 25% retirement chance
        - Age 39+: 50% retirement chance
        - Age 40+: 75% retirement chance
        - Overall rating <70: +15% retirement chance
        - Injury history: +5% per major injury

        Returns:
            RetirementResult with retired player list
        """
        pass

    def age_all_players(self, season_year: int) -> AgingResult:
        """
        Age all active players by 1 year, apply attribute degradation.

        Aging Effects:
        - Speed: -1 per year after age 28
        - Strength: -1 per year after age 30
        - Awareness: +1 per year until age 32
        - Injury risk: +2% per year after age 30

        Returns:
            AgingResult with aged player count
        """
        pass

    def update_free_agent_pool(
        self,
        expired_contracts: List[Dict]
    ) -> FreeAgentResult:
        """
        Add players with expired contracts to free agent pool.

        Args:
            expired_contracts: List from ContractIncrementResult

        Returns:
            FreeAgentResult with new UFA/RFA counts
        """
        pass
```

**Database Changes:**
```sql
-- Retired players table
CREATE TABLE IF NOT EXISTS retired_players (
    retired_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    retirement_year INTEGER NOT NULL,
    retirement_age INTEGER NOT NULL,
    career_years INTEGER NOT NULL,
    final_team_id INTEGER,
    dynasty_id TEXT NOT NULL
);

-- Player attribute history
CREATE TABLE IF NOT EXISTS player_attribute_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    season_year INTEGER NOT NULL,
    age INTEGER NOT NULL,
    speed INTEGER,
    strength INTEGER,
    awareness INTEGER,
    overall_rating INTEGER,
    dynasty_id TEXT NOT NULL
);
```

**Dependencies:**
- UnifiedDatabaseAPI (existing)
- Random number generation for retirement probability

**Estimated LOC:** 450 (200 retirements + 150 aging + 100 free agent pool)

---

### 4. RookieContractService (P1 - High Priority)

**Location:** `src/salary_cap/rookie_contract_service.py`

**Responsibilities:**
- Generate rookie contracts for draft class
- Calculate rookie pool allocation
- Assign contracts to drafted players
- Apply rookie wage scale

**Public API:**
```python
class RookieContractService:
    """Rookie contract generation using NFL wage scale."""

    def __init__(
        self,
        db: UnifiedDatabaseAPI,
        cap_calculator: CapCalculator,
        dynasty_id: str
    ):
        self.db = db
        self.cap_calculator = cap_calculator
        self.dynasty_id = dynasty_id

    def generate_rookie_contracts(
        self,
        draft_class_id: str,
        season_year: int
    ) -> RookieContractResult:
        """
        Generate contracts for entire draft class.

        Rookie Wage Scale (simplified):
        - Pick 1: 4 years, $9.5M/year (prorated signing bonus)
        - Pick 2-10: 4 years, $8M-$6M/year
        - Pick 11-32: 4 years, $5M-$3M/year
        - Rounds 2-3: 4 years, $2M-$1M/year
        - Rounds 4-7: 4 years, $800K-$750K/year

        Returns:
            RookieContractResult with contract list
        """
        pass
```

**Database Changes:** None (uses existing contracts table)

**Dependencies:**
- CapCalculator (existing)
- DraftClassGenerator (existing)
- UnifiedDatabaseAPI (existing)

**Estimated LOC:** 150

---

### 5. Enhanced OffseasonToPreseasonHandler

**Location:** `src/season/phase_transition/transition_handlers/offseason_to_preseason_handler.py`

**Current:** 2/14 systems (Schedule Validation, Standings Reset)

**Enhanced:** 14/14 systems (orchestrates all services)

**Proposed Structure:**
```python
class OffseasonToPreseasonHandler:
    """
    Enhanced handler for offseason → preseason transition.

    Orchestrates 8 services to complete all 14 initialization systems.
    """

    def __init__(
        self,
        # Existing dependencies
        verify_schedule: Callable,
        reset_standings: Callable,
        update_database_phase: Callable,

        # NEW: Service dependencies (injected)
        season_year_service: SeasonYearService,
        salary_cap_year_service: SalaryCapYearService,
        player_lifecycle_service: PlayerLifecycleService,
        rookie_contract_service: RookieContractService,

        # Optional services (P2)
        statistics_archival_service: Optional[StatisticsArchivalService] = None,
        event_cleanup_service: Optional[EventCleanupService] = None,

        dynasty_id: str,
        season_year: int,
        verbose_logging: bool = True
    ):
        self.verify_schedule = verify_schedule
        self.reset_standings = reset_standings
        self.update_database_phase = update_database_phase

        # Service instances
        self.year_service = season_year_service
        self.cap_service = salary_cap_year_service
        self.lifecycle_service = player_lifecycle_service
        self.rookie_service = rookie_contract_service
        self.stats_service = statistics_archival_service
        self.event_service = event_cleanup_service

        self.dynasty_id = dynasty_id
        self.season_year = season_year
        self.verbose_logging = verbose_logging

    def execute(self, context: TransitionContext) -> TransitionResult:
        """
        Execute complete offseason → preseason transition.

        Execution Order (Critical Dependencies):
        1. ✅ Schedule validation (existing)
        2. ✅ Standings reset (existing)
        3. 🆕 Season year increment (must happen before cap/contracts)
        4. 🆕 Salary cap year rollover (needs new year)
        5. 🆕 Contract year increments (needs new year)
        6. 🆕 Player retirements (before draft class generation)
        7. 🆕 Player aging (before free agency)
        8. 🆕 Free agent pool updates (after contract expirations)
        9. 🆕 Draft class generation (timing fix - happens here, not preseason)
        10. 🆕 Rookie contract generation (after draft)
        11. 🆕 Statistics archival (P2 - optional)
        12. 🆕 Event cleanup (P2 - optional)
        13. 🆕 Depth chart initialization (P2 - optional)
        14. 🆕 Team needs re-analysis (P2 - optional)
        """
        results = {}

        try:
            # === PHASE 1: EXISTING SYSTEMS ===

            # System 1: Schedule validation
            schedule_valid = self.verify_schedule(self.dynasty_id, self.season_year)
            results['schedule_validation'] = schedule_valid

            # System 2: Standings reset
            standings_reset = self.reset_standings(self.dynasty_id, self.season_year)
            results['standings_reset'] = standings_reset

            # === PHASE 2: SEASON YEAR INCREMENT (P0) ===

            # System 3: Increment season year
            new_year = self.year_service.increment_season_year(
                current_year=self.season_year,
                synchronizer=context.synchronizer
            )
            results['season_year_increment'] = new_year
            self.season_year = new_year  # Update for subsequent operations

            # === PHASE 3: SALARY CAP OPERATIONS (P0) ===

            # System 5: Salary cap year rollover
            cap_rollover = self.cap_service.rollover_cap_year(
                old_year=new_year - 1,
                new_year=new_year
            )
            results['cap_rollover'] = cap_rollover

            # System 6: Contract year increments
            contract_update = self.cap_service.increment_contract_years(
                season_year=new_year
            )
            results['contract_increments'] = contract_update

            # === PHASE 4: PLAYER LIFECYCLE (P1) ===

            # System 7: Player retirements
            retirements = self.lifecycle_service.process_retirements(
                season_year=new_year
            )
            results['retirements'] = retirements

            # System 8: Player aging
            aging = self.lifecycle_service.age_all_players(
                season_year=new_year
            )
            results['aging'] = aging

            # System 9: Free agent pool updates
            free_agents = self.lifecycle_service.update_free_agent_pool(
                expired_contracts=contract_update.expired_contracts
            )
            results['free_agent_updates'] = free_agents

            # === PHASE 5: DRAFT & ROOKIES (P0/P1) ===

            # System 4: Draft class generation (timing fix)
            draft_class = self._generate_draft_class(new_year)
            results['draft_class_generation'] = draft_class

            # System 10: Rookie contract generation
            rookie_contracts = self.rookie_service.generate_rookie_contracts(
                draft_class_id=draft_class['draft_class_id'],
                season_year=new_year
            )
            results['rookie_contracts'] = rookie_contracts

            # === PHASE 6: OPTIONAL SYSTEMS (P2) ===

            # System 11: Statistics archival (if enabled)
            if self.stats_service:
                stats_archival = self.stats_service.archive_season_stats(
                    season_year=new_year - 1
                )
                results['statistics_archival'] = stats_archival

            # System 12: Event cleanup (if enabled)
            if self.event_service:
                event_cleanup = self.event_service.cleanup_old_events(
                    season_year=new_year - 1
                )
                results['event_cleanup'] = event_cleanup

            # === PHASE 7: DATABASE UPDATE ===

            # Update database phase to PRESEASON
            self.update_database_phase("PRESEASON", new_year)

            return TransitionResult(
                success=True,
                next_phase="PRESEASON",
                data=results,
                message=f"Successfully transitioned to Season {new_year} Preseason"
            )

        except Exception as e:
            return TransitionResult(
                success=False,
                error_message=f"Offseason transition failed: {e}",
                data=results  # Partial results for debugging
            )
```

**Estimated LOC:** 150 (orchestration logic + error handling)

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    OFFSEASON → PRESEASON TRANSITION                      │
│                   (OffseasonToPreseasonHandler.execute)                  │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: EXISTING SYSTEMS                                                │
├─────────────────────────────────────────────────────────────────────────┤
│ 1. verify_schedule()           → Validate 320 games exist               │
│ 2. reset_standings()           → All teams to 0-0-0                     │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: SEASON YEAR INCREMENT (P0)                                      │
├─────────────────────────────────────────────────────────────────────────┤
│ 3. SeasonYearService.increment_season_year()                             │
│    ├─> SeasonYearSynchronizer.increment_year()                           │
│    └─> UnifiedDatabaseAPI.dynasty_update_state(season=new_year)         │
│                                                                           │
│    DATABASE WRITES:                                                      │
│    • dynasty_state.season_year = 2025                                    │
│    • dynasty_state.current_phase = "PRESEASON"                           │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: SALARY CAP OPERATIONS (P0)                                      │
├─────────────────────────────────────────────────────────────────────────┤
│ 5. SalaryCapYearService.rollover_cap_year(2024 → 2025)                  │
│    FOR EACH TEAM (1-32):                                                 │
│    ├─> cap_get_team_summary(team_id, 2024)                              │
│    ├─> Calculate carryover = max(0, cap_space)                          │
│    ├─> Calculate dead_money carryover                                   │
│    └─> CapCalculator.calculate_cap_space(2025)                          │
│                                                                           │
│    DATABASE WRITES (x32 teams):                                          │
│    • salary_cap_summary.season_year = 2025                               │
│    • salary_cap_summary.carryover_amount = <calculated>                  │
│                                                                           │
│ 6. SalaryCapYearService.increment_contract_years(2025)                   │
│    FOR EACH CONTRACT:                                                    │
│    ├─> IF current_year >= total_years:                                  │
│    │   └─> EXPIRE contract → free agency                                │
│    └─> ELSE:                                                             │
│        └─> INCREMENT current_year += 1                                   │
│                                                                           │
│    DATABASE WRITES:                                                      │
│    • contracts.current_year += 1 (for active contracts)                  │
│    • contracts.status = 'EXPIRED' (for expired contracts)                │
│    • contract_history records (for auditing)                             │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: PLAYER LIFECYCLE (P1)                                           │
├─────────────────────────────────────────────────────────────────────────┤
│ 7. PlayerLifecycleService.process_retirements(2025)                      │
│    FOR EACH PLAYER:                                                      │
│    ├─> Calculate retirement probability                                 │
│    │   • Age: 35+ → 10%, 37+ → 25%, 39+ → 50%, 40+ → 75%               │
│    │   • Overall <70: +15%                                               │
│    │   • Injury history: +5% per major injury                            │
│    └─> IF retire: Move to retired_players table                         │
│                                                                           │
│    DATABASE WRITES:                                                      │
│    • retired_players (for retirees)                                      │
│    • players.status = 'RETIRED'                                          │
│                                                                           │
│ 8. PlayerLifecycleService.age_all_players(2025)                          │
│    FOR EACH ACTIVE PLAYER:                                               │
│    ├─> Age += 1                                                          │
│    ├─> Apply attribute degradation:                                     │
│    │   • Speed: -1 after age 28                                          │
│    │   • Strength: -1 after age 30                                       │
│    │   • Awareness: +1 until age 32                                      │
│    └─> Log to player_attribute_history                                  │
│                                                                           │
│    DATABASE WRITES:                                                      │
│    • players.age += 1 (for all active players)                           │
│    • players.speed/strength/awareness (attribute changes)                │
│    • player_attribute_history (for tracking)                             │
│                                                                           │
│ 9. PlayerLifecycleService.update_free_agent_pool(expired_contracts)      │
│    FOR EACH EXPIRED CONTRACT:                                            │
│    ├─> Determine FA type (UFA vs RFA)                                   │
│    │   • <4 accrued seasons: RFA                                         │
│    │   • ≥4 accrued seasons: UFA                                         │
│    └─> Add to free_agents table                                         │
│                                                                           │
│    DATABASE WRITES:                                                      │
│    • free_agents table (for new UFAs/RFAs)                               │
│    • players.free_agent_type = 'UFA' or 'RFA'                            │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: DRAFT & ROOKIES (P0/P1)                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ 4. DraftClassGenerator.generate_class(2025)  [TIMING FIX]               │
│    ├─> Generate 300+ rookie players                                     │
│    │   • 7 rounds × 32 teams = 224 picks                                 │
│    │   • Compensatory picks: ~32                                         │
│    │   • UDFAs: ~50                                                      │
│    └─> Assign to draft_class_2025                                       │
│                                                                           │
│    DATABASE WRITES:                                                      │
│    • draft_classes table (draft_class_id, season_year=2025)             │
│    • generated_players table (300+ rookies)                              │
│                                                                           │
│ 10. RookieContractService.generate_rookie_contracts(draft_class_id)     │
│     FOR EACH DRAFTED PLAYER:                                             │
│     ├─> Calculate rookie wage scale value                               │
│     │   • Pick 1: $9.5M/year × 4 years                                   │
│     │   • Pick 2-10: $8M-$6M/year × 4 years                              │
│     │   • Rounds 2-7: $2M-$750K/year × 4 years                           │
│     └─> Create contract record                                          │
│                                                                           │
│     DATABASE WRITES:                                                     │
│     • contracts table (224 rookie contracts)                             │
│     • salary_cap_summary updates (rookie pool allocation)                │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 6: OPTIONAL SYSTEMS (P2)                                           │
├─────────────────────────────────────────────────────────────────────────┤
│ 11. StatisticsArchivalService.archive_season_stats(2024)  [OPTIONAL]    │
│     • Compress 2024 statistics for long-term storage                     │
│     • Keep raw data for 3 seasons, archive older data                    │
│                                                                           │
│ 12. EventCleanupService.cleanup_old_events(2024)  [OPTIONAL]            │
│     • Remove completed events from previous seasons                      │
│     • Preserve milestone events (draft, schedule release, etc.)          │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 7: DATABASE PHASE UPDATE                                           │
├─────────────────────────────────────────────────────────────────────────┤
│ update_database_phase("PRESEASON", 2025)                                │
│                                                                           │
│ DATABASE WRITES:                                                         │
│ • dynasty_state.current_phase = "PRESEASON"                              │
│ • dynasty_state.current_week = 0                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                              ✅ TRANSITION COMPLETE
                           Ready for Preseason Week 1
```

---

## Service Interaction Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     SeasonCycleController (Orchestrator)                  │
│                                                                            │
│  • Phase management (Regular Season, Playoffs, Offseason)                 │
│  • Calendar coordination                                                  │
│  • Active controller delegation                                           │
│  • Database state synchronization                                         │
└──────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ delegates to
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  OffseasonToPreseasonHandler (Orchestrator)               │
│                                                                            │
│  • Coordinates all 14 initialization systems                              │
│  • Manages service dependencies and execution order                       │
│  • Handles errors and rollback                                            │
│  • Reports transition results                                             │
└──────────────────────────────────────────────────────────────────────────┘
         │              │              │              │              │
         │              │              │              │              │
         ▼              ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Season     │ │   Salary     │ │   Player     │ │   Rookie     │ │  Statistics  │
│    Year      │ │     Cap      │ │  Lifecycle   │ │  Contract    │ │  Archival    │
│   Service    │ │     Year     │ │   Service    │ │   Service    │ │   Service    │
│              │ │   Service    │ │              │ │              │ │              │
│              │ │              │ │              │ │              │ │              │
│ • Increment  │ │ • Cap        │ │ • Retire-    │ │ • Generate   │ │ • Archive    │
│   year       │ │   rollover   │ │   ments      │ │   rookie     │ │   old stats  │
│ • Sync all   │ │ • Contract   │ │ • Aging      │ │   contracts  │ │ • Compress   │
│   components │ │   increments │ │ • FA pool    │ │ • Wage scale │ │   data       │
│ • Prevent    │ │ • Carryover  │ │   updates    │ │   calc       │ │ • Cleanup    │
│   drift      │ │   calc       │ │              │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
         │              │              │              │              │
         │              │              │              │              │
         └──────────────┴──────────────┴──────────────┴──────────────┘
                                      │
                                      │ all services use
                                      ▼
                        ┌──────────────────────────────┐
                        │    UnifiedDatabaseAPI        │
                        │                              │
                        │  • Single source of truth    │
                        │  • Dynasty isolation         │
                        │  • Transaction management    │
                        │  • Query execution           │
                        └──────────────────────────────┘
                                      │
                                      │ uses
                                      ▼
                        ┌──────────────────────────────┐
                        │    TransactionContext        │
                        │                              │
                        │  • BEGIN/COMMIT/ROLLBACK     │
                        │  • Savepoint support         │
                        │  • Atomic operations         │
                        └──────────────────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────────┐
                        │    SQLite Database           │
                        │  (nfl_simulation.db)         │
                        └──────────────────────────────┘
```

---

## Design Patterns

### 1. Service Pattern

**Why:** Avoid bloating SeasonCycleController (already 2,825 lines)

**Pattern:**
```python
# GOOD: Service extraction
class SeasonYearService:
    """Single responsibility: Year increment logic"""
    def increment_season_year(self, current_year: int) -> int:
        # Year increment logic here
        pass

# BAD: Monolithic controller
class SeasonCycleController:
    def _increment_season_year(self):
        # Embedded in 3,000+ line controller
        pass
```

**Benefits:**
- ✅ Testable in isolation
- ✅ Reusable across different contexts
- ✅ Clear ownership of domain logic
- ✅ Easier to maintain and extend

---

### 2. Dependency Injection

**Why:** Enable testing without full database setup

**Pattern:**
```python
# Constructor injection for testing
class OffseasonToPreseasonHandler:
    def __init__(
        self,
        season_year_service: SeasonYearService,  # Injected
        cap_year_service: SalaryCapYearService,  # Injected
        # ...
    ):
        self.year_service = season_year_service
        self.cap_service = cap_year_service

# Usage in production
handler = OffseasonToPreseasonHandler(
    season_year_service=SeasonYearService(db, dynasty_id),
    cap_year_service=SalaryCapYearService(db, calculator, dynasty_id),
)

# Usage in testing (with mocks)
handler = OffseasonToPreseasonHandler(
    season_year_service=MockSeasonYearService(),  # Mock
    cap_year_service=MockCapYearService(),        # Mock
)
```

---

### 3. Transaction Boundaries

**Why:** Ensure atomic multi-table operations

**Pattern:**
```python
from src.database.transaction_context import TransactionContext, TransactionMode

class SalaryCapYearService:
    def rollover_cap_year(self, old_year: int, new_year: int):
        # Use TransactionContext for atomic operations
        with TransactionContext(
            self.db.conn,
            mode=TransactionMode.IMMEDIATE
        ) as txn:
            # All 32 teams rolled over atomically
            for team_id in range(1, 33):
                self._rollover_team_cap(team_id, old_year, new_year)

            # Explicit commit (all or nothing)
            txn.commit()
```

**Benefits:**
- ✅ Atomic all-or-nothing operations
- ✅ Automatic rollback on errors
- ✅ Nested transaction support via savepoints
- ✅ Proven pattern (25 passing tests)

---

### 4. Idempotency

**Why:** Safe to call multiple times without side effects

**Pattern:**
```python
class SeasonYearService:
    def increment_season_year(self, current_year: int) -> int:
        # Early return check (idempotent)
        db_year = self.db.dynasty_get_state()['season_year']
        if db_year == current_year + 1:
            # Already incremented, safe to return
            return db_year

        # Proceed with increment
        new_year = current_year + 1
        self.db.dynasty_update_state(season=new_year)
        return new_year
```

**Benefits:**
- ✅ Safe to retry on failure
- ✅ Prevents double-increment bugs
- ✅ Resilient to network/database issues

---

### 5. Error Handling

**Why:** Graceful degradation and debugging

**Pattern:**
```python
class OffseasonToPreseasonHandler:
    def execute(self, context: TransitionContext) -> TransitionResult:
        results = {}

        try:
            # Critical systems (P0)
            results['year_increment'] = self.year_service.increment_season_year(...)
            results['cap_rollover'] = self.cap_service.rollover_cap_year(...)

            # High priority systems (P1)
            try:
                results['retirements'] = self.lifecycle_service.process_retirements(...)
            except RetirementError as e:
                # Log but continue (non-critical)
                logging.warning(f"Retirement processing failed: {e}")
                results['retirements'] = None

            return TransitionResult(success=True, data=results)

        except Exception as e:
            # Fail loudly for critical errors
            logging.error(f"Critical transition failure: {e}")
            return TransitionResult(
                success=False,
                error_message=str(e),
                data=results  # Partial results for debugging
            )
```

---

## Database Schema Design

### New Tables

#### 1. contract_history (Audit Trail)
```sql
CREATE TABLE IF NOT EXISTS contract_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    season_year INTEGER NOT NULL,
    action TEXT NOT NULL,  -- 'SIGNED', 'EXPIRED', 'YEAR_INCREMENT', 'RESTRUCTURE'
    old_values TEXT,       -- JSON: Previous contract state
    new_values TEXT,       -- JSON: New contract state
    timestamp INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,

    INDEX idx_contract_history_contract (contract_id),
    INDEX idx_contract_history_player (player_id, dynasty_id),
    INDEX idx_contract_history_season (season_year, dynasty_id)
);
```

#### 2. retired_players (Player Retirements)
```sql
CREATE TABLE IF NOT EXISTS retired_players (
    retired_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    retirement_year INTEGER NOT NULL,
    retirement_age INTEGER NOT NULL,
    career_years INTEGER NOT NULL,
    final_team_id INTEGER,
    final_position TEXT,
    career_stats TEXT,     -- JSON: Career totals
    dynasty_id TEXT NOT NULL,

    INDEX idx_retired_players_year (retirement_year, dynasty_id),
    INDEX idx_retired_players_team (final_team_id, dynasty_id)
);
```

#### 3. player_attribute_history (Aging Tracking)
```sql
CREATE TABLE IF NOT EXISTS player_attribute_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    season_year INTEGER NOT NULL,
    age INTEGER NOT NULL,
    speed INTEGER,
    strength INTEGER,
    awareness INTEGER,
    overall_rating INTEGER,
    injury_risk INTEGER,   -- Percentage
    timestamp INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,

    INDEX idx_player_attr_history_player (player_id, dynasty_id),
    INDEX idx_player_attr_history_season (season_year, dynasty_id)
);
```

#### 4. draft_classes (Draft Class Tracking)
```sql
CREATE TABLE IF NOT EXISTS draft_classes (
    draft_class_id TEXT PRIMARY KEY,
    season_year INTEGER NOT NULL,
    generation_date INTEGER NOT NULL,
    total_players INTEGER NOT NULL,
    drafted_count INTEGER DEFAULT 0,
    udfa_count INTEGER DEFAULT 0,
    dynasty_id TEXT NOT NULL,

    INDEX idx_draft_classes_season (season_year, dynasty_id)
);
```

### Modified Tables

#### 1. salary_cap_summary (Add Carryover Tracking)
```sql
ALTER TABLE salary_cap_summary
    ADD COLUMN carryover_amount INTEGER DEFAULT 0;

ALTER TABLE salary_cap_summary
    ADD COLUMN previous_year_cap_space INTEGER DEFAULT 0;
```

#### 2. contracts (Add Year Tracking)
```sql
ALTER TABLE contracts
    ADD COLUMN current_year INTEGER DEFAULT 1;

ALTER TABLE contracts
    ADD COLUMN is_rookie_contract INTEGER DEFAULT 0;  -- Boolean flag

-- Index for contract expiration queries
CREATE INDEX IF NOT EXISTS idx_contracts_expiration
    ON contracts(current_year, total_years, dynasty_id);
```

#### 3. players (Add Retirement/Aging Fields)
```sql
ALTER TABLE players
    ADD COLUMN retirement_probability REAL DEFAULT 0.0;  -- Calculated %

ALTER TABLE players
    ADD COLUMN career_years INTEGER DEFAULT 0;

ALTER TABLE players
    ADD COLUMN injury_history TEXT;  -- JSON: List of injuries

-- Index for retirement queries
CREATE INDEX IF NOT EXISTS idx_players_retirement
    ON players(age, overall_rating, dynasty_id);
```

---

## Testing Architecture

### Unit Testing Strategy

**Principle:** Each service testable in isolation without database

**Pattern:**
```python
# tests/season/services/test_season_year_service.py

from unittest.mock import Mock, MagicMock
from src.season.services.season_year_service import SeasonYearService

class TestSeasonYearService:
    """Unit tests for SeasonYearService (no database required)."""

    def test_increment_season_year_success(self):
        # Mock dependencies
        mock_db = Mock()
        mock_synchronizer = Mock()

        # Create service with mocks
        service = SeasonYearService(db=mock_db, dynasty_id="test_dynasty")

        # Execute
        new_year = service.increment_season_year(
            current_year=2024,
            synchronizer=mock_synchronizer
        )

        # Verify
        assert new_year == 2025
        mock_synchronizer.increment_year.assert_called_once()
        mock_db.dynasty_update_state.assert_called_once_with(
            season=2025,
            current_phase="PRESEASON",
            current_week=0
        )

    def test_increment_season_year_idempotency(self):
        # Test that calling twice doesn't double-increment
        mock_db = Mock()
        mock_db.dynasty_get_state.return_value = {'season_year': 2025}

        service = SeasonYearService(db=mock_db, dynasty_id="test_dynasty")

        # Call twice
        year1 = service.increment_season_year(2024, Mock())
        year2 = service.increment_season_year(2024, Mock())

        # Should return same year, only update once
        assert year1 == year2 == 2025
```

### Integration Testing Strategy

**Principle:** Test complete offseason transition with real database

**Pattern:**
```python
# tests/season/integration/test_offseason_to_preseason_integration.py

import pytest
from src.database.unified_api import UnifiedDatabaseAPI
from src.season.phase_transition.transition_handlers.offseason_to_preseason_handler import OffseasonToPreseasonHandler

@pytest.fixture
def test_database():
    """Create in-memory test database."""
    db = UnifiedDatabaseAPI(database_path=":memory:", dynasty_id="test_dynasty")
    # Initialize schema, seed test data
    return db

class TestOffseasonToPreseasonIntegration:
    """Integration tests for complete transition."""

    def test_two_season_cycle(self, test_database):
        """Test complete 2-season cycle: 2024 → Offseason → 2025."""

        # === SEASON 1 (2024) ===
        # Simulate regular season, playoffs, offseason
        # ...

        # === TRANSITION: OFFSEASON → PRESEASON ===
        handler = OffseasonToPreseasonHandler(
            # Real service instances with test database
            season_year_service=SeasonYearService(test_database, "test_dynasty"),
            salary_cap_year_service=SalaryCapYearService(test_database, ...),
            # ...
            dynasty_id="test_dynasty",
            season_year=2024
        )

        result = handler.execute(context)

        # === VERIFY RESULTS ===
        assert result.success is True
        assert result.next_phase == "PRESEASON"

        # Verify season year incremented
        db_state = test_database.dynasty_get_state()
        assert db_state['season_year'] == 2025

        # Verify cap rolled over
        cap_summary = test_database.cap_get_team_summary(team_id=1, season=2025)
        assert cap_summary['carryover_amount'] >= 0

        # Verify contracts incremented
        contracts = test_database.cap_get_all_active_contracts("test_dynasty")
        assert all(c['season_year'] == 2025 for c in contracts)

        # Verify draft class generated
        draft_classes = test_database.draft_get_classes(season=2025)
        assert len(draft_classes) == 1

        # === SEASON 2 (2025) ===
        # Verify can simulate second season
        # ...
```

---

## Performance Considerations

### Execution Time Targets

**Goal:** Complete offseason transition in <20 seconds total

| System | Target Time | Optimization |
|--------|-------------|--------------|
| Schedule Validation | <0.1s | Single query with COUNT(*) |
| Standings Reset | <0.5s | Batch UPDATE for 32 teams |
| Season Year Increment | <0.1s | Single UPDATE |
| Cap Rollover | <2s | Batch processing, 32 teams |
| Contract Increments | <3s | Single UPDATE with WHERE clause |
| Retirements | <2s | Batch probability calculation |
| Aging | <3s | Batch attribute updates |
| FA Pool Updates | <1s | Batch INSERT |
| Draft Class Generation | <5s | Optimized player generation |
| Rookie Contracts | <2s | Batch INSERT |
| **TOTAL** | **<20s** | |

### Database Query Efficiency

**Batch Operations:**
```python
# GOOD: Single batch update
UPDATE players
SET age = age + 1
WHERE dynasty_id = ? AND status = 'ACTIVE';

# BAD: Individual updates (N queries)
for player in players:
    UPDATE players SET age = age + 1 WHERE player_id = ?;
```

**Strategic Indexes:**
```sql
-- Contract expiration queries
CREATE INDEX idx_contracts_expiration
    ON contracts(current_year, total_years, dynasty_id);

-- Retirement probability queries
CREATE INDEX idx_players_retirement
    ON players(age, overall_rating, dynasty_id);

-- Cap summary queries
CREATE INDEX idx_cap_summary_season
    ON salary_cap_summary(season_year, dynasty_id);
```

---

## Scalability & Maintainability

### Code Organization Principles

**File Structure:**
```
src/
├── season/
│   ├── services/
│   │   └── season_year_service.py          (50 LOC)
│   └── phase_transition/
│       └── transition_handlers/
│           └── offseason_to_preseason_handler.py  (150 LOC enhanced)
│
├── salary_cap/
│   ├── cap_year_service.py                  (250 LOC)
│   └── rookie_contract_service.py           (150 LOC)
│
├── player_generation/
│   └── player_lifecycle_service.py          (450 LOC)
│
└── statistics/
    └── statistics_archival_service.py       (500 LOC) [P2]
```

### SOLID Principles Application

1. **Single Responsibility Principle**
   - Each service owns one domain (year, cap, players, stats)
   - Handler only orchestrates, doesn't implement logic

2. **Open/Closed Principle**
   - Services open for extension (new retirement rules)
   - Closed for modification (stable APIs)

3. **Liskov Substitution Principle**
   - Services implement consistent interfaces
   - Mock services substitute for real services in tests

4. **Interface Segregation Principle**
   - Services expose minimal public APIs
   - Handler only depends on methods it uses

5. **Dependency Inversion Principle**
   - Handler depends on service abstractions
   - Concrete implementations injected at runtime

### Future Extensibility

**Adding New Systems:**
```python
# Easy to add new optional services
class OffseasonToPreseasonHandler:
    def __init__(
        self,
        # ... existing services ...

        # NEW: Injury recovery service (future)
        injury_recovery_service: Optional[InjuryRecoveryService] = None,
    ):
        self.injury_service = injury_recovery_service

    def execute(self, context):
        # ... existing logic ...

        # NEW: Injury recovery (if enabled)
        if self.injury_service:
            results['injury_recovery'] = self.injury_service.process_recoveries(...)
```

---

## Risk Mitigation

### Technical Risks

1. **Risk:** Database migration failures (schema changes)
   - **Mitigation:** Write reversible migrations, test on backup database first
   - **Rollback:** Migration scripts include DROP/ALTER rollback statements

2. **Risk:** Performance degradation (too slow for 10 seasons)
   - **Mitigation:** Batch operations, strategic indexes, benchmark each phase
   - **Fallback:** Make P2 systems optional (statistics archival)

3. **Risk:** Data corruption (atomicity failures)
   - **Mitigation:** Use TransactionContext for all multi-table operations
   - **Recovery:** Database backup before each offseason transition

4. **Risk:** Service dependency bugs (wrong execution order)
   - **Mitigation:** Explicit dependency graph in handler
   - **Testing:** Integration tests verify complete transition

---

## Conclusion

This architecture provides a **scalable, maintainable foundation** for implementing Milestone 1:

**Key Benefits:**
1. ✅ **Service-oriented:** Avoids monolithic controller bloat
2. ✅ **Testable:** Dependency injection enables isolated unit tests
3. ✅ **Atomic:** TransactionContext ensures data integrity
4. ✅ **Idempotent:** Safe to retry on failures
5. ✅ **Extensible:** Easy to add new systems in future milestones

**Estimated Effort:**
- **Phase 1 (P0):** ~350 LOC, 24-32 hours → 2-season simulation
- **Phase 2 (P1):** ~600 LOC, 28-36 hours → Dynamic rosters
- **Phase 3:** Integration testing → Production readiness
- **Phase 4 (P2):** ~500 LOC, 20-28 hours → Polish (optional)

**Total:** ~1,650 LOC, 3-4 weeks for production-ready implementation

**Next Steps:**
1. Review and approve architecture
2. Begin Phase 1 implementation (P0 systems)
3. Establish testing infrastructure
4. Execute 4-phase implementation plan

---

**References:**
- [01_audit_report.md](01_audit_report.md) - Gap analysis and current state
- [02_requirements.md](02_requirements.md) - Detailed system requirements
- [04_implementation_plan.md](04_implementation_plan.md) - Execution roadmap
- `/PHASE_3_COMPLETE.md` - Service extraction pattern proof-of-concept
- `/TRANSACTION_CONTEXT_IMPLEMENTATION.md` - Transaction safety implementation
