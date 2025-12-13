"""
Unit tests for PlayerPreferenceEngine.

Tests score calculation, persona bonuses, acceptance probability,
and concern generation.
Part of Tollgate 5: Preference Engine.
"""
import pytest

from src.player_management.player_persona import PlayerPersona, PersonaType
from src.player_management.team_attractiveness import TeamAttractiveness
from src.player_management.preference_engine import (
    ContractOffer,
    OfferEvaluation,
    PlayerPreferenceEngine,
)


# -------------------- Fixtures --------------------


@pytest.fixture
def engine():
    """Create a preference engine instance."""
    return PlayerPreferenceEngine()


@pytest.fixture
def default_persona():
    """Create a default persona with balanced preferences."""
    return PlayerPersona(
        player_id=1,
        persona_type=PersonaType.COMPETITOR,
        money_importance=50,
        winning_importance=50,
        location_importance=50,
        playing_time_importance=50,
        loyalty_importance=50,
        market_size_importance=50,
    )


@pytest.fixture
def contender_team():
    """Create a contending team (high scores)."""
    return TeamAttractiveness(
        team_id=17,
        market_size=90,
        state_income_tax_rate=0.0,  # Texas
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
    """Create a rebuilding team (low scores)."""
    return TeamAttractiveness(
        team_id=5,
        market_size=30,
        state_income_tax_rate=0.10,  # High tax
        weather_score=30,
        state="OH",
        playoff_appearances_5yr=0,
        super_bowl_wins_5yr=0,
        winning_culture_score=25,
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
        guaranteed=20_000_000,
        market_aav=10_000_000,
        role="starter",
    )


# -------------------- ContractOffer Tests --------------------


class TestContractOffer:
    """Tests for ContractOffer dataclass."""

    def test_offer_vs_market_at_value(self):
        """Offer at market value returns 1.0."""
        offer = ContractOffer(
            team_id=1,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=20_000_000,
            market_aav=10_000_000,
        )
        assert offer.offer_vs_market == 1.0

    def test_offer_vs_market_above(self):
        """Offer above market value returns > 1.0."""
        offer = ContractOffer(
            team_id=1,
            aav=12_000_000,
            total_value=48_000_000,
            years=4,
            guaranteed=24_000_000,
            market_aav=10_000_000,
        )
        assert offer.offer_vs_market == 1.2

    def test_offer_vs_market_below(self):
        """Offer below market value returns < 1.0."""
        offer = ContractOffer(
            team_id=1,
            aav=8_000_000,
            total_value=32_000_000,
            years=4,
            guaranteed=16_000_000,
            market_aav=10_000_000,
        )
        assert offer.offer_vs_market == 0.8

    def test_offer_vs_market_zero_market(self):
        """Zero market_aav returns 1.0 (default)."""
        offer = ContractOffer(
            team_id=1,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=20_000_000,
            market_aav=0,
        )
        assert offer.offer_vs_market == 1.0

    def test_guaranteed_percentage(self):
        """Guaranteed percentage calculated correctly."""
        offer = ContractOffer(
            team_id=1,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=20_000_000,
        )
        assert offer.guaranteed_percentage == 0.5


# -------------------- Money Score Tests --------------------


class TestMoneyScore:
    """Tests for money score calculation."""

    def test_at_market_value(self, engine):
        """Offer at market value scores 80."""
        offer = ContractOffer(
            team_id=1,
            aav=10_000_000,
            total_value=40_000_000,
            years=4,
            guaranteed=20_000_000,
            market_aav=10_000_000,
        )
        score = engine._calculate_money_score(offer)
        assert score == 80

    def test_above_market_120_scores_100(self, engine):
        """120%+ of market scores 100."""
        offer = ContractOffer(
            team_id=1,
            aav=12_000_000,
            total_value=48_000_000,
            years=4,
            guaranteed=24_000_000,
            market_aav=10_000_000,
        )
        score = engine._calculate_money_score(offer)
        assert score == 100

    def test_above_market_110_scores_90(self, engine):
        """110% of market scores ~90."""
        offer = ContractOffer(
            team_id=1,
            aav=11_000_000,
            total_value=44_000_000,
            years=4,
            guaranteed=22_000_000,
            market_aav=10_000_000,
        )
        score = engine._calculate_money_score(offer)
        assert score == 90

    def test_below_market_80_scores_40(self, engine):
        """80% of market scores 40."""
        offer = ContractOffer(
            team_id=1,
            aav=8_000_000,
            total_value=32_000_000,
            years=4,
            guaranteed=16_000_000,
            market_aav=10_000_000,
        )
        score = engine._calculate_money_score(offer)
        assert score == 40

    def test_below_market_70_scores_low(self, engine):
        """70% of market scores ~35."""
        offer = ContractOffer(
            team_id=1,
            aav=7_000_000,
            total_value=28_000_000,
            years=4,
            guaranteed=14_000_000,
            market_aav=10_000_000,
        )
        score = engine._calculate_money_score(offer)
        assert score < 40


# -------------------- Winning Score Tests --------------------


class TestWinningScore:
    """Tests for winning score calculation."""

    def test_contender_high_score(self, engine, contender_team):
        """Contending team has high winning score."""
        score = engine._calculate_winning_score(contender_team)
        assert score > 70

    def test_rebuilding_low_score(self, engine, rebuilding_team):
        """Rebuilding team has low winning score."""
        score = engine._calculate_winning_score(rebuilding_team)
        assert score < 30


# -------------------- Location Score Tests --------------------


class TestLocationScore:
    """Tests for location score calculation."""

    def test_no_tax_state_bonus(self, engine, default_persona, contender_team):
        """No-tax state gets tax bonus."""
        score = engine._calculate_location_score(default_persona, contender_team)
        # TX has 0% tax = 100 tax_advantage_score * 0.3 = 30 points from tax
        assert score >= 30

    def test_high_tax_penalty(self, engine, default_persona, rebuilding_team):
        """High tax state gets lower score."""
        score = engine._calculate_location_score(default_persona, rebuilding_team)
        # OH has 10% tax = ~23 tax_advantage_score * 0.3 = ~7 points from tax
        assert score < 40

    def test_home_state_bonus(self, engine, contender_team):
        """Player from team's state gets +40."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.COMPETITOR,
            birthplace_state="TX",
        )
        score = engine._calculate_location_score(persona, contender_team)
        # Should get 40 bonus for home state
        assert score >= 70


# -------------------- Playing Time Score Tests --------------------


class TestPlayingTimeScore:
    """Tests for playing time score calculation."""

    def test_starter_scores_100(self, engine):
        """Starter role scores 100."""
        offer = ContractOffer(
            team_id=1, aav=1, total_value=1, years=1, guaranteed=1, role="starter"
        )
        assert engine._calculate_playing_time_score(offer) == 100

    def test_rotational_scores_60(self, engine):
        """Rotational role scores 60."""
        offer = ContractOffer(
            team_id=1, aav=1, total_value=1, years=1, guaranteed=1, role="rotational"
        )
        assert engine._calculate_playing_time_score(offer) == 60

    def test_backup_scores_30(self, engine):
        """Backup role scores 30."""
        offer = ContractOffer(
            team_id=1, aav=1, total_value=1, years=1, guaranteed=1, role="backup"
        )
        assert engine._calculate_playing_time_score(offer) == 30


# -------------------- Persona Bonus Tests --------------------


class TestPersonaBonuses:
    """Tests for persona-specific bonus application."""

    def test_ring_chaser_contender_bonus(self, engine, contender_team, market_value_offer):
        """Ring Chaser gets +20 winning score for contender."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.RING_CHASER,
        )
        # contender_team.contender_score > 70
        winning_before = engine._calculate_winning_score(contender_team)

        scores = engine._apply_persona_bonuses(
            persona, contender_team, market_value_offer,
            money_score=80, winning_score=winning_before, location_score=50,
            playing_time_score=100, loyalty_score=0, market_score=90,
        )

        winning_after = scores[1]
        assert winning_after == min(100, winning_before + 20)

    def test_ring_chaser_no_bonus_non_contender(self, engine, rebuilding_team, market_value_offer):
        """Ring Chaser gets no bonus for non-contender."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.RING_CHASER,
        )
        # rebuilding_team.contender_score < 70
        winning_before = engine._calculate_winning_score(rebuilding_team)

        scores = engine._apply_persona_bonuses(
            persona, rebuilding_team, market_value_offer,
            money_score=80, winning_score=winning_before, location_score=50,
            playing_time_score=100, loyalty_score=0, market_score=30,
        )

        winning_after = scores[1]
        assert winning_after == winning_before  # No bonus

    def test_big_market_bonus(self, engine, contender_team, market_value_offer):
        """Big Market persona gets +25 for large market."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.BIG_MARKET,
        )
        # contender_team.market_size = 90 > 70

        scores = engine._apply_persona_bonuses(
            persona, contender_team, market_value_offer,
            money_score=80, winning_score=80, location_score=50,
            playing_time_score=100, loyalty_score=0, market_score=90,
        )

        market_after = scores[5]
        assert market_after == 100  # 90 + 25 capped at 100

    def test_competitor_starter_bonus(self, engine, contender_team):
        """Competitor gets +30 playing time for starter role."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.COMPETITOR,
        )
        offer = ContractOffer(
            team_id=17, aav=10_000_000, total_value=40_000_000,
            years=4, guaranteed=20_000_000, role="starter",
        )

        scores = engine._apply_persona_bonuses(
            persona, contender_team, offer,
            money_score=80, winning_score=80, location_score=50,
            playing_time_score=100, loyalty_score=0, market_score=90,
        )

        playing_time_after = scores[3]
        assert playing_time_after == 100  # 100 + 30 capped at 100

    def test_competitor_backup_penalty(self, engine, contender_team):
        """Competitor gets -30 playing time for backup role."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.COMPETITOR,
        )
        offer = ContractOffer(
            team_id=17, aav=10_000_000, total_value=40_000_000,
            years=4, guaranteed=20_000_000, role="backup",
        )

        scores = engine._apply_persona_bonuses(
            persona, contender_team, offer,
            money_score=80, winning_score=80, location_score=50,
            playing_time_score=30, loyalty_score=0, market_score=90,
        )

        playing_time_after = scores[3]
        assert playing_time_after == 0  # 30 - 30 = 0


# -------------------- Weighted Score Tests --------------------


class TestWeightedScore:
    """Tests for full weighted score calculation."""

    def test_money_focused_persona_values_money(
        self, engine, contender_team, market_value_offer
    ):
        """Money-focused persona scores higher with good offer."""
        money_persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.MONEY_FIRST,
            money_importance=90,
            winning_importance=20,
            location_importance=10,
            playing_time_importance=20,
            loyalty_importance=10,
            market_size_importance=10,
        )

        score = engine.calculate_team_score(
            money_persona, contender_team, market_value_offer
        )

        # Should score high because offer is at market (80 money score)
        # and money is heavily weighted
        assert score >= 70

    def test_winning_focused_persona_values_contender(
        self, engine, contender_team, market_value_offer
    ):
        """Winning-focused persona scores higher for contenders."""
        winning_persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.RING_CHASER,
            money_importance=20,
            winning_importance=90,
            location_importance=10,
            playing_time_importance=20,
            loyalty_importance=10,
            market_size_importance=10,
        )

        score = engine.calculate_team_score(
            winning_persona, contender_team, market_value_offer
        )

        # Should score high because team is a contender
        assert score >= 80

    def test_balanced_persona_moderate_score(
        self, engine, default_persona, contender_team, market_value_offer
    ):
        """Balanced persona scores moderately."""
        score = engine.calculate_team_score(
            default_persona, contender_team, market_value_offer
        )

        # Should be moderate (not extreme)
        assert 50 <= score <= 90


# -------------------- Acceptance Probability Tests --------------------


class TestAcceptanceProbability:
    """Tests for acceptance probability calculation."""

    def test_money_override_120_percent(self, engine, default_persona):
        """120%+ of market always 95% acceptance."""
        prob = engine.calculate_acceptance_probability(
            default_persona, team_score=30, offer_vs_market=1.25
        )
        assert prob == 0.95

    def test_money_override_110_percent_bonus(self, engine, default_persona):
        """110%+ of market gets +30% bonus."""
        # Base prob = 50 / 100 = 0.5
        # With +30% = 0.8
        prob = engine.calculate_acceptance_probability(
            default_persona, team_score=50, offer_vs_market=1.15
        )
        assert prob == 0.8

    def test_low_offer_penalty(self, engine, default_persona):
        """Below 80% market gets -40% penalty."""
        # Base prob = 70 / 100 = 0.7
        # With -40% = 0.3
        prob = engine.calculate_acceptance_probability(
            default_persona, team_score=70, offer_vs_market=0.75
        )
        assert prob == pytest.approx(0.30)

    def test_money_first_high_acceptance(self, engine):
        """Money First persona has high acceptance for market offers."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.MONEY_FIRST,
        )
        prob = engine.calculate_acceptance_probability(
            persona, team_score=50, offer_vs_market=1.05
        )
        assert prob >= 0.85

    def test_probability_clamped_high(self, engine, default_persona):
        """Probability capped at 0.95."""
        prob = engine.calculate_acceptance_probability(
            default_persona, team_score=100, offer_vs_market=1.15
        )
        # 1.0 + 0.30 would be 1.30, but capped at 0.95
        assert prob == 0.95

    def test_probability_clamped_low(self, engine, default_persona):
        """Probability floored at 0.05."""
        prob = engine.calculate_acceptance_probability(
            default_persona, team_score=10, offer_vs_market=0.70
        )
        # 0.10 - 0.40 would be -0.30, but floored at 0.05
        assert prob == 0.05


# -------------------- Concern Tests --------------------


class TestConcerns:
    """Tests for concern generation."""

    def test_winning_concern_for_non_contender(self, engine, rebuilding_team):
        """Player with high winning_importance concerned about non-contender."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.RING_CHASER,
            winning_importance=85,
        )
        offer = ContractOffer(
            team_id=5, aav=10_000_000, total_value=40_000_000,
            years=4, guaranteed=20_000_000,
        )

        concerns = engine.get_concerns(persona, rebuilding_team, offer)
        assert any("playoff" in c.lower() for c in concerns)

    def test_big_market_small_market_concern(self, engine, rebuilding_team):
        """Big Market persona concerned about small market."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.BIG_MARKET,
        )
        offer = ContractOffer(
            team_id=5, aav=10_000_000, total_value=40_000_000,
            years=4, guaranteed=20_000_000,
        )

        concerns = engine.get_concerns(persona, rebuilding_team, offer)
        assert any("market" in c.lower() for c in concerns)

    def test_competitor_backup_concern(self, engine, contender_team):
        """Competitor concerned about backup role."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.COMPETITOR,
        )
        offer = ContractOffer(
            team_id=17, aav=10_000_000, total_value=40_000_000,
            years=4, guaranteed=20_000_000, role="backup",
        )

        concerns = engine.get_concerns(persona, contender_team, offer)
        assert any("playing time" in c.lower() for c in concerns)

    def test_money_first_low_offer_concern(self, engine, contender_team):
        """Money First persona concerned about below-market offer."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.MONEY_FIRST,
        )
        offer = ContractOffer(
            team_id=17, aav=8_000_000, total_value=32_000_000,
            years=4, guaranteed=16_000_000,
            market_aav=10_000_000,  # 80% of market
        )

        concerns = engine.get_concerns(persona, contender_team, offer)
        assert any("top dollar" in c.lower() for c in concerns)

    def test_legacy_builder_always_concerned(self, engine, contender_team):
        """Legacy Builder always has commitment concern."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.LEGACY_BUILDER,
        )
        offer = ContractOffer(
            team_id=17, aav=15_000_000, total_value=60_000_000,
            years=4, guaranteed=30_000_000,
        )

        concerns = engine.get_concerns(persona, contender_team, offer)
        assert any("commitment" in c.lower() for c in concerns)


# -------------------- Offer Evaluation Tests --------------------


class TestOfferEvaluation:
    """Tests for multi-offer evaluation."""

    def test_evaluate_ranks_by_score(self, engine, default_persona, contender_team, rebuilding_team):
        """Offers ranked by team score (highest first)."""
        good_offer = ContractOffer(
            team_id=17, aav=12_000_000, total_value=48_000_000,
            years=4, guaranteed=24_000_000, market_aav=10_000_000, role="starter",
        )
        bad_offer = ContractOffer(
            team_id=5, aav=8_000_000, total_value=32_000_000,
            years=4, guaranteed=16_000_000, market_aav=10_000_000, role="backup",
        )

        offers = [(contender_team, good_offer), (rebuilding_team, bad_offer)]
        evaluations = engine.evaluate_all_offers(default_persona, offers)

        assert len(evaluations) == 2
        assert evaluations[0].team_id == 17  # Contender should be first
        assert evaluations[0].team_score >= evaluations[1].team_score

    def test_evaluation_includes_concerns(self, engine, rebuilding_team):
        """Evaluations include concerns."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.RING_CHASER,
            winning_importance=85,
        )
        offer = ContractOffer(
            team_id=5, aav=10_000_000, total_value=40_000_000,
            years=4, guaranteed=20_000_000,
        )

        evaluations = engine.evaluate_all_offers(persona, [(rebuilding_team, offer)])

        assert len(evaluations) == 1
        assert len(evaluations[0].concerns) > 0


# -------------------- Should Accept Tests --------------------


class TestShouldAccept:
    """Tests for should_accept_offer decision."""

    def test_should_accept_returns_tuple(
        self, engine, default_persona, contender_team, market_value_offer
    ):
        """should_accept_offer returns (bool, float, list)."""
        result = engine.should_accept_offer(
            default_persona, contender_team, market_value_offer
        )

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float)
        assert isinstance(result[2], list)

    def test_should_accept_high_probability_usually_accepts(self, engine, contender_team):
        """Very high probability usually accepts (statistical test)."""
        persona = PlayerPersona(
            player_id=1,
            persona_type=PersonaType.MONEY_FIRST,
        )
        offer = ContractOffer(
            team_id=17, aav=15_000_000, total_value=60_000_000,
            years=4, guaranteed=30_000_000, market_aav=10_000_000, role="starter",
        )

        # Run 100 trials
        accepts = sum(
            1 for _ in range(100)
            if engine.should_accept_offer(persona, contender_team, offer)[0]
        )

        # Should accept most of the time (>80 of 100)
        assert accepts > 80
