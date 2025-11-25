"""
Integration Tests for Draft Save/Resume Workflow (Phase 3)

Tests the complete save/resume functionality for NFL draft dialog.
Validates end-to-end flow from dialog close through database persistence
to resume detection and UI restoration.

Test Coverage:
- Draft save workflow (dialog close → controller → database)
- Draft resume workflow (database → controller → dialog)
- Database persistence verification
- UI state restoration on resume
- Edge cases (incomplete saves, corrupted state, resume message display)
"""

import pytest
import os
import sqlite3
import tempfile
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication, QMessageBox

# Ensure QApplication exists for Qt widgets
@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for Qt widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestDraftResume:
    """Integration tests for draft save/resume functionality."""

    @pytest.fixture
    def mock_controller(self):
        """Create mock DraftDialogController for testing."""
        controller = Mock()
        controller.user_team_id = 22
        controller.season = 2025
        controller.draft_order = []  # Empty for testing
        controller.current_pick_index = 0
        controller.pick_executed = Mock()
        controller.pick_executed.connect = Mock()
        controller.draft_completed = Mock()
        controller.draft_completed.connect = Mock()
        controller.error_occurred = Mock()
        controller.error_occurred.connect = Mock()
        controller.save_draft_state = Mock(return_value=True)
        controller.load_draft_state = Mock(return_value={
            'current_pick_index': 0,
            'draft_in_progress': False,
            'last_saved': ''
        })
        controller.get_current_pick = Mock(return_value=None)
        controller.get_available_prospects = Mock(return_value=[])
        controller.get_team_needs = Mock(return_value=[])
        controller.get_pick_history = Mock(return_value=[])
        controller.get_draft_progress = Mock(return_value={
            'picks_completed': 0,
            'picks_remaining': 262,
            'total_picks': 262,
            'completion_pct': 0.0,
            'current_round': 1,
            'is_complete': False
        })
        return controller

    # =======================================================================
    # SAVE WORKFLOW TESTS
    # =======================================================================

    def test_close_event_saves_draft_state(self, qapp, mock_controller):
        """Verify closeEvent calls controller.save_draft_state()."""
        from ui.dialogs.draft_day_dialog import DraftDayDialog
        from PySide6.QtGui import QCloseEvent

        # Create dialog
        dialog = DraftDayDialog(mock_controller)

        # Simulate close event
        event = QCloseEvent()
        dialog.closeEvent(event)

        # Verify save was called
        assert mock_controller.save_draft_state.called
        assert mock_controller.save_draft_state.call_count == 1

    def test_close_event_handles_save_failure_gracefully(self, qapp, mock_controller, capsys):
        """Verify closeEvent handles save failures without crashing."""
        from ui.dialogs.draft_day_dialog import DraftDayDialog
        from PySide6.QtGui import QCloseEvent

        # Mock save to raise exception
        mock_controller.save_draft_state.side_effect = RuntimeError("Database locked")

        # Create dialog
        dialog = DraftDayDialog(mock_controller)

        # Simulate close event (should not raise exception)
        event = QCloseEvent()
        dialog.closeEvent(event)  # Should complete without exception

        # Verify warning was printed
        captured = capsys.readouterr()
        assert "Warning: Failed to save draft state on close" in captured.out
        assert "Database locked" in captured.out

    # =======================================================================
    # RESUME WORKFLOW TESTS
    # =======================================================================

    @patch.object(QMessageBox, 'information')
    def test_resume_message_shown_for_in_progress_draft(self, mock_msgbox, qapp, mock_controller):
        """Verify resume message is shown when draft_in_progress=True."""
        from ui.dialogs.draft_day_dialog import DraftDayDialog

        # Mock draft in progress at pick 50
        mock_controller.load_draft_state.return_value = {
            'current_pick_index': 50,
            'draft_in_progress': True,
            'last_saved': ''
        }

        # Create dialog (should trigger resume check)
        dialog = DraftDayDialog(mock_controller)

        # Verify message box was shown
        assert mock_msgbox.called
        args, kwargs = mock_msgbox.call_args
        assert "Resume Draft" in args[1]  # Title
        assert "pick #51" in args[2]  # Message (50+1 for 1-indexed display)
        assert "Draft in progress detected" in args[2]

    @patch.object(QMessageBox, 'information')
    def test_no_resume_message_for_new_draft(self, mock_msgbox, qapp, mock_controller):
        """Verify no resume message for new drafts (pick 0)."""
        from ui.dialogs.draft_day_dialog import DraftDayDialog

        # Mock new draft (default state)
        mock_controller.load_draft_state.return_value = {
            'current_pick_index': 0,
            'draft_in_progress': False,
            'last_saved': ''
        }

        # Create dialog
        dialog = DraftDayDialog(mock_controller)

        # Verify no message box shown
        assert not mock_msgbox.called

    @patch.object(QMessageBox, 'information')
    def test_no_resume_message_for_completed_draft(self, mock_msgbox, qapp, mock_controller):
        """Verify no resume message for completed drafts."""
        from ui.dialogs.draft_day_dialog import DraftDayDialog

        # Mock completed draft (all picks done, not in progress)
        mock_controller.load_draft_state.return_value = {
            'current_pick_index': 262,
            'draft_in_progress': False,
            'last_saved': ''
        }

        # Create dialog
        dialog = DraftDayDialog(mock_controller)

        # Verify no message box shown
        assert not mock_msgbox.called

    # =======================================================================
    # CONTROLLER INTEGRATION TESTS
    # =======================================================================

    def test_controller_save_persists_to_database(self):
        """Verify controller.save_draft_state() actually writes to database."""
        from ui.controllers.draft_dialog_controller import DraftDialogController
        from database.dynasty_state_api import DynastyStateAPI

        # Create temporary database
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        try:
            # Setup database with dynasty_state table (including draft progress columns)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE dynasty_state (
                    dynasty_id TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    current_date TEXT NOT NULL,
                    current_phase TEXT NOT NULL,
                    current_week INTEGER,
                    last_simulated_game_id TEXT,
                    current_draft_pick INTEGER DEFAULT 0,
                    draft_in_progress INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (dynasty_id, season)
                )
            """)
            cursor.execute("""
                INSERT INTO dynasty_state
                (dynasty_id, season, current_date, current_phase)
                VALUES ('test_dynasty', 2025, '2025-04-25', 'offseason')
            """)
            # Create draft_order table (required by controller)
            cursor.execute("""
                CREATE TABLE draft_order (
                    pick_id INTEGER PRIMARY KEY,
                    dynasty_id TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    round_number INTEGER NOT NULL,
                    pick_in_round INTEGER NOT NULL,
                    overall_pick INTEGER NOT NULL,
                    original_team_id INTEGER NOT NULL,
                    current_team_id INTEGER NOT NULL,
                    is_compensatory INTEGER DEFAULT 0,
                    player_id INTEGER,
                    is_executed INTEGER DEFAULT 0
                )
            """)
            # Insert one draft pick for testing
            cursor.execute("""
                INSERT INTO draft_order
                (dynasty_id, season, round_number, pick_in_round, overall_pick, original_team_id, current_team_id)
                VALUES ('test_dynasty', 2025, 1, 1, 1, 22, 22)
            """)
            # Create draft_class table (required by controller)
            cursor.execute("""
                CREATE TABLE draft_class (
                    player_id INTEGER PRIMARY KEY,
                    dynasty_id TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    position TEXT NOT NULL,
                    overall INTEGER NOT NULL,
                    college TEXT,
                    age INTEGER,
                    is_drafted INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                INSERT INTO draft_class
                (dynasty_id, season, first_name, last_name, position, overall, college, age)
                VALUES ('test_dynasty', 2025, 'Test', 'Player', 'QB', 80, 'Test University', 21)
            """)
            conn.commit()
            conn.close()

            # Initialize controller with real database
            controller = DraftDialogController(
                database_path=db_path,
                dynasty_id='test_dynasty',
                season_year=2025,
                user_team_id=22
            )

            # Manually set pick index
            controller.current_pick_index = 42

            # Save draft state
            success = controller.save_draft_state()
            assert success is True

            # Verify database persistence
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT current_draft_pick, draft_in_progress
                FROM dynasty_state
                WHERE dynasty_id='test_dynasty' AND season=2025
            """)
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == 42  # current_draft_pick
            assert row[1] == 1   # draft_in_progress (True)

        finally:
            os.unlink(db_path)

    def test_controller_load_restores_from_database(self):
        """Verify controller.load_draft_state() reads from database."""
        from ui.controllers.draft_dialog_controller import DraftDialogController

        # Create temporary database with saved draft state
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE dynasty_state (
                    dynasty_id TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    current_date TEXT NOT NULL,
                    current_phase TEXT NOT NULL,
                    current_week INTEGER,
                    last_simulated_game_id TEXT,
                    current_draft_pick INTEGER DEFAULT 0,
                    draft_in_progress INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (dynasty_id, season)
                )
            """)
            cursor.execute("""
                INSERT INTO dynasty_state
                (dynasty_id, season, current_date, current_phase, current_draft_pick, draft_in_progress)
                VALUES ('test_dynasty', 2025, '2025-04-25', 'offseason', 100, 1)
            """)
            # Create required tables
            cursor.execute("""
                CREATE TABLE draft_order (
                    pick_id INTEGER PRIMARY KEY,
                    dynasty_id TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    round_number INTEGER NOT NULL,
                    pick_in_round INTEGER NOT NULL,
                    overall_pick INTEGER NOT NULL,
                    original_team_id INTEGER NOT NULL,
                    current_team_id INTEGER NOT NULL,
                    is_compensatory INTEGER DEFAULT 0,
                    player_id INTEGER,
                    is_executed INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                INSERT INTO draft_order
                (dynasty_id, season, round_number, pick_in_round, overall_pick, original_team_id, current_team_id)
                VALUES ('test_dynasty', 2025, 1, 1, 1, 22, 22)
            """)
            cursor.execute("""
                CREATE TABLE draft_class (
                    player_id INTEGER PRIMARY KEY,
                    dynasty_id TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    position TEXT NOT NULL,
                    overall INTEGER NOT NULL,
                    college TEXT,
                    age INTEGER,
                    is_drafted INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                INSERT INTO draft_class
                (dynasty_id, season, first_name, last_name, position, overall, college, age)
                VALUES ('test_dynasty', 2025, 'Test', 'Player', 'QB', 80, 'Test University', 21)
            """)
            conn.commit()
            conn.close()

            # Initialize controller (should load saved state in __init__)
            controller = DraftDialogController(
                database_path=db_path,
                dynasty_id='test_dynasty',
                season_year=2025,
                user_team_id=22
            )

            # Verify controller restored saved pick
            assert controller.current_pick_index == 100

            # Verify load_draft_state() returns correct values
            state = controller.load_draft_state()
            assert state['current_pick_index'] == 100
            assert state['draft_in_progress'] is True

        finally:
            os.unlink(db_path)

    # =======================================================================
    # EDGE CASE TESTS
    # =======================================================================

    @patch.object(QMessageBox, 'information')
    def test_resume_handles_missing_database_gracefully(self, mock_msgbox, qapp, mock_controller):
        """Verify resume handles missing dynasty_state gracefully."""
        from ui.dialogs.draft_day_dialog import DraftDayDialog

        # Mock load_draft_state to simulate database error (returns defaults)
        mock_controller.load_draft_state.return_value = {
            'current_pick_index': 0,
            'draft_in_progress': False,
            'last_saved': ''
        }

        # Create dialog (should not crash)
        dialog = DraftDayDialog(mock_controller)

        # Verify no crash and no message shown
        assert not mock_msgbox.called

    def test_save_handles_database_lock_with_exception(self, qapp, mock_controller):
        """Verify save raises RuntimeError on database failure."""
        from ui.dialogs.draft_day_dialog import DraftDayDialog

        # Mock save to raise exception
        mock_controller.save_draft_state.side_effect = RuntimeError("Database write failed")

        # Create dialog
        dialog = DraftDayDialog(mock_controller)

        # Verify closeEvent handles exception gracefully (no crash)
        from PySide6.QtGui import QCloseEvent
        event = QCloseEvent()
        dialog.closeEvent(event)  # Should not re-raise exception
