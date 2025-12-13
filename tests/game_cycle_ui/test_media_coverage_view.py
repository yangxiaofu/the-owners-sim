"""
Tests for MediaCoverageView and related media UI components.

Part of Milestone 12: Media Coverage, Tollgate 7.
Tests headline cards, power rankings widget, media coverage view, and article dialog.
"""

import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock

# Skip import if PySide6 not available (CI/headless environments)
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


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
def sample_headline_data() -> Dict[str, Any]:
    """Sample headline data for testing."""
    return {
        "id": 1,
        "headline": "Chiefs Clinch Playoff Berth with Dominant Win",
        "subheadline": "Kansas City improves to 10-2 with victory over division rival",
        "body_text": "The Kansas City Chiefs secured their spot in the playoffs...",
        "sentiment": "POSITIVE",
        "priority": 80,
        "headline_type": "GAME_RECAP",
        "team_ids": [15],  # Chiefs
        "player_ids": [101, 102],
    }


@pytest.fixture
def sample_rankings_data() -> List[Dict[str, Any]]:
    """Sample power rankings data for testing."""
    return [
        {
            "team_id": 15,
            "team_name": "Kansas City Chiefs",
            "rank": 1,
            "previous_rank": 1,
            "tier": "ELITE",
            "blurb": "The Chiefs continue to dominate the AFC.",
        },
        {
            "team_id": 21,
            "team_name": "Philadelphia Eagles",
            "rank": 2,
            "previous_rank": 4,
            "tier": "ELITE",
            "blurb": "Eagles soar up the rankings after impressive win.",
        },
        {
            "team_id": 6,
            "team_name": "Dallas Cowboys",
            "rank": 3,
            "previous_rank": 2,
            "tier": "CONTENDER",
            "blurb": "Cowboys slip after tough loss.",
        },
    ]


# ============================================================================
# Theme constants tests
# ============================================================================

class TestThemeConstants:
    """Test theme constants for media coverage."""

    def test_sentiment_colors_exist(self):
        """SENTIMENT_COLORS has required entries."""
        from game_cycle_ui.theme import SENTIMENT_COLORS
        assert "POSITIVE" in SENTIMENT_COLORS
        assert "NEGATIVE" in SENTIMENT_COLORS
        assert "NEUTRAL" in SENTIMENT_COLORS
        assert "HYPE" in SENTIMENT_COLORS
        assert "CRITICAL" in SENTIMENT_COLORS

    def test_sentiment_badges_exist(self):
        """SENTIMENT_BADGES has required entries."""
        from game_cycle_ui.theme import SENTIMENT_BADGES
        assert "POSITIVE" in SENTIMENT_BADGES
        assert "NEGATIVE" in SENTIMENT_BADGES
        assert "NEUTRAL" in SENTIMENT_BADGES
        assert "HYPE" in SENTIMENT_BADGES
        assert "CRITICAL" in SENTIMENT_BADGES

    def test_tier_colors_exist(self):
        """TIER_COLORS has required entries."""
        from game_cycle_ui.theme import TIER_COLORS
        assert "ELITE" in TIER_COLORS
        assert "CONTENDER" in TIER_COLORS
        assert "PLAYOFF" in TIER_COLORS
        assert "BUBBLE" in TIER_COLORS
        assert "REBUILDING" in TIER_COLORS

    def test_tier_text_colors_exist(self):
        """TIER_TEXT_COLORS has required entries."""
        from game_cycle_ui.theme import TIER_TEXT_COLORS
        assert "ELITE" in TIER_TEXT_COLORS
        assert "CONTENDER" in TIER_TEXT_COLORS
        assert "PLAYOFF" in TIER_TEXT_COLORS
        assert "BUBBLE" in TIER_TEXT_COLORS
        assert "REBUILDING" in TIER_TEXT_COLORS

    def test_movement_colors_exist(self):
        """MOVEMENT_COLORS has required entries."""
        from game_cycle_ui.theme import MOVEMENT_COLORS
        assert "up" in MOVEMENT_COLORS
        assert "down" in MOVEMENT_COLORS
        assert "same" in MOVEMENT_COLORS
        assert "new" in MOVEMENT_COLORS


# ============================================================================
# HeadlineCardWidget tests
# ============================================================================

class TestHeadlineCardWidget:
    """Test HeadlineCardWidget."""

    def test_headline_card_initializes(self, qapp, sample_headline_data):
        """HeadlineCardWidget initializes without errors."""
        from game_cycle_ui.widgets.headline_card_widget import HeadlineCardWidget
        card = HeadlineCardWidget(sample_headline_data)
        assert card is not None

    def test_headline_card_displays_headline(self, qapp, sample_headline_data):
        """HeadlineCardWidget displays headline text."""
        from game_cycle_ui.widgets.headline_card_widget import HeadlineCardWidget
        card = HeadlineCardWidget(sample_headline_data)
        assert card._headline_label.text() == sample_headline_data["headline"]

    def test_headline_card_displays_badge(self, qapp, sample_headline_data):
        """HeadlineCardWidget displays sentiment badge."""
        from game_cycle_ui.widgets.headline_card_widget import HeadlineCardWidget
        from game_cycle_ui.theme import SENTIMENT_BADGES
        card = HeadlineCardWidget(sample_headline_data)
        expected_badge = SENTIMENT_BADGES.get("POSITIVE", "•")
        assert card._badge.text() == expected_badge

    def test_headline_card_featured_styling(self, qapp, sample_headline_data):
        """Featured card has larger text styling."""
        from game_cycle_ui.widgets.headline_card_widget import HeadlineCardWidget
        card = HeadlineCardWidget(sample_headline_data, is_featured=True)
        # Check style includes larger font size
        style = card._headline_label.styleSheet()
        assert "16px" in style

    def test_headline_card_regular_styling(self, qapp, sample_headline_data):
        """Regular card has smaller text styling."""
        from game_cycle_ui.widgets.headline_card_widget import HeadlineCardWidget
        card = HeadlineCardWidget(sample_headline_data, is_featured=False)
        style = card._headline_label.styleSheet()
        assert "13px" in style

    def test_headline_card_emits_clicked_signal(self, qapp, sample_headline_data):
        """HeadlineCardWidget emits clicked signal with headline_id."""
        from game_cycle_ui.widgets.headline_card_widget import HeadlineCardWidget
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent

        card = HeadlineCardWidget(sample_headline_data)
        signal_received = []

        card.clicked.connect(lambda id: signal_received.append(id))

        # Simulate mouse press
        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            card.rect().center(),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        card.mousePressEvent(event)

        assert len(signal_received) == 1
        assert signal_received[0] == sample_headline_data["id"]

    def test_headline_card_headline_id_property(self, qapp, sample_headline_data):
        """headline_id property returns correct ID."""
        from game_cycle_ui.widgets.headline_card_widget import HeadlineCardWidget
        card = HeadlineCardWidget(sample_headline_data)
        assert card.headline_id == sample_headline_data["id"]

    def test_headline_card_headline_data_property(self, qapp, sample_headline_data):
        """headline_data property returns full data."""
        from game_cycle_ui.widgets.headline_card_widget import HeadlineCardWidget
        card = HeadlineCardWidget(sample_headline_data)
        assert card.headline_data == sample_headline_data


# ============================================================================
# PowerRankingsWidget tests
# ============================================================================

class TestPowerRankingsWidget:
    """Test PowerRankingsWidget."""

    def test_power_rankings_initializes(self, qapp):
        """PowerRankingsWidget initializes without errors."""
        from game_cycle_ui.widgets.power_rankings_widget import PowerRankingsWidget
        widget = PowerRankingsWidget()
        assert widget is not None

    def test_power_rankings_has_table(self, qapp):
        """PowerRankingsWidget has a table with 5 columns."""
        from game_cycle_ui.widgets.power_rankings_widget import PowerRankingsWidget
        widget = PowerRankingsWidget()
        assert widget._table is not None
        assert widget._table.columnCount() == 5

    def test_power_rankings_set_rankings(self, qapp, sample_rankings_data):
        """set_rankings populates the table."""
        from game_cycle_ui.widgets.power_rankings_widget import PowerRankingsWidget
        widget = PowerRankingsWidget()
        widget.set_rankings(sample_rankings_data)
        assert widget._table.rowCount() == 3

    def test_power_rankings_displays_rank(self, qapp, sample_rankings_data):
        """Rankings display rank numbers correctly."""
        from game_cycle_ui.widgets.power_rankings_widget import PowerRankingsWidget
        widget = PowerRankingsWidget()
        widget.set_rankings(sample_rankings_data)

        # Check first row rank
        rank_item = widget._table.item(0, widget.COL_RANK)
        assert rank_item.text() == "1"

    def test_power_rankings_displays_team_name(self, qapp, sample_rankings_data):
        """Rankings display team names correctly."""
        from game_cycle_ui.widgets.power_rankings_widget import PowerRankingsWidget
        widget = PowerRankingsWidget()
        widget.set_rankings(sample_rankings_data)

        team_item = widget._table.item(0, widget.COL_TEAM)
        assert team_item.text() == "Kansas City Chiefs"

    def test_power_rankings_displays_tier(self, qapp, sample_rankings_data):
        """Rankings display tier correctly."""
        from game_cycle_ui.widgets.power_rankings_widget import PowerRankingsWidget
        widget = PowerRankingsWidget()
        widget.set_rankings(sample_rankings_data)

        tier_item = widget._table.item(0, widget.COL_TIER)
        assert tier_item.text() == "Elite"  # Title case

    def test_power_rankings_calculates_movement_up(self, qapp):
        """Movement arrow calculated for rising team."""
        from game_cycle_ui.widgets.power_rankings_widget import PowerRankingsWidget
        widget = PowerRankingsWidget()

        # Team moved up from 4 to 2
        rankings = [{
            "team_id": 1,
            "team_name": "Test Team",
            "rank": 2,
            "previous_rank": 4,
            "tier": "ELITE",
            "blurb": "Rising"
        }]
        widget.set_rankings(rankings)

        move_item = widget._table.item(0, widget.COL_MOVE)
        assert "▲" in move_item.text()
        assert "2" in move_item.text()

    def test_power_rankings_calculates_movement_down(self, qapp):
        """Movement arrow calculated for falling team."""
        from game_cycle_ui.widgets.power_rankings_widget import PowerRankingsWidget
        widget = PowerRankingsWidget()

        # Team moved down from 2 to 5
        rankings = [{
            "team_id": 1,
            "team_name": "Test Team",
            "rank": 5,
            "previous_rank": 2,
            "tier": "CONTENDER",
            "blurb": "Falling"
        }]
        widget.set_rankings(rankings)

        move_item = widget._table.item(0, widget.COL_MOVE)
        assert "▼" in move_item.text()
        assert "3" in move_item.text()

    def test_power_rankings_calculates_movement_same(self, qapp):
        """Movement dash shown for unchanged rank."""
        from game_cycle_ui.widgets.power_rankings_widget import PowerRankingsWidget
        widget = PowerRankingsWidget()

        rankings = [{
            "team_id": 1,
            "team_name": "Test Team",
            "rank": 1,
            "previous_rank": 1,
            "tier": "ELITE",
            "blurb": "Steady"
        }]
        widget.set_rankings(rankings)

        move_item = widget._table.item(0, widget.COL_MOVE)
        assert move_item.text() == "—"

    def test_power_rankings_new_entry(self, qapp):
        """NEW shown when no previous rank."""
        from game_cycle_ui.widgets.power_rankings_widget import PowerRankingsWidget
        widget = PowerRankingsWidget()

        rankings = [{
            "team_id": 1,
            "team_name": "Test Team",
            "rank": 10,
            "previous_rank": None,
            "tier": "PLAYOFF",
            "blurb": "First ranking"
        }]
        widget.set_rankings(rankings)

        move_item = widget._table.item(0, widget.COL_MOVE)
        assert move_item.text() == "NEW"

    def test_power_rankings_clear(self, qapp, sample_rankings_data):
        """clear() removes all rankings."""
        from game_cycle_ui.widgets.power_rankings_widget import PowerRankingsWidget
        widget = PowerRankingsWidget()
        widget.set_rankings(sample_rankings_data)

        widget.clear()

        assert widget._table.rowCount() == 0
        assert len(widget._rankings) == 0


# ============================================================================
# MediaCoverageView tests
# ============================================================================

class TestMediaCoverageView:
    """Test MediaCoverageView."""

    def test_media_coverage_view_initializes(self, qapp):
        """MediaCoverageView initializes without errors."""
        from game_cycle_ui.views.media_coverage_view import MediaCoverageView
        view = MediaCoverageView()
        assert view is not None

    def test_media_coverage_view_has_tabs(self, qapp):
        """MediaCoverageView has 3 tabs."""
        from game_cycle_ui.views.media_coverage_view import MediaCoverageView
        view = MediaCoverageView()
        assert view._tabs.count() == 3

    def test_media_coverage_view_tab_names(self, qapp):
        """MediaCoverageView tabs have correct names."""
        from game_cycle_ui.views.media_coverage_view import MediaCoverageView
        view = MediaCoverageView()
        assert view._tabs.tabText(0) == "Headlines"
        assert view._tabs.tabText(1) == "Power Rankings"
        assert view._tabs.tabText(2) == "Award Watch"

    def test_media_coverage_view_has_week_combo(self, qapp):
        """MediaCoverageView has week selector dropdown."""
        from game_cycle_ui.views.media_coverage_view import MediaCoverageView
        view = MediaCoverageView()
        assert view._week_combo is not None
        # Should have 18 weeks
        assert view._week_combo.count() == 18

    def test_media_coverage_view_has_refresh_button(self, qapp):
        """MediaCoverageView has refresh button."""
        from game_cycle_ui.views.media_coverage_view import MediaCoverageView
        view = MediaCoverageView()
        assert view._refresh_btn is not None

    def test_media_coverage_view_emits_refresh_signal(self, qapp):
        """Refresh button emits refresh_requested signal."""
        from game_cycle_ui.views.media_coverage_view import MediaCoverageView
        view = MediaCoverageView()

        signal_received = []
        view.refresh_requested.connect(lambda: signal_received.append(True))

        view._refresh_btn.click()

        assert len(signal_received) == 1

    def test_media_coverage_view_week_combo_data(self, qapp):
        """Week combo has correct week data."""
        from game_cycle_ui.views.media_coverage_view import MediaCoverageView
        view = MediaCoverageView()

        # First week should be Week 1
        assert view._week_combo.itemData(0) == 1
        # Last week should be Week 18
        assert view._week_combo.itemData(17) == 18

    def test_media_coverage_view_week_combo_selection(self, qapp):
        """Week combo selection returns correct week via currentData."""
        from game_cycle_ui.views.media_coverage_view import MediaCoverageView
        view = MediaCoverageView()
        view._week_combo.setCurrentIndex(4)  # Week 5

        assert view._week_combo.currentData() == 5


# ============================================================================
# ArticleDetailDialog tests
# ============================================================================

class TestArticleDetailDialog:
    """Test ArticleDetailDialog."""

    def test_article_dialog_initializes(self, qapp, sample_headline_data):
        """ArticleDetailDialog initializes without errors."""
        from game_cycle_ui.dialogs.article_detail_dialog import ArticleDetailDialog
        dialog = ArticleDetailDialog(sample_headline_data)
        assert dialog is not None

    def test_article_dialog_shows_headline(self, qapp, sample_headline_data):
        """ArticleDetailDialog displays headline text."""
        from game_cycle_ui.dialogs.article_detail_dialog import ArticleDetailDialog
        dialog = ArticleDetailDialog(sample_headline_data)
        # The headline should be visible somewhere in the dialog
        assert dialog._data["headline"] == sample_headline_data["headline"]

    def test_article_dialog_shows_body_text(self, qapp, sample_headline_data):
        """ArticleDetailDialog handles body text."""
        from game_cycle_ui.dialogs.article_detail_dialog import ArticleDetailDialog
        dialog = ArticleDetailDialog(sample_headline_data)
        assert dialog._data["body_text"] == sample_headline_data["body_text"]

    def test_article_dialog_handles_missing_body(self, qapp):
        """ArticleDetailDialog handles missing body text gracefully."""
        from game_cycle_ui.dialogs.article_detail_dialog import ArticleDetailDialog

        headline_data = {
            "id": 1,
            "headline": "Test Headline",
            "sentiment": "NEUTRAL",
        }

        dialog = ArticleDetailDialog(headline_data)
        assert dialog is not None  # Should not crash

    def test_article_dialog_is_modal(self, qapp, sample_headline_data):
        """ArticleDetailDialog is modal."""
        from game_cycle_ui.dialogs.article_detail_dialog import ArticleDetailDialog
        dialog = ArticleDetailDialog(sample_headline_data)
        assert dialog.isModal()


# ============================================================================
# Integration tests
# ============================================================================

class TestMediaCoverageIntegration:
    """Integration tests for media coverage UI components."""

    def test_headline_card_in_view(self, qapp, sample_headline_data):
        """HeadlineCardWidget can be added to MediaCoverageView scroll area."""
        from game_cycle_ui.views.media_coverage_view import MediaCoverageView
        from game_cycle_ui.widgets.headline_card_widget import HeadlineCardWidget

        view = MediaCoverageView()
        card = HeadlineCardWidget(sample_headline_data)

        # Should be able to add to scroll area layout
        view._headlines_layout.addWidget(card)
        assert view._headlines_layout.count() >= 1

    def test_power_rankings_in_view(self, qapp, sample_rankings_data):
        """PowerRankingsWidget in MediaCoverageView can display rankings."""
        from game_cycle_ui.views.media_coverage_view import MediaCoverageView

        view = MediaCoverageView()
        view._rankings_widget.set_rankings(sample_rankings_data)

        assert view._rankings_widget._table.rowCount() == 3

    def test_headline_click_opens_dialog(self, qapp, sample_headline_data):
        """Clicking headline should open article dialog."""
        from game_cycle_ui.views.media_coverage_view import MediaCoverageView
        from game_cycle_ui.widgets.headline_card_widget import HeadlineCardWidget
        from game_cycle_ui.dialogs.article_detail_dialog import ArticleDetailDialog

        view = MediaCoverageView()
        view._headline_data_cache = {sample_headline_data["id"]: sample_headline_data}

        # Simulate headline click (should not crash)
        view._on_headline_clicked(sample_headline_data["id"])
        # Dialog would be shown - can't easily test modal dialogs

    def test_empty_state_handling(self, qapp):
        """View handles empty data gracefully."""
        from game_cycle_ui.views.media_coverage_view import MediaCoverageView

        view = MediaCoverageView()
        view._rankings_widget.set_rankings([])

        assert view._rankings_widget._table.rowCount() == 0


# ============================================================================
# Module exports tests
# ============================================================================

class TestModuleExports:
    """Test that modules export correctly."""

    def test_views_init_exports_media_coverage_view(self):
        """MediaCoverageView exported from views/__init__.py."""
        from game_cycle_ui.views import MediaCoverageView
        assert MediaCoverageView is not None

    def test_widgets_init_exports_headline_card(self):
        """HeadlineCardWidget exported from widgets/__init__.py."""
        from game_cycle_ui.widgets import HeadlineCardWidget
        assert HeadlineCardWidget is not None

    def test_widgets_init_exports_power_rankings(self):
        """PowerRankingsWidget exported from widgets/__init__.py."""
        from game_cycle_ui.widgets import PowerRankingsWidget
        assert PowerRankingsWidget is not None

    def test_dialogs_init_exports_article_dialog(self):
        """ArticleDetailDialog exported from dialogs/__init__.py."""
        from game_cycle_ui.dialogs import ArticleDetailDialog
        assert ArticleDetailDialog is not None
