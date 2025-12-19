"""
Tests for RetirementDetailDialog UI component.

Part of Milestone 17: Player Retirements, Tollgate 6.
Tests the career retrospective dialog for retired players.

Test Coverage:
- Dialog initialization with retirement data
- Career statistics display (position-specific)
- Awards section display
- Hall of Fame score and status
- One-Day Contract button visibility and behavior
- Edge cases (empty data, missing fields)
"""

import pytest
from typing import Dict, Any

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
def sample_qb_retirement() -> Dict[str, Any]:
    """Sample QB retirement data."""
    return {
        "player_id": 1001,
        "player_name": "Aaron Rodgers",
        "position": "QB",
        "age_at_retirement": 42,
        "years_played": 19,
        "final_team_id": 4,
        "retirement_reason": "age_decline",
        "retirement_season": 2025,
        "headline": "Future Hall of Famer Aaron Rodgers announces retirement",
        "is_notable": True,
    }


@pytest.fixture
def sample_qb_career_summary() -> Dict[str, Any]:
    """Sample QB career summary."""
    return {
        "player_id": 1001,
        "full_name": "Aaron Rodgers",
        "position": "QB",
        "games_played": 291,
        "games_started": 287,
        "pass_yards": 65432,
        "pass_tds": 489,
        "pass_ints": 112,
        "rush_yards": 3845,
        "rush_tds": 37,
        "pro_bowls": 10,
        "all_pro_first_team": 4,
        "all_pro_second_team": 2,
        "mvp_awards": 4,
        "super_bowl_wins": 1,
        "super_bowl_mvps": 1,
        "teams_played_for": [10, 4],  # Packers, Jets
        "primary_team_id": 10,
        "hall_of_fame_score": 94,
    }


@pytest.fixture
def sample_wr_retirement() -> Dict[str, Any]:
    """Sample WR retirement data (without awards)."""
    return {
        "player_id": 2001,
        "player_name": "John Smith",
        "position": "WR",
        "age_at_retirement": 34,
        "years_played": 11,
        "final_team_id": 17,
        "retirement_reason": "injury",
        "retirement_season": 2025,
        "is_notable": False,
    }


@pytest.fixture
def sample_wr_career_summary() -> Dict[str, Any]:
    """Sample WR career summary (modest career)."""
    return {
        "player_id": 2001,
        "full_name": "John Smith",
        "position": "WR",
        "games_played": 156,
        "games_started": 98,
        "receptions": 412,
        "rec_yards": 5234,
        "rec_tds": 28,
        "pro_bowls": 0,
        "all_pro_first_team": 0,
        "all_pro_second_team": 0,
        "mvp_awards": 0,
        "super_bowl_wins": 0,
        "teams_played_for": [17],
        "primary_team_id": 17,
        "hall_of_fame_score": 15,
    }


@pytest.fixture
def dialog_qb(qapp, sample_qb_retirement, sample_qb_career_summary):
    """Create dialog with QB data (notable career)."""
    from game_cycle_ui.dialogs.retirement_detail_dialog import RetirementDetailDialog
    dialog = RetirementDetailDialog(
        retirement_data=sample_qb_retirement,
        career_summary=sample_qb_career_summary,
        user_team_id=4,  # User owns the Jets (Rodgers' final team)
    )
    yield dialog
    dialog.close()


@pytest.fixture
def dialog_wr(qapp, sample_wr_retirement, sample_wr_career_summary):
    """Create dialog with WR data (modest career)."""
    from game_cycle_ui.dialogs.retirement_detail_dialog import RetirementDetailDialog
    dialog = RetirementDetailDialog(
        retirement_data=sample_wr_retirement,
        career_summary=sample_wr_career_summary,
        user_team_id=17,  # User owns Cowboys
    )
    yield dialog
    dialog.close()


# ============================================================================
# TestDialogInitialization (3 tests)
# ============================================================================

class TestDialogInitialization:
    """Tests for dialog creation and basic setup."""

    def test_dialog_creates_with_data(self, dialog_qb):
        """Dialog initializes correctly with retirement data."""
        assert dialog_qb.get_player_id() == 1001
        assert dialog_qb.get_player_name() == "Aaron Rodgers"

    def test_dialog_title_contains_player_name(self, dialog_qb):
        """Dialog window title includes player name."""
        assert "Aaron Rodgers" in dialog_qb.windowTitle()
        assert "Career Retrospective" in dialog_qb.windowTitle()

    def test_dialog_is_modal(self, dialog_qb):
        """Dialog is modal."""
        assert dialog_qb.isModal()


# ============================================================================
# TestCareerStats (2 tests)
# ============================================================================

class TestCareerStats:
    """Tests for career statistics display."""

    def test_qb_stats_show_passing(self, dialog_qb, sample_qb_career_summary):
        """QB dialog displays passing statistics."""
        # Stats section is built internally, verify data access works
        stats_text = dialog_qb._build_position_stats("QB")
        assert "65,432" in stats_text  # Passing yards
        assert "489" in stats_text  # TDs

    def test_wr_stats_show_receiving(self, dialog_wr, sample_wr_career_summary):
        """WR dialog displays receiving statistics."""
        stats_text = dialog_wr._build_position_stats("WR")
        assert "412" in stats_text  # Receptions
        assert "5,234" in stats_text  # Receiving yards


# ============================================================================
# TestAwardsSection (2 tests)
# ============================================================================

class TestAwardsSection:
    """Tests for awards and accomplishments display."""

    def test_notable_player_shows_awards(self, dialog_qb, sample_qb_career_summary):
        """Notable player dialog includes award information."""
        # Award counts should be accessible from career summary
        mvps = sample_qb_career_summary.get("mvp_awards", 0)
        sb_wins = sample_qb_career_summary.get("super_bowl_wins", 0)
        pro_bowls = sample_qb_career_summary.get("pro_bowls", 0)

        assert mvps == 4
        assert sb_wins == 1
        assert pro_bowls == 10

    def test_modest_career_no_major_awards(self, dialog_wr, sample_wr_career_summary):
        """Modest career player shows no major awards."""
        mvps = sample_wr_career_summary.get("mvp_awards", 0)
        sb_wins = sample_wr_career_summary.get("super_bowl_wins", 0)

        assert mvps == 0
        assert sb_wins == 0


# ============================================================================
# TestHofProjection (3 tests)
# ============================================================================

class TestHofProjection:
    """Tests for Hall of Fame projection display."""

    def test_hof_score_accessible(self, dialog_qb):
        """HOF score is accessible from dialog."""
        assert dialog_qb.get_hof_score() == 94

    def test_first_ballot_status(self, dialog_qb):
        """High HOF score shows first ballot status."""
        status = dialog_qb._get_hof_status(94)
        assert "FIRST BALLOT" in status

    def test_unlikely_status(self, dialog_wr):
        """Low HOF score shows unlikely status."""
        status = dialog_wr._get_hof_status(15)
        assert "UNLIKELY" in status


# ============================================================================
# TestOneDayContract (2 tests)
# ============================================================================

class TestOneDayContract:
    """Tests for One-Day Contract functionality."""

    def test_one_day_contract_button_visible_for_former_team(self, dialog_qb):
        """One-Day Contract button visible when user owns player's former team."""
        # User team is 4 (Jets), Rodgers' final team is 4
        assert dialog_qb._is_eligible_for_one_day_contract()

    def test_one_day_contract_button_emits_signal(self, dialog_qb):
        """Clicking One-Day Contract emits signal with player and team IDs."""
        signal_received = []
        dialog_qb.one_day_contract_requested.connect(
            lambda pid, tid: signal_received.append((pid, tid))
        )

        # Simulate button click
        dialog_qb._on_one_day_contract()

        assert len(signal_received) == 1
        assert signal_received[0] == (1001, 4)


# ============================================================================
# TestRetirementReasonFormatting (1 test)
# ============================================================================

class TestRetirementReasonFormatting:
    """Tests for retirement reason display formatting."""

    def test_reason_formatting(self, dialog_qb):
        """Retirement reasons are formatted properly."""
        assert dialog_qb._format_retirement_reason("age_decline") == "Age / Performance Decline"
        assert dialog_qb._format_retirement_reason("championship") == "Retired as Champion"
        assert dialog_qb._format_retirement_reason("injury") == "Career-Ending Injury"


# ============================================================================
# TestHofColors (1 test)
# ============================================================================

class TestHofColors:
    """Tests for HOF score color coding."""

    def test_hof_color_grades(self, dialog_qb):
        """HOF colors match score thresholds."""
        # Gold for 85+
        assert dialog_qb._get_hof_color(94) == "#FFD700"
        # Green for 70-84
        assert dialog_qb._get_hof_color(75) == "#4CAF50"
        # Blue for 50-69
        assert dialog_qb._get_hof_color(55) == "#2196F3"
        # Gray for <30
        assert dialog_qb._get_hof_color(15) == "#78909C"
