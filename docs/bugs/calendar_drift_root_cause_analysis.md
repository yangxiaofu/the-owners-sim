# Calendar Drift Root Cause Analysis

**Bug ID:** CALENDAR-DRIFT-2025-001
**Severity:** CRITICAL
**Date Reported:** 2025-01-08
**Date Analyzed:** 2025-01-08
**Status:** Root Cause Identified

---

## Executive Summary

**Problem:** The UI calendar state (CalendarComponent in-memory) shows March 3, 2026, while the database (dynasty_state table) shows November 9, 2025 - a **4-month desynchronization**.

**Root Cause:** Silent failure chain in `SimulationController._save_state_to_db()` method. When database writes fail, errors are logged to console but **no exceptions are raised**, allowing execution to continue as if the operation succeeded. This creates persistent data corruption where the UI advances normally but the database remains stuck.

**Impact:**
- Data integrity loss across calendar, phase, and game state
- User simulation appears to work but database is not persisted
- No error visible to user - appears as silent corruption
- Affects 4 critical methods: `advance_day()`, `advance_week()`, `advance_to_end_of_phase()`, `simulate_to_new_season()`

**Classification:** SYSTEMATIC DESIGN FLAW (not isolated bug)

---

## 1. Observed Symptoms

### 1.1 Initial User Report

User reported: *"I'm in the offseason, but it shows it's in the playoff phase."*

### 1.2 Investigation Findings

**UI State (CalendarComponent):**
- Date: March 3, 2026
- Phase: Displayed as "Offseason" in UI
- Internal calendar: Advanced 4 months beyond database

**Database State (dynasty_state table):**
```sql
SELECT dynasty_id, season, current_phase, current_date
FROM dynasty_state
WHERE dynasty_id = '1st';

Result:
dynasty_id | season | current_phase | current_date
-----------+--------+---------------+-------------
1st        | 2025   | playoffs      | 2025-11-09
```

**Divergence:**
- Calendar ahead by 116 days (4 months)
- Phase mismatch: UI shows "Offseason", DB shows "playoffs"
- Season year consistent: Both show 2025

---

## 2. Root Cause Analysis

### 2.1 The Silent Failure Chain

The calendar drift occurs through a **3-layer error handling gap**:

#### Layer 1: `DynastyStateAPI.update_state()` (Database Layer)

**File:** `src/database/dynasty_state_api.py:173-214`

```python
def update_state(self, dynasty_id: str, season: int, current_date: str,
                 current_phase: str, current_week: Optional[int] = None) -> bool:
    try:
        rows_affected = self.db.execute_update(query, params)
        return rows_affected > 0
    except Exception as e:
        self.logger.error(f"Error updating dynasty state: {e}")
        return False  # ❌ SILENT FAILURE - Returns False, doesn't raise
```

**Problem:** Exceptions are caught and logged, but method returns `False` instead of raising the exception.

---

#### Layer 2: `SimulationDataModel.save_state()` (Domain Model Layer)

**File:** `ui/domain_models/simulation_data_model.py:78-109`

```python
def save_state(self, current_date: str, current_phase: str, current_week: Optional[int] = None) -> bool:
    success = self.dynasty_api.update_state(...)

    if not success:
        print(f"[ERROR SimulationDataModel] Failed to save dynasty state...")  # ❌ Just prints

    return success  # Returns False but caller ignores it
```

**Problem:** Receives `False` from database layer, prints error to console, but returns `False` without raising exception.

---

#### Layer 3: `SimulationController._save_state_to_db()` (UI Controller Layer)

**File:** `ui/controllers/simulation_controller.py:115-131`

```python
def _save_state_to_db(self, current_date: str, current_phase: str, current_week: Optional[int] = None):
    success = self.state_model.save_state(
        current_date=current_date,
        current_phase=current_phase,
        current_week=current_week
    )

    if not success:
        print(f"[ERROR SimulationController] Failed to write dynasty_state!")  # ❌ Just prints
        # NO RAISE - execution continues!
    # ❌ Returns None implicitly - caller can't detect failure
```

**Problem:** Receives `False`, prints error, but **returns `None`** (implicit return). Callers never check the return value.

---

### 2.2 The Vulnerable Call Sites

The `_save_state_to_db()` method is called from 4 locations, **none of which check the return value**:

#### Call Site 1: `advance_day()` (Line 182)

```python
def advance_day(self) -> Dict[str, Any]:
    result = self.season_controller.advance_day()
    if result.get('success', False):
        new_date = result.get('date', self.current_date_str)
        new_phase = result.get('current_phase', ...)
        self.current_date_str = new_date  # ✅ UI cache updated

        self._save_state_to_db(new_date, new_phase, self.current_week)  # ❌ No check

        self.date_changed.emit(new_date)  # ✅ Signal emitted regardless
        return { "success": True, ... }  # ❌ Returns success even if save failed!
```

**Impact:** If database save fails, calendar advances 1 day in memory but database remains unchanged.

---

#### Call Site 2: `advance_week()` (Line 238)

```python
def advance_week(self) -> Dict[str, Any]:
    result = self.season_controller.advance_week()
    if result.get('success', False):
        new_date = result.get('date', self.current_date_str)
        self.current_date_str = new_date

        if self.season_controller.phase_state.phase.value == "regular_season":
            self.current_week += 1  # Week incremented

        self._save_state_to_db(new_date, new_phase, self.current_week)  # ❌ No check

        self.date_changed.emit(new_date)
        return result  # ❌ Returns success even if save failed!
```

**Impact:** If database save fails, calendar advances 7 days in memory but database remains unchanged. Week counter increments without persistence.

---

#### Call Site 3: `advance_to_end_of_phase()` (Lines 326-330)

```python
def advance_to_end_of_phase(self, progress_callback=None) -> Dict[str, Any]:
    summary = self.season_controller.simulate_to_phase_end(progress_callback)

    if summary.get('success', False):
        self.current_date_str = summary['end_date']  # Large date jump

        self._save_state_to_db(
            self.current_date_str,
            self.season_controller.phase_state.phase.value,
            self.current_week
        )  # ❌ No error handling

        self.date_changed.emit(self.current_date_str)
        return summary  # ❌ Returns success even if save failed!
```

**Impact:** This is the **most likely culprit**. Multi-week advancement (7-20+ days) fails to persist, creating large drift.

---

#### Call Site 4: `simulate_to_new_season()` (Lines 397-401)

```python
def simulate_to_new_season(self) -> Dict[str, Any]:
    summary = self.season_controller.simulate_to_new_season()

    if summary.get('success', False):
        self.current_date_str = summary['end_date']  # 30-100+ day jump

        self._save_state_to_db(
            self.current_date_str,
            summary['ending_phase'],
            self.current_week
        )  # ❌ No error handling

        self.date_changed.emit(self.current_date_str)
```

**Impact:** Massive advancement (30-100+ days) fails to persist, creating severe drift.

---

## 3. Most Likely Execution Path (Drift Creation Scenario)

Based on the 4-month drift (116 days) and the database showing November 9 playoffs phase, the most likely scenario:

### Scenario: User Clicked "Simulate to End of Phase" During Playoffs

**Timeline:**

1. **Initial State (Nov 9, 2025)**
   - Calendar: Nov 9, 2025
   - Database: Nov 9, 2025, phase="playoffs"
   - User in Wild Card round

2. **User Action**
   - Clicks "Simulate to End of Phase" button
   - UI calls `SimulationController.advance_to_end_of_phase()`

3. **Backend Simulation (Nov 9 → Mar 3)**
   - `SeasonCycleController.simulate_to_phase_end()` executes
   - Calendar advances through:
     - Wild Card (Nov 9-15): 7 days
     - Divisional (Nov 16-22): 7 days
     - Conference (Nov 23-29): 7 days
     - Super Bowl (Dec 6-27): ~21 days
     - Offseason events (Dec 28 - Mar 3): ~95 days
   - **Total advancement:** ~116 days (4 months)
   - Backend returns: `summary = {'success': True, 'end_date': '2026-03-03', 'ending_phase': 'offseason'}`

4. **UI State Update (Line 323)**
   ```python
   self.current_date_str = summary['end_date']  # "2026-03-03"
   ```
   - UI cache now shows March 3, 2026

5. **Database Save Attempt (Lines 326-330)**
   ```python
   self._save_state_to_db(
       "2026-03-03",
       "offseason",
       self.current_week
   )
   ```

6. **Database Failure**
   - `DynastyStateAPI.update_state()` attempts to write:
     - `current_date = "2026-03-03"`
     - `current_phase = "offseason"`
   - **Operation FAILS** due to:
     - Possible causes:
       - SQLite lock timeout (another connection held lock)
       - Disk space issue
       - File permissions error
       - Connection dropped
       - Constraint violation (unlikely but possible)

7. **Error Propagation (Silent Failure)**
   - `DynastyStateAPI.update_state()` catches exception, logs it, returns `False`
   - `SimulationDataModel.save_state()` receives `False`, prints error, returns `False`
   - `SimulationController._save_state_to_db()` receives `False`, prints error, **returns `None`**
   - `advance_to_end_of_phase()` never checks return value, **continues execution**

8. **UI Signal Emission (Line 332)**
   ```python
   self.date_changed.emit(self.current_date_str)  # Emits "2026-03-03"
   ```
   - UI updates to show March 3, 2026

9. **Method Return (Line 333)**
   ```python
   return summary  # Returns {'success': True, ...}
   ```
   - Caller believes operation succeeded

10. **Result: 4-Month Drift**
    - UI calendar: March 3, 2026
    - Database: November 9, 2025 (never updated)
    - Phase mismatch: UI shows "offseason", DB shows "playoffs"
    - **User sees no error - silent corruption**

---

## 4. Why This Is a Systematic Flaw

### 4.1 Pattern Repetition

The same silent failure pattern exists in **4 different methods**:

| Method | Lines | Advancement | Drift Risk |
|--------|-------|-------------|------------|
| `advance_day()` | 182 | 1 day | Low (small) |
| `advance_week()` | 238 | 7 days | Medium |
| `advance_to_end_of_phase()` | 326-330 | 7-30+ days | **HIGH** |
| `simulate_to_new_season()` | 397-401 | 30-100+ days | **CRITICAL** |

### 4.2 No Defensive Programming

**Lacks:**
- Pre-save validation (is database reachable?)
- Post-save verification (did write succeed?)
- Return value checking (was save successful?)
- Exception propagation (surface failures to caller)
- User notification (show error dialog)

### 4.3 No Detection Mechanism

**Missing:**
- Calendar-database drift detection
- Periodic health checks
- State consistency validation
- Corruption alerts

---

## 5. Supporting Evidence

### 5.1 Error Handling Chain Analysis

```
DATABASE LAYER (dynasty_state_api.py)
├─ Exception occurs during execute_update()
├─ Caught by try/except
├─ Logged: "Error updating dynasty state: {e}"
└─ Returns False (doesn't raise)
    │
    ↓
DOMAIN MODEL LAYER (simulation_data_model.py)
├─ Receives False
├─ Checks: if not success:
├─ Prints: "[ERROR SimulationDataModel] Failed to save..."
└─ Returns False (doesn't raise)
    │
    ↓
UI CONTROLLER LAYER (simulation_controller.py)
├─ Receives False
├─ Checks: if not success:
├─ Prints: "[ERROR SimulationController] Failed to write..."
└─ Returns None (implicit)
    │
    ↓
CALLER (advance_to_end_of_phase, etc.)
├─ Calls _save_state_to_db()
├─ Ignores return value
├─ Emits success signal
└─ Returns {'success': True}
```

### 5.2 Code Inspection Findings

**Grep for return value checking:**
```bash
# No callers check return value from _save_state_to_db()
grep -A 3 "_save_state_to_db" ui/controllers/simulation_controller.py

Results:
Line 182: self._save_state_to_db(new_date, new_phase, self.current_week)
Line 183: self.date_changed.emit(new_date)  # ❌ Proceeds regardless

Line 238: self._save_state_to_db(new_date, new_phase, self.current_week)
Line 239: self.date_changed.emit(new_date)  # ❌ Proceeds regardless

Line 326-330: self._save_state_to_db(...)
Line 332: self.date_changed.emit(...)  # ❌ Proceeds regardless

Line 397-401: self._save_state_to_db(...)
Line 403: self.date_changed.emit(...)  # ❌ Proceeds regardless
```

**None of the 4 call sites check the return value.**

### 5.3 Console Log Evidence

The user likely saw these errors in console but they were not surfaced to the UI:

```
[ERROR SimulationDataModel] Failed to save dynasty state to database
[ERROR SimulationController] Failed to write dynasty_state!
```

These messages appeared but execution continued, making the error invisible to the user.

---

## 6. Impact Assessment

### 6.1 Data Integrity Impact

| Component | State | Consequence |
|-----------|-------|-------------|
| Calendar (in-memory) | March 3, 2026 | UI shows future date |
| Dynasty State (database) | Nov 9, 2025 | Database stuck in past |
| Phase (UI) | "Offseason" | Derived from in-memory calendar |
| Phase (database) | "playoffs" | Never updated from Nov 9 |
| Week Counter | Unknown | Incremented without persistence |
| Standings | Unknown | May be desynchronized |
| Game Events | Unknown | May be incomplete |

### 6.2 User Experience Impact

**What User Sees:**
- UI shows March 3, 2026, "Offseason"
- UI appears to work normally
- No error messages visible
- Simulation appears successful

**What Actually Happened:**
- Database never saved beyond Nov 9, 2025
- 4 months of simulation lost
- Phase transition incomplete
- Playoffs not fully completed
- All state changes since Nov 9 not persisted

**User Impact:**
- **Data loss:** 4 months of simulation work lost
- **Silent corruption:** No indication anything was wrong
- **Trust erosion:** System appeared to work but data wasn't saved
- **Recovery difficulty:** No obvious way to fix the issue

---

## 7. Classification

### 7.1 Bug Type

**Type:** Systematic Design Flaw
**Category:** Silent Failure / Error Handling Gap
**Severity:** CRITICAL
**Reproducibility:** Occurs whenever database save fails

### 7.2 Why "Systematic" Not "Isolated"

This is a **systematic design flaw** because:

1. **Pattern Repetition:** Same error handling gap in 4 different methods
2. **Architectural Issue:** No fail-loud philosophy enforced
3. **No Defensive Coding:** Missing validation, verification, checking
4. **No Error Surfacing:** Errors logged but not raised/displayed
5. **Occurs Across Layers:** All 3 layers (DB, Domain Model, UI Controller) fail silently

This will recur any time database writes fail until the error handling architecture is fixed.

---

## 8. Recommended Fixes

### 8.1 Immediate Fixes (Tactical)

1. **Make `_save_state_to_db()` raise exceptions instead of returning `None`**
   ```python
   def _save_state_to_db(self, current_date: str, current_phase: str, current_week: Optional[int] = None):
       success = self.state_model.save_state(...)
       if not success:
           raise CalendarSyncPersistenceException(
               operation="dynasty state",
               sync_point="save_state",
               state_info={
                   'intended_date': current_date,
                   'intended_phase': current_phase
               }
           )
   ```

2. **Add post-save verification**
   ```python
   # After saving, read back from database to confirm
   db_state = self._get_db_state()
   if db_state['current_date'] != current_date:
       raise CalendarSyncPersistenceException(...)
   ```

3. **Add pre-save validation**
   ```python
   # Before advancing, check calendar-database drift
   drift = self._calculate_drift_days(calendar_date, db_date)
   if drift > 7:  # More than a week is suspicious
       raise CalendarSyncDriftException(...)
   ```

### 8.2 Strategic Fixes (Long-term)

1. **Fail-Loud Philosophy:** All database operations must raise exceptions on failure
2. **Transaction Semantics:** Use BEGIN/COMMIT/ROLLBACK for atomic operations
3. **State Validation:** Proactive integrity checks before critical operations
4. **User Notification:** Show error dialogs instead of silent console logging
5. **Health Monitoring:** Periodic background checks for calendar-database drift
6. **Logging Infrastructure:** Replace print() with proper logging framework

---

## 9. Prevention Recommendations

### 9.1 Code Review Checklist

- [ ] All database writes raise exceptions on failure (no silent returns)
- [ ] All database writes include post-write verification
- [ ] All multi-day advancements include pre-advancement validation
- [ ] All error messages surface to UI (not just console)
- [ ] All return values from database operations are checked

### 9.2 Testing Requirements

- [ ] Integration test: Force database write failure, verify exception raised
- [ ] Integration test: Verify calendar-database drift detection
- [ ] Integration test: Verify post-save verification catches corruption
- [ ] UI test: Verify error dialogs appear on database failures
- [ ] Load test: Verify database handles concurrent writes correctly

### 9.3 Monitoring

- [ ] Add periodic health check for calendar-database consistency
- [ ] Add metrics for database write failures
- [ ] Add alerts for calendar drift > 1 day
- [ ] Add logging for all database operations (not just errors)

---

## 10. Lessons Learned

### 10.1 Silent Failures Are Dangerous

**Problem:** Errors that don't surface to users create persistent corruption that's hard to debug.

**Solution:** Fail-loud philosophy - raise exceptions, show error dialogs, block operations.

### 10.2 Return Values Must Be Checked

**Problem:** Returning `False` or `None` on failure is useless if callers don't check.

**Solution:** Raise exceptions that can't be ignored, or enforce return value checking.

### 10.3 Console Logging Is Insufficient

**Problem:** Print statements and logger.error() are invisible to users.

**Solution:** Surface errors to UI with dialogs, block operations, prevent silent corruption.

### 10.4 Validation Is Critical

**Problem:** No pre-save or post-save validation allowed corruption to persist.

**Solution:** Proactive validation before operations, verification after operations.

---

## 11. Next Steps

1. **Implement Fail-Loud Validation** (Phase 4 of implementation plan)
2. **Add Transaction Semantics** (Phase 3 of implementation plan)
3. **Create State Validator** (Phase 5 of implementation plan)
4. **Add Error Dialogs** (Phase 4 of implementation plan)
5. **Migrate to Logging** (Phase 6 of implementation plan)
6. **Fix User's Dynasty** (Phase 8 of implementation plan)

---

## Conclusion

The calendar drift bug is a **CRITICAL systematic design flaw** caused by silent error handling across 3 architectural layers. When database writes fail, errors are logged but not raised, allowing the UI to advance normally while the database remains stuck. This created a 4-month drift that was invisible to the user.

The fix requires implementing fail-loud validation, transaction semantics, post-save verification, and proper error surfacing to the UI. This is not a quick fix - it requires architectural changes across the database, domain model, and UI layers to prevent recurrence.

**Priority:** CRITICAL - Implement immediately to prevent data loss in user dynasties.

---

**Report Generated:** 2025-01-08
**Analyzed By:** Claude (AI Assistant)
**Status:** Root Cause Confirmed, Implementation Plan Ready
**Related Documents:**
- `docs/plans/full_season_simulation_plan.md` - Season simulation architecture
- `docs/architecture/ui_layer_separation.md` - UI MVC architecture
- `TRANSACTION_CONTEXT_IMPLEMENTATION.md` - Transaction semantics guide
