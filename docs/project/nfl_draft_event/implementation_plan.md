# NFL Draft Event Integration - Implementation Plan

**Document Version:** 1.0
**Created:** 2025-11-23
**Status:** Ready for Implementation
**Estimated Effort:** 16-22 hours (2-3 days)

---

## Overview

This plan integrates the NFL Draft Day dialog into the main UI simulation flow, enabling automatic draft triggering on April 24th during offseason simulation. The implementation follows a 6-phase approach with clear dependencies and success criteria.

**Key Features:**
- Automatic draft event triggering on April 24
- Save/resume support for partial drafts
- Non-modal dialog (access other UI tabs during draft)
- Draft progress tracking in status bar
- Event marking and cleanup

---

## Phase 1: Backend Event Scheduling

**Goal:** Schedule DraftDayEvent in offseason calendar

**Duration:** 2-3 hours

### Step 1.1: Add DraftDayEvent to OffseasonEventScheduler ✅ **COMPLETE**

**Completed:** 2025-11-23
**Status:** Implemented with minor deviation
**File:** `src/offseason/offseason_event_scheduler.py`
**Location:** Method `_schedule_milestone_events()` (lines 440-454)

**Note:** Implementation uses `user_team_id=1` instead of planned `user_team_id=None`. This provides a fallback default but bypasses Step 1.2's dynamic lookup feature.

**Code Changes:**

```python
def _schedule_milestone_events(self, season_year: int):
    """Schedule informational milestone events."""
    # ... existing code ...

    # Add after other milestone events (Combine, Pro Days, etc.)

    # Draft Day (Late April)
    draft_day_date = self._calculate_offseason_date(season_year, month=4, day=24)
    draft_day_event = DraftDayEvent(
        event_id=self.db.generate_event_id(),
        event_date=draft_day_date,
        dynasty_id=self.dynasty_id,
        season_year=season_year,
        user_team_id=None,  # Will be populated dynamically
        description="NFL Draft (7 Rounds, 262 Picks)"
    )
    self.db.save_event(draft_day_event)
    logger.info(f"Scheduled Draft Day for {draft_day_date}")
```

**Import Addition:**

```python
from events.draft_day_event import DraftDayEvent
```

**Testing:**

```python
# Test script: tests/events/test_draft_day_scheduling.py
def test_draft_day_scheduled_after_super_bowl():
    """Verify DraftDayEvent is created in database."""
    # Setup: Create dynasty, advance to Super Bowl completion
    # Query: SELECT * FROM events WHERE event_type='DRAFT_DAY' AND dynasty_id=?
    # Assert: Event exists with event_date = 'YYYY-04-24'
    # Assert: season_year matches current season
```

---

### Step 1.2: Add Dynamic User Team ID Support ✅ **COMPLETE**

**Completed:** 2025-11-23
**Status:** All tests passing (6/6)
**Test File:** `tests/events/test_draft_day_event.py`

**File:** `src/events/draft_day_event.py`

**Current Issue:** `user_team_id` is hardcoded or set at event creation

**Solution:** Fetch dynamically from `dynasties` table at execution time

**Code Changes:**

```python
class DraftDayEvent(BaseEvent):
    """Interactive draft day event."""

    def __init__(
        self,
        event_id: str,
        event_date: str,
        dynasty_id: str,
        season_year: int,
        user_team_id: Optional[int] = None,  # Made optional
        description: str = "NFL Draft"
    ):
        super().__init__(
            event_id=event_id,
            event_type="DRAFT_DAY",
            event_date=event_date,
            dynasty_id=dynasty_id,
            description=description
        )
        self.season_year = season_year
        self._user_team_id = user_team_id  # Private attribute

    @property
    def user_team_id(self) -> int:
        """
        Get user team ID dynamically from dynasty state.

        Returns:
            int: User's controlled team ID
        """
        if self._user_team_id is not None:
            return self._user_team_id

        # Fetch from database
        from database.dynasty_state_api import DynastyStateAPI
        dynasty_state_api = DynastyStateAPI()
        state = dynasty_state_api.get_dynasty_state(self.dynasty_id)

        if state and state.get('user_team_id'):
            return state['user_team_id']

        # Fallback: default to team 1 (or raise error)
        raise ValueError(f"No user_team_id found for dynasty {self.dynasty_id}")
```

**Testing:**

```python
def test_draft_day_event_fetches_user_team():
    """Verify user_team_id is dynamically retrieved."""
    event = DraftDayEvent(
        event_id="test_id",
        event_date="2025-04-24",
        dynasty_id="test_dynasty",
        season_year=2025,
        user_team_id=None  # Not provided
    )

    # Mock dynasty_state with user_team_id=7 (Denver Broncos)
    # Assert: event.user_team_id == 7
```

---

### Phase 1 Success Criteria

- [x] `DraftDayEvent` appears in `events` table after Super Bowl completion (Step 1.1 - **COMPLETE** ✓)
- [x] Event has correct `event_date` = last Thursday in April (Step 1.1 - **COMPLETE** ✓)
- [x] Event has correct `dynasty_id` and `season_year` (Step 1.1 - **COMPLETE** ✓)
- [x] Database query successfully retrieves event (Step 1.1 - **COMPLETE** ✓)
- [x] Unit test passes for dynamic user team ID retrieval (Step 1.2 - **COMPLETE** ✓)
- [x] Import statement added for DraftDayEvent (Step 1.1 - **COMPLETE** ✓)

---

## Phase 2: UI Component Migration

**Goal:** Move draft dialog to production codebase

**Duration:** 3-4 hours

### Step 2.1: Move DraftDayDialog to Production

**Source:** `demo/draft_day_demo/draft_day_dialog.py`
**Destination:** `ui/dialogs/draft_day_dialog.py`

**Import Updates in Dialog:**

```python
# OLD imports (demo)
from demo.draft_day_demo.draft_round_widget import DraftRoundWidget
from demo.draft_day_demo.player_search_widget import PlayerSearchWidget

# NEW imports (production)
from ui.widgets.draft_round_widget import DraftRoundWidget
from ui.widgets.player_search_widget import PlayerSearchWidget
```

**File Move Checklist:**

1. Copy `draft_day_dialog.py` → `ui/dialogs/`
2. Copy `draft_round_widget.py` → `ui/widgets/`
3. Copy `player_search_widget.py` → `ui/widgets/`
4. Update all imports in moved files

---

### Step 2.2: Create DraftDialogController

**File:** `ui/controllers/draft_controller.py` (NEW)

**Purpose:** Separate business logic from UI presentation

**Code:**

```python
"""
Draft Dialog Controller

Responsibilities:
- Initialize DraftManager with correct database/dynasty context
- Handle draft operations (make_pick, auto_sim)
- Expose clean API to DraftDayDialog
"""

from typing import Dict, List, Optional
from src.offseason.draft_manager import DraftManager
from src.database.api import DatabaseAPI


class DraftDialogController:
    """Controller for draft day dialog operations."""

    def __init__(self, database_path: str, dynasty_id: str):
        """
        Initialize draft controller.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Current dynasty identifier
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id

        # Initialize DraftManager
        self.draft_manager = DraftManager(
            database_path=database_path,
            dynasty_id=dynasty_id
        )

        # Initialize DatabaseAPI for queries
        self.db_api = DatabaseAPI(database_path)

    def get_current_pick(self) -> Dict:
        """
        Get current draft pick information.

        Returns:
            Dict with keys: pick_number, round, pick_in_round, team_id, team_name
        """
        return self.draft_manager.get_current_pick()

    def make_pick(self, player_id: int) -> bool:
        """
        Make a draft selection.

        Args:
            player_id: Player to be drafted

        Returns:
            True if pick successful, False otherwise
        """
        return self.draft_manager.make_pick(player_id)

    def auto_sim_to_next_user_pick(self, user_team_id: int) -> int:
        """
        Auto-simulate draft until user's next pick.

        Args:
            user_team_id: User's controlled team ID

        Returns:
            Number of picks simulated
        """
        return self.draft_manager.auto_sim_to_next_user_pick(user_team_id)

    def get_available_players(self, position: Optional[str] = None) -> List[Dict]:
        """
        Get list of available draft prospects.

        Args:
            position: Optional position filter (QB, RB, WR, etc.)

        Returns:
            List of player dictionaries
        """
        return self.draft_manager.get_available_players(position)

    def get_draft_order(self) -> List[Dict]:
        """
        Get complete draft order (262 picks).

        Returns:
            List of pick dictionaries with team assignments
        """
        return self.draft_manager.get_draft_order()

    def is_draft_complete(self) -> bool:
        """Check if draft is complete (all 262 picks made)."""
        return self.draft_manager.is_draft_complete()

    def get_pick_number(self) -> int:
        """Get current pick number (1-262)."""
        return self.draft_manager.current_pick
```

**Testing:**

```python
# tests/ui/test_draft_controller.py
def test_controller_initialization():
    """Verify controller initializes with correct context."""
    controller = DraftDialogController(
        database_path="test.db",
        dynasty_id="test_dynasty"
    )
    assert controller.draft_manager is not None
    assert controller.dynasty_id == "test_dynasty"

def test_make_pick():
    """Verify pick execution through controller."""
    controller = DraftDialogController(...)
    success = controller.make_pick(player_id=12345)
    assert success is True
```

---

### Step 2.3: Update Dialog to Use New Controller

**File:** `ui/dialogs/draft_day_dialog.py`

**Constructor Change:**

```python
# OLD (demo version)
def __init__(self, database_path: str, dynasty_id: str, user_team_id: int, parent=None):
    super().__init__(parent)
    self.draft_manager = DraftManager(database_path, dynasty_id)
    self.user_team_id = user_team_id

# NEW (production version)
def __init__(self, controller: DraftDialogController, user_team_id: int, parent=None):
    super().__init__(parent)
    self.controller = controller
    self.user_team_id = user_team_id
```

**Method Updates:**

```python
# Replace all self.draft_manager calls with self.controller calls

# OLD
def _load_current_pick(self):
    pick = self.draft_manager.get_current_pick()

# NEW
def _load_current_pick(self):
    pick = self.controller.get_current_pick()
```

---

### Phase 2 Success Criteria

- [ ] Dialog imports successfully from `ui/dialogs/`
- [ ] Controller can be instantiated with database path and dynasty_id
- [ ] Manual test: Open dialog standalone, verify displays correctly
- [ ] All controller methods accessible from dialog
- [ ] No import errors or missing dependencies

**Manual Test Script:**

```python
# test_draft_dialog_standalone.py
from ui.dialogs.draft_day_dialog import DraftDayDialog
from ui.controllers.draft_controller import DraftDialogController
from PySide6.QtWidgets import QApplication

app = QApplication([])
controller = DraftDialogController(
    database_path="data/database/nfl_simulation.db",
    dynasty_id="test_dynasty"
)
dialog = DraftDayDialog(controller, user_team_id=7)
dialog.show()
app.exec()
```

---

## Phase 3: Draft State Management

**Goal:** Support save/resume for partial drafts

**Duration:** 4-5 hours

### Step 3.1: Add Draft Progress Fields to DynastyState

**File:** `src/database/dynasty_state_api.py`

**Database Schema Changes:**

```sql
-- Add to dynasty_state table
ALTER TABLE dynasty_state ADD COLUMN current_draft_pick INTEGER DEFAULT 0;
ALTER TABLE dynasty_state ADD COLUMN draft_in_progress INTEGER DEFAULT 0;  -- Boolean (0/1)
```

**Python API Updates:**

```python
def get_dynasty_state(self, dynasty_id: str) -> Optional[Dict]:
    """
    Retrieve dynasty state including draft progress.

    Returns:
        Dict with keys: current_date, current_phase, season_year, user_team_id,
                       current_draft_pick, draft_in_progress
    """
    query = """
        SELECT current_date, current_phase, season_year, user_team_id,
               current_draft_pick, draft_in_progress
        FROM dynasty_state
        WHERE dynasty_id = ?
    """
    result = self.conn.execute(query, (dynasty_id,)).fetchone()

    if result:
        return {
            'current_date': result[0],
            'current_phase': result[1],
            'season_year': result[2],
            'user_team_id': result[3],
            'current_draft_pick': result[4],
            'draft_in_progress': bool(result[5])
        }
    return None

def update_draft_progress(
    self,
    dynasty_id: str,
    current_pick: int,
    in_progress: bool
) -> bool:
    """
    Update draft progress state.

    Args:
        dynasty_id: Dynasty identifier
        current_pick: Current pick number (1-262)
        in_progress: Whether draft is active

    Returns:
        True if update successful
    """
    update = """
        UPDATE dynasty_state
        SET current_draft_pick = ?,
            draft_in_progress = ?
        WHERE dynasty_id = ?
    """
    try:
        self.conn.execute(update, (current_pick, int(in_progress), dynasty_id))
        self.conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to update draft progress: {e}")
        return False
```

---

### Step 3.2: Implement Save Progress on Dialog Close

**File:** `ui/dialogs/draft_day_dialog.py`

**Override closeEvent:**

```python
def closeEvent(self, event):
    """
    Handle dialog close - save draft progress.

    If draft is incomplete, save current pick number to dynasty_state
    so user can resume later.
    """
    if not self.controller.is_draft_complete():
        # Draft still in progress
        current_pick = self.controller.get_pick_number()

        # Save to database
        from database.dynasty_state_api import DynastyStateAPI
        dynasty_state_api = DynastyStateAPI(self.controller.database_path)

        success = dynasty_state_api.update_draft_progress(
            dynasty_id=self.controller.dynasty_id,
            current_pick=current_pick,
            in_progress=True
        )

        if success:
            logger.info(f"Draft progress saved: Pick {current_pick}/262")
        else:
            logger.error("Failed to save draft progress!")

    # Accept close event
    event.accept()
```

---

### Step 3.3: Implement Resume Logic

**File:** `ui/dialogs/draft_day_dialog.py`

**Constructor Update:**

```python
def __init__(self, controller: DraftDialogController, user_team_id: int, parent=None):
    super().__init__(parent)
    self.controller = controller
    self.user_team_id = user_team_id

    # Check for existing draft progress
    self._check_resume_draft()

    # Setup UI
    self._setup_ui()
    self._load_current_pick()

def _check_resume_draft(self):
    """
    Check if draft was previously in progress and resume if needed.
    """
    from database.dynasty_state_api import DynastyStateAPI
    dynasty_state_api = DynastyStateAPI(self.controller.database_path)

    state = dynasty_state_api.get_dynasty_state(self.controller.dynasty_id)

    if state and state.get('draft_in_progress', False):
        saved_pick = state.get('current_draft_pick', 1)

        # Resume draft at saved pick
        self.controller.draft_manager.current_pick = saved_pick

        logger.info(f"Resuming draft at pick {saved_pick}/262")

        # Show resume message to user
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Resume Draft",
            f"Resuming draft at pick {saved_pick} (Round {(saved_pick-1)//32 + 1})"
        )
```

---

### Phase 3 Success Criteria

- [ ] Database schema includes `current_draft_pick` and `draft_in_progress` columns
- [ ] `DynastyStateAPI` has `update_draft_progress()` method
- [ ] Making 10 picks and closing dialog saves progress
- [ ] Reopening dialog shows picks 1-10 as completed
- [ ] Pick 11 is active and ready for selection
- [ ] UI displays "Resume Draft" message on reopen

**Testing Script:**

```python
# tests/ui/test_draft_resume.py
def test_draft_save_resume():
    """Verify draft save/resume functionality."""
    # 1. Create controller and dialog
    # 2. Make 10 picks
    # 3. Close dialog (should save progress)
    # 4. Query database: assert current_draft_pick=11, draft_in_progress=True
    # 5. Reopen dialog
    # 6. Assert: current pick = 11
    # 7. Assert: picks 1-10 marked complete in UI
```

---

## Phase 4: Event-UI Integration

**Goal:** Connect event system to dialog display

**Duration:** 3-4 hours

### Step 4.1: Add Interactive Event Detection

**File:** `ui/controllers/simulation_controller.py`

**New Method:**

```python
def check_for_interactive_events(self, date: str) -> Optional[Dict]:
    """
    Check if there are interactive events on the given date.

    Interactive events require user input and pause simulation:
    - DRAFT_DAY: NFL Draft (user makes picks)

    Args:
        date: Date string in 'YYYY-MM-DD' format

    Returns:
        Dict with event info if interactive event found, None otherwise
        Keys: event_id, event_type, event_date, description, metadata
    """
    # Query events for this date
    query = """
        SELECT event_id, event_type, event_date, description
        FROM events
        WHERE dynasty_id = ?
          AND event_date = ?
          AND is_executed = 0
        ORDER BY event_id
    """

    events = self.event_db_api.conn.execute(
        query,
        (self.dynasty_id, date)
    ).fetchall()

    # Check for interactive event types
    for event in events:
        event_id, event_type, event_date, description = event

        if event_type == 'DRAFT_DAY':
            return {
                'event_id': event_id,
                'event_type': event_type,
                'event_date': event_date,
                'description': description,
                'metadata': {
                    'requires_user_input': True,
                    'dialog_type': 'draft_day'
                }
            }

    # No interactive events found
    return None
```

---

### Step 4.2: Add Qt Signal

**File:** `ui/controllers/simulation_controller.py`

**Class-level Signal:**

```python
from PySide6.QtCore import QObject, Signal

class SimulationController(QObject):
    """Controller for simulation operations."""

    # Existing signals
    date_changed = Signal(str)
    phase_changed = Signal(str)

    # NEW: Interactive event signal
    interactive_event_detected = Signal(dict)  # Emits event info dict
```

---

### Step 4.3: Modify Advance Day/Week Methods

**File:** `ui/controllers/simulation_controller.py`

**Update advance_day():**

```python
def advance_day(self) -> bool:
    """
    Advance simulation by one day.

    Returns:
        True if day advanced successfully, False if interactive event blocks
    """
    current_date = self.simulation_data_model.get_current_date()

    # Calculate next date
    next_date = self._calculate_next_date(current_date)

    # CHECK FOR INTERACTIVE EVENTS BEFORE ADVANCING
    interactive_event = self.check_for_interactive_events(next_date)

    if interactive_event:
        # Emit signal to main window
        self.interactive_event_detected.emit(interactive_event)

        logger.info(f"Interactive event detected on {next_date}: {interactive_event['event_type']}")

        # Return False to indicate simulation paused
        return False

    # No interactive events - proceed with normal advancement
    try:
        # Execute simulation for this day
        result = self.simulation_executor.simulate_day(next_date)

        # Update dynasty state
        self.simulation_data_model.advance_to_date(next_date)

        # Emit date changed signal
        self.date_changed.emit(next_date)

        return True
    except Exception as e:
        logger.error(f"Failed to advance day: {e}")
        return False
```

**Update advance_week():**

```python
def advance_week(self) -> bool:
    """
    Advance simulation by one week.

    Returns:
        True if week advanced successfully, False if interactive event blocks
    """
    # Advance day by day, checking for interactive events
    for _ in range(7):
        success = self.advance_day()

        if not success:
            # Interactive event detected - stop week advancement
            return False

    return True
```

---

### Step 4.4: Connect Signal in MainWindow

**File:** `ui/main_window.py`

**Signal Connection in Constructor:**

```python
def __init__(self):
    super().__init__()

    # ... existing initialization ...

    # Connect interactive event signal
    self.simulation_controller.interactive_event_detected.connect(
        self._on_interactive_event
    )
```

**Signal Handler:**

```python
def _on_interactive_event(self, event_info: Dict):
    """
    Handle interactive event detection.

    Args:
        event_info: Dict with keys: event_id, event_type, event_date, description, metadata
    """
    event_type = event_info['event_type']
    event_date = event_info['event_date']

    logger.info(f"Interactive event triggered: {event_type} on {event_date}")

    if event_type == 'DRAFT_DAY':
        self._show_draft_day_dialog(event_info)
    else:
        logger.warning(f"Unknown interactive event type: {event_type}")

def _show_draft_day_dialog(self, event_info: Dict):
    """
    Show draft day dialog.

    Args:
        event_info: Draft event information
    """
    from ui.controllers.draft_controller import DraftDialogController
    from ui.dialogs.draft_day_dialog import DraftDayDialog

    # Create controller
    controller = DraftDialogController(
        database_path=self.simulation_controller.database_path,
        dynasty_id=self.simulation_controller.dynasty_id
    )

    # Get user team ID
    state = self.simulation_controller.simulation_data_model.get_dynasty_state()
    user_team_id = state.get('user_team_id', 1)

    # Create and show dialog (modal for now - Phase 5 makes it non-modal)
    dialog = DraftDayDialog(controller, user_team_id, parent=self)
    dialog.exec()  # Will change to dialog.show() in Phase 5

    # After dialog closes, mark event as executed
    self._mark_event_executed(event_info['event_id'])

def _mark_event_executed(self, event_id: str):
    """
    Mark event as executed in database.

    Args:
        event_id: Event identifier
    """
    update = """
        UPDATE events
        SET is_executed = 1
        WHERE event_id = ?
    """
    try:
        self.simulation_controller.event_db_api.conn.execute(update, (event_id,))
        self.simulation_controller.event_db_api.conn.commit()
        logger.info(f"Event {event_id} marked as executed")
    except Exception as e:
        logger.error(f"Failed to mark event executed: {e}")
```

---

### Phase 4 Success Criteria

- [ ] Advance simulation to April 23
- [ ] Click "Advance Day"
- [ ] Draft dialog appears automatically on April 24
- [ ] `interactive_event_detected` signal emitted
- [ ] Event marked as executed after dialog closes
- [ ] Simulation resumes normally after draft completion

**Testing:**

```python
# tests/ui/test_interactive_events.py
def test_draft_day_triggers_dialog():
    """Verify draft dialog appears on April 24."""
    # Setup: Create dynasty, advance to April 23
    # Action: Call simulation_controller.advance_day()
    # Assert: interactive_event_detected signal emitted
    # Assert: event_info['event_type'] == 'DRAFT_DAY'
```

---

## Phase 5: Non-Modal Behavior

**Goal:** Allow UI access during draft

**Duration:** 2-3 hours

### Step 5.1: Make Dialog Non-Modal

**File:** `ui/main_window.py`

**Update _show_draft_day_dialog():**

```python
def _show_draft_day_dialog(self, event_info: Dict):
    """
    Show draft day dialog (non-modal).

    Args:
        event_info: Draft event information
    """
    from ui.controllers.draft_controller import DraftDialogController
    from ui.dialogs.draft_day_dialog import DraftDayDialog

    # Create controller
    controller = DraftDialogController(
        database_path=self.simulation_controller.database_path,
        dynasty_id=self.simulation_controller.dynasty_id
    )

    # Get user team ID
    state = self.simulation_controller.simulation_data_model.get_dynasty_state()
    user_team_id = state.get('user_team_id', 1)

    # Create dialog
    self.draft_dialog = DraftDayDialog(controller, user_team_id, parent=self)

    # Connect completion signal
    self.draft_dialog.draft_completed.connect(self._on_draft_completed)

    # Show non-modal
    self.draft_dialog.show()  # Changed from exec()

    # Store event ID for later marking
    self.active_draft_event_id = event_info['event_id']

    # Update UI state
    self._set_draft_mode(True)
```

**Dialog Completion Signal:**

**File:** `ui/dialogs/draft_day_dialog.py`

```python
from PySide6.QtCore import Signal

class DraftDayDialog(QDialog):
    """Draft day dialog with non-modal support."""

    # Signal emitted when draft is complete
    draft_completed = Signal()

    def _handle_pick_made(self):
        """Handle pick completion."""
        # ... existing pick logic ...

        # Check if draft complete
        if self.controller.is_draft_complete():
            logger.info("Draft complete! All 262 picks made.")

            # Emit completion signal
            self.draft_completed.emit()

            # Close dialog
            self.close()
```

---

### Step 5.2: Add Draft Progress Indicator

**File:** `ui/main_window.py`

**Status Bar Update:**

```python
def _set_draft_mode(self, active: bool):
    """
    Toggle draft mode UI state.

    Args:
        active: True to enable draft mode, False to disable
    """
    if active:
        # Show draft progress in status bar
        self.draft_progress_label = QLabel("Draft in Progress - Pick 1/262")
        self.statusBar().addWidget(self.draft_progress_label)

        # Connect to pick made signal for updates
        if hasattr(self, 'draft_dialog'):
            self.draft_dialog.pick_made.connect(self._update_draft_progress)

        # Disable simulation controls
        self._set_simulation_controls_enabled(False)
    else:
        # Remove draft progress indicator
        if hasattr(self, 'draft_progress_label'):
            self.statusBar().removeWidget(self.draft_progress_label)
            self.draft_progress_label = None

        # Re-enable simulation controls
        self._set_simulation_controls_enabled(True)

def _update_draft_progress(self, pick_number: int):
    """
    Update draft progress indicator.

    Args:
        pick_number: Current pick number (1-262)
    """
    round_num = (pick_number - 1) // 32 + 1
    pick_in_round = (pick_number - 1) % 32 + 1

    if hasattr(self, 'draft_progress_label'):
        self.draft_progress_label.setText(
            f"Draft in Progress - Round {round_num}, Pick {pick_in_round} (Overall: {pick_number}/262)"
        )
```

**Pick Made Signal:**

**File:** `ui/dialogs/draft_day_dialog.py`

```python
class DraftDayDialog(QDialog):
    """Draft day dialog with progress signals."""

    draft_completed = Signal()
    pick_made = Signal(int)  # Emits pick number

    def _handle_pick_made(self):
        """Handle pick completion."""
        pick_number = self.controller.get_pick_number()

        # Emit signal
        self.pick_made.emit(pick_number)

        # ... rest of existing logic ...
```

---

### Step 5.3: Disable Simulation Controls

**File:** `ui/main_window.py`

**Control Management:**

```python
def _set_simulation_controls_enabled(self, enabled: bool):
    """
    Enable/disable simulation controls.

    Args:
        enabled: True to enable, False to disable
    """
    # Disable toolbar buttons
    if hasattr(self, 'advance_day_action'):
        self.advance_day_action.setEnabled(enabled)

    if hasattr(self, 'advance_week_action'):
        self.advance_week_action.setEnabled(enabled)

    # Add visual indicator
    if not enabled:
        self.statusBar().showMessage("⚠ Simulation paused - Complete draft to continue")
    else:
        self.statusBar().clearMessage()
```

---

### Phase 5 Success Criteria

- [ ] Draft dialog opens non-modal
- [ ] Can click Team tab and view roster while draft is open
- [ ] Advance Day/Week buttons disabled during draft
- [ ] Status bar shows "Draft in Progress - Pick X/262"
- [ ] Status bar updates in real-time as picks are made
- [ ] Warning message displays when controls are disabled

**Manual Test:**

1. Advance to April 24 (draft day)
2. Draft dialog appears
3. Click "Team" tab - verify accessible
4. Click "Offseason" tab - verify accessible
5. Try clicking "Advance Day" - verify disabled
6. Status bar shows draft progress
7. Make a pick - status bar updates

---

## Phase 6: Completion & Cleanup

**Goal:** Handle draft completion and cleanup

**Duration:** 2-3 hours

### Step 6.1: Handle Draft Completion

**File:** `ui/main_window.py`

**Completion Handler:**

```python
def _on_draft_completed(self):
    """
    Handle draft completion signal.

    Cleanup actions:
    1. Mark event as executed
    2. Clear draft_in_progress flag
    3. Re-enable simulation controls
    4. Show completion message
    """
    logger.info("Draft completed - cleaning up")

    # Mark event executed
    if hasattr(self, 'active_draft_event_id'):
        self._mark_event_executed(self.active_draft_event_id)
        del self.active_draft_event_id

    # Clear draft progress in dynasty_state
    from database.dynasty_state_api import DynastyStateAPI
    dynasty_state_api = DynastyStateAPI(self.simulation_controller.database_path)

    dynasty_state_api.update_draft_progress(
        dynasty_id=self.simulation_controller.dynasty_id,
        current_pick=262,  # Final pick
        in_progress=False  # Draft complete
    )

    # Update UI
    self._set_draft_mode(False)

    # Show completion message
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.information(
        self,
        "Draft Complete",
        "The 2025 NFL Draft is complete! All 262 picks have been made.\n\n"
        "You can now advance the simulation to continue the offseason."
    )
```

---

### Step 6.2: Mark Event Executed

**File:** `ui/main_window.py`

**Already implemented in Phase 4.4** - ensure it's called from `_on_draft_completed()`

```python
def _mark_event_executed(self, event_id: str):
    """
    Mark event as executed in database.

    Args:
        event_id: Event identifier
    """
    update = """
        UPDATE events
        SET is_executed = 1
        WHERE event_id = ?
    """
    try:
        self.simulation_controller.event_db_api.conn.execute(update, (event_id,))
        self.simulation_controller.event_db_api.conn.commit()
        logger.info(f"Event {event_id} marked as executed")
    except Exception as e:
        logger.error(f"Failed to mark event executed: {e}")
```

---

### Step 6.3: Re-enable Simulation Controls

**File:** `ui/main_window.py`

**Already implemented in Phase 5.2** - called from `_set_draft_mode(False)`

---

### Step 6.4: Auto-Resume Partial Drafts on Startup

**File:** `ui/main_window.py`

**Startup Check:**

```python
def showEvent(self, event):
    """
    Override showEvent to check for incomplete drafts on startup.

    Args:
        event: Qt show event
    """
    super().showEvent(event)

    # Only check once
    if not hasattr(self, '_draft_startup_check_done'):
        self._draft_startup_check_done = True
        self._check_incomplete_draft()

def _check_incomplete_draft(self):
    """
    Check if there's an incomplete draft and offer to resume.
    """
    from database.dynasty_state_api import DynastyStateAPI

    dynasty_state_api = DynastyStateAPI(self.simulation_controller.database_path)
    state = dynasty_state_api.get_dynasty_state(self.simulation_controller.dynasty_id)

    if state and state.get('draft_in_progress', False):
        current_pick = state.get('current_draft_pick', 1)

        # Ask user if they want to resume
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Resume Draft?",
            f"You have an incomplete draft (currently at pick {current_pick}/262).\n\n"
            "Would you like to resume the draft now?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Query for draft event
            query = """
                SELECT event_id, event_type, event_date, description
                FROM events
                WHERE dynasty_id = ?
                  AND event_type = 'DRAFT_DAY'
                  AND is_executed = 0
                LIMIT 1
            """

            event = self.simulation_controller.event_db_api.conn.execute(
                query,
                (self.simulation_controller.dynasty_id,)
            ).fetchone()

            if event:
                event_info = {
                    'event_id': event[0],
                    'event_type': event[1],
                    'event_date': event[2],
                    'description': event[3]
                }

                # Show draft dialog
                self._show_draft_day_dialog(event_info)
```

---

### Phase 6 Success Criteria

- [ ] Complete all 262 picks
- [ ] Draft completion message displays
- [ ] Event marked as executed in database (`is_executed = 1`)
- [ ] `draft_in_progress` flag cleared in dynasty_state
- [ ] Simulation controls re-enabled
- [ ] Can advance to April 25
- [ ] Draft doesn't re-trigger on April 24
- [ ] Startup check detects incomplete draft
- [ ] User can resume incomplete draft from startup

**Testing:**

```python
# tests/ui/test_draft_completion.py
def test_draft_completion_cleanup():
    """Verify all cleanup actions execute."""
    # 1. Simulate 262 picks
    # 2. Verify draft_completed signal emitted
    # 3. Query database: assert is_executed=1
    # 4. Query dynasty_state: assert draft_in_progress=False
    # 5. Verify simulation controls re-enabled

def test_partial_draft_resume_on_startup():
    """Verify startup detects incomplete draft."""
    # 1. Set draft_in_progress=True, current_draft_pick=50
    # 2. Create MainWindow instance
    # 3. Trigger showEvent
    # 4. Verify resume dialog appears
```

---

## File Summary

### Files to Create

| File Path | Purpose | Lines (Est.) |
|-----------|---------|-------------|
| `ui/controllers/draft_controller.py` | Draft business logic controller | 150-200 |
| `ui/dialogs/draft_day_dialog.py` | Moved from demo/ with updates | 800-1000 |
| `ui/widgets/draft_round_widget.py` | Moved from demo/ | 400-500 |
| `ui/widgets/player_search_widget.py` | Moved from demo/ | 300-400 |

### Files to Modify

| File Path | Changes | Lines Added (Est.) |
|-----------|---------|-------------------|
| `src/offseason/offseason_event_scheduler.py` | Add DraftDayEvent scheduling | 15-20 |
| `src/events/draft_day_event.py` | Dynamic user_team_id support | 25-30 |
| `src/database/dynasty_state_api.py` | Add draft progress fields + methods | 50-60 |
| `ui/controllers/simulation_controller.py` | Interactive event detection + signal | 80-100 |
| `ui/main_window.py` | Signal handling + draft mode management | 150-200 |

---

## Timeline & Dependencies

```
Phase 1 (Backend Event Scheduling) - ✅ COMPLETE
  ├─ Step 1.1: Add DraftDayEvent to scheduler [2h] - ✅ COMPLETE (2025-11-23)
  └─ Step 1.2: Dynamic user_team_id support [1h] - ✅ COMPLETE (2025-11-23)

Phase 2 (UI Component Migration)
  ├─ Step 2.1: Move files to production [1h]
  ├─ Step 2.2: Create DraftDialogController [2h]
  └─ Step 2.3: Update dialog imports [1h]
  (Depends on: Phase 1 complete)

Phase 3 (Draft State Management)
  ├─ Step 3.1: Database schema changes [2h]
  ├─ Step 3.2: Save progress on close [1h]
  └─ Step 3.3: Resume logic [2h]
  (Can run parallel to Phase 2)

Phase 4 (Event-UI Integration)
  ├─ Step 4.1: Interactive event detection [1h]
  ├─ Step 4.2: Add Qt signal [0.5h]
  ├─ Step 4.3: Modify advance methods [1.5h]
  └─ Step 4.4: Connect signal in MainWindow [1h]
  (Depends on: Phase 2 complete)

Phase 5 (Non-Modal Behavior)
  ├─ Step 5.1: Make dialog non-modal [1h]
  ├─ Step 5.2: Add draft progress indicator [1h]
  └─ Step 5.3: Disable simulation controls [1h]
  (Depends on: Phase 4 complete)

Phase 6 (Completion & Cleanup)
  ├─ Step 6.1: Handle draft completion [1h]
  ├─ Step 6.2: Mark event executed [0.5h]
  ├─ Step 6.3: Re-enable controls [0.5h]
  └─ Step 6.4: Auto-resume on startup [1h]
  (Depends on: Phase 5 complete)
```

**Total Estimated Time:** 16-22 hours (2-3 days)

**Parallelization Opportunities:**
- Phase 3 can run parallel to Phase 2
- Testing can run parallel to development

---

## Risk Assessment

### High Risk

**1. Database Schema Changes (Phase 3.1)**
- **Risk:** Adding columns to `dynasty_state` table may fail on existing databases
- **Mitigation:** Create migration script with `ALTER TABLE` + error handling
- **Rollback Plan:** Provide SQL to drop columns if needed

**2. Non-Modal Dialog Qt Event Loop (Phase 5.1)**
- **Risk:** Non-modal dialog may cause unexpected Qt event loop interactions
- **Mitigation:** Thorough testing with manual user interaction
- **Rollback Plan:** Can fall back to modal dialog (exec()) if issues arise

### Medium Risk

**3. Draft State Persistence Edge Cases (Phase 3)**
- **Risk:** User closes dialog unexpectedly (crash, force quit)
- **Mitigation:** Save progress after each pick (not just on close)
- **Fallback:** Resume dialog checks for inconsistent state and offers recovery

**4. Signal Connection Timing (Phase 4)**
- **Risk:** Signal emitted before UI fully initialized
- **Mitigation:** Connect signals in constructor, use queued connections
- **Rollback Plan:** Add connection validation checks

### Low Risk

**5. Event Marking Failures (Phase 6.2)**
- **Risk:** Database write fails when marking event executed
- **Mitigation:** Add retry logic + error logging
- **Impact:** Minor - event may re-trigger, but can be manually marked

---

## Testing Strategy

### Unit Tests

```python
# tests/events/test_draft_day_scheduling.py
- test_draft_day_scheduled_after_super_bowl()
- test_draft_day_event_fetches_user_team()

# tests/database/test_dynasty_state_draft_progress.py
- test_update_draft_progress()
- test_get_draft_progress()
- test_clear_draft_progress()

# tests/ui/test_draft_controller.py
- test_controller_initialization()
- test_make_pick()
- test_auto_sim_to_next_user_pick()
- test_is_draft_complete()

# tests/ui/test_interactive_events.py
- test_draft_day_triggers_dialog()
- test_check_for_interactive_events()
- test_interactive_event_signal_emitted()

# tests/ui/test_draft_resume.py
- test_draft_save_resume()
- test_partial_draft_resume_on_startup()
- test_draft_completion_cleanup()
```

### Integration Tests

```python
# tests/integration/test_draft_flow.py
- test_full_draft_flow()
  1. Advance to April 24
  2. Draft dialog appears
  3. Make 10 picks
  4. Close and reopen
  5. Verify resume works
  6. Complete draft
  7. Verify cleanup

- test_non_modal_draft_interaction()
  1. Open draft dialog
  2. Switch to Team tab
  3. Make picks while browsing roster
  4. Verify no crashes or UI freezes
```

### Manual Testing Checklist

**Before Phase 1:**
- [ ] Create clean test database
- [ ] Advance to Super Bowl completion
- [ ] Verify no draft events exist

**After Phase 1:**
- [ ] Query database, confirm DraftDayEvent scheduled
- [ ] Verify event_date = April 24
- [ ] Check season_year matches current season

**After Phase 2:**
- [ ] Run standalone dialog test script
- [ ] Verify dialog displays correctly
- [ ] Test all controller methods

**After Phase 3:**
- [ ] Make 50 picks, close dialog
- [ ] Query database, verify progress saved
- [ ] Reopen dialog, verify resumes at pick 51

**After Phase 4:**
- [ ] Advance day by day to April 24
- [ ] Verify dialog appears automatically
- [ ] Complete draft, verify event marked executed

**After Phase 5:**
- [ ] Open draft dialog
- [ ] Click Team tab (verify accessible)
- [ ] Click Offseason tab (verify accessible)
- [ ] Verify Advance Day/Week disabled
- [ ] Make picks, watch status bar update

**After Phase 6:**
- [ ] Complete all 262 picks
- [ ] Verify completion message
- [ ] Advance to April 25 (should work)
- [ ] Advance to April 24 again (should NOT re-trigger)
- [ ] Close app, set draft_in_progress=True manually
- [ ] Restart app, verify resume prompt

---

## Code Snippets Reference

### Database Migration Script

**File:** `scripts/migrate_add_draft_progress.py`

```python
"""
Database migration: Add draft progress fields to dynasty_state table.

Run with: python scripts/migrate_add_draft_progress.py
"""

import sqlite3
import sys

DATABASE_PATH = "data/database/nfl_simulation.db"

def migrate():
    """Add draft progress columns to dynasty_state."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(dynasty_state)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'current_draft_pick' not in columns:
            print("Adding current_draft_pick column...")
            cursor.execute("""
                ALTER TABLE dynasty_state
                ADD COLUMN current_draft_pick INTEGER DEFAULT 0
            """)
            print("✓ current_draft_pick added")
        else:
            print("⚠ current_draft_pick already exists")

        if 'draft_in_progress' not in columns:
            print("Adding draft_in_progress column...")
            cursor.execute("""
                ALTER TABLE dynasty_state
                ADD COLUMN draft_in_progress INTEGER DEFAULT 0
            """)
            print("✓ draft_in_progress added")
        else:
            print("⚠ draft_in_progress already exists")

        conn.commit()
        print("\n✓ Migration complete!")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
```

---

## Success Metrics

**Phase 1:**
- Event scheduled in database ✓
- Dynamic user team ID retrieval ✓

**Phase 2:**
- Dialog imports from production ✓
- Controller API functional ✓
- Standalone test passes ✓

**Phase 3:**
- Save/resume functionality works ✓
- Database persistence reliable ✓
- UI state restoration accurate ✓

**Phase 4:**
- Automatic trigger on April 24 ✓
- Event marking successful ✓
- Signal emission correct ✓

**Phase 5:**
- Non-modal dialog operational ✓
- Other tabs accessible ✓
- Progress indicator updates ✓
- Controls disabled properly ✓

**Phase 6:**
- Completion cleanup executes ✓
- Event marked executed ✓
- Controls re-enabled ✓
- No re-triggering ✓
- Startup resume works ✓

---

## Rollback Plan

If issues arise during any phase:

1. **Phase 1 Rollback:**
   - Remove `DraftDayEvent` from `OffseasonEventScheduler`
   - Delete event from database: `DELETE FROM events WHERE event_type='DRAFT_DAY'`

2. **Phase 2 Rollback:**
   - Keep demo/ version intact as backup
   - Revert ui/ file additions

3. **Phase 3 Rollback:**
   - Run rollback migration to drop columns
   - Restore DynastyStateAPI to previous version

4. **Phase 4 Rollback:**
   - Remove signal connection in MainWindow
   - Comment out interactive event check in advance_day()

5. **Phase 5 Rollback:**
   - Change dialog.show() back to dialog.exec()
   - Remove status bar indicators

6. **Phase 6 Rollback:**
   - Remove startup check
   - Keep manual draft triggering via Offseason tab

---

## Post-Implementation

### Documentation Updates

- [ ] Update `CLAUDE.md` with draft integration notes
- [ ] Add draft flow diagram to `docs/ui/`
- [ ] Document new controller in API docs
- [ ] Update testing guide with draft test cases

### Future Enhancements

1. **Draft Trade Support** (Future)
   - Allow trading draft picks during draft
   - Trade dialog integration

2. **Draft Analytics** (Future)
   - Team needs analysis during draft
   - Real-time draft grades
   - Best player available recommendations

3. **Mock Draft Mode** (Future)
   - Run mock drafts before real draft
   - AI learning from mock results

4. **Multi-User Draft** (Future)
   - Network support for multi-user drafts
   - Turn-based draft with timers

---

## Contact & Support

**Implementation Questions:**
- Check existing implementations in `demo/draft_day_demo/`
- Review `DraftManager` API in `src/offseason/draft_manager.py`
- Consult `docs/plans/offseason_plan.md` for architecture

**Bug Reports:**
- Test each phase independently
- Use comprehensive logging
- Document edge cases discovered

**Code Review Checklist:**
- All signals properly connected
- Database transactions committed
- Error handling comprehensive
- Logging statements added
- Type hints included
- Docstrings complete

---

**End of Implementation Plan**
