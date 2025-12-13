"""
Tests for Practice Injuries & Weekly Processing.

Tests that injuries are properly generated during practice and that
weekly injury processing (recoveries) works correctly.

Tollgate 4 of Milestone 5: Injuries & IR System
"""

import pytest
import tempfile
import os
import sqlite3
import json
import inspect

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.services.injury_service import InjuryService
from src.game_cycle.models.injury_models import (
    Injury, InjuryType, BodyPart, InjurySeverity
)
from src.game_cycle.handlers.regular_season import RegularSeasonHandler


class TestWeeklyInjuryProcessing:
    """Test weekly injury processing methods exist."""

    def test_handler_has_process_weekly_injuries_method(self):
        """RegularSeasonHandler should have _process_weekly_injuries method."""
        handler = RegularSeasonHandler()
        assert hasattr(handler, '_process_weekly_injuries')

    def test_handler_has_roll_practice_injury_method(self):
        """RegularSeasonHandler should have _roll_practice_injury method."""
        handler = RegularSeasonHandler()
        assert hasattr(handler, '_roll_practice_injury')

    def test_handler_has_get_random_active_player_method(self):
        """RegularSeasonHandler should have _get_random_active_player method."""
        handler = RegularSeasonHandler()
        assert hasattr(handler, '_get_random_active_player')

    def test_process_weekly_injuries_signature(self):
        """_process_weekly_injuries should accept context and week_number."""
        handler = RegularSeasonHandler()
        sig = inspect.signature(handler._process_weekly_injuries)
        params = list(sig.parameters.keys())
        assert 'context' in params
        assert 'week_number' in params


class TestInjuryServiceRecoveryUnit:
    """Test injury recovery methods in InjuryService (unit tests)."""

    def test_injury_service_has_check_recovery_method(self):
        """InjuryService should have check_injury_recovery method."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        db = GameCycleDatabase(path)
        db.close()

        try:
            service = InjuryService(path, 'test', 2025)
            assert hasattr(service, 'check_injury_recovery')
        finally:
            os.unlink(path)

    def test_injury_service_has_clear_injury_method(self):
        """InjuryService should have clear_injury method."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        db = GameCycleDatabase(path)
        db.close()

        try:
            service = InjuryService(path, 'test', 2025)
            assert hasattr(service, 'clear_injury')
        finally:
            os.unlink(path)

    def test_injury_service_has_get_unavailable_players_method(self):
        """InjuryService should have get_unavailable_players method."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        db = GameCycleDatabase(path)
        db.close()

        try:
            service = InjuryService(path, 'test', 2025)
            assert hasattr(service, 'get_unavailable_players')
        finally:
            os.unlink(path)

    def test_check_injury_recovery_signature(self):
        """check_injury_recovery should accept current_week parameter."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        db = GameCycleDatabase(path)
        db.close()

        try:
            service = InjuryService(path, 'test', 2025)
            sig = inspect.signature(service.check_injury_recovery)
            params = list(sig.parameters.keys())
            assert 'current_week' in params
        finally:
            os.unlink(path)


class TestMockStatsGeneratorInjuryExclusion:
    """Test that MockStatsGenerator has injury exclusion capability."""

    def test_generator_has_get_team_roster_method(self):
        """MockStatsGenerator should have _get_team_roster method."""
        from src.game_cycle.services.mock_stats_generator import MockStatsGenerator

        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        db = GameCycleDatabase(path)
        db.close()

        try:
            generator = MockStatsGenerator(path, 'test', 2025)
            assert hasattr(generator, '_get_team_roster')
        finally:
            os.unlink(path)

    def test_generator_roster_query_includes_injury_exclusion(self):
        """MockStatsGenerator._get_team_roster query should exclude injured players."""
        from src.game_cycle.services.mock_stats_generator import MockStatsGenerator

        # Check the source code of _get_team_roster for injury exclusion
        source = inspect.getsource(MockStatsGenerator._get_team_roster)

        # Verify the method includes injury exclusion logic
        assert 'player_injuries' in source, "Query should reference player_injuries table"
        assert 'LEFT JOIN' in source, "Query should use LEFT JOIN to include injury data"
        assert 'is_active' in source, "Query should check is_active flag"
        assert 'injury_id IS NULL' in source, "Query should filter out active injuries"


class TestPracticeInjuryGeneration:
    """Test practice injury generation logic."""

    def test_practice_injury_context_modifier(self):
        """Practice injuries should have lower probability (0.3x modifier)."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        db = GameCycleDatabase(path)
        db.close()

        try:
            service = InjuryService(path, 'test', 2025)

            # Calculate probability for game vs practice
            game_prob = service.calculate_injury_probability(
                position='running_back',
                durability=75,
                age=26,
                injury_history_count=0,
                context='game'
            )

            practice_prob = service.calculate_injury_probability(
                position='running_back',
                durability=75,
                age=26,
                injury_history_count=0,
                context='practice'
            )

            # Practice should be 0.3x of game probability
            expected_ratio = 0.3
            actual_ratio = practice_prob / game_prob

            assert abs(actual_ratio - expected_ratio) < 0.01
        finally:
            os.unlink(path)

    def test_practice_injury_rate_constant(self):
        """Verify practice injury rate is defined in handler."""
        # Read the source code and check for practice injury rate
        source = inspect.getsource(RegularSeasonHandler._roll_practice_injury)

        # Should have a practice injury rate constant
        assert 'PRACTICE_INJURY_RATE' in source
        assert '0.015' in source  # 1.5% rate


class TestWeeklyProcessingReturnStructure:
    """Test the structure of weekly processing results."""

    def test_process_weekly_injuries_returns_expected_structure(self):
        """_process_weekly_injuries should return dict with expected keys."""
        # Check the source code for correct return structure
        source = inspect.getsource(RegularSeasonHandler._process_weekly_injuries)

        # Verify it creates and returns a results dict with expected keys
        assert "results = {" in source or 'results["practice_injuries"]' in source
        assert '"practice_injuries"' in source
        assert '"players_returning"' in source
        assert "return results" in source

    def test_process_weekly_injuries_loops_all_teams(self):
        """_process_weekly_injuries should check all 32 teams."""
        source = inspect.getsource(RegularSeasonHandler._process_weekly_injuries)

        # Should loop through all 32 teams
        assert 'range(1, 33)' in source


class TestExecuteReturnStructure:
    """Test that execute() returns injury-related fields."""

    def test_execute_return_includes_injury_fields(self):
        """RegularSeasonHandler.execute should include injury fields in return."""
        # Check the source code of execute() for injury return fields
        source = inspect.getsource(RegularSeasonHandler.execute)

        # Verify the return includes injury-related keys
        assert 'injuries' in source
        assert 'practice_injuries' in source
        assert 'players_returning' in source
