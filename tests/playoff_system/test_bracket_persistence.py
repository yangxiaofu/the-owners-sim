"""
Test suite for BracketPersistence class.

This module tests the BracketPersistence class which handles playoff bracket
database operations including:
- Checking for existing playoff rounds in the database
- Loading playoff events from the calendar/events system
- Reconstructing playoff state from persisted data

The persistence layer enables playoff bracket recovery across simulation sessions
and supports dynasty isolation for multi-save game management.
"""

import json
import uuid
import pytest
from unittest.mock import Mock, MagicMock

from src.playoff_system.bracket_persistence import BracketPersistence
from src.playoff_system.playoff_state import PlayoffState
from events.event_database_api import EventDatabaseAPI


class TestCheckExistingRound:
    """Test the check_existing_round method for finding persisted playoff games."""

    def test_check_existing_round_returns_empty_when_no_games(self):
        """Should return empty list when no games exist for the round."""
        # Create mock EventDatabaseAPI that returns empty list
        mock_db = Mock(spec=EventDatabaseAPI)
        mock_db.get_events_by_dynasty.return_value = []

        # Create BracketPersistence with mock
        persistence = BracketPersistence(mock_db)

        # Call check_existing_round
        result = persistence.check_existing_round('dynasty1', 2025, 'wild_card')

        # Assert result is empty list
        assert result == []
        assert len(result) == 0

    def test_check_existing_round_finds_wild_card_games(self):
        """Should find all 6 wild card round games when they exist."""
        # Create mock that returns 6 wild card games
        wild_card_games = [
            {'game_id': 'playoff_2025_wild_card_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_2', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_3', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_4', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_5', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_6', 'event_type': 'GAME'},
        ]
        mock_db = Mock(spec=EventDatabaseAPI)
        mock_db.get_events_by_dynasty.return_value = wild_card_games

        persistence = BracketPersistence(mock_db)

        # Call check_existing_round
        result = persistence.check_existing_round('dynasty1', 2025, 'wild_card')

        # Assert result has 6 events
        assert len(result) == 6
        assert all(event['game_id'].startswith('playoff_2025_wild_card_') for event in result)

    def test_check_existing_round_finds_divisional_games(self):
        """Should find all 4 divisional round games when they exist."""
        # Create mock that returns 4 divisional games
        divisional_games = [
            {'game_id': 'playoff_2025_divisional_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_divisional_2', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_divisional_3', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_divisional_4', 'event_type': 'GAME'},
        ]
        mock_db = Mock(spec=EventDatabaseAPI)
        mock_db.get_events_by_dynasty.return_value = divisional_games

        persistence = BracketPersistence(mock_db)

        # Call check_existing_round
        result = persistence.check_existing_round('dynasty1', 2025, 'divisional')

        # Assert result has 4 events
        assert len(result) == 4
        assert all(event['game_id'].startswith('playoff_2025_divisional_') for event in result)

    def test_check_existing_round_filters_by_season(self):
        """Should only return games from the specified season."""
        # Create mock that returns mix of 2024 and 2025 games
        mixed_games = [
            {'game_id': 'playoff_2024_wild_card_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2024_wild_card_2', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_2', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_3', 'event_type': 'GAME'},
        ]
        mock_db = Mock(spec=EventDatabaseAPI)
        mock_db.get_events_by_dynasty.return_value = mixed_games

        persistence = BracketPersistence(mock_db)

        # Call check_existing_round for 2025
        result = persistence.check_existing_round('dynasty1', 2025, 'wild_card')

        # Assert result only contains 2025 games, not 2024
        assert len(result) == 3
        assert all('2025' in event['game_id'] for event in result)
        assert all('2024' not in event['game_id'] for event in result)

    def test_check_existing_round_filters_by_dynasty(self):
        """Should only return games from the specified dynasty context."""
        # Create mock that returns games (filtering is done at DB level)
        mock_db = Mock(spec=EventDatabaseAPI)
        mock_db.get_events_by_dynasty.return_value = [
            {'game_id': 'playoff_2025_wild_card_1', 'event_type': 'GAME'},
        ]

        persistence = BracketPersistence(mock_db)

        # Call check_existing_round with dynasty_id='dynasty1'
        result = persistence.check_existing_round('dynasty1', 2025, 'wild_card')

        # Verify mock was called with dynasty_id='dynasty1'
        mock_db.get_events_by_dynasty.assert_called_once_with(
            dynasty_id='dynasty1',
            event_type='GAME'
        )

    def test_check_existing_round_uses_correct_game_id_format(self):
        """Should query using correct game_id format (e.g., WC1, DIV1, CONF1)."""
        # Create mock that returns various game_ids
        various_games = [
            {'game_id': 'playoff_2025_wild_card_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_divisional_1', 'event_type': 'GAME'},
            {'game_id': 'regular_season_2025_week_1_game_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_2', 'event_type': 'GAME'},
        ]
        mock_db = Mock(spec=EventDatabaseAPI)
        mock_db.get_events_by_dynasty.return_value = various_games

        persistence = BracketPersistence(mock_db)

        # Verify it filters using format: playoff_{season}_{round}_
        result = persistence.check_existing_round('dynasty1', 2025, 'wild_card')

        # Test that regular season games are excluded
        assert len(result) == 2
        assert all('playoff_2025_wild_card_' in event['game_id'] for event in result)
        assert not any('regular_season' in event['game_id'] for event in result)
        assert not any('divisional' in event['game_id'] for event in result)


class TestLoadPlayoffEvents:
    """Test the load_playoff_events method for retrieving playoff games from calendar."""

    def test_load_playoff_events_returns_empty_when_no_events(self):
        """Should return empty list when no playoff events exist."""
        # Arrange
        mock_event_db_api = Mock()
        mock_event_db_api.get_events_by_dynasty.return_value = []
        persistence = BracketPersistence(mock_event_db_api)

        # Act
        result = persistence.load_playoff_events(dynasty_id='test_dynasty', season=2025)

        # Assert
        assert result == []
        mock_event_db_api.get_events_by_dynasty.assert_called_once_with(
            dynasty_id='test_dynasty',
            event_type='GAME'
        )

    def test_load_playoff_events_loads_all_rounds(self):
        """Should load events from all playoff rounds (WC, DIV, CONF, SB)."""
        # Arrange
        mock_event_db_api = Mock()
        mock_events = [
            # Wild Card (6 games)
            {'game_id': 'playoff_2025_wild_card_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_2', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_3', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_4', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_5', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_6', 'event_type': 'GAME'},
            # Divisional (4 games)
            {'game_id': 'playoff_2025_divisional_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_divisional_2', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_divisional_3', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_divisional_4', 'event_type': 'GAME'},
            # Conference (2 games)
            {'game_id': 'playoff_2025_conference_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_conference_2', 'event_type': 'GAME'},
            # Super Bowl (1 game)
            {'game_id': 'playoff_2025_super_bowl', 'event_type': 'GAME'},
        ]
        mock_event_db_api.get_events_by_dynasty.return_value = mock_events
        persistence = BracketPersistence(mock_event_db_api)

        # Act
        result = persistence.load_playoff_events(dynasty_id='test_dynasty', season=2025)

        # Assert
        assert len(result) == 13

    def test_load_playoff_events_filters_by_dynasty(self):
        """Should only return events from the specified dynasty context."""
        # Arrange
        mock_event_db_api = Mock()
        mock_events = [
            {'game_id': 'playoff_2025_wild_card_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_2', 'event_type': 'GAME'},
        ]
        mock_event_db_api.get_events_by_dynasty.return_value = mock_events
        persistence = BracketPersistence(mock_event_db_api)

        # Act
        result = persistence.load_playoff_events(dynasty_id='dynasty1', season=2025)

        # Assert
        mock_event_db_api.get_events_by_dynasty.assert_called_once_with(
            dynasty_id='dynasty1',
            event_type='GAME'
        )
        assert len(result) == 2

    def test_load_playoff_events_filters_by_season(self):
        """Should only return events from the specified season."""
        # Arrange
        mock_event_db_api = Mock()
        mock_events = [
            # 2024 playoff games (should be excluded)
            {'game_id': 'playoff_2024_wild_card_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2024_wild_card_2', 'event_type': 'GAME'},
            # 2025 playoff games (should be included)
            {'game_id': 'playoff_2025_wild_card_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_2', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_divisional_1', 'event_type': 'GAME'},
        ]
        mock_event_db_api.get_events_by_dynasty.return_value = mock_events
        persistence = BracketPersistence(mock_event_db_api)

        # Act
        result = persistence.load_playoff_events(dynasty_id='test', season=2025)

        # Assert
        assert len(result) == 3
        for event in result:
            assert '2025' in event['game_id']
            assert '2024' not in event['game_id']

    def test_load_playoff_events_excludes_regular_season_games(self):
        """Should not return regular season game events (Week 1-18)."""
        # Arrange
        mock_event_db_api = Mock()
        mock_events = [
            # Regular season games (should be excluded)
            {'game_id': 'game_2025_week_1', 'event_type': 'GAME'},
            {'game_id': 'game_2025_week_10', 'event_type': 'GAME'},
            {'game_id': 'game_2025_week_18', 'event_type': 'GAME'},
            # Playoff games (should be included)
            {'game_id': 'playoff_2025_wild_card_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_divisional_1', 'event_type': 'GAME'},
        ]
        mock_event_db_api.get_events_by_dynasty.return_value = mock_events
        persistence = BracketPersistence(mock_event_db_api)

        # Act
        result = persistence.load_playoff_events(dynasty_id='test', season=2025)

        # Assert
        assert len(result) == 2
        for event in result:
            assert event['game_id'].startswith('playoff_')

    def test_load_playoff_events_handles_null_game_ids(self):
        """Should handle events with null or missing game_id fields gracefully."""
        # Arrange
        mock_event_db_api = Mock()
        mock_events = [
            # Events with null or empty game_id (should be excluded)
            {'game_id': None, 'event_type': 'GAME'},
            {'game_id': '', 'event_type': 'GAME'},
            # Valid playoff events (should be included)
            {'game_id': 'playoff_2025_wild_card_1', 'event_type': 'GAME'},
            {'game_id': 'playoff_2025_wild_card_2', 'event_type': 'GAME'},
        ]
        mock_event_db_api.get_events_by_dynasty.return_value = mock_events
        persistence = BracketPersistence(mock_event_db_api)

        # Act
        result = persistence.load_playoff_events(dynasty_id='test', season=2025)

        # Assert
        assert len(result) == 2
        for event in result:
            assert event['game_id'] is not None
            assert event['game_id'] != ''
            assert event['game_id'].startswith('playoff_')


class TestReconstructState:
    """Test the reconstruct_state method for rebuilding playoff bracket from database."""

    def test_reconstruct_state_creates_empty_state_for_no_events(self):
        """Should create empty PlayoffState when no playoff events exist."""
        # Arrange
        mock_event_db = Mock()
        persistence = BracketPersistence(mock_event_db)

        # Mock detect function (won't be called with empty list)
        def mock_detect(game_id):
            return None

        # Act
        state = persistence.reconstruct_state([], mock_detect)

        # Assert: state has zero games
        assert state.total_games_played == 0
        assert len(state.completed_games['wild_card']) == 0
        assert len(state.completed_games['divisional']) == 0
        assert len(state.completed_games['conference']) == 0
        assert len(state.completed_games['super_bowl']) == 0

    def test_reconstruct_state_populates_completed_games(self):
        """Should populate completed_games dict with game results."""
        # Arrange
        mock_event_db = Mock()
        persistence = BracketPersistence(mock_event_db)

        # Create 3 mock events with game results
        mock_events = [
            {
                "game_id": "playoff_2025_wild_card_1",
                "data": json.dumps({
                    "parameters": {"away_team_id": 1, "home_team_id": 2},
                    "results": {"away_score": 24, "home_score": 31}
                })
            },
            {
                "game_id": "playoff_2025_wild_card_2",
                "data": json.dumps({
                    "parameters": {"away_team_id": 3, "home_team_id": 4},
                    "results": {"away_score": 28, "home_score": 21}
                })
            },
            {
                "game_id": "playoff_2025_wild_card_3",
                "data": json.dumps({
                    "parameters": {"away_team_id": 5, "home_team_id": 6},
                    "results": {"away_score": 17, "home_score": 20}
                })
            }
        ]

        # Mock detect function
        def mock_detect(game_id):
            if 'wild_card' in game_id:
                return 'wild_card'
            return None

        # Act
        state = persistence.reconstruct_state(mock_events, mock_detect)

        # Assert: state has 3 completed games
        assert state.total_games_played == 3
        assert len(state.completed_games['wild_card']) == 3

    def test_reconstruct_state_uses_game_id_not_event_id(self):
        """Should use game_id (WC1, DIV2) as key, not event database ID."""
        # Arrange
        mock_event_db = Mock()
        persistence = BracketPersistence(mock_event_db)

        # Create event with game_id and different event_id (UUID)
        event_uuid = str(uuid.uuid4())
        mock_event = {
            "event_id": event_uuid,
            "game_id": "playoff_2025_wild_card_1",
            "data": json.dumps({
                "parameters": {"away_team_id": 1, "home_team_id": 2},
                "results": {"away_score": 24, "home_score": 31}
            })
        }

        # Mock detect function that tracks what it receives
        detect_calls = []
        def mock_detect(game_id):
            detect_calls.append(game_id)
            if 'wild_card' in game_id:
                return 'wild_card'
            return None

        # Act
        state = persistence.reconstruct_state([mock_event], mock_detect)

        # Assert: detect function was called with game_id, not event_id
        assert len(detect_calls) == 1
        assert detect_calls[0] == "playoff_2025_wild_card_1"
        assert detect_calls[0] != event_uuid

    def test_reconstruct_state_prevents_duplicates(self):
        """Should not add duplicate game entries if multiple events exist."""
        # Arrange
        mock_event_db = Mock()
        persistence = BracketPersistence(mock_event_db)

        # Create 2 events with same game_id
        same_game_id = "playoff_2025_wild_card_1"
        mock_events = [
            {
                "game_id": same_game_id,
                "data": json.dumps({
                    "parameters": {"away_team_id": 1, "home_team_id": 2},
                    "results": {"away_score": 24, "home_score": 31}
                })
            },
            {
                "game_id": same_game_id,
                "data": json.dumps({
                    "parameters": {"away_team_id": 1, "home_team_id": 2},
                    "results": {"away_score": 24, "home_score": 31}
                })
            }
        ]

        # Mock detect function
        def mock_detect(game_id):
            if 'wild_card' in game_id:
                return 'wild_card'
            return None

        # Act
        state = persistence.reconstruct_state(mock_events, mock_detect)

        # Assert: state has only 1 completed game (not 2)
        assert len(state.completed_games['wild_card']) == 1
        assert state.total_games_played == 1

    def test_reconstruct_state_determines_current_round(self):
        """Should correctly determine current_round based on completed games."""
        # Arrange
        mock_event_db = Mock()
        persistence = BracketPersistence(mock_event_db)

        # Create 6 completed wild card games (full round)
        mock_events = []
        for i in range(1, 7):
            mock_events.append({
                "game_id": f"playoff_2025_wild_card_{i}",
                "data": json.dumps({
                    "parameters": {"away_team_id": i, "home_team_id": i + 10},
                    "results": {"away_score": 20 + i, "home_score": 30 + i}
                })
            })

        # Mock detect function
        def mock_detect(game_id):
            if 'wild_card' in game_id:
                return 'wild_card'
            return None

        # Act
        state = persistence.reconstruct_state(mock_events, mock_detect)

        # Assert: current_round == 'divisional' (next round after wild card complete)
        assert state.current_round == 'divisional'
        assert len(state.completed_games['wild_card']) == 6

    def test_reconstruct_state_handles_partial_rounds(self):
        """Should handle rounds where some games are complete and others aren't."""
        # Arrange
        mock_event_db = Mock()
        persistence = BracketPersistence(mock_event_db)

        # Create only 3 wild card games (not all 6)
        mock_events = []
        for i in range(1, 4):
            mock_events.append({
                "game_id": f"playoff_2025_wild_card_{i}",
                "data": json.dumps({
                    "parameters": {"away_team_id": i, "home_team_id": i + 10},
                    "results": {"away_score": 20 + i, "home_score": 30 + i}
                })
            })

        # Mock detect function
        def mock_detect(game_id):
            if 'wild_card' in game_id:
                return 'wild_card'
            return None

        # Act
        state = persistence.reconstruct_state(mock_events, mock_detect)

        # Assert: current_round == 'wild_card' (not advanced because round incomplete)
        assert state.current_round == 'wild_card'
        assert len(state.completed_games['wild_card']) == 3
        assert state.total_games_played == 3

    def test_reconstruct_state_skips_scheduled_games_without_results(self):
        """Should not include scheduled games that haven't been simulated yet."""
        # Arrange
        mock_event_db = Mock()
        persistence = BracketPersistence(mock_event_db)

        # Create event with parameters but NO results field
        mock_event = {
            "game_id": "playoff_2025_wild_card_1",
            "data": json.dumps({
                "parameters": {"away_team_id": 1, "home_team_id": 2}
                # Note: NO "results" field
            })
        }

        # Mock detect function (won't be reached because event is skipped)
        def mock_detect(game_id):
            if 'wild_card' in game_id:
                return 'wild_card'
            return None

        # Act
        state = persistence.reconstruct_state([mock_event], mock_detect)

        # Assert: event is not added to completed_games
        assert state.total_games_played == 0
        assert len(state.completed_games['wild_card']) == 0

    def test_reconstruct_state_handles_invalid_round_names(self):
        """Should gracefully handle or skip events with invalid round names."""
        # Arrange
        mock_event_db = Mock()
        persistence = BracketPersistence(mock_event_db)

        # Create event that will have invalid round detected
        mock_event = {
            "game_id": "playoff_2025_invalid_round_1",
            "data": json.dumps({
                "parameters": {"away_team_id": 1, "home_team_id": 2},
                "results": {"away_score": 24, "home_score": 31}
            })
        }

        # Mock detect function that returns None for invalid rounds
        def mock_detect(game_id):
            if 'wild_card' in game_id:
                return 'wild_card'
            # Return None for invalid/unknown game_ids
            return None

        # Act
        state = persistence.reconstruct_state([mock_event], mock_detect)

        # Assert: events with invalid rounds are skipped
        assert state.total_games_played == 0
        assert len(state.completed_games['wild_card']) == 0
