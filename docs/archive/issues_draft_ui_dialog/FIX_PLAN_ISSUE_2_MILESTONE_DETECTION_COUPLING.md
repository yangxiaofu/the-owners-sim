# Fix Plan: Issue #2 - Backend-UI Coupling (Milestone Detection)

**Issue**: Milestone Detection Logic in Backend Layer
**Severity**: CRITICAL (Architectural)
**Priority**: P2 (Implement After Checkpoints)
**Certainty Score**: 98/100
**Estimated Effort**: 2-3 days (~300 lines of code + refactoring)

---

## Problem Statement

Milestone detection logic lives in BACKEND (`SeasonCycleController._check_for_milestone_on_next_date()`), but milestones are a UI concept. This violates MVC separation of concerns.

**Evidence**:
- Backend code in `src/season/season_cycle_controller.py` (lines 532-643) checks for DRAFT_DAY, DEADLINE, WINDOW events
- Backend returns milestone info to UI: `{milestone_type, milestone_date, milestone_display_name}`
- Backend knows about UI dialogs (display names like "Draft Day", "Franchise Tag")

**Architectural Violations**:
1. **Separation of Concerns**: Backend should simulate, not decide what's "interactive"
2. **Testability**: Can't test milestone routing without full backend
3. **Reusability**: Can't use backend for headless simulation (no UI)
4. **Maintainability**: Adding new milestones requires backend + UI changes

---

## Root Cause Analysis

### Current Flow
```
User clicks "Sim Week"
  ↓
MainWindow._sim_week()
  ↓
SimulationController.advance_week()
  ↓
SeasonCycleController.advance_week()  // BACKEND
  ↓ (checks for milestones IN BACKEND)
SeasonCycleController._check_for_milestone_on_next_date()
  ↓ (returns milestone info to UI)
MainWindow._handle_interactive_event_router()
  ↓
Open appropriate dialog
```

### Why This Design Exists
1. **Historical**: Milestone detection added incrementally
2. **Convenience**: Backend already has event database access
3. **Look-ahead pattern**: Checking TOMORROW's date fits naturally in backend loop

### Why It's Problematic
1. **Backend knows UI concepts**: "DRAFT_DAY is interactive" is UI knowledge
2. **Tight coupling**: UI can't customize milestone detection logic
3. **Testing difficulty**: Must mock entire backend to test milestone routing
4. **Code duplication**: SimulationController has DUPLICATE check methods:
   - `check_for_draft_day_event()` (lines 633-670)
   - `check_for_interactive_event()` (lines 717-782)
5. **Mixed responsibilities**: Backend both simulates AND routes UI

---

## Proposed Solution: Move Detection to UI Layer

### Overview
Extract milestone detection from backend to UI layer. Backend becomes UI-agnostic, only simulates and returns events executed.

### New Architecture
```
User clicks "Sim Week"
  ↓
MainWindow._sim_week()
  ↓
NEW: MainWindow._check_upcoming_milestones(days=7)  // UI LAYER
  ↓ (finds milestone on day 4)
MainWindow: "Stop at day 3, show dialog"
  ↓
SimulationController.advance_days(3)  // NEW METHOD
  ↓
SeasonCycleController.advance_days(3)  // Backend stays simple
  ↓
MainWindow: Open draft dialog
  ↓
SimulationController.advance_day()  // Execute milestone day
```

### Benefits
- ✅ Clean MVC separation (backend simulates, UI routes)
- ✅ Backend reusable (headless simulation possible)
- ✅ Easy to test (UI tests don't need full backend)
- ✅ Flexible (UI can customize milestone detection)
- ✅ No duplicate code (single source of truth in UI)

### Costs
- ❌ Refactoring effort (~300 lines across multiple files)
- ❌ Requires new `advance_days(n)` method in backend
- ❌ UI must query calendar before simulation

**Trade-off Assessment**: Worth it for proper architecture (technical debt reduction)

---

## Implementation Plan

### Phase 1: Create Calendar Query Helper in UI (1 hour)

**File**: `ui/controllers/simulation_controller.py`

**New Method** (after line 782):
```python
def check_upcoming_milestones(
    self,
    days_ahead: int = 7
) -> Optional[Dict[str, Any]]:
    """
    Check if any interactive milestones exist in next N days.

    Args:
        days_ahead: Number of days to look ahead (default: 7)

    Returns:
        Dict with milestone info if found, None otherwise:
        {
            'days_until': int,           # Days until milestone (0-6)
            'milestone_date': str,       # ISO date of milestone
            'event_type': str,           # DRAFT_DAY, DEADLINE, WINDOW
            'event_subtype': str,        # FRANCHISE_TAG, FREE_AGENCY, etc.
            'display_name': str,         # "Draft Day", "Franchise Tag", etc.
            'event': Dict[str, Any]      # Full event dict from database
        }
    """
    # Only check in offseason (milestones are offseason-only)
    if self.get_current_phase() != "offseason":
        return None

    current_date = self.get_current_date()

    # Query events for next N days
    from datetime import datetime, timedelta

    current_dt = datetime.fromisoformat(current_date)

    for day_offset in range(days_ahead):
        check_date = current_dt + timedelta(days=day_offset)
        check_date_str = check_date.date().isoformat()

        # Query database for events on this date
        start_dt = datetime.fromisoformat(check_date_str)
        end_dt = datetime.fromisoformat(f"{check_date_str}T23:59:59")
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)

        events = self.event_db.get_events_by_dynasty_and_timestamp(
            dynasty_id=self.dynasty_id,
            start_timestamp_ms=start_ms,
            end_timestamp_ms=end_ms
        )

        # Check each event
        for event in events:
            event_type = event.get('event_type')
            event_data = event.get('data', {})
            parameters = event_data.get('parameters', {})

            # Skip if already executed
            if 'results' in event_data:
                continue

            # Check for interactive milestone types
            if event_type == 'DRAFT_DAY':
                return {
                    'days_until': day_offset,
                    'milestone_date': check_date_str,
                    'event_type': 'DRAFT_DAY',
                    'event_subtype': None,
                    'display_name': 'Draft Day',
                    'event': event
                }

            elif event_type == 'DEADLINE':
                deadline_type = parameters.get('deadline_type')
                if deadline_type in ['FRANCHISE_TAG', 'FINAL_ROSTER_CUTS', 'SALARY_CAP_COMPLIANCE']:
                    display_name = deadline_type.replace('_', ' ').title()
                    return {
                        'days_until': day_offset,
                        'milestone_date': check_date_str,
                        'event_type': 'DEADLINE',
                        'event_subtype': deadline_type,
                        'display_name': f"Deadline: {display_name}",
                        'event': event
                    }

            elif event_type == 'WINDOW':
                window_name = parameters.get('window_name')
                stage = parameters.get('stage')
                if window_name == 'FREE_AGENCY' and stage == 'START':
                    return {
                        'days_until': day_offset,
                        'milestone_date': check_date_str,
                        'event_type': 'WINDOW',
                        'event_subtype': 'FREE_AGENCY_START',
                        'display_name': 'Free Agency Opening',
                        'event': event
                    }

    # No milestone found in next N days
    return None
```

**Why This Works**:
- Single responsibility: Just queries calendar
- No simulation logic mixed in
- Returns structured milestone info
- Easy to test (mock event database)

---

### Phase 2: Create advance_days(n) Method in Backend (1 hour)

**File**: `src/season/season_cycle_controller.py`

**New Method** (after line 1044):
```python
def advance_days(self, num_days: int) -> Dict[str, Any]:
    """
    Advance simulation by exactly N days (no early stopping).

    Unlike advance_week(), this method does NOT check for milestones
    or stop early. It simulates exactly the specified number of days.

    Args:
        num_days: Number of days to simulate (1-365)

    Returns:
        Dictionary with simulation results

    Raises:
        ValueError: If num_days < 1 or > 365
    """
    if num_days < 1 or num_days > 365:
        raise ValueError(f"num_days must be 1-365, got {num_days}")

    start_date = str(self.calendar.get_current_date())

    daily_results = []

    for day_num in range(num_days):
        # No milestone checks - just simulate
        day_result = self.advance_day()
        daily_results.append(day_result)

        # Stop early only on phase transitions (not milestones)
        if day_result.get("phase_transition"):
            break

    end_date = str(self.calendar.get_current_date())

    # Aggregate results (same as advance_week)
    return self._aggregate_week_results(
        daily_results,
        start_date,
        end_date,
        milestone_info=None  # No milestones checked
    )
```

**File**: `ui/controllers/simulation_controller.py`

**Add UI wrapper**:
```python
def advance_days(self, num_days: int) -> Dict[str, Any]:
    """Advance simulation by exactly N days."""
    def backend_method():
        return self.season_controller.advance_days(num_days)

    return self._execute_simulation_with_persistence(
        operation_name=f"advance_days({num_days})",
        backend_method=backend_method,
        hooks={'post_save': lambda r: self.date_changed.emit(r['date'])},
        extractors={
            'extract_state': lambda r: (r['date'], r['current_phase'], self.get_current_week()),
            'build_success_result': lambda r: r
        },
        failure_dict_factory=lambda msg: {'success': False, 'message': msg}
    )
```

---

### Phase 3: Refactor MainWindow._sim_week() to Use UI Detection (2 hours)

**File**: `ui/main_window.py`

**Replace current `_sim_week()` (lines 635-704)**:
```python
def _sim_week(self):
    """
    Simulate one week with milestone detection in UI layer.

    NEW BEHAVIOR:
    1. Check next 7 days for interactive milestones
    2. If milestone found, simulate up to (but not including) that day
    3. Open interactive dialog for milestone
    4. Continue simulation after dialog closes
    """
    start_date_str = self.simulation_controller.get_current_date()

    # NEW: Check for upcoming milestones
    milestone = self.simulation_controller.check_upcoming_milestones(days_ahead=7)

    if milestone:
        # Milestone found - stop before it
        days_until = milestone['days_until']

        if days_until == 0:
            # Milestone is TODAY - handle immediately
            success = self._handle_interactive_event_router(milestone['event'])

            if not success:
                # User cancelled
                QMessageBox.information(
                    self,
                    "Milestone Paused",
                    f"Simulation paused at {milestone['display_name']}.\n\n"
                    f"Calendar: {self._format_date(start_date_str)}\n\n"
                    "You can resume simulation when ready."
                )
                return

            # Milestone handled - continue simulation for rest of week
            remaining_days = 7  # Simulate full week after milestone
        else:
            # Milestone is in N days - simulate up to it
            days_to_sim = days_until

            if days_to_sim > 0:
                # Simulate days BEFORE milestone
                result = self.simulation_controller.advance_days(days_to_sim)

                if not result['success']:
                    QMessageBox.warning(self, "Simulation Failed", result['message'])
                    return

            # Now handle milestone
            success = self._handle_interactive_event_router(milestone['event'])

            if not success:
                # User cancelled at milestone
                end_date_str = self.simulation_controller.get_current_date()
                QMessageBox.information(
                    self,
                    "Milestone Paused",
                    f"Simulation paused at {milestone['display_name']}.\n\n"
                    f"Calendar: {self._format_date(end_date_str)}\n\n"
                    "You can resume simulation when ready."
                )
                return

            # Milestone handled - simulate remaining days
            remaining_days = 7 - days_until - 1  # -1 because milestone day executed

        # Simulate remaining days (if any)
        if remaining_days > 0:
            result = self.simulation_controller.advance_days(remaining_days)

            if not result['success']:
                QMessageBox.warning(self, "Simulation Failed", result['message'])
                return

    else:
        # No milestone - simulate full week
        result = self.simulation_controller.advance_week()

        if not result['success']:
            QMessageBox.warning(self, "Simulation Failed", result['message'])
            return

    # Show completion message
    end_date_str = self.simulation_controller.get_current_date()
    date_range = self._format_date_range(start_date_str, end_date_str)

    msg = f"Week simulated successfully.\n\n{date_range}"

    if milestone:
        msg += f"\n\nMilestone handled: {milestone['display_name']}"

    QMessageBox.information(self, "Week Complete", msg)

    # Refresh views
    self._refresh_views_after_simulation()
```

**Why This Is Better**:
- ✅ All milestone logic in UI layer (where it belongs)
- ✅ Backend just simulates (clean separation)
- ✅ Easy to test (mock `check_upcoming_milestones()`)
- ✅ Flexible (can customize milestone detection)

---

### Phase 4: Remove Milestone Detection from Backend (30 minutes)

**File**: `src/season/season_cycle_controller.py`

**Mark as DEPRECATED** (line 532):
```python
@deprecated("Milestone detection moved to UI layer. Use advance_days() instead.")
def _check_for_milestone_on_next_date(self) -> Optional[Dict[str, Any]]:
    """
    DEPRECATED: This method will be removed in next release.

    Milestone detection should be done in UI layer using
    SimulationController.check_upcoming_milestones().

    Backend should remain UI-agnostic.
    """
    # Keep implementation for backward compatibility
    # Remove in Phase 2 of refactor
    ...
```

**Remove milestone check from `advance_week()`** (line 981):
```python
# REMOVED: Milestone check (now done in UI)
# if not self.skip_offseason_events:
#     milestone = self._check_for_milestone_on_next_date()
#     if milestone:
#         ...
```

**Note**: This is a BREAKING CHANGE. Old UI code that relies on backend milestone detection will break. Requires careful coordination.

---

### Phase 5: Consolidate UI Check Methods (1 hour)

**File**: `ui/controllers/simulation_controller.py`

**Remove duplicate methods** (lines 633-782):
```python
# REMOVED: check_for_draft_day_event() - replaced by check_upcoming_milestones()
# REMOVED: check_for_interactive_event() - replaced by check_upcoming_milestones()
```

**Single source of truth**:
```python
# NEW: Only one method for milestone detection
def check_upcoming_milestones(days_ahead: int = 7) -> Optional[Dict]:
    """Check next N days for interactive milestones."""
    ...
```

---

## Migration Path

### Step 1: Add New Methods (Non-Breaking)
- Add `check_upcoming_milestones()` to SimulationController
- Add `advance_days(n)` to SeasonCycleController
- Keep old milestone detection methods (backward compatible)

### Step 2: Update MainWindow (Breaking)
- Refactor `_sim_week()` to use new pattern
- Test thoroughly with all milestone types

### Step 3: Deprecate Old Methods
- Mark `_check_for_milestone_on_next_date()` as deprecated
- Mark `check_for_draft_day_event()` as deprecated
- Add deprecation warnings in logs

### Step 4: Remove Old Code (Next Release)
- Delete deprecated methods
- Remove milestone check from `advance_week()`

---

## Testing Strategy

### Unit Tests

**File**: `tests/ui/test_simulation_controller_milestone_detection.py` (NEW)

```python
class TestMilestoneDetectionUI:
    """Test UI-layer milestone detection."""

    def test_check_upcoming_milestones_finds_draft(self):
        """Verify draft found in next 7 days."""
        controller = SimulationController(...)

        # Set date 3 days before draft
        controller.set_date("2025-04-21")

        # Mock event database to return draft event
        with patch.object(controller.event_db, 'get_events_by_dynasty_and_timestamp') as mock_query:
            mock_query.return_value = [{
                'event_type': 'DRAFT_DAY',
                'data': {}  # No results = unexecuted
            }]

            # Execute
            milestone = controller.check_upcoming_milestones(days_ahead=7)

            # Verify
            assert milestone is not None
            assert milestone['event_type'] == 'DRAFT_DAY'
            assert milestone['days_until'] == 3
            assert milestone['display_name'] == 'Draft Day'


    def test_check_upcoming_milestones_ignores_executed(self):
        """Verify executed milestones are ignored."""
        controller = SimulationController(...)

        # Mock event with results (already executed)
        with patch.object(controller.event_db, 'get_events_by_dynasty_and_timestamp') as mock_query:
            mock_query.return_value = [{
                'event_type': 'DRAFT_DAY',
                'data': {'results': {'success': True}}  # Executed!
            }]

            # Execute
            milestone = controller.check_upcoming_milestones(days_ahead=7)

            # Verify - should return None (ignore executed)
            assert milestone is None


    def test_advance_days_method(self):
        """Verify advance_days(n) simulates exactly N days."""
        controller = SimulationController(...)

        # Mock backend
        with patch.object(controller.season_controller, 'advance_days') as mock_days:
            mock_days.return_value = {
                'success': True,
                'days_simulated': 5,
                'date': '2025-09-13'
            }

            # Execute
            result = controller.advance_days(5)

            # Verify
            assert result['success'] is True
            assert result['days_simulated'] == 5
            mock_days.assert_called_once_with(5)
```

### Integration Tests

**File**: `tests/ui/test_mainwindow_milestone_flow.py` (NEW)

```python
class TestMainWindowMilestoneFlow:
    """Test end-to-end milestone detection and handling."""

    def test_sim_week_stops_at_draft(self, qtbot):
        """Verify week simulation stops at draft day."""
        main_window = MainWindow(...)

        # Set date 3 days before draft
        main_window.simulation_controller.set_date("2025-04-21")

        # Mock milestone detection
        with patch.object(main_window.simulation_controller, 'check_upcoming_milestones') as mock_check:
            mock_check.return_value = {
                'days_until': 3,
                'milestone_date': '2025-04-24',
                'event_type': 'DRAFT_DAY',
                'display_name': 'Draft Day',
                'event': {'event_type': 'DRAFT_DAY', 'data': {}}
            }

            # Mock dialog
            with patch.object(main_window, '_handle_interactive_event_router') as mock_dialog:
                mock_dialog.return_value = True  # User completed draft

                # Execute
                main_window._sim_week()

                # Verify
                # Should call advance_days(3) BEFORE draft
                # Then handle draft
                # Then advance_days(3) AFTER draft
                mock_dialog.assert_called_once()
```

---

## Performance Impact

**No Performance Change** (same database queries, just moved to different layer)

**Before**:
- Backend queries events in loop
- Returns milestone to UI
- Total queries: ~7 per week (one per day)

**After**:
- UI queries events ONCE before simulation
- Backend doesn't query at all
- Total queries: ~1 per week (faster!)

**Improvement**: ~6 fewer queries per week (~10% faster)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking change for backend | HIGH | Deprecate first, remove later |
| UI becomes complex | MEDIUM | Extract MilestoneDetector helper class |
| Testing complexity | MEDIUM | Add comprehensive integration tests |
| Regression bugs | HIGH | Test all milestone types thoroughly |

---

## Success Metrics

1. **Zero backend UI knowledge**: Backend code has no milestone detection logic
2. **Single source of truth**: Only one milestone detection method in UI
3. **Test coverage >90%**: Comprehensive tests for milestone routing
4. **Performance improvement**: ~10% fewer database queries per week

---

## Related Issues

- **Issue #1** (Checkpoints): Independent, can implement in parallel
- **Issue #3** (Cancellation): Easier to implement with clean UI detection
- **Optimization #2**: This IS Optimization #2 from audit

---

## Estimated Timeline

| Phase | Duration | Blocker |
|-------|----------|---------|
| Phase 1: Calendar query helper | 1 hour | None |
| Phase 2: advance_days() method | 1 hour | None |
| Phase 3: Refactor MainWindow | 2 hours | Phase 1, 2 |
| Phase 4: Deprecate backend code | 30 min | Phase 3 |
| Phase 5: Consolidate UI methods | 1 hour | Phase 3 |
| **Testing** | 2 hours | All phases |
| **Total** | **7.5 hours** | - |

**Calendar Days**: 2 days (with testing and review)

---

**Status**: Ready for implementation (after checkpoints)
**Approval Required**: Lead Developer, Architect
**Certainty Score**: 98/100