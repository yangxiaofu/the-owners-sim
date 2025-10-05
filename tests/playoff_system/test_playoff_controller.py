"""
Integration Tests for PlayoffController

Tests complete playoff progression through all rounds to verify:
- Correct number of games scheduled per round
- Proper round transitions
- Bracket state management
- Super Bowl completion detection

Note: These are integration tests using temporary databases, not pure unit tests.
The PlayoffController creates all dependencies internally, making unit testing difficult.
"""

import pytest
import tempfile
import os
from pathlib import Path
from playoff_system.playoff_controller import PlayoffController
from calendar.date_models import Date
from database.connection import DatabaseConnection


class TestPlayoffControllerIntegration:
    """Integration tests for PlayoffController."""

    @pytest.fixture
    def test_db_path(self):
        """
        Create temporary database for testing.

        Yields:
            Path to temporary database file with schema initialized

        Cleanup:
            Removes database after test
        """
        # Create temporary file
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        # Initialize database schema
        db_conn = DatabaseConnection(path)
        db_conn.ensure_dynasty_exists("test_dynasty")

        yield path

        # Cleanup
        try:
            os.unlink(path)
        except:
            pass

    @pytest.fixture
    def controller(self, test_db_path):
        """
        Create PlayoffController with test database.

        Uses random seeding for reproducible testing.
        """
        return PlayoffController(
            database_path=test_db_path,
            dynasty_id="test_dynasty",
            season_year=2024,
            wild_card_start_date=Date(2025, 1, 11),
            initial_seeding=None,  # Random seeding
            enable_persistence=False,  # No persistence needed for tests
            verbose_logging=False  # Quiet mode for test output
        )

    def test_playoff_controller_initialization(self, controller):
        """Test that PlayoffController initializes correctly."""
        assert controller.current_round == 'wild_card'
        assert controller.total_games_played == 0
        assert controller.total_days_simulated == 0
        assert controller.wild_card_start_date == Date(2025, 1, 11)

        # Check that all rounds start with 0 completed games
        for round_name in controller.ROUND_ORDER:
            assert len(controller.completed_games[round_name]) == 0

    def test_wild_card_round_schedules_6_games(self, controller):
        """Test that Wild Card round schedules exactly 6 games."""
        # Get current bracket
        bracket = controller.get_current_bracket()

        assert bracket is not None, "Wild Card bracket should be initialized"

        # Count Wild Card games using completed_games dict
        wild_card_bracket = bracket.get('wild_card')
        assert wild_card_bracket is not None, "Wild Card bracket should exist"

        # Wild Card round should have games scheduled
        # Check using the bracket's games attribute
        assert hasattr(wild_card_bracket, 'games'), "Bracket should have games"
        assert len(wild_card_bracket.games) == 6, \
            f"Wild Card should have 6 games, got {len(wild_card_bracket.games)}"

    def test_playoff_progression_schedules_all_13_games(self, controller):
        """
        Integration test verifying all playoff games are scheduled correctly:
        - 6 Wild Card games
        - 4 Divisional games
        - 2 Conference Championship games (currently FAILS - only schedules 1)
        - 1 Super Bowl game

        This test SHOULD FAIL initially, reproducing the bug where Conference
        round only schedules 1 game instead of 2.
        """
        # Track all games scheduled across all rounds
        total_games_scheduled = 0
        games_by_round = {}

        # Simulate to Super Bowl completion
        summary = controller.simulate_to_super_bowl()

        # Check summary structure
        assert 'total_games' in summary
        assert 'rounds_completed' in summary

        # Get final bracket state
        for round_name in controller.ROUND_ORDER:
            games_in_round = len(controller.completed_games[round_name])
            games_by_round[round_name] = games_in_round
            total_games_scheduled += games_in_round

        # Verify game counts per round
        assert games_by_round['wild_card'] == 6, \
            f"Wild Card should have 6 games, got {games_by_round['wild_card']}"

        assert games_by_round['divisional'] == 4, \
            f"Divisional should have 4 games, got {games_by_round['divisional']}"

        # THIS ASSERTION WILL FAIL - REPRODUCING THE BUG
        assert games_by_round['conference'] == 2, \
            f"Conference should have 2 games, got {games_by_round['conference']} (BUG DETECTED)"

        assert games_by_round['super_bowl'] == 1, \
            f"Super Bowl should have 1 game, got {games_by_round['super_bowl']}"

        # Verify total
        assert total_games_scheduled == 13, \
            f"Playoffs should have 13 total games, got {total_games_scheduled}\n" \
            f"Breakdown: Wild Card={games_by_round['wild_card']}, " \
            f"Divisional={games_by_round['divisional']}, " \
            f"Conference={games_by_round['conference']}, " \
            f"Super Bowl={games_by_round['super_bowl']}"

    def test_round_progression_order(self, controller):
        """Test that rounds progress in correct order using active_round."""
        # Should start in Wild Card
        assert controller.get_active_round() == 'wild_card'

        # Complete Wild Card round
        controller.advance_to_next_round()
        assert controller.get_active_round() == 'divisional', \
            "Active round should be Divisional after Wild Card"

        # Complete Divisional round
        controller.advance_to_next_round()
        assert controller.get_active_round() == 'conference', \
            "Active round should be Conference after Divisional"

        # Complete Conference round
        controller.advance_to_next_round()
        assert controller.get_active_round() == 'super_bowl', \
            "Active round should be Super Bowl after Conference"

    def test_advance_day_returns_correct_structure(self, controller):
        """Test that advance_day returns properly structured result."""
        result = controller.advance_day()

        # Check required keys
        assert 'date' in result
        assert 'games_played' in result
        assert 'results' in result
        assert 'current_round' in result
        assert 'round_complete' in result
        assert 'success' in result

        # Check types
        assert isinstance(result['date'], str)
        assert isinstance(result['games_played'], int)
        assert isinstance(result['results'], list)
        assert isinstance(result['current_round'], str)
        assert isinstance(result['round_complete'], bool)
        assert isinstance(result['success'], bool)

    def test_advance_week_simulates_multiple_days(self, controller):
        """Test that advance_week simulates 7 days."""
        initial_days = controller.total_days_simulated

        result = controller.advance_week()

        # Check return structure
        assert 'start_date' in result
        assert 'end_date' in result
        assert 'total_games_played' in result
        assert 'daily_results' in result

        # Verify 7 days were simulated
        assert len(result['daily_results']) == 7, \
            f"Should have 7 daily results, got {len(result['daily_results'])}"
        assert controller.total_days_simulated == initial_days + 7

    def test_super_bowl_detection(self, controller):
        """Test that Super Bowl completion is properly detected."""
        # Simulate to Super Bowl
        summary = controller.simulate_to_super_bowl()

        # Check that Super Bowl round is complete
        super_bowl_games = controller.completed_games['super_bowl']
        assert len(super_bowl_games) == 1, \
            f"Super Bowl should have exactly 1 game, got {len(super_bowl_games)}"

        # Check that the game was successful
        super_bowl_game = super_bowl_games[0]
        assert super_bowl_game.get('success', False), \
            "Super Bowl game should be marked as successful"

    def test_bracket_state_tracking(self, controller):
        """Test that bracket state is properly maintained throughout simulation."""
        # Initial state - Wild Card bracket should exist
        initial_bracket = controller.get_current_bracket()
        assert initial_bracket is not None

        # Simulate through all rounds
        controller.simulate_to_super_bowl()

        # All bracket states should be populated
        assert controller.brackets['wild_card'] is not None
        assert controller.brackets['divisional'] is not None
        assert controller.brackets['conference'] is not None
        assert controller.brackets['super_bowl'] is not None

    def test_completed_games_tracking(self, controller):
        """Test that completed games are properly tracked per round."""
        # Simulate to Super Bowl
        controller.simulate_to_super_bowl()

        # Check that each round has games tracked
        for round_name in controller.ROUND_ORDER:
            games = controller.completed_games[round_name]
            assert len(games) > 0, f"Round {round_name} should have completed games"

            # Verify game structure
            for game in games:
                assert 'event_id' in game, "Game should have event_id"
                assert 'success' in game, "Game should have success flag"


class TestPlayoffControllerRoundTransitions:
    """Focused tests on round transition logic."""

    @pytest.fixture
    def test_db_path(self):
        """Create temporary database for round transition tests."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        # Initialize database schema
        db_conn = DatabaseConnection(path)
        db_conn.ensure_dynasty_exists("test_round_transitions")

        yield path

        # Cleanup
        try:
            os.unlink(path)
        except:
            pass

    @pytest.fixture
    def controller(self, test_db_path):
        """Create PlayoffController for round transition tests."""
        return PlayoffController(
            database_path=test_db_path,
            dynasty_id="test_round_transitions",
            season_year=2024,
            wild_card_start_date=Date(2025, 1, 11),
            enable_persistence=False,
            verbose_logging=True  # Enable verbose logging to debug transitions
        )

    def test_wild_card_to_divisional_transition(self, controller):
        """Test transition from Wild Card to Divisional round."""
        # Verify starting in Wild Card
        assert controller.current_round == 'wild_card'

        # Complete Wild Card round
        controller.advance_to_next_round()

        # current_round stays 'wild_card' until divisional games are simulated
        # But Wild Card should have 6 completed games
        wild_card_games = controller.completed_games['wild_card']
        assert len(wild_card_games) == 6, \
            f"Wild Card should have 6 completed games, got {len(wild_card_games)}"

        # Verify divisional round was scheduled (check using active_round)
        active_round = controller.get_active_round()
        assert active_round == 'divisional', \
            f"Active round should be 'divisional' after Wild Card completion, got '{active_round}'"

    def test_divisional_to_conference_transition(self, controller):
        """Test transition from Divisional to Conference round."""
        # Advance through Wild Card
        controller.advance_to_next_round()

        # Complete Divisional round
        controller.advance_to_next_round()

        # Divisional should have 4 completed games
        divisional_games = controller.completed_games['divisional']
        assert len(divisional_games) == 4, \
            f"Divisional should have 4 completed games, got {len(divisional_games)}"

        # Verify conference round was scheduled (check using active_round)
        active_round = controller.get_active_round()
        assert active_round == 'conference', \
            f"Active round should be 'conference' after Divisional completion, got '{active_round}'"

    def test_conference_to_super_bowl_transition(self, controller):
        """
        Test transition from Conference to Super Bowl round.

        THIS TEST WILL HELP DIAGNOSE THE BUG - we expect Conference to have
        2 games before transitioning to Super Bowl.
        """
        # Advance through Wild Card and Divisional
        controller.advance_to_next_round()  # Wild Card -> Divisional
        controller.advance_to_next_round()  # Divisional -> Conference

        # Complete Conference round
        controller.advance_to_next_round()

        # Conference should have 2 completed games (THIS WILL FAIL IF BUG EXISTS)
        conference_games = controller.completed_games['conference']
        assert len(conference_games) == 2, \
            f"Conference should have 2 completed games, got {len(conference_games)}\n" \
            f"Conference games: {conference_games}"

        # Verify Super Bowl round was scheduled (check using active_round)
        active_round = controller.get_active_round()
        assert active_round == 'super_bowl', \
            f"Active round should be 'super_bowl' after Conference completion, got '{active_round}'"


class TestPlayoffControllerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_controller_with_custom_start_date(self):
        """Test PlayoffController with custom Wild Card start date."""
        # Create temporary database
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        try:
            # Initialize database schema
            db_conn = DatabaseConnection(db_path)
            db_conn.ensure_dynasty_exists("custom_date_test")

            custom_date = Date(2025, 1, 15)
            controller = PlayoffController(
                database_path=db_path,
                dynasty_id="custom_date_test",
                season_year=2024,
                wild_card_start_date=custom_date,
                enable_persistence=False,
                verbose_logging=False
            )

            assert controller.wild_card_start_date == custom_date
            assert controller.calendar.get_current_date() == custom_date
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except:
                pass

    def test_controller_with_persistence_enabled(self, tmp_path):
        """Test PlayoffController with persistence enabled."""
        # Use temporary file path for database
        db_path = str(tmp_path / "test_playoffs.db")

        controller = PlayoffController(
            database_path=db_path,
            dynasty_id="persistence_test",
            season_year=2024,
            enable_persistence=True,
            verbose_logging=False
        )

        assert controller.enable_persistence == True

        # Simulate one day
        result = controller.advance_day()
        assert result['success'] == True
