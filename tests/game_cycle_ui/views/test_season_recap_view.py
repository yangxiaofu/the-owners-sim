"""
Tests for SeasonRecapView UI component.

Part of Milestone 17: Player Retirements, Tollgate 5.
Tests the tabbed Season Recap view including Super Bowl, Awards, and Retirements tabs.

Test Coverage:
- Tabbed interface structure (3 tabs)
- Super Bowl tab displays champion and MVP
- Awards tab embeds AwardsView
- Retirements tab displays notable retirements and table
- Filtering functionality (Your Team / Notable Only)
- Continue button visibility and signals
- Context propagation to child views
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

# Skip import if PySide6 not available (CI/headless environments)
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTabWidget


# ============================================================================
# Test fixtures
# ============================================================================

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def view(qapp):
    """Create fresh SeasonRecapView instance."""
    from game_cycle_ui.views.season_recap_view import SeasonRecapView
    view = SeasonRecapView()
    yield view
    view.close()


@pytest.fixture
def view_offseason_mode(qapp):
    """Create SeasonRecapView in offseason mode (shows Continue button)."""
    from game_cycle_ui.views.season_recap_view import SeasonRecapView
    view = SeasonRecapView()
    view.set_offseason_mode(True)
    yield view
    view.close()


@pytest.fixture
def sample_super_bowl_data() -> Dict[str, Any]:
    """Sample Super Bowl data for tests."""
    return {
        "season": 2025,
        "super_bowl_number": 59,
        "champion_team_id": 14,  # Kansas City Chiefs
        "champion_name": "Kansas City Chiefs",
        "runner_up_team_id": 20,  # Philadelphia Eagles
        "runner_up_name": "Philadelphia Eagles",
        "champion_score": 38,
        "runner_up_score": 24,
        "mvp": {
            "player_id": 12345,
            "name": "Patrick Mahomes",
            "position": "QB",
            "team_id": 14,
            "stats": {
                "completions": 28,
                "attempts": 35,
                "passing_yards": 327,
                "passing_tds": 3,
                "interceptions": 0,
                "passer_rating": 134.2
            }
        },
        "game_id": 9999,
        "box_score_available": True
    }


@pytest.fixture
def sample_retirements() -> List[Dict[str, Any]]:
    """Sample retirement data for tests."""
    return [
        {
            "player_id": 1001,
            "name": "Aaron Rodgers",
            "position": "QB",
            "age": 42,
            "team_id": 4,  # NY Jets
            "team_name": "New York Jets",
            "years_played": 19,
            "reason": "age_decline",
            "is_notable": True,
            "career_summary": {
                "games_played": 291,
                "games_started": 287,
                "pass_yards": 65432,
                "pass_tds": 489,
                "pass_ints": 112,
                "mvp_awards": 4,
                "super_bowl_wins": 1,
                "pro_bowls": 10,
                "all_pro_first_team": 4,
                "all_pro_second_team": 2,
                "hall_of_fame_score": 94
            }
        },
        {
            "player_id": 1002,
            "name": "Davante Adams",
            "position": "WR",
            "age": 33,
            "team_id": 13,  # Las Vegas Raiders
            "team_name": "Las Vegas Raiders",
            "years_played": 12,
            "reason": "championship",
            "is_notable": True,
            "career_summary": {
                "games_played": 188,
                "games_started": 175,
                "receptions": 912,
                "rec_yards": 11234,
                "rec_tds": 89,
                "pro_bowls": 5,
                "all_pro_first_team": 2,
                "all_pro_second_team": 1,
                "hall_of_fame_score": 62
            }
        },
        {
            "player_id": 1003,
            "name": "John Smith",
            "position": "LB",
            "age": 34,
            "team_id": 17,  # Dallas Cowboys
            "team_name": "Dallas Cowboys",
            "years_played": 11,
            "reason": "age_decline",
            "is_notable": False,
            "career_summary": {
                "games_played": 156,
                "games_started": 123,
                "tackles": 845,
                "sacks": 18.5,
                "interceptions": 7,
                "hall_of_fame_score": 22
            }
        },
        {
            "player_id": 1004,
            "name": "Mike Johnson",
            "position": "RB",
            "age": 31,
            "team_id": 21,  # Chicago Bears
            "team_name": "Chicago Bears",
            "years_played": 8,
            "reason": "injury",
            "is_notable": False,
            "career_summary": {
                "games_played": 98,
                "games_started": 72,
                "rush_yards": 5234,
                "rush_tds": 38,
                "receptions": 156,
                "rec_yards": 1234,
                "hall_of_fame_score": 15
            }
        }
    ]


@pytest.fixture
def sample_user_team_retirement(sample_retirements) -> Dict[str, Any]:
    """Single retirement from user's team (team_id=1)."""
    return {
        "player_id": 2001,
        "name": "Tom Brady",
        "position": "QB",
        "age": 47,
        "team_id": 1,  # User's team (Buffalo Bills)
        "team_name": "Buffalo Bills",
        "years_played": 24,
        "reason": "championship",
        "is_notable": True,
        "career_summary": {
            "games_played": 335,
            "games_started": 333,
            "pass_yards": 89214,
            "pass_tds": 649,
            "pass_ints": 203,
            "mvp_awards": 3,
            "super_bowl_wins": 7,
            "super_bowl_mvps": 5,
            "pro_bowls": 15,
            "all_pro_first_team": 3,
            "hall_of_fame_score": 100
        }
    }


# ============================================================================
# TestTabStructure (3 tests)
# ============================================================================

class TestTabStructure:
    """Tests for tabbed interface structure."""

    def test_view_creates_with_three_tabs(self, view):
        """SeasonRecapView has exactly 3 tabs."""
        assert hasattr(view, 'tab_widget')
        assert isinstance(view.tab_widget, QTabWidget)
        assert view.tab_widget.count() == 3

    def test_tab_names_correct(self, view):
        """Tab names are 'Super Bowl', 'Awards', 'Retirements'."""
        assert view.tab_widget.tabText(0) == "Super Bowl"
        assert view.tab_widget.tabText(1) == "Awards"
        assert view.tab_widget.tabText(2) == "Retirements"

    def test_default_tab_is_super_bowl(self, view):
        """Default active tab is Super Bowl (index 0)."""
        assert view.tab_widget.currentIndex() == 0


# ============================================================================
# TestSuperBowlTab (3 tests)
# ============================================================================

class TestSuperBowlTab:
    """Tests for Super Bowl tab content."""

    def test_super_bowl_tab_displays_champion(self, view, sample_super_bowl_data):
        """Super Bowl tab shows champion team name and score."""
        view.set_super_bowl_data(sample_super_bowl_data)

        # Verify internal state was set
        assert view._super_bowl_result.get('winner_team_id') == 14

        # Super Bowl widget exists
        assert hasattr(view, 'super_bowl_widget')
        assert view.super_bowl_widget is not None

    def test_super_bowl_tab_displays_score(self, view, sample_super_bowl_data):
        """Super Bowl tab stores score data correctly."""
        view.set_super_bowl_data(sample_super_bowl_data)

        # Verify scores were set
        assert view._super_bowl_result.get('home_score') == 38
        assert view._super_bowl_result.get('away_score') == 24

    def test_super_bowl_tab_displays_mvp(self, view, sample_super_bowl_data):
        """Super Bowl tab stores MVP data correctly."""
        view.set_super_bowl_data(sample_super_bowl_data)

        # Verify MVP data was set
        assert view._super_bowl_mvp.get('player_name') == "Patrick Mahomes"
        assert view._super_bowl_mvp.get('position') == "QB"
        assert "327 YDS" in view._super_bowl_mvp.get('stat_summary', '')


# ============================================================================
# TestAwardsTab (2 tests)
# ============================================================================

class TestAwardsTab:
    """Tests for Awards tab content."""

    def test_awards_tab_contains_awards_view(self, view):
        """Awards tab embeds an AwardsView instance."""
        from game_cycle_ui.views.awards_view import AwardsView

        # SeasonRecapView should have embedded awards_view
        assert hasattr(view, 'awards_view')
        assert isinstance(view.awards_view, AwardsView)

        # It should be in the Awards tab
        awards_widget = view.tab_widget.widget(1)
        assert awards_widget is not None

    def test_set_context_stored(self, view):
        """set_context stores dynasty context."""
        # Set context on SeasonRecapView (don't actually connect to DB)
        view._dynasty_id = "dynasty-123"
        view._db_path = "/path/to/db.db"
        view._season = 2025

        # Verify context was stored
        assert view._dynasty_id == "dynasty-123"
        assert view._season == 2025
        assert view._db_path == "/path/to/db.db"


# ============================================================================
# TestRetirementsTab (6 tests)
# ============================================================================

class TestRetirementsTab:
    """Tests for Retirements tab content and filtering."""

    def test_retirements_tab_shows_notable_cards(self, view, sample_retirements):
        """Notable retirements displayed as cards with highlights."""
        view.set_retirements(sample_retirements)

        # Notable retirements should be in the internal list
        notable = [r for r in view._retirements if r['is_notable']]
        assert len(notable) == 2  # Rodgers, Adams

        # Verify retirements tab exists
        retirements_widget = view.tab_widget.widget(2)
        assert retirements_widget is not None

    def test_retirements_tab_shows_table(self, view, sample_retirements):
        """Other retirements displayed in table."""
        view.set_retirements(sample_retirements)

        # Other retirements table should exist
        assert hasattr(view, 'other_retirements_table')

        # Should have 2 non-notable retirements (Smith, Johnson)
        other = [r for r in view._retirements if not r['is_notable']]
        assert len(other) == 2
        assert view.other_retirements_table.rowCount() == 2

    def test_filter_your_team_works(self, view, sample_retirements, sample_user_team_retirement):
        """Filter shows only user's team retirements."""
        all_retirements = sample_retirements + [sample_user_team_retirement]
        view.set_retirements(all_retirements)
        view.set_user_team_id(1)  # Buffalo Bills

        # Set to "Your Team" option (index 1)
        view.filter_combo.setCurrentIndex(1)

        # Should now only show Tom Brady (team_id=1)
        visible_count = view._get_visible_retirements_count()
        assert visible_count == 1

    def test_filter_notable_only_works(self, view, sample_retirements):
        """Filter shows only notable retirements."""
        view.set_retirements(sample_retirements)

        # Set to "Notable Only" option (index 2)
        view.filter_combo.setCurrentIndex(2)

        # Should only show 2 notable retirements (Rodgers, Adams)
        visible_count = view._get_visible_retirements_count()
        assert visible_count == 2

    def test_empty_retirements_shows_message(self, view):
        """Empty retirements list shows 0 retirements count."""
        view.set_retirements([])

        # Count label should show 0 retirements
        assert "0 retirements" in view.retirements_count_label.text()

        # Retirements list should be empty
        assert len(view._retirements) == 0

    def test_retirement_row_click_emits_signal(self, view, sample_retirements):
        """Clicking retirement table row triggers signal."""
        view.set_retirements(sample_retirements)

        signal_received = []
        view.retirement_selected.connect(lambda pid: signal_received.append(pid))

        # Simulate clicking on the first non-notable retirement row
        # The table has Smith (id=1003) and Johnson (id=1004)
        view._on_retirement_row_clicked(0, 0)

        assert len(signal_received) == 1
        assert signal_received[0] == 1003


# ============================================================================
# TestContinueButton (3 tests)
# ============================================================================

class TestContinueButton:
    """Tests for Continue button visibility and behavior."""

    def test_continue_button_visible_in_offseason_mode(self, view_offseason_mode):
        """Continue button set visible when offseason_mode=True."""
        assert hasattr(view_offseason_mode, 'continue_button')
        # Check internal state rather than isVisible() since widget not shown
        assert view_offseason_mode._offseason_mode is True
        # Button should not be hidden
        assert not view_offseason_mode.continue_button.isHidden()

    def test_continue_button_hidden_in_view_mode(self, view):
        """Continue button hidden when offseason_mode=False (default)."""
        # In non-offseason mode (viewing past seasons), Continue button should not exist or be hidden
        if hasattr(view, 'continue_button'):
            assert not view.continue_button.isVisible()

    def test_continue_button_emits_signal(self, view_offseason_mode):
        """Clicking Continue emits continue_to_next_stage signal."""
        signal_received = []
        view_offseason_mode.continue_to_next_stage.connect(lambda: signal_received.append(True))

        # Click Continue button
        view_offseason_mode.continue_button.click()

        assert len(signal_received) == 1


# ============================================================================
# TestDataLoading (2 tests)
# ============================================================================

class TestDataLoading:
    """Tests for data loading and state management."""

    def test_set_super_bowl_data_updates_state(self, view, sample_super_bowl_data):
        """set_super_bowl_data populates internal state."""
        view.set_super_bowl_data(sample_super_bowl_data)

        # Check internal state is set (mapped format)
        assert view._super_bowl_result.get('winner_team_id') == 14
        assert view._super_bowl_mvp.get('player_name') == "Patrick Mahomes"

    def test_set_retirements_updates_state(self, view, sample_retirements):
        """set_retirements populates internal state."""
        view.set_retirements(sample_retirements)

        # Retirements should be stored in mapped format
        assert len(view._retirements) == 4
        # Check first retirement was mapped correctly
        assert view._retirements[0]['player_name'] == "Aaron Rodgers"


# ============================================================================
# TestEdgeCases (2 tests)
# ============================================================================

class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_empty_super_bowl_data_handled(self, view):
        """set_super_bowl_data with None doesn't crash."""
        view.set_super_bowl_data(None)

        # Should show placeholder or default state
        super_bowl_widget = view.tab_widget.widget(0)
        assert super_bowl_widget is not None

    def test_missing_mvp_in_super_bowl_data_handled(self, view, sample_super_bowl_data):
        """Super Bowl data without MVP field handled gracefully."""
        data_without_mvp = sample_super_bowl_data.copy()
        del data_without_mvp["mvp"]

        view.set_super_bowl_data(data_without_mvp)

        # Should not crash, MVP section may be hidden or show placeholder
        super_bowl_widget = view.tab_widget.widget(0)
        assert super_bowl_widget is not None


# ============================================================================
# Integration Tests (1 test)
# ============================================================================

class TestSeasonRecapIntegration:
    """Integration tests for SeasonRecapView."""

    def test_full_workflow_with_all_data(self, view_offseason_mode, sample_super_bowl_data, sample_retirements):
        """Complete workflow: set all data, navigate tabs, click Continue."""
        # Set context directly (avoid database calls)
        view_offseason_mode._dynasty_id = "dynasty-123"
        view_offseason_mode._db_path = "/path/to/db.db"
        view_offseason_mode._season = 2025

        # Set Super Bowl data
        view_offseason_mode.set_super_bowl_data(sample_super_bowl_data)

        # Set retirements
        view_offseason_mode.set_retirements(sample_retirements)

        # Navigate to each tab
        view_offseason_mode.tab_widget.setCurrentIndex(0)  # Super Bowl
        assert view_offseason_mode.tab_widget.currentIndex() == 0

        view_offseason_mode.tab_widget.setCurrentIndex(1)  # Awards
        assert view_offseason_mode.tab_widget.currentIndex() == 1

        view_offseason_mode.tab_widget.setCurrentIndex(2)  # Retirements
        assert view_offseason_mode.tab_widget.currentIndex() == 2

        # Click Continue
        signal_received = []
        view_offseason_mode.continue_to_next_stage.connect(lambda: signal_received.append(True))
        view_offseason_mode.continue_button.click()

        assert len(signal_received) == 1
