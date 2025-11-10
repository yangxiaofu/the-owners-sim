# Season 1 → Season 2 Transition Audit

**Date**: 2025-11-09
**Dynasty**: `1st`
**Issue**: Games not detected/simulated in Season 2 despite successful transition
**Status**: Root cause identified, fixes in progress

---

## Executive Summary

Season 2 preseason and regular season games are not being detected during simulation due to a **critical bug in `SimulationExecutor`** (lines 507-519) that queries for the wrong season year. The root cause is that **`PhaseState` class is missing the `season_year` attribute**, causing the query logic to fall back to stale initialization values.

**Impact**: Multi-year dynasty mode completely broken - all games after Season 1 fail to simulate.

**Solution**: 5-part fix to add `season_year` to PhaseState and simplify query logic.

---

## Bug Timeline

### Initial Symptoms
- ✅ Season 1 (2025) completed successfully with all phases
- ✅ OFFSEASON → PRESEASON transition executed for Season 2 (2026)
- ✅ Games scheduled in database with correct `game_id` format: `preseason_2026_*`, `regular_2026_*`
- ❌ Calendar shows games but they don't simulate
- ❌ No game results generated in Season 2

### Fixes Applied So Far

#### Fix A: Calendar Date Advancement (COMPLETED)
**File**: `src/season/season_cycle_controller.py` (lines 1917-1937)

**Problem**: Calendar remained at Nov 10, 2025 during OFFSEASON → PRESEASON transition while games scheduled for Aug 5, 2026.

**Solution**: Added `calendar.reset()` to jump calendar forward to preseason start date:

```python
# CRITICAL FIX: Advance calendar to preseason start date
preseason_start_datetime = self._calculate_preseason_start_for_handler(self.season_year)
from src.calendar.date_models import Date
preseason_start_date = Date(
    preseason_start_datetime.year,
    preseason_start_datetime.month,
    preseason_start_datetime.day
)

if self.verbose_logging:
    old_date = self.calendar.get_current_date()
    print(f"[CALENDAR_ADVANCE] Jumping calendar from {old_date} to {preseason_start_date}")

# Jump calendar forward to preseason start (e.g., Nov 2025 → Aug 2026)
self.calendar.reset(preseason_start_date)

self.db.dynasty_update_state(
    season=self.season_year,  # Already updated by synchronizer
    current_date=str(self.calendar.get_current_date()),  # Now correctly at preseason start
    current_phase="PRESEASON",
    current_week=0,
)
```

**Test Result**: `test_2026_game_simulation.py` passed - games simulate correctly when run standalone.

**Outcome**: ⚠️ Partial success - test script works, but actual gameplay still broken.

#### Fix B: Event Query Optimization (COMPLETED)
**File**: `src/events/event_database_api.py` (lines 1487-1497)

**Problem**: `get_events_by_dynasty_and_timestamp()` ignored `event_type` parameter, causing 5x query overhead (260 events instead of 52).

**Solution**: Added conditional logic to use `event_type` when provided:

```python
if event_type:
    return unified.events_get_by_type(
        event_type=event_type,
        start_timestamp=start_timestamp_ms,
        end_timestamp=end_timestamp_ms
    )
else:
    return unified.events_get_by_date_range(start_timestamp_ms, end_timestamp_ms)
```

**Outcome**: ✅ UI calendar performance improved, no functional impact on game detection.

#### Fix C: Database Cleanup (COMPLETED)
**Problem**: Duplicate conflicting records in `dynasty_state` table:
```
id=42: season=2026, date=2025-11-10, phase=PRESEASON
id=44: season=2025, date=2025-11-10, phase=offseason
```

**Solution**: Deleted stale record and updated date:
```sql
DELETE FROM dynasty_state WHERE dynasty_id = '1st' AND id = 44;
UPDATE dynasty_state SET "current_date" = '2026-08-05' WHERE dynasty_id = '1st' AND id = 42;
```

**Outcome**: ✅ Single source of truth restored.

---

## Root Cause Analysis

### THE CRITICAL BUG: Missing `season_year` in PhaseState

**Location**: `src/calendar/simulation_executor.py` lines 507-519

**Bug Description**:
During preseason 2026, the query logic tries to determine which season year to query for:

```python
# Get preseason game events for this specific dynasty/season
all_preseason_events = self.event_db.get_events_by_dynasty(
    dynasty_id=self.dynasty_id,
    event_type="GAME"
)

phase_info = self.calendar.get_phase_info()  # ← Returns dict from PhaseState
current_phase = phase_info.get("current_phase", "").lower()
current_date = self.calendar.get_current_date()

if current_phase == "offseason":
    current_season_year = current_date.year  # Uses calendar year
else:
    # ❌ BUG: phase_info DOES NOT CONTAIN "season_year" key!
    current_season_year = phase_info.get("season_year", self.season_year)
    # Falls back to self.season_year = 2025 (STALE FROM INITIALIZATION!)

preseason_season = current_season_year + 1 if current_phase == "offseason" else current_season_year
# During PRESEASON 2026: preseason_season = 2025 ❌

# Query filters by WRONG year
preseason_events = [
    e for e in all_preseason_events
    if e.get('game_id', '').startswith(f'preseason_{preseason_season}_')  # preseason_2025_*
]
# Database has: preseason_2026_*
# Result: ZERO MATCHES ❌
```

### Why Does `phase_info.get("season_year")` Return None?

**Investigation of PhaseState**:

```python
# src/calendar/phase_state.py
class PhaseState:
    def __init__(self, initial_phase: SeasonPhase = SeasonPhase.REGULAR_SEASON):
        self._phase = initial_phase
        self._lock = threading.Lock()
        # ❌ NO self._season_year attribute!

    def to_dict(self) -> dict:
        return {
            "current_phase": self._phase.value.upper()
            # ❌ NO "season_year" key in dictionary!
        }
```

**Key Finding**: PhaseState is meant to be the "single source of truth" for the current phase, but it's **missing the season year entirely**. This forces SimulationExecutor to use unreliable fallback logic.

### Cascading Effects

1. **Initialization**: `SimulationExecutor.__init__()` sets `self.season_year = 2025` (from initial state)
2. **Season Advances**: SeasonCycleController updates its own `season_year = 2026`
3. **PhaseState Never Updated**: No code updates PhaseState with new season year
4. **Query Failure**: SimulationExecutor queries for 2025 games while database has 2026 games
5. **No Games Detected**: Zero matches, no simulation occurs

### Why Test Script Passed But UI Failed

**Test Script** (`test_2026_game_simulation.py`):
- Creates fresh `SeasonCycleController` with correct date (2026-08-05)
- Calls `advance_day()` directly
- SimulationExecutor created with synchronized state

**UI Workflow**:
- Long-running SeasonCycleController instance
- SimulationExecutor initialized in Season 1 (2025)
- Never re-initialized or updated with Season 2 year (2026)
- Uses stale `self.season_year = 2025`

---

## Database Evidence

### Events Table - Games Scheduled Correctly
```sql
SELECT game_id, json_extract(data, '$.parameters.game_date') as game_date
FROM events
WHERE event_type = 'GAME'
  AND game_id LIKE 'preseason_2026_%'
  AND dynasty_id = '1st'
ORDER BY timestamp ASC
LIMIT 5;
```

**Results**:
```
preseason_2026_week1_game1: 2026-08-05T19:00:00
preseason_2026_week1_game2: 2026-08-05T19:00:00
preseason_2026_week1_game3: 2026-08-06T19:00:00
preseason_2026_week2_game1: 2026-08-12T19:00:00
preseason_2026_week2_game2: 2026-08-12T19:00:00
```

✅ Games exist with correct 2026 year prefix.

### Dynasty State - After Fix A
```sql
SELECT * FROM dynasty_state WHERE dynasty_id = '1st';
```

**Results**:
```
id: 42
dynasty_id: 1st
season: 2026
current_date: 2026-08-05
current_phase: PRESEASON
current_week: 0
updated_at: 2025-11-09 23:48:05
```

✅ Database state correct after calendar advancement fix.

### Query Simulation - What SimulationExecutor Sees

**Actual Query Executed** (with bug):
```python
# current_season_year = 2025 (STALE!)
# preseason_season = 2025
preseason_events = [e for e in all_events if e['game_id'].startswith('preseason_2025_')]
# Result: [] (empty list)
```

**Expected Query** (after fix):
```python
# current_season_year = 2026 (FROM PhaseState!)
# preseason_season = 2026
preseason_events = [e for e in all_events if e['game_id'].startswith('preseason_2026_')]
# Result: 84 preseason games
```

---

## Architectural Analysis

### Current Architecture (BROKEN)

```
SeasonCycleController
├── season_year = 2026 (UPDATED via SeasonYearSynchronizer)
├── calendar.get_current_date() = 2026-08-05 (UPDATED via calendar.reset())
├── phase_state.phase = PRESEASON (UPDATED via transition handler)
└── simulation_executor
    └── season_year = 2025 (STALE! Never updated!)

PhaseState (Single Source of Truth?)
├── _phase = SeasonPhase.PRESEASON ✅
└── _season_year = ❌ DOES NOT EXIST
```

**Problem**: PhaseState claims to be "single source of truth" but doesn't track the season year, forcing consumers to use unreliable fallback logic.

### Target Architecture (FIXED)

```
SeasonCycleController
├── season_year = 2026 (SYNCHRONIZED)
├── calendar.get_current_date() = 2026-08-05 (SYNCHRONIZED)
├── phase_state
│   ├── phase = PRESEASON (SYNCHRONIZED)
│   └── season_year = 2026 (NEW! SYNCHRONIZED)
└── simulation_executor
    └── Uses phase_state.season_year = 2026 (RELIABLE!)

PhaseState (True Single Source of Truth)
├── _phase = SeasonPhase.PRESEASON ✅
└── _season_year = 2026 ✅ (NEW!)
```

**Solution**: PhaseState becomes true single source of truth by tracking both phase AND season year.

---

## Proposed Fixes

### Fix #1: Add `season_year` to PhaseState ⏳
**File**: `src/calendar/phase_state.py`
**Estimated Time**: 30 minutes

**Changes**:
```python
class PhaseState:
    def __init__(
        self,
        initial_phase: SeasonPhase = SeasonPhase.REGULAR_SEASON,
        season_year: int = 2025  # ← NEW PARAMETER
    ):
        self._phase = initial_phase
        self._season_year = season_year  # ← NEW ATTRIBUTE
        self._lock = threading.Lock()

    @property
    def season_year(self) -> int:
        """Get current season year (thread-safe)."""
        with self._lock:
            return self._season_year

    @season_year.setter
    def season_year(self, new_year: int) -> None:
        """Update season year (thread-safe)."""
        with self._lock:
            old_year = self._season_year
            self._season_year = new_year
            logger.info(f"PhaseState season_year updated: {old_year} → {new_year}")

    def to_dict(self) -> dict:
        """Return dictionary representation."""
        with self._lock:
            return {
                "current_phase": self._phase.value.upper(),
                "season_year": self._season_year  # ← NEW KEY
            }
```

**Impact**: PhaseState now tracks season year, making `phase_info.get("season_year")` reliable.

### Fix #2: Update PhaseState During Transition ⏳
**File**: `src/season/season_cycle_controller.py` (line ~1935)
**Estimated Time**: 5 minutes

**Changes**:
```python
# In OffseasonToPreseasonHandler (after line 1935):

# Update PhaseState with new season year (FIX #2)
self.phase_state.season_year = self.season_year

if self.verbose_logging:
    print(f"[PHASE_STATE] Updated season_year to {self.season_year}")
```

**Impact**: PhaseState.season_year synchronized during transition.

### Fix #3: Simplify SimulationExecutor Query Logic ⏳
**File**: `src/calendar/simulation_executor.py` (lines 507-519)
**Estimated Time**: 15 minutes

**Current Code** (BROKEN):
```python
phase_info = self.calendar.get_phase_info()
current_phase = phase_info.get("current_phase", "").lower()
current_date = self.calendar.get_current_date()

if current_phase == "offseason":
    current_season_year = current_date.year
else:
    current_season_year = phase_info.get("season_year", self.season_year)  # ❌ UNRELIABLE

preseason_season = current_season_year + 1 if current_phase == "offseason" else current_season_year
```

**New Code** (FIXED):
```python
phase_info = self.calendar.get_phase_info()
current_phase = phase_info.get("current_phase", "").lower()

# SIMPLIFIED: Always get season_year from PhaseState (single source of truth)
current_season_year = phase_info.get("season_year")

if current_season_year is None:
    # Fallback only for legacy/test scenarios
    current_date = self.calendar.get_current_date()
    current_season_year = current_date.year
    logger.warning(
        f"PhaseState missing season_year, falling back to calendar year: {current_season_year}"
    )

# Calculate preseason year (offseason looks forward, other phases use current)
preseason_season = current_season_year + 1 if current_phase == "offseason" else current_season_year
```

**Impact**: Reliable season year from PhaseState, clear fallback logging for debugging.

### Fix #4: Update SimulationExecutor Initialization ⏳
**File**: `src/calendar/simulation_executor.py` (lines 1-100)
**Estimated Time**: 5 minutes

**Changes**:
```python
def __init__(
    self,
    calendar: CalendarComponent,
    database_path: str,
    dynasty_id: str,
    enable_persistence: bool = True,
    verbose_logging: bool = False
):
    # ... existing code ...

    # Initialize season_year from PhaseState (not hardcoded!)
    phase_info = self.calendar.get_phase_info()
    self.season_year = phase_info.get("season_year", 2025)  # ← READ FROM PhaseState

    if verbose_logging:
        print(f"[SIMULATION_EXECUTOR] Initialized with season_year={self.season_year}")
```

**Impact**: SimulationExecutor starts with correct season year from PhaseState.

### Fix #5: Audit Documentation 📝
**File**: `docs/milestone_1/season_transition_audit.md`
**Estimated Time**: 10 minutes (THIS FILE!)

**Status**: ✅ COMPLETE

---

## Testing Plan

### Test Case 1: Fresh Season 2 Start
**Scenario**: Clean Season 1 → Season 2 transition

**Steps**:
1. Complete Season 1 (2025) through Super Bowl
2. Advance through offseason
3. Verify calendar jumps to Aug 5, 2026
4. Verify PhaseState.season_year = 2026
5. Simulate first preseason day
6. Verify games are detected and simulated

**Expected Results**:
- ✅ Calendar date: 2026-08-05
- ✅ PhaseState.season_year: 2026
- ✅ Query: `preseason_2026_*`
- ✅ Games found: 5+ events
- ✅ Games simulated with results

### Test Case 2: Multi-Year Dynasty (Years 1→2→3)
**Scenario**: Verify fixes work across multiple seasons

**Steps**:
1. Simulate complete Year 1 (2025)
2. Transition to Year 2 (2026) - verify game detection
3. Simulate complete Year 2 (2026)
4. Transition to Year 3 (2027) - verify game detection
5. Verify PhaseState.season_year advances correctly

**Expected Results**:
- ✅ Year 1 → Year 2: Games detected in 2026
- ✅ Year 2 → Year 3: Games detected in 2027
- ✅ PhaseState.season_year: 2025 → 2026 → 2027

### Test Case 3: SimulationExecutor Robustness
**Scenario**: Test fallback logic when PhaseState missing (backwards compatibility)

**Steps**:
1. Create SimulationExecutor with mock PhaseState (no season_year)
2. Verify fallback to calendar year works
3. Verify warning logged

**Expected Results**:
- ✅ Falls back to `calendar.get_current_date().year`
- ✅ Warning logged: "PhaseState missing season_year, falling back..."
- ✅ Games still detected (graceful degradation)

### Regression Testing
**Files to Test**:
- ✅ `test_2026_game_simulation.py` (existing test)
- ✅ Interactive season simulation UI
- ✅ Offseason system integration
- ✅ Playoff system integration

---

## Related Issues

### Issue 1: `_initialize_next_season()` Deprecated Method
**File**: `src/season/season_cycle_controller.py` (line 2858)
**Status**: ⚠️ Not causing active bugs but should be removed

**Problem**: Contains deprecated code with known bug (missing `season` parameter in `dynasty_update_state()` call at line ~2927).

**Reason Not Fixed**: Method is unused (transition system handles initialization).

**Recommendation**: Remove in future cleanup sprint.

### Issue 2: EventDatabaseAPI_DEPRECATED Performance
**File**: `src/events/event_database_api.py`
**Status**: ⚠️ Performance impact but functionally correct after Fix B

**Problem**: Deprecated wrapper adds 5x query overhead in some paths.

**Recommendation**: Migrate all callers to `UnifiedDatabaseAPI` and remove deprecated wrapper.

---

## Appendix: Code Locations

### Files Modified (Completed Fixes)
1. `src/season/season_cycle_controller.py` (lines 1917-1937) - Calendar advancement
2. `src/events/event_database_api.py` (lines 1487-1497) - Event query optimization
3. Database `dynasty_state` table - Cleanup of duplicate records

### Files To Modify (Pending Fixes)
1. `src/calendar/phase_state.py` - Add season_year attribute
2. `src/season/season_cycle_controller.py` (line ~1935) - Update PhaseState during transition
3. `src/calendar/simulation_executor.py` (lines 507-519) - Simplify query logic
4. `src/calendar/simulation_executor.py` (lines 1-100) - Update initialization

### Key Database Tables
- `events` - Game events with `game_id` format: `{phase}_{year}_*`
- `dynasty_state` - Persistent dynasty state with `season`, `current_date`, `current_phase`

### Related Documentation
- `docs/plans/full_season_simulation_plan.md` - Season cycle architecture
- `docs/architecture/play_engine.md` - Core system design
- `docs/plans/statistics_preservation.md` - Season year tracking system

---

## Conclusion

The root cause of Season 2 game detection failure is a **missing `season_year` attribute in PhaseState** that causes SimulationExecutor to query for the wrong season year. The 5-part fix plan will:

1. Make PhaseState a true single source of truth (phase + season year)
2. Synchronize PhaseState.season_year during transitions
3. Simplify query logic to use reliable PhaseState values
4. Provide graceful fallback with clear logging

**Estimated Total Implementation Time**: ~65 minutes

**Risk Level**: Low - All changes are additive with backwards compatibility

**Test Coverage**: 3 test cases + regression suite

---

**Audit Completed**: 2025-11-09
**Next Steps**: Implement Fix #1-4 in order, then run full test suite
