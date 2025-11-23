# NFL Draft Event UI Integration - Research Summary

**Document Version:** 1.0
**Date:** 2025-11-23
**Author:** Claude Code
**Status:** Complete Codebase Analysis

---

## Executive Summary

This document summarizes comprehensive research into integrating the existing Draft Day Dialog into the main UI simulation flow. All required infrastructure exists in the codebase - the task requires **wiring only**, not new development.

**Key Findings:**
- ✅ Draft system infrastructure complete and production-ready
- ✅ Draft dialog exists and is fully functional
- ✅ Event scheduling pattern well-established
- ❌ No event-to-UI dialog trigger mechanism exists
- ❌ DraftDayEvent not scheduled in offseason event scheduler
- ❌ No simulation pause/resume for interactive events

**Implementation Estimate:** ~150 lines of integration code across 5 files

---

## 1. Offseason Event Scheduling Pattern

### 1.1 Current Implementation

**File:** `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/offseason/offseason_event_scheduler.py`

The `OffseasonEventScheduler` creates all offseason events in batch after Super Bowl completion via `PlayoffsToOffseasonHandler`.

**Scheduling Workflow:**
```python
def schedule_offseason_events(
    self,
    super_bowl_date: Date,
    season_year: int,
    dynasty_id: str,
    event_db: EventDatabaseAPI
) -> Dict[str, Any]:
    """Schedule all offseason events after Super Bowl."""

    # Step 1: Calculate all milestones
    milestones = self.milestone_calculator.calculate_milestones_for_season(
        season_year=season_year,
        super_bowl_date=super_bowl_date
    )

    # Step 2-4: Schedule different event types
    deadline_count = self._schedule_deadline_events(...)
    window_count = self._schedule_window_events(...)
    milestone_count = self._schedule_milestone_events(...)
```

**Event Types Scheduled:**
- **Deadline Events** (5): Franchise Tag, Salary Cap Compliance, RFA Tender, Final Roster Cuts, June 1 Releases
- **Window Events** (12 START/END pairs): Legal Tampering, Free Agency, OTA, Minicamp, Training Camp, Preseason Games
- **Milestone Events** (7): Draft, New League Year, Combine, Rookie Minicamp, Schedule Release, Preseason Start

### 1.2 Milestone Event Scheduling Pattern

**Code Location:** `OffseasonEventScheduler._schedule_milestone_events()` (lines 394-514)

```python
def _schedule_milestone_events(
    self,
    milestones: List[Any],
    season_year: int,
    dynasty_id: str,
    event_db: EventDatabaseAPI
) -> int:
    """Schedule all milestone events."""
    count = 0

    # Create dictionary for easy lookup
    milestone_dict = {m.milestone_type: m for m in milestones}

    # Define which milestone types should create basic MilestoneEvents
    milestone_type_map = {
        MilestoneType.DRAFT: "DRAFT",  # ← CURRENTLY MILESTONE EVENT
        MilestoneType.NEW_LEAGUE_YEAR: "NEW_LEAGUE_YEAR",
        MilestoneType.SCOUTING_COMBINE: "COMBINE_START",
        MilestoneType.ROOKIE_MINICAMP: "ROOKIE_MINICAMP",
    }

    # Schedule basic milestone events from calculator
    for milestone_type, event_type in milestone_type_map.items():
        if milestone_type in milestone_dict:
            milestone = milestone_dict[milestone_type]
            milestone_event = MilestoneEvent(
                milestone_type=event_type,
                description=milestone.description,
                season_year=season_year,
                event_date=milestone.date,
                dynasty_id=dynasty_id,
                metadata=milestone.calculation_metadata
            )
            event_db.insert_event(milestone_event)
            count += 1

    # Special case: Schedule Release - uses custom event
    schedule_release_milestone = milestone_dict.get(MilestoneType.SCHEDULE_RELEASE)
    if schedule_release_milestone:
        schedule_release_event = ScheduleReleaseEvent(
            season_year=season_year,
            event_date=schedule_release_milestone.date,
            dynasty_id=dynasty_id,
            event_db=event_db,
            preseason_start_date=preseason_start_milestone.date,
            metadata=schedule_release_milestone.calculation_metadata
        )
        event_db.insert_event(schedule_release_event)
        count += 1
```

**Key Pattern:**
- `MilestoneType.DRAFT` currently creates basic `MilestoneEvent` (informational only)
- `ScheduleReleaseEvent` shows precedent for custom event types with business logic
- **Gap Identified:** Need to replace `MilestoneEvent` with `DraftDayEvent` for interactive draft

---

## 2. Existing Draft Event Types

### 2.1 DraftDayEvent - Complete Orchestrator

**File:** `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/events/draft_day_event.py`

**Purpose:** Full 7-round NFL draft orchestrator with lazy initialization and skip logic

**Key Features:**
```python
class DraftDayEvent(BaseEvent):
    """
    NFL Draft simulation orchestrator event.

    Key Design:
    - Lazy initialization: DraftManager created only when simulate() is called
    - Wraps existing draft logic without modifying DraftManager code
    - Implements BaseEvent contract for polymorphic storage/retrieval
    - Supports both fully automated (all AI) and semi-automated (user + AI) drafts
    """

    def __init__(
        self,
        season_year: int,
        event_date: Date,
        dynasty_id: str,
        database_path: str = "data/database/nfl_simulation.db",
        user_team_id: Optional[int] = None,
        user_picks: Optional[Dict[int, str]] = None,
        verbose: bool = False,
        event_id: Optional[str] = None
    ):
        """Initialize draft day event orchestrator."""
        # Lazy initialization
        self._draft_manager = None
        self._cached_result = None

    def simulate(self) -> EventResult:
        """
        Execute full 7-round NFL draft simulation.

        If draft has already been completed interactively (all picks executed),
        this method skips re-execution and returns a success result.
        """
        # Check if draft already completed (via interactive dialog)
        if self._is_draft_already_completed():
            return EventResult(
                success=True,
                data={"message": "Draft already completed (interactive)"}
            )

        # Lazy initialization of DraftManager
        if self._draft_manager is None:
            from offseason.draft_manager import DraftManager
            self._draft_manager = DraftManager(...)

        # Run full draft simulation
        draft_results = self._draft_manager.simulate_draft(...)
```

**Completion Detection:**
```python
def _is_draft_already_completed(self) -> bool:
    """
    Check if draft has already been executed (all picks completed).

    Queries draft_order table to see if all 224 picks have been executed.
    """
    from database.draft_order_database_api import DraftOrderDatabaseAPI

    draft_order_api = DraftOrderDatabaseAPI(self.database_path)
    picks = draft_order_api.get_draft_order(
        dynasty_id=self.dynasty_id,
        season=self.season_year
    )

    if not picks:
        return False

    # Check if all picks have been executed
    all_executed = all(pick.is_executed for pick in picks)
    return all_executed
```

**Critical Insight:** `DraftDayEvent.simulate()` already has skip logic for interactive completion! When the UI dialog completes picks, the event's `simulate()` method will detect all picks are executed and skip re-execution.

### 2.2 Supporting Draft Event Types

**File:** `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/events/draft_events.py`

- `DraftPickEvent`: Individual pick execution
- `UDFASigningEvent`: Undrafted free agent signings
- `DraftTradeEvent`: Draft pick trades

**Usage:** These are lower-level events used by DraftManager internally.

---

## 3. Existing Draft UI Component

### 3.1 DraftDayDialog - Production-Ready Dialog

**File:** `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/demo/draft_day_demo/draft_day_dialog.py`

**Status:** ✅ Production-ready, fully functional PySide6/Qt dialog

**Key Features:**
- Sortable prospects table with 300+ players
- Team needs display with urgency color coding
- User pick controls with selection validation
- AI simulation with configurable speed
- Pick history tracking (last 15 picks)
- Draft completion detection and summary

**UI Components:**
```python
class DraftDayDialog(QDialog):
    """Interactive Draft Day Simulation Dialog."""

    def __init__(
        self,
        controller: DraftDemoController,  # Business logic controller
        parent=None
    ):
        super().__init__(parent)

        # UI references
        self.current_pick_label: Optional[QLabel] = None
        self.prospects_table: Optional[QTableWidget] = None  # Sortable
        self.team_needs_list: Optional[QListWidget] = None
        self.pick_history_table: Optional[QTableWidget] = None
        self.make_pick_btn: Optional[QPushButton] = None
        self.auto_sim_btn: Optional[QPushButton] = None

    def on_make_pick_clicked(self):
        """User picks selected prospect."""
        selected_rows = self.prospects_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a prospect.")
            return

        # Execute pick through controller
        result = self.controller.execute_user_pick(player_id)
        self.refresh_all_ui()
        self.advance_to_next_pick()

    def on_auto_sim_clicked(self):
        """Simulate until user's next pick."""
        self._auto_sim_next_pick()  # Recursive simulation with 500ms delay

    def execute_cpu_pick(self):
        """AI makes a pick."""
        result = self.controller.execute_ai_pick()
        self.refresh_all_ui()
```

**Controller Pattern:**
```python
# demo/draft_day_demo/draft_demo_controller.py
class DraftDemoController:
    """Business logic for draft dialog."""

    def __init__(self, database_path, dynasty_id, season, user_team_id):
        self.draft_manager = DraftManager(...)
        self.draft_order = draft_manager.get_draft_order()
        self.current_pick_index = 0

    def execute_user_pick(self, player_id: str) -> Dict:
        """Execute user's manual pick."""
        current_pick = self.draft_order[self.current_pick_index]
        result = self.draft_manager.make_draft_selection(
            pick_number=current_pick.overall_pick,
            player_id=player_id
        )
        self.current_pick_index += 1
        return result

    def execute_ai_pick(self) -> Dict:
        """Execute AI pick for current team."""
        current_pick = self.draft_order[self.current_pick_index]
        result = self.draft_manager.make_draft_selection(
            pick_number=current_pick.overall_pick,
            player_id=None  # AI selects best available
        )
        self.current_pick_index += 1
        return result
```

**Dependencies:**
- `DraftManager` (business logic)
- `DraftOrderDatabaseAPI` (224-pick draft order)
- `DraftClassAPI` (prospect data)
- `TeamNeedsAnalyzer` (position needs)
- All infrastructure already exists in `src/`

### 3.2 Dialog Migration Plan

**Current Location:** `demo/draft_day_demo/draft_day_dialog.py`
**Target Location:** `ui/dialogs/draft_day_dialog.py`

**Required Changes:**
1. Move dialog to `ui/dialogs/`
2. Update imports to use `ui.controllers.draft_controller` instead of demo controller
3. Add dialog to `ui/dialogs/__init__.py`
4. No business logic changes needed - dialog is production-ready

---

## 4. Event-to-UI Dialog Pattern

### 4.1 Current State: NO EXISTING PATTERN

**Finding:** The codebase has NO existing mechanism for events to trigger UI dialogs.

**Current Event Execution Flow:**
```
SimulationController.advance_day()
  → SeasonCycleController.advance_day()
    → SimulationExecutor.simulate_day()
      → event.simulate() for each event
        → Returns EventResult
      → Persists results
    → Returns day summary
  → Emits signals for UI refresh
```

**Gap:** Events execute business logic and return results, but have no way to pause simulation and trigger interactive dialogs.

### 4.2 Proposed Pattern: Pre-Simulation Event Detection

**Integration Point:** `SimulationController.advance_day()` (before calling backend)

**New Method Added:**
```python
# ui/controllers/simulation_controller.py
def check_for_draft_day_event(self) -> Optional[Dict[str, Any]]:
    """
    Check if today's date has a draft day event that hasn't been executed yet.

    This method allows the UI layer to intercept draft day events BEFORE
    simulation runs, enabling interactive draft dialog to launch.

    Returns:
        Draft day event dict if found and not yet executed, None otherwise
    """
    try:
        current_date = self.get_current_date()

        # Query events for today
        events = self.event_db.get_events_by_date(
            date=current_date,
            dynasty_id=self.dynasty_id
        )

        # Check for draft day event
        for event in events:
            if event.get('event_type') == 'DRAFT_DAY':
                # Skip if already executed (results field populated)
                if event.get('data', {}).get('results') is not None:
                    self._logger.info(f"Draft day event already executed, skipping")
                    continue

                self._logger.info(
                    f"Draft day event detected: {current_date}, season {event.get('season')}"
                )
                return event

        return None

    except Exception as e:
        self._logger.error(f"Error checking for draft day event: {e}")
        return None
```

**Code Location:** Already exists in `SimulationController` (lines 617-661)!

### 4.3 UI Layer Integration Pattern

**MainWindow Integration:**
```python
# ui/main_window.py (in advance_day action handler)
def on_advance_day_clicked(self):
    """Advance simulation by one day (with draft day detection)."""

    # Check for draft day event BEFORE simulating
    draft_event = self.simulation_controller.check_for_draft_day_event()

    if draft_event:
        # Launch interactive draft dialog
        self._show_draft_day_dialog(draft_event)
        return  # Don't advance day - dialog will handle it

    # Normal day advancement
    result = self.simulation_controller.advance_day()
    self._update_ui_from_day_result(result)

def _show_draft_day_dialog(self, draft_event: Dict):
    """Launch interactive draft day dialog."""
    from ui.dialogs.draft_day_dialog import DraftDayDialog
    from ui.controllers.draft_controller import DraftController

    # Create controller with event metadata
    controller = DraftController(
        database_path=self.db_path,
        dynasty_id=self.dynasty_id,
        season=draft_event['season'],
        user_team_id=self.user_team_id
    )

    # Show non-modal dialog
    dialog = DraftDayDialog(controller, parent=self)
    dialog.finished.connect(self._on_draft_dialog_closed)
    dialog.show()  # Non-modal - allows calendar/standings interaction

def _on_draft_dialog_closed(self, result_code):
    """Handle draft dialog completion."""
    if result_code == QDialog.Accepted:
        # Draft completed - advance day to process event
        self.simulation_controller.advance_day()
        self._refresh_all_ui()
    else:
        # Draft cancelled - do nothing
        pass
```

**Non-Modal Pattern:** Dialog remains open while user can view calendar, standings, and team needs.

---

## 5. Draft System Architecture

### 5.1 Core Components (All Production-Ready)

**DraftManager** - Complete business logic
**File:** `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/offseason/draft_manager.py`

```python
class DraftManager:
    """Manages NFL draft operations with AI team selections."""

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        season_year: int,
        enable_persistence: bool = True
    ):
        self.draft_order_api = DraftOrderDatabaseAPI(database_path)
        self.draft_api = DraftClassAPI(database_path)
        self.roster_api = PlayerRosterAPI(database_path)
        self.depth_chart_api = DepthChartAPI(database_path)
        self.team_needs_analyzer = TeamNeedsAnalyzer(...)

    def simulate_draft(
        self,
        user_team_id: int,
        user_picks: Dict[int, str],
        verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Simulate complete 7-round NFL draft.

        Returns:
            List of 224 pick results
        """

    def make_draft_selection(
        self,
        pick_number: int,
        player_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute single draft pick (user manual or AI).

        If player_id is None, AI selects best available player.
        """
```

**DraftOrderDatabaseAPI** - 224-pick draft order management
**File:** `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/database/draft_order_database_api.py`

**DraftClassAPI** - Prospect generation and tracking
**File:** `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/database/draft_class_api.py`

**TeamNeedsAnalyzer** - Position needs evaluation
**File:** `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/offseason/team_needs_analyzer.py`

**GMArchetypeFactory** - GM personality modifiers
**File:** `/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/src/offseason/gm_archetype_factory.py`

### 5.2 Database Schema

**draft_order table:**
```sql
CREATE TABLE draft_order (
    id INTEGER PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    round_number INTEGER NOT NULL,
    pick_in_round INTEGER NOT NULL,
    overall_pick INTEGER NOT NULL,
    original_team_id INTEGER NOT NULL,
    current_team_id INTEGER NOT NULL,
    is_compensatory BOOLEAN DEFAULT 0,
    player_id TEXT,
    is_executed BOOLEAN DEFAULT 0,
    timestamp INTEGER,
    UNIQUE(dynasty_id, season, overall_pick)
);
```

**draft_class table:**
```sql
CREATE TABLE draft_class (
    player_id TEXT PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    position TEXT NOT NULL,
    college TEXT,
    overall INTEGER NOT NULL,
    is_drafted BOOLEAN DEFAULT 0,
    drafted_by_team_id INTEGER,
    draft_position INTEGER,
    UNIQUE(dynasty_id, season, player_id)
);
```

### 5.3 Data Flow

```
UI Dialog (DraftDayDialog)
  ↓
Controller (DraftController)
  ↓
Business Logic (DraftManager)
  ↓ ↓ ↓
DraftOrderDatabaseAPI  DraftClassAPI  PlayerRosterAPI
  ↓                      ↓               ↓
draft_order table    draft_class    players table
```

---

## 6. Gaps Identified

### Gap 1: DraftDayEvent Not Scheduled ❌

**Current:** `MilestoneType.DRAFT` creates basic `MilestoneEvent`
**Needed:** Replace with `DraftDayEvent` for interactive draft

**Fix Location:** `OffseasonEventScheduler._schedule_milestone_events()` (line 421)

**Estimated Change:** 5-10 lines

```python
# BEFORE
milestone_type_map = {
    MilestoneType.DRAFT: "DRAFT",  # ← Creates MilestoneEvent
    ...
}

# AFTER
# Remove DRAFT from milestone_type_map, add custom handling:
draft_milestone = milestone_dict.get(MilestoneType.DRAFT)
if draft_milestone:
    draft_day_event = DraftDayEvent(
        season_year=season_year,
        event_date=draft_milestone.date,
        dynasty_id=dynasty_id,
        database_path=self.database_path,
        verbose=False
    )
    event_db.insert_event(draft_day_event)
    count += 1
```

### Gap 2: Event-to-UI Dialog Trigger Mechanism ❌

**Current:** No mechanism for events to trigger UI dialogs
**Needed:** Pre-simulation event detection in UI layer

**Fix Location:** `MainWindow` event handlers (advance_day, advance_week, etc.)

**Estimated Change:** 30-40 lines

```python
def on_advance_day_clicked(self):
    # NEW: Check for interactive events before simulating
    draft_event = self.simulation_controller.check_for_draft_day_event()

    if draft_event:
        self._show_draft_day_dialog(draft_event)
        return  # Pause simulation

    # Existing code...
    result = self.simulation_controller.advance_day()
```

### Gap 3: Simulation Pause/Resume for Interactive Events ❌

**Current:** Simulation runs continuously through all events
**Needed:** Ability to pause at draft day and resume after dialog closes

**Fix Location:** UI controller and dialog communication

**Estimated Change:** 20-30 lines (dialog.finished signal handler)

```python
def _on_draft_dialog_closed(self, result_code):
    """Resume simulation after draft dialog closes."""
    if result_code == QDialog.Accepted:
        # Draft completed - advance day to process event
        self.simulation_controller.advance_day()
        self._refresh_all_ui()
```

### Gap 4: Draft Progress Persistence for Save/Resume ⚠️ (Optional)

**Current:** Draft progress stored in draft_order.is_executed flags
**Status:** Already implemented! No additional work needed.

**Evidence:**
- `DraftDayEvent._is_draft_already_completed()` checks `is_executed` flags
- `DraftManager.make_draft_selection()` sets `is_executed=True` for each pick
- If user saves/exits mid-draft and resumes, draft dialog will show correct state

**Conclusion:** This gap is already solved by existing infrastructure.

---

## 7. Recommended Approach

### Phase 1: Schedule DraftDayEvent (5 lines)

**File:** `src/offseason/offseason_event_scheduler.py`
**Method:** `_schedule_milestone_events()`
**Change:** Replace `MilestoneEvent` creation with `DraftDayEvent` for DRAFT milestone

### Phase 2: Add Interactive Event Detection (20 lines)

**File:** `ui/controllers/simulation_controller.py`
**Method:** Already exists! `check_for_draft_day_event()` (lines 617-661)
**Status:** ✅ Complete - no changes needed

### Phase 3: Add Dialog Trigger in MainWindow (30 lines)

**File:** `ui/main_window.py`
**Method:** `on_advance_day_clicked()` (new code)
**Change:** Check for draft event before simulating, launch dialog if found

### Phase 4: Move Dialog to UI Package (20 lines)

**Source:** `demo/draft_day_demo/draft_day_dialog.py`
**Target:** `ui/dialogs/draft_day_dialog.py`
**Changes:** Update imports, add to `__init__.py`, verify Qt parent chain

### Phase 5: Create Draft Controller (50 lines)

**File:** `ui/controllers/draft_controller.py` (new)
**Purpose:** Adapt `DraftDemoController` for production UI use
**Changes:** Remove demo-specific code, add dynasty state tracking

**Total Estimated LOC:** ~150 lines across 5 files

---

## 8. Code Examples

### 8.1 Event Scheduling Pattern (OffseasonEventScheduler)

**Complete Method:**
```python
def _schedule_milestone_events(
    self,
    milestones: List[Any],
    season_year: int,
    dynasty_id: str,
    event_db: EventDatabaseAPI
) -> int:
    """Schedule all milestone events."""
    count = 0

    milestone_dict = {m.milestone_type: m for m in milestones}

    # Basic milestone events
    milestone_type_map = {
        MilestoneType.NEW_LEAGUE_YEAR: "NEW_LEAGUE_YEAR",
        MilestoneType.SCOUTING_COMBINE: "COMBINE_START",
        MilestoneType.ROOKIE_MINICAMP: "ROOKIE_MINICAMP",
        # NOTE: DRAFT removed - now handled with custom DraftDayEvent
    }

    for milestone_type, event_type in milestone_type_map.items():
        if milestone_type in milestone_dict:
            milestone = milestone_dict[milestone_type]
            milestone_event = MilestoneEvent(
                milestone_type=event_type,
                description=milestone.description,
                season_year=season_year,
                event_date=milestone.date,
                dynasty_id=dynasty_id,
                metadata=milestone.calculation_metadata
            )
            event_db.insert_event(milestone_event)
            count += 1

    # Special case: Schedule Release (shows custom event precedent)
    schedule_release_milestone = milestone_dict.get(MilestoneType.SCHEDULE_RELEASE)
    if schedule_release_milestone:
        schedule_release_event = ScheduleReleaseEvent(
            season_year=season_year,
            event_date=schedule_release_milestone.date,
            dynasty_id=dynasty_id,
            event_db=event_db,
            preseason_start_date=preseason_start_milestone.date
        )
        event_db.insert_event(schedule_release_event)
        count += 1

    # NEW: Draft Day Event (custom interactive event)
    draft_milestone = milestone_dict.get(MilestoneType.DRAFT)
    if draft_milestone:
        draft_day_event = DraftDayEvent(
            season_year=season_year,
            event_date=draft_milestone.date,
            dynasty_id=dynasty_id,
            database_path=self.database_path,
            verbose=False
        )
        event_db.insert_event(draft_day_event)
        count += 1

    return count
```

### 8.2 DraftDayEvent.simulate() Skip Logic

**Key Feature:** Detects interactive completion and skips re-execution

```python
def simulate(self) -> EventResult:
    """Execute full 7-round NFL draft simulation."""
    try:
        # Check if draft already completed (via interactive dialog)
        if self._is_draft_already_completed():
            logging.getLogger(__name__).info(
                f"Draft for season {self.season_year} already completed interactively. "
                f"Skipping automated execution."
            )

            return EventResult(
                event_id=self.event_id,
                event_type=self.get_event_type(),
                success=True,
                timestamp=datetime.now(),
                data={
                    "season_year": self.season_year,
                    "total_picks": 224,
                    "draft_type": "interactive",
                    "message": f"{self.season_year} NFL Draft already completed (interactive)"
                }
            )

        # Lazy initialization of DraftManager
        if self._draft_manager is None:
            from offseason.draft_manager import DraftManager
            self._draft_manager = DraftManager(...)

        # Run full draft simulation (only if not completed interactively)
        draft_results = self._draft_manager.simulate_draft(...)

        # Build summary statistics
        result_data = self._build_result_data(draft_results)

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            data=result_data
        )

    except Exception as e:
        return EventResult(
            success=False,
            error_message=f"Draft simulation failed: {str(e)}"
        )
```

### 8.3 SimulationExecutor Event Execution (Current Pattern)

**No Dialog Triggering:**
```python
# src/calendar/simulation_executor.py
def simulate_day(self, date: Date) -> Dict[str, Any]:
    """Execute all events for a given date."""

    # Query events for date
    events = self.event_db.get_events_by_date(
        date=date.to_string(),
        dynasty_id=self.dynasty_id
    )

    results = []
    for event in events:
        # Execute each event directly (no UI interaction)
        event_obj = self._deserialize_event(event)
        result = event_obj.simulate()  # ← Executes business logic
        results.append(result)

    return {
        'success': True,
        'date': date.to_string(),
        'results': results
    }
```

**Gap:** No mechanism for pausing execution and showing interactive UI.

### 8.4 SimulationController.check_for_draft_day_event() (Already Implemented!)

**Detection Method:**
```python
# ui/controllers/simulation_controller.py (lines 617-661)
def check_for_draft_day_event(self) -> Optional[Dict[str, Any]]:
    """
    Check if today's date has a draft day event that hasn't been executed yet.

    Returns:
        Draft day event dict if found and not yet executed, None otherwise
    """
    try:
        current_date = self.get_current_date()

        # Query events for today
        events = self.event_db.get_events_by_date(
            date=current_date,
            dynasty_id=self.dynasty_id
        )

        # Check for draft day event
        for event in events:
            if event.get('event_type') == 'DRAFT_DAY':
                # Skip if already executed (results field populated)
                if event.get('data', {}).get('results') is not None:
                    self._logger.info(f"Draft day event already executed, skipping")
                    continue

                self._logger.info(
                    f"Draft day event detected: {current_date}, season {event.get('season')}"
                )
                return event

        return None

    except Exception as e:
        self._logger.error(f"Error checking for draft day event: {e}")
        return None
```

**Status:** ✅ Already implemented and ready to use!

---

## 9. Key Insights

### 9.1 All Infrastructure Exists

**Complete Systems:**
- ✅ Draft business logic (DraftManager, 224-pick order, AI selection)
- ✅ Draft UI component (DraftDayDialog, sortable tables, team needs)
- ✅ Draft event orchestrator (DraftDayEvent with skip logic)
- ✅ Event scheduling pattern (OffseasonEventScheduler)
- ✅ Interactive event detection (SimulationController.check_for_draft_day_event)

**Required Work:** Wiring only - no new development needed

### 9.2 Event System Designed for Automated Execution

**Current Design:** Events execute business logic and return results - no UI interaction

**Extension Needed:** Add pre-simulation detection layer in UI to intercept interactive events

**Pattern:**
```
UI Layer Check (NEW)
  ↓
If interactive event → Show Dialog → Mark Completed
  ↓
Backend Simulation
  ↓
Event.simulate() → Skip if already completed (EXISTING)
```

### 9.3 Draft Dialog is Production-Ready

**Evidence:**
- Complete PySide6/Qt implementation
- Sortable tables with 300+ prospects
- AI simulation with configurable speed
- Comprehensive error handling
- Draft completion detection

**Migration:** Simple file move + import updates (~20 lines)

### 9.4 Non-Modal Dialog Requirement Adds Complexity

**Challenge:** Dialog must remain open while user can interact with calendar/standings

**Solution:** Use `dialog.show()` instead of `dialog.exec()` (non-modal)

**Implication:** Need robust state management to prevent duplicate draft dialogs

### 9.5 Draft Progress Persistence Already Solved

**Discovery:** `draft_order.is_executed` flags provide save/resume capability

**Benefits:**
- User can save mid-draft and resume later
- `DraftDayEvent.simulate()` detects completion and skips re-execution
- No additional persistence work needed

---

## 10. Implementation Roadmap

### Phase 1: Backend Event Scheduling ✅ **COMPLETE (2025-11-23)**

**Step 1.1: Schedule DraftDayEvent** ✅ **COMPLETE**
- **File:** `src/offseason/offseason_event_scheduler.py` (lines 440-454)
- **Import:** Line 23 - `from events.draft_day_event import DraftDayEvent`
- **Implementation:** Event scheduled with dynamic draft date calculation
- **Note:** Uses `user_team_id=1` as fallback default

**Step 1.2: Dynamic User Team ID Support** ✅ **COMPLETE**
- **Status:** All tests passing (6/6)
- **File:** `src/events/draft_day_event.py`
- **Tests:** `tests/events/test_draft_day_event.py`
- **Details:** See `step_1_2_completion_summary.md`

**Phase 1 Summary:** Backend event scheduling infrastructure complete. DraftDayEvent is now scheduled during offseason and ready for UI integration (Phase 2).

---

### Step 1: Schedule DraftDayEvent (1 hour) [REPLACED BY PHASE 1 ABOVE]

**File:** `src/offseason/offseason_event_scheduler.py`
**Changes:**
- Remove `MilestoneType.DRAFT` from `milestone_type_map`
- Add custom `DraftDayEvent` creation in `_schedule_milestone_events()`
- Add `database_path` parameter to `OffseasonEventScheduler.__init__()`

**Testing:**
- Verify draft event appears in events table with correct date
- Verify event_type is 'DRAFT_DAY' (not 'MILESTONE')

### Step 2: Move Dialog to UI Package (1 hour)

**Files:**
- Move: `demo/draft_day_demo/draft_day_dialog.py` → `ui/dialogs/draft_day_dialog.py`
- Move: `demo/draft_day_demo/draft_demo_controller.py` → `ui/controllers/draft_controller.py`
- Update: `ui/dialogs/__init__.py` (add DraftDayDialog export)
- Update: `ui/controllers/__init__.py` (add DraftController export)

**Changes:**
- Update import statements (remove `../../src` path manipulation)
- Rename `DraftDemoController` to `DraftController`
- Verify Qt parent chain works correctly

**Testing:**
- Import dialog in test script
- Verify all dependencies resolve correctly

### Step 3: Add Dialog Trigger in MainWindow (2 hours)

**File:** `ui/main_window.py`
**New Methods:**
- `_show_draft_day_dialog(draft_event)`
- `_on_draft_dialog_closed(result_code)`

**Modified Methods:**
- `on_advance_day_clicked()` - add draft detection
- `on_advance_week_clicked()` - add draft detection
- `on_advance_to_phase_end_clicked()` - add draft detection

**Pattern:**
```python
def on_advance_day_clicked(self):
    # Check for draft event
    draft_event = self.simulation_controller.check_for_draft_day_event()
    if draft_event:
        self._show_draft_day_dialog(draft_event)
        return

    # Normal advancement
    result = self.simulation_controller.advance_day()
    self._update_ui_from_result(result)
```

**Testing:**
- Advance to draft day in simulation
- Verify dialog opens automatically
- Verify dialog is non-modal (can view other tabs)
- Complete draft and verify event marked as executed

### Step 4: Add State Management (1 hour)

**File:** `ui/main_window.py`
**New Attributes:**
- `self.active_draft_dialog: Optional[DraftDayDialog] = None`

**Purpose:** Prevent duplicate draft dialogs

**Pattern:**
```python
def _show_draft_day_dialog(self, draft_event):
    # Prevent duplicate dialogs
    if self.active_draft_dialog is not None:
        self.active_draft_dialog.raise_()  # Bring to front
        return

    # Create dialog
    controller = DraftController(...)
    dialog = DraftDayDialog(controller, parent=self)

    # Track active dialog
    self.active_draft_dialog = dialog

    # Connect cleanup
    dialog.finished.connect(self._on_draft_dialog_closed)
    dialog.finished.connect(lambda: setattr(self, 'active_draft_dialog', None))

    # Show non-modal
    dialog.show()
```

### Step 5: Add Draft Controller Enhancements (Optional, 1 hour)

**File:** `ui/controllers/draft_controller.py`
**Enhancements:**
- Add `get_draft_status()` method for UI state queries
- Add `export_draft_summary()` for post-draft reports
- Add logging for debugging

### Step 6: Integration Testing (2 hours)

**Test Cases:**
1. Advance to draft day → dialog opens
2. Make manual picks → database updates
3. Auto-sim to next pick → AI picks execute
4. Complete draft → dialog closes, simulation advances
5. Save mid-draft → resume → draft state restored
6. Close dialog without completing → can reopen later

---

## 11. File Locations Reference

### Event System
- `src/offseason/offseason_event_scheduler.py` - Event scheduling after Super Bowl
- `src/events/draft_day_event.py` - DraftDayEvent orchestrator
- `src/events/draft_events.py` - Supporting draft event types
- `src/calendar/simulation_executor.py` - Event execution engine

### Draft Infrastructure
- `src/offseason/draft_manager.py` - Draft business logic
- `src/database/draft_order_database_api.py` - 224-pick draft order
- `src/database/draft_class_api.py` - Prospect data management
- `src/offseason/team_needs_analyzer.py` - Position needs evaluation
- `src/offseason/gm_archetype_factory.py` - GM personality system

### UI Components
- `demo/draft_day_demo/draft_day_dialog.py` - Draft dialog (source)
- `demo/draft_day_demo/draft_demo_controller.py` - Demo controller (source)
- `ui/dialogs/` - Target location for dialog
- `ui/controllers/` - Target location for controller
- `ui/main_window.py` - Main application window
- `ui/controllers/simulation_controller.py` - Simulation orchestration

### Configuration
- `src/calendar/season_milestones.py` - Milestone date calculations
- `src/database/dynasty_state_api.py` - Dynasty state persistence

---

## 12. Dependencies and Risks

### Dependencies
- ✅ PySide6/Qt (already installed)
- ✅ DraftManager (production-ready)
- ✅ All database APIs (complete)
- ✅ Event system infrastructure (complete)

### Risks
1. **Non-Modal Dialog Complexity** (MEDIUM)
   - Risk: User opens multiple draft dialogs
   - Mitigation: Track active dialog in MainWindow state

2. **Event Detection Timing** (LOW)
   - Risk: Draft event detected after execution starts
   - Mitigation: Check for events BEFORE calling advance_day()

3. **Dialog Import Chain** (LOW)
   - Risk: Circular imports when moving dialog to ui/
   - Mitigation: Careful import ordering, use TYPE_CHECKING if needed

4. **Database State Synchronization** (LOW)
   - Risk: Dialog and simulation state desync
   - Mitigation: Use existing `is_executed` flags, single source of truth

---

## 13. Success Criteria

### Functional Requirements
- ✅ Draft dialog opens automatically on draft day
- ✅ User can make manual picks
- ✅ AI teams make realistic selections
- ✅ Draft progress persists across save/exit/resume
- ✅ Dialog is non-modal (can view other tabs)
- ✅ Simulation advances after draft completion
- ✅ No duplicate dialogs can open

### Non-Functional Requirements
- ✅ Code follows existing UI/controller pattern
- ✅ Zero breaking changes to existing systems
- ✅ Integration < 200 lines of new code
- ✅ All existing tests continue passing

---

## 14. Next Steps

1. **Review this document** with user for feedback
2. **Create implementation plan document** with detailed pseudocode
3. **Begin Phase 1:** Schedule DraftDayEvent in OffseasonEventScheduler
4. **Test:** Verify draft event appears correctly in database
5. **Continue phases 2-6** as outlined in Section 10

---

## Document History

**Version 1.0** (2025-11-23)
- Initial comprehensive research summary
- Complete codebase analysis across 15+ files
- Identified 4 gaps, 5 implementation phases
- Estimated ~150 lines of integration code

---

**End of Research Summary**
