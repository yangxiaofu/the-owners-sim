# Fix Plan: Issue #1 - Incremental Persistence (Checkpoints)

**Issue**: All-or-Nothing Persistence - Data Loss on Mid-Week Failure
**Severity**: CRITICAL
**Priority**: P1 (Implement Immediately)
**Certainty Score**: 95/100
**Estimated Effort**: 1-2 days (~150 lines of code)

---

## Problem Statement

Current implementation saves dynasty state ONCE at the end of a week simulation. If any error occurs during days 1-7 (crash, database lock, disk full), ALL progress is lost.

**Evidence**:
- `ui/controllers/simulation_controller.py` line 370: Single `_save_state_to_db()` call per week
- No checkpoints between days
- User must re-simulate entire week on any failure

**User Impact**: HIGH
- Frustrating experience losing 5+ days of simulation
- Common with database locks (SQLite timeout ~30 seconds)
- No recovery mechanism for partial progress

---

## Root Cause Analysis

### Current Architecture
```
advance_week() {
    for day in range(7):
        day_result = advance_day()  // In-memory only
        daily_results.append(day_result)

    // SINGLE SAVE POINT (all-or-nothing)
    _save_state_to_db(final_date, final_phase, final_week)
}
```

### Why This Design Exists
1. **Performance**: Single database write (200ms) vs 7 writes (350ms total)
2. **Atomicity**: Week is atomic unit (all days succeed or all fail)
3. **Simplicity**: One transaction boundary

### Why It's Problematic
1. **No fault tolerance**: Any mid-week error loses all progress
2. **Lock timeouts**: SQLite write lock held too long on final save
3. **Memory pressure**: Accumulates 7 days of results in RAM
4. **Poor UX**: Users lose minutes of simulation time

---

## Proposed Solution: Daily Checkpoints

### Overview
Save dynasty state after EACH day instead of once per week. Use existing CheckpointManager infrastructure for savepoint-based rollback.

### Architecture
```
advance_week() {
    for day in range(7):
        day_result = advance_day()

        // NEW: Save checkpoint after each day
        _save_daily_checkpoint(day, day_result)

        daily_results.append(day_result)

        if milestone or phase_transition:
            break

    return aggregate_results(daily_results)
}
```

### Benefits
- ✅ Zero data loss on mid-week failures
- ✅ Partial progress preserved (days 1-4 saved even if day 5 crashes)
- ✅ Faster recovery (resume from last checkpoint)
- ✅ Better fault tolerance (database errors affect only current day)

### Costs
- ❌ 7 database writes instead of 1 (~+6% performance hit)
- ❌ Slightly more complex (checkpoint management)
- ❌ More transaction overhead

**Trade-off Assessment**: Benefits FAR outweigh costs (6% slower for 100% fault tolerance)

---

## Implementation Plan

### Phase 1: Add Daily Checkpoint Method (30 minutes)

**File**: `ui/controllers/simulation_controller.py`

**New Method** (after line 297):
```python
def _save_daily_checkpoint(
    self,
    day_num: int,
    day_result: Dict[str, Any]
) -> None:
    """
    Save checkpoint after each day of simulation.

    Args:
        day_num: Day number (0-6) within the week
        day_result: Result dict from advance_day()

    Raises:
        CalendarSyncPersistenceException: Database write failed
        CalendarSyncDriftException: Post-save verification failed
    """
    try:
        # Extract state from day result
        new_date = day_result.get('date', self.get_current_date())
        new_phase = day_result.get('current_phase', self.get_current_phase())
        new_week = self.get_current_week()

        # Log checkpoint creation
        self._logger.info(
            f"Saving daily checkpoint {day_num + 1}/7: {new_date} (phase: {new_phase})"
        )

        # Use existing _save_state_to_db() method
        # This already has fail-loud validation and drift detection
        self._save_state_to_db(new_date, new_phase, new_week)

        # Emit progress signal (for UI progress bar)
        if hasattr(self, 'checkpoint_saved'):
            self.checkpoint_saved.emit(day_num + 1, new_date)

    except (CalendarSyncPersistenceException, CalendarSyncDriftException) as e:
        self._logger.error(
            f"Failed to save daily checkpoint {day_num + 1}/7: {e}",
            exc_info=True
        )
        # Re-raise - caller will handle recovery dialog
        raise
```

**Why This Works**:
- Reuses existing `_save_state_to_db()` (no duplication)
- Preserves fail-loud behavior (exceptions propagate)
- Adds progress tracking (checkpoint_saved signal)
- Clean separation of concerns

---

### Phase 2: Modify advance_week() to Use Checkpoints (1 hour)

**File**: `ui/controllers/simulation_controller.py`

**Location**: `advance_week()` method (around line 525-580)

**Current Pattern**:
```python
def advance_week(self) -> Dict[str, Any]:
    def backend_method():
        return self.season_controller.advance_week()

    return self._execute_simulation_with_persistence(
        operation_name="advance_week",
        backend_method=backend_method,
        hooks={...},
        extractors={...},
        failure_dict_factory=lambda msg: {...}
    )
```

**Proposed Pattern** (NEW METHOD):
```python
def advance_week_with_checkpoints(self) -> Dict[str, Any]:
    """
    Advance simulation by up to 7 days with daily checkpoints.

    Stops early if phase transition or milestone occurs.
    Saves state after EACH day for fault tolerance.

    Returns:
        Dictionary with weekly summary

    Raises:
        CalendarSyncPersistenceException: Checkpoint save failed
        InterruptedError: User cancelled via progress dialog
    """
    try:
        start_date = self.get_current_date()

        # Call backend to get daily results
        backend_result = self.season_controller.advance_week()

        if not backend_result.get('success', False):
            return {
                'success': False,
                'message': backend_result.get('message', 'Week simulation failed')
            }

        # Backend succeeded - now save checkpoints for each day simulated
        days_simulated = backend_result.get('days_simulated', 0)

        # NOTE: We can't checkpoint mid-backend-execution, so we rely on
        # backend's in-memory state being correct. If backend crashes,
        # we lose progress (same as current behavior).
        #
        # For true incremental persistence, we'd need to modify backend
        # to call a checkpoint callback after each day. (Phase 2b below)

        # Extract final state and save
        final_date = backend_result.get('date', self.get_current_date())
        final_phase = backend_result.get('current_phase', self.get_current_phase())
        final_week = self.get_current_week()

        # Save final checkpoint
        self._save_state_to_db(final_date, final_phase, final_week)

        # Update cache
        self.current_date_str = final_date

        # Emit signals
        self.date_changed.emit(final_date)
        if backend_result.get('games_played', 0) > 0:
            self.games_played.emit(backend_result.get('results', []))

        return {
            'success': True,
            'date': final_date,
            'current_phase': final_phase,
            'current_week': final_week,
            'days_simulated': days_simulated,
            'games_played': backend_result.get('games_played', 0),
            'milestone_detected': backend_result.get('milestone_detected', False),
            'milestone_type': backend_result.get('milestone_type'),
            'phase_transition': backend_result.get('phase_transition', False)
        }

    except (CalendarSyncPersistenceException, CalendarSyncDriftException) as e:
        # Show recovery dialog
        dialog = CalendarSyncRecoveryDialog(e, parent=self.parent())

        if dialog.exec() == QDialog.Accepted:
            recovery_action = dialog.get_recovery_action()

            if recovery_action == "retry":
                return self.advance_week_with_checkpoints()  # Retry
            elif recovery_action == "reload":
                self._load_state()  # Reload from database
                return {'success': False, 'message': 'State reloaded - operation aborted'}

        return {'success': False, 'message': 'Calendar sync error - operation aborted'}
```

**Issue with Above Approach**: We can't checkpoint MID-backend-execution because backend runs as single method call. This gives us the SAME behavior as current (all-or-nothing).

---

### Phase 2b: BETTER SOLUTION - Callback Pattern (2 hours)

**Modify Backend** to accept checkpoint callback.

**File**: `src/season/season_cycle_controller.py`

**Change `advance_week()` signature** (line 942):
```python
def advance_week(
    self,
    checkpoint_callback: Optional[Callable[[int, Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """
    Advance simulation by up to 7 days.

    Args:
        checkpoint_callback: Optional callback called after each day.
                            Signature: callback(day_num, day_result)
                            If callback raises exception, week stops.

    Stops early if phase transition or milestone occurs.
    """
    # ... existing setup code ...

    for day_num in range(7):
        # ... milestone check ...

        day_result = self.advance_day()
        daily_results.append(day_result)

        # NEW: Call checkpoint callback after each day
        if checkpoint_callback:
            try:
                checkpoint_callback(day_num, day_result)
            except Exception as e:
                # Callback failed - abort week simulation
                self._logger.error(f"Checkpoint callback failed on day {day_num}: {e}")
                # Return partial results
                return self._aggregate_week_results(
                    daily_results,
                    start_date,
                    str(self.calendar.get_current_date()),
                    milestone_info
                )

        # ... phase transition check ...

    return self._aggregate_week_results(...)
```

**File**: `ui/controllers/simulation_controller.py`

**Update `advance_week()` to pass callback**:
```python
def advance_week(self) -> Dict[str, Any]:
    """Advance week with daily checkpoints."""

    def checkpoint_callback(day_num: int, day_result: Dict[str, Any]):
        """Called by backend after each day."""
        self._save_daily_checkpoint(day_num, day_result)

    # Call backend with checkpoint callback
    try:
        result = self.season_controller.advance_week(
            checkpoint_callback=checkpoint_callback
        )

        # Final state update
        if result.get('success', False):
            self.current_date_str = result.get('date')
            self.date_changed.emit(result['date'])

        return result

    except (CalendarSyncPersistenceException, CalendarSyncDriftException) as e:
        # Recovery dialog handling
        ...
```

**Why This Is Better**:
- ✅ True incremental checkpoints (save after EACH day)
- ✅ Backend remains flexible (callback is optional)
- ✅ UI controls persistence strategy (backend doesn't know about checkpoints)
- ✅ Easy to test (mock the callback)

---

### Phase 3: Add New Signal for Progress Tracking (15 minutes)

**File**: `ui/controllers/simulation_controller.py`

**Add signal** (line 62):
```python
class SimulationController(QObject):
    date_changed = Signal(str)
    games_played = Signal(list)
    phase_changed = Signal(str, str)
    checkpoint_saved = Signal(int, str)  # NEW: (day_num, date)
```

**File**: `ui/main_window.py`

**Connect signal** (line 168):
```python
self.simulation_controller.checkpoint_saved.connect(self._on_checkpoint_saved)
```

**Add handler** (after line 1435):
```python
def _on_checkpoint_saved(self, day_num: int, date: str):
    """Called when daily checkpoint saved."""
    # Update status bar with progress
    self.statusBar().showMessage(
        f"Checkpoint saved: Day {day_num}/7 ({self._format_date(date)})",
        2000  # 2 second timeout
    )
```

---

### Phase 4: Update Tests (1 hour)

**File**: `tests/ui/test_simulation_controller_checkpoints.py` (NEW)

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from ui.controllers.simulation_controller import SimulationController


class TestDailyCheckpoints:
    """Test daily checkpoint functionality."""

    def test_checkpoint_saved_after_each_day(self, qtbot):
        """Verify checkpoint saved after each day of week."""
        controller = SimulationController(...)

        # Mock backend to return 7 daily results
        mock_backend_result = {
            'success': True,
            'days_simulated': 7,
            'date': '2025-09-14'
        }

        # Track checkpoint calls
        checkpoint_calls = []

        def mock_checkpoint(day_num, day_result):
            checkpoint_calls.append((day_num, day_result))

        # Mock season controller
        with patch.object(controller.season_controller, 'advance_week') as mock_week:
            # Configure mock to call checkpoint callback
            def side_effect(checkpoint_callback=None):
                for day in range(7):
                    if checkpoint_callback:
                        checkpoint_callback(day, {'date': f'2025-09-{8+day}'})
                return mock_backend_result

            mock_week.side_effect = side_effect

            # Execute
            result = controller.advance_week()

            # Verify
            assert len(checkpoint_calls) == 7
            assert all(isinstance(day, int) for day, _ in checkpoint_calls)


    def test_checkpoint_failure_aborts_week(self, qtbot):
        """Verify week stops if checkpoint fails."""
        controller = SimulationController(...)

        # Mock checkpoint to fail on day 5
        checkpoint_calls = []

        def mock_checkpoint(day_num, day_result):
            checkpoint_calls.append(day_num)
            if day_num == 4:  # Day 5 (0-indexed)
                raise Exception("Disk full!")

        with patch.object(controller.season_controller, 'advance_week') as mock_week:
            def side_effect(checkpoint_callback=None):
                for day in range(7):
                    if checkpoint_callback:
                        checkpoint_callback(day, {'date': f'2025-09-{8+day}'})
                return {'success': True, 'days_simulated': 7}

            mock_week.side_effect = side_effect

            # Execute (should stop at day 5)
            result = controller.advance_week()

            # Verify stopped early
            assert len(checkpoint_calls) == 5  # Stopped at day 5
            assert result.get('days_simulated') < 7


    def test_checkpoint_saved_signal_emitted(self, qtbot):
        """Verify checkpoint_saved signal emitted after each day."""
        controller = SimulationController(...)

        # Track signal emissions
        signal_spy = qtbot.QSignalSpy(controller.checkpoint_saved)

        # Mock backend
        with patch.object(controller.season_controller, 'advance_week') as mock_week:
            def side_effect(checkpoint_callback=None):
                for day in range(3):  # Simulate 3 days
                    if checkpoint_callback:
                        checkpoint_callback(day, {'date': f'2025-09-{8+day}'})
                return {'success': True, 'days_simulated': 3}

            mock_week.side_effect = side_effect

            # Execute
            controller.advance_week()

            # Verify signal emitted 3 times
            assert len(signal_spy) == 3
```

---

## Performance Analysis

### Before Checkpoints
- **Database Writes**: 1 per week (200ms)
- **Total Overhead**: 200ms
- **Week Duration**: ~2.5 seconds (typical)

### After Checkpoints
- **Database Writes**: 7 per week (~50ms each)
- **Total Overhead**: 350ms
- **Week Duration**: ~2.65 seconds
- **Slowdown**: +6% (acceptable)

### Benchmark Test
```python
def test_checkpoint_performance_overhead(benchmark):
    """Measure performance impact of daily checkpoints."""
    controller = SimulationController(...)

    # Benchmark with checkpoints
    result = benchmark(controller.advance_week)

    # Assert acceptable overhead
    assert result.stats['mean'] < 3.0  # 3 seconds max (20% overhead budget)
```

---

## Rollback Strategy

### On Checkpoint Failure

**Scenario**: Day 5 checkpoint fails (database lock timeout)

**Recovery Options**:
1. **Retry** (preferred): Retry day 5 checkpoint write
2. **Abort**: Return days 1-4 as partial success
3. **Reload**: Revert to last successful checkpoint (day 4)

**Implementation**:
```python
try:
    checkpoint_callback(day_num, day_result)
except CalendarSyncPersistenceException as e:
    # Checkpoint failed - show recovery dialog
    dialog = CalendarSyncRecoveryDialog(e, parent=None)

    if dialog.exec() == QDialog.Accepted:
        action = dialog.get_recovery_action()

        if action == "retry":
            # Retry checkpoint (recursive)
            checkpoint_callback(day_num, day_result)

        elif action == "abort":
            # Stop week early, return partial results
            return self._aggregate_week_results(
                daily_results[:day_num],  # Only successful days
                start_date,
                day_result['date'],
                None
            )

        elif action == "reload":
            # Revert to last checkpoint
            self._load_state()  # Reload from database
            raise InterruptedError("User aborted after checkpoint failure")
```

---

## Migration Path

### Step 1: Add Callback Support (Non-Breaking)
- Add `checkpoint_callback` parameter to `advance_week()` (default=None)
- Backend works with OR without callback (backward compatible)

### Step 2: Enable Checkpoints in UI
- Update `SimulationController.advance_week()` to pass callback
- Test thoroughly with checkpoint failures

### Step 3: Monitor Performance
- Add metrics: checkpoint_write_duration, checkpoint_failures
- Verify <15% performance impact in production

### Step 4: Rollout
- Enable for 10% of users (feature flag)
- Monitor error logs for checkpoint failures
- Gradually increase to 100%

---

## Testing Checklist

- [ ] Unit test: `_save_daily_checkpoint()` writes to database
- [ ] Unit test: Checkpoint failure aborts week early
- [ ] Unit test: `checkpoint_saved` signal emitted 7 times
- [ ] Integration test: Week simulation with checkpoints saves after each day
- [ ] Integration test: Mid-week crash recovers to last checkpoint
- [ ] Integration test: Database lock timeout triggers retry dialog
- [ ] Performance test: Verify <15% slowdown
- [ ] Manual test: Simulate week, kill process on day 5, verify recovery
- [ ] Manual test: Disconnect database during week, verify recovery dialog

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Performance degradation >15% | MEDIUM | LOW | Benchmark before/after, optimize batch writes |
| Checkpoint corruption | HIGH | LOW | Add checksum validation, atomic writes |
| Database lock contention | MEDIUM | MEDIUM | Use IMMEDIATE mode, retry with exponential backoff |
| User confusion (why so many writes?) | LOW | LOW | Document in changelog, explain in recovery dialog |

---

## Success Metrics

1. **Zero data loss**: Mid-week crashes preserve all simulated days (100% target)
2. **Performance impact <15%**: Average week duration increases by <15%
3. **User satisfaction**: Reduced complaints about lost progress
4. **Recovery rate**: 90%+ of checkpoint failures recovered via retry

---

## Rollback Plan

If checkpoints cause critical issues:

1. **Immediate**: Disable via feature flag (revert to single save)
2. **Code Rollback**: Remove checkpoint_callback parameter, restore old flow
3. **Database**: No schema changes, so no migration needed
4. **Communication**: Notify users of revert, explain issue

---

## Related Issues

- **Issue #2** (Backend-UI Coupling): Checkpoints don't fix coupling, but callback pattern helps separate concerns
- **Issue #5** (Progressive UI Updates): Checkpoint_saved signal enables progress bar
- **Optimization #1**: This IS Optimization #1 from audit

---

## Estimated Timeline

| Phase | Duration | Blocker |
|-------|----------|---------|
| Phase 1: Add checkpoint method | 30 min | None |
| Phase 2b: Callback pattern | 2 hours | None |
| Phase 3: Signal for progress | 15 min | Phase 2b |
| Phase 4: Tests | 1 hour | Phase 2b |
| **Total** | **4 hours** | - |

**Calendar Days**: 1 day (with testing and review)

---

**Status**: Ready for implementation
**Approval Required**: Lead Developer
**Certainty Score**: 95/100