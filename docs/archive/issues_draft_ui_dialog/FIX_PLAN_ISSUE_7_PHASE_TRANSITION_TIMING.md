# Fix Plan: Issue #7 - Phase Transition Detection After Execution

**Priority**: LOW
**Complexity**: Low
**Estimated Time**: 2-3 hours
**Risk Level**: LOW
**Recommendation**: **IMPLEMENT** - Simple fix with moderate benefit

## Problem Statement

### Current Behavior
Phase transitions are detected AFTER the entire week has been simulated:

```python
def advance_week(self) -> Dict[str, Any]:
    # Simulate all 7 days
    for day in range(7):
        self._simulate_day()

    # Check for phase transition AFTER all days complete
    if self._backend.has_phase_transition_occurred():
        return {'phase_transition': True}
```

### Impact
- **Delayed Detection**: Week completes, then discovers it transitioned 3 days ago
- **No Mid-Week Stop**: Cannot stop week early when phase changes
- **UI Confusion**: User sees "Week completed" but actually entered new phase mid-week
- **Missed Opportunity**: Could show "Season Ended!" immediately on last game, not 4 days later
- **Log Confusion**: Logs show "advancing in Regular Season" but already in Playoffs

### Example Scenario
```
Current Phase: Regular Season, Week 18
Current Date: January 5, 2026

Day 1 (Jan 6): Simulate games ✅
Day 2 (Jan 7): Last regular season game ✅
    → Phase transition: Regular Season → Playoffs
Day 3 (Jan 8): Advance (but should stop!) ❌
Day 4 (Jan 9): Advance (still simulating!) ❌
Day 5 (Jan 10): Advance ❌
Day 6 (Jan 11): Advance ❌
Day 7 (Jan 12): Advance ❌
    → Week ends
    → Check phase: Oh, we're in playoffs now!

Result: Simulated 5 extra days in new phase without notifying user
```

### Root Cause
`SeasonCycleController.advance_day()` doesn't check for phase transition after each day - only checked at end of week loop by caller:

```python
# In SeasonCycleController
def advance_day(self):
    """Advance one day - no phase transition check."""
    self._current_date = self._calendar.advance_day()
    self._execute_today_events()
    # Missing: check if phase just changed
```

## Solution Architecture

### Overview
Check for phase transitions after each day simulation and return result immediately. This allows caller to detect transition mid-week and handle appropriately (show dialog, stop simulation, etc.).

### Design Decision: Return Phase Status from advance_day()

**Current Signature**:
```python
def advance_day(self) -> None:
    """Advance one day - no return value."""
    pass
```

**New Signature**:
```python
def advance_day(self) -> Dict[str, Any]:
    """
    Advance one day.

    Returns:
        dict: {
            'success': bool,
            'date': str,
            'phase': str,
            'phase_transition': bool,
            'previous_phase': Optional[str],
            'new_phase': Optional[str]
        }
    """
    pass
```

**Alternative: Raise Exception on Transition (Rejected)**
```python
class PhaseTransitionOccurred(Exception):
    pass

def advance_day(self):
    # ... simulation ...
    if phase_changed:
        raise PhaseTransitionOccurred(new_phase)
```

**Why Rejected**: Transitions aren't errors - they're expected events. Using exceptions for control flow is anti-pattern.

## Implementation Plan

### Phase 1: Backend Phase Detection (1 hour)

**File**: `src/season/season_cycle_controller.py`

**1.1 Add Phase Tracking**
```python
class SeasonCycleController:
    def __init__(self, ...):
        # ... existing init ...
        self._last_phase = None  # Track phase changes
        self._phase_changed_today = False

    def _initialize_phase_tracking(self):
        """Initialize phase tracking on first use."""
        current_state = self._dynasty_state_api.get_dynasty_state(self.dynasty_id)
        self._last_phase = current_state['current_phase']
```

**1.2 Modify advance_day() to Return Phase Info**
```python
def advance_day(self) -> Dict[str, Any]:
    """
    Advance simulation by one day.

    Returns:
        dict: {
            'success': bool,
            'date': str,              # Current date after advance
            'day_of_week': str,       # "Monday", "Tuesday", etc.
            'phase': str,             # Current phase after advance
            'week': int,              # Current week number
            'phase_transition': bool, # True if phase changed today
            'previous_phase': Optional[str],  # If transition occurred
            'new_phase': Optional[str]        # If transition occurred
        }
    """
    # Remember phase before simulation
    phase_before = self._get_current_phase()

    # Simulate the day
    self._advance_one_day_internal()

    # Check if phase changed
    phase_after = self._get_current_phase()
    phase_transitioned = (phase_after != phase_before)

    # Build result
    result = {
        'success': True,
        'date': self._get_current_date(),
        'day_of_week': self._get_day_of_week(),
        'phase': phase_after,
        'week': self._get_current_week(),
        'phase_transition': phase_transitioned,
        'previous_phase': phase_before if phase_transitioned else None,
        'new_phase': phase_after if phase_transitioned else None
    }

    if phase_transitioned:
        logger.info(
            f"Phase transition detected: {phase_before} → {phase_after} "
            f"on {result['date']}"
        )

    return result

def _advance_one_day_internal(self):
    """Internal method - actual day simulation logic."""
    # Existing advance_day() logic here
    self._current_date = self._calendar.advance_day(
        self.dynasty_id,
        self._current_date
    )
    self._execute_events_for_date(self._current_date)
    # Phase may have changed during event execution
```

**1.3 Update Phase Detection Method**
```python
def _get_current_phase(self) -> str:
    """Get current phase from database."""
    state = self._dynasty_state_api.get_dynasty_state(self.dynasty_id)
    return state['current_phase']

def has_phase_transitioned_since(self, previous_phase: str) -> bool:
    """Check if phase has changed since given phase."""
    current_phase = self._get_current_phase()
    return current_phase != previous_phase
```

### Phase 2: Update UI Controller (0.5 hours)

**File**: `ui/controllers/simulation_controller.py`

**2.1 Handle Phase Transition in simulate_day()**
```python
def simulate_day(self) -> Dict[str, Any]:
    """
    Simulate one day and detect phase transitions.

    Returns:
        dict: Day result including phase transition status
    """
    try:
        # Call backend (now returns dict)
        day_result = self._backend.advance_day()

        # Emit progress signal
        self.day_completed.emit(day_result)

        # Check for phase transition
        if day_result['phase_transition']:
            logger.info(
                f"Phase transition detected in UI layer: "
                f"{day_result['previous_phase']} → {day_result['new_phase']}"
            )
            # Emit special signal for phase transitions
            self.phase_transitioned.emit(day_result)

        # Update data model
        self._data_model.refresh()

        return day_result

    except Exception as e:
        logger.error(f"Day simulation failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'phase_transition': False
        }
```

**2.2 Update simulate_week() to Handle Mid-Week Transitions**
```python
def simulate_week(self) -> Dict[str, Any]:
    """
    Simulate up to 7 days, stopping early if phase transition occurs.

    Returns:
        dict: {
            'success': bool,
            'days_simulated': int,
            'phase_transition': bool,
            'milestone_detected': bool,
            'final_date': str,
            'final_phase': str
        }
    """
    phase_transition_occurred = False

    for day_num in range(7):
        # Check for milestone tomorrow (existing logic)
        if self._check_upcoming_milestone():
            return {
                'success': True,
                'days_simulated': day_num,
                'phase_transition': False,
                'milestone_detected': True,
                'stop_reason': 'milestone'
            }

        # Simulate day
        day_result = self.simulate_day()

        if not day_result['success']:
            return {
                'success': False,
                'days_simulated': day_num,
                'error': day_result.get('error')
            }

        # Check for phase transition
        if day_result['phase_transition']:
            phase_transition_occurred = True
            logger.info(f"Week stopped early - phase transition on day {day_num + 1}")
            return {
                'success': True,
                'days_simulated': day_num + 1,
                'phase_transition': True,
                'milestone_detected': False,
                'stop_reason': 'phase_transition',
                'previous_phase': day_result['previous_phase'],
                'new_phase': day_result['new_phase'],
                'transition_date': day_result['date']
            }

    # Week completed normally
    return {
        'success': True,
        'days_simulated': 7,
        'phase_transition': False,
        'milestone_detected': False,
        'final_date': self._data_model.state['current_date'],
        'final_phase': self._data_model.state['current_phase']
    }
```

**2.3 Add New Signal for Phase Transitions**
```python
class SimulationController(QObject):
    simulation_updated = Signal()
    day_completed = Signal(dict)
    phase_transitioned = Signal(dict)  # NEW signal
```

### Phase 3: UI Notification (0.5 hours)

**File**: `ui/main_window.py`

**3.1 Connect to Phase Transition Signal**
```python
def _connect_simulation_signals(self):
    """Connect to simulation controller signals."""
    self._simulation_controller.simulation_updated.connect(
        self._on_simulation_updated
    )
    self._simulation_controller.day_completed.connect(
        self._on_day_completed
    )
    self._simulation_controller.phase_transitioned.connect(
        self._on_phase_transitioned  # NEW
    )

@Slot(dict)
def _on_phase_transitioned(self, transition_info: Dict[str, Any]):
    """Handle phase transition notification."""
    previous_phase = transition_info['previous_phase']
    new_phase = transition_info['new_phase']
    transition_date = transition_info['date']

    # Show notification dialog
    title = "Phase Transition"
    message = (
        f"The simulation has entered a new phase!\n\n"
        f"Previous Phase: {self._format_phase_name(previous_phase)}\n"
        f"New Phase: {self._format_phase_name(new_phase)}\n"
        f"Transition Date: {transition_date}\n\n"
    )

    if new_phase == 'PLAYOFFS':
        message += (
            "The regular season has ended.\n"
            "Playoff seeding is now locked.\n\n"
            "Ready to simulate the playoffs?"
        )
    elif new_phase == 'OFFSEASON':
        message += (
            "The season has concluded.\n"
            "Offseason activities will begin soon.\n\n"
            "View final standings?"
        )

    QMessageBox.information(self, title, message)

    # Update UI to reflect new phase
    self._refresh_all_views()

def _format_phase_name(self, phase: str) -> str:
    """Format phase enum for display."""
    return phase.replace('_', ' ').title()
```

**3.2 Update simulate_week() Handler**
```python
def _sim_week(self):
    """Simulate week with phase transition handling."""
    result = self._simulation_controller.simulate_week()

    if not result['success']:
        QMessageBox.warning(
            self, "Simulation Error",
            f"Week simulation failed: {result.get('error', 'Unknown error')}"
        )
        return

    # Check stop reason
    if result.get('phase_transition'):
        # Phase transition dialog already shown by signal handler
        status_msg = (
            f"Week stopped early - entered {result['new_phase']} "
            f"on day {result['days_simulated']}"
        )
    elif result.get('milestone_detected'):
        status_msg = "Week stopped - milestone detected"
    else:
        status_msg = f"Week completed ({result['days_simulated']} days)"

    self.statusBar().showMessage(status_msg, 5000)
```

### Phase 4: Testing (1 hour)

**File**: `tests/season/test_phase_transition_detection.py` (NEW)

**4.1 Unit Tests**
```python
def test_advance_day_detects_phase_transition():
    """Verify advance_day() returns phase transition info."""
    controller = SeasonCycleController(...)

    # Setup: Last day of regular season
    controller._set_date("2026-01-07")  # Last game day
    controller._set_phase("REGULAR_SEASON")

    # Advance day (triggers phase transition to playoffs)
    result = controller.advance_day()

    # Verify transition detected
    assert result['phase_transition'] is True
    assert result['previous_phase'] == 'REGULAR_SEASON'
    assert result['new_phase'] == 'PLAYOFFS'
    assert result['date'] == "2026-01-08"

def test_advance_week_stops_on_phase_transition():
    """Verify week simulation stops when phase changes."""
    controller = SeasonCycleController(...)

    # Setup: 3 days before end of regular season
    controller._set_date("2026-01-05")
    controller._set_phase("REGULAR_SEASON")

    # Simulate week
    result = controller.advance_week()

    # Verify stopped early (should stop on Jan 8 when playoffs start)
    assert result['days_simulated'] == 3  # Only 3 days, not 7
    assert result['phase_transition'] is True
    assert result['stop_reason'] == 'phase_transition'
    assert controller.current_date == "2026-01-08"

def test_no_false_positives():
    """Verify no phase transition detected during normal week."""
    controller = SeasonCycleController(...)

    # Setup: Middle of regular season
    controller._set_date("2025-09-15")
    controller._set_phase("REGULAR_SEASON")

    # Simulate week
    result = controller.advance_week()

    # Verify no transition
    assert result['phase_transition'] is False
    assert result['days_simulated'] == 7  # Full week
    assert controller.current_phase == "REGULAR_SEASON"  # Same phase
```

**4.2 Integration Test**
```python
def test_ui_receives_phase_transition_signal(qtbot, simulation_controller):
    """Verify UI layer receives phase transition signal."""
    signal_received = False
    transition_info = {}

    def on_transition(info):
        nonlocal signal_received, transition_info
        signal_received = True
        transition_info = info

    simulation_controller.phase_transitioned.connect(on_transition)

    # Setup phase transition scenario
    # ... setup code ...

    # Simulate until transition
    simulation_controller.simulate_week()

    # Verify signal fired
    assert signal_received
    assert transition_info['phase_transition'] is True
    assert transition_info['new_phase'] == 'PLAYOFFS'
```

## Performance Impact

### Overhead
- **Phase Check**: 1 database query per day (~0.5ms)
- **String Comparison**: `phase_before != phase_after` (~0.001ms)
- **Dict Construction**: Building result dict (~0.01ms)

**Total Per Day**: ~0.5ms
**Per Week**: ~3.5ms (~0.1% of 3000ms simulation)

**Verdict**: Negligible performance impact.

## Risk Assessment

### Low Risks
- Simple string comparison for phase detection
- No breaking changes to existing API (return value added, not modified)
- Phase transitions rare (2-3 per season)

### Mitigation
- **Backward Compatibility**: Old code ignoring return value still works
- **Defensive Coding**: Check `'phase_transition' in result` before accessing
- **Logging**: Extensive logging for debugging

## Dependencies

### Prerequisites
- None (uses existing infrastructure)

### Synergies with Other Fixes
- **Issue #5 (Progressive UI Updates)**: Can emit phase transition via same signal mechanism
- **Issue #1 (Incremental Persistence)**: Phase transition day auto-checkpointed

## Implementation Timeline

| Phase | Time | Description |
|-------|------|-------------|
| 1. Backend Detection | 1h | Add phase tracking, modify advance_day() |
| 2. UI Controller | 0.5h | Handle transitions in simulate_week() |
| 3. UI Notification | 0.5h | Show dialog on transition |
| 4. Testing | 1h | Unit + integration tests |
| **Total** | **3h** | **~1 day** |

## Acceptance Criteria

1. ✅ `advance_day()` returns dict with phase info
2. ✅ Phase transition detected on day it occurs
3. ✅ `simulate_week()` stops immediately when phase changes
4. ✅ UI shows notification dialog on phase transition
5. ✅ Status bar displays "Phase changed" message
6. ✅ No false positives (normal weeks don't trigger)
7. ✅ Performance overhead <1% of simulation time
8. ✅ All tests pass (unit + integration)
9. ✅ Backward compatible with existing code

## User Experience Improvements

### Before Fix
```
User: *clicks "Simulate Week"*
UI: "Week completed"
User: "Huh, why am I in playoffs now? When did that happen?"
```

### After Fix
```
User: *clicks "Simulate Week"*
UI: *after 3 days* "Phase Transition!
     Regular Season → Playoffs
     Transition Date: January 8, 2026

     The regular season has ended.
     Playoff seeding is now locked."
User: "Perfect! Let me check the bracket."
```

## Future Enhancements

- **Transition Animation**: Smooth visual transition between phases
- **Phase Summary**: Show season stats before transitioning
- **Auto-Actions**: Offer to run playoff seeding automatically
- **Phase History**: Track all phase transitions in database

## References

- **Phase Management**: `src/season/season_cycle_controller.py:200-450`
- **Dynasty State**: `src/database/dynasty_state_api.py`
- **Similar Pattern**: Draft dialog detects pick transitions (round/pick number)
- **Qt Signals**: `phase_transitioned` follows same pattern as `simulation_updated`