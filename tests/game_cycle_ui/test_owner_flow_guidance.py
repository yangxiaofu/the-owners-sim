"""
Tests for OwnerFlowGuidance and FlowState.

Tests the flow guidance logic extracted in Phase 4 of the
Owner Review refactoring.
"""

import pytest

# Skip import if PySide6 not available (CI/headless environments)
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QTabWidget
from game_cycle_ui.widgets.owner_flow_guidance import FlowState, OwnerFlowGuidance


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_widgets(qapp):
    """Create mock Qt widgets for flow guidance."""
    banner = QFrame()
    banner.setObjectName("action_banner")
    banner_icon = QLabel()
    banner_text = QLabel()
    action_btn = QPushButton()
    tab_widget = QTabWidget()
    tab_widget.addTab(QLabel("Tab 1"), "Season Review")
    tab_widget.addTab(QLabel("Tab 2"), "Strategic Direction")

    return {
        "banner": banner,
        "banner_icon": banner_icon,
        "banner_text": banner_text,
        "action_btn": action_btn,
        "tab_widget": tab_widget
    }


@pytest.fixture
def flow_guidance(mock_widgets):
    """Create OwnerFlowGuidance instance with mock widgets."""
    return OwnerFlowGuidance(
        banner=mock_widgets["banner"],
        banner_icon=mock_widgets["banner_icon"],
        banner_text=mock_widgets["banner_text"],
        action_btn=mock_widgets["action_btn"],
        tab_widget=mock_widgets["tab_widget"]
    )


class TestFlowStateInitialization:
    """Test FlowState dataclass initialization."""

    def test_default_initialization(self):
        """FlowState should have sensible defaults."""
        state = FlowState()
        assert state.summary_reviewed is False
        assert state.staff_decisions_complete is False
        assert state.directives_saved is False
        assert state.gm_fired_not_hired is False
        assert state.hc_fired_not_hired is False

    def test_custom_initialization(self):
        """Can initialize with custom values."""
        state = FlowState(
            summary_reviewed=True,
            staff_decisions_complete=True,
            directives_saved=False,
            gm_fired_not_hired=True
        )
        assert state.summary_reviewed is True
        assert state.staff_decisions_complete is True
        assert state.directives_saved is False
        assert state.gm_fired_not_hired is True


class TestFlowStateIsComplete:
    """Test FlowState.is_complete() method."""

    def test_incomplete_initially(self):
        """Fresh state should not be complete."""
        state = FlowState()
        assert state.is_complete() is False

    def test_complete_when_all_true(self):
        """State is complete when all three steps are done."""
        state = FlowState(
            summary_reviewed=True,
            staff_decisions_complete=True,
            directives_saved=True
        )
        assert state.is_complete() is True

    def test_incomplete_with_summary_only(self):
        """Not complete with just summary."""
        state = FlowState(summary_reviewed=True)
        assert state.is_complete() is False

    def test_incomplete_with_two_steps(self):
        """Not complete with only two steps."""
        state = FlowState(
            summary_reviewed=True,
            staff_decisions_complete=True
        )
        assert state.is_complete() is False


class TestFlowStateCurrentStep:
    """Test FlowState.current_step() method."""

    def test_step_1_when_nothing_done(self):
        """Should be step 1 when nothing is complete."""
        state = FlowState()
        assert state.current_step() == 1

    def test_step_2_when_summary_done(self):
        """Should be step 2 when summary is reviewed."""
        state = FlowState(summary_reviewed=True)
        assert state.current_step() == 2

    def test_step_3_when_summary_and_staff_done(self):
        """Should be step 3 when summary and staff are done."""
        state = FlowState(
            summary_reviewed=True,
            staff_decisions_complete=True
        )
        assert state.current_step() == 3

    def test_step_4_when_all_done(self):
        """Should be step 4 when all steps complete."""
        state = FlowState(
            summary_reviewed=True,
            staff_decisions_complete=True,
            directives_saved=True
        )
        assert state.current_step() == 4


class TestOwnerFlowGuidanceInitialization:
    """Test OwnerFlowGuidance initialization."""

    def test_stores_widget_references(self, flow_guidance, mock_widgets):
        """Should store references to all provided widgets."""
        assert flow_guidance.banner is mock_widgets["banner"]
        assert flow_guidance.banner_icon is mock_widgets["banner_icon"]
        assert flow_guidance.banner_text is mock_widgets["banner_text"]
        assert flow_guidance.action_btn is mock_widgets["action_btn"]
        assert flow_guidance.tab_widget is mock_widgets["tab_widget"]


class TestOwnerFlowGuidanceUpdate:
    """Test OwnerFlowGuidance.update() method."""

    def test_updates_banner_for_step_1(self, flow_guidance, mock_widgets):
        """Should show step 1 banner when nothing is complete."""
        state = FlowState()
        flow_guidance.update(state)

        assert "1" in mock_widgets["banner_icon"].text()
        assert "Step 1" in mock_widgets["banner_text"].text()
        assert "View Summary" in mock_widgets["action_btn"].text()

    def test_updates_banner_for_step_2(self, flow_guidance, mock_widgets):
        """Should show step 2 banner when summary is reviewed."""
        state = FlowState(summary_reviewed=True)
        flow_guidance.update(state)

        assert "2" in mock_widgets["banner_icon"].text()
        assert "Step 2" in mock_widgets["banner_text"].text()
        assert "Staff Decisions" in mock_widgets["action_btn"].text()

    def test_updates_banner_for_step_3(self, flow_guidance, mock_widgets):
        """Should show step 3 banner when summary and staff are done."""
        state = FlowState(
            summary_reviewed=True,
            staff_decisions_complete=True
        )
        flow_guidance.update(state)

        assert "3" in mock_widgets["banner_icon"].text()
        assert "Step 3" in mock_widgets["banner_text"].text()
        assert "Strategic Direction" in mock_widgets["action_btn"].text()

    def test_updates_banner_for_complete(self, flow_guidance, mock_widgets):
        """Should show completion banner when all steps done."""
        state = FlowState(
            summary_reviewed=True,
            staff_decisions_complete=True,
            directives_saved=True
        )
        flow_guidance.update(state)

        assert "✓" in mock_widgets["banner_icon"].text()
        assert "complete" in mock_widgets["banner_text"].text().lower()
        assert "Continue" in mock_widgets["action_btn"].text()

    def test_updates_tab_titles_with_checkmarks(self, flow_guidance, mock_widgets):
        """Should add checkmarks to completed tabs."""
        state = FlowState(
            summary_reviewed=True,
            staff_decisions_complete=False,
            directives_saved=False
        )
        flow_guidance.update(state)

        # First tab should have checkmark
        assert "✓" in mock_widgets["tab_widget"].tabText(0)

    def test_staff_tab_alert_when_gm_fired_not_hired(self, flow_guidance, mock_widgets):
        """Should show alert on staff tab when GM fired but not hired."""
        state = FlowState(
            summary_reviewed=True,
            staff_decisions_complete=False,
            gm_fired_not_hired=True
        )
        flow_guidance.update(state)

        # Banner should mention GM replacement needed
        assert "GM" in mock_widgets["banner_text"].text()
        assert "replacement" in mock_widgets["banner_text"].text().lower()


class TestOwnerFlowGuidanceWorkflow:
    """Test realistic workflow scenarios."""

    def test_progression_through_all_steps(self, flow_guidance, mock_widgets):
        """Test progression from step 1 to completion."""
        # Step 1
        state = FlowState()
        flow_guidance.update(state)
        assert "Step 1" in mock_widgets["banner_text"].text()

        # Step 2
        state.summary_reviewed = True
        flow_guidance.update(state)
        assert "Step 2" in mock_widgets["banner_text"].text()

        # Step 3
        state.staff_decisions_complete = True
        flow_guidance.update(state)
        assert "Step 3" in mock_widgets["banner_text"].text()

        # Complete
        state.directives_saved = True
        flow_guidance.update(state)
        assert "complete" in mock_widgets["banner_text"].text().lower()

    def test_banner_reflects_blocking_staff_decision(self, flow_guidance, mock_widgets):
        """Banner should reflect when staff decision is blocking progress."""
        state = FlowState(
            summary_reviewed=True,
            staff_decisions_complete=False,
            hc_fired_not_hired=True
        )
        flow_guidance.update(state)

        banner_text = mock_widgets["banner_text"].text()
        assert "Head Coach" in banner_text or "HC" in banner_text
        assert "select a replacement" in banner_text.lower()


class TestFlowStateEdgeCases:
    """Test edge cases in flow state logic."""

    def test_staff_flags_dont_affect_completion(self):
        """Staff-specific flags (gm_fired_not_hired) don't affect is_complete."""
        state = FlowState(
            summary_reviewed=True,
            staff_decisions_complete=True,
            directives_saved=True,
            gm_fired_not_hired=True  # This shouldn't matter
        )
        assert state.is_complete() is True

    def test_current_step_ignores_staff_flags(self):
        """current_step() only looks at the three main flags."""
        state1 = FlowState(
            summary_reviewed=True,
            gm_fired_not_hired=True
        )
        state2 = FlowState(
            summary_reviewed=True,
            gm_fired_not_hired=False
        )
        assert state1.current_step() == state2.current_step() == 2
