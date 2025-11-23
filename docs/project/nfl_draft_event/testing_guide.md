# NFL Draft Event Integration - Testing Guide

**Version**: 1.0
**Last Updated**: 2025-11-23
**Status**: Phase 1-6 Testing Strategy

---

## Table of Contents

1. [Testing Strategy Overview](#testing-strategy-overview)
2. [Phase 1: Backend Event Scheduling](#phase-1-backend-event-scheduling)
3. [Phase 2: UI Component Migration](#phase-2-ui-component-migration)
4. [Phase 3: Draft State Management](#phase-3-draft-state-management)
5. [Phase 4: Event-UI Integration](#phase-4-event-ui-integration)
6. [Phase 5: Non-Modal Behavior](#phase-5-non-modal-behavior)
7. [Phase 6: Completion & Cleanup](#phase-6-completion--cleanup)
8. [Regression Testing](#regression-testing)
9. [Acceptance Criteria](#acceptance-criteria)
10. [Test Data Setup](#test-data-setup)
11. [Known Edge Cases](#known-edge-cases)

---

## Testing Strategy Overview

### Testing Approach

The NFL Draft Event integration requires a multi-layered testing strategy:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions and data flow
- **Manual Tests**: Verify UI behavior and user workflows
- **Regression Tests**: Ensure existing functionality remains intact

### Testing Phases

Each implementation phase has specific testable outcomes:

| Phase | Primary Test Type | Key Validation Points |
|-------|------------------|----------------------|
| Phase 1 | Unit + Integration | Event scheduling, database persistence |
| Phase 2 | Unit + Manual | UI component functionality, dialog behavior |
| Phase 3 | Unit + Integration | State persistence, resume capability |
| Phase 4 | Integration + Manual | Event detection, simulation pause |
| Phase 5 | Manual | Non-modal behavior, UI accessibility |
| Phase 6 | Integration + Manual | Completion cleanup, state reset |

### Test File Locations

```
tests/
├── events/
│   └── test_draft_day_event.py              # Phase 1 tests
├── ui/
│   ├── test_draft_dialog_controller.py      # Phase 2 tests
│   └── test_draft_state_management.py       # Phase 3 tests
└── integration/
    ├── test_draft_event_ui_integration.py   # Phase 4 tests
    └── test_draft_completion.py             # Phase 6 tests
```

---

## Phase 1: Backend Event Scheduling

**Goal**: Verify `DraftDayEvent` is scheduled correctly during offseason initialization.

### Unit Tests

#### Test 1.1: Draft Day Event Created

```python
# File: tests/events/test_draft_day_event.py

import pytest
from datetime import date as Date
from events.draft_events import DraftDayEvent
from offseason.offseason_event_scheduler import OffseasonEventScheduler
from database.event_database_api import EventDatabaseAPI

def test_draft_day_event_scheduled(test_database, dynasty_context):
    """Verify DraftDayEvent is created for April 24 during offseason scheduling."""
    # Arrange
    event_db = EventDatabaseAPI(test_database)
    scheduler = OffseasonEventScheduler(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id']
    )

    # Act
    scheduler.schedule_offseason_events(
        season_year=2026,
        super_bowl_date=Date(2026, 2, 7)
    )

    # Assert
    events = event_db.get_events_by_date(
        dynasty_id=dynasty_context['dynasty_id'],
        event_date=Date(2026, 4, 24)
    )

    draft_events = [e for e in events if e['event_type'] == 'DRAFT_DAY']

    assert len(draft_events) == 1, "Expected exactly one DraftDayEvent"
    assert draft_events[0]['season_year'] == 2026
    assert draft_events[0]['is_executed'] == False
    assert draft_events[0]['event_date'] == Date(2026, 4, 24)
```

#### Test 1.2: Draft Day Event Properties

```python
def test_draft_day_event_properties(dynasty_context):
    """Verify DraftDayEvent has correct properties."""
    # Arrange & Act
    event = DraftDayEvent(
        event_date=Date(2026, 4, 24),
        season_year=2026,
        dynasty_id=dynasty_context['dynasty_id']
    )

    # Assert
    assert event.event_type == 'DRAFT_DAY'
    assert event.is_interactive() == True
    assert event.requires_user_action() == True
    assert event.description == "NFL Draft Day - 7 Rounds, 262 Picks"
    assert event.category == "OFFSEASON"
```

#### Test 1.3: Draft Day Event Execution Hook

```python
def test_draft_day_event_execution(test_database, dynasty_context):
    """Verify DraftDayEvent execute() method returns proper interaction signal."""
    # Arrange
    event = DraftDayEvent(
        event_date=Date(2026, 4, 24),
        season_year=2026,
        dynasty_id=dynasty_context['dynasty_id']
    )

    # Act
    result = event.execute(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id']
    )

    # Assert
    assert result.success == True
    assert result.requires_user_interaction == True
    assert result.interaction_type == 'draft_day'
    assert 'season_year' in result.metadata
    assert result.metadata['season_year'] == 2026
```

### Integration Tests

#### Test 1.4: Full Offseason Scheduling Flow

```python
def test_full_offseason_draft_scheduling(test_database, dynasty_context):
    """Integration test: Verify draft scheduling in full offseason workflow."""
    # Arrange
    from season.season_cycle_controller import SeasonCycleController

    controller = SeasonCycleController(
        dynasty_id=dynasty_context['dynasty_id'],
        database_path=test_database,
        season_year=2025
    )

    # Act - Simulate through Super Bowl
    controller.advance_to_phase('PLAYOFFS')
    controller.advance_through_playoffs()  # Completes Super Bowl

    # Offseason events should be scheduled automatically

    # Assert
    event_db = EventDatabaseAPI(test_database)
    draft_events = event_db.get_events_by_type(
        dynasty_id=dynasty_context['dynasty_id'],
        event_type='DRAFT_DAY'
    )

    assert len(draft_events) == 1
    assert draft_events[0]['event_date'] == Date(2026, 4, 24)
    assert draft_events[0]['is_executed'] == False
```

### Manual Test Checklist

- [ ] **Step 1**: Run full season simulation through Super Bowl
  ```bash
  python main.py
  # Simulate regular season (17 weeks)
  # Simulate playoffs (Wild Card → Divisional → Conference → Super Bowl)
  ```

- [ ] **Step 2**: Verify offseason events scheduled
  ```bash
  sqlite3 data/database/nfl_simulation.db
  > SELECT event_id, event_type, event_date, season_year, is_executed
    FROM events
    WHERE event_type='DRAFT_DAY'
    AND dynasty_id='YOUR_DYNASTY_ID';
  ```

- [ ] **Step 3**: Verify draft event properties
  - `event_date` = 2026-04-24 (79 days after Feb 7 Super Bowl)
  - `season_year` = 2026
  - `is_executed` = 0 (FALSE)
  - `dynasty_id` matches active dynasty

- [ ] **Step 4**: Verify no duplicate events
  ```bash
  > SELECT COUNT(*) FROM events
    WHERE event_type='DRAFT_DAY'
    AND season_year=2026
    AND dynasty_id='YOUR_DYNASTY_ID';
  # Expected: 1
  ```

---

## Phase 2: UI Component Migration

**Goal**: Verify `DraftDayDialog` and `DraftDialogController` work standalone before integration.

### Unit Tests

#### Test 2.1: Draft Dialog Controller Initialization

```python
# File: tests/ui/test_draft_dialog_controller.py

import pytest
from ui.controllers.draft_dialog_controller import DraftDialogController

def test_draft_controller_creation(test_database, dynasty_context):
    """Verify controller creates with proper dependencies."""
    # Arrange & Act
    controller = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22  # Detroit Lions
    )

    # Assert
    assert controller.draft_manager is not None
    assert controller.draft_order_api is not None
    assert controller.player_roster_api is not None
    assert controller.season_year == 2026
    assert controller.user_team_id == 22
```

#### Test 2.2: Draft Order Loading

```python
def test_draft_order_loads(test_database, dynasty_context):
    """Verify draft order loads correctly for controller."""
    # Arrange
    controller = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22
    )

    # Act
    draft_order = controller.get_draft_order()

    # Assert
    assert len(draft_order) == 262, "Expected 7 rounds × 32 teams = 224 picks + 38 compensatory"

    # Verify first pick structure
    first_pick = draft_order[0]
    assert 'pick_number' in first_pick
    assert 'round' in first_pick
    assert 'team_id' in first_pick
    assert first_pick['round'] == 1
    assert first_pick['pick_number'] == 1
```

#### Test 2.3: Draft Class Loading

```python
def test_draft_class_loads(test_database, dynasty_context):
    """Verify draft class prospects load correctly."""
    # Arrange
    controller = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22
    )

    # Act
    prospects = controller.get_available_prospects()

    # Assert
    assert len(prospects) >= 224, "Expected at least 224 prospects (32 teams × 7 rounds)"

    # Verify prospect structure
    first_prospect = prospects[0]
    assert 'player_id' in first_prospect
    assert 'name' in first_prospect
    assert 'position' in first_prospect
    assert 'overall_grade' in first_prospect
    assert 'draft_projection' in first_prospect
```

### Manual Test Checklist

- [ ] **Step 1**: Import dialog components
  ```python
  from ui.dialogs.draft_day_dialog import DraftDayDialog
  from ui.controllers.draft_dialog_controller import DraftDialogController
  ```

- [ ] **Step 2**: Create controller standalone
  ```python
  controller = DraftDialogController(
      database_path="data/database/nfl_simulation.db",
      dynasty_id="test_dynasty",
      season_year=2026,
      user_team_id=22  # Detroit Lions
  )
  ```

- [ ] **Step 3**: Open dialog manually
  ```python
  from PySide6.QtWidgets import QApplication
  import sys

  app = QApplication(sys.argv)
  dialog = DraftDayDialog(controller)
  dialog.show()
  sys.exit(app.exec())
  ```

- [ ] **Step 4**: Verify UI elements display correctly
  - [ ] Prospects table populates with player data
  - [ ] Draft order widget shows pick progression
  - [ ] Team needs panel displays position priorities
  - [ ] User team picks highlighted in draft order
  - [ ] Current pick indicator visible

- [ ] **Step 5**: Test "Make Pick" button
  - [ ] Select a prospect from table
  - [ ] Click "Make Pick" button
  - [ ] Verify pick confirmation dialog appears
  - [ ] Confirm pick
  - [ ] Verify prospect disappears from available list
  - [ ] Verify draft order advances to next pick

- [ ] **Step 6**: Test filtering/sorting
  - [ ] Filter prospects by position (QB, RB, WR, etc.)
  - [ ] Sort by overall grade (high to low)
  - [ ] Sort by draft projection
  - [ ] Verify filters apply correctly

---

## Phase 3: Draft State Management

**Goal**: Verify draft progress saves and resumes correctly across sessions.

### Unit Tests

#### Test 3.1: Draft Progress Persistence

```python
# File: tests/ui/test_draft_state_management.py

import pytest
from ui.controllers.draft_dialog_controller import DraftDialogController
from database.dynasty_state_api import DynastyStateAPI

def test_draft_progress_save(test_database, dynasty_context):
    """Verify draft state saves after picks."""
    # Arrange
    controller = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22
    )

    dynasty_state_api = DynastyStateAPI(test_database)

    # Act - Make 10 picks
    prospects = controller.get_available_prospects()
    for i in range(10):
        controller.make_pick(prospects[i]['player_id'])

    # Save state explicitly
    controller.save_draft_state()

    # Assert
    state = dynasty_state_api.get_dynasty_state(dynasty_context['dynasty_id'])
    assert state['current_draft_pick'] == 11
    assert state['draft_in_progress'] == True
```

#### Test 3.2: Draft Resume from Saved State

```python
def test_draft_resume(test_database, dynasty_context):
    """Verify draft resumes from saved position."""
    # Arrange - Create controller and make 10 picks
    controller1 = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22
    )

    prospects = controller1.get_available_prospects()
    for i in range(10):
        controller1.make_pick(prospects[i]['player_id'])

    controller1.save_draft_state()

    # Act - Create NEW controller (simulates app restart)
    controller2 = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22
    )

    # Assert
    current_pick = controller2.get_current_pick()
    assert current_pick['pick_number'] == 11

    # Verify previous picks marked as completed
    draft_order = controller2.get_draft_order()
    for i in range(10):
        assert draft_order[i]['is_completed'] == True
```

#### Test 3.3: Draft Completion State Reset

```python
def test_draft_completion_resets_state(test_database, dynasty_context):
    """Verify draft completion clears progress flags."""
    # Arrange
    controller = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22
    )

    # Act - Complete all 262 picks
    controller.simulate_full_draft()  # Utility method for testing

    # Assert
    dynasty_state_api = DynastyStateAPI(test_database)
    state = dynasty_state_api.get_dynasty_state(dynasty_context['dynasty_id'])

    assert state['draft_in_progress'] == False
    assert state['current_draft_pick'] == 0  # Reset to 0
```

### Integration Tests

#### Test 3.4: Draft State Across Dialog Close/Reopen

```python
def test_draft_state_dialog_lifecycle(test_database, dynasty_context, qtbot):
    """Integration test: Verify state persists across dialog close/reopen."""
    # Arrange
    from PySide6.QtWidgets import QApplication

    controller1 = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22
    )

    dialog1 = DraftDayDialog(controller1)
    qtbot.addWidget(dialog1)

    # Act - Make 10 picks and close dialog
    prospects = controller1.get_available_prospects()
    for i in range(10):
        dialog1.make_pick(prospects[i]['player_id'])

    dialog1.close()  # Should trigger closeEvent and save state

    # Create new dialog (simulates reopen)
    controller2 = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22
    )

    dialog2 = DraftDayDialog(controller2)
    qtbot.addWidget(dialog2)

    # Assert
    assert dialog2.current_pick_number == 11
    assert dialog2.draft_order_widget.completed_picks == 10
```

### Manual Test Checklist

- [ ] **Step 1**: Start draft and make 10 picks
  ```python
  python main.py
  # Navigate to April 24, 2026
  # Draft dialog opens automatically
  # Make picks 1-10
  ```

- [ ] **Step 2**: Close draft dialog mid-draft
  - [ ] Click "X" button to close dialog
  - [ ] Verify no error messages appear
  - [ ] Verify status bar shows "Draft Paused - Pick 11/262"

- [ ] **Step 3**: Query database state
  ```bash
  sqlite3 data/database/nfl_simulation.db
  > SELECT current_draft_pick, draft_in_progress
    FROM dynasty_state
    WHERE dynasty_id='YOUR_DYNASTY_ID';
  # Expected: current_draft_pick=11, draft_in_progress=1
  ```

- [ ] **Step 4**: Reopen draft dialog
  - [ ] Reopen main window
  - [ ] Navigate to Season tab → Draft section
  - [ ] Click "Resume Draft" button
  - [ ] Verify dialog opens

- [ ] **Step 5**: Verify resume state
  - [ ] Current pick indicator shows "Pick 11"
  - [ ] Picks 1-10 marked completed in draft order
  - [ ] Pick 11 is active selection
  - [ ] Available prospects list excludes picks 1-10

- [ ] **Step 6**: Complete remaining picks
  - [ ] Make picks 11-262 (or use auto-sim)
  - [ ] Verify dialog closes automatically
  - [ ] Verify status bar clears "Draft in Progress"

- [ ] **Step 7**: Query database completion state
  ```bash
  > SELECT current_draft_pick, draft_in_progress
    FROM dynasty_state
    WHERE dynasty_id='YOUR_DYNASTY_ID';
  # Expected: current_draft_pick=0, draft_in_progress=0

  > SELECT is_executed FROM events
    WHERE event_type='DRAFT_DAY'
    AND season_year=2026
    AND dynasty_id='YOUR_DYNASTY_ID';
  # Expected: is_executed=1
  ```

---

## Phase 4: Event-UI Integration

**Goal**: Verify draft event triggers dialog automatically when simulation reaches April 24.

### Integration Tests

#### Test 4.1: Interactive Event Detection

```python
# File: tests/integration/test_draft_event_ui_integration.py

import pytest
from datetime import date as Date
from ui.controllers.simulation_controller import SimulationController

def test_draft_day_triggers_dialog(test_database, dynasty_context, qtbot, monkeypatch):
    """Verify advancing to draft day triggers dialog and pauses simulation."""
    # Arrange
    sim_controller = SimulationController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id']
    )

    # Mock dialog display to test detection without UI
    dialog_triggered = {'value': False}

    def mock_show_draft_dialog(season_year):
        dialog_triggered['value'] = True
        return True  # User completed draft

    monkeypatch.setattr(
        sim_controller,
        '_show_draft_day_dialog',
        mock_show_draft_dialog
    )

    # Act - Advance to April 23
    sim_controller.set_date(Date(2026, 4, 23))

    # Advance one day to April 24
    result = sim_controller.advance_day()

    # Assert
    assert result['status'] == 'paused'
    assert result['reason'] == 'interactive_event'
    assert result['event_type'] == 'DRAFT_DAY'
    assert dialog_triggered['value'] == True
```

#### Test 4.2: Simulation Pause State

```python
def test_simulation_pauses_during_draft(test_database, dynasty_context):
    """Verify simulation remains paused while draft in progress."""
    # Arrange
    from database.dynasty_state_api import DynastyStateAPI

    sim_controller = SimulationController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id']
    )

    dynasty_state_api = DynastyStateAPI(test_database)

    # Set draft in progress state
    dynasty_state_api.update_dynasty_state(
        dynasty_id=dynasty_context['dynasty_id'],
        draft_in_progress=True,
        current_draft_pick=50
    )

    # Act - Try to advance day while draft in progress
    result = sim_controller.advance_day()

    # Assert
    assert result['status'] == 'blocked'
    assert result['reason'] == 'draft_in_progress'
    assert 'Complete draft before advancing' in result['message']
```

#### Test 4.3: Dialog Return Triggers Resume

```python
def test_draft_completion_resumes_simulation(test_database, dynasty_context, monkeypatch):
    """Verify completing draft allows simulation to resume."""
    # Arrange
    sim_controller = SimulationController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id']
    )

    # Mock draft dialog to return completion
    def mock_show_draft_dialog(season_year):
        # Simulate draft completion
        dynasty_state_api = DynastyStateAPI(test_database)
        dynasty_state_api.update_dynasty_state(
            dynasty_id=dynasty_context['dynasty_id'],
            draft_in_progress=False,
            current_draft_pick=0
        )
        return True  # Draft completed

    monkeypatch.setattr(
        sim_controller,
        '_show_draft_day_dialog',
        mock_show_draft_dialog
    )

    # Act - Advance to draft day and complete
    sim_controller.set_date(Date(2026, 4, 23))
    result1 = sim_controller.advance_day()  # April 24 - draft triggers

    # Try to advance again after completion
    result2 = sim_controller.advance_day()  # Should succeed to April 25

    # Assert
    assert result1['status'] == 'paused'
    assert result2['status'] == 'success'
    assert result2['current_date'] == Date(2026, 4, 25)
```

### Manual Test Checklist

- [ ] **Step 1**: Create fresh dynasty
  ```python
  python main.py
  # Create new dynasty
  # Select user team (e.g., Detroit Lions)
  ```

- [ ] **Step 2**: Simulate through regular season
  - [ ] Advance through 18 weeks (17 games + bye)
  - [ ] Verify regular season completes
  - [ ] Check standings finalized

- [ ] **Step 3**: Simulate through playoffs
  - [ ] Advance through Wild Card round
  - [ ] Advance through Divisional round
  - [ ] Advance through Conference Championships
  - [ ] Advance through Super Bowl (Feb 7)

- [ ] **Step 4**: Verify offseason events scheduled
  - [ ] Check calendar for franchise tag deadline (Feb 25)
  - [ ] Check calendar for free agency start (March 12)
  - [ ] Check calendar for draft day (April 24)

- [ ] **Step 5**: Advance to April 23
  - [ ] Click "Advance Day" repeatedly until April 23
  - [ ] Verify calendar shows April 23, 2026
  - [ ] Verify no dialog opens yet

- [ ] **Step 6**: Advance to April 24 (Draft Day)
  - [ ] Click "Advance Day" button
  - [ ] **VERIFY**: Simulation pauses
  - [ ] **VERIFY**: Draft Day Dialog appears automatically
  - [ ] **VERIFY**: Status bar shows "Draft in Progress - Pick 1/262"
  - [ ] **VERIFY**: "Advance Day" button becomes disabled

- [ ] **Step 7**: Verify pause state persists
  - [ ] Try clicking "Advance Day" (should be disabled)
  - [ ] Try clicking "Advance Week" (should be disabled)
  - [ ] Verify status message explains draft must complete

---

## Phase 5: Non-Modal Behavior

**Goal**: Verify dialog is non-modal and other UI features remain accessible during draft.

### Manual Test Checklist

- [ ] **Step 1**: Open draft dialog on April 24
  ```python
  python main.py
  # Advance to April 24
  # Draft dialog opens automatically
  ```

- [ ] **Step 2**: Verify dialog is non-modal
  - [ ] Draft dialog should NOT block main window
  - [ ] Main window should remain fully interactive
  - [ ] Dialog should stay on top but allow access to main window

- [ ] **Step 3**: Test Team tab accessibility
  - [ ] Click "Team" tab in main window
  - [ ] **VERIFY**: Tab switches successfully
  - [ ] View team roster
  - [ ] **VERIFY**: Roster displays correctly
  - [ ] View depth chart
  - [ ] **VERIFY**: Depth chart displays correctly
  - [ ] Switch back to Season tab
  - [ ] **VERIFY**: Draft dialog still visible

- [ ] **Step 4**: Test Player tab accessibility
  - [ ] Click "Player" tab in main window
  - [ ] **VERIFY**: Tab switches successfully
  - [ ] Search for a player
  - [ ] **VERIFY**: Player search works
  - [ ] View player details
  - [ ] **VERIFY**: Player stats display correctly

- [ ] **Step 5**: Test Offseason tab accessibility
  - [ ] Click "Offseason" tab in main window
  - [ ] **VERIFY**: Tab switches successfully
  - [ ] View free agents
  - [ ] **VERIFY**: Free agent list displays
  - [ ] View franchise tag candidates
  - [ ] **VERIFY**: Tag candidates display

- [ ] **Step 6**: Verify simulation controls disabled
  - [ ] Return to Season tab
  - [ ] Try clicking "Advance Day"
  - [ ] **VERIFY**: Button is disabled/grayed out
  - [ ] Try clicking "Advance Week"
  - [ ] **VERIFY**: Button is disabled/grayed out
  - [ ] **VERIFY**: Tooltip explains "Complete draft to continue"

- [ ] **Step 7**: Test status bar updates
  - [ ] Make a pick in draft dialog
  - [ ] **VERIFY**: Status bar updates to "Pick 2/262"
  - [ ] Make 10 more picks
  - [ ] **VERIFY**: Status bar updates to "Pick 12/262"
  - [ ] **VERIFY**: Pick counter increments correctly

- [ ] **Step 8**: Test dialog minimize/restore
  - [ ] Minimize draft dialog
  - [ ] **VERIFY**: Status bar still shows draft progress
  - [ ] Access other UI features
  - [ ] Restore draft dialog
  - [ ] **VERIFY**: Draft state unchanged

- [ ] **Step 9**: Test dialog close mid-draft
  - [ ] Close draft dialog (X button)
  - [ ] **VERIFY**: Dialog closes without error
  - [ ] **VERIFY**: Status bar shows "Draft Paused - Pick X/262"
  - [ ] **VERIFY**: Can still access all UI features
  - [ ] **VERIFY**: Simulation controls remain disabled

- [ ] **Step 10**: Test draft resume
  - [ ] Click "Resume Draft" in Season tab
  - [ ] **VERIFY**: Draft dialog reopens
  - [ ] **VERIFY**: Resumes from correct pick number
  - [ ] **VERIFY**: Previous picks marked completed

---

## Phase 6: Completion & Cleanup

**Goal**: Verify draft completion properly cleans up state and allows simulation to continue.

### Integration Tests

#### Test 6.1: Draft Completion Cleanup

```python
# File: tests/integration/test_draft_completion.py

import pytest
from datetime import date as Date
from ui.controllers.draft_dialog_controller import DraftDialogController
from database.dynasty_state_api import DynastyStateAPI
from database.event_database_api import EventDatabaseAPI

def test_draft_completion_marks_event_executed(test_database, dynasty_context):
    """Verify draft completion marks event as executed."""
    # Arrange
    controller = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22
    )

    event_db = EventDatabaseAPI(test_database)

    # Get draft event
    draft_events = event_db.get_events_by_type(
        dynasty_id=dynasty_context['dynasty_id'],
        event_type='DRAFT_DAY'
    )
    draft_event_id = draft_events[0]['event_id']

    # Act - Complete all 262 picks
    controller.simulate_full_draft()

    # Assert - Event marked executed
    event = event_db.get_event_by_id(draft_event_id)
    assert event['is_executed'] == True

    # Assert - Dynasty state cleared
    dynasty_state_api = DynastyStateAPI(test_database)
    state = dynasty_state_api.get_dynasty_state(dynasty_context['dynasty_id'])
    assert state['draft_in_progress'] == False
    assert state['current_draft_pick'] == 0
```

#### Test 6.2: Prevent Draft Re-execution

```python
def test_draft_does_not_retrigger_after_completion(test_database, dynasty_context):
    """Verify draft doesn't re-trigger after completion in subsequent seasons."""
    # Arrange
    sim_controller = SimulationController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id']
    )

    # Complete 2026 draft
    sim_controller.set_date(Date(2026, 4, 24))
    sim_controller.advance_day()  # Triggers and completes draft

    # Act - Advance to 2027 draft day
    sim_controller.set_date(Date(2027, 4, 23))
    result = sim_controller.advance_day()

    # Assert - New draft event for 2027 should trigger
    assert result['status'] == 'paused'
    assert result['event_type'] == 'DRAFT_DAY'

    # But 2026 draft should NOT re-execute
    event_db = EventDatabaseAPI(test_database)
    events_2026 = event_db.get_events_by_date(
        dynasty_id=dynasty_context['dynasty_id'],
        event_date=Date(2026, 4, 24)
    )

    draft_2026 = [e for e in events_2026 if e['event_type'] == 'DRAFT_DAY'][0]
    assert draft_2026['is_executed'] == True  # Still marked executed
```

#### Test 6.3: All Picks Persisted to Database

```python
def test_all_draft_picks_persisted(test_database, dynasty_context):
    """Verify all 262 picks saved to database."""
    # Arrange
    from database.player_roster_api import PlayerRosterAPI

    controller = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22
    )

    player_roster_api = PlayerRosterAPI(test_database)

    # Act - Complete draft
    controller.simulate_full_draft()

    # Assert - Query all rookies added
    rookies_query = """
        SELECT COUNT(*) as rookie_count
        FROM player_rosters
        WHERE dynasty_id = ?
        AND years_experience = 0
        AND contract_type = 'ROOKIE'
    """

    result = player_roster_api.execute_query(
        rookies_query,
        (dynasty_context['dynasty_id'],)
    )

    assert result[0]['rookie_count'] == 262
```

### Manual Test Checklist

- [ ] **Step 1**: Complete full draft (262 picks)
  ```python
  python main.py
  # Advance to April 24, 2026
  # Draft dialog opens
  # Complete all 262 picks (or use auto-sim feature)
  ```

- [ ] **Step 2**: Verify dialog closes automatically
  - [ ] After pick 262, dialog should close
  - [ ] No error messages appear
  - [ ] Status bar updates

- [ ] **Step 3**: Verify status bar clears draft state
  - [ ] Status bar should NO longer show "Draft in Progress"
  - [ ] Status bar should show current date (April 24, 2026)
  - [ ] Simulation phase should remain "Offseason"

- [ ] **Step 4**: Verify simulation controls re-enabled
  - [ ] "Advance Day" button should be enabled
  - [ ] "Advance Week" button should be enabled
  - [ ] Click "Advance Day"
  - [ ] **VERIFY**: Advances to April 25 successfully

- [ ] **Step 5**: Query database event state
  ```bash
  sqlite3 data/database/nfl_simulation.db
  > SELECT event_id, is_executed, event_date
    FROM events
    WHERE event_type='DRAFT_DAY'
    AND season_year=2026
    AND dynasty_id='YOUR_DYNASTY_ID';
  # Expected: is_executed=1 (TRUE)
  ```

- [ ] **Step 6**: Query database dynasty state
  ```bash
  > SELECT draft_in_progress, current_draft_pick
    FROM dynasty_state
    WHERE dynasty_id='YOUR_DYNASTY_ID';
  # Expected: draft_in_progress=0, current_draft_pick=0
  ```

- [ ] **Step 7**: Verify rookies added to rosters
  ```bash
  > SELECT COUNT(*) FROM player_rosters
    WHERE dynasty_id='YOUR_DYNASTY_ID'
    AND years_experience=0
    AND contract_type='ROOKIE';
  # Expected: 262 (or close, depending on compensatory picks)
  ```

- [ ] **Step 8**: Advance to next season's draft
  - [ ] Continue simulating through 2026 season
  - [ ] Complete 2026 regular season
  - [ ] Complete 2026 playoffs
  - [ ] Advance to April 24, 2027
  - [ ] **VERIFY**: NEW draft event triggers for 2027
  - [ ] **VERIFY**: 2026 draft does NOT re-trigger

- [ ] **Step 9**: Query 2026 draft event again
  ```bash
  > SELECT is_executed FROM events
    WHERE event_type='DRAFT_DAY'
    AND season_year=2026
    AND dynasty_id='YOUR_DYNASTY_ID';
  # Expected: is_executed=1 (still TRUE, not re-executed)
  ```

- [ ] **Step 10**: Test draft history view
  - [ ] Navigate to Offseason tab
  - [ ] Click "Draft History" section
  - [ ] **VERIFY**: 2026 draft appears in history
  - [ ] **VERIFY**: All 262 picks visible
  - [ ] **VERIFY**: Can filter by team/position/round

---

## Regression Testing

**Goal**: Ensure existing functionality remains intact after draft integration.

### Critical Regression Tests

#### Regression Test 1: Franchise Tag Events

```python
def test_franchise_tag_events_still_work(test_database, dynasty_context):
    """Verify franchise tag events execute correctly after draft integration."""
    from events.contract_events import FranchiseTagEvent
    from datetime import date as Date

    # Arrange
    event = FranchiseTagEvent(
        event_date=Date(2026, 2, 25),
        season_year=2026,
        dynasty_id=dynasty_context['dynasty_id'],
        team_id=22,
        player_id=1001
    )

    # Act
    result = event.execute(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id']
    )

    # Assert
    assert result.success == True
    assert result.requires_user_interaction == False
```

#### Regression Test 2: Free Agency Events

```python
def test_free_agency_events_still_work(test_database, dynasty_context):
    """Verify free agency events execute correctly."""
    from events.free_agency_events import UFASigningEvent
    from datetime import date as Date

    # Arrange
    event = UFASigningEvent(
        event_date=Date(2026, 3, 15),
        season_year=2026,
        dynasty_id=dynasty_context['dynasty_id'],
        team_id=22,
        player_id=2001,
        contract_years=3,
        total_value=30000000
    )

    # Act
    result = event.execute(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id']
    )

    # Assert
    assert result.success == True
```

#### Regression Test 3: Regular Season Games

```python
def test_regular_season_games_still_simulate(test_database, dynasty_context):
    """Verify regular season games still simulate correctly."""
    from calendar.simulation_executor import SimulationExecutor
    from datetime import date as Date

    # Arrange
    executor = SimulationExecutor(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id']
    )

    # Act - Execute game on Week 1
    result = executor.execute_scheduled_events(Date(2025, 9, 7))

    # Assert
    assert result['games_played'] > 0
    assert result['status'] == 'success'
```

#### Regression Test 4: Playoff Simulation

```python
def test_playoffs_still_work(test_database, dynasty_context):
    """Verify playoff system still functions correctly."""
    from season.season_cycle_controller import SeasonCycleController

    # Arrange
    controller = SeasonCycleController(
        dynasty_id=dynasty_context['dynasty_id'],
        database_path=test_database,
        season_year=2025
    )

    # Simulate through regular season
    controller.advance_to_phase('PLAYOFFS')

    # Act - Simulate playoffs
    result = controller.advance_through_playoffs()

    # Assert
    assert result['super_bowl_winner'] is not None
    assert result['status'] == 'completed'
```

### Manual Regression Checklist

- [ ] **Test 1**: Franchise tag events
  - [ ] Create dynasty
  - [ ] Advance to franchise tag deadline (Feb 25)
  - [ ] Apply franchise tag to player
  - [ ] **VERIFY**: Tag applies successfully
  - [ ] **VERIFY**: Contract created correctly

- [ ] **Test 2**: Free agency events
  - [ ] Advance to free agency start (March 12)
  - [ ] Sign a free agent
  - [ ] **VERIFY**: Signing processes correctly
  - [ ] **VERIFY**: Cap space deducted

- [ ] **Test 3**: Regular season games
  - [ ] Advance to Week 1 (September)
  - [ ] Simulate games
  - [ ] **VERIFY**: Games execute normally
  - [ ] **VERIFY**: Stats recorded correctly

- [ ] **Test 4**: Playoff simulation
  - [ ] Complete regular season
  - [ ] Advance to playoffs
  - [ ] Simulate Wild Card round
  - [ ] **VERIFY**: Playoff bracket generates
  - [ ] Simulate through Super Bowl
  - [ ] **VERIFY**: Super Bowl winner determined

- [ ] **Test 5**: Other offseason events unaffected
  - [ ] Schedule release (May 8)
  - [ ] OTAs (May 20)
  - [ ] Training camp (July 23)
  - [ ] Preseason games (August)
  - [ ] **VERIFY**: All execute normally

- [ ] **Test 6**: Calendar system integrity
  - [ ] Create new dynasty
  - [ ] Check calendar for all events
  - [ ] **VERIFY**: All offseason events present
  - [ ] **VERIFY**: Draft day scheduled correctly
  - [ ] **VERIFY**: No duplicate events

---

## Acceptance Criteria

**The implementation is considered complete when ALL of the following criteria are met:**

### Backend Criteria

- [x] **AC-1**: `DraftDayEvent` scheduled for April 24 each season
  - Verify: Event exists in database with correct date
  - Verify: Event created during offseason initialization

- [x] **AC-2**: `DraftDayEvent.execute()` returns proper interaction signal
  - Verify: `requires_user_interaction = True`
  - Verify: `interaction_type = 'draft_day'`
  - Verify: Metadata includes season_year

- [x] **AC-3**: Event marked executed after completion
  - Verify: `is_executed = TRUE` in database
  - Verify: Event does not re-trigger in subsequent years

### UI Criteria

- [x] **AC-4**: Simulation pauses when reaching draft day
  - Verify: `advance_day()` returns `status='paused'`
  - Verify: UI shows pause state

- [x] **AC-5**: Draft dialog displays automatically
  - Verify: Dialog opens without user action
  - Verify: Dialog populates with correct data

- [x] **AC-6**: User can make picks interactively
  - Verify: Prospects table displays all available players
  - Verify: "Make Pick" button executes selection
  - Verify: Draft order advances after pick

- [x] **AC-7**: Dialog is non-modal
  - Verify: Main window remains interactive
  - Verify: Other tabs accessible during draft

- [x] **AC-8**: Simulation controls disabled during draft
  - Verify: "Advance Day" button disabled
  - Verify: "Advance Week" button disabled
  - Verify: Tooltip explains why

### State Management Criteria

- [x] **AC-9**: Draft progress saves if dialog closed early
  - Verify: `closeEvent()` triggers state save
  - Verify: `current_draft_pick` persisted to database
  - Verify: `draft_in_progress = TRUE` in database

- [x] **AC-10**: Draft resumes from saved position
  - Verify: Reopen dialog shows correct pick number
  - Verify: Previous picks marked completed
  - Verify: Available prospects exclude drafted players

- [x] **AC-11**: Draft completion cleans up state
  - Verify: `draft_in_progress = FALSE` after completion
  - Verify: `current_draft_pick = 0` after completion
  - Verify: Simulation controls re-enabled

- [x] **AC-12**: All picks persisted to database
  - Verify: 262 rookies added to player_rosters
  - Verify: Contract type = 'ROOKIE'
  - Verify: Years_experience = 0

### Integration Criteria

- [x] **AC-13**: Simulation resumes after draft complete
  - Verify: "Advance Day" works after draft
  - Verify: Advances to April 25 successfully

- [x] **AC-14**: Draft doesn't re-trigger after completion
  - Verify: Advancing to April 24 next year triggers NEW draft
  - Verify: Previous year draft remains executed

- [x] **AC-15**: Other offseason events unaffected
  - Verify: Franchise tag events execute
  - Verify: Free agency events execute
  - Verify: All calendar events function normally

### Quality Criteria

- [x] **AC-16**: No errors or exceptions during draft
  - Verify: No console errors
  - Verify: No database lock errors
  - Verify: Graceful error handling

- [x] **AC-17**: Regression tests pass
  - Verify: All 4 critical regression tests pass
  - Verify: Manual regression checklist complete

- [x] **AC-18**: Documentation complete
  - Verify: Testing guide exists
  - Verify: Implementation plan complete
  - Verify: API documentation updated

---

## Test Data Setup

**Prerequisites for testing:**

### Database Setup

```bash
# Create fresh test database
sqlite3 data/database/test_draft.db < schema/database_schema.sql

# Or use existing database with dynasty
sqlite3 data/database/nfl_simulation.db
```

### Dynasty Initialization

```python
# File: tests/fixtures/dynasty_setup.py

def setup_test_dynasty(database_path="data/database/test_draft.db"):
    """Create test dynasty with all required data."""
    from database.dynasty_database_api import DynastyDatabaseAPI
    from services.dynasty_initialization_service import DynastyInitializationService

    # Create dynasty
    dynasty_api = DynastyDatabaseAPI(database_path)
    dynasty_id = dynasty_api.create_dynasty(
        dynasty_name="Test Dynasty",
        user_team_id=22,  # Detroit Lions
        start_season=2025
    )

    # Initialize dynasty (rosters, contracts, schedule)
    service = DynastyInitializationService(database_path)
    service.initialize_dynasty(
        dynasty_id=dynasty_id,
        user_team_id=22,
        season_year=2025
    )

    return dynasty_id
```

### Season Completion

```python
def complete_season_to_super_bowl(database_path, dynasty_id):
    """Simulate through Super Bowl to trigger offseason."""
    from season.season_cycle_controller import SeasonCycleController

    controller = SeasonCycleController(
        dynasty_id=dynasty_id,
        database_path=database_path,
        season_year=2025
    )

    # Regular season
    controller.advance_to_phase('REGULAR_SEASON')
    controller.advance_through_regular_season()

    # Playoffs
    controller.advance_to_phase('PLAYOFFS')
    controller.advance_through_playoffs()

    # Offseason events should now be scheduled
    return controller
```

### Draft Order Generation

```python
def generate_draft_order(database_path, dynasty_id, season_year=2026):
    """Generate draft order for testing."""
    from database.draft_order_api import DraftOrderAPI
    from database.standings_api import StandingsAPI

    draft_api = DraftOrderAPI(database_path)
    standings_api = StandingsAPI(database_path)

    # Get final standings
    standings = standings_api.get_final_standings(
        dynasty_id=dynasty_id,
        season_year=2025
    )

    # Generate draft order
    draft_api.generate_draft_order(
        dynasty_id=dynasty_id,
        season_year=season_year,
        standings=standings
    )
```

### Draft Class Generation

```python
def generate_draft_class(database_path, dynasty_id, season_year=2026):
    """Generate draft class prospects."""
    from database.draft_class_api import DraftClassAPI
    from player_generation.draft_class_generator import DraftClassGenerator

    generator = DraftClassGenerator()
    prospects = generator.generate_draft_class(
        season_year=season_year,
        num_prospects=300  # Generate 300+ prospects
    )

    draft_class_api = DraftClassAPI(database_path)
    for prospect in prospects:
        draft_class_api.add_prospect(
            dynasty_id=dynasty_id,
            season_year=season_year,
            prospect_data=prospect
        )
```

### Complete Test Setup Script

```python
# File: tests/fixtures/complete_test_setup.py

def setup_complete_test_environment():
    """One-shot setup for complete draft testing environment."""
    database_path = "data/database/test_draft.db"

    # Step 1: Create dynasty
    dynasty_id = setup_test_dynasty(database_path)

    # Step 2: Complete season to Super Bowl
    complete_season_to_super_bowl(database_path, dynasty_id)

    # Step 3: Generate draft order
    generate_draft_order(database_path, dynasty_id, season_year=2026)

    # Step 4: Generate draft class
    generate_draft_class(database_path, dynasty_id, season_year=2026)

    return {
        'database_path': database_path,
        'dynasty_id': dynasty_id,
        'season_year': 2026,
        'user_team_id': 22
    }
```

### Usage in Tests

```python
# File: tests/integration/test_draft_full_flow.py

@pytest.fixture(scope="module")
def test_environment():
    """Fixture providing complete test environment."""
    return setup_complete_test_environment()

def test_full_draft_integration(test_environment):
    """Integration test using complete test environment."""
    # Test environment has:
    # - Dynasty created
    # - Season completed to Super Bowl
    # - Draft order generated
    # - Draft class generated
    # - Ready for draft day testing

    sim_controller = SimulationController(
        database_path=test_environment['database_path'],
        dynasty_id=test_environment['dynasty_id']
    )

    # Advance to draft day and test...
```

---

## Known Edge Cases

**Critical edge cases that require explicit testing:**

### Edge Case 1: User Closes Dialog After Pick 1

**Scenario**: User makes exactly 1 pick then closes dialog.

**Expected Behavior**:
- Draft state saves: `current_draft_pick = 2`, `draft_in_progress = TRUE`
- Picked player removed from available prospects
- Reopen dialog shows pick 2 active

**Test**:
```python
def test_close_after_one_pick(test_database, dynasty_context, qtbot):
    """Verify state saves correctly after only 1 pick."""
    controller = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22
    )

    dialog = DraftDayDialog(controller)
    qtbot.addWidget(dialog)

    # Make 1 pick
    prospects = controller.get_available_prospects()
    dialog.make_pick(prospects[0]['player_id'])

    # Close immediately
    dialog.close()

    # Verify state
    dynasty_state_api = DynastyStateAPI(test_database)
    state = dynasty_state_api.get_dynasty_state(dynasty_context['dynasty_id'])

    assert state['current_draft_pick'] == 2
    assert state['draft_in_progress'] == True
```

### Edge Case 2: User Closes Dialog Before Pick 1

**Scenario**: User opens dialog but closes immediately without making any picks.

**Expected Behavior**:
- Draft state saves: `current_draft_pick = 1`, `draft_in_progress = TRUE`
- No picks recorded
- Reopen dialog shows pick 1 active

**Test**:
```python
def test_close_before_any_picks(test_database, dynasty_context, qtbot):
    """Verify safe close before making picks."""
    controller = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22
    )

    dialog = DraftDayDialog(controller)
    qtbot.addWidget(dialog)

    # Close without picks
    dialog.close()

    # Verify state
    dynasty_state_api = DynastyStateAPI(test_database)
    state = dynasty_state_api.get_dynasty_state(dynasty_context['dynasty_id'])

    assert state['current_draft_pick'] == 1
    assert state['draft_in_progress'] == True
```

### Edge Case 3: Advance to April 24 After Completion

**Scenario**: Complete draft in 2026, then advance to April 24, 2027.

**Expected Behavior**:
- 2026 draft event remains `is_executed = TRUE`
- 2027 draft event triggers (NEW event)
- 2026 draft does NOT re-execute

**Test**:
```python
def test_draft_does_not_retrigger_next_year(test_database, dynasty_context):
    """Verify completed draft doesn't re-execute next year."""
    sim_controller = SimulationController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id']
    )

    # Complete 2026 draft
    sim_controller.set_date(Date(2026, 4, 24))
    sim_controller.advance_day()  # Triggers and completes draft

    # Advance to 2027 draft
    sim_controller.set_date(Date(2027, 4, 24))
    result = sim_controller.advance_day()

    # Should trigger NEW 2027 draft
    assert result['event_type'] == 'DRAFT_DAY'
    assert result['season_year'] == 2027

    # 2026 draft still executed
    event_db = EventDatabaseAPI(test_database)
    draft_2026 = event_db.get_events_by_date(
        dynasty_id=dynasty_context['dynasty_id'],
        event_date=Date(2026, 4, 24)
    )[0]

    assert draft_2026['is_executed'] == True
```

### Edge Case 4: Database Connection Lost During Draft

**Scenario**: Database becomes unavailable mid-draft (disk full, permissions issue).

**Expected Behavior**:
- Graceful error message to user
- Draft state NOT corrupted
- Last successful pick persisted
- Can resume after database restored

**Test**:
```python
def test_database_failure_during_draft(test_database, dynasty_context, monkeypatch):
    """Verify graceful handling of database failures."""
    controller = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_context['dynasty_id'],
        season_year=2026,
        user_team_id=22
    )

    # Make 5 picks successfully
    prospects = controller.get_available_prospects()
    for i in range(5):
        controller.make_pick(prospects[i]['player_id'])

    # Simulate database failure on pick 6
    def mock_database_error(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(
        controller.player_roster_api,
        'add_player_to_roster',
        mock_database_error
    )

    # Try to make pick 6
    with pytest.raises(sqlite3.OperationalError):
        controller.make_pick(prospects[5]['player_id'])

    # Verify state preserved at pick 5
    dynasty_state_api = DynastyStateAPI(test_database)
    state = dynasty_state_api.get_dynasty_state(dynasty_context['dynasty_id'])

    assert state['current_draft_pick'] == 6  # Still at pick 6

    # Verify only 5 picks persisted
    player_roster_api = PlayerRosterAPI(test_database)
    rookies = player_roster_api.get_rookies(dynasty_context['dynasty_id'])
    assert len(rookies) == 5
```

### Edge Case 5: App Crashes Mid-Draft

**Scenario**: Application crashes during draft (power loss, OS crash).

**Expected Behavior**:
- Last committed draft state preserved
- Relaunch app and resume from last committed pick
- No data corruption

**Manual Test**:
- [ ] Make 20 picks
- [ ] Force quit application (kill -9)
- [ ] Relaunch application
- [ ] **VERIFY**: Dynasty state shows pick 21
- [ ] **VERIFY**: Database has 20 rookies
- [ ] Resume draft from pick 21
- [ ] **VERIFY**: No errors, no duplicate picks

### Edge Case 6: Concurrent Dynasty Drafts

**Scenario**: Multiple dynasties in same database, both at draft day.

**Expected Behavior**:
- Each dynasty has separate draft state
- No cross-contamination of picks
- Can complete draft in Dynasty A without affecting Dynasty B

**Test**:
```python
def test_concurrent_dynasty_drafts(test_database):
    """Verify multiple dynasties can draft simultaneously."""
    # Create two dynasties
    dynasty_a = setup_test_dynasty(test_database)
    dynasty_b = setup_test_dynasty(test_database)

    # Create controllers for both
    controller_a = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_a,
        season_year=2026,
        user_team_id=22
    )

    controller_b = DraftDialogController(
        database_path=test_database,
        dynasty_id=dynasty_b,
        season_year=2026,
        user_team_id=15
    )

    # Make picks in dynasty A
    prospects_a = controller_a.get_available_prospects()
    controller_a.make_pick(prospects_a[0]['player_id'])
    controller_a.make_pick(prospects_a[1]['player_id'])

    # Make picks in dynasty B
    prospects_b = controller_b.get_available_prospects()
    controller_b.make_pick(prospects_b[0]['player_id'])

    # Verify states independent
    dynasty_state_api = DynastyStateAPI(test_database)

    state_a = dynasty_state_api.get_dynasty_state(dynasty_a)
    state_b = dynasty_state_api.get_dynasty_state(dynasty_b)

    assert state_a['current_draft_pick'] == 3
    assert state_b['current_draft_pick'] == 2
```

### Edge Case 7: Draft Order Not Generated

**Scenario**: Advance to draft day but draft order missing from database.

**Expected Behavior**:
- Error dialog displays explaining issue
- User cannot proceed with draft
- Provide option to generate draft order

**Manual Test**:
- [ ] Delete draft order from database
  ```sql
  DELETE FROM draft_order WHERE season_year=2026;
  ```
- [ ] Advance to April 24
- [ ] **VERIFY**: Error dialog appears
- [ ] **VERIFY**: Message explains missing draft order
- [ ] **VERIFY**: Provides "Generate Draft Order" button
- [ ] Click "Generate Draft Order"
- [ ] **VERIFY**: Draft order created
- [ ] **VERIFY**: Can proceed with draft

### Edge Case 8: Draft Class Not Generated

**Scenario**: Advance to draft day but no prospects in database.

**Expected Behavior**:
- Error dialog displays explaining issue
- User cannot proceed with draft
- Provide option to generate draft class

**Manual Test**:
- [ ] Delete draft class from database
  ```sql
  DELETE FROM draft_class WHERE season_year=2026;
  ```
- [ ] Advance to April 24
- [ ] **VERIFY**: Error dialog appears
- [ ] **VERIFY**: Message explains missing draft class
- [ ] **VERIFY**: Provides "Generate Draft Class" button
- [ ] Click "Generate Draft Class"
- [ ] **VERIFY**: Prospects created
- [ ] **VERIFY**: Can proceed with draft

---

## Summary

This comprehensive testing guide covers all aspects of the NFL Draft Event integration across 6 implementation phases. Use this guide to:

1. **Unit Test**: Verify individual components in isolation
2. **Integration Test**: Verify component interactions and data flow
3. **Manual Test**: Validate UI behavior and user workflows
4. **Regression Test**: Ensure existing functionality remains intact
5. **Edge Case Test**: Handle critical failure scenarios

**Testing Completion Checklist**:
- [ ] All Phase 1 tests pass (Backend event scheduling)
- [ ] All Phase 2 tests pass (UI component migration)
- [ ] All Phase 3 tests pass (Draft state management)
- [ ] All Phase 4 tests pass (Event-UI integration)
- [ ] All Phase 5 tests pass (Non-modal behavior)
- [ ] All Phase 6 tests pass (Completion & cleanup)
- [ ] All regression tests pass
- [ ] All edge case tests pass
- [ ] All 18 acceptance criteria met

**Reference**: See `implementation_plan.md` for detailed implementation steps for each phase.
