"""
Tests for TeamContextService

Verifies team context building from database state.
"""

import pytest
from transactions.team_context_service import TeamContextService
from transactions.personality_modifiers import TeamContext


class TestTeamContextService:
    """Tests for TeamContextService"""

    @pytest.fixture
    def service(self):
        """TeamContextService instance"""
        return TeamContextService(
            database_path=":memory:",
            dynasty_id="test_dynasty"
        )

    @pytest.fixture
    def mock_standings(self):
        """Mock standings data"""
        return [
            {'team_id': 1, 'wins': 11, 'losses': 6, 'ties': 0},  # Contender
            {'team_id': 2, 'wins': 8, 'losses': 9, 'ties': 0},   # Bubble
            {'team_id': 3, 'wins': 3, 'losses': 14, 'ties': 0}   # Rebuilder
        ]

    # ========== get_team_record() Tests ==========

    def test_get_team_record_contender(self, service, mock_standings, monkeypatch):
        """Get record for contending team (11-6)"""
        monkeypatch.setattr(service.db_api, 'get_standings', lambda *args, **kwargs: mock_standings)

        record = service.get_team_record(team_id=1, season=2024)

        assert record['wins'] == 11
        assert record['losses'] == 6
        assert record['ties'] == 0

    def test_get_team_record_rebuilder(self, service, mock_standings, monkeypatch):
        """Get record for rebuilding team (3-14)"""
        monkeypatch.setattr(service.db_api, 'get_standings', lambda *args, **kwargs: mock_standings)

        record = service.get_team_record(team_id=3, season=2024)

        assert record['wins'] == 3
        assert record['losses'] == 14
        assert record['ties'] == 0

    def test_get_team_record_team_not_found(self, service, monkeypatch):
        """Fallback when team not in standings (preseason)"""
        monkeypatch.setattr(service.db_api, 'get_standings', lambda *args, **kwargs: [])

        record = service.get_team_record(team_id=99, season=2024)

        # Should return zeros
        assert record == {'wins': 0, 'losses': 0, 'ties': 0}

    # ========== get_team_cap_space() Tests ==========

    def test_get_team_cap_space_offseason(self, service, monkeypatch):
        """Get cap space with offseason (top-51) roster mode"""
        monkeypatch.setattr(
            service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 25_000_000
        )

        cap_space = service.get_team_cap_space(
            team_id=1,
            season=2024,
            roster_mode="offseason"
        )

        assert cap_space == 25_000_000

    def test_get_team_cap_space_regular_season(self, service, monkeypatch):
        """Get cap space with regular season (53-man) roster mode"""
        monkeypatch.setattr(
            service.cap_calc,
            'calculate_team_cap_space',
            lambda *args, **kwargs: 20_000_000
        )

        cap_space = service.get_team_cap_space(
            team_id=1,
            season=2024,
            roster_mode="regular_season"
        )

        assert cap_space == 20_000_000

    # ========== build_team_context() Tests ==========

    def test_build_team_context_complete(self, service, mock_standings, monkeypatch):
        """Build complete TeamContext with all fields"""
        # Mock dependencies
        monkeypatch.setattr(service.db_api, 'get_standings', lambda *args, **kwargs: mock_standings)
        monkeypatch.setattr(service.cap_calc, 'calculate_team_cap_space', lambda *args, **kwargs: 20_000_000)

        # Mock needs analyzer
        mock_needs_analyzer = type('MockNeedsAnalyzer', (), {
            'analyze_team_needs': lambda *args, **kwargs: [
                {'position': 'quarterback', 'urgency': 0.9},
                {'position': 'edge_rusher', 'urgency': 0.8},
                {'position': 'cornerback', 'urgency': 0.7}
            ]
        })()

        context = service.build_team_context(
            team_id=1,
            season=2024,
            needs_analyzer=mock_needs_analyzer,
            is_offseason=True,
            roster_mode="offseason"
        )

        # Verify all fields
        assert context.team_id == 1
        assert context.season == 2024
        assert context.wins == 11
        assert context.losses == 6
        assert context.cap_space == 20_000_000
        assert 0.07 < context.cap_percentage < 0.08  # 20M / 255.5M ≈ 7.8%
        assert context.top_needs == ['quarterback', 'edge_rusher', 'cornerback']
        assert context.is_offseason == True

    def test_build_team_context_without_needs_analyzer(self, service, mock_standings, monkeypatch):
        """Build TeamContext without needs analyzer (empty top_needs)"""
        monkeypatch.setattr(service.db_api, 'get_standings', lambda *args, **kwargs: mock_standings)
        monkeypatch.setattr(service.cap_calc, 'calculate_team_cap_space', lambda *args, **kwargs: 10_000_000)

        context = service.build_team_context(
            team_id=2,
            season=2024,
            needs_analyzer=None,  # No needs provided
            is_offseason=True
        )

        assert context.team_id == 2
        assert context.top_needs == []  # Empty without analyzer

    def test_build_team_context_win_percentage(self, service, mock_standings, monkeypatch):
        """Verify TeamContext computes win_percentage correctly"""
        monkeypatch.setattr(service.db_api, 'get_standings', lambda *args, **kwargs: mock_standings)
        monkeypatch.setattr(service.cap_calc, 'calculate_team_cap_space', lambda *args, **kwargs: 5_000_000)

        context = service.build_team_context(team_id=1, season=2024)

        # Team 1: 11 wins, 6 losses = 11/17 ≈ 0.647
        assert 0.64 < context.win_percentage < 0.65

    def test_build_team_context_is_playoff_contender(self, service, mock_standings, monkeypatch):
        """Verify TeamContext identifies playoff contenders"""
        monkeypatch.setattr(service.db_api, 'get_standings', lambda *args, **kwargs: mock_standings)
        monkeypatch.setattr(service.cap_calc, 'calculate_team_cap_space', lambda *args, **kwargs: 5_000_000)

        context = service.build_team_context(team_id=1, season=2024)

        # Team 1: 11-6 (64.7% win_pct) should be playoff contender
        assert context.is_playoff_contender == True

    def test_build_team_context_is_rebuilding(self, service, mock_standings, monkeypatch):
        """Verify TeamContext identifies rebuilding teams"""
        monkeypatch.setattr(service.db_api, 'get_standings', lambda *args, **kwargs: mock_standings)
        monkeypatch.setattr(service.cap_calc, 'calculate_team_cap_space', lambda *args, **kwargs: 50_000_000)

        context = service.build_team_context(team_id=3, season=2024)

        # Team 3: 3-14 (17.6% win_pct) should be rebuilding
        assert context.is_rebuilding == True

    def test_build_team_context_regular_season_mode(self, service, mock_standings, monkeypatch):
        """Build context with regular_season roster mode (53-man)"""
        monkeypatch.setattr(service.db_api, 'get_standings', lambda *args, **kwargs: mock_standings)

        # Cap space should differ based on roster mode
        def mock_cap_space(*args, **kwargs):
            if kwargs.get('roster_mode') == 'regular_season':
                return 15_000_000
            return 20_000_000

        monkeypatch.setattr(service.cap_calc, 'calculate_team_cap_space', mock_cap_space)

        context = service.build_team_context(
            team_id=1,
            season=2024,
            roster_mode="regular_season"
        )

        assert context.cap_space == 15_000_000

    def test_build_team_context_cap_percentage_calculation(self, service, mock_standings, monkeypatch):
        """Verify cap_percentage is calculated correctly"""
        monkeypatch.setattr(service.db_api, 'get_standings', lambda *args, **kwargs: mock_standings)
        monkeypatch.setattr(service.cap_calc, 'calculate_team_cap_space', lambda *args, **kwargs: 25_550_000)

        context = service.build_team_context(team_id=1, season=2024)

        # 25.55M / 255.5M = 0.10 (10%)
        assert 0.09 < context.cap_percentage < 0.11

    def test_build_team_context_zero_cap_space(self, service, mock_standings, monkeypatch):
        """Handle zero cap space gracefully"""
        monkeypatch.setattr(service.db_api, 'get_standings', lambda *args, **kwargs: mock_standings)
        monkeypatch.setattr(service.cap_calc, 'calculate_team_cap_space', lambda *args, **kwargs: 0)

        context = service.build_team_context(team_id=1, season=2024)

        assert context.cap_space == 0
        assert context.cap_percentage == 0.0  # Should be 0, not error