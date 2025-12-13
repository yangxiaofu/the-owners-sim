"""
Tests for ScheduleView and related schedule UI components.

Part of Milestone 11: Schedule & Rivalries, Tollgate 7.
Tests schedule display, rivalry highlighting, primetime badges, and interactions.
"""

import pytest
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional
from unittest.mock import Mock, patch, MagicMock

# Skip import if PySide6 not available (CI/headless environments)
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor


# ============================================================================
# Test fixtures and mocks
# ============================================================================

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@dataclass
class MockScheduledGame:
    """Mock ScheduledGame for testing."""
    id: int
    week: int
    home_team_id: int
    away_team_id: int
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    is_played: bool = False


class MockRivalryType(Enum):
    """Mock RivalryType enum."""
    division = "division"
    historic = "historic"
    geographic = "geographic"
    recent = "recent"


@dataclass
class MockRivalry:
    """Mock Rivalry for testing."""
    team_a_id: int
    team_b_id: int
    rivalry_type: MockRivalryType
    rivalry_name: str
    intensity: int
    is_protected: bool = False


@dataclass
class MockHeadToHeadRecord:
    """Mock HeadToHeadRecord for testing."""
    team_a_wins: int
    team_b_wins: int
    ties: int = 0
    current_streak_team: Optional[int] = None
    current_streak_count: int = 0
    playoff_meetings: int = 0
    playoff_team_a_wins: int = 0
    playoff_team_b_wins: int = 0
    last_meeting_season: Optional[int] = None
    last_meeting_winner: Optional[int] = None


@dataclass
class MockTeamStanding:
    """Mock TeamStanding for testing."""
    team_id: int
    wins: int
    losses: int
    ties: int = 0


# ============================================================================
# Theme function tests
# ============================================================================

class TestThemeFunctions:
    """Test theme utility functions."""

    def test_get_rivalry_intensity_color_legendary(self):
        """Legendary intensity (90+) returns red."""
        from game_cycle_ui.theme import get_rivalry_intensity_color
        color = get_rivalry_intensity_color(95)
        assert color == "#FFCDD2"

    def test_get_rivalry_intensity_color_intense(self):
        """Intense intensity (75-89) returns orange."""
        from game_cycle_ui.theme import get_rivalry_intensity_color
        color = get_rivalry_intensity_color(80)
        assert color == "#FFE0B2"

    def test_get_rivalry_intensity_color_competitive(self):
        """Competitive intensity (50-74) returns yellow."""
        from game_cycle_ui.theme import get_rivalry_intensity_color
        color = get_rivalry_intensity_color(60)
        assert color == "#FFF9C4"

    def test_get_rivalry_intensity_color_developing(self):
        """Developing intensity (25-49) returns green."""
        from game_cycle_ui.theme import get_rivalry_intensity_color
        color = get_rivalry_intensity_color(30)
        assert color == "#C8E6C9"

    def test_get_rivalry_intensity_color_mild(self):
        """Mild intensity (<25) returns white."""
        from game_cycle_ui.theme import get_rivalry_intensity_color
        color = get_rivalry_intensity_color(15)
        assert color == "#FFFFFF"

    def test_get_intensity_label_legendary(self):
        """Legendary label for 90+ intensity."""
        from game_cycle_ui.theme import get_intensity_label
        label = get_intensity_label(92)
        assert label == "Legendary"

    def test_get_intensity_label_intense(self):
        """Intense label for 75-89 intensity."""
        from game_cycle_ui.theme import get_intensity_label
        label = get_intensity_label(78)
        assert label == "Intense"

    def test_get_intensity_label_competitive(self):
        """Competitive label for 50-74 intensity."""
        from game_cycle_ui.theme import get_intensity_label
        label = get_intensity_label(55)
        assert label == "Competitive"

    def test_get_intensity_label_developing(self):
        """Developing label for 25-49 intensity."""
        from game_cycle_ui.theme import get_intensity_label
        label = get_intensity_label(35)
        assert label == "Developing"

    def test_get_intensity_label_mild(self):
        """Mild label for <25 intensity."""
        from game_cycle_ui.theme import get_intensity_label
        label = get_intensity_label(10)
        assert label == "Mild"


# ============================================================================
# ScheduleView tests
# ============================================================================

class TestScheduleViewBasics:
    """Test ScheduleView initialization and basic functionality."""

    def test_schedule_view_initializes(self, qapp):
        """ScheduleView initializes without errors."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        assert view is not None
        assert view._current_week == 1
        assert view._selected_team_id is None

    def test_schedule_view_has_games_table(self, qapp):
        """ScheduleView has a games table."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        assert view.games_table is not None
        assert view.games_table.columnCount() == 8

    def test_schedule_view_has_team_filter(self, qapp):
        """ScheduleView has team filter dropdown."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        assert view.team_filter is not None

    def test_schedule_view_has_week_navigation(self, qapp):
        """ScheduleView has prev/next week buttons."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        assert view.prev_btn is not None
        assert view.next_btn is not None
        assert view.week_label is not None

    def test_schedule_view_has_bye_indicator(self, qapp):
        """ScheduleView has bye week label."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        assert view.bye_label is not None


class TestScheduleViewNavigation:
    """Test week navigation."""

    def test_prev_week_decrements(self, qapp):
        """Previous button decrements current week."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        view._current_week = 5
        view._prev_week()
        assert view._current_week == 4

    def test_prev_week_stops_at_1(self, qapp):
        """Previous button stops at week 1."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        view._current_week = 1
        view._prev_week()
        assert view._current_week == 1

    def test_next_week_increments(self, qapp):
        """Next button increments current week."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        view._current_week = 5
        view._next_week()
        assert view._current_week == 6

    def test_next_week_stops_at_18(self, qapp):
        """Next button stops at week 18."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        view._current_week = 18
        view._next_week()
        assert view._current_week == 18

    def test_set_current_week_valid(self, qapp):
        """set_current_week works for valid weeks."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        view.set_current_week(10)
        assert view._current_week == 10

    def test_set_current_week_invalid(self, qapp):
        """set_current_week ignores invalid weeks."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        view._current_week = 5
        view.set_current_week(25)  # Invalid
        assert view._current_week == 5  # Unchanged


class TestScheduleViewTeamFilter:
    """Test team filter functionality."""

    def test_set_selected_team(self, qapp):
        """Setting selected team updates filter."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        # Add a mock team to filter
        view.team_filter.addItem("All Teams", None)
        view.team_filter.addItem("Test Team", 5)

        view.set_selected_team(5)
        assert view._selected_team_id == 5

    def test_get_selected_team_id(self, qapp):
        """get_selected_team_id returns current selection."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        view._selected_team_id = 10
        assert view.get_selected_team_id() == 10


class TestScheduleViewRivalryHighlighting:
    """Test rivalry highlighting functionality."""

    def test_get_rivalry_from_cache(self, qapp):
        """_get_rivalry returns rivalry from cache."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()

        # Add mock rivalry to cache
        mock_rivalry = MockRivalry(
            team_a_id=5,
            team_b_id=10,
            rivalry_type=MockRivalryType.division,
            rivalry_name="Test Rivalry",
            intensity=75
        )
        view._rivalry_cache[(5, 10)] = mock_rivalry

        # Should find it regardless of order
        result = view._get_rivalry(5, 10)
        assert result == mock_rivalry

        result = view._get_rivalry(10, 5)
        assert result == mock_rivalry

    def test_get_rivalry_returns_none_if_not_found(self, qapp):
        """_get_rivalry returns None if not in cache."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()

        result = view._get_rivalry(5, 10)
        assert result is None


class TestScheduleViewRecordDisplay:
    """Test team record display."""

    def test_get_record_string_wins_losses(self, qapp):
        """Record string formats W-L correctly."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        view._standings_cache[5] = (10, 3, 0)

        result = view._get_record_string(5)
        assert result == "10-3"

    def test_get_record_string_with_ties(self, qapp):
        """Record string includes ties."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()
        view._standings_cache[5] = (10, 3, 2)

        result = view._get_record_string(5)
        assert result == "10-3-2"

    def test_get_record_string_no_data(self, qapp):
        """Record string defaults to 0-0."""
        from game_cycle_ui.views.schedule_view import ScheduleView
        view = ScheduleView()

        result = view._get_record_string(99)  # Not in cache
        assert result == "0-0"


# ============================================================================
# RivalryInfoDialog tests
# ============================================================================

class TestRivalryInfoDialog:
    """Test RivalryInfoDialog."""

    def test_dialog_initializes(self, qapp):
        """RivalryInfoDialog initializes without data."""
        from game_cycle_ui.dialogs.rivalry_info_dialog import RivalryInfoDialog
        dialog = RivalryInfoDialog()
        assert dialog is not None

    def test_dialog_with_rivalry_data(self, qapp):
        """RivalryInfoDialog populates with rivalry data."""
        from game_cycle_ui.dialogs.rivalry_info_dialog import RivalryInfoDialog

        rivalry = MockRivalry(
            team_a_id=1,
            team_b_id=2,
            rivalry_type=MockRivalryType.historic,
            rivalry_name="Bears vs Packers",
            intensity=95,
            is_protected=True
        )

        h2h = MockHeadToHeadRecord(
            team_a_wins=105,
            team_b_wins=95,
            ties=6,
            current_streak_team=2,
            current_streak_count=3,
            playoff_meetings=4,
            playoff_team_a_wins=2,
            playoff_team_b_wins=2
        )

        team_names = {1: "Bears", 2: "Packers"}

        dialog = RivalryInfoDialog(rivalry, h2h, team_names)
        assert dialog.name_label.text() == "Bears vs Packers"
        assert dialog.team_a_record.text() == "105"
        assert dialog.team_b_record.text() == "95"

    def test_dialog_shows_intensity(self, qapp):
        """RivalryInfoDialog shows intensity meter."""
        from game_cycle_ui.dialogs.rivalry_info_dialog import RivalryInfoDialog

        rivalry = MockRivalry(
            team_a_id=1,
            team_b_id=2,
            rivalry_type=MockRivalryType.division,
            rivalry_name="Test Rivalry",
            intensity=80
        )

        h2h = MockHeadToHeadRecord(team_a_wins=10, team_b_wins=12)
        team_names = {1: "Team A", 2: "Team B"}

        dialog = RivalryInfoDialog(rivalry, h2h, team_names)
        assert dialog.intensity_bar.value() == 80
        assert dialog.intensity_value_label.text() == "80"


# ============================================================================
# TeamScheduleWidget tests
# ============================================================================

class TestTeamScheduleWidget:
    """Test TeamScheduleWidget."""

    def test_widget_initializes(self, qapp):
        """TeamScheduleWidget initializes without errors."""
        from game_cycle_ui.widgets.team_schedule_widget import TeamScheduleWidget
        widget = TeamScheduleWidget()
        assert widget is not None
        assert widget.schedule_table is not None
        assert widget.schedule_table.columnCount() == 5

    def test_widget_shows_bye_week(self, qapp):
        """TeamScheduleWidget shows bye week correctly."""
        from game_cycle_ui.widgets.team_schedule_widget import TeamScheduleWidget
        widget = TeamScheduleWidget()

        # Set up minimal schedule with bye
        schedule = [
            {'week': 1, 'home_team_id': 1, 'away_team_id': 2, 'is_played': False},
            {'week': 2, 'home_team_id': 3, 'away_team_id': 1, 'is_played': False},
        ]
        team_names = {1: "Team A", 2: "Team B", 3: "Team C"}

        widget.set_team_schedule(
            team_id=1,
            team_name="Team A",
            schedule=schedule,
            bye_week=5,
            team_names=team_names
        )

        # Check bye week row
        bye_item = widget.schedule_table.item(4, 1)  # Row 4 = Week 5
        assert bye_item is not None
        assert "BYE" in bye_item.text().upper()

    def test_widget_shows_opponent(self, qapp):
        """TeamScheduleWidget shows opponent names."""
        from game_cycle_ui.widgets.team_schedule_widget import TeamScheduleWidget
        widget = TeamScheduleWidget()

        schedule = [
            {'week': 1, 'home_team_id': 1, 'away_team_id': 2, 'is_played': False},
        ]
        team_names = {1: "Team A", 2: "Team B"}

        widget.set_team_schedule(
            team_id=1,
            team_name="Team A",
            schedule=schedule,
            bye_week=None,
            team_names=team_names
        )

        # Team A is home, so opponent is Team B (away)
        opp_item = widget.schedule_table.item(0, 1)
        assert opp_item is not None
        assert opp_item.text() == "Team B"

    def test_widget_clears_properly(self, qapp):
        """TeamScheduleWidget clear() resets state."""
        from game_cycle_ui.widgets.team_schedule_widget import TeamScheduleWidget
        widget = TeamScheduleWidget()

        # Set some data first
        widget._team_id = 5
        widget._bye_week = 8

        widget.clear()

        assert widget._team_id is None
        assert widget._bye_week is None
        assert widget.schedule_table.rowCount() == 0


# ============================================================================
# Integration tests (with mocked database)
# ============================================================================

class TestScheduleViewIntegration:
    """Integration tests with mocked database APIs."""

    @patch('team_management.teams.team_loader.get_team_by_id')
    @patch('src.game_cycle.database.standings_api.StandingsAPI')
    @patch('src.game_cycle.database.bye_week_api.ByeWeekAPI')
    @patch('src.game_cycle.database.rivalry_api.RivalryAPI')
    @patch('src.game_cycle.database.connection.GameCycleDatabase')
    def test_set_context_loads_data(
        self, mock_db, mock_rivalry_api,
        mock_bye_api, mock_standings_api, mock_get_team, qapp
    ):
        """set_context loads schedule from games table, rivalries, bye weeks, standings."""
        from game_cycle_ui.views.schedule_view import ScheduleView

        # Set up mocks
        mock_db_instance = MagicMock()
        mock_db_instance.query_all.return_value = []  # Games query returns empty
        mock_db.return_value = mock_db_instance

        mock_rivalry = MagicMock()
        mock_rivalry.get_all_rivalries.return_value = []
        mock_rivalry_api.return_value = mock_rivalry

        mock_bye = MagicMock()
        mock_bye.get_all_bye_weeks.return_value = {}
        mock_bye_api.return_value = mock_bye

        mock_standings = MagicMock()
        mock_standings.get_standings.return_value = []
        mock_standings_api.return_value = mock_standings

        # Mock team loader
        mock_team = MagicMock()
        mock_team.name = "Test Team"
        mock_team.full_name = "Test Team"
        mock_get_team.return_value = mock_team

        view = ScheduleView()
        view.set_context("test_dynasty", "/path/to/db", 2025)

        # Verify games table was queried 18 times (once per week)
        assert mock_db_instance.query_all.call_count == 18  # Weeks 1-18
        mock_rivalry.get_all_rivalries.assert_called_once_with("test_dynasty")
        mock_bye.get_all_bye_weeks.assert_called_once_with("test_dynasty", 2025)
        mock_standings.get_standings.assert_called_once_with("test_dynasty", 2025)
