# Fix Plan: Issue #3 - Add Cancellation Support

**Issue**: No Cancellation Support for Long Simulations
**Severity**: HIGH
**Priority**: P3 (Implement After Mileston Detection Refactor)
**Certainty Score**: 90/100
**Estimated Effort**: 3-5 days (~250 lines of code)

---

## Problem Statement

Once user clicks "Sim Week", they MUST wait for completion. No way to cancel mid-week simulation, even if they made a mistake or the simulation is taking too long.

**Evidence**:
- `ui/main_window.py` line 647: `result = self.simulation_controller.advance_week()` BLOCKS UI
- No QThread usage (all simulation runs on main thread)
- No cancellation token or interrupt mechanism
- Only example: `_sim_to_phase_end()` uses `QProgressDialog.wasCanceled()` (lines 727-729)

**User Impact**: MEDIUM-HIGH
- Can't cancel if clicked wrong button
- Can't cancel if simulation slower than expected
- Can't cancel if realized they're in wrong phase/date
- App feels unresponsive (frozen for 3-5 seconds)

---

## Root Cause Analysis

### Current Architecture
```
MainWindow._sim_week() {
    result = simulation_controller.advance_week()  // BLOCKS UI!
    // No cancellation, no escape hatch
    show_completion_message()
}
```

### Why This Design Exists
1. **Simplicity**: Single-threaded, no concurrency complexity
2. **SQLite**: Database connections not thread-safe by default
3. **Qt Default**: Qt widgets run on main thread
4. **Historical**: Cancellation not prioritized in MVP

### Why It's Problematic
1. **Poor UX**: App feels frozen during simulation
2. **No user control**: Can't cancel mistakes
3. **Frustration**: Especially on slower hardware (10+ seconds)
4. **Professional feel**: Modern apps should allow cancellation

---

## Proposed Solution: QThread with Cancellation Token

### Overview
Run simulation in background QThread with cancellation token. Allow user to cancel via progress dialog.

### Architecture
```
User clicks "Sim Week"
  ↓
MainWindow: Show QProgressDialog with "Cancel" button
  ↓
Create WeekSimulationWorker (QObject, not QThread!)
Move worker to QThread
  ↓
Worker.run() {
    for day in range(7):
        if cancellation_token.is_cancelled():
            break  // Check cancellation before each day

        day_result = advance_day()
        emit progress_updated(day)  // Signal to main thread

        QThread.msleep(10)  // Allow cancellation to be processed
}
  ↓
Main thread updates progress dialog
User can click "Cancel" button → sets cancellation_token
  ↓
Worker detects cancellation, stops cleanly
Emit finished signal with partial results
```

### Benefits
- ✅ Responsive UI (progress dialog updates live)
- ✅ User control (can cancel at any time)
- ✅ Professional feel (modern UX pattern)
- ✅ Graceful cancellation (stops between days, not mid-day)

### Costs
- ❌ Threading complexity (race conditions, deadlocks)
- ❌ Database thread safety (need connection management)
- ❌ Testing complexity (threading bugs hard to reproduce)
- ❌ Implementation effort (~250 lines)

**Trade-off Assessment**: Worth it for better UX, but LOW priority (current UX acceptable for 3-5 second waits)

---

## Implementation Plan

### Phase 1: Create Cancellation Token (30 minutes)

**File**: `ui/utils/cancellation_token.py` (NEW)

```python
"""
Cancellation token for long-running operations.

Thread-safe token that can be checked by worker threads.
"""
import threading
from typing import Optional


class CancellationToken:
    """
    Thread-safe cancellation token.

    Example:
        token = CancellationToken()

        # In worker thread
        while not token.is_cancelled():
            do_work()

        # In main thread
        token.cancel()
    """

    def __init__(self):
        """Initialize uncancelled token."""
        self._cancelled = False
        self._lock = threading.Lock()
        self._message: Optional[str] = None

    def cancel(self, message: str = "Operation cancelled"):
        """
        Cancel the operation.

        Args:
            message: Cancellation reason (for logging)
        """
        with self._lock:
            self._cancelled = True
            self._message = message

    def is_cancelled(self) -> bool:
        """Check if operation cancelled."""
        with self._lock:
            return self._cancelled

    def get_message(self) -> Optional[str]:
        """Get cancellation message."""
        with self._lock:
            return self._message

    def reset(self):
        """Reset token to uncancelled state."""
        with self._lock:
            self._cancelled = False
            self._message = None
```

---

### Phase 2: Create Week Simulation Worker (2 hours)

**File**: `ui/workers/week_simulation_worker.py` (NEW)

```python
"""
Background worker for week simulation.

Runs simulation in separate thread, emits signals for progress updates.
"""
from PySide6.QtCore import QObject, Signal
from typing import Dict, Any, Optional
from ui.utils.cancellation_token import CancellationToken


class WeekSimulationWorker(QObject):
    """
    Worker that runs week simulation in background thread.

    Signals:
        progress_updated: (day_num, day_result) - Emitted after each day
        finished: (result_dict) - Emitted when simulation completes
        error: (error_message) - Emitted on exception
    """

    # Qt signals (thread-safe communication)
    progress_updated = Signal(int, dict)  # (day_num, day_result)
    finished = Signal(dict)  # (result_dict)
    error = Signal(str)  # (error_message)

    def __init__(
        self,
        simulation_controller,
        cancellation_token: CancellationToken
    ):
        """
        Initialize worker.

        Args:
            simulation_controller: SimulationController instance
            cancellation_token: Token to check for cancellation
        """
        super().__init__()
        self.controller = simulation_controller
        self.cancellation_token = cancellation_token

    def run(self):
        """
        Run week simulation (called when thread starts).

        Simulates up to 7 days, checking cancellation before each day.
        Emits progress signals after each day.
        """
        try:
            daily_results = []
            start_date = self.controller.get_current_date()

            # Simulate each day
            for day_num in range(7):
                # Check cancellation BEFORE simulating day
                if self.cancellation_token.is_cancelled():
                    # User cancelled - return partial results
                    self.finished.emit({
                        'success': True,
                        'cancelled': True,
                        'days_simulated': day_num,
                        'message': f"Cancelled after {day_num} days"
                    })
                    return

                # Simulate one day
                # CRITICAL: Database operations must be thread-safe!
                day_result = self.controller.advance_day()

                daily_results.append(day_result)

                # Emit progress signal (updates UI on main thread)
                self.progress_updated.emit(day_num + 1, day_result)

                # Check for early stopping conditions
                if day_result.get('milestone_detected') or day_result.get('phase_transition'):
                    break

            # Simulation complete (not cancelled)
            end_date = self.controller.get_current_date()

            self.finished.emit({
                'success': True,
                'cancelled': False,
                'days_simulated': len(daily_results),
                'start_date': start_date,
                'end_date': end_date,
                'results': daily_results
            })

        except Exception as e:
            # Error during simulation
            self.error.emit(f"Simulation error: {str(e)}")
```

---

### Phase 3: Update MainWindow to Use Threading (2 hours)

**File**: `ui/main_window.py`

**Replace `_sim_week()` method** (lines 635-704):
```python
def _sim_week(self):
    """
    Simulate one week with cancellation support.

    Shows progress dialog with cancel button.
    Runs simulation in background thread for responsive UI.
    """
    from PySide6.QtCore import QThread
    from PySide6.QtWidgets import QProgressDialog
    from ui.workers.week_simulation_worker import WeekSimulationWorker
    from ui.utils.cancellation_token import CancellationToken

    start_date_str = self.simulation_controller.get_current_date()

    # Create progress dialog with cancel button
    progress = QProgressDialog(
        "Simulating week...",
        "Cancel",
        0, 7,  # Min=0, Max=7 days
        self
    )
    progress.setWindowTitle("Week Simulation")
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)  # Show immediately
    progress.setValue(0)

    # Create cancellation token
    cancel_token = CancellationToken()

    # Connect cancel button to token
    progress.canceled.connect(lambda: cancel_token.cancel())

    # Create worker and thread
    worker = WeekSimulationWorker(
        self.simulation_controller,
        cancel_token
    )

    thread = QThread()
    worker.moveToThread(thread)

    # Connect signals
    thread.started.connect(worker.run)  # Start work when thread starts
    worker.progress_updated.connect(self._on_day_simulated)  # Update progress
    worker.finished.connect(lambda r: self._on_week_finished(r, progress, thread, worker))
    worker.error.connect(lambda e: self._on_week_error(e, progress, thread, worker))

    # Connect progress dialog value to worker
    worker.progress_updated.connect(lambda day, _: progress.setValue(day))

    # Start thread
    thread.start()

    # Progress dialog blocks here (modal) until simulation finishes
    # User can click "Cancel" button during this time


def _on_day_simulated(self, day_num: int, day_result: Dict[str, Any]):
    """
    Called after each day simulated (runs on main thread).

    Args:
        day_num: Day number (1-7)
        day_result: Result dict from advance_day()
    """
    # Update status bar
    games_played = day_result.get('games_played', 0)
    self.statusBar().showMessage(
        f"Day {day_num}/7: {games_played} games played",
        1000  # 1 second
    )

    # Optionally refresh standings after each day
    if games_played > 0:
        self._refresh_standings_view()


def _on_week_finished(
    self,
    result: Dict[str, Any],
    progress: QProgressDialog,
    thread: QThread,
    worker: WeekSimulationWorker
):
    """
    Called when simulation finishes (success or cancelled).

    Args:
        result: Simulation result dict
        progress: Progress dialog to close
        thread: Thread to stop
        worker: Worker to delete
    """
    # Close progress dialog
    progress.close()

    # Cleanup thread
    thread.quit()
    thread.wait()
    thread.deleteLater()
    worker.deleteLater()

    # Show result message
    if result.get('cancelled'):
        QMessageBox.information(
            self,
            "Simulation Cancelled",
            f"Simulation cancelled after {result['days_simulated']} days.\n\n"
            f"Calendar: {self._format_date(self.simulation_controller.get_current_date())}"
        )
    else:
        days_simulated = result['days_simulated']
        end_date = result['end_date']
        QMessageBox.information(
            self,
            "Week Complete",
            f"Simulated {days_simulated} days.\n\n"
            f"Calendar: {self._format_date(end_date)}"
        )

    # Refresh views
    self._refresh_views_after_simulation()


def _on_week_error(
    self,
    error_message: str,
    progress: QProgressDialog,
    thread: QThread,
    worker: WeekSimulationWorker
):
    """
    Called when simulation encounters error.

    Args:
        error_message: Error description
        progress: Progress dialog to close
        thread: Thread to stop
        worker: Worker to delete
    """
    # Close progress dialog
    progress.close()

    # Cleanup thread
    thread.quit()
    thread.wait()
    thread.deleteLater()
    worker.deleteLater()

    # Show error message
    QMessageBox.critical(
        self,
        "Simulation Error",
        f"An error occurred during simulation:\n\n{error_message}"
    )
```

---

### Phase 4: Ensure Database Thread Safety (1 hour)

**Problem**: SQLite connections created with `check_same_thread=True` (default) can't be used from worker thread.

**Solution**: Use connection pool OR pass connection to worker OR use signals for DB ops.

**Option 1: Use Existing Connection Pool** (PREFERRED)

**File**: `ui/controllers/simulation_controller.py`

**Modify `advance_day()` to use pooled connection**:
```python
def advance_day(self) -> Dict[str, Any]:
    """Advance one day (thread-safe via connection pool)."""

    # Get connection from pool (thread-safe)
    from src.database.connection_pool import ConnectionPool
    pool = ConnectionPool.get_instance()

    with pool.get_connection() as conn:
        # Use this connection for all database operations
        result = self.season_controller.advance_day(connection=conn)

        # Save state using same connection
        self._save_state_to_db(
            result['date'],
            result['current_phase'],
            self.get_current_week(),
            connection=conn  # NEW: Pass connection
        )

    return result
```

**Why This Works**:
- ConnectionPool already thread-safe (uses `threading.Lock()`)
- Each worker thread gets its own connection
- No shared state between threads

---

### Phase 5: Add Tests (1 day)

**File**: `tests/ui/test_week_simulation_cancellation.py` (NEW)

```python
class TestWeekSimulationCancellation:
    """Test cancellation of week simulation."""

    def test_cancellation_token(self):
        """Verify cancellation token works."""
        token = CancellationToken()

        assert not token.is_cancelled()

        token.cancel("Test cancellation")

        assert token.is_cancelled()
        assert token.get_message() == "Test cancellation"


    def test_worker_stops_on_cancellation(self, qtbot):
        """Verify worker stops when token cancelled."""
        controller = SimulationController(...)
        token = CancellationToken()

        worker = WeekSimulationWorker(controller, token)

        # Track progress updates
        progress_updates = []
        worker.progress_updated.connect(lambda day, _: progress_updates.append(day))

        # Track finished signal
        finished_results = []
        worker.finished.connect(lambda r: finished_results.append(r))

        # Cancel after 3 days
        def cancel_after_3_days(day, _):
            if day == 3:
                token.cancel()

        worker.progress_updated.connect(cancel_after_3_days)

        # Start worker in thread
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        thread.start()

        # Wait for completion
        qtbot.waitUntil(lambda: len(finished_results) > 0, timeout=10000)

        # Verify stopped at 3 days
        assert len(progress_updates) == 3
        assert finished_results[0]['cancelled'] is True
        assert finished_results[0]['days_simulated'] == 3

        # Cleanup
        thread.quit()
        thread.wait()


    def test_progress_dialog_shows_progress(self, qtbot):
        """Verify progress dialog updates as days simulate."""
        main_window = MainWindow(...)

        # Mock simulation to emit progress signals
        with patch.object(main_window.simulation_controller, 'advance_day') as mock_day:
            mock_day.return_value = {'success': True, 'games_played': 5}

            # Start simulation
            main_window._sim_week()

            # Progress dialog should show
            # (Hard to test modal dialogs, may need to mock)
```

---

## Database Thread Safety Considerations

### Current Issues
1. **SQLite Default**: Connections created with `check_same_thread=True`
2. **Shared State**: SimulationController has in-memory cache
3. **Signal Timing**: Signals emitted from worker thread → main thread

### Solutions

**1. Use Connection Pool** (IMPLEMENTED in Phase 4)
- Each thread gets its own connection
- Pool handles thread safety with locks

**2. Use Qt Signals for DB Operations**
- Worker emits `save_state_requested` signal
- Main thread handles actual database write
- Slower but safer (no threading issues)

**3. Disable Thread Check** (NOT RECOMMENDED)
```python
conn = sqlite3.connect(db_path, check_same_thread=False)
```
- Allows connection use from any thread
- Risky (SQLite not fully thread-safe)
- Can cause corruption if not careful

**Recommendation**: Use Connection Pool (Option 1)

---

## Performance Impact

**Before**:
- Main thread blocked: 2.5 seconds
- UI frozen: 2.5 seconds
- User can't interact: 2.5 seconds

**After**:
- Main thread blocked: 0 seconds (background thread)
- UI responsive: Entire time
- Progress updates: Every ~300ms (per day)
- Overhead: ~50ms (thread creation + signals)
- Total: 2.55 seconds (~2% slower, barely noticeable)

**Trade-off**: 2% slower for MUCH better UX (worth it!)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Thread race conditions | HIGH | Use connection pool, thorough testing |
| Database corruption | CRITICAL | Use transactions, WAL mode |
| Deadlocks | HIGH | Avoid nested locks, use timeouts |
| Memory leaks | MEDIUM | Properly cleanup threads (deleteLater) |
| Signal ordering issues | MEDIUM | Use Qt::QueuedConnection explicitly |

---

## Alternative Approaches Considered

### Alternative 1: QTimer-based Cancellation (REJECTED)
```python
# Simulate one day at a time with QTimer
QTimer.singleShot(100, lambda: self._simulate_next_day())
```
**Why Rejected**: Awkward control flow, state management complex

### Alternative 2: QtConcurrent::run() (REJECTED)
```python
QtConcurrent.run(self.simulation_controller.advance_week)
```
**Why Rejected**: No progress updates, no fine-grained cancellation

### Alternative 3: asyncio/async-await (REJECTED)
```python
async def advance_week():
    for day in range(7):
        await advance_day()
```
**Why Rejected**: Python asyncio doesn't play well with Qt event loop

**Chosen Approach**: QThread + Signals (standard Qt pattern)

---

## Success Metrics

1. **Responsive UI**: Main thread never blocks >100ms
2. **Clean cancellation**: Stops between days (not mid-day)
3. **Progress updates**: UI refreshes every ~300ms
4. **No crashes**: Zero database corruption from threading
5. **User satisfaction**: Positive feedback on cancellation feature

---

## Rollback Plan

If threading causes critical issues:

1. **Immediate**: Revert to old single-threaded implementation
2. **Feature Flag**: Disable threading via config flag
3. **Fallback**: Keep old `_sim_week_blocking()` method as backup

---

## Estimated Timeline

| Phase | Duration | Blocker |
|-------|----------|---------|
| Phase 1: Cancellation token | 30 min | None |
| Phase 2: Worker class | 2 hours | Phase 1 |
| Phase 3: MainWindow integration | 2 hours | Phase 2 |
| Phase 4: Thread safety | 1 hour | Phase 2 |
| Phase 5: Testing | 1 day | All phases |
| **Total** | **3 days** | - |

**Calendar Days**: 3-5 days (with testing, review, and bugfixes)

---

**Status**: Deferred (implement after Issue #1 and #2)
**Priority**: P3 (nice-to-have, not critical)
**Approval Required**: Lead Developer, QA Lead
**Certainty Score**: 90/100 (threading is always tricky)