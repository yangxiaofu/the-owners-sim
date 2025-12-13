"""
Unit tests for AwardsView.

Tests the Awards UI component including:
- View initialization and structure
- Context setting and data loading
- Major Awards tab functionality
- All-Pro Teams tab functionality
- Pro Bowl tab functionality
- Statistical Leaders tab functionality

Part of Milestone 10: Awards System, Tollgate 6.
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Dict, List, Optional

# Check if Qt is available
try:
    from PySide6.QtWidgets import QApplication, QTabWidget, QComboBox, QTableWidget
    from PySide6.QtCore import Qt
    HAS_QT = True
except ImportError:
    HAS_QT = False

# Skip all tests if Qt is not available
pytestmark = pytest.mark.skipif(not HAS_QT, reason="Qt not available")


# ============================================
# Mock Data Classes
# ============================================

@dataclass
class MockVotingResult:
    """Mock VotingResult for testing."""
    player_id: int
    player_name: str
    team_id: int
    position: str
    total_points: int = 0
    vote_share: float = 0.0
    first_place_votes: int = 0


@dataclass
class MockAwardResult:
    """Mock AwardResult for testing."""
    award_id: str
    season: int
    winner: Optional[MockVotingResult] = None
    finalists: List[MockVotingResult] = None
    all_votes: List[MockVotingResult] = None
    candidates_evaluated: int = 0

    def __post_init__(self):
        if self.finalists is None:
            self.finalists = []
        if self.all_votes is None:
            self.all_votes = []

    @property
    def has_winner(self) -> bool:
        return self.winner is not None

    @property
    def top_5(self) -> List[MockVotingResult]:
        if self.winner is None:
            return []
        return [self.winner] + self.finalists[:4]


@dataclass
class MockAllProSelection:
    """Mock AllProSelection for testing."""
    player_id: int
    player_name: str
    team_id: int
    position: str
    team_type: str
    overall_grade: float = 0.0
    position_rank: int = 0


@dataclass
class MockAllProTeam:
    """Mock AllProTeam for testing."""
    season: int
    first_team: Dict[str, List[MockAllProSelection]] = None
    second_team: Dict[str, List[MockAllProSelection]] = None
    total_selections: int = 0

    def __post_init__(self):
        if self.first_team is None:
            self.first_team = {}
        if self.second_team is None:
            self.second_team = {}


@dataclass
class MockProBowlSelection:
    """Mock ProBowlSelection for testing."""
    player_id: int
    player_name: str
    team_id: int
    position: str
    conference: str
    selection_type: str
    overall_grade: float = 0.0
    combined_score: float = 0.0


@dataclass
class MockProBowlRoster:
    """Mock ProBowlRoster for testing."""
    season: int
    afc_roster: Dict[str, List[MockProBowlSelection]] = None
    nfc_roster: Dict[str, List[MockProBowlSelection]] = None
    total_selections: int = 0

    def __post_init__(self):
        if self.afc_roster is None:
            self.afc_roster = {}
        if self.nfc_roster is None:
            self.nfc_roster = {}


@dataclass
class MockStatLeaderEntry:
    """Mock StatisticalLeaderEntry for testing."""
    player_id: int
    player_name: str
    team_id: int
    position: str
    stat_category: str
    stat_value: float
    league_rank: int


@dataclass
class MockStatLeadersResult:
    """Mock StatisticalLeadersResult for testing."""
    season: int
    leaders_by_category: Dict[str, List[MockStatLeaderEntry]] = None
    total_recorded: int = 0

    def __post_init__(self):
        if self.leaders_by_category is None:
            self.leaders_by_category = {}

    def get_category_top_10(self, category: str) -> List[MockStatLeaderEntry]:
        return self.leaders_by_category.get(category, [])


# ============================================
# Test Fixtures
# ============================================

@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    if not HAS_QT:
        return None
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def awards_view(qapp):
    """Create an AwardsView instance for testing."""
    from game_cycle_ui.views.awards_view import AwardsView
    view = AwardsView()
    yield view
    view.deleteLater()


@pytest.fixture
def mock_mvp_winner():
    """Create a mock MVP winner."""
    return MockVotingResult(
        player_id=1,
        player_name="John Smith",
        team_id=22,
        position="QB",
        total_points=437,
        vote_share=0.874,
        first_place_votes=40
    )


@pytest.fixture
def mock_award_result(mock_mvp_winner):
    """Create a mock AwardResult for MVP."""
    finalists = [
        MockVotingResult(player_id=2, player_name="Jane Doe", team_id=28, position="RB",
                         total_points=291, vote_share=0.582),
        MockVotingResult(player_id=3, player_name="Bob Johnson", team_id=12, position="QB",
                         total_points=162, vote_share=0.324),
        MockVotingResult(player_id=4, player_name="Alice Williams", team_id=15, position="WR",
                         total_points=93, vote_share=0.186),
        MockVotingResult(player_id=5, player_name="Mike Davis", team_id=6, position="DE",
                         total_points=64, vote_share=0.128),
    ]
    return MockAwardResult(
        award_id='mvp',
        season=2025,
        winner=mock_mvp_winner,
        finalists=finalists,
        candidates_evaluated=150
    )


@pytest.fixture
def mock_all_pro_team():
    """Create a mock AllProTeam."""
    first_team = {
        'QB': [MockAllProSelection(1, "John Smith", 22, "QB", "FIRST_TEAM", 94.2, 1)],
        'RB': [
            MockAllProSelection(2, "Jane Doe", 28, "RB", "FIRST_TEAM", 91.8, 1),
            MockAllProSelection(6, "Tom Brown", 6, "RB", "FIRST_TEAM", 89.4, 2),
        ],
    }
    second_team = {
        'QB': [MockAllProSelection(3, "Bob Johnson", 12, "QB", "SECOND_TEAM", 88.5, 2)],
        'RB': [
            MockAllProSelection(7, "Sam Wilson", 18, "RB", "SECOND_TEAM", 85.2, 3),
        ],
    }
    return MockAllProTeam(
        season=2025,
        first_team=first_team,
        second_team=second_team,
        total_selections=5
    )


@pytest.fixture
def mock_pro_bowl_roster():
    """Create a mock ProBowlRoster."""
    afc_roster = {
        'QB': [
            MockProBowlSelection(1, "QB1 AFC", 1, "QB", "AFC", "STARTER", 92.0, 85.0),
            MockProBowlSelection(2, "QB2 AFC", 2, "QB", "AFC", "RESERVE", 88.0, 78.0),
        ],
    }
    nfc_roster = {
        'QB': [
            MockProBowlSelection(10, "QB1 NFC", 17, "QB", "NFC", "STARTER", 94.0, 88.0),
        ],
    }
    return MockProBowlRoster(
        season=2025,
        afc_roster=afc_roster,
        nfc_roster=nfc_roster,
        total_selections=3
    )


@pytest.fixture
def mock_stat_leaders():
    """Create mock statistical leaders."""
    leaders = {
        'passing_yards': [
            MockStatLeaderEntry(1, "QB1", 22, "QB", "passing_yards", 5234, 1),
            MockStatLeaderEntry(2, "QB2", 12, "QB", "passing_yards", 4892, 2),
        ],
        'rushing_yards': [
            MockStatLeaderEntry(10, "RB1", 28, "RB", "rushing_yards", 1847, 1),
        ],
    }
    return MockStatLeadersResult(
        season=2025,
        leaders_by_category=leaders,
        total_recorded=30
    )


# ============================================
# Initialization Tests
# ============================================

class TestAwardsViewInitialization:
    """Tests for AwardsView initialization."""

    def test_view_creates_without_errors(self, awards_view):
        """View should create without errors."""
        assert awards_view is not None

    def test_view_has_tabs_widget(self, awards_view):
        """View should have a QTabWidget."""
        assert hasattr(awards_view, 'tabs')
        assert isinstance(awards_view.tabs, QTabWidget)

    def test_view_has_four_tabs(self, awards_view):
        """View should have exactly 4 tabs."""
        assert awards_view.tabs.count() == 4

    def test_tab_names_correct(self, awards_view):
        """Tab names should match expected values."""
        expected = ["Major Awards", "All-Pro Teams", "Pro Bowl", "Stat Leaders"]
        actual = [awards_view.tabs.tabText(i) for i in range(4)]
        assert actual == expected

    def test_season_combo_exists(self, awards_view):
        """Season combo box should exist."""
        assert hasattr(awards_view, 'season_combo')
        assert isinstance(awards_view.season_combo, QComboBox)

    def test_refresh_button_exists(self, awards_view):
        """Refresh button should exist."""
        assert hasattr(awards_view, 'refresh_btn')

    def test_signals_defined(self, awards_view):
        """Required signals should be defined."""
        assert hasattr(awards_view, 'refresh_requested')
        assert hasattr(awards_view, 'player_selected')


# ============================================
# Context Setting Tests
# ============================================

class TestAwardsViewContext:
    """Tests for context setting and data loading."""

    def test_set_context_stores_values(self, awards_view):
        """set_context should store dynasty_id, db_path, and season."""
        with patch.object(awards_view, 'refresh_data'):
            awards_view.set_context("test_dynasty", "/path/to/db", 2025)

        assert awards_view._dynasty_id == "test_dynasty"
        assert awards_view._db_path == "/path/to/db"
        assert awards_view._season == 2025

    def test_set_context_populates_season_combo(self, awards_view):
        """set_context should populate the season dropdown."""
        with patch.object(awards_view, 'refresh_data'):
            awards_view.set_context("test_dynasty", "/path/to/db", 2025)

        assert awards_view.season_combo.count() > 0
        assert awards_view.season_combo.currentData() == 2025


# ============================================
# Major Awards Tab Tests
# ============================================

class TestMajorAwardsTab:
    """Tests for Major Awards tab functionality."""

    def test_all_six_awards_have_widgets(self, awards_view):
        """All 6 major awards should have widgets."""
        expected_awards = ['mvp', 'opoy', 'dpoy', 'oroy', 'droy', 'cpoy']
        for award_id in expected_awards:
            assert award_id in awards_view.award_widgets

    def test_award_widget_has_finalists_table(self, awards_view):
        """Each award widget should have a finalists table."""
        for award_id in ['mvp', 'opoy', 'dpoy']:
            widget = awards_view.award_widgets[award_id]
            finalists_table = widget.findChild(QTableWidget, f"{award_id}_finalists")
            assert finalists_table is not None

    def test_populate_major_awards_displays_winner(self, awards_view, mock_award_result):
        """populate_major_awards should display winner information."""
        awards_view._awards_data = {'mvp': mock_award_result}
        awards_view._populate_major_awards()

        widget = awards_view.award_widgets['mvp']
        finalists_table = widget.findChild(QTableWidget, "mvp_finalists")

        # Should have 5 rows (winner + 4 finalists)
        assert finalists_table.rowCount() == 5


# ============================================
# All-Pro Tab Tests
# ============================================

class TestAllProTab:
    """Tests for All-Pro Teams tab functionality."""

    def test_first_team_table_exists(self, awards_view):
        """First Team table should exist."""
        assert hasattr(awards_view, 'first_team_table')
        assert isinstance(awards_view.first_team_table, QTableWidget)

    def test_second_team_table_exists(self, awards_view):
        """Second Team table should exist."""
        assert hasattr(awards_view, 'second_team_table')
        assert isinstance(awards_view.second_team_table, QTableWidget)

    def test_all_pro_tables_have_correct_columns(self, awards_view):
        """All-Pro tables should have 4 columns."""
        assert awards_view.first_team_table.columnCount() == 4
        assert awards_view.second_team_table.columnCount() == 4

    def test_populate_all_pro_populates_tables(self, awards_view, mock_all_pro_team):
        """populate_all_pro should populate both tables."""
        awards_view._all_pro_data = mock_all_pro_team
        awards_view._populate_all_pro()

        # First team should have 3 rows (1 QB + 2 RB)
        assert awards_view.first_team_table.rowCount() == 3

        # Second team should have 2 rows (1 QB + 1 RB)
        assert awards_view.second_team_table.rowCount() == 2


# ============================================
# Pro Bowl Tab Tests
# ============================================

class TestProBowlTab:
    """Tests for Pro Bowl tab functionality."""

    def test_conference_radios_exist(self, awards_view):
        """AFC and NFC radio buttons should exist."""
        assert hasattr(awards_view, 'afc_radio')
        assert hasattr(awards_view, 'nfc_radio')

    def test_afc_selected_by_default(self, awards_view):
        """AFC should be selected by default."""
        assert awards_view.afc_radio.isChecked()
        assert not awards_view.nfc_radio.isChecked()

    def test_pro_bowl_table_exists(self, awards_view):
        """Pro Bowl table should exist."""
        assert hasattr(awards_view, 'pro_bowl_table')
        assert isinstance(awards_view.pro_bowl_table, QTableWidget)

    def test_pro_bowl_table_has_correct_columns(self, awards_view):
        """Pro Bowl table should have 5 columns."""
        assert awards_view.pro_bowl_table.columnCount() == 5

    def test_conference_toggle_repopulates_table(self, awards_view, mock_pro_bowl_roster):
        """Toggling conference should repopulate the table."""
        awards_view._pro_bowl_data = mock_pro_bowl_roster
        awards_view._populate_pro_bowl()

        # AFC should show 2 QBs
        afc_rows = awards_view.pro_bowl_table.rowCount()

        # Switch to NFC
        awards_view.nfc_radio.setChecked(True)
        awards_view._on_conference_changed()

        # NFC should show 1 QB
        nfc_rows = awards_view.pro_bowl_table.rowCount()

        assert afc_rows == 2
        assert nfc_rows == 1


# ============================================
# Statistical Leaders Tab Tests
# ============================================

class TestStatLeadersTab:
    """Tests for Statistical Leaders tab functionality."""

    def test_category_combo_exists(self, awards_view):
        """Category combo box should exist."""
        assert hasattr(awards_view, 'category_combo')
        assert isinstance(awards_view.category_combo, QComboBox)

    def test_category_combo_has_categories(self, awards_view):
        """Category combo should have statistical categories."""
        assert awards_view.category_combo.count() > 0

    def test_stat_leaders_table_exists(self, awards_view):
        """Statistical leaders table should exist."""
        assert hasattr(awards_view, 'stat_leaders_table')
        assert isinstance(awards_view.stat_leaders_table, QTableWidget)

    def test_stat_leaders_table_has_correct_columns(self, awards_view):
        """Statistical leaders table should have 5 columns."""
        assert awards_view.stat_leaders_table.columnCount() == 5

    def test_populate_stat_leaders_populates_table(self, awards_view, mock_stat_leaders):
        """populate_stat_leaders should populate the table for selected category."""
        awards_view._stat_leaders_data = mock_stat_leaders

        # Set to passing_yards category
        for i in range(awards_view.category_combo.count()):
            if awards_view.category_combo.itemData(i) == 'passing_yards':
                awards_view.category_combo.setCurrentIndex(i)
                break

        awards_view._populate_stat_leaders()

        # Should have 2 rows for passing_yards
        assert awards_view.stat_leaders_table.rowCount() == 2


# ============================================
# Empty State Tests
# ============================================

class TestEmptyStates:
    """Tests for empty state handling."""

    def test_show_no_awards_clears_summary(self, awards_view):
        """_show_no_awards_state should clear summary labels."""
        awards_view._show_no_awards_state()

        assert awards_view.awards_count_label.text() == "0"
        assert awards_view.all_pro_count_label.text() == "0"
        assert awards_view.pro_bowl_count_label.text() == "0"
        assert awards_view.stat_leaders_count_label.text() == "0"

    def test_show_no_awards_clears_tables(self, awards_view):
        """_show_no_awards_state should clear all tables."""
        awards_view._show_no_awards_state()

        assert awards_view.first_team_table.rowCount() == 0
        assert awards_view.second_team_table.rowCount() == 0
        assert awards_view.pro_bowl_table.rowCount() == 0
        assert awards_view.stat_leaders_table.rowCount() == 0


# ============================================
# Helper Method Tests
# ============================================

class TestHelperMethods:
    """Tests for helper methods."""

    def test_format_stat_value_passer_rating(self, awards_view):
        """Passer rating should format with 1 decimal."""
        result = awards_view._format_stat_value('passer_rating', 108.7)
        assert result == "108.7"

    def test_format_stat_value_yards(self, awards_view):
        """Yards should format with commas."""
        result = awards_view._format_stat_value('passing_yards', 5234)
        assert result == "5,234"

    def test_format_stat_value_sacks(self, awards_view):
        """Sacks with half value should show decimal."""
        result = awards_view._format_stat_value('sacks', 12.5)
        assert result == "12.5"

    def test_format_stat_value_sacks_whole(self, awards_view):
        """Sacks with whole value should not show decimal."""
        result = awards_view._format_stat_value('sacks', 12.0)
        assert result == "12"


# ============================================
# Signal Tests
# ============================================

class TestSignals:
    """Tests for signal emissions."""

    def test_player_selected_emits_on_table_click(self, awards_view):
        """Clicking a player row should emit player_selected signal."""
        from PySide6.QtWidgets import QTableWidgetItem

        # Set up a table with a player
        awards_view.first_team_table.setRowCount(1)
        name_item = QTableWidgetItem("Test Player")
        name_item.setData(Qt.UserRole, 123)  # player_id
        awards_view.first_team_table.setItem(0, 1, name_item)

        # Connect to signal
        received_ids = []
        awards_view.player_selected.connect(lambda pid: received_ids.append(pid))

        # Simulate click
        awards_view._on_table_player_clicked(awards_view.first_team_table, 0)

        assert 123 in received_ids
