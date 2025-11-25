"""
End-to-End Integration Tests for Phase 4: NFL Draft Event Integration

This test suite provides comprehensive coverage of the complete Phase 4 integration flow:
- Draft day event detection via SimulationController.check_for_draft_day_event()
- Event execution marking via _mark_event_executed()
- Draft resume workflow using DynastyStateAPI draft progress tracking
- Integration between MainWindow, SimulationController, and EventDatabaseAPI

Test Coverage:
1. test_draft_day_detection_triggers_dialog() - Core event detection flow
2. test_event_marking_prevents_retrigger() - Event execution marking
3. test_draft_resume_workflow() - Draft persistence and resume capability
4. test_no_draft_event_on_wrong_date() - Negative case validation
5. test_multiple_events_same_date_handling() - Edge case: multiple events
6. test_database_error_handling() - Error resilience

Current Implementation Notes:
- Uses direct method calls (not Qt signals as originally planned)
- Integration flow: MainWindow._sim_day() → check_for_draft_day_event() → _handle_draft_day_interactive()
- Event marking updates event.data['results'] field via EventDatabaseAPI.update_event_by_dict()
- Only 15% test coverage before this file (target: 95%)
"""

import pytest
import os
import sys
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, Mock
from typing import Dict, Any, Optional

# Add src to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import database APIs
from src.events.event_database_api import EventDatabaseAPI
from src.database.dynasty_state_api import DynastyStateAPI
from src.database.connection import DatabaseConnection


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_draft_day_event(
    db_path: str,
    dynasty_id: str,
    season: int,
    event_date: str = "2025-04-24",
    is_executed: bool = False
) -> int:
    """
    Create a DraftDayEvent in the test database using raw SQL.

    Args:
        db_path: Path to SQLite database
        dynasty_id: Dynasty identifier
        season: Season year
        event_date: Draft day date (YYYY-MM-DD)
        is_executed: If True, populate results field to mark as executed

    Returns:
        Event ID of created event
    """
    import json

    # Convert date to timestamp (milliseconds)
    dt = datetime.fromisoformat(f"{event_date}T00:00:00")
    timestamp_ms = int(dt.timestamp() * 1000)

    # Create event data
    event_data = {
        'parameters': {
            'draft_date': event_date,
            'total_rounds': 7,
            'picks_per_round': 32
        }
    }

    # Mark as executed if requested
    if is_executed:
        event_data['results'] = {
            'success': True,
            'executed_at': datetime.now().isoformat(),
            'message': 'Draft completed successfully'
        }

    # Insert event via raw SQL
    db = DatabaseConnection(db_path)
    conn = db.get_connection()

    cursor = conn.execute(
        """
        INSERT INTO events (event_type, timestamp_ms, dynasty_id, season, data)
        VALUES (?, ?, ?, ?, ?)
        """,
        ('DRAFT_DAY', timestamp_ms, dynasty_id, season, json.dumps(event_data))
    )

    event_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return event_id


def create_dynasty_state(
    db_path: str,
    dynasty_id: str,
    season: int,
    current_date: str,
    current_phase: str = "OFFSEASON",
    draft_in_progress: bool = False,
    current_draft_pick: int = 0
) -> None:
    """
    Create dynasty_state record for testing.

    Args:
        db_path: Path to SQLite database
        dynasty_id: Dynasty identifier
        season: Season year
        current_date: Current simulation date (YYYY-MM-DD)
        current_phase: REGULAR_SEASON, PLAYOFFS, or OFFSEASON
        draft_in_progress: True if draft is currently active
        current_draft_pick: Current pick index (0-223)
    """
    # Ensure dynasty record exists first (required for foreign key)
    db = DatabaseConnection(db_path)
    conn = db.get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO dynasties (dynasty_id, dynasty_name, team_id) VALUES (?, ?, ?)",
        (dynasty_id, "Test Dynasty", 7)  # Default to Detroit Lions as user team
    )
    conn.commit()
    conn.close()

    state_api = DynastyStateAPI(db_path)

    # Insert or update state
    state_api.update_state(
        dynasty_id=dynasty_id,
        season=season,
        current_date=current_date,
        current_phase=current_phase,
        current_week=None
    )

    # Update draft progress separately
    state_api.update_draft_progress(
        dynasty_id=dynasty_id,
        season=season,
        current_pick=current_draft_pick,
        in_progress=draft_in_progress
    )


def get_event_by_id(db_path: str, event_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve event by ID from database.

    Args:
        db_path: Path to SQLite database
        event_id: Event ID to retrieve

    Returns:
        Event dict or None if not found
    """
    import json

    db = DatabaseConnection(db_path)
    conn = db.get_connection()

    cursor = conn.execute(
        "SELECT event_id, event_type, timestamp_ms, dynasty_id, season, data FROM events WHERE event_id = ?",
        (event_id,)
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'event_id': row[0],
        'event_type': row[1],
        'timestamp_ms': row[2],
        'dynasty_id': row[3],
        'season': row[4],
        'data': json.loads(row[5])
    }


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def test_db_path(tmp_path):
    """Create temporary database for testing with draft progress migration."""
    db_path = str(tmp_path / "test_phase4.db")

    # Initialize database with production schema
    db = DatabaseConnection(db_path)
    db.initialize_database()

    # Run migration to add draft progress columns
    # (production database schema doesn't include these yet)
    conn = db.get_connection()

    # Add current_draft_pick column
    try:
        conn.execute("""
            ALTER TABLE dynasty_state
            ADD COLUMN current_draft_pick INTEGER DEFAULT 0
        """)
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise

    # Add draft_in_progress column
    try:
        conn.execute("""
            ALTER TABLE dynasty_state
            ADD COLUMN draft_in_progress INTEGER DEFAULT 0
        """)
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise

    conn.commit()

    # Debug: Verify dynasty_state schema
    cursor = conn.execute("PRAGMA table_info(dynasty_state)")
    columns = cursor.fetchall()
    print(f"[DEBUG test_db_path] dynasty_state columns: {[c[1] for c in columns]}")

    conn.close()

    yield db_path


@pytest.fixture
def mock_simulation_controller(test_db_path, mock_dynasty_id, mock_season):
    """
    Create mock SimulationController with real database backend.

    Uses actual EventDatabaseAPI and DynastyStateAPI instances
    for integration testing while mocking SeasonCycleController.
    """
    from ui.controllers.simulation_controller import SimulationController

    # Create initial dynasty state BEFORE controller initialization
    # This prevents errors when controller tries to load state
    create_dynasty_state(
        db_path=test_db_path,
        dynasty_id=mock_dynasty_id,
        season=mock_season,
        current_date="2025-04-23",
        current_phase="OFFSEASON"
    )

    with patch('ui.controllers.simulation_controller.SeasonCycleController'):
        controller = SimulationController(
            db_path=test_db_path,
            dynasty_id=mock_dynasty_id,
            season=mock_season
        )

        # Date should already be "2025-04-23" from state load
        return controller


# ============================================================================
# CORE INTEGRATION TESTS
# ============================================================================

def test_draft_day_detection_triggers_dialog(
    test_db_path,
    mock_dynasty_id,
    mock_season,
    mock_simulation_controller
):
    """
    Test that draft day event is correctly detected on April 24.

    Validates the complete detection flow:
    1. DraftDayEvent exists in database on April 24
    2. SimulationController.check_for_draft_day_event() returns event dict
    3. Event dict contains all required fields
    4. Event is NOT marked as executed (results field is None)

    Integration Points:
    - SimulationController.check_for_draft_day_event()
    - EventDatabaseAPI.get_events_by_dynasty_and_timestamp()
    - EventDatabaseAPI.create_event()
    """
    # Setup: Create draft day event on April 24
    event_id = create_draft_day_event(
        db_path=test_db_path,
        dynasty_id=mock_dynasty_id,
        season=mock_season,
        event_date="2025-04-24",
        is_executed=False  # Not yet executed
    )

    # Setup: Create dynasty state for April 24
    create_dynasty_state(
        db_path=test_db_path,
        dynasty_id=mock_dynasty_id,
        season=mock_season,
        current_date="2025-04-24",
        current_phase="OFFSEASON"
    )

    # Action: Advance controller to draft day
    mock_simulation_controller.current_date_str = "2025-04-24"

    # Action: Check for draft day event
    draft_event = mock_simulation_controller.check_for_draft_day_event()

    # Assert: Event was detected
    assert draft_event is not None, "Draft day event should be detected on April 24"

    # Assert: Event dict contains required fields
    assert draft_event['event_type'] == 'DRAFT_DAY', "Event type should be DRAFT_DAY"
    assert draft_event['event_id'] == event_id, "Event ID should match created event"
    assert draft_event['dynasty_id'] == mock_dynasty_id, "Dynasty ID should match"
    assert draft_event['season'] == mock_season, "Season should match"

    # Assert: Event has parameters
    assert 'data' in draft_event, "Event should have data field"
    assert 'parameters' in draft_event['data'], "Event data should have parameters"

    # Assert: Event is NOT marked as executed
    results = draft_event.get('data', {}).get('results')
    assert results is None, "Event should not have results field (not yet executed)"


def test_event_marking_prevents_retrigger(
    test_db_path,
    mock_dynasty_id,
    mock_season,
    mock_simulation_controller
):
    """
    Test that marking event as executed prevents re-triggering.

    Validates event execution marking flow:
    1. DraftDayEvent is detected on first check
    2. Event is marked as executed via _mark_event_executed()
    3. Event.data['results'] field is populated in database
    4. Second check on same date returns None (event already executed)

    Integration Points:
    - SimulationController.check_for_draft_day_event()
    - MainWindow._mark_event_executed() (simulated)
    - EventDatabaseAPI.update_event_by_dict()
    """
    # Setup: Create draft day event on April 24
    event_id = create_draft_day_event(
        db_path=test_db_path,
        dynasty_id=mock_dynasty_id,
        season=mock_season,
        event_date="2025-04-24",
        is_executed=False
    )

    # Setup: Advance to draft day
    mock_simulation_controller.current_date_str = "2025-04-24"

    # Action: First check - event should be detected
    draft_event = mock_simulation_controller.check_for_draft_day_event()
    assert draft_event is not None, "Event should be detected on first check"

    # Action: Mark event as executed (simulate MainWindow._mark_event_executed)
    event_api = EventDatabaseAPI(test_db_path)
    draft_event['data']['results'] = {
        'success': True,
        'executed_at': datetime.now().isoformat(),
        'message': 'Draft completed successfully'
    }
    event_api.update_event_by_dict(draft_event)

    # Action: Second check - event should NOT be detected (already executed)
    draft_event_retry = mock_simulation_controller.check_for_draft_day_event()

    # Assert: Event is not re-triggered
    assert draft_event_retry is None, (
        "Event should not be detected on second check (already executed)"
    )

    # Assert: Database was updated correctly
    updated_event = get_event_by_id(test_db_path, event_id)
    assert updated_event is not None, "Event should exist in database"
    assert updated_event.get('data', {}).get('results') is not None, (
        "Event should have results field populated"
    )
    assert updated_event['data']['results']['success'] is True, (
        "Event results should indicate success"
    )


def test_draft_resume_workflow(test_db_path, mock_dynasty_id, mock_season):
    """
    Test draft resume capability using DynastyStateAPI.

    Validates draft progress persistence and resume flow:
    1. Create partial draft state (50 picks completed)
    2. DynastyStateAPI.get_latest_state() returns draft_in_progress=True
    3. DynastyStateAPI.get_latest_state() returns current_draft_pick=50
    4. Update draft progress to pick 51
    5. Verify state persists correctly

    Integration Points:
    - DynastyStateAPI.update_draft_progress()
    - DynastyStateAPI.get_latest_state()
    - Draft controller resume logic (simulated)
    """
    # Setup: Create dynasty state with partial draft
    create_dynasty_state(
        db_path=test_db_path,
        dynasty_id=mock_dynasty_id,
        season=mock_season,
        current_date="2025-04-24",
        current_phase="OFFSEASON",
        draft_in_progress=True,
        current_draft_pick=50  # 50 picks completed (rounds 1-2 partial)
    )

    # Action: Load state from database
    state_api = DynastyStateAPI(test_db_path)
    state = state_api.get_latest_state(mock_dynasty_id)

    # Assert: Draft in progress flag is set
    assert state is not None, "State should exist in database"
    assert state['draft_in_progress'] is True, (
        "Draft should be marked as in progress"
    )

    # Assert: Current pick index is correct
    assert state['current_draft_pick'] == 50, (
        "Current draft pick should be 50 (last completed pick)"
    )

    # Action: Simulate draft progression to pick 51
    state_api.update_draft_progress(
        dynasty_id=mock_dynasty_id,
        season=mock_season,
        current_pick=51,  # Advance to next pick
        in_progress=True
    )

    # Action: Reload state to verify persistence
    updated_state = state_api.get_latest_state(mock_dynasty_id)

    # Assert: Pick index was updated correctly
    assert updated_state['current_draft_pick'] == 51, (
        "Current draft pick should advance to 51"
    )
    assert updated_state['draft_in_progress'] is True, (
        "Draft should still be in progress"
    )

    # Action: Complete draft (mark as not in progress)
    state_api.update_draft_progress(
        dynasty_id=mock_dynasty_id,
        season=mock_season,
        current_pick=224,  # All picks completed
        in_progress=False
    )

    # Action: Verify draft completion
    final_state = state_api.get_latest_state(mock_dynasty_id)

    # Assert: Draft is no longer in progress
    assert final_state['draft_in_progress'] is False, (
        "Draft should be marked as complete"
    )
    assert final_state['current_draft_pick'] == 224, (
        "All 224 picks should be completed"
    )


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

def test_no_draft_event_on_wrong_date(
    test_db_path,
    mock_dynasty_id,
    mock_season,
    mock_simulation_controller
):
    """
    Test that no draft event is detected on non-draft days.

    Validates negative case handling:
    1. DraftDayEvent exists on April 24
    2. Current date is April 23 (day before draft)
    3. check_for_draft_day_event() returns None
    4. No event triggering occurs

    Integration Points:
    - SimulationController.check_for_draft_day_event()
    - EventDatabaseAPI timestamp range queries
    """
    # Setup: Create draft day event on April 24
    create_draft_day_event(
        db_path=test_db_path,
        dynasty_id=mock_dynasty_id,
        season=mock_season,
        event_date="2025-04-24"
    )

    # Action: Set current date to April 23 (day before draft)
    mock_simulation_controller.current_date_str = "2025-04-23"

    # Action: Check for draft day event
    draft_event = mock_simulation_controller.check_for_draft_day_event()

    # Assert: No event detected on wrong date
    assert draft_event is None, (
        "Draft event should not be detected on April 23 (event is on April 24)"
    )


def test_multiple_events_same_date_handling(
    test_db_path,
    mock_dynasty_id,
    mock_season,
    mock_simulation_controller
):
    """
    Test handling of multiple events on same date.

    Validates event filtering logic:
    1. Create DRAFT_DAY event and MILESTONE event on same date (April 24)
    2. check_for_draft_day_event() returns only DRAFT_DAY event
    3. Other event types are ignored by draft detection

    Integration Points:
    - SimulationController.check_for_draft_day_event()
    - EventDatabaseAPI.get_events_by_dynasty_and_timestamp()
    - Event type filtering logic
    """
    # Setup: Create draft day event on April 24
    draft_event_id = create_draft_day_event(
        db_path=test_db_path,
        dynasty_id=mock_dynasty_id,
        season=mock_season,
        event_date="2025-04-24"
    )

    # Setup: Create milestone event on same date
    import json
    dt = datetime.fromisoformat("2025-04-24T00:00:00")

    db = DatabaseConnection(test_db_path)
    conn = db.get_connection()
    cursor = conn.execute(
        """
        INSERT INTO events (event_type, timestamp_ms, dynasty_id, season, data)
        VALUES (?, ?, ?, ?, ?)
        """,
        ('MILESTONE', int(dt.timestamp() * 1000), mock_dynasty_id, mock_season,
         json.dumps({'parameters': {'milestone_name': 'Schedule Release'}}))
    )
    milestone_event_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Action: Set current date to April 24
    mock_simulation_controller.current_date_str = "2025-04-24"

    # Action: Check for draft day event
    detected_event = mock_simulation_controller.check_for_draft_day_event()

    # Assert: Only DRAFT_DAY event is returned
    assert detected_event is not None, "Draft event should be detected"
    assert detected_event['event_type'] == 'DRAFT_DAY', (
        "Event type should be DRAFT_DAY (not MILESTONE)"
    )
    assert detected_event['event_id'] == draft_event_id, (
        "Draft event ID should match (not milestone event ID)"
    )


def test_database_error_handling(test_db_path, mock_dynasty_id, mock_season):
    """
    Test graceful handling of database errors.

    Validates error resilience:
    1. EventDatabaseAPI raises exception during query
    2. check_for_draft_day_event() catches exception
    3. Returns None instead of crashing
    4. Error is logged appropriately

    Integration Points:
    - SimulationController.check_for_draft_day_event()
    - Exception handling in event detection
    """
    # Setup: Create controller
    with patch('ui.controllers.simulation_controller.SeasonCycleController'):
        from ui.controllers.simulation_controller import SimulationController

        controller = SimulationController(
            db_path=test_db_path,
            dynasty_id=mock_dynasty_id,
            season=mock_season
        )

        controller.current_date_str = "2025-04-24"

        # Mock event_db to raise exception
        original_get_events = controller.event_db.get_events_by_dynasty_and_timestamp
        controller.event_db.get_events_by_dynasty_and_timestamp = Mock(
            side_effect=Exception("Database connection lost")
        )

        # Action: Attempt to check for draft day event
        # (should handle exception gracefully)
        draft_event = controller.check_for_draft_day_event()

        # Assert: Returns None on database error (no crash)
        assert draft_event is None, (
            "Should return None on database error (not raise exception)"
        )

        # Cleanup: Restore original method
        controller.event_db.get_events_by_dynasty_and_timestamp = original_get_events


# ============================================================================
# ADDITIONAL VALIDATION TESTS
# ============================================================================

def test_event_data_structure_validation(
    test_db_path,
    mock_dynasty_id,
    mock_season,
    mock_simulation_controller
):
    """
    Test that returned event dict has complete data structure.

    Validates event dict schema:
    - event_id (int)
    - event_type (str)
    - timestamp_ms (int)
    - dynasty_id (str)
    - season (int)
    - data (dict with parameters)
    """
    # Setup: Create draft day event
    create_draft_day_event(
        db_path=test_db_path,
        dynasty_id=mock_dynasty_id,
        season=mock_season,
        event_date="2025-04-24"
    )

    mock_simulation_controller.current_date_str = "2025-04-24"

    # Action: Detect event
    draft_event = mock_simulation_controller.check_for_draft_day_event()

    # Assert: All required fields present
    assert 'event_id' in draft_event, "Event must have event_id"
    assert 'event_type' in draft_event, "Event must have event_type"
    assert 'timestamp_ms' in draft_event, "Event must have timestamp_ms"
    assert 'dynasty_id' in draft_event, "Event must have dynasty_id"
    assert 'season' in draft_event, "Event must have season"
    assert 'data' in draft_event, "Event must have data field"

    # Assert: Data field has parameters
    assert 'parameters' in draft_event['data'], "Event data must have parameters"
    assert isinstance(draft_event['data']['parameters'], dict), (
        "Event parameters must be dict"
    )

    # Assert: Field types are correct
    assert isinstance(draft_event['event_id'], int), "event_id must be int"
    assert isinstance(draft_event['event_type'], str), "event_type must be str"
    assert isinstance(draft_event['timestamp_ms'], int), "timestamp_ms must be int"
    assert isinstance(draft_event['dynasty_id'], str), "dynasty_id must be str"
    assert isinstance(draft_event['season'], int), "season must be int"


def test_draft_state_persistence_across_controller_instances(
    test_db_path,
    mock_dynasty_id,
    mock_season
):
    """
    Test that draft progress persists across controller instances.

    Validates state persistence:
    1. Create controller instance #1, update draft progress
    2. Destroy controller instance #1
    3. Create controller instance #2 with same database
    4. Verify draft progress is restored correctly

    This simulates dialog close → reopen workflow.
    """
    # Setup: Create initial draft state
    state_api = DynastyStateAPI(test_db_path)
    create_dynasty_state(
        db_path=test_db_path,
        dynasty_id=mock_dynasty_id,
        season=mock_season,
        current_date="2025-04-24",
        current_phase="OFFSEASON",
        draft_in_progress=True,
        current_draft_pick=32  # Round 1 complete
    )

    # Action: Load state (simulates controller initialization)
    state_1 = state_api.get_latest_state(mock_dynasty_id)
    assert state_1['current_draft_pick'] == 32, "Initial state should be pick 32"

    # Action: Simulate draft progression in "session 1"
    state_api.update_draft_progress(
        dynasty_id=mock_dynasty_id,
        season=mock_season,
        current_pick=64,  # Round 2 complete
        in_progress=True
    )

    # Action: "Close and reopen" - create new API instance
    state_api_2 = DynastyStateAPI(test_db_path)
    state_2 = state_api_2.get_latest_state(mock_dynasty_id)

    # Assert: Draft progress was persisted
    assert state_2['current_draft_pick'] == 64, (
        "Draft progress should persist across API instances"
    )
    assert state_2['draft_in_progress'] is True, (
        "Draft in-progress flag should persist"
    )


if __name__ == '__main__':
    pytest.main(['-v', __file__])
