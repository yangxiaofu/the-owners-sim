"""
Tests for PopularityView widget.

Verifies:
- View initialization
- Context setting
- Data loading
- Filtering (tier and position)
- Sorting
- Table population
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PySide6.QtWidgets import QApplication
from game_cycle_ui.views.popularity_view import PopularityView


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def popularity_view(qapp):
    """Create PopularityView instance."""
    view = PopularityView()
    yield view
    view.deleteLater()


def test_initialization(popularity_view):
    """Test view initializes correctly."""
    assert popularity_view is not None
    assert popularity_view._season == 2025
    assert popularity_view._week == 1
    assert popularity_view._dynasty_id == ""
    assert popularity_view._db_path == ""
    assert popularity_view._tier_filter is None
    assert popularity_view._position_filter is None


def test_set_context(popularity_view):
    """Test setting dynasty context."""
    dynasty_id = "test_dynasty"
    db_path = "data/database/game_cycle/game_cycle.db"
    season = 2025
    week = 10

    with patch('game_cycle.database.connection.GameCycleDatabase'):
        with patch('game_cycle.database.popularity_api.PopularityAPI'):
            popularity_view.set_context(dynasty_id, db_path, season, week)

    assert popularity_view._dynasty_id == dynasty_id
    assert popularity_view._db_path == db_path
    assert popularity_view._season == season
    assert popularity_view._week == week


def test_tier_filter(popularity_view):
    """Test tier filtering."""
    popularity_view._popularity_api = Mock()
    popularity_view._popularity_api.get_players_by_tier = Mock(return_value=[])
    popularity_view._dynasty_id = "test_dynasty"
    popularity_view._season = 2025
    popularity_view._week = 10

    # Change tier filter to STAR
    popularity_view.tier_combo.setCurrentIndex(2)  # STAR is at index 2

    # Verify filter was set
    assert popularity_view._tier_filter == "STAR"


def test_position_filter(popularity_view):
    """Test position filtering."""
    popularity_view._popularity_api = Mock()
    popularity_view._popularity_api.get_top_players = Mock(return_value=[])
    popularity_view._dynasty_id = "test_dynasty"
    popularity_view._season = 2025
    popularity_view._week = 10

    # Change position filter to QB
    popularity_view.position_combo.setCurrentIndex(1)  # QB is at index 1

    # Verify filter was set
    assert popularity_view._position_filter == "QB"


def test_table_headers(popularity_view):
    """Test table has correct headers."""
    headers = []
    for col in range(popularity_view.rankings_table.columnCount()):
        headers.append(popularity_view.rankings_table.horizontalHeaderItem(col).text())

    expected = [
        "Rank", "Player", "Pos", "Team", "Score", "Tier", "Trend",
        "Performance", "Visibility", "Market"
    ]
    assert headers == expected


def test_format_tier(popularity_view):
    """Test tier formatting."""
    assert popularity_view._format_tier("TRANSCENDENT") == "TRANS"
    assert popularity_view._format_tier("STAR") == "STAR"
    assert popularity_view._format_tier("KNOWN") == "KNOWN"
    assert popularity_view._format_tier("ROLE_PLAYER") == "ROLE"
    assert popularity_view._format_tier("UNKNOWN") == "UNK"


def test_format_trend(popularity_view):
    """Test trend formatting."""
    assert popularity_view._format_trend("RISING", 5.5) == "↑ +5.5"
    assert popularity_view._format_trend("FALLING", -3.2) == "↓ -3.2"
    assert popularity_view._format_trend("STABLE", 0.0) == "→ 0.0"
    assert popularity_view._format_trend("STABLE", None) == "→ 0.0"


def test_clear(popularity_view):
    """Test clearing the view."""
    popularity_view.clear()

    assert popularity_view.total_players_label.text() == "0"
    assert popularity_view.avg_popularity_label.text() == "0.0"
    assert popularity_view.top_player_label.text() == "-"
    assert popularity_view.week_label.text() == "1"
    assert popularity_view.rankings_table.rowCount() == 0


def test_get_team_abbr(popularity_view):
    """Test team abbreviation retrieval."""
    # Free agent
    assert popularity_view._get_team_abbr(0) == "FA"

    # Invalid team (should return FA or fallback)
    abbr = popularity_view._get_team_abbr(999)
    assert abbr in ["FA", "T999"]


def test_refresh_without_api(popularity_view):
    """Test refresh without API doesn't crash."""
    popularity_view._popularity_api = None
    popularity_view._dynasty_id = ""

    # Should not crash
    popularity_view.refresh_rankings()


def test_refresh_button_click(popularity_view):
    """Test refresh button emits signal."""
    signal_emitted = False

    def on_refresh():
        nonlocal signal_emitted
        signal_emitted = True

    popularity_view.refresh_requested.connect(on_refresh)
    popularity_view._popularity_api = Mock()
    popularity_view._popularity_api.get_top_players = Mock(return_value=[])
    popularity_view._dynasty_id = "test"

    popularity_view.refresh_btn.click()

    assert signal_emitted
