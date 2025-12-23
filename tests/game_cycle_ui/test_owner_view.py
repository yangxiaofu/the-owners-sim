"""
Tests for OwnerView UI component.

Part of Milestone 13: Owner Review, Tollgate 5.
Tests the 2-step wizard owner review UI including staff management, directives, and flow guidance.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import MagicMock

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
def view(qapp):
    """Create fresh OwnerView instance."""
    from game_cycle_ui.views.owner_view import OwnerView
    view = OwnerView()
    yield view
    view.close()


@pytest.fixture
def sample_staff() -> Dict[str, Any]:
    """Sample staff data for tests using MagicMock objects."""
    gm = MagicMock()
    gm.staff_id = "gm-uuid-1"
    gm.name = "John Smith"
    gm.archetype_key = "balanced"
    gm.history = "Experienced GM with a balanced approach to roster building."
    gm.hire_season = 2024

    hc = MagicMock()
    hc.staff_id = "hc-uuid-1"
    hc.name = "Jane Doe"
    hc.archetype_key = "aggressive"
    hc.history = "Former coordinator known for aggressive play calling."
    hc.hire_season = 2023

    return {"gm": gm, "hc": hc}


@pytest.fixture
def sample_staff_dict() -> Dict[str, Any]:
    """Sample staff data as dicts (for update_staff_info)."""
    return {
        "gm": {
            "staff_id": "gm-uuid-1",
            "name": "John Smith",
            "archetype_key": "balanced",
            "history": "Experienced GM with a balanced approach to roster building.",
            "hire_season": 2024
        },
        "hc": {
            "staff_id": "hc-uuid-1",
            "name": "Jane Doe",
            "archetype_key": "aggressive",
            "history": "Former coordinator known for aggressive play calling.",
            "hire_season": 2023
        }
    }


@pytest.fixture
def sample_candidates() -> List[Dict[str, Any]]:
    """Sample GM/HC candidates."""
    return [
        {
            "staff_id": "c1-uuid",
            "name": "Candidate One",
            "archetype_key": "win_now",
            "history": "Known for aggressive roster moves to win immediately.",
            "custom_traits": {"risk_tolerance": 0.8}
        },
        {
            "staff_id": "c2-uuid",
            "name": "Candidate Two",
            "archetype_key": "rebuilder",
            "history": "Patient approach focusing on draft picks and development.",
            "custom_traits": {"draft_pick_value": 0.9}
        },
        {
            "staff_id": "c3-uuid",
            "name": "Candidate Three",
            "archetype_key": "balanced",
            "history": "Versatile executive with varied background.",
            "custom_traits": {"cap_management": 0.7}
        },
    ]


@pytest.fixture
def sample_summary() -> Dict[str, Any]:
    """Sample season summary."""
    return {
        "season": 2025,
        "wins": 10,
        "losses": 7,
        "target_wins": 8
    }


@pytest.fixture
def sample_directives() -> Dict[str, Any]:
    """Sample owner directives."""
    return {
        "target_wins": 12,
        "priority_positions": ["QB", "EDGE", "CB"],
        "draft_strategy": "bpa",
        "fa_philosophy": "aggressive",
        "fa_wishlist": ["Player A", "Player B"],
        "draft_wishlist": ["Prospect X", "Prospect Y"],
        "max_contract_years": 4,
        "max_guaranteed_percent": 0.6
    }


# ============================================================================
# TestWizardStructure (3 tests)
# ============================================================================

class TestWizardStructure:
    """Tests for 2-step wizard structure."""

    def test_has_two_steps(self, view):
        """OwnerView has exactly 2 wizard steps."""
        assert view._stacked_widget.count() == 2

    def test_navigation_buttons_exist(self, view):
        """Navigation buttons (Back, Next, Continue) exist."""
        assert hasattr(view, '_back_btn')
        assert hasattr(view, '_next_btn')
        assert hasattr(view, '_continue_btn')

    def test_default_step_is_review(self, view):
        """Default step is Season Review (index 0)."""
        assert view._stacked_widget.currentIndex() == 0


# ============================================================================
# TestSeasonSummary (4 tests)
# ============================================================================

class TestSeasonSummary:
    """Tests for Season Summary tab."""

    def test_set_season_summary_updates_state(self, view, sample_summary):
        """set_season_summary populates internal state."""
        view.set_season_summary(sample_summary)
        assert view._season_summary == sample_summary

    def test_summary_shows_wins_losses(self, view, sample_summary):
        """Summary displays wins and losses correctly."""
        view.set_season_summary(sample_summary)
        assert view._record_label.text() == "10 - 7"

    def test_summary_shows_target_wins(self, view, sample_summary):
        """Summary displays target wins from directives."""
        view.set_season_summary(sample_summary)
        assert view._target_label.text() == "8 wins"

    def test_summary_shows_season_year(self, view, sample_summary):
        """Summary displays season year correctly."""
        view.set_season_summary(sample_summary)
        assert view._season_label.text() == "2025"

    def test_summary_expectations_met(self, view, sample_summary):
        """Expectations Met shown when wins >= target."""
        view.set_season_summary(sample_summary)  # 10 wins vs 8 target
        assert view._expectations_label.text() == "Met"

    def test_summary_expectations_not_met(self, view):
        """Expectations Not Met shown when wins < target."""
        summary = {"season": 2025, "wins": 5, "losses": 12, "target_wins": 10}
        view.set_season_summary(summary)
        assert view._expectations_label.text() == "Not Met"


# ============================================================================
# TestStaffDisplay (4 tests)
# ============================================================================

class TestStaffDisplay:
    """Tests for staff display and data loading."""

    def test_set_current_staff_updates_state(self, view, sample_staff_dict):
        """set_current_staff populates internal staff state."""
        view.set_current_staff(sample_staff_dict)
        assert view._current_staff == sample_staff_dict

    def test_staff_resets_firing_state(self, view, sample_staff_dict):
        """set_current_staff resets firing flags."""
        view._staff_state["gm"].is_fired = True
        view._staff_state["hc"].is_fired = True
        view.set_current_staff(sample_staff_dict)
        assert view._staff_state["gm"].is_fired is False
        assert view._staff_state["hc"].is_fired is False

    def test_staff_clears_candidates(self, view, sample_staff_dict, sample_candidates):
        """set_current_staff clears any existing candidates."""
        view._staff_state["gm"].candidates = sample_candidates
        view._staff_state["hc"].candidates = sample_candidates
        view.set_current_staff(sample_staff_dict)
        assert view._staff_state["gm"].candidates == []
        assert view._staff_state["hc"].candidates == []

    def test_staff_clears_selection(self, view, sample_staff_dict):
        """set_current_staff clears selected IDs."""
        view._staff_state["gm"].selected_id = "some-id"
        view._staff_state["hc"].selected_id = "other-id"
        view.set_current_staff(sample_staff_dict)
        assert view._staff_state["gm"].selected_id is None
        assert view._staff_state["hc"].selected_id is None


# ============================================================================
# TestFireGMFlow (4 tests)
# ============================================================================

class TestFireGMFlow:
    """Tests for GM fire/hire workflow."""

    def test_fire_gm_emits_signal(self, view, sample_staff_dict):
        """Firing GM emits gm_fired signal."""
        view.set_current_staff(sample_staff_dict)

        signal_received = []
        view.gm_fired.connect(lambda: signal_received.append(True))

        view._on_fire_staff("gm")

        assert len(signal_received) == 1
        assert view._staff_state["gm"].is_fired is True

    def test_set_gm_candidates_populates_list(self, view, sample_candidates):
        """set_gm_candidates populates internal candidates list."""
        view.set_gm_candidates(sample_candidates)
        assert len(view._staff_state["gm"].candidates) == 3
        assert view._staff_state["gm"].candidates[0]["name"] == "Candidate One"

    def test_hire_gm_emits_signal_with_id(self, view, sample_staff_dict, sample_candidates):
        """Hiring GM emits gm_hired signal with candidate_id."""
        view.set_current_staff(sample_staff_dict)
        view._staff_state["gm"].is_fired = True
        view.set_gm_candidates(sample_candidates)

        signal_received = []
        view.gm_hired.connect(lambda cid: signal_received.append(cid))

        view._staff_state["gm"].hire("c1-uuid")

        assert len(signal_received) == 1
        assert signal_received[0] == "c1-uuid"
        assert view._staff_state["gm"].selected_id == "c1-uuid"

    def test_keep_gm_resets_state(self, view, sample_staff_dict, sample_candidates):
        """Keeping GM clears firing state and candidates."""
        view.set_current_staff(sample_staff_dict)
        view._staff_state["gm"].is_fired = True
        view.set_gm_candidates(sample_candidates)

        view._on_keep_staff("gm")

        assert view._staff_state["gm"].is_fired is False
        assert view._staff_state["gm"].candidates == []
        assert view._staff_state["gm"].selected_id is None


# ============================================================================
# TestFireHCFlow (3 tests)
# ============================================================================

class TestFireHCFlow:
    """Tests for HC fire/hire workflow."""

    def test_fire_hc_emits_signal(self, view, sample_staff_dict):
        """Firing HC emits hc_fired signal."""
        view.set_current_staff(sample_staff_dict)

        signal_received = []
        view.hc_fired.connect(lambda: signal_received.append(True))

        view._on_fire_staff("hc")

        assert len(signal_received) == 1
        assert view._staff_state["hc"].is_fired is True

    def test_set_hc_candidates_populates_list(self, view, sample_candidates):
        """set_hc_candidates populates internal candidates list."""
        view.set_hc_candidates(sample_candidates)
        assert len(view._staff_state["hc"].candidates) == 3
        assert view._staff_state["hc"].candidates[1]["archetype_key"] == "rebuilder"

    def test_hire_hc_emits_signal_with_id(self, view, sample_staff_dict, sample_candidates):
        """Hiring HC emits hc_hired signal with candidate_id."""
        view.set_current_staff(sample_staff_dict)
        view._staff_state["hc"].is_fired = True
        view.set_hc_candidates(sample_candidates)

        signal_received = []
        view.hc_hired.connect(lambda cid: signal_received.append(cid))

        view._staff_state["hc"].hire("c2-uuid")

        assert len(signal_received) == 1
        assert signal_received[0] == "c2-uuid"
        assert view._staff_state["hc"].selected_id == "c2-uuid"


# ============================================================================
# TestStrategicDirection (5 tests)
# ============================================================================

class TestStrategicDirection:
    """Tests for Strategic Direction tab."""

    def test_set_directives_populates_win_target(self, view, sample_directives):
        """set_directives sets win target spinbox."""
        view.set_directives(sample_directives)
        assert view._win_target_spin.value() == 12

    def test_set_directives_populates_draft_strategy(self, view, sample_directives):
        """set_directives sets draft strategy combo."""
        view.set_directives(sample_directives)
        assert view._draft_strategy_combo.currentData() == "bpa"

    def test_set_directives_populates_fa_philosophy(self, view, sample_directives):
        """set_directives sets FA philosophy combo."""
        view.set_directives(sample_directives)
        assert view._fa_philosophy_combo.currentData() == "aggressive"

    def test_save_directives_emits_signal(self, view):
        """Save Directives button emits directives_saved signal with data."""
        view._win_target_spin.setValue(11)

        signal_received = []
        view.directives_saved.connect(lambda d: signal_received.append(d))

        view._on_save_directives()

        assert len(signal_received) == 1
        assert "target_wins" in signal_received[0]
        assert signal_received[0]["target_wins"] == 11
        assert view._directives_saved is True

    def test_win_target_range_0_to_17(self, view):
        """Win target spinner is constrained to 0-17."""
        assert view._win_target_spin.minimum() == 0
        assert view._win_target_spin.maximum() == 17


# ============================================================================
# TestFlowGuidance (5 tests)
# ============================================================================

class TestFlowGuidance:
    """Tests for flow guidance and completion tracking."""

    def test_continue_button_initially_disabled(self, view):
        """Continue button is disabled before all steps complete."""
        assert not view._continue_btn.isEnabled()

    def test_summary_reviewed_on_next(self, view, sample_summary, sample_staff_dict):
        """Advancing from Step 1 to Step 2 marks summary as reviewed."""
        view.set_season_summary(sample_summary)
        view.set_current_staff(sample_staff_dict)

        # Initially not reviewed
        assert view._summary_reviewed is False

        # Click Next to advance to Step 2
        view._on_next_clicked()

        # Should mark as reviewed and advance to Step 2
        assert view._summary_reviewed is True
        assert view._stacked_widget.currentIndex() == 1

    def test_staff_decisions_complete_when_keeping(self, view, sample_staff_dict):
        """Staff decisions complete when keeping both GM and HC."""
        view.set_current_staff(sample_staff_dict)
        # Not fired = keeping
        assert view._staff_state["gm"].is_fired is False
        assert view._staff_state["hc"].is_fired is False
        assert view._check_staff_decisions_complete() is True

    def test_staff_decisions_incomplete_when_gm_fired_not_hired(self, view, sample_staff_dict, sample_candidates):
        """Staff decisions incomplete when GM fired but not yet hired."""
        view.set_current_staff(sample_staff_dict)
        view._staff_state["gm"].is_fired = True
        view.set_gm_candidates(sample_candidates)

        assert view._check_staff_decisions_complete() is False

    def test_continue_enabled_after_all_steps(self, view, sample_staff_dict, sample_summary):
        """Continue button enabled after all steps complete."""
        view.set_season_summary(sample_summary)
        view.set_current_staff(sample_staff_dict)

        # Complete all steps
        view._summary_reviewed = True
        view._staff_decisions_complete = True
        view._directives_saved = True
        view._update_flow_guidance()

        assert view._continue_btn.isEnabled()

    def test_continue_emits_signal(self, view, sample_staff_dict, sample_summary):
        """Continue button emits continue_clicked signal."""
        view.set_season_summary(sample_summary)
        view.set_current_staff(sample_staff_dict)

        # Complete all steps
        view._summary_reviewed = True
        view._staff_decisions_complete = True
        view._directives_saved = True
        view._update_flow_guidance()

        signal_received = []
        view.continue_clicked.connect(lambda: signal_received.append(True))

        view._continue_btn.click()

        assert len(signal_received) == 1


# ============================================================================
# TestRefresh (3 tests)
# ============================================================================

class TestRefresh:
    """Tests for refresh/reset functionality."""

    def test_refresh_clears_firing_state(self, view, sample_staff_dict, sample_candidates):
        """refresh() resets firing state."""
        view.set_current_staff(sample_staff_dict)
        view._staff_state["gm"].is_fired = True
        view._staff_state["hc"].is_fired = True
        view.set_gm_candidates(sample_candidates)
        view.set_hc_candidates(sample_candidates)

        view.refresh()

        assert view._staff_state["gm"].is_fired is False
        assert view._staff_state["hc"].is_fired is False
        assert view._staff_state["gm"].candidates == []
        assert view._staff_state["hc"].candidates == []

    def test_refresh_clears_completion_state(self, view):
        """refresh() resets summary/directives completion tracking."""
        view._summary_reviewed = True
        view._directives_saved = True

        view.refresh()

        # Summary and directives should be reset
        assert view._summary_reviewed is False
        assert view._directives_saved is False
        # Note: _staff_decisions_complete is recalculated by _update_flow_guidance()
        # and defaults to True when neither GM nor HC is fired (keeping both)

    def test_refresh_resets_to_step_1(self, view):
        """refresh() switches back to Step 1 (Season Review)."""
        view._stacked_widget.setCurrentIndex(1)  # Go to Step 2
        view.refresh()
        assert view._stacked_widget.currentIndex() == 0


# ============================================================================
# Additional edge case tests (3 tests)
# ============================================================================

class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_empty_directives_handled(self, view):
        """set_directives with None doesn't crash."""
        view.set_directives(None)
        # Should use defaults
        assert view._win_target_spin.value() == 8  # Default

    def test_empty_summary_handled(self, view):
        """set_season_summary with missing fields handled."""
        partial_summary = {"season": 2025}
        view.set_season_summary(partial_summary)
        # Should show dashes for missing data
        assert view._record_label.text() == "-- - --"

    def test_priority_positions_collected_correctly(self, view):
        """Save directives collects priority positions without duplicates."""
        # Set some positions
        view._priority_combos[0].setCurrentText("QB")
        view._priority_combos[1].setCurrentText("QB")  # Duplicate
        view._priority_combos[2].setCurrentText("EDGE")

        signal_received = []
        view.directives_saved.connect(lambda d: signal_received.append(d))

        view._on_save_directives()

        positions = signal_received[0]["priority_positions"]
        assert "QB" in positions
        assert "EDGE" in positions
        assert positions.count("QB") == 1  # No duplicates


# ============================================================================
# Integration tests (2 tests)
# ============================================================================

class TestOwnerViewIntegration:
    """Integration tests for OwnerView."""

    def test_full_workflow_gm_fire_hire(self, view, sample_staff_dict, sample_candidates):
        """Complete GM fire/hire workflow updates state correctly."""
        # Setup
        view.set_current_staff(sample_staff_dict)

        # Fire GM
        view._on_fire_staff("gm")
        assert view._staff_state["gm"].is_fired is True

        # Receive candidates
        view.set_gm_candidates(sample_candidates)
        assert len(view._staff_state["gm"].candidates) == 3

        # Hire new GM
        view._staff_state["gm"].hire("c1-uuid")
        assert view._staff_state["gm"].selected_id == "c1-uuid"

        # Staff decisions should now be complete
        assert view._check_staff_decisions_complete() is True

    def test_navigation_buttons_work(self, view, sample_summary, sample_staff_dict):
        """Next and Back buttons navigate between wizard steps."""
        view.set_season_summary(sample_summary)
        view.set_current_staff(sample_staff_dict)

        # Start at Step 1
        assert view._stacked_widget.currentIndex() == 0

        # Next should advance to Step 2
        view._on_next_clicked()
        assert view._stacked_widget.currentIndex() == 1

        # Back should return to Step 1
        view._on_back_clicked()
        assert view._stacked_widget.currentIndex() == 0
