"""
Tests for FAWaveExecutor - Orchestrator for wave-based free agency.

Part of Milestone 8: Free Agency Depth - Tollgate 3.

Tests focus on:
- Constructor/factory pattern
- User action methods (submit/withdraw offers)
- AI turn processing
- Wave control (advance day/wave)
- Full execute() method
"""

import pytest
from unittest.mock import Mock, patch

from src.game_cycle.services.fa_wave_executor import (
    FAWaveExecutor,
    OfferOutcome,
    OfferResult,
    SigningResult,
    WaveExecutionResult,
)


@pytest.fixture
def mock_wave_service():
    """Create a mock FAWaveService."""
    service = Mock()

    # Default wave state
    service.get_wave_state.return_value = {
        "current_wave": 1,
        "wave_name": "Wave 1 - Elite",
        "current_day": 1,
        "days_in_wave": 3,
        "signing_allowed": True,
        "wave_complete": False,
    }

    # Default wave summary
    service.get_wave_summary.return_value = {
        "current_wave": 1,
        "wave_name": "Wave 1 - Elite",
        "current_day": 1,
        "days_in_wave": 3,
        "pending_offers": 5,
    }

    # Default is_fa_complete
    service.is_fa_complete.return_value = False

    return service


@pytest.fixture
def executor(mock_wave_service):
    """Create executor with mock service."""
    return FAWaveExecutor(mock_wave_service)


class TestConstructorFactory:
    """Tests for constructor and factory method."""

    def test_constructor_accepts_mock_service(self, mock_wave_service):
        """Constructor should accept any object with FAWaveService interface."""
        executor = FAWaveExecutor(mock_wave_service)
        assert executor._wave_service is mock_wave_service

    @patch("src.game_cycle.services.fa_wave_service.FAWaveService")
    def test_create_factory_builds_executor(self, mock_fa_wave_service_class):
        """Factory method should create FAWaveService and wrap it."""
        mock_instance = Mock()
        mock_fa_wave_service_class.return_value = mock_instance

        executor = FAWaveExecutor.create("test.db", "dynasty_1", 2025)

        mock_fa_wave_service_class.assert_called_once_with("test.db", "dynasty_1", 2025)
        assert executor._wave_service is mock_instance


class TestSubmitOffer:
    """Tests for offer submission."""

    def test_submit_offer_returns_submitted_result(self, executor, mock_wave_service):
        """Successful offer submission should return SUBMITTED outcome."""
        mock_wave_service.submit_offer.return_value = {
            "success": True,
            "offer_id": 123,
        }

        result = executor.submit_offer(
            player_id=100,
            team_id=1,
            aav=10_000_000,
            years=3,
            guaranteed=20_000_000,
            signing_bonus=5_000_000,
        )

        assert result.player_id == 100
        assert result.outcome == OfferOutcome.SUBMITTED
        assert result.offer_id == 123
        assert result.error is None

        mock_wave_service.submit_offer.assert_called_once_with(
            player_id=100,
            team_id=1,
            aav=10_000_000,
            years=3,
            guaranteed=20_000_000,
            signing_bonus=5_000_000,
        )

    def test_submit_offer_returns_duplicate_result(self, executor, mock_wave_service):
        """Duplicate offer error should return DUPLICATE outcome."""
        mock_wave_service.submit_offer.return_value = {
            "success": False,
            "error": "Already have pending offer for this player",
        }

        result = executor.submit_offer(
            player_id=100, team_id=1, aav=10_000_000, years=3, guaranteed=20_000_000
        )

        assert result.outcome == OfferOutcome.DUPLICATE
        assert "already" in result.error.lower()

    def test_submit_offer_returns_cap_exceeded_result(self, executor, mock_wave_service):
        """Cap space error should return CAP_EXCEEDED outcome."""
        mock_wave_service.submit_offer.return_value = {
            "success": False,
            "error": "Insufficient cap space: $5,000,000 available",
        }

        result = executor.submit_offer(
            player_id=100, team_id=1, aav=10_000_000, years=3, guaranteed=20_000_000
        )

        assert result.outcome == OfferOutcome.CAP_EXCEEDED
        assert "cap" in result.error.lower()

    def test_submit_offer_returns_not_allowed_result(self, executor, mock_wave_service):
        """Generic error should return NOT_ALLOWED outcome."""
        mock_wave_service.submit_offer.return_value = {
            "success": False,
            "error": "Signing not allowed in Legal Tampering",
        }

        result = executor.submit_offer(
            player_id=100, team_id=1, aav=10_000_000, years=3, guaranteed=20_000_000
        )

        assert result.outcome == OfferOutcome.NOT_ALLOWED


class TestWithdrawOffer:
    """Tests for offer withdrawal."""

    def test_withdraw_offer_returns_success(self, executor, mock_wave_service):
        """Successful withdrawal should return True."""
        mock_wave_service.withdraw_offer.return_value = True

        result = executor.withdraw_offer(offer_id=123)

        assert result is True
        mock_wave_service.withdraw_offer.assert_called_once_with(123)

    def test_withdraw_offer_returns_failure(self, executor, mock_wave_service):
        """Failed withdrawal should return False."""
        mock_wave_service.withdraw_offer.return_value = False

        result = executor.withdraw_offer(offer_id=999)

        assert result is False


class TestProcessAITurn:
    """Tests for AI turn processing."""

    def test_process_ai_turn_returns_offer_count(self, executor, mock_wave_service):
        """Should return count of AI offers made."""
        mock_wave_service.generate_ai_offers.return_value = {
            "offers_made": 15,
            "events": ["Team 5 submitted offer to Player 100"],
        }
        mock_wave_service.process_surprise_signings.return_value = []

        ai_offers_made, surprises = executor.process_ai_turn(user_team_id=1)

        assert ai_offers_made == 15
        mock_wave_service.generate_ai_offers.assert_called_once_with(1)

    def test_process_ai_turn_returns_surprises(self, executor, mock_wave_service):
        """Should return surprise signings as SigningResult list."""
        mock_wave_service.generate_ai_offers.return_value = {"offers_made": 5, "events": []}
        mock_wave_service.process_surprise_signings.return_value = [
            {"player_id": 100, "player_name": "Star QB", "team_id": 5, "aav": 30_000_000},
            {"player_id": 200, "player_name": "Top WR", "team_id": 10, "aav": 25_000_000},
        ]

        ai_offers_made, surprises = executor.process_ai_turn(user_team_id=1)

        assert len(surprises) == 2
        assert isinstance(surprises[0], SigningResult)
        assert surprises[0].player_id == 100
        assert surprises[0].player_name == "Star QB"
        assert surprises[0].is_surprise is True
        assert surprises[1].player_id == 200


class TestWaveControl:
    """Tests for wave control methods."""

    def test_advance_day_returns_new_state(self, executor, mock_wave_service):
        """advance_day should return updated wave state."""
        expected_state = {
            "current_wave": 1,
            "wave_name": "Wave 1 - Elite",
            "current_day": 2,
            "days_in_wave": 3,
        }
        mock_wave_service.advance_day.return_value = expected_state

        result = executor.advance_day()

        assert result == expected_state
        mock_wave_service.advance_day.assert_called_once()

    def test_advance_wave_resolves_offers(self, executor, mock_wave_service):
        """advance_wave should resolve pending offers."""
        mock_wave_service.resolve_wave_offers.return_value = {
            "signings": [
                {"player_id": 100, "player_name": "QB Star", "team_id": 5, "aav": 30_000_000, "years": 4},
            ],
            "no_accepts": [{"player_id": 200}],
        }
        mock_wave_service.advance_wave.return_value = {"current_wave": 2, "wave_name": "Wave 2 - Quality"}

        signings, rejections, new_state = executor.advance_wave()

        assert len(signings) == 1
        assert isinstance(signings[0], SigningResult)
        assert signings[0].player_id == 100
        assert signings[0].is_surprise is False

        assert len(rejections) == 1
        assert rejections[0] == 200

    def test_advance_wave_returns_signings(self, executor, mock_wave_service):
        """advance_wave should return list of SigningResult."""
        mock_wave_service.resolve_wave_offers.return_value = {
            "signings": [
                {"player_id": 100, "player_name": "QB Star", "team_id": 1, "aav": 30_000_000, "years": 4},
                {"player_id": 200, "player_name": "WR Ace", "team_id": 5, "aav": 20_000_000, "years": 3},
            ],
            "no_accepts": [],
        }
        mock_wave_service.advance_wave.return_value = {"current_wave": 2}

        signings, rejections, new_state = executor.advance_wave()

        assert len(signings) == 2
        assert signings[0].player_name == "QB Star"
        assert signings[1].player_name == "WR Ace"

    def test_advance_wave_handles_cannot_advance(self, executor, mock_wave_service):
        """advance_wave should return None state if can't advance (waiting for draft)."""
        mock_wave_service.resolve_wave_offers.return_value = {"signings": [], "no_accepts": []}
        mock_wave_service.advance_wave.side_effect = ValueError("Cannot advance to Wave 4 until draft complete")

        signings, rejections, new_state = executor.advance_wave()

        assert new_state is None

    def test_enable_post_draft_returns_wave_4_state(self, executor, mock_wave_service):
        """enable_post_draft should return wave 4 state."""
        expected_state = {
            "current_wave": 4,
            "wave_name": "Post-Draft",
            "current_day": 1,
            "days_in_wave": 1,
        }
        mock_wave_service.enable_post_draft_wave.return_value = expected_state

        result = executor.enable_post_draft()

        assert result == expected_state
        mock_wave_service.enable_post_draft_wave.assert_called_once()


class TestExecute:
    """Tests for the full execute() method."""

    def test_execute_combines_all_actions(self, executor, mock_wave_service):
        """execute() should process offers, AI turn, and wave control."""
        mock_wave_service.submit_offer.return_value = {"success": True, "offer_id": 1}
        mock_wave_service.withdraw_offer.return_value = True
        mock_wave_service.generate_ai_offers.return_value = {"offers_made": 10, "events": []}
        mock_wave_service.process_surprise_signings.return_value = []
        mock_wave_service.advance_day.return_value = {
            "current_wave": 1,
            "wave_name": "Wave 1 - Elite",
            "current_day": 2,
            "days_in_wave": 3,
            "wave_complete": False,
        }

        result = executor.execute(
            user_team_id=1,
            submit_offers=[{"player_id": 100, "aav": 10_000_000, "years": 3, "guaranteed": 15_000_000}],
            withdraw_offers=[50],
            advance_day=True,
        )

        assert len(result.offers_submitted) == 1
        assert len(result.offers_withdrawn) == 1
        assert result.ai_offers_made == 10
        assert result.current_day == 2

    def test_execute_returns_complete_result(self, executor, mock_wave_service):
        """execute() should return WaveExecutionResult with all fields."""
        mock_wave_service.submit_offer.return_value = {"success": True, "offer_id": 1}
        mock_wave_service.generate_ai_offers.return_value = {"offers_made": 5, "events": []}
        mock_wave_service.process_surprise_signings.return_value = [
            {"player_id": 100, "player_name": "Surprise QB", "team_id": 5, "aav": 20_000_000}
        ]

        result = executor.execute(
            user_team_id=1,
            submit_offers=[{"player_id": 200, "aav": 10_000_000, "years": 3, "guaranteed": 15_000_000}],
        )

        assert isinstance(result, WaveExecutionResult)
        assert result.wave == 1
        assert result.wave_name == "Wave 1 - Elite"
        assert result.current_day == 1
        assert result.days_in_wave == 3
        assert result.is_fa_complete is False
        assert len(result.offers_submitted) == 1
        assert len(result.surprises) == 1
        assert result.ai_offers_made == 5
        assert result.pending_offers == 5

    def test_execute_with_empty_actions(self, executor, mock_wave_service):
        """execute() with no actions should still return valid result."""
        mock_wave_service.generate_ai_offers.return_value = {"offers_made": 0, "events": []}
        mock_wave_service.process_surprise_signings.return_value = []

        result = executor.execute(user_team_id=1)

        assert isinstance(result, WaveExecutionResult)
        assert len(result.offers_submitted) == 0
        assert len(result.offers_withdrawn) == 0
        assert result.ai_offers_made == 0

    def test_execute_skips_ai_when_signing_not_allowed(self, executor, mock_wave_service):
        """execute() should skip AI turn when in Legal Tampering."""
        mock_wave_service.get_wave_state.return_value = {
            "current_wave": 0,
            "wave_name": "Legal Tampering",
            "current_day": 1,
            "days_in_wave": 1,
            "signing_allowed": False,
            "wave_complete": False,
        }

        result = executor.execute(user_team_id=1)

        # AI methods should NOT be called
        mock_wave_service.generate_ai_offers.assert_not_called()
        mock_wave_service.process_surprise_signings.assert_not_called()
        assert result.ai_offers_made == 0

    def test_execute_with_advance_wave(self, executor, mock_wave_service):
        """execute() with advance_wave should resolve offers first."""
        mock_wave_service.generate_ai_offers.return_value = {"offers_made": 0, "events": []}
        mock_wave_service.process_surprise_signings.return_value = []
        mock_wave_service.resolve_wave_offers.return_value = {
            "signings": [
                {"player_id": 100, "player_name": "QB Star", "team_id": 1, "aav": 30_000_000, "years": 4}
            ],
            "no_accepts": [{"player_id": 200}],
        }
        mock_wave_service.advance_wave.return_value = {
            "current_wave": 2,
            "wave_name": "Wave 2 - Quality",
            "current_day": 1,
            "days_in_wave": 2,
            "wave_complete": False,
        }

        result = executor.execute(user_team_id=1, advance_wave=True)

        assert len(result.signings) == 1
        assert result.signings[0].player_name == "QB Star"
        assert len(result.rejections) == 1
        assert result.wave == 2


class TestStateQueries:
    """Tests for state query methods."""

    def test_get_wave_state(self, executor, mock_wave_service):
        """get_wave_state should delegate to service."""
        executor.get_wave_state()
        mock_wave_service.get_wave_state.assert_called_once()

    def test_get_wave_summary(self, executor, mock_wave_service):
        """get_wave_summary should delegate to service."""
        executor.get_wave_summary()
        mock_wave_service.get_wave_summary.assert_called_once()

    def test_is_fa_complete(self, executor, mock_wave_service):
        """is_fa_complete should delegate to service."""
        mock_wave_service.is_fa_complete.return_value = True

        result = executor.is_fa_complete()

        assert result is True
        mock_wave_service.is_fa_complete.assert_called_once()

    def test_get_available_players(self, executor, mock_wave_service):
        """get_available_players should delegate to service."""
        expected_players = [{"player_id": 100, "name": "Star QB"}]
        mock_wave_service.get_available_players_for_wave.return_value = expected_players

        result = executor.get_available_players(user_team_id=1)

        assert result == expected_players
        mock_wave_service.get_available_players_for_wave.assert_called_once_with(user_team_id=1)

    def test_get_team_pending_offers(self, executor, mock_wave_service):
        """get_team_pending_offers should delegate to service."""
        expected_offers = [{"offer_id": 1, "player_id": 100}]
        mock_wave_service.get_team_pending_offers.return_value = expected_offers

        result = executor.get_team_pending_offers(team_id=1)

        assert result == expected_offers
        mock_wave_service.get_team_pending_offers.assert_called_once_with(1)


class TestDataclasses:
    """Tests for dataclass structure and field types."""

    def test_offer_result_fields(self):
        """OfferResult should have correct fields."""
        result = OfferResult(
            player_id=100,
            outcome=OfferOutcome.SUBMITTED,
            offer_id=123,
            error=None
        )

        assert result.player_id == 100
        assert result.outcome == OfferOutcome.SUBMITTED
        assert result.offer_id == 123
        assert result.error is None

    def test_signing_result_fields(self):
        """SigningResult should have correct fields."""
        result = SigningResult(
            player_id=100,
            player_name="Star QB",
            team_id=5,
            aav=30_000_000,
            years=4,
            is_surprise=True
        )

        assert result.player_id == 100
        assert result.player_name == "Star QB"
        assert result.team_id == 5
        assert result.aav == 30_000_000
        assert result.years == 4
        assert result.is_surprise is True

    def test_wave_execution_result_defaults(self):
        """WaveExecutionResult should have correct default values."""
        result = WaveExecutionResult(
            wave=1,
            wave_name="Wave 1 - Elite",
            current_day=1,
            days_in_wave=3,
            wave_complete=False,
            is_fa_complete=False,
        )

        assert result.offers_submitted == []
        assert result.offers_withdrawn == []
        assert result.ai_offers_made == 0
        assert result.surprises == []
        assert result.signings == []
        assert result.rejections == []
        assert result.pending_offers == 0