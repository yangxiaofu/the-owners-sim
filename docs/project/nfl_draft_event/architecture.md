# NFL Draft Event Integration Architecture

## Overview

This document describes the architecture for integrating the NFL Draft Day event into the main simulation UI. The system enables users to participate interactively in the 7-round NFL draft when the simulation calendar reaches April 24, with automatic pausing, resumable draft state, and seamless integration with the existing season cycle.

## High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         NFL Draft Event Flow                             │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│ OffseasonEvent       │  (1) Creates DRAFT_DAY event for April 24
│ Scheduler            │      during offseason initialization
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ EventDatabase        │  (2) Stores event with season_year, dynasty_id
│ API                  │      Event type: DRAFT_DAY
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ SimulationController │  (3) Queries events when advancing calendar
│                      │  (4) Detects interactive DRAFT_DAY event
│                      │  (5) Emits interactive_event_detected signal
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ MainWindow           │  (6) Receives signal, pauses simulation
│                      │  (7) Creates DraftDialogController
│                      │  (8) Shows DraftDayDialog (non-modal)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ DraftDialogController│  (9) Orchestrates draft business logic
│                      │  (10) Loads draft order, draft class
│                      │  (11) Executes pick logic via DraftManager
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ DraftDayDialog       │  (12) Displays UI, user makes picks
│                      │  (13) Emits pick_made signals
│                      │  (14) Saves state on close
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ DraftManager         │  (15) Performs database operations:
│                      │      - Assigns players to teams
│                      │      - Creates rookie contracts
│                      │      - Updates draft order status
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ DynastyStateAPI      │  (16) Persists draft progress:
│                      │      - current_draft_pick
│                      │      - draft_in_progress flag
└──────────────────────┘
```

## Component Details

### 1. OffseasonEventScheduler

**File**: `src/offseason/offseason_event_scheduler.py`

**Responsibility**: Schedule draft-related events during offseason initialization

**Integration Point**: `_schedule_milestone_events()` method

**Code Snippet**:
```python
def _schedule_milestone_events(self, season_year: int) -> None:
    """Schedule milestone events like schedule release, draft, combine."""

    # Draft Day - April 24 (late April)
    draft_date = datetime(season_year, 4, 24).date()
    draft_event = DraftDayEvent(
        season_year=season_year,
        date=draft_date,
        dynasty_id=self.dynasty_id,
        name=f"{season_year} NFL Draft",
        description="7-round NFL Draft selection process",
        user_team_id=None,  # Will be set dynamically at runtime
        enable_persistence=self.enable_persistence
    )

    # Store event in database
    self.event_db_api.add_event(draft_event)
```

**Key Considerations**:
- Creates DraftDayEvent with all required metadata
- `user_team_id` set to `None` initially (resolved at runtime)
- Respects `enable_persistence` flag for testing/demo modes

---

### 2. DraftDayEvent

**File**: `src/events/draft_day_event.py`

**Event Type**: `DRAFT_DAY`

**Purpose**: Orchestrate full 7-round NFL draft with AI automation

**Key Attributes**:
```python
class DraftDayEvent(BaseEvent):
    """Event representing the NFL Draft Day."""

    def __init__(
        self,
        season_year: int,
        date: date,
        dynasty_id: str,
        name: str = "NFL Draft",
        description: str = "7-round NFL Draft",
        user_team_id: Optional[int] = None,
        enable_persistence: bool = True
    ):
        super().__init__(
            event_type=EventType.DRAFT_DAY,
            season_year=season_year,
            date=date,
            dynasty_id=dynasty_id,
            name=name,
            description=description
        )
        self.user_team_id = user_team_id
        self.enable_persistence = enable_persistence
```

**Execution Logic**:
```python
def execute(self) -> EventResult:
    """Execute draft event.

    If draft already completed interactively (all 262 picks made),
    skip execution and return success.

    Otherwise, simulate remaining AI picks.
    """
    # Check if draft already completed
    draft_progress = self._check_draft_completion()

    if draft_progress["completed"]:
        return EventResult(
            success=True,
            message=f"Draft already completed interactively ({draft_progress['picks_made']}/262 picks)",
            data={"interactive_completion": True}
        )

    # Execute AI simulation for remaining picks
    result = self.draft_manager.simulate_draft(
        start_pick=draft_progress["current_pick"],
        user_team_id=self.user_team_id
    )

    return EventResult(
        success=True,
        message=f"Draft completed: {result['picks_made']} picks simulated",
        data=result
    )
```

**Key Behavior**:
- Checks if draft already completed interactively before executing
- Supports resuming from specific pick number
- Skips execution gracefully if user completed all picks manually
- Falls back to AI simulation for remaining picks if user stops mid-draft

**Modification Needed**:
- Add dynamic `user_team_id` resolution from `DynastyStateAPI` at execution time
- Support resumable state via `current_draft_pick` field

---

### 3. SimulationController

**File**: `ui/controllers/simulation_controller.py`

**New Responsibility**: Detect interactive events before advancing calendar

**New Method**:
```python
def check_for_interactive_events(self, target_date: date) -> Optional[Dict[str, Any]]:
    """Check if target date has interactive events that require user action.

    Args:
        target_date: The date to check for interactive events

    Returns:
        Dict with event info if interactive event found, None otherwise

    Example return value:
    {
        "event_type": "DRAFT_DAY",
        "date": date(2025, 4, 24),
        "name": "2025 NFL Draft",
        "description": "7-round NFL Draft selection process",
        "event_id": 123
    }
    """
    # Query EventDatabaseAPI for events on target_date
    events = self.event_db_api.get_events_by_date(
        dynasty_id=self.dynasty_id,
        target_date=target_date
    )

    # Check for interactive event types
    INTERACTIVE_EVENTS = {EventType.DRAFT_DAY}

    for event in events:
        if event.event_type in INTERACTIVE_EVENTS:
            # Check if event already executed
            if event.executed:
                continue

            return {
                "event_type": event.event_type.name,
                "date": event.date,
                "name": event.name,
                "description": event.description,
                "event_id": event.event_id,
                "season_year": event.season_year
            }

    return None
```

**New Signal**:
```python
class SimulationController(QObject):
    # Existing signals
    simulation_advanced = Signal(dict)
    phase_changed = Signal(str)

    # NEW: Signal emitted when interactive event detected
    interactive_event_detected = Signal(dict)  # {event_type, date, name, description, event_id}
```

**Modified Methods**:

**advance_day()** - Before advancing, check for interactive events:
```python
def advance_day(self) -> bool:
    """Advance simulation by one day.

    Returns:
        bool: True if advanced successfully, False if interactive event detected
    """
    # Get target date (tomorrow)
    current_date = self.data_model.get_current_date()
    target_date = current_date + timedelta(days=1)

    # Check for interactive events BEFORE advancing
    interactive_event = self.check_for_interactive_events(target_date)

    if interactive_event:
        # Emit signal to pause simulation and show dialog
        self.interactive_event_detected.emit(interactive_event)
        return False  # Don't advance yet

    # Normal advancement logic
    result = self.data_model.advance_to_date(target_date)

    if result["success"]:
        self.simulation_advanced.emit(result)
        return True
    else:
        self._show_error(result["error"])
        return False
```

**advance_week()** - Check each day in the week:
```python
def advance_week(self) -> bool:
    """Advance simulation by one week (7 days).

    Returns:
        bool: True if advanced full week, False if interactive event detected
    """
    for day in range(7):
        if not self.advance_day():
            # Interactive event detected, stop advancement
            return False

    return True
```

**Key Considerations**:
- Interactive check happens BEFORE calendar advancement
- Simulation pauses when interactive event detected
- Event remains unexecuted until user completes interaction
- Supports resuming simulation after interactive event completion

---

### 4. MainWindow

**File**: `ui/main_window.py`

**New Connection**:
```python
def _connect_signals(self):
    """Connect signals from controllers to view handlers."""

    # Existing connections
    self.simulation_controller.simulation_advanced.connect(self._on_simulation_advanced)
    self.simulation_controller.phase_changed.connect(self._on_phase_changed)

    # NEW: Connect interactive event detection
    self.simulation_controller.interactive_event_detected.connect(self.on_draft_day_event)
```

**New Handler**:
```python
def on_draft_day_event(self, event_info: Dict[str, Any]) -> None:
    """Handle draft day event detection.

    Args:
        event_info: Dict containing:
            - event_type: "DRAFT_DAY"
            - date: date(2025, 4, 24)
            - name: "2025 NFL Draft"
            - description: "7-round NFL Draft selection process"
            - event_id: 123
            - season_year: 2025
    """
    # Check if draft already in progress
    if self.draft_in_progress:
        QMessageBox.warning(
            self,
            "Draft In Progress",
            "Draft dialog is already open. Please complete or close the current draft first."
        )
        return

    # Mark draft as in progress
    self.draft_in_progress = True

    # Disable simulation controls
    self._disable_simulation_controls()

    # Create draft dialog controller
    from ui.controllers.draft_controller import DraftDialogController

    self.draft_controller = DraftDialogController(
        dynasty_id=self.dynasty_id,
        season_year=event_info["season_year"],
        database_path=self.database_path,
        user_team_id=self._get_user_team_id()  # NEW helper method
    )

    # Create and show draft dialog
    from ui.dialogs.draft_day_dialog import DraftDayDialog

    self.draft_dialog = DraftDayDialog(
        controller=self.draft_controller,
        parent=self
    )

    # Connect dialog signals
    self.draft_dialog.pick_made.connect(self._on_draft_pick_made)
    self.draft_dialog.draft_completed.connect(self._on_draft_completed)
    self.draft_dialog.finished.connect(self._on_draft_dialog_closed)

    # Show dialog (non-modal)
    self.draft_dialog.show()

    # Update status bar
    self.statusBar().showMessage(
        f"Draft Day: {event_info['date']} - Make your picks!"
    )

def _get_user_team_id(self) -> int:
    """Get user's team ID from dynasty state.

    Returns:
        int: User team ID (1-32)
    """
    dynasty_state = self.dynasty_state_api.get_dynasty_state(self.dynasty_id)
    return dynasty_state.get("user_team_id", 1)  # Default to team 1 if not set

def _disable_simulation_controls(self) -> None:
    """Disable simulation advance buttons during draft."""
    # Disable buttons in toolbar/menu
    self.advance_day_action.setEnabled(False)
    self.advance_week_action.setEnabled(False)
    # Update status
    self.statusBar().showMessage("Simulation paused for draft")

def _enable_simulation_controls(self) -> None:
    """Re-enable simulation controls after draft."""
    self.advance_day_action.setEnabled(True)
    self.advance_week_action.setEnabled(True)

def _on_draft_pick_made(self, pick_number: int) -> None:
    """Update status bar when user makes a pick.

    Args:
        pick_number: Pick number just completed (1-262)
    """
    self.statusBar().showMessage(
        f"Draft in progress: Pick {pick_number}/262 completed"
    )

def _on_draft_completed(self) -> None:
    """Handle draft completion signal from dialog.

    Marks draft event as executed and advances calendar to next day.
    """
    # Mark event as executed in database
    event_info = self.draft_dialog.event_info
    self.event_db_api.mark_event_executed(
        event_id=event_info["event_id"],
        dynasty_id=self.dynasty_id
    )

    # Reset draft state
    self.dynasty_state_api.update_draft_state(
        dynasty_id=self.dynasty_id,
        draft_in_progress=False,
        current_draft_pick=0
    )

    # Update status
    self.statusBar().showMessage("Draft completed! Resuming simulation...", 3000)

    # Re-enable controls
    self._enable_simulation_controls()

    # Advance calendar to next day
    self.simulation_controller.advance_day()

def _on_draft_dialog_closed(self) -> None:
    """Handle draft dialog close (via X button or ESC).

    Saves current draft state and allows resuming later.
    """
    self.draft_in_progress = False

    # Re-enable simulation controls (user can advance past draft date)
    self._enable_simulation_controls()

    # Update status
    current_pick = self.draft_controller.get_current_pick()

    if current_pick < 262:
        self.statusBar().showMessage(
            f"Draft paused at pick {current_pick + 1}/262. "
            f"Remaining picks will be simulated automatically.",
            5000
        )

    # Clean up references
    self.draft_dialog = None
    self.draft_controller = None
```

**State Tracking**:
```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Draft state tracking
        self.draft_in_progress = False
        self.draft_dialog = None
        self.draft_controller = None
```

**Key Behavior**:
- Pauses simulation when draft detected
- Shows non-modal dialog (user can minimize/restore)
- Tracks draft state to prevent multiple dialogs
- Re-enables simulation after draft completion
- Saves draft progress when dialog closed mid-draft

---

### 5. DraftDialogController

**File**: `ui/controllers/draft_controller.py` (NEW - replaces DraftDemoController)

**Responsibility**: Business logic for draft operations, replacing DraftDemoController

**Dependencies**:
```python
class DraftDialogController:
    """Controller for draft day dialog business logic."""

    def __init__(
        self,
        dynasty_id: str,
        season_year: int,
        database_path: str,
        user_team_id: int
    ):
        self.dynasty_id = dynasty_id
        self.season_year = season_year
        self.user_team_id = user_team_id

        # Initialize database APIs
        self.draft_order_api = DraftOrderDatabaseAPI(database_path)
        self.draft_class_api = DraftClassAPI(database_path)
        self.draft_manager = DraftManager(
            dynasty_id=dynasty_id,
            database_path=database_path,
            enable_persistence=True
        )

        # Initialize state
        self.draft_order = None
        self.draft_class = None
        self.current_pick = 0
```

**Key Methods**:
```python
def load_draft_data(self) -> Dict[str, Any]:
    """Load draft order and draft class from database.

    Returns:
        Dict with draft_order, draft_class, current_pick
    """
    # Load draft order
    self.draft_order = self.draft_order_api.get_draft_order(
        dynasty_id=self.dynasty_id,
        season_year=self.season_year
    )

    # Load draft class
    self.draft_class = self.draft_class_api.get_draft_class(
        dynasty_id=self.dynasty_id,
        season_year=self.season_year
    )

    # Get current pick from dynasty state
    self.current_pick = self._get_current_pick()

    return {
        "draft_order": self.draft_order,
        "draft_class": self.draft_class,
        "current_pick": self.current_pick
    }

def execute_pick(self, player_id: int) -> Dict[str, Any]:
    """Execute a draft pick for user's team.

    Args:
        player_id: ID of player to draft

    Returns:
        Dict with success status and pick details
    """
    pick = self.draft_order[self.current_pick]

    # Validate it's user's pick
    if pick["team_id"] != self.user_team_id:
        return {
            "success": False,
            "error": "Not your team's pick"
        }

    # Execute pick via DraftManager
    result = self.draft_manager.make_pick(
        pick_number=self.current_pick + 1,
        team_id=self.user_team_id,
        player_id=player_id
    )

    if result["success"]:
        self.current_pick += 1
        self._save_draft_progress()

    return result

def simulate_next_pick(self) -> Dict[str, Any]:
    """Simulate AI pick for current non-user team.

    Returns:
        Dict with simulated pick details
    """
    pick = self.draft_order[self.current_pick]

    # Validate it's NOT user's pick
    if pick["team_id"] == self.user_team_id:
        return {
            "success": False,
            "error": "Cannot simulate user's pick"
        }

    # Let DraftManager's AI make the pick
    result = self.draft_manager.simulate_single_pick(
        pick_number=self.current_pick + 1
    )

    if result["success"]:
        self.current_pick += 1
        self._save_draft_progress()

    return result

def get_current_pick(self) -> int:
    """Get current pick number (0-261)."""
    return self.current_pick

def is_user_pick(self) -> bool:
    """Check if current pick belongs to user's team."""
    if self.current_pick >= len(self.draft_order):
        return False

    pick = self.draft_order[self.current_pick]
    return pick["team_id"] == self.user_team_id

def _save_draft_progress(self) -> None:
    """Save current pick to dynasty state."""
    # Update dynasty_state table
    self.draft_manager.dynasty_state_api.update_draft_state(
        dynasty_id=self.dynasty_id,
        draft_in_progress=True,
        current_draft_pick=self.current_pick
    )

def _get_current_pick(self) -> int:
    """Load current pick from dynasty state.

    Returns:
        int: Current pick number (0 if starting fresh)
    """
    state = self.draft_manager.dynasty_state_api.get_dynasty_state(
        self.dynasty_id
    )
    return state.get("current_draft_pick", 0)
```

**Key Differences from DraftDemoController**:
- Uses production database APIs (not mock data)
- Integrates with DynastyStateAPI for resumable state
- Validates user vs AI picks
- Persists draft progress after each pick
- No hardcoded mock data or `_demo_data()` methods

---

### 6. DraftDayDialog

**File**: `ui/dialogs/draft_day_dialog.py` (MOVED from demo/)

**Original Location**: `demo/draft_day_demo/draft_day_dialog.py`

**Modifications**:

**Constructor Change**:
```python
class DraftDayDialog(QDialog):
    """Draft day dialog for interactive draft."""

    # Signals
    pick_made = Signal(int)  # Emits pick_number when pick completed
    draft_completed = Signal()  # Emits when all 262 picks completed

    def __init__(self, controller: DraftDialogController, parent=None):
        """Initialize draft dialog.

        Args:
            controller: DraftDialogController instance (NOT DraftDemoController)
            parent: Parent widget
        """
        super().__init__(parent)

        self.controller = controller
        self.event_info = None  # Will be set by MainWindow

        # Load draft data
        draft_data = self.controller.load_draft_data()

        # Initialize UI with data
        self._init_ui(draft_data)
```

**closeEvent Override**:
```python
def closeEvent(self, event):
    """Handle dialog close - save draft progress.

    Allows user to close dialog mid-draft and resume later.
    """
    current_pick = self.controller.get_current_pick()

    if current_pick < 262:
        # Draft not completed - confirm save
        reply = QMessageBox.question(
            self,
            "Save Draft Progress?",
            f"Draft in progress at pick {current_pick + 1}/262.\n\n"
            f"Save progress and exit? Remaining picks will be simulated automatically.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            # Progress already saved by controller after each pick
            event.accept()
        else:
            event.ignore()  # Don't close
    else:
        # Draft completed
        event.accept()
```

**Pick Execution**:
```python
def _on_make_pick_clicked(self):
    """Handle user clicking 'Make Pick' button."""
    # Get selected player from table
    selected_player_id = self._get_selected_player_id()

    if not selected_player_id:
        QMessageBox.warning(self, "No Selection", "Please select a player to draft.")
        return

    # Execute pick via controller
    result = self.controller.execute_pick(selected_player_id)

    if result["success"]:
        # Emit pick_made signal with pick number
        self.pick_made.emit(self.controller.get_current_pick())

        # Update UI
        self._update_draft_board()

        # Check if draft completed
        if self.controller.get_current_pick() >= 262:
            self.draft_completed.emit()
            self.accept()  # Close dialog
        else:
            # Advance to next pick
            self._advance_to_next_pick()
    else:
        QMessageBox.critical(self, "Pick Failed", result["error"])
```

**Key Modifications**:
1. Accept `DraftDialogController` instead of `DraftDemoController`
2. Add `closeEvent()` to save draft progress
3. Emit `pick_made` and `draft_completed` signals
4. Remove any demo-specific mock data logic

---

## Data Flow Sequence Diagram

```
User                MainWindow           SimulationController      EventDatabaseAPI      DraftDialogController      DraftDayDialog
 |                      |                        |                        |                        |                        |
 |-- Click "Advance" -->|                        |                        |                        |                        |
 |                      |-- advance_day() ------>|                        |                        |                        |
 |                      |                        |-- check events ------->|                        |                        |
 |                      |                        |<-- DRAFT_DAY event ----|                        |                        |
 |                      |<-- interactive_event --|                        |                        |                        |
 |                      |                        |                        |                        |                        |
 |                      |-- on_draft_day_event() |                        |                        |                        |
 |                      |-- disable controls     |                        |                        |                        |
 |                      |-- create controller -->|                        |                        |                        |
 |                      |                        |                        |                        |<-- __init__() ---------|
 |                      |                        |                        |                        |-- load_draft_data() -->|
 |                      |-- show dialog -------->|                        |                        |                        |
 |                      |                        |                        |                        |                        |<-- show() --|
 |<-- Draft Dialog -----|                        |                        |                        |                        |             |
 |    displayed         |                        |                        |                        |                        |             |
 |                      |                        |                        |                        |                        |             |
 |-- Select player ---->|                        |                        |                        |                        |------------>|
 |-- Click "Make Pick"->|                        |                        |                        |                        |------------>|
 |                      |                        |                        |                        |<-- execute_pick() -----|             |
 |                      |                        |                        |                        |-- DraftManager.make_pick() -------->|
 |                      |                        |                        |                        |<-- success result -----|             |
 |                      |<-- pick_made signal ---|                        |                        |                        |             |
 |                      |-- update status bar    |                        |                        |                        |             |
 |                      |                        |                        |                        |                        |<-- UI update |
 |                      |                        |                        |                        |                        |             |
 |-- ... 262 picks ...  |                        |                        |                        |                        |             |
 |                      |                        |                        |                        |                        |             |
 |<-- Draft completed --|                        |                        |                        |                        |             |
 |                      |<-- draft_completed ----|                        |                        |                        |             |
 |                      |-- mark_event_executed->|                        |                        |                        |             |
 |                      |-- reset_draft_state -->|                        |                        |                        |             |
 |                      |-- enable controls      |                        |                        |                        |             |
 |                      |-- advance_day() ------>|                        |                        |                        |             |
 |                      |<-- simulation resumed --|                        |                        |                        |             |
```

## Database Schema Changes

### dynasty_state Table Additions

```sql
ALTER TABLE dynasty_state ADD COLUMN current_draft_pick INTEGER DEFAULT 0;
ALTER TABLE dynasty_state ADD COLUMN draft_in_progress BOOLEAN DEFAULT FALSE;
```

**Field Descriptions**:
- `current_draft_pick`: Pick number (0-261) representing next pick to be made
- `draft_in_progress`: Boolean flag indicating if draft is actively being conducted

**Usage**:
```python
# Start draft
dynasty_state_api.update_draft_state(
    dynasty_id="dynasty_1",
    draft_in_progress=True,
    current_draft_pick=0
)

# After each pick
dynasty_state_api.update_draft_state(
    dynasty_id="dynasty_1",
    current_draft_pick=current_pick + 1
)

# Complete draft
dynasty_state_api.update_draft_state(
    dynasty_id="dynasty_1",
    draft_in_progress=False,
    current_draft_pick=0
)

# Load draft state
state = dynasty_state_api.get_dynasty_state("dynasty_1")
current_pick = state.get("current_draft_pick", 0)
in_progress = state.get("draft_in_progress", False)
```

## Integration Points

### 1. Event Scheduling

**Component**: `OffseasonEventScheduler`

**Integration**: Creates `DraftDayEvent` during offseason initialization

**Code Location**: `src/offseason/offseason_event_scheduler.py:_schedule_milestone_events()`

**Trigger**: Called by `OffseasonToPreseasonHandler` during offseason-to-preseason transition

**Data Flow**:
```
OffseasonToPreseasonHandler
  → OffseasonEventScheduler.__init__()
    → _schedule_milestone_events(season_year)
      → Create DraftDayEvent(date=April 24)
        → EventDatabaseAPI.add_event()
          → SQLite events table
```

---

### 2. Event Detection

**Component**: `SimulationController`

**Integration**: Queries `EventDatabaseAPI` before advancing calendar

**Code Location**: `ui/controllers/simulation_controller.py:check_for_interactive_events()`

**Trigger**: Called by `advance_day()` before executing day advancement

**Data Flow**:
```
User clicks "Advance Day"
  → MainWindow triggers SimulationController.advance_day()
    → check_for_interactive_events(tomorrow)
      → EventDatabaseAPI.get_events_by_date(date, dynasty_id)
        → SQLite events table query
      → Filter for INTERACTIVE_EVENTS (DRAFT_DAY)
        → If found: emit interactive_event_detected signal
        → If not found: continue with normal advancement
```

---

### 3. Event Execution

**Component**: `DraftManager`

**Integration**: Performs draft pick database operations

**Code Location**: `src/offseason/draft_manager.py:make_pick()`

**Trigger**: Called by `DraftDialogController.execute_pick()` when user selects player

**Data Flow**:
```
User selects player in DraftDayDialog
  → Dialog emits pick_made signal
    → DraftDialogController.execute_pick(player_id)
      → DraftManager.make_pick(pick_number, team_id, player_id)
        → PlayerRosterAPI.add_player_to_team()
        → ContractManager.create_rookie_contract()
        → DraftOrderDatabaseAPI.mark_pick_complete()
        → DynastyStateAPI.update_draft_state(current_pick + 1)
```

**Database Operations**:
1. **Player Assignment**: Update `players` table with `team_id`, `status='ACTIVE'`
2. **Contract Creation**: Insert into `contracts` table with rookie scale salary
3. **Draft Order Update**: Mark pick as `completed=1` in `draft_order` table
4. **State Persistence**: Update `dynasty_state.current_draft_pick`

---

### 4. UI Display

**Component**: `MainWindow`

**Integration**: Orchestrates dialog lifecycle and simulation state

**Code Location**: `ui/main_window.py:on_draft_day_event()`

**Trigger**: Receives `interactive_event_detected` signal from `SimulationController`

**Data Flow**:
```
SimulationController emits interactive_event_detected signal
  → MainWindow.on_draft_day_event(event_info)
    → Create DraftDialogController(dynasty_id, season_year, user_team_id)
    → Create DraftDayDialog(controller, parent=self)
    → Connect dialog signals (pick_made, draft_completed, finished)
    → Show dialog (non-modal)
    → Disable simulation controls

User makes picks in dialog
  → Dialog emits pick_made(pick_number) signal
    → MainWindow._on_draft_pick_made(pick_number)
      → Update status bar: "Draft in progress: Pick X/262 completed"

User completes all picks
  → Dialog emits draft_completed signal
    → MainWindow._on_draft_completed()
      → EventDatabaseAPI.mark_event_executed(event_id)
      → DynastyStateAPI.update_draft_state(draft_in_progress=False)
      → Enable simulation controls
      → SimulationController.advance_day()
```

**UI State Management**:
- `draft_in_progress` flag prevents multiple dialogs
- `advance_day_action.setEnabled(False)` disables simulation during draft
- Status bar shows pick progress
- Non-modal dialog allows user to minimize/restore

---

### 5. State Persistence

**Component**: `DynastyStateAPI`

**Integration**: Stores resumable draft progress

**Code Location**: `src/database/dynasty_state_api.py:update_draft_state()`

**Trigger**: Called after each pick by `DraftDialogController._save_draft_progress()`

**Data Flow**:
```
DraftDialogController.execute_pick(player_id)
  → DraftManager.make_pick() completes successfully
    → self.current_pick += 1
    → _save_draft_progress()
      → DynastyStateAPI.update_draft_state(
            dynasty_id=self.dynasty_id,
            draft_in_progress=True,
            current_draft_pick=self.current_pick
        )
        → SQLite dynasty_state table UPDATE
```

**Database Schema**:
```sql
UPDATE dynasty_state
SET current_draft_pick = ?,
    draft_in_progress = ?
WHERE dynasty_id = ?;
```

**Resume Logic**:
```python
# On dialog open, load last saved pick
def load_draft_data():
    state = dynasty_state_api.get_dynasty_state(dynasty_id)
    current_pick = state.get("current_draft_pick", 0)

    # Resume from saved pick
    return {
        "draft_order": draft_order_api.get_draft_order(...),
        "draft_class": draft_class_api.get_draft_class(...),
        "current_pick": current_pick  # 0 if starting fresh, N if resuming
    }
```

## Edge Cases and Error Handling

### 1. Draft Already Completed

**Scenario**: User tries to advance to April 24 after completing draft manually

**Handling**:
```python
# In DraftDayEvent.execute()
draft_progress = self._check_draft_completion()

if draft_progress["completed"]:
    # All 262 picks made interactively
    return EventResult(
        success=True,
        message="Draft already completed interactively",
        data={"interactive_completion": True}
    )
```

**Result**: Event marked as executed, simulation continues normally

---

### 2. User Closes Dialog Mid-Draft

**Scenario**: User closes dialog at pick 50/262

**Handling**:
```python
# In DraftDayDialog.closeEvent()
def closeEvent(self, event):
    current_pick = self.controller.get_current_pick()

    if current_pick < 262:
        reply = QMessageBox.question(
            self,
            "Save Draft Progress?",
            f"Draft in progress at pick {current_pick + 1}/262.\n\n"
            f"Save progress and exit? Remaining picks will be simulated automatically."
        )

        if reply == QMessageBox.Yes:
            # Progress saved after each pick - just accept close
            event.accept()
        else:
            event.ignore()  # Don't close
```

**Result Options**:
1. **User confirms**: Draft state saved at pick 50, dialog closes, simulation re-enabled
2. **User cancels**: Dialog remains open, draft continues
3. **When simulation advances past April 24**: `DraftDayEvent.execute()` simulates remaining 212 picks via AI

---

### 3. Database Lock During Pick

**Scenario**: SQLite database locked when executing pick

**Handling**:
```python
# In DraftManager.make_pick()
try:
    with transaction_context(self.connection, mode="IMMEDIATE"):
        # Perform all pick operations atomically
        self.player_roster_api.add_player_to_team(player_id, team_id)
        self.contract_manager.create_rookie_contract(player_id, team_id, pick_number)
        self.draft_order_api.mark_pick_complete(pick_number)
except sqlite3.OperationalError as e:
    return {
        "success": False,
        "error": f"Database locked: {str(e)}. Please try again."
    }
```

**Result**: Pick fails, user sees error message, can retry pick

---

### 4. User Advances Simulation Before Completing Draft

**Scenario**: User closes draft dialog at pick 100/262, then clicks "Advance Week"

**Handling**:
```python
# In SimulationController.advance_day()
target_date = current_date + timedelta(days=1)
interactive_event = self.check_for_interactive_events(target_date)

if interactive_event and interactive_event["event_type"] == "DRAFT_DAY":
    # Check if draft already started
    draft_state = self.dynasty_state_api.get_dynasty_state(self.dynasty_id)

    if draft_state.get("draft_in_progress"):
        # Draft in progress - show resume dialog
        reply = QMessageBox.question(
            self.parent(),
            "Resume Draft?",
            f"Draft in progress at pick {draft_state['current_draft_pick'] + 1}/262.\n\n"
            f"Resume draft? If you skip, remaining picks will be simulated automatically.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Re-open draft dialog
            self.interactive_event_detected.emit(interactive_event)
            return False
        else:
            # User chooses to skip - let event execute AI simulation
            pass  # Continue with normal advancement
```

**Result Options**:
1. **User resumes**: Draft dialog reopens at pick 101/262
2. **User skips**: `DraftDayEvent.execute()` simulates remaining 162 picks via AI

---

### 5. No User Team ID Set

**Scenario**: Dynasty initialized without `user_team_id` in `dynasty_state`

**Handling**:
```python
# In MainWindow._get_user_team_id()
def _get_user_team_id(self) -> int:
    """Get user's team ID from dynasty state."""
    dynasty_state = self.dynasty_state_api.get_dynasty_state(self.dynasty_id)
    user_team_id = dynasty_state.get("user_team_id")

    if not user_team_id:
        # Prompt user to select team
        from ui.dialogs.team_selection_dialog import TeamSelectionDialog

        dialog = TeamSelectionDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            user_team_id = dialog.selected_team_id

            # Save selection to dynasty state
            self.dynasty_state_api.update_user_team(
                dynasty_id=self.dynasty_id,
                user_team_id=user_team_id
            )
        else:
            # User cancelled - default to team 1
            user_team_id = 1

    return user_team_id
```

**Result**: User prompted to select team on first draft, selection saved for future drafts

---

### 6. Draft Class Missing

**Scenario**: Draft class not generated for season year

**Handling**:
```python
# In DraftDialogController.load_draft_data()
try:
    draft_class = self.draft_class_api.get_draft_class(
        dynasty_id=self.dynasty_id,
        season_year=self.season_year
    )
except DraftClassNotFoundError:
    # Generate draft class on demand
    from src.player_generation.draft_class_generator import DraftClassGenerator

    generator = DraftClassGenerator(
        dynasty_id=self.dynasty_id,
        season_year=self.season_year,
        database_path=self.database_path
    )

    draft_class = generator.generate_draft_class()
    self.draft_class_api.save_draft_class(draft_class)
```

**Result**: Draft class auto-generated if missing, draft continues normally

## Testing Strategy

### Unit Tests

**SimulationController Tests** (`tests/ui/test_simulation_controller_draft.py`):
```python
def test_check_for_interactive_events_draft_day():
    """Test detection of draft day interactive event."""

def test_advance_day_pauses_on_draft_day():
    """Test day advancement stops when draft day detected."""

def test_advance_week_stops_at_draft_day():
    """Test week advancement stops when draft day encountered."""
```

**DraftDialogController Tests** (`tests/ui/test_draft_controller.py`):
```python
def test_load_draft_data():
    """Test loading draft order and draft class."""

def test_execute_pick_user_team():
    """Test executing pick for user's team."""

def test_execute_pick_wrong_team():
    """Test validation of user vs AI pick."""

def test_save_draft_progress():
    """Test saving current pick to dynasty state."""

def test_resume_from_saved_pick():
    """Test loading saved pick and resuming draft."""
```

**MainWindow Tests** (`tests/ui/test_main_window_draft.py`):
```python
def test_on_draft_day_event_creates_dialog():
    """Test draft dialog creation when event detected."""

def test_simulation_disabled_during_draft():
    """Test controls disabled while draft in progress."""

def test_simulation_resumed_after_draft():
    """Test controls re-enabled after draft completion."""

def test_prevent_multiple_draft_dialogs():
    """Test only one draft dialog can be open at a time."""
```

### Integration Tests

**End-to-End Draft Flow** (`tests/integration/test_draft_integration.py`):
```python
def test_full_draft_flow():
    """Test complete draft from detection to completion.

    Steps:
    1. Advance simulation to April 24
    2. Verify draft event detected and dialog shown
    3. Make 5 user picks
    4. Close dialog mid-draft
    5. Verify state saved at pick 5
    6. Reopen dialog
    7. Verify resumed at pick 6
    8. Complete remaining picks
    9. Verify event marked executed
    10. Verify simulation advances to April 25
    """
```

### Manual Testing Checklist

- [ ] Draft event scheduled on April 24 during offseason
- [ ] Simulation pauses when April 24 reached
- [ ] Draft dialog opens with correct draft order
- [ ] User can make picks for their team
- [ ] AI picks execute for other teams
- [ ] Draft progress saves after each pick
- [ ] Status bar updates with pick count
- [ ] Dialog can be closed mid-draft
- [ ] Draft can be resumed from saved pick
- [ ] Draft completion marks event executed
- [ ] Simulation resumes after draft completion
- [ ] Cannot open multiple draft dialogs
- [ ] Advancing past April 24 without completing draft triggers AI simulation
- [ ] Database transaction handles errors gracefully

## Performance Considerations

### Database Operations

**Pick Execution**:
- **Operations per pick**: 4 database writes (player, contract, draft order, dynasty state)
- **Transaction mode**: Use `IMMEDIATE` to prevent lock contention
- **Optimization**: Batch AI picks in single transaction

```python
# Efficient AI simulation (remaining picks)
with transaction_context(self.connection, mode="IMMEDIATE"):
    for pick in remaining_picks:
        self._execute_ai_pick(pick)

    # Single commit for all AI picks
```

### UI Responsiveness

**Draft Board Updates**:
- **Issue**: Refreshing 262-row table after each pick is slow
- **Solution**: Update only affected row instead of full table rebuild

```python
# In DraftDayDialog._on_pick_made()
def _on_pick_made(self, pick_number):
    # Don't rebuild entire table
    # self.draft_board_table.setRowCount(0)  # SLOW
    # self._populate_draft_board()  # SLOW

    # Update only changed row
    row = pick_number - 1
    self.draft_board_table.setItem(row, COL_PLAYER, QTableWidgetItem(player_name))
    self.draft_board_table.setItem(row, COL_STATUS, QTableWidgetItem("✓ PICKED"))
```

### Memory Management

**Draft Class Loading**:
- **Issue**: Loading 262+ player objects at once
- **Solution**: Lazy load player details only when needed

```python
# Load only essential data initially
draft_class_summary = self.draft_class_api.get_draft_class_summary()  # Names, positions, grades

# Load full player details on demand
def _on_player_selected(self, player_id):
    player_details = self.draft_class_api.get_player_details(player_id)
    self._show_player_card(player_details)
```

## Future Enhancements

### Phase 2 Features

1. **Trade Draft Picks**:
   - Allow user to trade picks during draft
   - Update draft order dynamically
   - Show traded picks with team colors

2. **Draft Timer**:
   - Add configurable time limit per pick (e.g., 5 minutes)
   - Auto-simulate pick if timer expires
   - Show countdown in UI

3. **Draft War Room**:
   - Show team needs analysis
   - Best available player rankings
   - Draft grade/value indicators

4. **Draft History**:
   - View past draft classes
   - Compare player development to draft position
   - Track draft grade accuracy

### Phase 3 Features

1. **Multi-User Draft**:
   - Support multiple human users in same dynasty
   - Pass-and-play mode for local multiplayer
   - Network-based online draft

2. **Mock Draft Mode**:
   - Practice draft without affecting dynasty
   - AI-controlled user team for auto-simulation
   - Compare different draft strategies

3. **Draft Analytics**:
   - Show positional scarcity metrics
   - Draft value charts (trade value)
   - Projection systems for player success

## References

### Related Documentation

- **Main UI Architecture**: `docs/architecture/ui_layer_separation.md`
- **Draft System Plan**: `docs/plans/offseason_plan.md` (Section: Draft Phase)
- **Event System**: `src/events/README.md`
- **Season Cycle Controller**: `src/season/season_cycle_controller.py`
- **Database Schema**: `docs/schema/database_schema.md`

### Code Locations

- **Event Scheduling**: `src/offseason/offseason_event_scheduler.py`
- **Draft Event**: `src/events/draft_day_event.py`
- **Draft Manager**: `src/offseason/draft_manager.py`
- **Simulation Controller**: `ui/controllers/simulation_controller.py`
- **Main Window**: `ui/main_window.py`
- **Draft Dialog**: `ui/dialogs/draft_day_dialog.py`
- **Draft Dialog Controller**: `ui/controllers/draft_controller.py`

### Database APIs

- **EventDatabaseAPI**: `src/events/event_database_api.py`
- **DynastyStateAPI**: `src/database/dynasty_state_api.py`
- **DraftOrderDatabaseAPI**: `src/database/draft_order_database_api.py`
- **DraftClassAPI**: `src/database/draft_class_api.py`
- **PlayerRosterAPI**: `src/database/player_roster_api.py`
- **ContractManager**: `src/salary_cap/contract_manager.py`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-23
**Author**: System Architecture Team
