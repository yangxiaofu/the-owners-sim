"""
Tests for FreeAgencyManager

Integration tests for free agency operations.
"""

import pytest
from offseason.free_agency_manager import FreeAgencyManager
from transactions.personality_modifiers import TeamContext


class TestFreeAgencyManagerIntegration:
    """Integration tests for FreeAgencyManager"""

    @pytest.fixture
    def manager(self):
        """FreeAgencyManager instance"""
        return FreeAgencyManager(
            database_path=":memory:",
            dynasty_id="test_dynasty",
            season_year=2024,
            enable_persistence=False,
            verbose_logging=False
        )

    @pytest.fixture
    def mock_standings(self):
        """Mock standings data"""
        return [
            {'team_id': 1, 'wins': 11, 'losses': 6, 'ties': 0},  # Contender
            {'team_id': 2, 'wins': 8, 'losses': 9, 'ties': 0},   # Bubble
            {'team_id': 3, 'wins': 3, 'losses': 14, 'ties': 0}   # Rebuilder
        ]

    # ========== _get_team_context() Integration Tests ==========

    def test_get_team_context_integration(self, manager, mock_standings, monkeypatch):
        """Integration test: _get_team_context() returns complete TeamContext"""
        # Mock DatabaseAPI.get_standings
        monkeypatch.setattr(
            manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )

        # Mock CapCalculator.calculate_team_cap_space
        monkeypatch.setattr(
            manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 25_000_000
        )

        # Mock TeamNeedsAnalyzer.analyze_team_needs
        monkeypatch.setattr(
            manager.needs_analyzer,
            'analyze_team_needs',
            lambda *args, **kwargs: [
                {'position': 'quarterback', 'urgency': 0.9},
                {'position': 'edge_rusher', 'urgency': 0.8},
                {'position': 'cornerback', 'urgency': 0.7}
            ]
        )

        # Call _get_team_context
        context = manager._get_team_context(team_id=1)

        # Verify TeamContext is returned
        assert isinstance(context, TeamContext)
        assert context.team_id == 1
        assert context.season == 2024
        assert context.wins == 11
        assert context.losses == 6
        assert context.cap_space == 25_000_000
        assert 0.09 < context.cap_percentage < 0.10  # 25M / 255.5M ≈ 9.8%
        assert context.top_needs == ['quarterback', 'edge_rusher', 'cornerback']
        assert context.is_offseason == True

    def test_get_team_context_uses_offseason_roster_mode(self, manager, mock_standings, monkeypatch):
        """Integration test: _get_team_context() uses offseason roster mode (top-51)"""
        monkeypatch.setattr(
            manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )

        # Track roster_mode parameter
        called_with = {}

        def mock_cap_space(*args, **kwargs):
            called_with['roster_mode'] = kwargs.get('roster_mode')
            return 20_000_000

        monkeypatch.setattr(
            manager.context_service.cap_calc,
            'calculate_team_cap_space',
            mock_cap_space
        )

        # Call _get_team_context
        context = manager._get_team_context(team_id=1)

        # Verify roster_mode="offseason" was used (top-51 rule)
        assert called_with['roster_mode'] == "offseason"
        assert context.cap_space == 20_000_000

    def test_get_team_context_playoff_contender(self, manager, mock_standings, monkeypatch):
        """Integration test: _get_team_context() identifies playoff contenders"""
        monkeypatch.setattr(
            manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 10_000_000
        )

        # Team 1: 11-6 record
        context = manager._get_team_context(team_id=1)

        # Should be identified as playoff contender
        assert context.is_playoff_contender == True
        assert context.is_rebuilding == False

    def test_get_team_context_rebuilding_team(self, manager, mock_standings, monkeypatch):
        """Integration test: _get_team_context() identifies rebuilding teams"""
        monkeypatch.setattr(
            manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 50_000_000
        )

        # Team 3: 3-14 record
        context = manager._get_team_context(team_id=3)

        # Should be identified as rebuilding
        assert context.is_rebuilding == True
        assert context.is_playoff_contender == False

    def test_get_team_context_uses_needs_analyzer(self, manager, mock_standings, monkeypatch):
        """Integration test: _get_team_context() uses FreeAgencyManager's needs_analyzer"""
        monkeypatch.setattr(
            manager.context_service.db_api,
            'get_standings',
            lambda *args, **kwargs: mock_standings
        )
        monkeypatch.setattr(
            manager.context_service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 15_000_000
        )

        # Track if needs_analyzer was called
        called = {'count': 0}

        def mock_analyze_needs(*args, **kwargs):
            called['count'] += 1
            return [
                {'position': 'safety', 'urgency': 0.85},
                {'position': 'linebacker', 'urgency': 0.75}
            ]

        monkeypatch.setattr(
            manager.needs_analyzer,
            'analyze_team_needs',
            mock_analyze_needs
        )

        # Call _get_team_context
        context = manager._get_team_context(team_id=2)

        # Verify needs_analyzer was used
        assert called['count'] == 1
        assert context.top_needs == ['safety', 'linebacker']