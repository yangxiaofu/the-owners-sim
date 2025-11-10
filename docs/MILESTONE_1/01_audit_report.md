# Milestone 1: Complete System Audit Report

**Date:** 2025-11-09
**Auditor:** System Analysis (Comprehensive Codebase Review)
**Scope:** Offseason-to-Preseason Transition & Multi-Year Season Cycle Requirements
**Status:** 🔴 Critical Gap Identified - Only 2/14 systems implemented

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Implementation Analysis](#current-implementation-analysis)
3. [Complete Initialization Checklist](#complete-initialization-checklist)
4. [Gap Analysis](#gap-analysis)
5. [Recommended Implementation Plan](#recommended-implementation-plan)
6. [Validation & Testing Strategy](#validation--testing-strategy)
7. [Risk Assessment](#risk-assessment)
8. [Conclusion](#conclusion)

---

## Executive Summary

### Audit Objective

Determine all systems that must be initialized/reset for a **repeatable multi-year season cycle**, enabling users to simulate 10+ consecutive NFL seasons in "The Owners Sim" without manual intervention.

### Critical Finding

The offseason-to-preseason transition is **dramatically incomplete**. The `OffseasonToPreseasonHandler` implements only **2 of 14 critical systems** (14% complete):

- ✅ **Schedule Validation** (48 preseason + 272 regular season games)
- ✅ **Standings Reset** (all 32 teams to 0-0-0)
- ❌ **Season Year Increment** - Missing
- ❌ **12 additional systems** - Missing (~1,650 LOC needed)

### Scope of Missing Work

| Category | Systems | LOC Estimate | Complexity | Timeline |
|----------|---------|--------------|------------|----------|
| Critical (Must Have) | 6 | 650 | Low-Medium | Week 1-2 |
| High Priority (Should Have) | 4 | 600 | Medium-High | Week 2-3 |
| Nice-to-Have (Optional) | 4 | 900 | Medium-High | Week 4 |
| **Total** | **14** | **~2,150** | **Mixed** | **3-4 weeks** |

### Infrastructure Readiness

**Good News:** Core infrastructure is production-ready!
- ✅ Statistics Preservation System (Phases 1-5 complete)
- ✅ Season Year Tracking (auto-recovery + drift protection)
- ✅ Salary Cap System (full 2024-2025 NFL CBA compliance)
- ✅ Player Generation (DraftClassGenerator functional - 224 prospects/year)
- ✅ Schedule Generator (NFL-realistic timing with SCHEDULE_RELEASE milestone)
- ✅ Event System (complete offseason timeline)

**Challenge:** Infrastructure exists but **year-over-year integration is missing**!

---

## Current Implementation Analysis

### 1. Offseason-to-Preseason Handler

**File:** `src/season/phase_transition/transition_handlers/offseason_to_preseason.py`
**Lines:** 465 total
**Registration:** ✅ Properly registered in SeasonCycleController (lines 326-337)

#### What It DOES (2/14 systems):

**1.1 Schedule Validation** ✅ (Lines 204-210, 422-462)
```python
def _validate_games_exist(self, effective_year: int):
    """Validate SCHEDULE_RELEASE milestone executed successfully."""
    total_games = self._event_db.events_count_games_for_season(...)
    if total_games < 320:  # 48 preseason + 272 regular
        raise ValueError(f"Expected 320 games, found {total_games}")
```

**Key Insight:** Games are generated 3 months before preseason starts at SCHEDULE_RELEASE milestone (mid-May) - NFL realistic!

**1.2 Standings Reset** ✅ (Lines 212-217)
```python
self._reset_standings(effective_year)
# Resets all 32 teams to 0-0-0 for new season
```

#### What It DOES NOT Do (12/14 systems):

The handler is **missing**:
- ❌ Season year increment (Line 191 accepts `new_season_year` but never uses it!)
- ❌ Draft class generation for next season
- ❌ Salary cap year rollover
- ❌ Contract year increments
- ❌ Player retirements (age-based, injury-based)
- ❌ Player aging (years_pro++, attribute decay)
- ❌ Free agent pool updates
- ❌ Rookie contract generation
- ❌ Statistics archival
- ❌ Event cleanup (delete old events)
- ❌ Depth chart initialization
- ❌ Team needs re-analysis

**Code Evidence - Unused Parameter:**
```python
def __init__(self, ..., new_season_year: int, ...):
    self._new_season_year = new_season_year  # ← Stored but NEVER USED!
```

---

### 2. Season Year Management

**Status:** ✅ Infrastructure Complete (Phases 1-5), ❌ Increment Logic Missing

**Single Source of Truth:** `SeasonCycleController.season_year`

**Implementation:** `SeasonYearSynchronizer` (Atomic updates - Phase 3)
```python
self.year_synchronizer = SeasonYearSynchronizer(
    get_current_year=lambda: self.season_year,
    set_controller_year=self._set_season_year,
    update_database_year=self._update_database_year,
    dynasty_id=self.dynasty_id,
)
```

**Auto-Recovery Guards (Phase 5):**
- ✅ Guard after controller initialization
- ✅ Guard before daily simulation
- ✅ Protects against year drift from database corruption

**CRITICAL GAP:**
- ✅ Infrastructure complete
- ✅ Increment method exists: `year_synchronizer.increment_year()` (Hypothetical - needs implementation)
- ❌ **Never called** during offseason-to-preseason transition!
- ⚠️ Responsibility unclear: Handler or Controller?

**Recommendation:** Handler should call `_increment_season_year()` helper method that delegates to synchronizer.

---

### 3. Player Generation

**Status:** ✅ Generator Complete, ❌ Timing Wrong

**File:** `src/player_generation/generators/draft_class_generator.py`

**Capabilities:**
- ✅ Generate 224 prospects (7 rounds × 32 picks)
- ✅ Position distribution (QB 15%, EDGE 20%, OT 20%, WR 15%, CB 15% in R1)
- ✅ Realistic talent distribution by round
- ✅ Database integration via `draft_generate_class()`

**Current Timing (WRONG):**
```python
# SeasonCycleController.__init__ (Line 392)
self._generate_draft_class_if_needed()  # ← Runs at SEASON START
```

**Correct Timing (NEEDED):**
```python
# OffseasonToPreseasonHandler.execute() (Missing)
self._generate_draft_class(self._new_season_year + 1)  # ← Should run during OFFSEASON
```

**Why This Matters:**
- Current: Generates draft class for **current** season at season start
- Needed: Generate draft class for **next** season during offseason
- Impact: Allows scouting/planning during current season for next year's draft

---

### 4. Schedule Generation

**Status:** ✅ Complete (No Changes Needed)

**File:** `src/scheduling/schedule_generator.py`

**Strategy:**
1. ✅ **SCHEDULE_RELEASE Milestone** (mid-May, during offseason)
   - Generates all 320 games (48 preseason + 272 regular season)
   - 3 months before preseason starts (NFL realistic)

2. ✅ **Handler Validation** (offseason-to-preseason transition)
   - Validates games exist
   - Does NOT regenerate (assumes SCHEDULE_RELEASE executed)

**Date Calculations:**
- Labor Day: First Monday in September
- Regular Season Start: First Thursday after Labor Day
- Preseason Start: ~3.5 weeks before regular season

**No Action Required:** System is production-ready.

---

### 5. Standings Reset

**Status:** ✅ Complete (No Changes Needed)

**Implementation:** `StandingsStore.clear()`

**Database Schema:**
```sql
CREATE TABLE standings (
    dynasty_id TEXT,
    team_id INTEGER,
    season INTEGER,
    season_type TEXT,  -- 'preseason', 'regular_season', 'playoffs'
    wins, losses, ties INTEGER,
    PRIMARY KEY (dynasty_id, team_id, season, season_type)
)
```

**Reset Logic:**
1. ✅ Resets all 32 teams to 0-0-0
2. ✅ Clears head-to-head records
3. ✅ Re-sorts standings
4. ✅ Logs transaction

**Supports:** Preseason, regular season, and playoff standings separation.

**No Action Required:** System is production-ready.

---

### 6. Salary Cap Year Transition

**Status:** ⚠️ Infrastructure Exists, ❌ Transition Logic Missing

**Files:** `src/salary_cap/`

**Current Capabilities:**
- ✅ Cap calculation (top-51 offseason, 53-man regular season)
- ✅ Contract management
- ✅ Dead money calculations
- ✅ Signing bonus proration
- ✅ June 1 designations

**Missing Year Transition Logic:**

| Task | Estimated LOC | Complexity |
|------|---------------|------------|
| 1. Load new salary cap limit | 20 | Low |
| 2. Calculate carryover from prev season | 50 | Medium |
| 3. Increment contract years | 50 | Medium |
| 4. Move expired contracts to history | 30 | Low |
| 5. Rookie contract generation | 150 | Medium |
| 6. Dead money carryover | 50 | Medium |
| 7. Switch roster mode (top-51 → 53-man) | 20 | Low |
| **Total** | **370 LOC** | **Medium** |

**Recommended Service:** `CapYearRolloverService`

---

### 7. Contract Year Increments

**Status:** ❌ Missing Entirely

**Required Logic:**
```python
# Pseudo-code
for contract in active_contracts:
    contract.year += 1
    if contract.year > contract.total_years:
        move_to_historical_contracts(contract)
        if contract.player_status == 'UFA':
            add_to_free_agent_pool(contract.player_id)
```

**Database Impact:**
- Update `contracts` table (year column)
- Move expired to `contract_history` table
- Update `free_agents` table

**Estimated Work:** ~100 LOC

---

### 8. Statistics Preservation

**Status:** ✅ Phases 1-5 Complete (No Changes Needed for Basic Function)

**Documentation:** `docs/plans/statistics_preservation.md`

**Implemented:**
- ✅ Single source of truth for season_year tracking
- ✅ Statistics tagged by season + season_type
- ✅ Auto-recovery from drift
- ✅ Phase-aware synchronization

**Database Schema:**
```sql
player_game_stats (
    player_id, game_id,
    season INTEGER,              -- ← Season tagging
    season_type TEXT,            -- ← Phase separation
    ...
)
```

**Future Enhancement (Deferred to Milestone 2):**
- Statistics archival (hot/warm/cold storage)
- Aggregation of old seasons
- Deletion beyond retention window

**No Immediate Action Required.**

---

### 9. Event System Reset

**Status:** ✅ Scheduling Complete, ❌ Cleanup Missing

**File:** `src/offseason/offseason_event_scheduler.py`

**Current Capabilities:**
- ✅ Schedules 24 offseason events (deadlines, windows, milestones)
- ✅ **SCHEDULE_RELEASE milestone** generates next season's games
- ✅ Dynasty isolation (events per dynasty)

**Missing Cleanup Logic:**
```python
# Needed before scheduling new season events:
1. Delete completed game events (previous season)
2. Delete completed deadline events (previous offseason)
3. Delete completed milestone events
4. Archive for historical reference (optional)
```

**Estimated Work:** ~100 LOC

---

### 10. Calendar Initialization

**Status:** ✅ Continuous (No Reset Needed)

**Key Finding:** Calendar is **continuous** across season boundaries!

- ✅ No reset required
- ✅ Automatically advances day-by-day
- ✅ Date continuity preserved (2024 offseason → 2025 preseason)
- ✅ Preseason start calculated from year

**No Action Required.**

---

### 11. Player Lifecycle Management

**Status:** ❌ Missing Entirely

#### 11.1 Player Retirements
**Estimated Work:** ~200 LOC, High Complexity

**Required Logic:**
- Identify retirement candidates (age > 35, low ratings, injury history)
- Execute retirement (move to `retired_players` table)
- Remove from team rosters
- Calculate retirement dead money (signing bonus acceleration)

#### 11.2 Player Aging
**Estimated Work:** ~150 LOC, Medium Complexity

**Required Logic:**
- Increment `years_pro` for all active players
- Calculate age from `birth_year`
- Apply attribute decay for players 30+ (speed, acceleration decline)
- Update potential ratings (decline for aging players)

#### 11.3 Free Agent Pool Updates
**Estimated Work:** ~100 LOC, Low Complexity

**Required Logic:**
- Move unsigned players to `free_agents` table
- Update FA contract years
- Categorize by type (UFA, RFA, ERFA)
- Clear from team rosters

**Recommended Service:** `PlayerLifecycleManager`

---

### 12. Integration Points

**Master Orchestrator:** `SeasonCycleController` (2,825 lines after Phase 3 refactoring)

**Component Hierarchy:**
```
SeasonCycleController
├── PhaseTransitionManager
│   └── OffseasonToPreseasonHandler ← FOCUS OF THIS AUDIT
├── SeasonYearSynchronizer (atomic year updates)
├── SeasonYearValidator (drift detection)
└── TransactionService (AI transactions)
```

**Critical Dependencies:**
- UnifiedDatabaseAPI (database operations)
- EventDatabaseAPI (event storage)
- RandomScheduleGenerator (schedule generation)
- OffseasonEventScheduler (event scheduling)
- StandingsStore (standings management)
- CapCalculator (salary cap operations)
- DraftClassGenerator (player generation)

**Circular Dependency Risk:** ⚠️ Medium
- SeasonCycleController is large (2,825 lines)
- Service extraction ongoing (Phase 3 complete)
- Recommendation: Continue service extraction for new year transition logic

---

## Complete Initialization Checklist

### Critical Systems (Must Have - Week 1-2)

| # | System | Status | LOC | Owner |
|---|--------|--------|-----|-------|
| 1 | **Schedule Validation** | ✅ Complete | 40 | OffseasonToPreseasonHandler |
| 2 | **Standings Reset** | ✅ Complete | 30 | OffseasonToPreseasonHandler |
| 3 | **Season Year Increment** | ❌ Missing | 50 | SeasonYearSynchronizer |
| 4 | **Draft Class Generation (Timing Fix)** | ❌ Wrong Timing | 50 | OffseasonToPreseasonHandler |
| 5 | **Salary Cap Year Rollover** | ❌ Missing | 370 | CapYearRolloverService (new) |
| 6 | **Contract Year Increments** | ❌ Missing | 100 | ContractYearManager (new) |

**Subtotal:** 2 complete, 4 missing | ~570 LOC | **Deliverable: 2+ consecutive seasons**

### High-Priority Systems (Should Have - Week 2-3)

| # | System | Status | LOC | Owner |
|---|--------|--------|-----|-------|
| 7 | **Player Retirements** | ❌ Missing | 200 | PlayerLifecycleManager (new) |
| 8 | **Player Aging** | ❌ Missing | 150 | PlayerLifecycleManager (new) |
| 9 | **Free Agent Pool Updates** | ❌ Missing | 100 | PlayerLifecycleManager (new) |
| 10 | **Rookie Contract Generation** | ❌ Missing | 150 | CapYearRolloverService |

**Subtotal:** 0 complete, 4 missing | ~600 LOC | **Deliverable: Dynamic rosters**

### Nice-to-Have Systems (Optional - Week 4)

| # | System | Status | LOC | Owner |
|---|--------|--------|-----|-------|
| 11 | **Statistics Archival** | ⚠️ Planned | 500 | StatisticsArchivalService (new) |
| 12 | **Event Cleanup** | ❌ Missing | 100 | EventCleanupService (new) |
| 13 | **Depth Chart Initialization** | ❌ Missing | 150 | DepthChartManager |
| 14 | **Team Needs Re-analysis** | ❌ Missing | 100 | TeamNeedsAnalyzer |

**Subtotal:** 0 complete, 4 missing | ~850 LOC | **Deliverable: Polished experience**

---

## Gap Analysis

### What Exists and Works

| Component | Coverage | Quality | Testing |
|-----------|----------|---------|---------|
| Schedule generation | 100% | ✅ Production | ✅ Tested |
| Schedule validation | 100% | ✅ Production | ✅ Tested |
| Standings reset | 100% | ✅ Production | ✅ Tested |
| Event scheduling | 100% | ✅ Production | ✅ Tested |
| Season year tracking infrastructure | 100% | ✅ Production | ✅ Tested |
| Draft class generator | 100% | ✅ Production | ⚠️ Partial |
| Salary cap calculator | 100% | ✅ Production | ✅ Tested |
| Statistics preservation system | 100% | ✅ Production | ✅ Tested |

### What Doesn't Exist

| Component | LOC Estimate | Complexity | Dependencies |
|-----------|--------------|------------|--------------|
| Season year increment logic | 50 | Low | SeasonYearSynchronizer |
| Cap year rollover service | 370 | Medium | CapCalculator, ContractManager |
| Contract year increments | 100 | Medium | ContractManager |
| Player retirements | 200 | High | PlayerLifecycleManager (new) |
| Player aging | 150 | Medium | PlayerLifecycleManager (new) |
| FA pool updates | 100 | Low | Database API |
| Rookie contract generation | 150 | Medium | CapCalculator, Draft API |
| Statistics archival | 500 | High | Database API |
| Event cleanup | 100 | Low | EventDatabaseAPI |
| Depth chart init | 150 | Medium | DepthChartManager |
| Team needs analysis | 100 | Medium | TeamNeedsAnalyzer |

**Total New Code:** ~1,970 LOC

### What Exists But Doesn't Work

| Component | Issue | Fix LOC |
|-----------|-------|---------|
| Draft class timing | Runs at season start, not offseason | 50 |
| Handler year parameter | Accepted but never used | 20 |

---

## Recommended Implementation Plan

### Phase 1: Core Foundations (Week 1 - Days 1-5)

**Goal:** Enable 2+ consecutive seasons

**Day 1-2: Season Year & Draft Class**
- Implement season year increment in handler
- Fix draft class generation timing
- Add synchronization validation

**Day 3-4: Salary Cap Rollover**
- Create `CapYearRolloverService`
- Load new cap limit
- Calculate carryover
- Switch roster modes

**Day 5: Contract Years**
- Create `ContractYearManager`
- Increment contract years
- Archive expired contracts
- Update dead money

**Deliverable:** Working 2-season simulation

### Phase 2: Player Lifecycle (Week 2 - Days 6-10)

**Goal:** Realistic player progression

**Day 6-7: Retirements**
- Create `PlayerLifecycleManager`
- Implement retirement logic
- Calculate dead money
- Update rosters

**Day 8-9: Aging**
- Increment years_pro
- Apply attribute decay
- Update potential ratings

**Day 10: Free Agent Pool**
- Move unsigned players to FA
- Update FA contract years
- Categorize by type

**Deliverable:** Dynamic rosters with turnover

### Phase 3: Integration & Testing (Week 3 - Days 11-15)

**Goal:** Production readiness

**Day 11-12: Rookie Contracts**
- Generate contracts for drafted players
- Apply rookie wage scale
- Link to rosters

**Day 13: Event Cleanup**
- Delete old events
- Archive milestones

**Day 14-15: Testing**
- 2-season test
- 10-season test
- Edge cases
- Performance benchmarking

**Deliverable:** Production-ready cycle

---

## Validation & Testing Strategy

### Unit Tests (Per Component)

```python
# test_season_year_increment.py
def test_increment_year_updates_controller():
    assert controller.season_year == 2024
    handler.execute()
    assert controller.season_year == 2025

# test_cap_rollover.py
def test_cap_rollover_loads_new_limit():
    assert cap.get_limit(2025) == 255_400_000  # 2025 cap

# test_contract_increments.py
def test_contract_year_increments():
    assert contract.year == 1
    manager.increment_year()
    assert contract.year == 2
```

### Integration Tests

```python
# test_two_season_simulation.py
def test_two_consecutive_seasons():
    # Season 1: 2024
    controller.simulate_to_offseason()
    assert controller.season_year == 2024

    # Transition
    controller.advance_to_next_season()
    assert controller.season_year == 2025

    # Season 2: 2025
    controller.simulate_to_offseason()
    assert controller.season_year == 2025

# test_ten_season_simulation.py
@pytest.mark.slow
def test_ten_season_simulation():
    for year in range(2024, 2034):
        controller.simulate_to_offseason()
        assert controller.season_year == year
        controller.advance_to_next_season()
```

### Manual Validation Checklist

- [ ] Season year increments correctly (2024 → 2025 → 2026...)
- [ ] Standings reset to 0-0-0 each season
- [ ] New draft class available each offseason
- [ ] Salary cap rolls over with carryover
- [ ] Contracts increment and expire correctly
- [ ] Players age and retire realistically
- [ ] Statistics tagged with correct season_year
- [ ] No year drift between components

---

## Risk Assessment

### High-Risk Areas

1. **Season Year Drift** (Likelihood: Medium, Impact: Critical)
   - **Risk:** Controller and database fall out of sync
   - **Mitigation:** Use SeasonYearSynchronizer (already exists)
   - **Detection:** Auto-recovery guards (already implemented)

2. **Database Transaction Failures** (Likelihood: Low, Impact: High)
   - **Risk:** Partial transition leaves corrupt state
   - **Mitigation:** Use transaction contexts, add rollback logic
   - **Detection:** Comprehensive validation after each step

3. **Performance Degradation** (Likelihood: Medium, Impact: Medium)
   - **Risk:** 10-season simulation takes too long
   - **Mitigation:** Benchmark early, optimize hotspots
   - **Target:** <3 minutes per season, <30 minutes for 10 seasons

4. **Circular Dependencies** (Likelihood: Low, Impact: Medium)
   - **Risk:** New services create import cycles
   - **Mitigation:** Use dependency injection, avoid direct imports
   - **Detection:** Automated import analysis tools

### Rollback Strategy

If transition fails mid-execution:
1. Transaction rollback (database changes)
2. Controller state reset (in-memory state)
3. Error logging with full context
4. User notification with recovery steps

---

## Conclusion

### Summary of Findings

The offseason-to-preseason transition is **critically incomplete** with only **2 of 14 systems** (14%) implemented. However, the **underlying infrastructure is production-ready**, and the missing work is well-scoped at approximately **~2,000 lines of code** across 8-10 new service classes.

### Recommended Path Forward

1. **Immediate (Week 1):** Implement core foundations (P0 tasks)
   - Season year increment
   - Cap year rollover
   - Contract year increments
   - Draft class timing fix

2. **Near-Term (Weeks 2-3):** Complete high-priority systems
   - Player lifecycle management
   - Rookie contract generation
   - Comprehensive testing

3. **Future (Week 4+):** Polish and optimization
   - Statistics archival
   - Event cleanup
   - Depth chart initialization

### Success Criteria

Milestone 1 is **complete** when a user can:
- ✅ Simulate 2 consecutive seasons without manual intervention
- ✅ Simulate 10 consecutive seasons with realistic player progression
- ✅ Observe correct year increment, cap rollover, and contract management
- ✅ Verify statistics preservation across multiple seasons
- ✅ Experience no year drift or data corruption

### Effort Estimate

**Aggressive:** 3 weeks (core + high-priority only)
**Realistic:** 4 weeks (core + high-priority + polish)
**Conservative:** 6 weeks (includes thorough testing and documentation)

---

**End of Audit Report**

*This comprehensive audit was conducted through automated codebase analysis on 2025-11-09.*
*Last updated: 2025-11-09 09:51 PST*
