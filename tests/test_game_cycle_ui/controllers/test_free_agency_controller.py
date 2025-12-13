"""
Unit tests for FreeAgencyUIController.

Part of Milestone 8: Free Agency Depth - Tollgate 4.

Tests controller with mocked backend following same pattern as FAWaveExecutor tests.
"""

import pytest
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass

from game_cycle_ui.controllers.free_agency_controller import FreeAgencyUIController


@dataclass
class MockStageResult:
    """Mock stage result returned by backend.execute_current_stage()."""
    stage: Mock
    games_played: list
    events_processed: list
    errors: list
    success: bool
    can_advance: bool


@pytest.fixture
def mock_backend():
    """Create mock backend with default behavior."""
    backend = Mock()

    # Default execute result
    mock_stage = Mock()
    mock_stage.display_name = "Free Agency"

    backend.execute_current_stage.return_value = MockStageResult(
        stage=mock_stage,
        games_played=[],
        events_processed=["FA action processed"],
        errors=[],
        success=True,
        can_advance=False
    )

    return backend


@pytest.fixture
def controller(mock_backend):
    """Create controller with mock backend."""
    return FreeAgencyUIController(
        backend=mock_backend,
        dynasty_id="test_dynasty",
        season=2025,
        user_team_id=1
    )


class TestConstructor:
    """Tests for constructor and initialization."""

    def test_stores_dependencies(self, mock_backend):
        """Constructor should store all dependencies."""
        controller = FreeAgencyUIController(
            backend=mock_backend,
            dynasty_id="test_dynasty",
            season=2025,
            user_team_id=1
        )

        assert controller._backend is mock_backend
        assert controller._dynasty_id == "test_dynasty"
        assert controller._season == 2025
        assert controller._user_team_id == 1

    def test_initial_wave_actions_empty(self, controller):
        """Initial wave actions should be empty."""
        actions = controller.get_wave_actions()

        assert actions["submit_offers"] == []
        assert actions["withdraw_offers"] == []

    def test_initial_wave_control_all_false(self, controller):
        """Initial wave control flags should all be False."""
        control = controller.get_wave_control()

        assert control["advance_day"] is False
        assert control["advance_wave"] is False
        assert control["enable_post_draft"] is False


class TestOfferHandling:
    """Tests for offer submission and withdrawal handlers."""

    def test_on_offer_submitted_adds_to_list(self, controller):
        """on_offer_submitted should add offer to pending list."""
        controller.on_offer_submitted(100, {"aav": 5_000_000, "years": 3})

        actions = controller.get_wave_actions()
        assert len(actions["submit_offers"]) == 1
        assert actions["submit_offers"][0]["player_id"] == 100

    def test_on_offer_submitted_builds_complete_dict(self, controller):
        """on_offer_submitted should build complete offer dict."""
        controller.on_offer_submitted(
            player_id=100,
            offer_data={
                "aav": 10_000_000,
                "years": 4,
                "guaranteed": 25_000_000,
                "signing_bonus": 5_000_000
            }
        )

        actions = controller.get_wave_actions()
        offer = actions["submit_offers"][0]

        assert offer["player_id"] == 100
        assert offer["aav"] == 10_000_000
        assert offer["years"] == 4
        assert offer["guaranteed"] == 25_000_000
        assert offer["signing_bonus"] == 5_000_000

    def test_multiple_offers_accumulate(self, controller):
        """Multiple offers should accumulate in pending list."""
        controller.on_offer_submitted(100, {"aav": 5_000_000})
        controller.on_offer_submitted(101, {"aav": 6_000_000})
        controller.on_offer_submitted(102, {"aav": 7_000_000})

        actions = controller.get_wave_actions()
        assert len(actions["submit_offers"]) == 3

    def test_on_offer_withdrawn_adds_to_list(self, controller):
        """on_offer_withdrawn should add offer_id to pending list."""
        controller.on_offer_withdrawn(456)

        actions = controller.get_wave_actions()
        assert 456 in actions["withdraw_offers"]

    def test_multiple_withdrawals_accumulate(self, controller):
        """Multiple withdrawals should accumulate in pending list."""
        controller.on_offer_withdrawn(1)
        controller.on_offer_withdrawn(2)
        controller.on_offer_withdrawn(3)

        actions = controller.get_wave_actions()
        assert len(actions["withdraw_offers"]) == 3


class TestWaveControl:
    """Tests for wave control handlers."""

    def test_on_process_day_sets_flag(self, controller):
        """on_process_day should set advance_day flag."""
        controller.on_process_day()

        control = controller.get_wave_control()
        assert control["advance_day"] is True
        assert control["advance_wave"] is False
        assert control["enable_post_draft"] is False

    def test_on_process_wave_sets_flag(self, controller):
        """on_process_wave should set advance_wave flag."""
        controller.on_process_wave()

        control = controller.get_wave_control()
        assert control["advance_day"] is False
        assert control["advance_wave"] is True
        assert control["enable_post_draft"] is False

    def test_on_enable_post_draft_sets_flag(self, controller):
        """on_enable_post_draft should set enable_post_draft flag."""
        controller.on_enable_post_draft()

        control = controller.get_wave_control()
        assert control["advance_day"] is False
        assert control["advance_wave"] is False
        assert control["enable_post_draft"] is True


class TestExecution:
    """Tests for build_context and execute methods."""

    def test_build_context_includes_wave_actions(self, controller):
        """build_context should include wave actions in context."""
        controller.on_offer_submitted(100, {"aav": 5_000_000})
        controller.on_offer_withdrawn(456)

        base_context = {"dynasty_id": "test", "season": 2025}
        context = controller.build_context(base_context)

        assert "fa_wave_actions" in context
        assert len(context["fa_wave_actions"]["submit_offers"]) == 1
        assert 456 in context["fa_wave_actions"]["withdraw_offers"]

    def test_build_context_includes_wave_control(self, controller):
        """build_context should include wave control in context."""
        controller.on_process_day()

        base_context = {"dynasty_id": "test", "season": 2025}
        context = controller.build_context(base_context)

        assert "wave_control" in context
        assert context["wave_control"]["advance_day"] is True

    def test_build_context_preserves_base_context(self, controller):
        """build_context should preserve original base context."""
        base_context = {
            "dynasty_id": "test",
            "season": 2025,
            "user_team_id": 1,
            "custom_key": "custom_value"
        }

        context = controller.build_context(base_context)

        assert context["dynasty_id"] == "test"
        assert context["season"] == 2025
        assert context["custom_key"] == "custom_value"

    def test_execute_calls_backend(self, controller, mock_backend):
        """execute should call backend.execute_current_stage."""
        base_context = {"dynasty_id": "test", "season": 2025}

        controller.execute(base_context)

        mock_backend.execute_current_stage.assert_called_once()

    def test_execute_clears_pending_after(self, controller, mock_backend):
        """execute should clear pending actions after completion."""
        controller.on_offer_submitted(100, {"aav": 5_000_000})
        controller.on_process_day()

        base_context = {"dynasty_id": "test", "season": 2025}
        controller.execute(base_context)

        # Should be cleared
        actions = controller.get_wave_actions()
        control = controller.get_wave_control()

        assert actions["submit_offers"] == []
        assert actions["withdraw_offers"] == []
        assert control["advance_day"] is False

    def test_execute_returns_result_dict(self, controller, mock_backend):
        """execute should return structured result dict."""
        base_context = {"dynasty_id": "test", "season": 2025}

        result = controller.execute(base_context)

        assert "stage_name" in result
        assert "events_processed" in result
        assert "success" in result
        assert "can_advance" in result
        assert result["stage_name"] == "Free Agency"
        assert result["success"] is True


class TestStateQueries:
    """Tests for state query methods."""

    def test_has_pending_actions_false_when_empty(self, controller):
        """has_pending_actions should return False when nothing pending."""
        assert controller.has_pending_actions() is False

    def test_has_pending_actions_true_with_offer(self, controller):
        """has_pending_actions should return True with pending offer."""
        controller.on_offer_submitted(100, {"aav": 5_000_000})

        assert controller.has_pending_actions() is True

    def test_has_pending_actions_true_with_withdrawal(self, controller):
        """has_pending_actions should return True with pending withdrawal."""
        controller.on_offer_withdrawn(456)

        assert controller.has_pending_actions() is True

    def test_has_pending_actions_true_with_control(self, controller):
        """has_pending_actions should return True with control flag set."""
        controller.on_process_day()

        assert controller.has_pending_actions() is True

    def test_get_wave_actions_returns_copy(self, controller):
        """get_wave_actions should return a copy, not original."""
        controller.on_offer_submitted(100, {"aav": 5_000_000})

        actions1 = controller.get_wave_actions()
        actions2 = controller.get_wave_actions()

        # Should be equal but not same object
        assert actions1 == actions2
        assert actions1 is not actions2
        assert actions1["submit_offers"] is not actions2["submit_offers"]

    def test_get_wave_control_returns_copy(self, controller):
        """get_wave_control should return a copy, not original."""
        controller.on_process_day()

        control1 = controller.get_wave_control()
        control2 = controller.get_wave_control()

        # Should be equal but not same object
        assert control1 == control2
        assert control1 is not control2


class TestClearPending:
    """Tests for clear_pending method."""

    def test_clear_pending_resets_offers(self, controller):
        """clear_pending should reset offer lists."""
        controller.on_offer_submitted(100, {"aav": 5_000_000})
        controller.on_offer_withdrawn(456)

        controller.clear_pending()

        actions = controller.get_wave_actions()
        assert actions["submit_offers"] == []
        assert actions["withdraw_offers"] == []

    def test_clear_pending_resets_control(self, controller):
        """clear_pending should reset control flags."""
        controller.on_process_day()
        controller.on_process_wave()

        controller.clear_pending()

        control = controller.get_wave_control()
        assert control["advance_day"] is False
        assert control["advance_wave"] is False
        assert control["enable_post_draft"] is False


class TestViewConnection:
    """Tests for view connection."""

    def test_connect_view_stores_reference(self, controller):
        """connect_view should store view reference."""
        mock_view = Mock()

        controller.connect_view(mock_view)

        assert controller._view is mock_view

    def test_connect_view_connects_available_signals(self, controller):
        """connect_view should connect signals that exist."""
        mock_view = Mock()
        mock_view.offer_submitted = Mock()
        mock_view.offer_withdrawn = Mock()
        mock_view.process_day_requested = Mock()
        mock_view.process_wave_requested = Mock()

        controller.connect_view(mock_view)

        # Should have called connect on each signal
        mock_view.offer_submitted.connect.assert_called_once()
        mock_view.offer_withdrawn.connect.assert_called_once()
        mock_view.process_day_requested.connect.assert_called_once()
        mock_view.process_wave_requested.connect.assert_called_once()

    def test_connect_view_handles_missing_signals(self, controller):
        """connect_view should handle views without wave signals."""
        mock_view = Mock(spec=[])  # No signals

        # Should not raise
        controller.connect_view(mock_view)

        assert controller._view is mock_view


class TestRefreshView:
    """Tests for refresh_view method."""

    def test_refresh_view_does_nothing_without_view(self, controller):
        """refresh_view should do nothing if no view connected."""
        # Should not raise
        controller.refresh_view({"wave_state": {"wave": 1}})

    def test_refresh_view_calls_set_wave_info(self, controller):
        """refresh_view should call set_wave_info if view supports it."""
        mock_view = Mock()
        mock_view.set_wave_info = Mock()
        controller._view = mock_view

        preview = {
            "wave_state": {
                "wave": 1,
                "wave_name": "Wave 1 - Elite",
                "current_day": 2,
                "days_in_wave": 3,
            }
        }

        controller.refresh_view(preview)

        mock_view.set_wave_info.assert_called_once_with(
            wave=1,
            wave_name="Wave 1 - Elite",
            day=2,
            days_total=3
        )

    def test_refresh_view_calls_set_free_agents(self, controller):
        """refresh_view should call set_free_agents if view supports it."""
        mock_view = Mock()
        mock_view.set_free_agents = Mock()
        controller._view = mock_view

        preview = {
            "wave_state": {},
            "free_agents": [{"player_id": 1}, {"player_id": 2}]
        }

        controller.refresh_view(preview)

        mock_view.set_free_agents.assert_called_once()