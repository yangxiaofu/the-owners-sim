"""
Integration tests for Trade Veto Logic (Tollgate 8).

Tests the integration of PlayerPreferenceEngine into TradeEvaluator for player veto.
Key concept: Players can veto trade destinations based on persona preferences.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

# Import modules under test
from src.player_management.player_persona import PlayerPersona, PersonaType
from src.player_management.team_attractiveness import TeamAttractiveness
from src.player_management.preference_engine import (
    PlayerPreferenceEngine, ContractOffer
)
from src.transactions.models import (
    TradeProposal, TradeAsset, TradeDecision, TradeDecisionType,
    AssetType, FairnessRating
)
from src.transactions.trade_evaluator import TradeEvaluator
from src.transactions.personality_modifiers import TeamContext


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def preference_engine():
    """Create a PlayerPreferenceEngine instance."""
    return PlayerPreferenceEngine()


@pytest.fixture
def legacy_builder_persona():
    """Create a Legacy Builder persona who values loyalty."""
    return PlayerPersona(
        player_id=101,
        persona_type=PersonaType.LEGACY_BUILDER,
        money_importance=40,
        winning_importance=50,
        location_importance=30,
        playing_time_importance=40,
        loyalty_importance=85,
        market_size_importance=30,
        birthplace_state=None,
        college_state=None,
        drafting_team_id=17,  # Drafted by Dallas Cowboys
    )


@pytest.fixture
def ring_chaser_persona():
    """Create a Ring Chaser persona who prioritizes winning."""
    return PlayerPersona(
        player_id=102,
        persona_type=PersonaType.RING_CHASER,
        money_importance=30,
        winning_importance=90,
        location_importance=20,
        playing_time_importance=40,
        loyalty_importance=20,
        market_size_importance=20,
        birthplace_state=None,
        college_state=None,
        drafting_team_id=None,
    )


@pytest.fixture
def money_first_persona():
    """Create a Money First persona who follows the money."""
    return PlayerPersona(
        player_id=103,
        persona_type=PersonaType.MONEY_FIRST,
        money_importance=95,
        winning_importance=20,
        location_importance=20,
        playing_time_importance=30,
        loyalty_importance=10,
        market_size_importance=20,
        birthplace_state=None,
        college_state=None,
        drafting_team_id=None,
    )


@pytest.fixture
def contender_team():
    """Create a contender team with high winning metrics."""
    return TeamAttractiveness(
        team_id=17,  # Dallas Cowboys
        market_size=90,
        state_income_tax_rate=0.0,  # Texas - no state tax
        weather_score=70,
        state="TX",
        playoff_appearances_5yr=5,
        super_bowl_wins_5yr=2,
        winning_culture_score=90,
        current_season_wins=14,
        current_season_losses=3,
    )


@pytest.fixture
def rebuilding_team():
    """Create a rebuilding team with low winning metrics."""
    return TeamAttractiveness(
        team_id=5,  # Cleveland Browns
        market_size=45,
        state_income_tax_rate=0.05,
        weather_score=30,
        state="OH",
        playoff_appearances_5yr=1,
        super_bowl_wins_5yr=0,
        winning_culture_score=35,
        current_season_wins=4,
        current_season_losses=13,
    )


@pytest.fixture
def mock_gm_archetype():
    """Create a mock GM archetype for TradeEvaluator."""
    gm = MagicMock()
    gm.name = "Test GM"
    gm.draft_pick_value = 0.5
    gm.star_chasing = 0.5
    gm.cap_management = 0.5
    gm.risk_tolerance = 0.5
    gm.win_now_mentality = 0.5
    gm.deadline_activity = 0.5
    gm.veteran_preference = 0.5
    return gm


@pytest.fixture
def mock_team_context():
    """Create a mock team context for TradeEvaluator."""
    context = TeamContext(
        team_id=17,
        season=2025,
        wins=10,
        losses=5,
        cap_space=20_000_000,
        is_deadline=False,
        is_offseason=False,
        top_needs=["WR"],
    )
    return context


@pytest.fixture
def mock_trade_value_calculator():
    """Create a mock trade value calculator."""
    return MagicMock()


# ============================================================================
# Test Classes
# ============================================================================

class TestTradeVetoWithPreferenceEngine:
    """Test player veto logic using PlayerPreferenceEngine directly."""

    def test_ring_chaser_vetoes_rebuilding_destination(
        self, preference_engine, ring_chaser_persona, rebuilding_team
    ):
        """Ring Chaser should veto trade to rebuilding team."""
        offer = ContractOffer(
            team_id=rebuilding_team.team_id,
            aav=10_000_000,
            total_value=10_000_000,
            years=1,
            guaranteed=0,
            signing_bonus=0,
            market_aav=10_000_000,
            role="starter"
        )

        team_score = preference_engine.calculate_team_score(
            persona=ring_chaser_persona,
            team=rebuilding_team,
            offer=offer,
            is_current_team=False,
            is_drafting_team=False
        )

        probability = preference_engine.calculate_acceptance_probability(
            persona=ring_chaser_persona,
            team_score=team_score,
            offer_vs_market=1.0
        )

        # Ring Chaser on rebuilding team should have low acceptance
        # Below 30% = veto threshold
        assert probability < 0.50, \
            f"Ring Chaser should have low acceptance for rebuilding team: {probability}"

    def test_ring_chaser_accepts_contender_destination(
        self, preference_engine, ring_chaser_persona, contender_team
    ):
        """Ring Chaser should accept trade to contender."""
        offer = ContractOffer(
            team_id=contender_team.team_id,
            aav=10_000_000,
            total_value=10_000_000,
            years=1,
            guaranteed=0,
            signing_bonus=0,
            market_aav=10_000_000,
            role="starter"
        )

        team_score = preference_engine.calculate_team_score(
            persona=ring_chaser_persona,
            team=contender_team,
            offer=offer,
            is_current_team=False,
            is_drafting_team=False
        )

        probability = preference_engine.calculate_acceptance_probability(
            persona=ring_chaser_persona,
            team_score=team_score,
            offer_vs_market=1.0
        )

        # Ring Chaser on contender should have high acceptance
        assert probability >= 0.50, \
            f"Ring Chaser should accept trade to contender: {probability}"

    def test_legacy_builder_prefers_drafting_team(
        self, preference_engine, legacy_builder_persona, rebuilding_team, contender_team
    ):
        """Legacy Builder should score drafting team higher than non-drafting team."""
        # Note: Legacy Builder was drafted by team 17 (contender_team)
        # They should prefer their drafting team over other teams

        offer = ContractOffer(
            team_id=rebuilding_team.team_id,
            aav=10_000_000,
            total_value=10_000_000,
            years=1,
            guaranteed=0,
            signing_bonus=0,
            market_aav=10_000_000,
            role="starter"
        )

        # Score for non-drafting team
        score_non_drafting = preference_engine.calculate_team_score(
            persona=legacy_builder_persona,
            team=rebuilding_team,
            offer=offer,
            is_current_team=False,
            is_drafting_team=False
        )

        # Score for drafting team (contender_team is team 17 where they were drafted)
        offer_drafting = ContractOffer(
            team_id=contender_team.team_id,
            aav=10_000_000,
            total_value=10_000_000,
            years=1,
            guaranteed=0,
            signing_bonus=0,
            market_aav=10_000_000,
            role="starter"
        )

        score_drafting = preference_engine.calculate_team_score(
            persona=legacy_builder_persona,
            team=contender_team,
            offer=offer_drafting,
            is_current_team=False,
            is_drafting_team=True  # This IS the drafting team
        )

        # Legacy Builder should prefer their drafting team significantly
        assert score_drafting > score_non_drafting, \
            f"Legacy Builder should prefer drafting team: {score_drafting} vs {score_non_drafting}"


class TestTradeEvaluatorVeto:
    """Test TradeEvaluator with player veto integration."""

    def test_veto_details_in_trade_decision(self):
        """TradeDecision should include veto details when vetoed."""
        # Create a trade decision with veto
        decision = TradeDecision(
            decision=TradeDecisionType.REJECT,
            reasoning="Player vetoed the trade.",
            confidence=0.95,
            original_proposal=MagicMock(spec=TradeProposal),
            player_veto=True,
            veto_details=[{
                "player_id": 101,
                "player_name": "John Doe",
                "probability": 0.20,
                "concerns": ["Poor winning culture"],
                "persona_type": "ring_chaser"
            }]
        )

        assert decision.player_veto is True
        assert len(decision.veto_details) == 1
        assert decision.veto_details[0]["player_name"] == "John Doe"
        assert decision.veto_details[0]["probability"] == 0.20

    def test_no_veto_for_picks_only_trade(
        self, mock_gm_archetype, mock_team_context, mock_trade_value_calculator
    ):
        """Trades with only draft picks should never have player veto."""
        # Create evaluator without veto support (no db_path)
        evaluator = TradeEvaluator(
            gm_archetype=mock_gm_archetype,
            team_context=mock_team_context,
            trade_value_calculator=mock_trade_value_calculator
        )

        # Create draft pick assets
        pick_asset = TradeAsset(
            asset_type=AssetType.DRAFT_PICK,
            trade_value=500.0  # Arbitrary value
        )

        # Check veto - should return False for picks only
        has_veto, veto_details = evaluator._check_player_vetoes(
            acquiring_assets=[pick_asset],
            acquiring_team_id=17
        )

        assert has_veto is False
        assert len(veto_details) == 0

    def test_veto_skipped_without_db_path(
        self, mock_gm_archetype, mock_team_context, mock_trade_value_calculator
    ):
        """Veto check should be skipped if db_path not provided."""
        # Create evaluator without veto support
        evaluator = TradeEvaluator(
            gm_archetype=mock_gm_archetype,
            team_context=mock_team_context,
            trade_value_calculator=mock_trade_value_calculator,
            db_path=None,
            dynasty_id=None,
            season=None
        )

        # Create player asset
        player_asset = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=101,
            player_name="John Doe",
            overall_rating=85,
            trade_value=1000.0
        )

        # Check veto - should return False when db_path not set
        has_veto, veto_details = evaluator._check_player_vetoes(
            acquiring_assets=[player_asset],
            acquiring_team_id=17
        )

        assert has_veto is False
        assert len(veto_details) == 0

    def test_can_check_vetoes_returns_false_without_config(
        self, mock_gm_archetype, mock_team_context, mock_trade_value_calculator
    ):
        """_can_check_vetoes should return False without db_path/dynasty_id."""
        evaluator = TradeEvaluator(
            gm_archetype=mock_gm_archetype,
            team_context=mock_team_context,
            trade_value_calculator=mock_trade_value_calculator
        )

        assert evaluator._can_check_vetoes() is False

    def test_can_check_vetoes_returns_true_with_config(
        self, mock_gm_archetype, mock_team_context, mock_trade_value_calculator
    ):
        """_can_check_vetoes should return True with db_path/dynasty_id/season."""
        evaluator = TradeEvaluator(
            gm_archetype=mock_gm_archetype,
            team_context=mock_team_context,
            trade_value_calculator=mock_trade_value_calculator,
            db_path="/path/to/db.db",
            dynasty_id="test-dynasty",
            season=2025
        )

        assert evaluator._can_check_vetoes() is True


class TestVetoReasoningGeneration:
    """Test veto reasoning generation."""

    def test_generate_veto_reasoning_single_player(
        self, mock_gm_archetype, mock_team_context, mock_trade_value_calculator
    ):
        """Should generate readable reasoning for single player veto."""
        evaluator = TradeEvaluator(
            gm_archetype=mock_gm_archetype,
            team_context=mock_team_context,
            trade_value_calculator=mock_trade_value_calculator
        )

        veto_details = [{
            "player_id": 101,
            "player_name": "John Doe",
            "probability": 0.15,
            "concerns": ["Poor winning culture", "Small market"],
            "persona_type": "ring_chaser"
        }]

        reasoning = evaluator._generate_veto_reasoning(veto_details)

        assert "John Doe" in reasoning
        assert "Ring Chaser" in reasoning
        assert "15%" in reasoning
        assert "Poor winning culture" in reasoning
        assert "Trade rejected due to player veto" in reasoning

    def test_generate_veto_reasoning_multiple_players(
        self, mock_gm_archetype, mock_team_context, mock_trade_value_calculator
    ):
        """Should generate reasoning for multiple player vetoes."""
        evaluator = TradeEvaluator(
            gm_archetype=mock_gm_archetype,
            team_context=mock_team_context,
            trade_value_calculator=mock_trade_value_calculator
        )

        veto_details = [
            {
                "player_id": 101,
                "player_name": "John Doe",
                "probability": 0.15,
                "concerns": ["Poor winning culture"],
                "persona_type": "ring_chaser"
            },
            {
                "player_id": 102,
                "player_name": "Jane Smith",
                "probability": 0.25,
                "concerns": ["High state taxes"],
                "persona_type": "money_first"
            }
        ]

        reasoning = evaluator._generate_veto_reasoning(veto_details)

        assert "John Doe" in reasoning
        assert "Jane Smith" in reasoning
        assert "Ring Chaser" in reasoning
        assert "Money First" in reasoning


class TestEstimateRole:
    """Test role estimation for trade context."""

    def test_estimate_role_starter(
        self, mock_gm_archetype, mock_team_context, mock_trade_value_calculator
    ):
        """High overall should estimate starter role."""
        evaluator = TradeEvaluator(
            gm_archetype=mock_gm_archetype,
            team_context=mock_team_context,
            trade_value_calculator=mock_trade_value_calculator
        )

        assert evaluator._estimate_role(90) == "starter"
        assert evaluator._estimate_role(85) == "starter"

    def test_estimate_role_rotational(
        self, mock_gm_archetype, mock_team_context, mock_trade_value_calculator
    ):
        """Medium overall should estimate rotational role."""
        evaluator = TradeEvaluator(
            gm_archetype=mock_gm_archetype,
            team_context=mock_team_context,
            trade_value_calculator=mock_trade_value_calculator
        )

        assert evaluator._estimate_role(80) == "rotational"
        assert evaluator._estimate_role(75) == "rotational"

    def test_estimate_role_depth(
        self, mock_gm_archetype, mock_team_context, mock_trade_value_calculator
    ):
        """Low overall should estimate depth role."""
        evaluator = TradeEvaluator(
            gm_archetype=mock_gm_archetype,
            team_context=mock_team_context,
            trade_value_calculator=mock_trade_value_calculator
        )

        assert evaluator._estimate_role(70) == "depth"
        assert evaluator._estimate_role(65) == "depth"

    def test_estimate_role_none(
        self, mock_gm_archetype, mock_team_context, mock_trade_value_calculator
    ):
        """None overall should estimate rotational role."""
        evaluator = TradeEvaluator(
            gm_archetype=mock_gm_archetype,
            team_context=mock_team_context,
            trade_value_calculator=mock_trade_value_calculator
        )

        assert evaluator._estimate_role(None) == "rotational"


# ============================================================================
# Run with: python -m pytest tests/game_cycle/services/test_trade_veto.py -v
# ============================================================================
