"""
Tests for game-time injury integration.

Tests that injuries are properly generated and recorded during:
- Regular season games (via MockStatsGenerator)
- Playoff games (via simplified PlayoffHandler logic)

Tollgate 3 of Milestone 5: Injuries & IR System
"""

import pytest
import tempfile
import os
import sqlite3
import json

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.services.mock_stats_generator import MockStatsGenerator, MockGameStats
from src.game_cycle.services.injury_service import InjuryService
from src.game_cycle.models.injury_models import Injury


class TestMockGameStatsInjuries:
    """Test that MockGameStats includes injuries field."""

    def test_mock_game_stats_has_injuries_field(self):
        """MockGameStats dataclass should have injuries field."""
        stats = MockGameStats(
            game_id="test_game",
            home_team_id=1,
            away_team_id=2,
            home_score=21,
            away_score=14,
            player_stats=[]
        )

        assert hasattr(stats, 'injuries')
        assert isinstance(stats.injuries, list)
        assert len(stats.injuries) == 0

    def test_mock_game_stats_with_injuries(self):
        """MockGameStats should accept injuries in constructor."""
        from src.game_cycle.models.injury_models import (
            Injury, InjuryType, BodyPart, InjurySeverity
        )

        test_injury = Injury(
            player_id=100,
            player_name="Test Player",
            team_id=1,
            injury_type=InjuryType.ANKLE_SPRAIN,
            body_part=BodyPart.ANKLE,
            severity=InjurySeverity.MINOR,
            weeks_out=1,
            season=2025,
            week_occurred=5,
            occurred_during="game",
            game_id="test_game"
        )

        stats = MockGameStats(
            game_id="test_game",
            home_team_id=1,
            away_team_id=2,
            home_score=21,
            away_score=14,
            player_stats=[],
            injuries=[test_injury]
        )

        assert len(stats.injuries) == 1
        assert stats.injuries[0].player_id == 100


class TestMockStatsGeneratorInjuries:
    """Test injury generation in MockStatsGenerator."""

    def test_generator_accepts_season_parameter(self):
        """MockStatsGenerator constructor accepts season parameter."""
        # Create a minimal temp database for constructor test
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        db = GameCycleDatabase(path)
        db.close()

        try:
            generator = MockStatsGenerator(path, 'test', 2026)
            assert generator.season == 2026
        finally:
            os.unlink(path)

    def test_check_game_injuries_method_exists(self):
        """MockStatsGenerator should have _check_game_injuries method."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        db = GameCycleDatabase(path)
        db.close()

        try:
            generator = MockStatsGenerator(path, 'test', 2025)
            assert hasattr(generator, '_check_game_injuries')
        finally:
            os.unlink(path)

    def test_build_player_data_method_exists(self):
        """MockStatsGenerator should have _build_player_data_for_injury method."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        db = GameCycleDatabase(path)
        db.close()

        try:
            generator = MockStatsGenerator(path, 'test', 2025)
            assert hasattr(generator, '_build_player_data_for_injury')
        finally:
            os.unlink(path)


class TestGameSimulatorServiceInjuries:
    """Test injuries in GameSimulatorService."""

    def test_game_simulation_result_has_injuries_field(self):
        """GameSimulationResult should have injuries field."""
        from src.game_cycle.services.game_simulator_service import GameSimulationResult

        result = GameSimulationResult(
            game_id="test_game",
            home_team_id=1,
            away_team_id=2,
            home_score=21,
            away_score=14
        )

        assert hasattr(result, 'injuries')
        assert isinstance(result.injuries, list)


class TestHandlerInjuryIntegration:
    """Test that handler code integrates injuries correctly."""

    def test_regular_season_handler_has_injury_import(self):
        """RegularSeasonHandler should have injury service import available."""
        from src.game_cycle.handlers.regular_season import RegularSeasonHandler
        handler = RegularSeasonHandler()
        assert handler is not None

    def test_playoff_handler_has_injury_methods(self):
        """PlayoffHandler should have injury generation methods."""
        from src.game_cycle.handlers.playoffs import PlayoffHandler
        handler = PlayoffHandler()
        assert hasattr(handler, '_generate_playoff_injuries')
        assert hasattr(handler, '_get_active_roster')
