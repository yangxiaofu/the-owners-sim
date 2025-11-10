# Milestone 1 Implementation Plan: 4-Phase Roadmap

**Last Updated:** 2025-11-09
**Target Timeline:** 3-4 weeks (realistic), 3 weeks (aggressive), 6 weeks (conservative)
**Status:** 📋 Ready to Execute
**Estimated Total Effort:** ~1,650 LOC across 12 systems

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Phase 1: Core Foundations (Week 1)](#phase-1-core-foundations-week-1---critical-path)
3. [Phase 2: Player Lifecycle (Week 2)](#phase-2-player-lifecycle-week-2---high-priority)
4. [Phase 3: Integration & Testing (Week 3)](#phase-3-integration--testing-week-3---production-readiness)
5. [Phase 4: Advanced Features (Week 4)](#phase-4-advanced-features-week-4---optional-polish)
6. [Implementation Guidelines](#implementation-guidelines)
7. [Risk Mitigation Strategy](#risk-mitigation-strategy)
8. [Rollback Plan](#rollback-plan)
9. [Timeline Variations](#timeline-variations)
10. [Progress Tracking](#progress-tracking)

---

## Executive Summary

### Overview of 4-Phase Approach

This implementation plan delivers the **Complete Multi-Year Season Cycle** capability for "The Owners Sim" through a structured 4-phase approach spanning 3-4 weeks. The plan leverages existing production-ready infrastructure (Statistics Preservation, Season Year Tracking, Salary Cap System, Player Generation) while adding the critical year-over-year transition logic.

### Total Scope

| Category | Systems | LOC Estimate | Complexity | Priority |
|----------|---------|--------------|------------|----------|
| **Phase 1 (Week 1)** | 4 systems | 350 | Low-Medium | P0 (Must Have) |
| **Phase 2 (Week 2)** | 4 systems | 600 | Medium-High | P1 (Should Have) |
| **Phase 3 (Week 3)** | Integration & Testing | 200 | Medium | P0 (Must Have) |
| **Phase 4 (Week 4)** | 4 systems | 500 | Medium-High | P2 (Nice-to-Have) |
| **Total** | **12 systems** | **~1,650** | **Mixed** | **Mixed** |

**Note:** Infrastructure already exists for ~1,000+ LOC of supporting code (Statistics Preservation, Season Year Tracking, Salary Cap System, Draft Class Generator, etc.)

### Success Criteria Reference

See [01_audit_report.md](01_audit_report.md) Section "Success Criteria" for detailed acceptance criteria.

**Core Requirements:**
1. ✅ Can simulate 2 consecutive seasons without manual intervention
2. ✅ Can simulate 10 consecutive seasons (target: <30 minutes)
3. ✅ Season year increments correctly (2024 → 2025 → 2026...)
4. ✅ Salary cap rolls over with carryover and dead money
5. ✅ Contract years increment and expire correctly
6. ✅ Statistics preserved across seasons with proper season_year tagging
7. ✅ No year drift between components

### Risk Summary

| Risk Category | Likelihood | Impact | Mitigation |
|--------------|------------|--------|------------|
| Season Year Drift | Medium | Critical | Use existing SeasonYearSynchronizer |
| Database Transaction Failures | Low | High | Use TransactionContext (implemented) |
| Performance Degradation | Medium | Medium | Benchmark early, optimize hotspots |
| Circular Dependencies | Low | Medium | Service extraction pattern (Phase 3 proven) |

**Overall Risk Level:** 🟡 MEDIUM (well-mitigated with existing infrastructure)

---

## Phase 1: Core Foundations (Week 1) - CRITICAL PATH

**Goal:** Enable 2+ consecutive season simulation

**Priority:** P0 (Must Have)
**Estimated Effort:** 24-32 hours
**Estimated LOC:** ~350 lines (new code)

### Task 1.1: Season Year Increment Service

**Objective:** Implement season year increment logic to progress from 2024 → 2025 → 2026...

**File:** `src/season/services/season_year_service.py` (NEW)

**Method Signatures Needed:**
```python
class SeasonYearService:
    """Service for managing season year increments during offseason-to-preseason transition."""

    def __init__(
        self,
        year_synchronizer: SeasonYearSynchronizer,
        event_db: EventDatabaseAPI,
        logger: logging.Logger,
        dynasty_id: str
    ):
        """Initialize season year service with dependencies."""

    def increment_season_year(self) -> int:
        """
        Increment season year by 1 using SeasonYearSynchronizer.

        Returns:
            int: New season year after increment

        Raises:
            ValueError: If year synchronizer not available
            RuntimeError: If increment fails
        """

    def validate_year_consistency(self, expected_year: int) -> bool:
        """
        Validate that all systems have consistent season year.

        Args:
            expected_year: Expected season year after increment

        Returns:
            bool: True if all systems match expected_year
        """
```

**Implementation Details:**
1. Leverage existing `SeasonYearSynchronizer` (already implemented in Statistics Preservation Phase 1)
2. Call `year_synchronizer.increment_year()` method (if exists) or implement wrapper
3. Validate year consistency across controller, database, and events
4. Add comprehensive logging for debugging

**Test Requirements:**
- Unit test: `test_increment_year_updates_controller()`
- Unit test: `test_increment_year_updates_database()`
- Unit test: `test_validate_year_consistency_pass()`
- Unit test: `test_validate_year_consistency_fail()`
- Integration test: `test_year_increment_in_full_transition()`

**Acceptance Criteria:**
- ✅ Season year increments from 2024 → 2025
- ✅ Controller season_year property updated
- ✅ Database dynasty_state.season_year updated
- ✅ No drift between controller and database
- ✅ Auto-recovery guards still functional (Phase 5 protection)

**Estimated Time:** 4-6 hours

---

### Task 1.2: Salary Cap Year Rollover Service

**Objective:** Implement salary cap year rollover with carryover, dead money, and new cap limit

**File:** `src/salary_cap/cap_year_service.py` (NEW)

**Method Signatures Needed:**
```python
class CapYearRolloverService:
    """Service for rolling over salary cap state to new season."""

    def __init__(
        self,
        cap_calculator: CapCalculator,
        cap_database_api: CapDatabaseAPI,
        logger: logging.Logger,
        dynasty_id: str
    ):
        """Initialize cap year rollover service."""

    def rollover_to_new_season(
        self,
        current_year: int,
        new_year: int,
        new_cap_limit: int = None  # If None, auto-calculate from CBA rules
    ) -> Dict[str, Any]:
        """
        Roll over salary cap state from current season to new season.

        Args:
            current_year: Current season year
            new_year: New season year (typically current_year + 1)
            new_cap_limit: New season cap limit (default: auto-calculate)

        Returns:
            Dict with rollover summary:
                {
                    'new_cap_limit': int,
                    'teams_rolled_over': int,
                    'total_carryover': int,
                    'total_dead_money': int,
                    'roster_mode': str  # 'top_51' (offseason mode)
                }

        Raises:
            ValueError: If new_year != current_year + 1
        """

    def calculate_team_carryover(self, team_id: int, season_year: int) -> int:
        """Calculate cap space carryover for team (positive or negative)."""

    def switch_to_offseason_roster_mode(self, season_year: int) -> None:
        """Switch all teams to top-51 roster calculation mode."""

    def load_new_cap_limit(self, season_year: int) -> int:
        """Load or calculate new season cap limit from CBA rules."""
```

**Implementation Details:**
1. **Load New Cap Limit** (~20 LOC)
   - Query from `salary_cap_limits` table OR calculate from CBA rules
   - Default: Use 2024-2025 CBA escalator (~$255.4M for 2025)

2. **Calculate Carryover** (~50 LOC)
   - For each team: `carryover = cap_limit - cap_used`
   - Positive carryover = extra space for new season
   - Negative carryover = over cap (must cut players)
   - Update `team_cap` table with carryover amounts

3. **Dead Money Carryover** (~50 LOC)
   - Query all dead money from previous season
   - Apply proration to new season (signing bonus amortization)
   - Handle June 1 designations (split dead money over 2 years)

4. **Switch Roster Mode** (~20 LOC)
   - Update all teams to `top_51` calculation mode (offseason)
   - Will switch back to `53_man` at regular season start

5. **Database Updates** (~30 LOC)
   - Insert new `team_cap` rows for new season
   - Update `cap_space` with carryover amounts
   - Log all transactions

**Test Requirements:**
- Unit test: `test_rollover_loads_new_cap_limit()`
- Unit test: `test_rollover_calculates_carryover_positive()`
- Unit test: `test_rollover_calculates_carryover_negative()`
- Unit test: `test_rollover_carries_over_dead_money()`
- Unit test: `test_rollover_switches_to_top51_mode()`
- Integration test: `test_full_cap_rollover_all_32_teams()`

**Acceptance Criteria:**
- ✅ New cap limit loaded correctly for new season
- ✅ All 32 teams have cap state for new season
- ✅ Carryover calculated correctly (positive/negative)
- ✅ Dead money carries over with correct proration
- ✅ Roster mode set to `top_51` (offseason)
- ✅ No teams lost during transition

**Estimated Time:** 8-10 hours

---

### Task 1.3: Contract Year Increments Service

**Objective:** Increment contract years and handle expired contracts

**File:** `src/salary_cap/contract_year_service.py` (NEW)

**Method Signatures Needed:**
```python
class ContractYearService:
    """Service for incrementing contract years and handling expirations."""

    def __init__(
        self,
        contract_manager: ContractManager,
        cap_database_api: CapDatabaseAPI,
        logger: logging.Logger,
        dynasty_id: str
    ):
        """Initialize contract year service."""

    def increment_all_contract_years(self, season_year: int) -> Dict[str, int]:
        """
        Increment year for all active contracts.

        Args:
            season_year: Season year being transitioned to

        Returns:
            Dict with summary:
                {
                    'contracts_incremented': int,
                    'contracts_expired': int,
                    'contracts_archived': int,
                    'new_ufas': int,
                    'new_rfas': int
                }
        """

    def detect_expired_contracts(self, season_year: int) -> List[int]:
        """
        Find all contracts expiring after previous season.

        Returns:
            List of contract IDs that expired
        """

    def archive_expired_contracts(self, contract_ids: List[int]) -> None:
        """Move expired contracts to contract_history table."""

    def update_player_free_agency_status(self, contract_ids: List[int]) -> Dict[str, List[int]]:
        """
        Update free agency status for players with expired contracts.

        Returns:
            Dict mapping FA type to player IDs:
                {
                    'UFA': [player_ids...],
                    'RFA': [player_ids...],
                    'ERFA': [player_ids...]
                }
        """
```

**Implementation Details:**
1. **Increment Contract Years** (~50 LOC)
   - Query all active contracts (`contracts` table)
   - Increment `current_year` column by 1
   - Detect contracts where `current_year > total_years` (expired)

2. **Archive Expired Contracts** (~30 LOC)
   - Move expired contracts to `contract_history` table
   - Preserve all contract details for historical tracking
   - Delete from `contracts` table

3. **Update Free Agency Status** (~50 LOC)
   - Determine FA type based on years of service:
     - 0-2 years → ERFA (Exclusive Rights FA)
     - 3 years → RFA (Restricted FA)
     - 4+ years → UFA (Unrestricted FA)
   - Update `players` table with `contract_status = 'FA'`
   - Update `free_agents` table with FA type and contract year

4. **Database Transactions** (~20 LOC)
   - Use `TransactionContext` for atomic operations
   - Rollback all changes if any step fails
   - Log all contract changes for audit trail

**Test Requirements:**
- Unit test: `test_increment_contract_years_active_contracts()`
- Unit test: `test_detect_expired_contracts()`
- Unit test: `test_archive_expired_contracts_to_history()`
- Unit test: `test_update_fa_status_ufa()`
- Unit test: `test_update_fa_status_rfa()`
- Unit test: `test_update_fa_status_erfa()`
- Integration test: `test_full_contract_year_increment_cycle()`

**Acceptance Criteria:**
- ✅ All active contracts have `current_year` incremented by 1
- ✅ Expired contracts moved to `contract_history` table
- ✅ Players with expired contracts marked as free agents
- ✅ FA type correctly determined (UFA/RFA/ERFA)
- ✅ No data loss during archival
- ✅ Atomic transaction (all-or-nothing)

**Estimated Time:** 6-8 hours

---

### Task 1.4: Draft Class Timing Fix

**Objective:** Move draft class generation from season start to offseason end

**File:** `src/offseason/draft_manager.py` (MODIFY)

**Current Behavior (WRONG):**
```python
# SeasonCycleController.__init__ (Line 392)
self._generate_draft_class_if_needed()  # ← Runs at SEASON START
```

**Target Behavior (CORRECT):**
```python
# OffseasonToPreseasonHandler.execute()
self._generate_draft_class_for_upcoming_season(self._new_season_year + 1)
```

**Changes Needed:**
1. **Remove from SeasonCycleController** (~10 LOC deleted)
   - Delete `_generate_draft_class_if_needed()` call from `__init__`
   - Keep method for backward compatibility (deprecated)

2. **Add to OffseasonToPreseasonHandler** (~40 LOC added)
   ```python
   def _generate_draft_class(self, draft_year: int) -> None:
       """
       Generate draft class for upcoming season.

       Args:
           draft_year: Year of the upcoming draft (new_season_year + 1)
       """
       if self._event_db:
           existing_prospects = self._event_db.draft_get_prospects_count(
               dynasty_id=self._dynasty_id,
               draft_year=draft_year
           )

           if existing_prospects > 0:
               self._log(f"Draft class already exists for {draft_year} ({existing_prospects} prospects)")
               return

       # Generate new draft class (224 prospects)
       from player_generation.generators.draft_class_generator import DraftClassGenerator

       generator = DraftClassGenerator(dynasty_id=self._dynasty_id)
       prospects = generator.generate_draft_class(
           draft_year=draft_year,
           enable_persistence=True,
           database_path=self._database_path
       )

       self._log(f"Generated draft class for {draft_year}: {len(prospects)} prospects")
   ```

3. **Integration with Handler** (~10 LOC)
   - Call in `execute()` method after standings reset
   - Pass `self._new_season_year + 1` as draft_year (generate for NEXT year's draft)

**Test Requirements:**
- Unit test: `test_draft_class_not_generated_at_season_start()`
- Unit test: `test_draft_class_generated_during_offseason_transition()`
- Unit test: `test_draft_class_year_is_next_season_plus_one()`
- Integration test: `test_draft_class_available_for_scouting_in_new_season()`

**Acceptance Criteria:**
- ✅ Draft class NOT generated at season start
- ✅ Draft class generated during offseason-to-preseason transition
- ✅ Draft class year is `new_season_year + 1` (e.g., 2025 season → 2026 draft)
- ✅ 224 prospects generated (7 rounds × 32 picks)
- ✅ Prospects available for scouting during new season

**Estimated Time:** 3-4 hours

---

### Task 1.5: Enhanced OffseasonToPreseasonHandler

**Objective:** Orchestrate all Phase 1 services in handler

**File:** `src/season/phase_transition/transition_handlers/offseason_to_preseason.py` (MODIFY)

**Changes Needed:**

1. **Add Service Dependencies** (~20 LOC)
   ```python
   def __init__(self, ..., year_service=None, cap_service=None, contract_service=None):
       """Add new service dependencies to constructor."""
       self._year_service = year_service
       self._cap_service = cap_service
       self._contract_service = contract_service
   ```

2. **Enhanced execute() Method** (~80 LOC)
   ```python
   def execute(self, transition: PhaseTransition) -> Dict[str, Any]:
       """Execute offseason-to-preseason transition with full initialization."""

       self._log("=" * 80)
       self._log(f"OFFSEASON → PRESEASON TRANSITION (Season {self._new_season_year})")
       self._log("=" * 80)

       # Step 1: Increment season year (NEW)
       if self._year_service:
           self._log("\n[1/7] Incrementing season year...")
           new_year = self._year_service.increment_season_year()
           assert new_year == self._new_season_year, "Year increment mismatch!"

       # Step 2: Salary cap year rollover (NEW)
       if self._cap_service:
           self._log("\n[2/7] Rolling over salary cap to new season...")
           cap_summary = self._cap_service.rollover_to_new_season(
               current_year=self._new_season_year - 1,
               new_year=self._new_season_year
           )
           self._log(f"  - New cap limit: ${cap_summary['new_cap_limit']:,}")
           self._log(f"  - Teams rolled over: {cap_summary['teams_rolled_over']}/32")

       # Step 3: Contract year increments (NEW)
       if self._contract_service:
           self._log("\n[3/7] Incrementing contract years...")
           contract_summary = self._contract_service.increment_all_contract_years(
               season_year=self._new_season_year
           )
           self._log(f"  - Contracts incremented: {contract_summary['contracts_incremented']}")
           self._log(f"  - Contracts expired: {contract_summary['contracts_expired']}")
           self._log(f"  - New UFAs: {contract_summary['new_ufas']}")

       # Step 4: Generate draft class for next season (FIXED TIMING)
       self._log("\n[4/7] Generating draft class for upcoming draft...")
       self._generate_draft_class(draft_year=self._new_season_year + 1)

       # Step 5: Validate schedule exists (EXISTING)
       self._log("\n[5/7] Validating game schedule...")
       self._validate_games_exist(effective_year=self._new_season_year)

       # Step 6: Reset standings (EXISTING)
       self._log("\n[6/7] Resetting standings...")
       self._reset_standings(self._new_season_year)

       # Step 7: Update database phase (EXISTING)
       self._log("\n[7/7] Updating database phase to PRESEASON...")
       self._update_database_phase("preseason", self._new_season_year)

       self._log("\n" + "=" * 80)
       self._log("TRANSITION COMPLETE: Ready for preseason simulation")
       self._log("=" * 80)

       return {
           'success': True,
           'new_season_year': self._new_season_year,
           'transition_type': 'offseason_to_preseason'
       }
   ```

3. **Error Handling & Rollback** (~30 LOC)
   - Wrap entire execute() in try-except
   - Track which steps completed
   - Provide rollback hints on failure
   - Log detailed error information

**Test Requirements:**
- Integration test: `test_handler_executes_all_7_steps()`
- Integration test: `test_handler_increments_year_correctly()`
- Integration test: `test_handler_rolls_over_cap()`
- Integration test: `test_handler_increments_contracts()`
- Integration test: `test_handler_generates_draft_class()`
- Integration test: `test_handler_rollback_on_failure()`

**Acceptance Criteria:**
- ✅ All 7 initialization steps execute in correct order
- ✅ Detailed logging shows progress
- ✅ Season year incremented before other operations
- ✅ Cap rollover completes for all 32 teams
- ✅ Contracts incremented and expired handled
- ✅ Draft class generated for next season
- ✅ Standings reset and schedule validated
- ✅ Database phase updated to PRESEASON

**Estimated Time:** 6-8 hours

---

### Phase 1 Deliverables

**New Files Created:**
1. `src/season/services/season_year_service.py` (~100 LOC)
2. `src/salary_cap/cap_year_service.py` (~150 LOC)
3. `src/salary_cap/contract_year_service.py` (~100 LOC)
4. `tests/season/test_season_year_service.py` (~150 LOC)
5. `tests/salary_cap/test_cap_year_service.py` (~200 LOC)
6. `tests/salary_cap/test_contract_year_service.py` (~150 LOC)

**Modified Files:**
1. `src/season/phase_transition/transition_handlers/offseason_to_preseason.py` (+100 LOC)
2. `src/season/season_cycle_controller.py` (-10 LOC, cleanup draft class call)

**Total New Code:** ~950 LOC (includes tests)

**Test Coverage:** 15+ unit tests, 5+ integration tests

**Integration Test:** 2-Season Simulation
```python
def test_two_consecutive_seasons():
    """Test that can simulate Season 1 (2024) → Offseason → Season 2 (2025)."""
    controller = SeasonCycleController(dynasty_id="test", season_year=2024)

    # Season 1
    controller.simulate_full_season()  # Preseason → Regular → Playoffs → Offseason
    assert controller.season_year == 2024

    # Transition (should happen automatically in simulate_full_season)
    # Or manually: controller.transition_to_next_season()

    # Season 2
    assert controller.season_year == 2025
    assert controller.phase == "PRESEASON"

    # Verify cap rolled over
    team_cap = controller.db.cap_get_team_cap(team_id=1, season_year=2025)
    assert team_cap is not None

    # Verify contracts incremented
    contracts = controller.db.contract_get_active_contracts(team_id=1, season_year=2025)
    assert len(contracts) > 0
```

**Phase 1 Success Criteria:**
- ✅ Can simulate Season 1 (2024) → Offseason → Season 2 (2025)
- ✅ Season year increments correctly (2024 → 2025)
- ✅ Salary cap carries over with correct values
- ✅ Contracts expire and year increments work
- ✅ Draft class generated at correct time (offseason end, not season start)
- ✅ No year drift between controller and database
- ✅ All 32 teams transition successfully

**Estimated Total Time for Phase 1:** 24-32 hours (Week 1)

---

## Phase 2: Player Lifecycle (Week 2) - HIGH PRIORITY

**Goal:** Dynamic rosters with realistic player turnover

**Priority:** P1 (Should Have)
**Estimated Effort:** 28-36 hours
**Estimated LOC:** ~600 lines (new code)

### Task 2.1: Player Retirement Service

**Objective:** Implement realistic player retirement based on age, performance, and injury history

**File:** `src/player_management/player_retirement_service.py` (NEW)

**Method Signatures Needed:**
```python
class PlayerRetirementService:
    """Service for managing player retirements at season end."""

    def __init__(
        self,
        db: UnifiedDatabaseAPI,
        cap_calculator: CapCalculator,
        logger: logging.Logger,
        dynasty_id: str
    ):
        """Initialize retirement service."""

    def evaluate_retirements(self, season_year: int) -> List[int]:
        """
        Evaluate all players for retirement eligibility.

        Returns:
            List of player IDs who are retiring

        Retirement Criteria:
        - Age 38+: 50% retirement chance per year
        - Age 35-37: 20% if overall < 70, 5% otherwise
        - Age 32-34: 5% if overall < 65
        - Injury History: +10% if 2+ season-ending injuries
        - Super Bowl Winner: -10% retirement chance (play one more year)
        """

    def process_retirements(
        self,
        player_ids: List[int],
        season_year: int
    ) -> Dict[str, Any]:
        """
        Execute retirements for players.

        Returns:
            Dict with summary:
                {
                    'players_retired': int,
                    'dead_money_total': int,
                    'cap_space_freed': int,
                    'roster_spots_freed': int
                }

        Side Effects:
        - Moves players to retired_players table
        - Calculates dead money (signing bonus acceleration)
        - Updates team cap space
        - Removes from team rosters
        """

    def calculate_retirement_dead_money(
        self,
        player_id: int,
        season_year: int
    ) -> int:
        """
        Calculate dead money from player retirement.

        Retirement triggers signing bonus acceleration:
        - All remaining signing bonus cap hits apply immediately
        - Team can designate as June 1 cut (split over 2 years)
        """
```

**Implementation Details:**

1. **Retirement Evaluation Logic** (~100 LOC)
   - Query all active players (exclude rookies, players in first 3 years)
   - Calculate retirement probability based on:
     - Age (primary factor)
     - Overall rating (performance decline)
     - Injury history (from `player_injuries` table)
     - Recent success (Super Bowl winner bonus)
   - Use randomization with weighted probabilities
   - Position-specific adjustments:
     - QB, K, P: +5 years career length
     - RB, EDGE: -2 years career length

2. **Dead Money Calculation** (~50 LOC)
   - Query player's active contract
   - Calculate remaining signing bonus proration
   - Apply acceleration rules (all hits in current year OR June 1 split)
   - Update `dead_money` table with retirement entries

3. **Player Archival** (~30 LOC)
   - Move player record to `retired_players` table
   - Preserve complete player history
   - Update `career_stats` aggregation
   - Remove from `players` table

4. **Team Updates** (~20 LOC)
   - Remove from `team_rosters` table
   - Update depth charts (remove retired player)
   - Recalculate team cap space
   - Log retirement transactions

**Test Requirements:**
- Unit test: `test_retirement_age_38_high_probability()`
- Unit test: `test_retirement_age_32_low_overall_moderate_probability()`
- Unit test: `test_retirement_injury_history_increases_chance()`
- Unit test: `test_retirement_super_bowl_winner_bonus()`
- Unit test: `test_retirement_dead_money_calculation()`
- Unit test: `test_retirement_removes_from_roster()`
- Integration test: `test_process_retirements_full_league()`

**Acceptance Criteria:**
- ✅ Realistic retirement rates (5-15 players per year league-wide)
- ✅ Age-based probabilities work correctly
- ✅ Injury history affects retirement chance
- ✅ Dead money calculated correctly (signing bonus acceleration)
- ✅ Players moved to `retired_players` table
- ✅ Team rosters and cap space updated
- ✅ No active contracts left for retired players

**Estimated Time:** 10-12 hours

---

### Task 2.2: Player Aging Service

**Objective:** Age all players and apply attribute decay

**File:** `src/player_management/player_aging_service.py` (NEW)

**Method Signatures Needed:**
```python
class PlayerAgingService:
    """Service for aging players and applying attribute decay."""

    def __init__(
        self,
        db: UnifiedDatabaseAPI,
        logger: logging.Logger,
        dynasty_id: str
    ):
        """Initialize aging service."""

    def age_all_players(self, season_year: int) -> Dict[str, int]:
        """
        Increment years_pro and apply attribute decay for all players.

        Returns:
            Dict with summary:
                {
                    'players_aged': int,
                    'players_in_prime': int,  # Age 26-29
                    'players_declining': int,  # Age 30+
                    'avg_attribute_decay': float
                }
        """

    def calculate_attribute_decay(
        self,
        player: Dict[str, Any],
        current_age: int
    ) -> Dict[str, int]:
        """
        Calculate attribute changes for player based on age.

        Returns:
            Dict mapping attribute name to decay amount (negative for decline)

        Decay Rules:
        - Age 18-25: +1-3% improvement (young player development)
        - Age 26-29: Peak (no decay)
        - Age 30-32: -1-2% decay (gradual decline)
        - Age 33-35: -3-5% decay (faster decline)
        - Age 36+: -5-10% decay (steep decline)

        Physical Attributes Decay Faster:
        - Speed, Acceleration, Agility: 2x decay rate
        - Strength, Stamina: 1.5x decay rate

        Mental Attributes Improve with Age:
        - Awareness, Play Recognition: +1-2% until age 35
        """

    def update_player_potential(self, player_id: int, current_age: int) -> int:
        """
        Update player potential rating based on age.

        Returns:
            New potential rating
        """
```

**Implementation Details:**

1. **Years Pro Increment** (~30 LOC)
   - Query all active players
   - Increment `years_pro` by 1
   - Calculate age from `birth_year` (if exists) or use proxy
   - Update `players` table

2. **Attribute Decay Calculation** (~80 LOC)
   - Load player attributes (speed, strength, awareness, etc.)
   - Apply age-based decay curves:
     - Linear decay for physical attributes (speed, acceleration)
     - Slower decay for mental attributes (awareness, route running)
     - Position-specific decay rates (QB mental attributes decay slower)
   - Randomize decay slightly (±1-2 points) for realism
   - Never decay below minimum thresholds (e.g., speed never < 40)

3. **Potential Rating Updates** (~20 LOC)
   - Young players (age < 25): Potential can still increase
   - Prime players (age 26-29): Potential stable
   - Aging players (age 30+): Potential decreases 2-5 points per year
   - Update `potential` column in `players` table

4. **Database Batch Updates** (~20 LOC)
   - Use batched UPDATE statements for performance
   - Process in chunks of 100 players to avoid memory issues
   - Use `TransactionContext` for atomic updates

**Test Requirements:**
- Unit test: `test_increment_years_pro_all_players()`
- Unit test: `test_attribute_decay_age_30_moderate()`
- Unit test: `test_attribute_decay_age_36_steep()`
- Unit test: `test_physical_attributes_decay_faster()`
- Unit test: `test_mental_attributes_improve_with_age()`
- Unit test: `test_potential_decreases_for_aging_players()`
- Integration test: `test_age_all_players_full_league()`

**Acceptance Criteria:**
- ✅ All active players have `years_pro` incremented by 1
- ✅ Physical attributes decay for players 30+
- ✅ Mental attributes improve slightly for players < 35
- ✅ Potential ratings decrease for aging players
- ✅ Decay is realistic (no players dropping 20+ overall in 1 year)
- ✅ Batch updates efficient (<5 seconds for ~1,600 players)

**Estimated Time:** 8-10 hours

---

### Task 2.3: Free Agent Pool Updates

**Objective:** Update free agent pool with players whose contracts expired

**File:** `src/player_management/free_agent_pool_service.py` (NEW)

**Method Signatures Needed:**
```python
class FreeAgentPoolService:
    """Service for managing free agent pool updates."""

    def __init__(
        self,
        db: UnifiedDatabaseAPI,
        logger: logging.Logger,
        dynasty_id: str
    ):
        """Initialize FA pool service."""

    def update_free_agent_pool(self, season_year: int) -> Dict[str, int]:
        """
        Update free agent pool with players from expired contracts.

        Returns:
            Dict with summary:
                {
                    'new_ufas': int,
                    'new_rfas': int,
                    'new_erfas': int,
                    'total_free_agents': int
                }

        Side Effects:
        - Removes unsigned players from team rosters
        - Adds players to free_agents table
        - Categorizes by FA type (UFA, RFA, ERFA)
        - Updates player contract status
        """

    def categorize_free_agent_type(
        self,
        player_id: int,
        years_of_service: int
    ) -> str:
        """
        Determine FA type based on years of service.

        Returns:
            'UFA', 'RFA', or 'ERFA'

        Rules:
        - 0-2 years: ERFA (Exclusive Rights FA)
        - 3 years: RFA (Restricted FA)
        - 4+ years: UFA (Unrestricted FA)
        """

    def clear_unsigned_players_from_rosters(self, season_year: int) -> int:
        """
        Remove all unsigned free agents from team rosters.

        Returns:
            Number of players removed from rosters
        """
```

**Implementation Details:**

1. **Query Unsigned Players** (~20 LOC)
   - Find players with expired contracts (from Task 1.3)
   - Filter for players not yet signed to new contracts
   - Query `contract_status = 'expired'` or similar flag

2. **Categorize FA Type** (~30 LOC)
   - Calculate years of service from `years_pro` field
   - Apply NFL FA rules (ERFA/RFA/UFA)
   - Handle edge cases (veteran minimum players, practice squad)

3. **Update Free Agents Table** (~30 LOC)
   - Insert records into `free_agents` table
   - Include: player_id, fa_type, contract_year, previous_team
   - Set initial market value (from MarketValueCalculator if exists)

4. **Remove from Rosters** (~20 LOC)
   - Delete from `team_rosters` table
   - Update depth charts (remove unsigned players)
   - Log roster changes

**Test Requirements:**
- Unit test: `test_categorize_erfa_0_2_years_service()`
- Unit test: `test_categorize_rfa_3_years_service()`
- Unit test: `test_categorize_ufa_4_plus_years_service()`
- Unit test: `test_update_fa_pool_adds_to_table()`
- Unit test: `test_clear_unsigned_removes_from_rosters()`
- Integration test: `test_full_fa_pool_update_cycle()`

**Acceptance Criteria:**
- ✅ All players with expired contracts added to FA pool
- ✅ FA type correctly categorized (ERFA/RFA/UFA)
- ✅ Players removed from team rosters
- ✅ `free_agents` table populated with all eligible players
- ✅ No active contracts for free agents

**Estimated Time:** 5-6 hours

---

### Task 2.4: Rookie Contract Generation

**Objective:** Generate rookie contracts for drafted players

**File:** `src/salary_cap/rookie_contract_service.py` (NEW)

**Method Signatures Needed:**
```python
class RookieContractService:
    """Service for generating rookie contracts based on draft position."""

    def __init__(
        self,
        cap_calculator: CapCalculator,
        cap_database_api: CapDatabaseAPI,
        logger: logging.Logger,
        dynasty_id: str
    ):
        """Initialize rookie contract service."""

    def generate_rookie_contracts_for_draft_class(
        self,
        draft_year: int,
        season_year: int
    ) -> Dict[str, int]:
        """
        Generate contracts for all drafted players.

        Args:
            draft_year: Year of the draft
            season_year: Season year contracts start

        Returns:
            Dict with summary:
                {
                    'contracts_generated': int,
                    'total_cap_hit': int,
                    'avg_contract_value': int
                }

        Side Effects:
        - Creates contract records in contracts table
        - Links players to teams (team_rosters)
        - Updates team cap space
        """

    def calculate_rookie_contract_value(
        self,
        draft_position: int,
        draft_round: int
    ) -> Dict[str, int]:
        """
        Calculate rookie contract value based on draft position.

        Returns:
            Dict with contract details:
                {
                    'total_value': int,
                    'signing_bonus': int,
                    'year_1_salary': int,
                    'year_2_salary': int,
                    'year_3_salary': int,
                    'year_4_salary': int,
                    'year_5_salary': int,  # Round 1 only
                    'total_years': int,
                    'cap_hit_year_1': int
                }

        Uses 2024-2025 Rookie Wage Scale:
        - Round 1: 4 years + 5th year option (~$2M-$35M total)
        - Rounds 2-7: 4 years (~$500K-$5M total)
        """
```

**Implementation Details:**

1. **Load Rookie Wage Scale** (~30 LOC)
   - Use 2024-2025 NFL rookie wage scale
   - Store in JSON config file or database table
   - Index by draft position (1-224)

2. **Generate Contracts** (~80 LOC)
   - Query all drafted players for draft_year
   - Calculate contract value for each player
   - Apply signing bonus proration (spread over contract years)
   - Generate year-by-year salary structure
   - Insert into `contracts` table

3. **Link to Teams** (~20 LOC)
   - Update `players.team_id` to drafting team
   - Add to `team_rosters` table
   - Update depth charts (add rookies at bottom)

4. **Cap Space Updates** (~20 LOC)
   - Calculate first-year cap hit (signing bonus + year 1 salary)
   - Update team cap space
   - Validate teams don't exceed cap (rookies are guaranteed)

**Test Requirements:**
- Unit test: `test_calculate_rookie_value_round_1_pick_1()`
- Unit test: `test_calculate_rookie_value_round_1_pick_32()`
- Unit test: `test_calculate_rookie_value_round_7_pick_224()`
- Unit test: `test_generate_contracts_all_224_players()`
- Unit test: `test_rookie_contracts_update_cap_space()`
- Integration test: `test_full_rookie_contract_generation_cycle()`

**Acceptance Criteria:**
- ✅ All 224 drafted players have contracts generated
- ✅ Contract values match NFL rookie wage scale
- ✅ Round 1 picks have 5th year option
- ✅ Rounds 2-7 have 4-year contracts
- ✅ Signing bonus prorated correctly
- ✅ Teams' cap space updated correctly
- ✅ Players linked to teams and added to rosters

**Estimated Time:** 8-10 hours

---

### Phase 2 Deliverables

**New Files Created:**
1. `src/player_management/player_retirement_service.py` (~200 LOC)
2. `src/player_management/player_aging_service.py` (~150 LOC)
3. `src/player_management/free_agent_pool_service.py` (~100 LOC)
4. `src/salary_cap/rookie_contract_service.py` (~150 LOC)
5. `tests/player_management/test_player_retirement_service.py` (~250 LOC)
6. `tests/player_management/test_player_aging_service.py` (~200 LOC)
7. `tests/player_management/test_free_agent_pool_service.py` (~150 LOC)
8. `tests/salary_cap/test_rookie_contract_service.py` (~200 LOC)

**Modified Files:**
1. `src/season/phase_transition/transition_handlers/offseason_to_preseason.py` (+50 LOC, integrate Phase 2 services)

**Total New Code:** ~1,450 LOC (includes tests)

**Test Coverage:** 20+ unit tests, 5+ integration tests

**Integration with Handler:**
```python
# Add to OffseasonToPreseasonHandler.execute()
# Step 3.5: Process player retirements
if self._retirement_service:
    self._log("\n[3.5/9] Processing player retirements...")
    retirement_ids = self._retirement_service.evaluate_retirements(self._new_season_year)
    retirement_summary = self._retirement_service.process_retirements(
        retirement_ids, self._new_season_year
    )
    self._log(f"  - Players retired: {retirement_summary['players_retired']}")

# Step 3.6: Age all players
if self._aging_service:
    self._log("\n[3.6/9] Aging all players...")
    aging_summary = self._aging_service.age_all_players(self._new_season_year)
    self._log(f"  - Players aged: {aging_summary['players_aged']}")

# Step 3.7: Update FA pool
if self._fa_pool_service:
    self._log("\n[3.7/9] Updating free agent pool...")
    fa_summary = self._fa_pool_service.update_free_agent_pool(self._new_season_year)
    self._log(f"  - New UFAs: {fa_summary['new_ufas']}")
```

**Phase 2 Success Criteria:**
- ✅ Realistic player retirements (5-15 per year)
- ✅ All players aged with attribute decay
- ✅ Free agent pool updated with unsigned players
- ✅ Rookie contracts generated for drafted players (if draft happened)
- ✅ Dynamic rosters with realistic player turnover
- ✅ Team cap space remains valid after all operations

**Estimated Total Time for Phase 2:** 28-36 hours (Week 2)

---

## Phase 3: Integration & Testing (Week 3) - PRODUCTION READINESS

**Goal:** Comprehensive validation and 10-season test

**Priority:** P0 (Must Have)
**Estimated Effort:** 24-32 hours
**Estimated LOC:** ~200 lines (test code)

### Task 3.1: 2-Season Integration Test

**Objective:** Validate that 2 consecutive seasons can be simulated

**File:** `tests/integration/test_two_season_simulation.py` (NEW)

**Test Scenarios:**
1. **Basic 2-Season Cycle** (~50 LOC)
   ```python
   def test_two_consecutive_seasons_full_cycle():
       """Test Season 1 (2024) → Offseason → Season 2 (2025) → Offseason."""
       controller = SeasonCycleController(dynasty_id="test_2season", season_year=2024)

       # Season 1: 2024
       controller.simulate_full_season()  # Preseason → Regular → Playoffs → Offseason
       assert controller.season_year == 2024
       assert controller.phase == "OFFSEASON"

       # Verify season 1 statistics persisted
       stats_2024 = controller.db.stats_get_season_leaders(season_year=2024, stat='passing_yards')
       assert len(stats_2024) > 0

       # Transition to Season 2
       controller.advance_to_next_season()
       assert controller.season_year == 2025
       assert controller.phase == "PRESEASON"

       # Verify cap rolled over
       for team_id in range(1, 33):
           team_cap = controller.db.cap_get_team_cap(team_id=team_id, season_year=2025)
           assert team_cap is not None
           assert team_cap['cap_limit'] > 0

       # Verify contracts incremented
       total_contracts = 0
       for team_id in range(1, 33):
           contracts = controller.db.contract_get_active_contracts(team_id=team_id, season_year=2025)
           total_contracts += len(contracts)
       assert total_contracts > 1000  # Should have ~1,600 active contracts

       # Season 2: 2025
       controller.simulate_full_season()
       assert controller.season_year == 2025

       # Verify season 2 statistics separate from season 1
       stats_2025 = controller.db.stats_get_season_leaders(season_year=2025, stat='passing_yards')
       assert len(stats_2025) > 0
       assert stats_2024 != stats_2025  # Different leaders
   ```

2. **Year Consistency Validation** (~30 LOC)
   ```python
   def test_season_year_consistency_across_systems():
       """Verify season_year is consistent across all systems."""
       controller = SeasonCycleController(dynasty_id="test_consistency", season_year=2024)
       controller.simulate_full_season()
       controller.advance_to_next_season()

       # Verify controller
       assert controller.season_year == 2025

       # Verify database dynasty_state
       dynasty_state = controller.db.dynasty_get_state(controller.dynasty_id)
       assert dynasty_state['season_year'] == 2025

       # Verify standings
       standings = controller.db.standings_get_all(season_year=2025)
       assert len(standings) == 32

       # Verify events (should have games scheduled for 2025)
       games_2025 = controller.event_db.events_count_games_for_season(
           dynasty_id=controller.dynasty_id,
           season_year=2025
       )
       assert games_2025 == 320  # 48 preseason + 272 regular
   ```

3. **Contract Expiration Test** (~40 LOC)
   ```python
   def test_contract_expiration_creates_free_agents():
       """Verify contracts expire and create free agents."""
       # Create test contract expiring after Season 1
       # Simulate Season 1
       # Verify contract archived
       # Verify player added to FA pool
   ```

**Test Requirements:**
- Test passes without errors
- Completes in <5 minutes
- All assertions pass
- Database state valid after both seasons

**Acceptance Criteria:**
- ✅ Can simulate 2 full seasons consecutively
- ✅ Season year increments correctly
- ✅ Statistics preserved separately for each season
- ✅ Cap state valid for both seasons
- ✅ Contracts handled correctly
- ✅ No year drift detected

**Estimated Time:** 6-8 hours

---

### Task 3.2: 10-Season Integration Test

**Objective:** Validate that 10 consecutive seasons can be simulated

**File:** `tests/integration/test_ten_season_simulation.py` (NEW)

**Test Implementation:**
```python
@pytest.mark.slow
@pytest.mark.timeout(1800)  # 30 minute timeout
def test_ten_consecutive_seasons():
    """
    Test that can simulate 10 consecutive seasons (2024-2033).

    This is the ultimate validation test for Milestone 1.
    """
    controller = SeasonCycleController(
        dynasty_id="test_10seasons",
        season_year=2024,
        enable_persistence=True
    )

    season_summary = {}

    for year in range(2024, 2034):
        print(f"\n{'='*80}")
        print(f"SIMULATING SEASON {year}")
        print(f"{'='*80}")

        # Simulate full season
        start_time = time.time()
        result = controller.simulate_full_season()
        elapsed = time.time() - start_time

        # Verify season year
        assert controller.season_year == year, f"Expected {year}, got {controller.season_year}"

        # Collect statistics
        stats = controller.db.stats_get_season_leaders(season_year=year, stat='passing_yards', limit=10)
        super_bowl_winner = controller.db.playoff_get_champion(dynasty_id=controller.dynasty_id, season_year=year)

        season_summary[year] = {
            'elapsed_time': elapsed,
            'super_bowl_winner': super_bowl_winner,
            'passing_leader': stats[0]['player_name'] if stats else None,
            'passing_yards': stats[0]['passing_yards'] if stats else 0
        }

        # Advance to next season
        if year < 2033:
            controller.advance_to_next_season()

    # Print summary
    print(f"\n{'='*80}")
    print("10-SEASON SIMULATION COMPLETE")
    print(f"{'='*80}")

    total_time = sum(s['elapsed_time'] for s in season_summary.values())
    avg_time = total_time / 10

    print(f"\nTotal Time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"Average per Season: {avg_time:.1f}s")

    for year, summary in season_summary.items():
        print(f"\n{year}: {summary['super_bowl_winner']} ({summary['elapsed_time']:.1f}s)")
        print(f"  Passing Leader: {summary['passing_leader']} ({summary['passing_yards']} yards)")

    # Performance validation
    assert total_time < 1800, f"10 seasons took {total_time}s (target: <1800s / 30 min)"
    assert avg_time < 180, f"Average {avg_time}s per season (target: <180s / 3 min)"

    # Data validation
    assert len(season_summary) == 10
    for year in range(2024, 2034):
        assert season_summary[year]['super_bowl_winner'] is not None
        assert season_summary[year]['passing_yards'] > 0
```

**Validation Checks:**
1. All 10 seasons complete without errors
2. Total time < 30 minutes (target)
3. Average time per season < 3 minutes
4. Each season has valid Super Bowl winner
5. Each season has valid statistics
6. No memory leaks (monitor memory usage)

**Acceptance Criteria:**
- ✅ Simulates 10 consecutive seasons (2024-2033)
- ✅ Completes in <30 minutes (realistic target)
- ✅ All seasons have valid statistics
- ✅ All seasons have Super Bowl winners
- ✅ No crashes or errors
- ✅ No year drift across 10 seasons

**Estimated Time:** 8-10 hours (includes debugging and optimization)

---

### Task 3.3: Edge Case Testing

**Objective:** Test edge cases and error scenarios

**File:** `tests/integration/test_season_transition_edge_cases.py` (NEW)

**Edge Cases to Test:**

1. **All Teams Over Cap** (~20 LOC)
   - Setup: Set all teams to negative cap space
   - Transition to new season
   - Verify: Handler completes (may require cap enforcement elsewhere)

2. **No Draft Class Generated** (~20 LOC)
   - Skip draft class generation step
   - Verify: Transition still completes
   - Verify: Warning logged

3. **Mid-Transition Database Failure** (~30 LOC)
   - Inject database error during transition
   - Verify: Rollback occurs
   - Verify: No partial state corruption

4. **Leap Year Date Calculations** (~20 LOC)
   - Test season starting in leap year
   - Verify: Schedule dates calculated correctly

5. **Contract Expiration Edge Cases** (~30 LOC)
   - Player with multi-year signing bonus retires
   - Dead money calculated correctly
   - June 1 designation splits across years

**Acceptance Criteria:**
- ✅ All edge cases handled gracefully
- ✅ No crashes or data corruption
- ✅ Appropriate errors logged
- ✅ Rollback works when expected

**Estimated Time:** 6-8 hours

---

### Task 3.4: Performance Benchmarking

**Objective:** Identify and optimize performance bottlenecks

**File:** `tests/performance/test_season_cycle_performance.py` (NEW)

**Benchmarks to Capture:**

1. **Phase Transition Performance** (~30 LOC)
   ```python
   def test_offseason_to_preseason_transition_performance():
       """Benchmark offseason-to-preseason transition."""
       controller = SeasonCycleController(dynasty_id="perf_test", season_year=2024)
       controller.simulate_full_season()  # Get to offseason

       start = time.time()
       controller.advance_to_next_season()
       elapsed = time.time() - start

       print(f"Transition time: {elapsed:.3f}s")
       assert elapsed < 5.0, f"Transition took {elapsed}s (target: <5s)"
   ```

2. **Service Operation Benchmarks** (~40 LOC)
   - Season year increment: <0.1s
   - Cap rollover (32 teams): <1s
   - Contract increments (~1,600 contracts): <2s
   - Player aging (~1,600 players): <2s

3. **Database Query Optimization** (~30 LOC)
   - Profile slow queries (>100ms)
   - Add indexes where needed
   - Optimize batch operations

**Optimization Targets:**
- Offseason-to-preseason transition: <5 seconds
- Full season simulation: <3 minutes
- 10-season simulation: <30 minutes

**Estimated Time:** 6-8 hours

---

### Task 3.5: Documentation Updates

**Objective:** Update all documentation to reflect Milestone 1 implementation

**Files to Update:**

1. **CLAUDE.md** (~30 LOC changes)
   - Update "Current Development Status" to mark Milestone 1 complete
   - Add new demo scripts for multi-season simulation
   - Update core commands section

2. **docs/plans/full_season_simulation_plan.md** (~50 LOC changes)
   - Mark Milestone 1 complete
   - Update implementation status
   - Add lessons learned section

3. **README.md** (if exists) (~20 LOC changes)
   - Add multi-season simulation feature
   - Update quick start guide

4. **API Documentation** (~40 LOC)
   - Document new service classes
   - Add method signatures and examples
   - Update integration guide

**Estimated Time:** 4-6 hours

---

### Phase 3 Deliverables

**New Files Created:**
1. `tests/integration/test_two_season_simulation.py` (~150 LOC)
2. `tests/integration/test_ten_season_simulation.py` (~100 LOC)
3. `tests/integration/test_season_transition_edge_cases.py` (~120 LOC)
4. `tests/performance/test_season_cycle_performance.py` (~100 LOC)

**Modified Files:**
1. `CLAUDE.md` (+30 LOC)
2. `docs/plans/full_season_simulation_plan.md` (+50 LOC)
3. `docs/MILESTONE_1/README.md` (+20 LOC)

**Total New Code:** ~570 LOC (mostly tests and docs)

**Test Coverage:** 10+ integration tests, 5+ performance benchmarks

**Phase 3 Success Criteria:**
- ✅ 2-season test passes consistently
- ✅ 10-season test passes in <30 minutes
- ✅ All edge cases handled gracefully
- ✅ Performance targets met
- ✅ Documentation updated and accurate
- ✅ No known bugs or issues

**Estimated Total Time for Phase 3:** 24-32 hours (Week 3)

---

## Phase 4: Advanced Features (Week 4) - OPTIONAL POLISH

**Goal:** Optimized multi-year simulation with polish

**Priority:** P2 (Nice-to-Have)
**Estimated Effort:** 20-28 hours
**Estimated LOC:** ~500 lines (new code)

**Note:** Phase 4 is optional and can be deferred to Milestone 2 if timeline is tight.

### Task 4.1: Statistics Archival Service

**Objective:** Archive old statistics to improve query performance

**File:** `src/statistics/statistics_archival_service.py` (NEW)

**Method Signatures Needed:**
```python
class StatisticsArchivalService:
    """Service for archiving old season statistics."""

    def __init__(
        self,
        db: UnifiedDatabaseAPI,
        logger: logging.Logger,
        dynasty_id: str
    ):
        """Initialize statistics archival service."""

    def archive_old_seasons(
        self,
        current_season: int,
        retention_years: int = 10
    ) -> Dict[str, int]:
        """
        Archive statistics older than retention window.

        Args:
            current_season: Current season year
            retention_years: How many years to keep in hot storage (default: 10)

        Returns:
            Dict with summary:
                {
                    'seasons_archived': int,
                    'records_moved': int,
                    'storage_freed_mb': float
                }

        Archival Strategy:
        - Keep last 10 seasons in main tables (hot storage)
        - Move older seasons to archive tables (warm storage)
        - Aggregate very old seasons (>20 years) to summary stats (cold storage)
        """

    def aggregate_ancient_seasons(
        self,
        current_season: int,
        ancient_threshold: int = 20
    ) -> Dict[str, int]:
        """
        Aggregate seasons older than threshold to summary statistics.

        Returns:
            Dict with summary of aggregated records
        """
```

**Implementation Details:**
1. Create archive tables (e.g., `player_game_stats_archive`)
2. Move old season data to archive tables
3. Create aggregated summary tables for ancient data
4. Maintain indexes for historical queries

**Estimated Time:** 12-14 hours

---

### Task 4.2: Event Cleanup Service

**Objective:** Clean up old events to reduce database bloat

**File:** `src/events/event_cleanup_service.py` (NEW)

**Method Signatures Needed:**
```python
class EventCleanupService:
    """Service for cleaning up old event data."""

    def cleanup_old_events(
        self,
        current_season: int,
        retention_years: int = 3
    ) -> Dict[str, int]:
        """
        Delete old event data beyond retention window.

        Returns:
            Dict with summary:
                {
                    'events_deleted': int,
                    'milestones_archived': int,
                    'games_archived': int
                }
        """
```

**Implementation Details:**
1. Delete completed game events (retain only current + previous season)
2. Archive milestone events (SCHEDULE_RELEASE, etc.)
3. Clean up expired deadline events
4. Vacuum database to reclaim space

**Estimated Time:** 4-6 hours

---

### Task 4.3: Depth Chart Initialization

**Objective:** Initialize depth charts for new season

**File:** `src/team_management/depth_chart_initialization_service.py` (NEW)

**Implementation Details:**
1. Re-evaluate depth charts after retirements/signings
2. Promote players based on overall rating
3. Fill holes from free agency/draft
4. Update `depth_charts` table

**Estimated Time:** 6-8 hours

---

### Task 4.4: Team Needs Re-analysis

**Objective:** Re-analyze team needs after roster changes

**File:** `src/offseason/team_needs_reanalysis_service.py` (NEW)

**Implementation Details:**
1. Evaluate roster after retirements/FA/draft
2. Update `team_needs` table with new priorities
3. Prepare for next offseason cycle

**Estimated Time:** 4-6 hours

---

### Phase 4 Deliverables

**New Files Created:**
1. `src/statistics/statistics_archival_service.py` (~250 LOC)
2. `src/events/event_cleanup_service.py` (~100 LOC)
3. `src/team_management/depth_chart_initialization_service.py` (~150 LOC)
4. `src/offseason/team_needs_reanalysis_service.py` (~100 LOC)
5. Tests for all services (~400 LOC)

**Total New Code:** ~1,000 LOC (includes tests)

**Phase 4 Success Criteria:**
- ✅ Old statistics archived efficiently
- ✅ Database size optimized (<500MB for 10 seasons)
- ✅ Depth charts updated correctly
- ✅ Team needs reflect current roster state
- ✅ Performance remains good with archival

**Estimated Total Time for Phase 4:** 20-28 hours (Week 4)

---

## Implementation Guidelines

### Code Style Requirements

**1. Follow Existing Patterns**
- Study `src/services/transaction_service.py` (Phase 3 extraction)
- Study `src/database/transaction_context.py` (transaction management)
- Use dependency injection for all services
- Implement lazy initialization where appropriate

**2. Type Hints**
```python
from typing import Dict, List, Optional, Any
from database.unified_api import UnifiedDatabaseAPI

def method_name(
    self,
    param1: int,
    param2: str,
    optional_param: Optional[str] = None
) -> Dict[str, Any]:
    """Comprehensive docstring with Args, Returns, Raises."""
```

**3. Error Handling**
```python
try:
    # Operation
    result = some_operation()
except SpecificException as e:
    self.logger.error(f"Operation failed: {e}")
    raise RuntimeError(f"Detailed error message") from e
```

**4. Logging**
```python
self.logger.debug(f"Starting operation...")
self.logger.info(f"Operation completed: {summary}")
self.logger.warning(f"Potential issue: {details}")
self.logger.error(f"Operation failed: {error}")
```

### Testing Standards

**Minimum Coverage Requirements:**
- Unit tests: 80% code coverage for new services
- Integration tests: All critical workflows covered
- Performance tests: All optimization targets validated

**Test Structure:**
```python
class TestServiceName:
    """Test suite for ServiceName."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for testing."""
        return {
            'db': Mock(spec=UnifiedDatabaseAPI),
            'logger': Mock(spec=logging.Logger)
        }

    def test_method_success_case(self, mock_dependencies):
        """Test method succeeds with valid inputs."""
        service = ServiceName(**mock_dependencies)
        result = service.method()
        assert result['success'] is True

    def test_method_error_case(self, mock_dependencies):
        """Test method handles errors gracefully."""
        service = ServiceName(**mock_dependencies)
        with pytest.raises(ValueError):
            service.method(invalid_input)
```

### Documentation Requirements

**Every New Service Class:**
1. Class docstring explaining purpose and responsibilities
2. Method docstrings with Args, Returns, Raises sections
3. Usage examples in docstring
4. Integration examples in `docs/` folder

**Every Major Feature:**
1. Add to CLAUDE.md "Core System Design" section
2. Update relevant planning documents
3. Create demo script if user-facing
4. Add to test guide

### Git Workflow

**Branch Strategy:**
```bash
# Create feature branch
git checkout -b feature/milestone-1-phase-1-core-foundations

# Commit frequently with clear messages
git commit -m "feat: Add SeasonYearService with increment logic"
git commit -m "test: Add unit tests for season year increment"
git commit -m "docs: Update CLAUDE.md with SeasonYearService"

# Push to remote
git push origin feature/milestone-1-phase-1-core-foundations
```

**Commit Message Format:**
```
type(scope): Short description

Longer description if needed.

- Bullet point 1
- Bullet point 2

Refs: #issue_number
```

**Types:** `feat`, `fix`, `test`, `docs`, `refactor`, `perf`, `chore`

**Review Checklist:**
- [ ] All tests pass (`python -m pytest tests/`)
- [ ] No syntax errors
- [ ] Type hints added
- [ ] Docstrings complete
- [ ] Logging added
- [ ] Error handling implemented
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)

---

## Risk Mitigation Strategy

### Technical Risks

**Risk 1: Season Year Drift**
- **Likelihood:** Medium
- **Impact:** Critical (breaks multi-season simulation)
- **Mitigation:**
  - Use existing `SeasonYearSynchronizer` (proven in Phases 1-5)
  - Add validation after every year increment
  - Leverage auto-recovery guards (Phase 5)
  - Test year consistency in integration tests
- **Detection:**
  - Auto-recovery guards (already implemented)
  - Integration test assertions
  - Manual validation in 10-season test

**Risk 2: Database Transaction Failures**
- **Likelihood:** Low
- **Impact:** High (data corruption)
- **Mitigation:**
  - Use `TransactionContext` for all multi-operation changes
  - Implement rollback logic in handlers
  - Test rollback scenarios explicitly
  - Add database backup before major operations
- **Detection:**
  - Transaction context error logs
  - Integration test validation
  - Database integrity checks

**Risk 3: Performance Degradation**
- **Likelihood:** Medium
- **Impact:** Medium (slow simulation)
- **Mitigation:**
  - Benchmark early and often
  - Use batch database operations
  - Add indexes for common queries
  - Profile and optimize hotspots
  - Target: <3 min per season, <30 min for 10 seasons
- **Detection:**
  - Performance test suite (Task 3.4)
  - `@pytest.mark.slow` tests with timeouts
  - Manual timing during development

**Risk 4: Circular Dependencies**
- **Likelihood:** Low
- **Impact:** Medium (import errors)
- **Mitigation:**
  - Use dependency injection (proven in Phase 3)
  - Avoid direct module imports in services
  - Use TYPE_CHECKING pattern for type hints
  - Service extraction pattern (established)
- **Detection:**
  - Import errors during testing
  - Automated import analysis (if available)
  - Code review

### Schedule Risks

**Risk 5: Phase 1 Takes Longer Than Expected**
- **Likelihood:** Medium
- **Impact:** High (delays entire milestone)
- **Mitigation:**
  - Focus on P0 tasks only in Week 1
  - Defer P1/P2 tasks if needed
  - Use aggressive timeline (3 weeks) as backup
  - Consider Phase 4 optional
- **Contingency:**
  - Extend to 4-week timeline (realistic)
  - Defer Phase 4 to Milestone 2
  - Complete P0 tasks only (2-season capability)

**Risk 6: Integration Testing Reveals Major Issues**
- **Likelihood:** Low-Medium
- **Impact:** High (requires rework)
- **Mitigation:**
  - Test early and often (2-season test after Phase 1)
  - Fix issues immediately (don't defer)
  - Add regression tests for fixed bugs
  - Allocate 50% of Phase 3 to fixes
- **Contingency:**
  - Extend Phase 3 by 1 week
  - Reduce scope of Phase 4
  - Ship with known minor issues (document clearly)

### Integration Risks

**Risk 7: Service Integration Complexity**
- **Likelihood:** Low
- **Impact:** Medium (integration bugs)
- **Mitigation:**
  - Follow Phase 3 service extraction pattern (proven)
  - Use dependency injection consistently
  - Test services in isolation first
  - Integration tests catch service interaction bugs
- **Detection:**
  - Unit tests for services
  - Integration tests for workflows
  - Manual testing of full transitions

**Risk 8: Database Migration Issues**
- **Likelihood:** Low
- **Impact:** High (data loss)
- **Mitigation:**
  - Use database migrations (if available)
  - Backup database before major operations
  - Test migrations on copy of production DB
  - Add rollback scripts
- **Contingency:**
  - Restore from backup
  - Revert code changes
  - Document migration issues for future

---

## Rollback Plan

### If Transition Fails Mid-Execution

**Scenario:** Handler crashes or database error during transition

**Rollback Steps:**

1. **Transaction Rollback** (Automatic)
   - `TransactionContext` auto-rolls back on exception
   - Database returns to pre-transition state
   - No partial state corruption

2. **Controller State Reset**
   - Reset in-memory state to previous season
   - Reload dynasty_state from database
   - Clear any cached data

3. **Error Logging**
   ```python
   try:
       handler.execute(transition)
   except Exception as e:
       self.logger.error(f"Transition failed: {e}", exc_info=True)
       self.logger.error(f"Controller state: season_year={self.season_year}, phase={self.phase}")
       self.logger.error(f"Database state: {self.db.dynasty_get_state(self.dynasty_id)}")
       # Attempt to restore consistency
       self._recover_from_transition_failure()
       raise
   ```

4. **User Notification**
   - Display error message with context
   - Suggest recovery steps (restore backup, retry, report bug)
   - Log detailed diagnostic information

### Database Backup Strategy

**Before Each Season Transition:**
```python
# Optional: Backup database before transition
import shutil
from pathlib import Path

def backup_database(database_path: str, dynasty_id: str, season_year: int):
    """Create backup of database before risky operation."""
    backup_path = f"backups/{dynasty_id}_season_{season_year}_backup.db"
    Path("backups").mkdir(exist_ok=True)
    shutil.copy2(database_path, backup_path)
    print(f"Database backed up to: {backup_path}")
```

**Restore from Backup:**
```python
def restore_database(backup_path: str, database_path: str):
    """Restore database from backup."""
    shutil.copy2(backup_path, database_path)
    print(f"Database restored from: {backup_path}")
```

### Feature Flags for Gradual Rollout

**Environment Variables:**
```python
# Enable/disable features for testing
ENABLE_PLAYER_RETIREMENTS = os.getenv("ENABLE_PLAYER_RETIREMENTS", "true") == "true"
ENABLE_PLAYER_AGING = os.getenv("ENABLE_PLAYER_AGING", "true") == "true"
ENABLE_STATISTICS_ARCHIVAL = os.getenv("ENABLE_STATISTICS_ARCHIVAL", "false") == "true"

# In handler
if ENABLE_PLAYER_RETIREMENTS:
    self._process_player_retirements()
```

**Benefits:**
- Disable problematic features without code changes
- Gradual rollout of new features
- Easy A/B testing
- Quick rollback if issues discovered

---

## Timeline Variations

### Aggressive Timeline (3 Weeks)

**Focus:** P0 + P1 tasks only

| Week | Phase | Tasks | Deliverable |
|------|-------|-------|-------------|
| Week 1 | Phase 1 | Tasks 1.1-1.5 (Core Foundations) | 2-season capability |
| Week 2 | Phase 2 | Tasks 2.1-2.4 (Player Lifecycle) | Dynamic rosters |
| Week 3 | Phase 3 | Tasks 3.1-3.3 (Integration & Testing) | Production-ready |

**Skip:** Phase 4 (Advanced Features) - defer to Milestone 2

**Risk:** Higher - less testing time, may miss edge cases

**Best For:** Tight deadlines, need basic functionality quickly

---

### Realistic Timeline (4 Weeks) - RECOMMENDED

**Focus:** P0 + P1 + integration + select P2 tasks

| Week | Phase | Tasks | Deliverable |
|------|-------|-------|-------------|
| Week 1 | Phase 1 | Tasks 1.1-1.5 (Core Foundations) | 2-season capability |
| Week 2 | Phase 2 | Tasks 2.1-2.4 (Player Lifecycle) | Dynamic rosters |
| Week 3 | Phase 3 | Tasks 3.1-3.5 (Integration & Testing) | Production-ready + docs |
| Week 4 | Phase 4 | Tasks 4.2, 4.3 (Event Cleanup, Depth Charts) | Polish + optimization |

**Skip:** Task 4.1 (Statistics Archival) - defer to Milestone 2 if needed

**Risk:** Medium - balanced approach with adequate testing

**Best For:** Production deployment, quality over speed

---

### Conservative Timeline (6 Weeks)

**Focus:** Thorough testing and validation at each step

| Week | Phase | Tasks | Deliverable |
|------|-------|-------|-------------|
| Week 1-2 | Phase 1 | Tasks 1.1-1.5 + extensive testing | 2-season capability (validated) |
| Week 3-4 | Phase 2 | Tasks 2.1-2.4 + integration testing | Dynamic rosters (validated) |
| Week 5 | Phase 3 | Tasks 3.1-3.5 (Integration & Testing) | Production-ready + docs |
| Week 6 | Phase 4 | All Phase 4 tasks | Complete polish |

**Skip:** Nothing - complete implementation

**Risk:** Low - maximum testing and validation

**Best For:** Mission-critical deployment, first-time implementation

---

### ASCII Gantt Chart

```
Realistic 4-Week Timeline (RECOMMENDED)

Week 1: Phase 1 - Core Foundations
[====Task 1.1====][===Task 1.2===][==Task 1.3==][1.4][==Task 1.5==]
Mon     Tue     Wed     Thu     Fri     Sat     Sun

Week 2: Phase 2 - Player Lifecycle
[====Task 2.1====][==Task 2.2==][Task 2.3][===Task 2.4===]
Mon     Tue     Wed     Thu     Fri     Sat     Sun

Week 3: Phase 3 - Integration & Testing
[==Task 3.1==][====Task 3.2====][Task 3.3][=3.4=][=3.5=]
Mon     Tue     Wed     Thu     Fri     Sat     Sun

Week 4: Phase 4 - Advanced Features (Select)
[Task 4.2][===Task 4.3===][=Polish=][=Final Testing=]
Mon     Tue     Wed     Thu     Fri     Sat     Sun
```

---

## Progress Tracking

### Daily Progress Measurement

**Metrics to Track:**
1. **Lines of Code Written** (target: ~50-75 LOC/hour for services)
2. **Tests Written** (target: 1-2 tests/hour)
3. **Test Pass Rate** (target: >90% by end of day)
4. **Tasks Completed** (compare to plan)

**Daily Log Format:**
```
Date: 2025-11-10
Phase: 1 (Core Foundations)
Tasks Completed:
  - ✅ Task 1.1: SeasonYearService (6 hours)
Tasks In Progress:
  - 🔄 Task 1.2: CapYearRolloverService (40% complete)
Blockers:
  - None
Tomorrow's Plan:
  - Complete Task 1.2
  - Start Task 1.3
LOC Written: 150 (100 production, 50 tests)
Tests Written: 5
Tests Passing: 5/5 (100%)
Notes:
  - SeasonYearSynchronizer integration smooth
  - Need to add validation for year consistency
```

### Weekly Milestone Reviews

**End of Week Checklist:**

**Week 1 (Phase 1):**
- [ ] All 4 new service files created
- [ ] OffseasonToPreseasonHandler enhanced
- [ ] 15+ unit tests passing
- [ ] 2-season integration test passing
- [ ] Documentation updated

**Week 2 (Phase 2):**
- [ ] All 4 player lifecycle services created
- [ ] Services integrated into handler
- [ ] 20+ unit tests passing
- [ ] Dynamic roster test passing
- [ ] Player aging/retirement validated

**Week 3 (Phase 3):**
- [ ] 2-season test passing consistently
- [ ] 10-season test passing in <30 min
- [ ] Edge cases tested
- [ ] Performance benchmarks met
- [ ] Documentation complete

**Week 4 (Phase 4):**
- [ ] Selected advanced features implemented
- [ ] All tests passing
- [ ] Performance optimized
- [ ] Final validation complete
- [ ] Ready for production

### Completion Checklist

**Milestone 1 is COMPLETE when:**

**Core Functionality:**
- [ ] ✅ Can simulate 2 consecutive seasons without intervention
- [ ] ✅ Can simulate 10 consecutive seasons (performance target met)
- [ ] ✅ Season year increments correctly (2024 → 2025 → 2026...)
- [ ] ✅ Salary cap rolls over with carryover and dead money
- [ ] ✅ Contract years increment, expired contracts handled
- [ ] ✅ Statistics preserved across seasons (proper season_year tagging)
- [ ] ✅ Draft classes generated at correct time (offseason end)
- [ ] ✅ Standings reset to 0-0-0 at season start
- [ ] ✅ No year drift detected (all systems synchronized)

**Player Lifecycle:**
- [ ] ✅ Player retirements working (5-15 per year)
- [ ] ✅ Player aging with attribute decay
- [ ] ✅ Free agent pool updated correctly
- [ ] ✅ Rookie contracts generated for drafted players

**Testing:**
- [ ] ✅ 2-season integration test passes
- [ ] ✅ 10-season integration test passes (<30 min)
- [ ] ✅ All unit tests passing (>90% coverage)
- [ ] ✅ Edge cases tested and handled
- [ ] ✅ Performance benchmarks met

**Documentation:**
- [ ] ✅ CLAUDE.md updated
- [ ] ✅ Full season simulation plan updated
- [ ] ✅ API documentation complete
- [ ] ✅ Demo scripts created
- [ ] ✅ README updated

**Code Quality:**
- [ ] ✅ All code follows style guidelines
- [ ] ✅ Type hints added throughout
- [ ] ✅ Docstrings complete
- [ ] ✅ Error handling implemented
- [ ] ✅ Logging comprehensive
- [ ] ✅ No breaking changes (or clearly documented)

**Deployment:**
- [ ] ✅ Feature branch merged to main
- [ ] ✅ Database migrations applied (if any)
- [ ] ✅ Backward compatibility verified
- [ ] ✅ No known critical bugs

---

## Summary

This 4-phase implementation plan provides a **structured roadmap** to deliver Milestone 1: Complete Multi-Year Season Cycle. The plan:

1. **Leverages existing infrastructure** (Statistics Preservation, Season Year Tracking, Salary Cap System)
2. **Follows proven patterns** (Service extraction from Phase 3, TransactionContext from recent work)
3. **Provides realistic estimates** (~1,650 LOC across 12 systems, 3-4 weeks)
4. **Includes comprehensive testing** (20+ unit tests, 10+ integration tests, performance benchmarks)
5. **Mitigates risks** (transaction safety, year drift protection, rollback plans)
6. **Offers flexibility** (aggressive/realistic/conservative timelines)

**Next Steps:**
1. Review and approve this plan
2. Create feature branch: `feature/milestone-1-season-cycle`
3. Begin Phase 1: Core Foundations (Week 1)
4. Track progress daily using provided templates
5. Validate with 2-season test after Phase 1
6. Complete all phases for production deployment

**Success Criteria:** Can simulate 10+ consecutive NFL seasons automatically with realistic player progression, salary cap management, and complete statistics preservation.

---

**End of Implementation Plan**

*Last Updated: 2025-11-09*
*Status: Ready to Execute*
*Estimated Completion: 3-4 weeks from start*
