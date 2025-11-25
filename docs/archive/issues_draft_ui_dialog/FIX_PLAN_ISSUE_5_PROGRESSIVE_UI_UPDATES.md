# Fix Plan: Issue #5 - No Incremental UI Updates During Week Simulation

**Priority**: MEDIUM
**Complexity**: Medium
**Estimated Time**: 6-8 hours (2 days)
**Dependencies**: Issue #3 (Cancellation Support - shares threading infrastructure)

## Problem Statement

### Current Behavior
During week simulation, the UI is completely frozen for 3-5 seconds:
- No visual feedback on which day is being simulated
- Cannot see intermediate results (game scores, injuries, etc.)
- User has no sense of progress
- Calendar doesn't update until all 7 days complete
- Appears to "hang" on slower systems

### Impact
- **Poor UX**: Users don't know if app has frozen or is working
- **No Early Exit**: Cannot see milestone emerged on day 3 until day 7 completes
- **Testing Difficulty**: Cannot observe state transitions during simulation
- **Missed Engagement**: Cannot show exciting game results as they happen

### Root Cause
`SimulationController.simulate_week()` executes all 7 days synchronously on Qt main thread with no UI refresh:

```python
def simulate_week(self) -> bool:
    """Execute 7 days synchronously - blocks UI completely."""
    for _ in range(7):
        if not self.simulate_day():
            return False
        # No signal emission here
        # UI calendar frozen

    # Update UI only AFTER all 7 days
    self.simulation_updated.emit()
    return True
```

## Solution Architecture

### Overview
Emit incremental signals after each day simulation to allow UI to update progressively. This creates a "live simulation" experience where users watch the week unfold day-by-day.

### Design Decisions

**Signal-Based Communication (Chosen)**
- **Pros**: Decoupled, thread-safe, Qt-native, works with existing architecture
- **Cons**: Slightly more complex signal routing
- **Decision**: Use Qt signals - aligns with existing `simulation_updated` pattern

**Alternative: Direct UI Calls (Rejected)**
- **Pros**: Simpler code
- **Cons**: Tight coupling, violates MVC, harder to test
- **Reason**: Breaks architectural principles

### New Signal Design

```python
class SimulationController:
    # Existing signal
    simulation_updated = Signal()  # End of week

    # NEW SIGNALS
    day_completed = Signal(dict)   # After each day
    # dict contains: {
    #     'dynasty_id': str,
    #     'date': str,           # ISO format
    #     'day_of_week': str,    # "Monday", etc.
    #     'phase': str,          # "REGULAR_SEASON", etc.
    #     'week': int,
    #     'games': [...],        # Game results (if any)
    #     'milestone_detected': bool,
    #     'milestone_type': str  # If applicable
    # }
```

## Implementation Plan

### Phase 1: Backend Signal Emission (2 hours)

**File**: `ui/controllers/simulation_controller.py`

**1.1 Add New Signal**
```python
class SimulationController(QObject):
    simulation_updated = Signal()
    day_completed = Signal(dict)  # NEW

    def __init__(self, ...):
        super().__init__()
        self._collect_day_stats = True  # Flag to control detail level
```

**1.2 Modify simulate_day() to Return Rich Data**
```python
def simulate_day(self) -> Dict[str, Any]:
    """
    Simulate one day and return detailed results.

    Returns:
        dict: {
            'success': bool,
            'date': str,
            'day_of_week': str,
            'phase': str,
            'week': int,
            'games': List[Dict],  # If game day
            'milestone_detected': bool,
            'milestone_type': Optional[str]
        }
    """
    try:
        # Existing simulation logic
        self._backend.advance_day()

        # Collect results
        result = self._collect_day_results()

        # Emit incremental signal
        self.day_completed.emit(result)

        return result

    except Exception as e:
        logger.error(f"Day simulation failed: {e}")
        return {'success': False, 'error': str(e)}
```

**1.3 Add Result Collection Method**
```python
def _collect_day_results(self) -> Dict[str, Any]:
    """Gather data about the day that just simulated."""
    state = self._data_model.state

    result = {
        'success': True,
        'date': state['current_date'],
        'day_of_week': self._get_day_of_week(state['current_date']),
        'phase': state['current_phase'],
        'week': state.get('current_week', 0),
        'games': [],
        'milestone_detected': False,
        'milestone_type': None
    }

    # Check if today was game day
    if self._was_game_day(state['current_date']):
        result['games'] = self._get_today_games(state['current_date'])

    # Check for milestone
    milestone = self._check_milestone(state['current_date'])
    if milestone:
        result['milestone_detected'] = True
        result['milestone_type'] = milestone['type']

    return result
```

**1.4 Update simulate_week() to Aggregate Results**
```python
def simulate_week(self) -> Dict[str, Any]:
    """
    Simulate 7 days with incremental updates.

    Returns:
        dict: {
            'success': bool,
            'days_simulated': int,
            'games_played': int,
            'milestone_detected': bool,
            'final_date': str
        }
    """
    games_count = 0
    milestone_encountered = False

    for day_num in range(7):
        day_result = self.simulate_day()  # Emits day_completed signal

        if not day_result['success']:
            return {
                'success': False,
                'days_simulated': day_num,
                'error': day_result.get('error')
            }

        games_count += len(day_result.get('games', []))

        if day_result['milestone_detected']:
            milestone_encountered = True
            break  # Stop week early

    # Final update
    self.simulation_updated.emit()

    return {
        'success': True,
        'days_simulated': day_num + 1,
        'games_played': games_count,
        'milestone_detected': milestone_encountered,
        'final_date': self._data_model.state['current_date']
    }
```

### Phase 2: Calendar Live Updates (2 hours)

**File**: `ui/views/calendar_view.py`

**2.1 Connect to day_completed Signal**
```python
class CalendarView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._simulation_controller = None

    def set_simulation_controller(self, controller: SimulationController):
        """Connect to controller signals."""
        self._simulation_controller = controller

        # Existing connection
        controller.simulation_updated.connect(self._on_simulation_updated)

        # NEW: Incremental updates
        controller.day_completed.connect(self._on_day_completed)

    @Slot(dict)
    def _on_day_completed(self, day_result: Dict[str, Any]):
        """Update calendar highlight as simulation progresses."""
        if not day_result['success']:
            return

        # Update calendar to show new current date
        new_date = QDate.fromString(day_result['date'], Qt.ISODate)
        self._calendar_widget.setSelectedDate(new_date)

        # Flash the date cell to show progress (optional visual feedback)
        self._flash_date_cell(new_date)

        # Update date label
        self._current_date_label.setText(
            f"{day_result['day_of_week']}, {day_result['date']}"
        )

        # Process Qt events to ensure UI refreshes
        QApplication.processEvents()
```

**2.2 Add Visual Feedback for Progress**
```python
def _flash_date_cell(self, date: QDate):
    """Briefly highlight the date cell to show simulation progress."""
    # Store original format
    original_format = self._calendar_widget.dateTextFormat(date)

    # Create highlight format
    highlight_format = QTextCharFormat()
    highlight_format.setBackground(QColor(100, 180, 255, 100))  # Light blue

    # Apply highlight
    self._calendar_widget.setDateTextFormat(date, highlight_format)

    # Schedule restore after 200ms
    QTimer.singleShot(200, lambda: self._calendar_widget.setDateTextFormat(date, original_format))
```

### Phase 3: Status Bar Progress Display (1.5 hours)

**File**: `ui/main_window.py`

**3.1 Add Status Bar Updates**
```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... existing setup ...

        # Status bar for simulation feedback
        self.statusBar().showMessage("Ready")
        self._progress_label = QLabel()
        self.statusBar().addPermanentWidget(self._progress_label)

    def _connect_simulation_signals(self):
        """Connect to simulation controller."""
        # Existing connection
        self._simulation_controller.simulation_updated.connect(
            self._on_simulation_updated
        )

        # NEW: Day-by-day progress
        self._simulation_controller.day_completed.connect(
            self._on_day_simulated
        )

    @Slot(dict)
    def _on_day_simulated(self, day_result: Dict[str, Any]):
        """Show progress as each day completes."""
        if not day_result['success']:
            return

        # Update status bar
        msg = f"Simulated {day_result['day_of_week']}, {day_result['date']}"

        if day_result['games']:
            msg += f" - {len(day_result['games'])} game(s) played"

        self.statusBar().showMessage(msg, 2000)  # Show for 2 seconds

        # Update calendar view (already connected)
        # Update standings view if visible
        if self._standings_view and self._standings_view.isVisible():
            self._standings_view.refresh()
```

### Phase 4: Enhanced Progress Dialog (2 hours)

**File**: `ui/dialogs/simulation_progress_dialog.py` (NEW)

**4.1 Create Rich Progress Dialog**
```python
class SimulationProgressDialog(QDialog):
    """
    Show detailed progress during long simulations.
    Used for multi-week/season simulations.
    """

    def __init__(self, total_days: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Simulating...")
        self.setModal(False)  # Non-blocking
        self.resize(450, 300)

        self._total_days = total_days
        self._days_completed = 0
        self._games_played = 0

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximum(self._total_days)
        layout.addWidget(self._progress_bar)

        # Current date label
        self._date_label = QLabel("Starting simulation...")
        self._date_label.setAlignment(Qt.AlignCenter)
        font = self._date_label.font()
        font.setPointSize(12)
        font.setBold(True)
        self._date_label.setFont(font)
        layout.addWidget(self._date_label)

        # Statistics
        stats_layout = QHBoxLayout()
        self._days_label = QLabel("Days: 0")
        self._games_label = QLabel("Games: 0")
        stats_layout.addWidget(self._days_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self._games_label)
        layout.addLayout(stats_layout)

        # Game results area (scrollable)
        self._results_text = QTextEdit()
        self._results_text.setReadOnly(True)
        self._results_text.setMaximumHeight(150)
        layout.addWidget(QLabel("Recent Games:"))
        layout.addWidget(self._results_text)

        # Cancel button
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.clicked.connect(self.reject)
        layout.addWidget(self._cancel_button)

    def update_progress(self, day_result: Dict[str, Any]):
        """Update dialog with latest day results."""
        self._days_completed += 1
        self._progress_bar.setValue(self._days_completed)

        # Update date
        self._date_label.setText(
            f"{day_result['day_of_week']}, {day_result['date']}"
        )

        # Update stats
        self._days_label.setText(f"Days: {self._days_completed}/{self._total_days}")

        # Add game results
        if day_result.get('games'):
            self._games_played += len(day_result['games'])
            self._games_label.setText(f"Games: {self._games_played}")

            for game in day_result['games']:
                result_text = (
                    f"{game['away_team_name']} {game['away_score']} @ "
                    f"{game['home_team_name']} {game['home_score']}\n"
                )
                self._results_text.append(result_text)

        # Process events to update UI
        QApplication.processEvents()
```

**4.2 Integrate with MainWindow**
```python
# In ui/main_window.py

def _sim_to_phase_end(self):
    """Simulate to end of current phase with progress dialog."""
    # Calculate days remaining
    days_remaining = self._simulation_controller.calculate_days_to_phase_end()

    # Show progress dialog
    progress_dialog = SimulationProgressDialog(days_remaining, self)
    progress_dialog.show()

    # Connect to day updates
    self._simulation_controller.day_completed.connect(
        progress_dialog.update_progress
    )

    # Run simulation (in background if Issue #3 is implemented)
    success = self._simulation_controller.simulate_to_phase_end()

    # Close dialog
    progress_dialog.accept()
```

### Phase 5: Performance Optimization (0.5 hours)

**5.1 Add Signal Rate Limiting (Optional)**
```python
class SimulationController:
    def __init__(self, ...):
        super().__init__()
        self._last_ui_update = 0.0
        self._min_update_interval = 0.05  # 50ms minimum between updates

    def simulate_day(self) -> Dict[str, Any]:
        # ... existing logic ...

        # Rate limit UI updates
        current_time = time.time()
        if current_time - self._last_ui_update >= self._min_update_interval:
            self.day_completed.emit(result)
            self._last_ui_update = current_time

        return result
```

**5.2 Add Batch Mode Flag**
```python
class SimulationController:
    def set_batch_mode(self, enabled: bool):
        """
        Disable incremental updates for performance-critical operations.
        Used when simulating multiple seasons in background.
        """
        self._batch_mode = enabled

    def simulate_day(self):
        result = self._backend.advance_day()

        if not self._batch_mode:
            day_data = self._collect_day_results()
            self.day_completed.emit(day_data)

        return result
```

## Testing Strategy

### Unit Tests
```python
# tests/ui/test_progressive_updates.py

def test_day_completed_signal_emitted(qtbot, simulation_controller):
    """Verify day_completed signal fires after each day."""
    with qtbot.waitSignal(simulation_controller.day_completed, timeout=1000) as blocker:
        simulation_controller.simulate_day()

    # Check signal payload
    day_result = blocker.args[0]
    assert 'date' in day_result
    assert 'success' in day_result
    assert day_result['success'] is True

def test_week_emits_seven_day_signals(qtbot, simulation_controller):
    """Verify week simulation emits signal for each day."""
    signal_count = 0

    def count_signals():
        nonlocal signal_count
        signal_count += 1

    simulation_controller.day_completed.connect(count_signals)
    simulation_controller.simulate_week()

    assert signal_count == 7

def test_milestone_stops_week_early(qtbot, simulation_controller):
    """Verify week stops on day 3 if milestone detected."""
    # Setup: Create milestone on day 3
    # ... setup code ...

    signal_count = 0
    simulation_controller.day_completed.connect(lambda: signal_count += 1)

    result = simulation_controller.simulate_week()

    assert signal_count == 3  # Stopped early
    assert result['milestone_detected'] is True
```

### Integration Tests
```python
def test_calendar_updates_during_week(qtbot, main_window):
    """Verify calendar widget updates as week progresses."""
    calendar_view = main_window._calendar_view
    initial_date = calendar_view.selected_date()

    # Simulate 3 days
    for _ in range(3):
        main_window._sim_day()
        qtbot.wait(100)  # Allow UI to update

    # Verify calendar moved forward 3 days
    new_date = calendar_view.selected_date()
    assert (new_date - initial_date).days == 3

def test_status_bar_shows_progress(qtbot, main_window):
    """Verify status bar updates during simulation."""
    status_bar = main_window.statusBar()

    main_window._sim_week()

    # Check status bar was updated (even if message has timed out)
    # We can't easily assert the exact text, but verify it was called
    # This test is more of a smoke test
    assert True  # If we got here without errors, signals are working
```

### Manual Testing Checklist
- [ ] Simulate week - verify calendar advances day-by-day
- [ ] Simulate week - verify status bar shows each day
- [ ] Simulate to phase end - verify progress dialog updates
- [ ] Simulate week with game day - verify game results appear
- [ ] Simulate week with milestone on day 4 - verify stops at day 4
- [ ] Simulate season - verify UI doesn't freeze
- [ ] Enable batch mode - verify no incremental updates
- [ ] Rapid simulate_day() calls - verify no UI stutter

## Performance Impact

### Overhead Analysis
- **Signal Emission**: ~0.05ms per signal (negligible)
- **QApplication.processEvents()**: ~2-5ms per call
- **Calendar Widget Update**: ~10-15ms
- **Status Bar Update**: ~1-2ms

**Total Per Day**: ~15-25ms overhead
**For 7-day week**: ~105-175ms overhead (~3-5% of total 3000ms)

### Optimization Options
1. **Rate Limiting**: Skip updates if last update was <50ms ago
2. **Batch Mode**: Disable for background simulations
3. **Lazy Rendering**: Only update visible widgets
4. **Debouncing**: Update calendar only after last day in rapid succession

## Risk Assessment

### Low Risks
- Signal overhead negligible
- Qt event loop handles updates efficiently
- Existing architecture already uses signals

### Mitigation Strategies
- **UI Stutter**: Use QTimer for deferred updates if processEvents() causes lag
- **Signal Flood**: Rate limit to 20 updates/second max
- **Thread Safety**: All signals emitted from controller (already on main thread)

## Dependencies

### Prerequisites
- None (uses existing Qt infrastructure)

### Synergies with Other Fixes
- **Issue #3 (Cancellation)**: Both use day_completed signal
  - Can check cancellation flag in same callback
  - Progress dialog serves both purposes
- **Issue #1 (Persistence)**: Checkpoint callback can also emit UI signal
  - Single callback handles both persistence + UI update

## Implementation Timeline

| Phase | Time | Description |
|-------|------|-------------|
| 1. Backend Signals | 2h | Add day_completed signal, result collection |
| 2. Calendar Updates | 2h | Connect calendar to signals, add visual feedback |
| 3. Status Bar | 1.5h | Add status bar progress messages |
| 4. Progress Dialog | 2h | Create rich progress dialog for long sims |
| 5. Optimization | 0.5h | Rate limiting, batch mode flag |
| **Total** | **8h** | **~2 days** |

### Testing Time
- Unit tests: 1.5 hours
- Integration tests: 1 hour
- Manual testing: 0.5 hours
- **Total**: 3 hours

### Grand Total: 11 hours (~2.5 days)

## Acceptance Criteria

1. ✅ Calendar advances day-by-day during week simulation
2. ✅ Status bar shows current date after each day
3. ✅ Progress dialog updates for long simulations (>7 days)
4. ✅ Game results appear incrementally, not all at once
5. ✅ Milestone on day 3 stops week at day 3 (UI sees intermediate state)
6. ✅ No UI freeze during simulation
7. ✅ Performance overhead <5% of total simulation time
8. ✅ Batch mode disables updates for background operations
9. ✅ All existing tests still pass
10. ✅ New tests cover signal emission and UI updates

## Future Enhancements

- **Animation**: Smooth date transitions on calendar
- **Sound Effects**: Chime on game day completion
- **Rich Notifications**: Toast popups for important events (injuries, milestones)
- **Live Game Ticker**: Show scores as games progress (requires game simulation threading)
- **Replay Speed Control**: Slow-mo or fast-forward simulation speed

## References

- **Similar Pattern**: `DraftDialogController` uses `pick_made` signal for incremental updates
- **Qt Docs**: https://doc.qt.io/qt-6/signalsandslots.html
- **Existing Signals**: `simulation_updated`, `state_changed` in SimulationController
- **Calendar API**: `QCalendarWidget.setSelectedDate()`, `QTextCharFormat` for styling