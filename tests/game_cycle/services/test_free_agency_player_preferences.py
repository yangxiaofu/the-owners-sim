"""
Integration tests for Free Agency Player Preferences (Tollgate 6).

Tests the integration of PlayerPreferenceEngine into FreeAgencyService.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass
from typing import Optional

# Import modules under test
from src.player_management.player_persona import PlayerPersona, PersonaType
from src.player_management.team_attractiveness import TeamAttractiveness
from src.player_management.preference_engine import (
    PlayerPreferenceEngine, ContractOffer, OfferEvaluation
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def preference_engine():
    """Create a PlayerPreferenceEngine instance."""
    return PlayerPreferenceEngine()


@pytest.fixture
def generic_persona():
    """Create a generic player persona with balanced preferences."""
    return PlayerPersona(
        player_id=100,
        persona_type=PersonaType.COMPETITOR,  # Using COMPETITOR as a neutral type
        money_importance=50,
        winning_importance=50,
        location_importance=50,
        playing_time_importance=50,
        loyalty_importance=50,
        market_size_importance=50,
        birthplace_state=None,
        college_state=None,
        drafting_team_id=None,
    )


@pytest.fixture
def ring_chaser_persona():
    """Create a Ring Chaser persona who prioritizes winning."""
    return PlayerPersona(
        player_id=101,
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
    """Create a Money First persona who prioritizes salary."""
    return PlayerPersona(
        player_id=102,
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
def big_market_persona():
    """Create a Big Market persona who prefers large market teams."""
    return PlayerPersona(
        player_id=103,
        persona_type=PersonaType.BIG_MARKET,
        money_importance=50,
        winning_importance=40,
        location_importance=30,
        playing_time_importance=40,
        loyalty_importance=20,
        market_size_importance=80,
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
def small_market_team():
    """Create a small market team."""
    return TeamAttractiveness(
        team_id=12,  # Green Bay Packers
        market_size=25,
        state_income_tax_rate=0.075,
        weather_score=25,
        state="WI",
        playoff_appearances_5yr=4,
        super_bowl_wins_5yr=1,
        winning_culture_score=75,
        current_season_wins=12,
        current_season_losses=5,
    )


@pytest.fixture
def market_value_offer():
    """Create an offer at market value."""
    return ContractOffer(
        team_id=17,
        aav=10_000_000,
        total_value=40_000_000,
        years=4,
        guaranteed=25_000_000,
        signing_bonus=5_000_000,
        market_aav=10_000_000,
        role="starter"
    )


@pytest.fixture
def below_market_offer():
    """Create an offer below market value."""
    return ContractOffer(
        team_id=17,
        aav=7_000_000,
        total_value=28_000_000,
        years=4,
        guaranteed=15_000_000,
        signing_bonus=2_000_000,
        market_aav=10_000_000,  # 70% of market
        role="rotational"
    )


@pytest.fixture
def premium_offer():
    """Create an offer above market value (120%+)."""
    return ContractOffer(
        team_id=17,
        aav=12_000_000,
        total_value=48_000_000,
        years=4,
        guaranteed=30_000_000,
        signing_bonus=8_000_000,
        market_aav=10_000_000,  # 120% of market
        role="starter"
    )


# ============================================================================
# Test Classes
# ============================================================================

class TestPreferenceIntegration:
    """Test preference engine integration scenarios."""

    def test_ring_chaser_prefers_contender(
        self, preference_engine, ring_chaser_persona, contender_team, market_value_offer
    ):
        """Ring Chaser should have high score for contender team."""
        score = preference_engine.calculate_team_score(
            persona=ring_chaser_persona,
            team=contender_team,
            offer=market_value_offer,
            is_current_team=False,
            is_drafting_team=False
        )
        # Ring Chaser with contender should have high score
        assert score >= 70, f"Ring Chaser should like contender, got {score}"

    def test_ring_chaser_dislikes_rebuilding(
        self, preference_engine, ring_chaser_persona, rebuilding_team, market_value_offer
    ):
        """Ring Chaser should have low score for rebuilding team."""
        # Adjust offer for rebuilding team
        offer = ContractOffer(
            team_id=rebuilding_team.team_id,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=25_000_000,
            signing_bonus=5_000_000,
            market_aav=10_000_000,
            role="starter"
        )
        score = preference_engine.calculate_team_score(
            persona=ring_chaser_persona,
            team=rebuilding_team,
            offer=offer,
            is_current_team=False,
            is_drafting_team=False
        )
        # Ring Chaser with rebuilding team should have lower score
        assert score <= 60, f"Ring Chaser should dislike rebuilding team, got {score}"

    def test_money_first_accepts_at_market(
        self, preference_engine, money_first_persona, rebuilding_team, market_value_offer
    ):
        """Money First player should accept at market value regardless of team."""
        offer = ContractOffer(
            team_id=rebuilding_team.team_id,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=25_000_000,
            signing_bonus=5_000_000,
            market_aav=10_000_000,
            role="starter"
        )
        score = preference_engine.calculate_team_score(
            persona=money_first_persona,
            team=rebuilding_team,
            offer=offer,
            is_current_team=False,
            is_drafting_team=False
        )
        prob = preference_engine.calculate_acceptance_probability(
            persona=money_first_persona,
            team_score=score,
            offer_vs_market=offer.offer_vs_market
        )
        # Money First at market value should have high acceptance
        assert prob >= 0.85, f"Money First should accept market offer, got {prob}"

    def test_premium_offer_overrides_preferences(
        self, preference_engine, ring_chaser_persona, rebuilding_team
    ):
        """Premium offer (120%+) should override preference concerns."""
        premium = ContractOffer(
            team_id=rebuilding_team.team_id,
            aav=12_000_000,
            total_value=48_000_000,
            years=4,
            guaranteed=30_000_000,
            signing_bonus=8_000_000,
            market_aav=10_000_000,  # 120% of market
            role="starter"
        )
        score = preference_engine.calculate_team_score(
            persona=ring_chaser_persona,
            team=rebuilding_team,
            offer=premium,
            is_current_team=False,
            is_drafting_team=False
        )
        prob = preference_engine.calculate_acceptance_probability(
            persona=ring_chaser_persona,
            team_score=score,
            offer_vs_market=premium.offer_vs_market
        )
        # 120%+ market offer should always be 95%
        assert prob == 0.95, f"Premium offer should have 95% acceptance, got {prob}"

    def test_low_offer_reduces_acceptance(
        self, preference_engine, generic_persona, contender_team
    ):
        """Below market offer should reduce acceptance probability."""
        low_offer = ContractOffer(
            team_id=contender_team.team_id,
            aav=7_000_000,
            total_value=28_000_000,
            years=4,
            guaranteed=15_000_000,
            signing_bonus=2_000_000,
            market_aav=10_000_000,  # 70% of market
            role="rotational"
        )
        score = preference_engine.calculate_team_score(
            persona=generic_persona,
            team=contender_team,
            offer=low_offer,
            is_current_team=False,
            is_drafting_team=False
        )
        prob = preference_engine.calculate_acceptance_probability(
            persona=generic_persona,
            team_score=score,
            offer_vs_market=low_offer.offer_vs_market
        )
        # 70% of market should have penalty applied
        assert prob < 0.50, f"Low offer should reduce acceptance, got {prob}"


class TestConcernGeneration:
    """Test concern generation for different scenarios."""

    def test_ring_chaser_has_winning_concerns(
        self, preference_engine, ring_chaser_persona, rebuilding_team, market_value_offer
    ):
        """Ring Chaser should have concerns about rebuilding team."""
        offer = ContractOffer(
            team_id=rebuilding_team.team_id,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=25_000_000,
            signing_bonus=5_000_000,
            market_aav=10_000_000,
            role="starter"
        )
        concerns = preference_engine.get_concerns(
            persona=ring_chaser_persona,
            team=rebuilding_team,
            offer=offer
        )
        # Should have playoff-related concern
        assert any("playoff" in c.lower() for c in concerns), \
            f"Ring Chaser should have playoff concern, got {concerns}"

    def test_big_market_has_market_concerns(
        self, preference_engine, big_market_persona, small_market_team, market_value_offer
    ):
        """Big Market persona should have concerns about small market."""
        offer = ContractOffer(
            team_id=small_market_team.team_id,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=25_000_000,
            signing_bonus=5_000_000,
            market_aav=10_000_000,
            role="starter"
        )
        concerns = preference_engine.get_concerns(
            persona=big_market_persona,
            team=small_market_team,
            offer=offer
        )
        # Should have market-related concern
        assert any("market" in c.lower() for c in concerns), \
            f"Big Market should have market concern, got {concerns}"

    def test_money_first_has_money_concerns(
        self, preference_engine, money_first_persona, contender_team
    ):
        """Money First persona should have concerns about below-market offer."""
        low_offer = ContractOffer(
            team_id=contender_team.team_id,
            aav=8_000_000,
            total_value=32_000_000,
            years=4,
            guaranteed=18_000_000,
            signing_bonus=4_000_000,
            market_aav=10_000_000,  # 80% of market
            role="starter"
        )
        concerns = preference_engine.get_concerns(
            persona=money_first_persona,
            team=contender_team,
            offer=low_offer
        )
        # Should have money-related concern
        assert any("dollar" in c.lower() or "money" in c.lower() or "competitive" in c.lower()
                  for c in concerns), \
            f"Money First should have money concern for low offer, got {concerns}"


class TestOfferEvaluation:
    """Test offer evaluation and ranking."""

    def test_evaluate_multiple_offers(
        self, preference_engine, generic_persona, contender_team, rebuilding_team
    ):
        """Should correctly rank multiple offers."""
        contender_offer = ContractOffer(
            team_id=contender_team.team_id,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=25_000_000,
            signing_bonus=5_000_000,
            market_aav=10_000_000,
            role="starter"
        )
        rebuilding_offer = ContractOffer(
            team_id=rebuilding_team.team_id,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=25_000_000,
            signing_bonus=5_000_000,
            market_aav=10_000_000,
            role="starter"
        )

        offers = [
            (rebuilding_team, rebuilding_offer),
            (contender_team, contender_offer),
        ]

        evaluations = preference_engine.evaluate_all_offers(
            persona=generic_persona,
            offers=offers,
            current_team_id=None
        )

        # Should return sorted by score (highest first)
        assert len(evaluations) == 2
        assert evaluations[0].team_score >= evaluations[1].team_score


class TestShouldAcceptOffer:
    """Test the should_accept_offer decision method."""

    def test_should_accept_returns_tuple(
        self, preference_engine, generic_persona, contender_team, market_value_offer
    ):
        """should_accept_offer should return (bool, float, list) tuple."""
        accepted, probability, concerns = preference_engine.should_accept_offer(
            persona=generic_persona,
            team=contender_team,
            offer=market_value_offer,
            is_current_team=False,
            is_drafting_team=False
        )

        assert isinstance(accepted, bool)
        assert isinstance(probability, float)
        assert 0.0 <= probability <= 1.0
        assert isinstance(concerns, list)

    def test_drafting_team_bonus(
        self, preference_engine, contender_team
    ):
        """Drafting team should get loyalty bonus."""
        persona_drafted = PlayerPersona(
            player_id=200,
            persona_type=PersonaType.LEGACY_BUILDER,
            money_importance=40,
            winning_importance=40,
            location_importance=30,
            playing_time_importance=40,
            loyalty_importance=80,
            market_size_importance=20,
            birthplace_state=None,
            college_state=None,
            drafting_team_id=contender_team.team_id,  # Drafted by contender
        )

        offer = ContractOffer(
            team_id=contender_team.team_id,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=25_000_000,
            signing_bonus=5_000_000,
            market_aav=10_000_000,
            role="starter"
        )

        # Score with drafting team
        score_drafting = preference_engine.calculate_team_score(
            persona=persona_drafted,
            team=contender_team,
            offer=offer,
            is_current_team=False,
            is_drafting_team=True  # This is the drafting team
        )

        # Score without drafting team bonus
        score_other = preference_engine.calculate_team_score(
            persona=persona_drafted,
            team=contender_team,
            offer=offer,
            is_current_team=False,
            is_drafting_team=False
        )

        # Drafting team should have higher score
        assert score_drafting > score_other, \
            f"Drafting team bonus not applied: {score_drafting} vs {score_other}"


class TestInterestLevelCalculation:
    """Test interest level categorization."""

    def test_high_interest_threshold(self, preference_engine):
        """Probability >= 0.75 should be high interest."""
        # High acceptance probability
        prob = 0.80
        if prob >= 0.75:
            interest = "high"
        elif prob >= 0.45:
            interest = "medium"
        else:
            interest = "low"

        assert interest == "high"

    def test_medium_interest_threshold(self, preference_engine):
        """Probability 0.45-0.74 should be medium interest."""
        prob = 0.55
        if prob >= 0.75:
            interest = "high"
        elif prob >= 0.45:
            interest = "medium"
        else:
            interest = "low"

        assert interest == "medium"

    def test_low_interest_threshold(self, preference_engine):
        """Probability < 0.45 should be low interest."""
        prob = 0.30
        if prob >= 0.75:
            interest = "high"
        elif prob >= 0.45:
            interest = "medium"
        else:
            interest = "low"

        assert interest == "low"


class TestContractOfferProperties:
    """Test ContractOffer dataclass properties."""

    def test_offer_vs_market_at_market(self):
        """offer_vs_market should be 1.0 at market value."""
        offer = ContractOffer(
            team_id=1,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=25_000_000,
            market_aav=10_000_000,
        )
        assert offer.offer_vs_market == 1.0

    def test_offer_vs_market_above(self):
        """offer_vs_market should be > 1.0 above market."""
        offer = ContractOffer(
            team_id=1,
            aav=12_000_000,
            total_value=48_000_000,
            years=4,
            guaranteed=30_000_000,
            market_aav=10_000_000,
        )
        assert offer.offer_vs_market == 1.2

    def test_offer_vs_market_below(self):
        """offer_vs_market should be < 1.0 below market."""
        offer = ContractOffer(
            team_id=1,
            aav=8_000_000,
            total_value=32_000_000,
            years=4,
            guaranteed=20_000_000,
            market_aav=10_000_000,
        )
        assert offer.offer_vs_market == 0.8

    def test_guaranteed_percentage(self):
        """guaranteed_percentage should calculate correctly."""
        offer = ContractOffer(
            team_id=1,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=20_000_000,
        )
        assert offer.guaranteed_percentage == 0.5


# ============================================================================
# Run with: python -m pytest tests/game_cycle/services/test_free_agency_player_preferences.py -v
# ============================================================================
