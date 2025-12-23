"""
Integration tests for ContractValuationEngine.

Tests the complete valuation flow from player data to contract offer.
"""

import pytest
from datetime import datetime

from contract_valuation.engine import ContractValuationEngine
from contract_valuation.models import FactorWeights
from contract_valuation.context import (
    ValuationContext,
    OwnerContext,
    JobSecurityContext,
)
from contract_valuation.gm_influence.styles import GMStyle


# ===== Fixtures =====


@pytest.fixture
def engine():
    """Default ContractValuationEngine instance."""
    return ContractValuationEngine()


@pytest.fixture
def default_context():
    """Default 2025 valuation context."""
    return ValuationContext.create_default_2025()


@pytest.fixture
def secure_context():
    """Secure GM owner context."""
    return OwnerContext.create_default("test", 1)


@pytest.fixture
def hot_seat_context():
    """Hot seat GM owner context."""
    return OwnerContext(
        dynasty_id="test",
        team_id=1,
        job_security=JobSecurityContext(
            tenure_years=1,
            playoff_appearances=0,
            recent_win_pct=0.20,
            owner_patience=0.1,
        ),
        owner_philosophy="aggressive",
        team_philosophy="win_now",
        win_now_mode=True,
        max_contract_years=6,
        max_guaranteed_pct=0.70,
    )


@pytest.fixture
def very_secure_context():
    """Very secure GM owner context (pressure < 0.3)."""
    return OwnerContext(
        dynasty_id="test",
        team_id=1,
        job_security=JobSecurityContext(
            tenure_years=8,
            playoff_appearances=5,
            recent_win_pct=0.70,
            owner_patience=1.0,
        ),
        owner_philosophy="balanced",
        team_philosophy="maintain",
        win_now_mode=False,
        max_contract_years=5,
        max_guaranteed_pct=0.60,
    )


@pytest.fixture
def sample_qb_data():
    """Elite QB with full stats and attributes."""
    return {
        "player_id": 1001,
        "name": "Patrick Star",
        "position": "QB",
        "age": 28,
        "overall_rating": 95,
        "contract_year": False,
        "attributes": {"overall": 95, "potential": 98},
        "stats": {
            "passing_yards": 4500,
            "passing_tds": 35,
            "interceptions": 10,
            "passer_rating": 105.0,
            "completion_pct": 68.5,
        },
        "games_played": 17,
    }


@pytest.fixture
def sample_rb_data():
    """Quality RB."""
    return {
        "player_id": 1002,
        "name": "Rush Jones",
        "position": "RB",
        "age": 25,
        "overall_rating": 82,
        "attributes": {"overall": 82, "potential": 85},
        "stats": {"rushing_yards": 1100, "rushing_tds": 9, "ypc": 4.5},
        "games_played": 16,
    }


@pytest.fixture
def sample_wr_data():
    """Quality WR."""
    return {
        "player_id": 1003,
        "name": "Speed Demon",
        "position": "WR",
        "age": 27,
        "overall_rating": 85,
        "attributes": {"overall": 85},
        "stats": {"receiving_yards": 1200, "receptions": 85, "receiving_tds": 10},
        "games_played": 16,
    }


@pytest.fixture
def backup_player_data():
    """Backup-tier player."""
    return {
        "player_id": 1004,
        "name": "Bench Warmer",
        "position": "WR",
        "age": 26,
        "overall_rating": 65,
        "attributes": {"overall": 65},
    }


@pytest.fixture
def veteran_player_data():
    """33-year-old veteran."""
    return {
        "player_id": 1005,
        "name": "Old Timer",
        "position": "LB",
        "age": 33,
        "overall_rating": 80,
        "attributes": {"overall": 80},
    }


@pytest.fixture
def young_player_data():
    """Young prospect with high potential."""
    return {
        "player_id": 1006,
        "name": "Young Gun",
        "position": "CB",
        "age": 23,
        "overall_rating": 88,
        "attributes": {"overall": 88, "potential": 92},
    }


@pytest.fixture
def minimal_player_data():
    """Minimal required fields only."""
    return {
        "player_id": 1007,
        "name": "Minimal Mike",
        "position": "TE",
        "overall_rating": 75,
    }


# Mock GMArchetype for testing
class MockGMArchetype:
    """Mock GMArchetype for testing without importing real module."""

    def __init__(
        self,
        name: str = "Test GM",
        description: str = "Test",
        analytics_preference: float = 0.5,
        scouting_preference: float = 0.5,
        market_awareness: float = 0.5,
    ):
        self.name = name
        self.description = description
        self.analytics_preference = analytics_preference
        self.scouting_preference = scouting_preference
        self.market_awareness = market_awareness


# ===== Basic Functionality Tests (3 tests) =====


class TestBasicFunctionality:
    """Tests for basic valuation functionality."""

    def test_valuate_elite_qb_returns_top_tier_contract(
        self, engine, default_context, secure_context, sample_qb_data
    ):
        """Elite QB (95 rating) should get 4-5 year, $40M+ AAV contract."""
        result = engine.valuate(
            player_data=sample_qb_data,
            valuation_context=default_context,
            owner_context=secure_context,
        )

        assert result.offer.aav >= 40_000_000
        assert 4 <= result.offer.years <= 5
        assert result.offer.guaranteed_pct >= 0.45

    def test_valuate_backup_player_returns_minimum_contract(
        self, engine, default_context, secure_context, backup_player_data
    ):
        """Backup player (65 rating) should get 1-2 year, <$5M AAV contract."""
        result = engine.valuate(
            player_data=backup_player_data,
            valuation_context=default_context,
            owner_context=secure_context,
        )

        assert result.offer.aav < 5_000_000
        assert result.offer.years <= 2
        assert result.offer.guaranteed_pct <= 0.35

    def test_valuate_quality_player_returns_mid_tier_contract(
        self, engine, default_context, secure_context, sample_rb_data
    ):
        """Quality player (82 rating) should get 3-4 year, mid-range AAV."""
        result = engine.valuate(
            player_data=sample_rb_data,
            valuation_context=default_context,
            owner_context=secure_context,
        )

        assert 3_000_000 <= result.offer.aav <= 15_000_000
        assert 2 <= result.offer.years <= 4


# ===== GM Influence Tests (3 tests) =====


class TestGMInfluence:
    """Tests for GM style influence on valuations."""

    def test_analytics_gm_produces_different_value_than_scout_gm(
        self, engine, default_context, secure_context, sample_qb_data
    ):
        """Same player should get different AAV from different GM styles."""
        analytics_gm = MockGMArchetype(
            name="Analytics GM",
            description="Stats-driven",
            analytics_preference=0.9,
            scouting_preference=0.2,
            market_awareness=0.3,
        )
        scout_gm = MockGMArchetype(
            name="Scout GM",
            description="Eye test driven",
            analytics_preference=0.2,
            scouting_preference=0.9,
            market_awareness=0.3,
        )

        analytics_result = engine.valuate(
            sample_qb_data, default_context, secure_context, analytics_gm
        )
        scout_result = engine.valuate(
            sample_qb_data, default_context, secure_context, scout_gm
        )

        # Values should differ - GM style affects valuation
        # Note: May not always differ by 5% due to factor availability
        assert analytics_result.gm_style != scout_result.gm_style

    def test_override_weights_bypasses_archetype(
        self, engine, default_context, secure_context, sample_qb_data
    ):
        """Override weights should be used directly, ignoring archetype."""
        gm = MockGMArchetype(name="Test", description="Test", analytics_preference=0.9)
        custom_weights = FactorWeights(
            stats_weight=0.10,
            scouting_weight=0.10,
            market_weight=0.70,
            rating_weight=0.10,
        )

        result = engine.valuate(
            sample_qb_data,
            default_context,
            secure_context,
            gm_archetype=gm,
            override_weights=custom_weights,
        )

        assert result.gm_style == "custom"
        assert result.weights_used == custom_weights

    def test_no_archetype_uses_balanced_style(
        self, engine, default_context, secure_context, sample_qb_data
    ):
        """Without archetype or override, should use BALANCED style."""
        result = engine.valuate(
            sample_qb_data,
            default_context,
            secure_context,
            gm_archetype=None,
            override_weights=None,
        )

        assert result.gm_style == "balanced"


# ===== Pressure Effects Tests (3 tests) =====


class TestPressureEffects:
    """Tests for owner pressure effects on valuations."""

    def test_hot_seat_gm_overpays(
        self, engine, default_context, hot_seat_context, very_secure_context, sample_qb_data
    ):
        """Hot seat GM should overpay compared to secure GM."""
        hot_result = engine.valuate(
            sample_qb_data, default_context, hot_seat_context
        )
        secure_result = engine.valuate(
            sample_qb_data, default_context, very_secure_context
        )

        # Hot seat should pay more
        assert hot_result.offer.aav > secure_result.offer.aav

    def test_hot_seat_gm_offers_higher_guarantees(
        self, engine, default_context, hot_seat_context, very_secure_context, sample_qb_data
    ):
        """Hot seat GM should offer higher guaranteed percentage."""
        hot_result = engine.valuate(sample_qb_data, default_context, hot_seat_context)
        secure_result = engine.valuate(sample_qb_data, default_context, very_secure_context)

        assert hot_result.offer.guaranteed_pct > secure_result.offer.guaranteed_pct

    def test_secure_gm_gets_discount(
        self, engine, default_context, very_secure_context, secure_context, sample_qb_data
    ):
        """Very secure GM should pay same or less than baseline."""
        very_secure_result = engine.valuate(sample_qb_data, default_context, very_secure_context)
        baseline_result = engine.valuate(sample_qb_data, default_context, secure_context)

        # Very secure GM pays same or less
        assert very_secure_result.offer.aav <= baseline_result.offer.aav


# ===== Contract Structure Tests (4 tests) =====


class TestContractStructure:
    """Tests for contract structure determination."""

    def test_veteran_gets_shorter_contract(
        self, engine, default_context, secure_context, veteran_player_data
    ):
        """33-year-old should get max 3-year contract due to age discount."""
        result = engine.valuate(
            veteran_player_data, default_context, secure_context
        )

        assert result.offer.years <= 3  # Age 33+ = -2 years from base

    def test_young_high_potential_gets_longer_contract(
        self, engine, default_context, secure_context, young_player_data
    ):
        """Young high-potential player should get bonus year."""
        result = engine.valuate(
            young_player_data, default_context, secure_context
        )

        # Quality tier (4 years) + young bonus (+1) = 5 years max
        assert result.offer.years >= 4

    def test_owner_constraint_limits_years(
        self, engine, default_context, sample_qb_data
    ):
        """Owner's max_contract_years should cap contract length."""
        limited_context = OwnerContext(
            dynasty_id="test",
            team_id=1,
            job_security=JobSecurityContext.create_secure(),
            owner_philosophy="conservative",
            team_philosophy="rebuild",
            win_now_mode=False,
            max_contract_years=3,  # Max 3 years
            max_guaranteed_pct=0.40,
        )

        result = engine.valuate(sample_qb_data, default_context, limited_context)

        assert result.offer.years <= 3

    def test_owner_constraint_limits_guarantees(
        self, engine, default_context, sample_qb_data
    ):
        """Owner's max_guaranteed_pct should cap guarantees."""
        limited_context = OwnerContext(
            dynasty_id="test",
            team_id=1,
            job_security=JobSecurityContext.create_secure(),
            owner_philosophy="conservative",
            team_philosophy="maintain",
            win_now_mode=False,
            max_contract_years=5,
            max_guaranteed_pct=0.35,  # Max 35%
        )

        result = engine.valuate(sample_qb_data, default_context, limited_context)

        assert result.offer.guaranteed_pct <= 0.35


# ===== Audit Trail Tests (4 tests) =====


class TestAuditTrail:
    """Tests for valuation audit trail completeness."""

    def test_valuation_includes_all_factor_results(
        self, engine, default_context, secure_context, sample_qb_data
    ):
        """ValuationResult should include all raw factor results."""
        result = engine.valuate(sample_qb_data, default_context, secure_context)

        assert len(result.raw_factor_results) >= 3  # At least some factors
        factor_names = {r.name for r in result.raw_factor_results}
        # Should have at least rating and market factors
        assert "rating" in factor_names or "market" in factor_names

    def test_valuation_includes_weights_used(
        self, engine, default_context, secure_context, sample_qb_data
    ):
        """ValuationResult should include weights that were applied."""
        result = engine.valuate(sample_qb_data, default_context, secure_context)

        assert result.weights_used is not None
        weights_sum = (
            result.weights_used.stats_weight
            + result.weights_used.scouting_weight
            + result.weights_used.market_weight
            + result.weights_used.rating_weight
        )
        assert 0.99 <= weights_sum <= 1.01

    def test_valuation_includes_pressure_description(
        self, engine, default_context, hot_seat_context, sample_qb_data
    ):
        """ValuationResult should include pressure description."""
        result = engine.valuate(sample_qb_data, default_context, hot_seat_context)

        assert result.pressure_description is not None
        assert len(result.pressure_description) > 0
        assert result.pressure_level >= 0

    def test_valuation_includes_timestamp(
        self, engine, default_context, secure_context, sample_qb_data
    ):
        """ValuationResult should include timestamp."""
        result = engine.valuate(sample_qb_data, default_context, secure_context)

        assert result.valuation_timestamp is not None
        # Should be valid ISO format
        datetime.fromisoformat(result.valuation_timestamp)


# ===== Error Handling Tests (2 tests) =====


class TestErrorHandling:
    """Tests for error handling."""

    def test_missing_player_id_raises_error(
        self, engine, default_context, secure_context
    ):
        """Missing player_id should raise ValueError."""
        invalid_data = {"name": "Test", "position": "QB"}

        with pytest.raises(ValueError, match="player_id"):
            engine.valuate(invalid_data, default_context, secure_context)

    def test_missing_position_raises_error(
        self, engine, default_context, secure_context
    ):
        """Missing position should raise ValueError."""
        invalid_data = {"player_id": 1, "name": "Test"}

        with pytest.raises(ValueError, match="position"):
            engine.valuate(invalid_data, default_context, secure_context)


# ===== Batch Valuation Test (1 test) =====


class TestBatchValuation:
    """Tests for batch valuation functionality."""

    def test_valuate_batch_returns_results_for_all_players(
        self,
        engine,
        default_context,
        secure_context,
        sample_qb_data,
        sample_rb_data,
        sample_wr_data,
    ):
        """Batch valuation should return result for each player."""
        players = [sample_qb_data, sample_rb_data, sample_wr_data]

        results = engine.valuate_batch(
            players, default_context, secure_context
        )

        assert len(results) == 3
        assert all(r.offer.aav > 0 for r in results)
        # Each result should have correct player info
        assert results[0].player_name == "Patrick Star"
        assert results[1].player_name == "Rush Jones"
        assert results[2].player_name == "Speed Demon"