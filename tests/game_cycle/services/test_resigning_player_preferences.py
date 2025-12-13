"""
Integration tests for Re-signing Player Preferences (Tollgate 7).

Tests the integration of PlayerPreferenceEngine into ResigningService.
Key difference from Free Agency: is_current_team=True provides loyalty bonus.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# Import modules under test
from src.player_management.player_persona import PlayerPersona, PersonaType
from src.player_management.team_attractiveness import TeamAttractiveness
from src.player_management.preference_engine import (
    PlayerPreferenceEngine, ContractOffer
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
        persona_type=PersonaType.COMPETITOR,
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
def legacy_builder_persona():
    """Create a Legacy Builder persona who values loyalty and long-term commitment."""
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
        drafting_team_id=17,  # Drafted by contender team
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
def ring_chaser_persona():
    """Create a Ring Chaser persona who prioritizes winning."""
    return PlayerPersona(
        player_id=103,
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
    """Create an offer below market value (80%)."""
    return ContractOffer(
        team_id=17,
        aav=8_000_000,
        total_value=32_000_000,
        years=4,
        guaranteed=18_000_000,
        signing_bonus=3_000_000,
        market_aav=10_000_000,  # 80% of market
        role="starter"
    )


# ============================================================================
# Test Classes
# ============================================================================

class TestResigningWithPreferences:
    """Test player preference checking during re-signing."""

    def test_current_team_gets_loyalty_bonus(
        self, preference_engine, generic_persona, contender_team, market_value_offer
    ):
        """Current team should get +50 loyalty bonus via is_current_team=True."""
        # Score WITH current team bonus (re-signing)
        score_current = preference_engine.calculate_team_score(
            persona=generic_persona,
            team=contender_team,
            offer=market_value_offer,
            is_current_team=True,  # Re-signing
            is_drafting_team=False
        )

        # Score WITHOUT current team bonus (FA signing)
        score_not_current = preference_engine.calculate_team_score(
            persona=generic_persona,
            team=contender_team,
            offer=market_value_offer,
            is_current_team=False,
            is_drafting_team=False
        )

        # Current team should have higher score due to loyalty bonus
        assert score_current > score_not_current, \
            f"Current team bonus not applied: {score_current} vs {score_not_current}"

    def test_player_accepts_good_offer_from_current_team(
        self, preference_engine, generic_persona, contender_team, market_value_offer
    ):
        """Player should accept market value offer from current team."""
        accepted, probability, concerns = preference_engine.should_accept_offer(
            persona=generic_persona,
            team=contender_team,
            offer=market_value_offer,
            is_current_team=True,  # Re-signing
            is_drafting_team=False
        )

        # High acceptance probability with current team + market value
        assert probability >= 0.60, \
            f"Expected high acceptance for re-signing, got {probability}"

    def test_player_may_reject_low_offer(
        self, preference_engine, money_first_persona, contender_team
    ):
        """Money First player may reject below-market offer even from current team."""
        low_offer = ContractOffer(
            team_id=contender_team.team_id,
            aav=7_000_000,
            total_value=28_000_000,
            years=4,
            guaranteed=15_000_000,
            signing_bonus=2_000_000,
            market_aav=10_000_000,  # 70% of market
            role="starter"
        )

        score = preference_engine.calculate_team_score(
            persona=money_first_persona,
            team=contender_team,
            offer=low_offer,
            is_current_team=True,
            is_drafting_team=False
        )

        prob = preference_engine.calculate_acceptance_probability(
            persona=money_first_persona,
            team_score=score,
            offer_vs_market=low_offer.offer_vs_market
        )

        # Low offer should reduce acceptance even for Money First
        # (70% of market triggers -40% penalty per preference_engine)
        assert prob < 0.65, \
            f"Expected lower acceptance for below-market offer, got {prob}"


class TestLoyaltyBonus:
    """Test loyalty bonus for current team (is_current_team=True)."""

    def test_legacy_builder_extra_loyalty(
        self, preference_engine, legacy_builder_persona, contender_team, market_value_offer
    ):
        """Legacy Builder gets additional +40 loyalty bonus on top of current team bonus."""
        # With current team + drafting team (Legacy Builder was drafted by team 17)
        score_full_loyalty = preference_engine.calculate_team_score(
            persona=legacy_builder_persona,
            team=contender_team,
            offer=market_value_offer,
            is_current_team=True,  # +50
            is_drafting_team=True  # +50
        )
        # Legacy Builder also gets +40 from persona bonus

        # Without loyalty bonuses
        score_no_loyalty = preference_engine.calculate_team_score(
            persona=legacy_builder_persona,
            team=contender_team,
            offer=market_value_offer,
            is_current_team=False,
            is_drafting_team=False
        )

        # Full loyalty should be noticeably higher
        # Bonuses are weighted by loyalty_importance, so difference may be smaller than raw bonus sum
        assert score_full_loyalty > score_no_loyalty + 10, \
            f"Legacy Builder loyalty not applied correctly: {score_full_loyalty} vs {score_no_loyalty}"

    def test_legacy_builder_high_acceptance_for_current_team(
        self, preference_engine, legacy_builder_persona, contender_team, market_value_offer
    ):
        """Legacy Builder should have very high acceptance for current/drafting team."""
        accepted, probability, concerns = preference_engine.should_accept_offer(
            persona=legacy_builder_persona,
            team=contender_team,
            offer=market_value_offer,
            is_current_team=True,
            is_drafting_team=True  # Same team that drafted them
        )

        # Very high acceptance with all loyalty bonuses
        assert probability >= 0.75, \
            f"Expected very high acceptance for Legacy Builder re-signing, got {probability}"


class TestAIResigningWithPreferences:
    """Test AI team awareness of player preferences during re-signing."""

    def test_ai_evaluates_acceptance_probability(
        self, preference_engine, ring_chaser_persona, rebuilding_team, market_value_offer
    ):
        """AI should evaluate acceptance probability before attempting re-signing."""
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
            is_current_team=True,
            is_drafting_team=False
        )

        probability = preference_engine.calculate_acceptance_probability(
            persona=ring_chaser_persona,
            team_score=score,
            offer_vs_market=1.0
        )

        # Ring Chaser on rebuilding team - even with current team bonus,
        # should have moderate-to-low probability
        assert 0.20 < probability < 0.80, \
            f"AI evaluation should show mixed likelihood: {probability}"

    def test_concerns_returned_for_poor_fit(
        self, preference_engine, ring_chaser_persona, rebuilding_team
    ):
        """AI should see concerns for poor player-team fit."""
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

        # Ring Chaser should have winning-related concerns about rebuilding team
        assert len(concerns) > 0, "Expected concerns for Ring Chaser on rebuilding team"
        assert any("playoff" in c.lower() for c in concerns), \
            f"Expected playoff concern, got {concerns}"


class TestResigningVsFreAgencyDifference:
    """Test the key difference between re-signing and free agency."""

    def test_same_offer_different_acceptance(
        self, preference_engine, generic_persona, contender_team, market_value_offer
    ):
        """Same offer should have higher acceptance in re-signing than free agency."""
        # Re-signing scenario (is_current_team=True)
        _, prob_resigning, _ = preference_engine.should_accept_offer(
            persona=generic_persona,
            team=contender_team,
            offer=market_value_offer,
            is_current_team=True,
            is_drafting_team=False
        )

        # Free agency scenario (is_current_team=False)
        _, prob_fa, _ = preference_engine.should_accept_offer(
            persona=generic_persona,
            team=contender_team,
            offer=market_value_offer,
            is_current_team=False,
            is_drafting_team=False
        )

        # Re-signing should have higher acceptance due to loyalty bonus
        assert prob_resigning >= prob_fa, \
            f"Re-signing should have >= acceptance than FA: {prob_resigning} vs {prob_fa}"


# ============================================================================
# Run with: python -m pytest tests/game_cycle/services/test_resigning_player_preferences.py -v
# ============================================================================
