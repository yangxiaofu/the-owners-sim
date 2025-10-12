"""
Test suite for PlayoffState class.

This module tests the PlayoffState class extracted from PlayoffController,
which manages playoff round progression, game completion tracking, and
bracket state management.

Tests cover:
- State initialization with default and custom values
- Round completion queries and active round detection
- State mutations (adding completed games)
- Validation of playoff dates and round progression
"""

import pytest
from datetime import date

from src.playoff_system.playoff_state import PlayoffState
from src.calendar.date_models import Date


class TestPlayoffStateInitialization:
    """Test PlayoffState initialization and default values."""

    def test_default_initialization(self):
        """Test PlayoffState initializes with correct default values."""
        state = PlayoffState()

        assert state.current_round == 'wild_card'
        assert state.original_seeding is None
        assert state.total_games_played == 0
        assert state.total_days_simulated == 0
        assert state.current_date is None

    def test_custom_initialization(self):
        """Test PlayoffState accepts custom initial values."""
        state = PlayoffState(
            current_round='divisional',
            total_games_played=6
        )

        assert state.current_round == 'divisional'
        assert state.total_games_played == 6

    def test_completed_games_default_structure(self):
        """Test completed_games dictionary has correct default structure for all rounds."""
        state = PlayoffState()

        assert isinstance(state.completed_games, dict)
        assert 'wild_card' in state.completed_games
        assert 'divisional' in state.completed_games
        assert 'conference' in state.completed_games
        assert 'super_bowl' in state.completed_games
        assert state.completed_games['wild_card'] == []
        assert state.completed_games['divisional'] == []
        assert state.completed_games['conference'] == []
        assert state.completed_games['super_bowl'] == []

    def test_brackets_default_structure(self):
        """Test brackets dictionary has correct default structure for AFC and NFC."""
        state = PlayoffState()

        assert isinstance(state.brackets, dict)
        assert 'wild_card' in state.brackets
        assert 'divisional' in state.brackets
        assert 'conference' in state.brackets
        assert 'super_bowl' in state.brackets
        assert state.brackets['wild_card'] is None
        assert state.brackets['divisional'] is None
        assert state.brackets['conference'] is None
        assert state.brackets['super_bowl'] is None


class TestStateQueries:
    """Test state query methods for round completion and active round detection."""

    def test_is_round_complete_wild_card(self):
        """Test is_round_complete() correctly identifies Wild Card round completion."""
        # Test with 6 games (complete)
        state = PlayoffState()
        for i in range(6):
            state.add_completed_game('wild_card', {'event_id': f'game_{i}'})
        assert state.is_round_complete('wild_card') == True

        # Test with only 5 games (incomplete)
        state2 = PlayoffState()
        for i in range(5):
            state2.add_completed_game('wild_card', {'event_id': f'game_{i}'})
        assert state2.is_round_complete('wild_card') == False

    def test_is_round_complete_divisional(self):
        """Test is_round_complete() correctly identifies Divisional round completion."""
        state = PlayoffState()
        for i in range(4):
            state.add_completed_game('divisional', {'event_id': f'game_{i}'})
        assert state.is_round_complete('divisional') == True

    def test_is_round_complete_conference(self):
        """Test is_round_complete() correctly identifies Conference round completion."""
        state = PlayoffState()
        for i in range(2):
            state.add_completed_game('conference', {'event_id': f'game_{i}'})
        assert state.is_round_complete('conference') == True

    def test_is_round_complete_super_bowl(self):
        """Test is_round_complete() correctly identifies Super Bowl completion."""
        state = PlayoffState()
        state.add_completed_game('super_bowl', {'event_id': 'game_0'})
        assert state.is_round_complete('super_bowl') == True

    def test_get_active_round_initial(self):
        """Test get_active_round() returns Wild Card at initialization."""
        state = PlayoffState()
        assert state.get_active_round() == 'wild_card'

    def test_get_active_round_after_wild_card(self):
        """Test get_active_round() returns Divisional after Wild Card completion."""
        state = PlayoffState()
        for i in range(6):
            state.add_completed_game('wild_card', {'event_id': f'game_{i}'})
        assert state.get_active_round() == 'divisional'

    def test_get_active_round_after_divisional(self):
        """Test get_active_round() returns Conference after Divisional completion."""
        state = PlayoffState()
        # Complete wild card (6 games)
        for i in range(6):
            state.add_completed_game('wild_card', {'event_id': f'game_{i}'})
        # Complete divisional (4 games)
        for i in range(4):
            state.add_completed_game('divisional', {'event_id': f'game_{i}'})
        assert state.get_active_round() == 'conference'

    def test_get_expected_game_count(self):
        """Test get_expected_game_count() returns correct game counts for each round."""
        state = PlayoffState()
        assert state._get_expected_game_count('wild_card') == 6
        assert state._get_expected_game_count('divisional') == 4
        assert state._get_expected_game_count('conference') == 2
        assert state._get_expected_game_count('super_bowl') == 1


class TestStateMutations:
    """Test state mutation methods for tracking completed games."""

    def test_add_completed_game_success(self):
        """Test add_completed_game() successfully adds a game to a round."""
        # Create state
        state = PlayoffState()

        # Add a game with event_id to 'wild_card'
        game = {'event_id': 'game_1', 'home_score': 24, 'away_score': 17}
        state.add_completed_game('wild_card', game)

        # Assert game appears in completed_games['wild_card']
        assert game in state.completed_games['wild_card']

        # Assert len(completed_games['wild_card']) == 1
        assert len(state.completed_games['wild_card']) == 1

    def test_add_completed_game_prevents_duplicates(self):
        """Test add_completed_game() prevents duplicate game IDs in the same round."""
        # Create state
        state = PlayoffState()

        # Add same game twice (same event_id)
        game = {'event_id': 'game_1', 'home_score': 24, 'away_score': 17}
        state.add_completed_game('wild_card', game)
        state.add_completed_game('wild_card', game)

        # Assert len(completed_games['wild_card']) == 1 (not 2!)
        assert len(state.completed_games['wild_card']) == 1

        # Assert total_games_played == 1 (not 2!)
        assert state.total_games_played == 1

    def test_add_completed_game_increments_counter(self):
        """Test add_completed_game() increments games_completed counter."""
        # Create state
        state = PlayoffState()

        # Assert total_games_played == 0
        assert state.total_games_played == 0

        # Add 3 games with different event_ids
        game1 = {'event_id': 'game_1', 'home_score': 24, 'away_score': 17}
        game2 = {'event_id': 'game_2', 'home_score': 31, 'away_score': 20}
        game3 = {'event_id': 'game_3', 'home_score': 27, 'away_score': 24}

        state.add_completed_game('wild_card', game1)
        state.add_completed_game('wild_card', game2)
        state.add_completed_game('wild_card', game3)

        # Assert total_games_played == 3
        assert state.total_games_played == 3

    def test_add_completed_game_to_all_rounds(self):
        """Test add_completed_game() works correctly for all playoff rounds."""
        # Create state
        state = PlayoffState()

        # Add 1 game to each round ('wild_card', 'divisional', 'conference', 'super_bowl')
        game_wild_card = {'event_id': 'wc_game_1', 'home_score': 24, 'away_score': 17}
        game_divisional = {'event_id': 'div_game_1', 'home_score': 31, 'away_score': 20}
        game_conference = {'event_id': 'conf_game_1', 'home_score': 27, 'away_score': 24}
        game_super_bowl = {'event_id': 'sb_game_1', 'home_score': 35, 'away_score': 28}

        state.add_completed_game('wild_card', game_wild_card)
        state.add_completed_game('divisional', game_divisional)
        state.add_completed_game('conference', game_conference)
        state.add_completed_game('super_bowl', game_super_bowl)

        # Assert each round has exactly 1 game
        assert len(state.completed_games['wild_card']) == 1
        assert len(state.completed_games['divisional']) == 1
        assert len(state.completed_games['conference']) == 1
        assert len(state.completed_games['super_bowl']) == 1

        # Assert total_games_played == 4
        assert state.total_games_played == 4


class TestValidation:
    """Test validation methods for playoff state consistency."""

    def test_validate_accepts_january_dates(self):
        """Test validate() accepts valid January playoff dates."""
        state = PlayoffState(current_date=Date(2025, 1, 15))
        errors = state.validate()
        assert errors == []

    def test_validate_accepts_february_dates(self):
        """Test validate() accepts valid February playoff dates."""
        state = PlayoffState(current_date=Date(2025, 2, 10))
        errors = state.validate()
        assert errors == []

    def test_validate_rejects_march_dates(self):
        """Test validate() rejects playoff dates in March or later."""
        state = PlayoffState(current_date=Date(2025, 3, 1))
        errors = state.validate()
        assert len(errors) > 0
        assert "outside valid playoff window" in errors[0]

    def test_validate_rejects_invalid_round_progression(self):
        """Test validate() detects invalid round progression (e.g., Conference before Divisional)."""
        state = PlayoffState(current_round='divisional')
        # Do NOT add any wild_card games (skip wild card)
        errors = state.validate()
        assert len(errors) > 0
        assert "divisional round when wild_card round is incomplete" in errors[0]

    def test_validate_detects_inconsistent_state(self):
        """Test validate() detects inconsistencies between completed_games and games_completed counter."""
        state = PlayoffState()
        # Manually set state.total_games_played = 10
        state.total_games_played = 10
        # Add only 3 games to completed_games
        state.completed_games['wild_card'].append({'event_id': 'game1'})
        state.completed_games['wild_card'].append({'event_id': 'game2'})
        state.completed_games['wild_card'].append({'event_id': 'game3'})
        errors = state.validate()
        assert len(errors) > 0
        assert "total_games_played (10) does not match actual completed games count (3)" in errors[0]
