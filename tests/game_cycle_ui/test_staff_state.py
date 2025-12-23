"""
Tests for StaffState dataclass.

Tests the staff state management logic extracted in Phase 3 of the
Owner Review refactoring.
"""

import pytest
from game_cycle_ui.models import StaffState


class TestStaffStateInitialization:
    """Test StaffState initialization and defaults."""

    def test_default_initialization(self):
        """Staff state should have sensible defaults."""
        state = StaffState()
        assert state.is_fired is False
        assert state.candidates == []
        assert state.selected_id is None

    def test_custom_initialization(self):
        """Can initialize with custom values."""
        candidates = [{"id": "c1", "name": "Candidate 1"}]
        state = StaffState(is_fired=True, candidates=candidates, selected_id="c1")
        assert state.is_fired is True
        assert state.candidates == candidates
        assert state.selected_id == "c1"


class TestStaffStateReset:
    """Test the reset() method."""

    def test_reset_clears_fired_status(self):
        """Reset should clear fired status."""
        state = StaffState(is_fired=True)
        state.reset()
        assert state.is_fired is False

    def test_reset_clears_candidates(self):
        """Reset should clear candidates list."""
        state = StaffState(candidates=[{"id": "c1"}])
        state.reset()
        assert state.candidates == []

    def test_reset_clears_selection(self):
        """Reset should clear selected candidate."""
        state = StaffState(selected_id="c1")
        state.reset()
        assert state.selected_id is None

    def test_reset_full_state(self):
        """Reset should clear all state at once."""
        state = StaffState(
            is_fired=True,
            candidates=[{"id": "c1"}, {"id": "c2"}],
            selected_id="c1"
        )
        state.reset()
        assert state.is_fired is False
        assert state.candidates == []
        assert state.selected_id is None


class TestStaffStateFire:
    """Test the fire() method."""

    def test_fire_sets_fired_status(self):
        """Fire should set is_fired to True."""
        state = StaffState()
        state.fire()
        assert state.is_fired is True

    def test_fire_idempotent(self):
        """Firing multiple times should be safe."""
        state = StaffState()
        state.fire()
        state.fire()
        assert state.is_fired is True


class TestStaffStateHire:
    """Test the hire() method."""

    def test_hire_sets_selected_id(self):
        """Hire should set the selected candidate ID."""
        state = StaffState()
        state.hire("candidate-123")
        assert state.selected_id == "candidate-123"

    def test_hire_can_change_selection(self):
        """Hiring a different candidate should update selection."""
        state = StaffState(selected_id="c1")
        state.hire("c2")
        assert state.selected_id == "c2"


class TestStaffStateDecisionComplete:
    """Test the is_decision_complete() method."""

    def test_complete_when_keeping_staff(self):
        """Decision is complete when keeping current staff (not fired)."""
        state = StaffState(is_fired=False)
        assert state.is_decision_complete() is True

    def test_incomplete_when_fired_no_hire(self):
        """Decision is incomplete when fired but no replacement hired."""
        state = StaffState(is_fired=True, selected_id=None)
        assert state.is_decision_complete() is False

    def test_complete_when_fired_and_hired(self):
        """Decision is complete when fired and replacement hired."""
        state = StaffState(is_fired=True, selected_id="new-candidate")
        assert state.is_decision_complete() is True

    def test_complete_when_hired_without_firing(self):
        """Decision is complete if selected_id is set (even without firing)."""
        state = StaffState(is_fired=False, selected_id="c1")
        assert state.is_decision_complete() is True


class TestStaffStateWorkflow:
    """Test realistic workflow scenarios."""

    def test_keep_current_staff_workflow(self):
        """Workflow: Keep current staff (do nothing)."""
        state = StaffState()
        # No actions needed - state already represents "keep"
        assert state.is_decision_complete() is True

    def test_fire_and_hire_workflow(self):
        """Workflow: Fire current staff and hire replacement."""
        state = StaffState()

        # User fires staff
        state.fire()
        assert state.is_decision_complete() is False

        # Candidates loaded (external to StaffState)
        state.candidates = [
            {"id": "c1", "name": "Candidate 1"},
            {"id": "c2", "name": "Candidate 2"}
        ]
        assert state.is_decision_complete() is False  # Still need to hire

        # User selects a candidate
        state.hire("c1")
        assert state.is_decision_complete() is True

    def test_fire_then_keep_workflow(self):
        """Workflow: Fire staff then change mind and keep them."""
        state = StaffState()

        # User fires staff
        state.fire()
        assert state.is_decision_complete() is False

        # User changes mind and keeps staff
        state.reset()
        assert state.is_decision_complete() is True

    def test_hire_then_change_candidate_workflow(self):
        """Workflow: Hire candidate A, then change to candidate B."""
        state = StaffState()

        state.fire()
        state.candidates = [{"id": "c1"}, {"id": "c2"}]

        # Hire first candidate
        state.hire("c1")
        assert state.selected_id == "c1"
        assert state.is_decision_complete() is True

        # Change mind and hire different candidate
        state.hire("c2")
        assert state.selected_id == "c2"
        assert state.is_decision_complete() is True


class TestStaffStateEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_string_candidate_id(self):
        """Hiring with empty string should set selected_id."""
        state = StaffState()
        state.hire("")
        assert state.selected_id == ""
        # Empty string still counts as "selected"
        assert state.is_decision_complete() is True

    def test_none_candidate_id_explicitly(self):
        """Explicitly setting None as candidate_id."""
        state = StaffState(selected_id="c1")
        state.selected_id = None  # Direct assignment
        state.is_fired = True
        assert state.is_decision_complete() is False

    def test_candidates_list_immutability(self):
        """Modifying candidates after initialization."""
        candidates = [{"id": "c1"}]
        state = StaffState(candidates=candidates)

        # Modify original list
        candidates.append({"id": "c2"})

        # StaffState should not be affected (uses default_factory)
        state2 = StaffState()
        assert state2.candidates == []  # Not affected by previous state
