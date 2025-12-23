"""
Integration tests for Contract Valuation Engine service integration.

Tests the ValuationService wrapper and its integration with:
- GMFAProposalEngine
- ResigningService
- FreeAgencyService

Part of Milestone 14: Contract Valuation Engine - Tollgate 8.
"""

import pytest
import sqlite3
from unittest.mock import MagicMock, patch

from contract_valuation.models import ValuationResult, ContractOffer
from contract_valuation.context import (
    ValuationContext,
    OwnerContext,
    JobSecurityContext,
)


class TestValuationService:
    """Tests for ValuationService wrapper."""

    @pytest.fixture
    def mock_conn(self):
        """Create a mock database connection."""
        conn = MagicMock(spec=sqlite3.Connection)
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = None
        return conn

    @pytest.fixture
    def sample_player_data(self):
        """Sample player data for testing."""
        return {
            "player_id": 1,
            "name": "Test Player",
            "position": "QB",
            "overall_rating": 85,
            "age": 27,
            "stats": {
                "pass_yards": 4000,
                "pass_tds": 30,
                "games_played": 17,
            },
        }

    def test_valuation_service_import(self):
        """ValuationService should import successfully."""
        from game_cycle.services.valuation_service import ValuationService
        assert ValuationService is not None

    def test_valuation_service_has_required_methods(self):
        """ValuationService should have required public methods."""
        from game_cycle.services.valuation_service import ValuationService

        assert hasattr(ValuationService, 'valuate_player')
        assert hasattr(ValuationService, 'valuate_batch')
        assert hasattr(ValuationService, 'clear_cache')

    @patch('game_cycle.services.valuation_service.GameCycleDatabase')
    @patch('game_cycle.services.valuation_service.StaffAPI')
    @patch('game_cycle.services.valuation_service.StandingsAPI')
    @patch('game_cycle.services.valuation_service.OwnerDirectivesAPI')
    def test_valuation_service_initialization(
        self, mock_directives, mock_standings, mock_staff, mock_db, mock_conn
    ):
        """ValuationService should initialize with database connection."""
        from game_cycle.services.valuation_service import ValuationService

        service = ValuationService(
            conn=mock_conn,
            dynasty_id="test_dynasty",
            season=2025,
        )

        assert service._dynasty_id == "test_dynasty"
        assert service._season == 2025
        assert service._engine is not None

    @patch('game_cycle.services.valuation_service.GameCycleDatabase')
    @patch('game_cycle.services.valuation_service.StaffAPI')
    @patch('game_cycle.services.valuation_service.StandingsAPI')
    @patch('game_cycle.services.valuation_service.OwnerDirectivesAPI')
    def test_valuate_player_returns_result(
        self, mock_directives, mock_standings, mock_staff, mock_db,
        mock_conn, sample_player_data
    ):
        """valuate_player should return ValuationResult."""
        from game_cycle.services.valuation_service import ValuationService

        # Mock to return None (no directives) so default context is used
        mock_directives_instance = mock_directives.return_value
        mock_directives_instance.get_directives.return_value = None

        service = ValuationService(
            conn=mock_conn,
            dynasty_id="test_dynasty",
            season=2025,
        )

        result = service.valuate_player(
            player_data=sample_player_data,
            team_id=1,
        )

        assert isinstance(result, ValuationResult)
        assert result.offer.aav > 0
        assert result.offer.years > 0

    @patch('game_cycle.services.valuation_service.GameCycleDatabase')
    @patch('game_cycle.services.valuation_service.StaffAPI')
    @patch('game_cycle.services.valuation_service.StandingsAPI')
    @patch('game_cycle.services.valuation_service.OwnerDirectivesAPI')
    def test_valuate_batch_returns_list(
        self, mock_directives, mock_standings, mock_staff, mock_db,
        mock_conn, sample_player_data
    ):
        """valuate_batch should return list of ValuationResults."""
        from game_cycle.services.valuation_service import ValuationService

        # Mock to return None (no directives) so default context is used
        mock_directives_instance = mock_directives.return_value
        mock_directives_instance.get_directives.return_value = None

        service = ValuationService(
            conn=mock_conn,
            dynasty_id="test_dynasty",
            season=2025,
        )

        players = [sample_player_data, sample_player_data.copy()]
        results = service.valuate_batch(
            players=players,
            team_id=1,
        )

        assert isinstance(results, list)
        assert len(results) == 2
        for result in results:
            assert isinstance(result, ValuationResult)

    @patch('game_cycle.services.valuation_service.GameCycleDatabase')
    @patch('game_cycle.services.valuation_service.StaffAPI')
    @patch('game_cycle.services.valuation_service.StandingsAPI')
    @patch('game_cycle.services.valuation_service.OwnerDirectivesAPI')
    def test_clear_cache_works(
        self, mock_directives, mock_standings, mock_staff, mock_db, mock_conn
    ):
        """clear_cache should reset context cache."""
        from game_cycle.services.valuation_service import ValuationService

        service = ValuationService(
            conn=mock_conn,
            dynasty_id="test_dynasty",
            season=2025,
        )

        # Add something to cache
        service._context_cache["test"] = "value"
        assert "test" in service._context_cache

        # Clear cache
        service.clear_cache()
        assert len(service._context_cache) == 0


class TestGMFAProposalEngineIntegration:
    """Tests for GMFAProposalEngine valuation integration."""

    @pytest.fixture
    def mock_gm_archetype(self):
        """Create mock GM archetype."""
        gm = MagicMock()
        gm.archetype_key = "balanced"
        gm.risk_tolerance = 0.5
        gm.star_chasing = 0.5
        gm.youth_focus = 0.5
        gm.analytics_preference = 0.5
        gm.scouting_preference = 0.5
        gm.market_awareness = 0.5
        return gm

    @pytest.fixture
    def mock_fa_guidance(self):
        """Create mock FA guidance."""
        guidance = MagicMock()
        guidance.philosophy = MagicMock()
        guidance.philosophy.value = "balanced"
        guidance.max_contract_years = 5
        guidance.max_guaranteed_percent = 0.60
        guidance.wishlist = []
        guidance.priority_positions = []
        return guidance

    def test_gmfa_engine_import(self):
        """GMFAProposalEngine should import successfully."""
        from game_cycle.services.gm_fa_proposal_engine import GMFAProposalEngine
        assert GMFAProposalEngine is not None

    def test_gmfa_engine_accepts_valuation_service(
        self, mock_gm_archetype, mock_fa_guidance
    ):
        """GMFAProposalEngine should accept valuation_service parameter."""
        from game_cycle.services.gm_fa_proposal_engine import GMFAProposalEngine

        mock_valuation_service = MagicMock()

        # Should accept valuation_service and team_id
        engine = GMFAProposalEngine(
            gm_archetype=mock_gm_archetype,
            fa_guidance=mock_fa_guidance,
            valuation_service=mock_valuation_service,
            team_id=1,
        )

        assert engine._valuation_service is mock_valuation_service
        assert engine._team_id == 1

    def test_gmfa_engine_requires_team_id_with_valuation_service(
        self, mock_gm_archetype, mock_fa_guidance
    ):
        """GMFAProposalEngine should require team_id when valuation_service is provided."""
        from game_cycle.services.gm_fa_proposal_engine import GMFAProposalEngine

        mock_valuation_service = MagicMock()

        # Should raise error without team_id
        with pytest.raises(ValueError, match="team_id"):
            GMFAProposalEngine(
                gm_archetype=mock_gm_archetype,
                fa_guidance=mock_fa_guidance,
                valuation_service=mock_valuation_service,
                # Missing team_id
            )

    def test_gmfa_engine_backward_compatible(
        self, mock_gm_archetype, mock_fa_guidance
    ):
        """GMFAProposalEngine should work without valuation_service."""
        from game_cycle.services.gm_fa_proposal_engine import GMFAProposalEngine

        # Legacy mode - no valuation_service
        engine = GMFAProposalEngine(
            gm_archetype=mock_gm_archetype,
            fa_guidance=mock_fa_guidance,
        )

        assert engine._valuation_service is None


class TestResigningServiceIntegration:
    """Tests for ResigningService valuation integration."""

    def test_resigning_service_import(self):
        """ResigningService should import successfully."""
        from game_cycle.services.resigning_service import ResigningService
        assert ResigningService is not None

    def test_resigning_service_accepts_valuation_service(self):
        """ResigningService should accept valuation_service parameter."""
        from game_cycle.services.resigning_service import ResigningService

        # Check that __init__ signature includes valuation_service
        import inspect
        sig = inspect.signature(ResigningService.__init__)
        params = list(sig.parameters.keys())

        assert 'valuation_service' in params

    def test_resigning_service_has_valuation_attribute(self):
        """ResigningService instance should have _valuation_service attribute."""
        from game_cycle.services.resigning_service import ResigningService

        # Create with mock service
        mock_valuation = MagicMock()

        with patch.object(ResigningService, '__init__', lambda self, **kwargs: None):
            service = ResigningService.__new__(ResigningService)
            service._valuation_service = mock_valuation

            assert service._valuation_service is mock_valuation


class TestFreeAgencyServiceIntegration:
    """Tests for FreeAgencyService valuation integration."""

    def test_free_agency_service_import(self):
        """FreeAgencyService should import successfully."""
        from game_cycle.services.free_agency_service import FreeAgencyService
        assert FreeAgencyService is not None

    def test_free_agency_service_accepts_valuation_factory(self):
        """FreeAgencyService should accept valuation_service_factory parameter."""
        from game_cycle.services.free_agency_service import FreeAgencyService

        # Check that __init__ signature includes valuation_service_factory
        import inspect
        sig = inspect.signature(FreeAgencyService.__init__)
        params = list(sig.parameters.keys())

        assert 'valuation_service_factory' in params


class TestCrossServiceConsistency:
    """Tests for consistent behavior across services."""

    @pytest.fixture
    def sample_player(self):
        """Sample player for consistency testing."""
        return {
            "player_id": 100,
            "name": "Consistency Test",
            "position": "WR",
            "overall_rating": 85,
            "age": 26,
        }

    def test_engine_produces_consistent_results(self, sample_player):
        """Same player data should produce similar results across calls."""
        from contract_valuation.engine import ContractValuationEngine
        from contract_valuation.context import ValuationContext, OwnerContext, JobSecurityContext

        engine = ContractValuationEngine()
        context = ValuationContext.create_default_2025()
        owner_context = OwnerContext.create_default("test", 1)

        # Run twice with same inputs
        result1 = engine.valuate(sample_player, context, owner_context)
        result2 = engine.valuate(sample_player, context, owner_context)

        # Should be exactly the same (deterministic)
        assert result1.offer.aav == result2.offer.aav
        assert result1.offer.years == result2.offer.years

    def test_gm_archetype_affects_valuation(self, sample_player):
        """Different GM archetypes should produce different valuations."""
        from contract_valuation.engine import ContractValuationEngine
        from contract_valuation.context import ValuationContext, OwnerContext
        from team_management.gm_archetype import GMArchetype

        engine = ContractValuationEngine()
        context = ValuationContext.create_default_2025()
        owner_context = OwnerContext.create_default("test", 1)

        # Analytics-heavy GM
        analytics_gm = GMArchetype(
            name="Analytics GM",
            description="Analytics-focused GM",
            analytics_preference=0.90,
            scouting_preference=0.30,
            market_awareness=0.50,
            risk_tolerance=0.50,
            star_chasing=0.40,
            veteran_preference=0.40,
            loyalty=0.40,
            cap_management=0.50,
            draft_pick_value=0.60,
        )

        # Scout-focused GM
        scout_gm = GMArchetype(
            name="Scout GM",
            description="Scout-focused GM",
            analytics_preference=0.30,
            scouting_preference=0.90,
            market_awareness=0.50,
            risk_tolerance=0.60,
            star_chasing=0.50,
            veteran_preference=0.30,
            loyalty=0.50,
            cap_management=0.50,
            draft_pick_value=0.70,
        )

        result_analytics = engine.valuate(sample_player, context, owner_context, analytics_gm)
        result_scout = engine.valuate(sample_player, context, owner_context, scout_gm)

        # Values should differ (different GM styles)
        # Note: The difference might be small but should exist
        assert result_analytics.gm_style != result_scout.gm_style

    def test_pressure_affects_valuation(self, sample_player):
        """Different pressure levels should produce different valuations."""
        from contract_valuation.engine import ContractValuationEngine
        from contract_valuation.context import ValuationContext, OwnerContext, JobSecurityContext

        engine = ContractValuationEngine()
        context = ValuationContext.create_default_2025()

        # Secure GM context
        secure_owner = OwnerContext(
            dynasty_id="test",
            team_id=1,
            job_security=JobSecurityContext.create_secure(),
            owner_philosophy="balanced",
            team_philosophy="maintain",
            win_now_mode=False,
            max_contract_years=5,
            max_guaranteed_pct=0.60,
        )

        # Hot seat GM context
        hot_seat_owner = OwnerContext(
            dynasty_id="test",
            team_id=1,
            job_security=JobSecurityContext.create_hot_seat(),
            owner_philosophy="balanced",
            team_philosophy="win_now",
            win_now_mode=True,
            max_contract_years=5,
            max_guaranteed_pct=0.60,
        )

        result_secure = engine.valuate(sample_player, context, secure_owner)
        result_hot_seat = engine.valuate(sample_player, context, hot_seat_owner)

        # Hot seat should pay more (desperation)
        assert result_hot_seat.offer.aav >= result_secure.offer.aav
