"""
Unit Tests for DatabaseAPI

Tests database API operations including:
- Playoff event counting
- Dynasty isolation verification
- Season filtering
- Event type filtering
"""

import pytest
from datetime import datetime
from database.api import DatabaseAPI
from database.connection import DatabaseConnection
from events.event_database_api import EventDatabaseAPI
from events.game_event import GameEvent


@pytest.fixture
def database_api(test_db_path, test_dynasty_id):
    """
    Provides DatabaseAPI instance with test database.

    Initializes database with events table schema and ensures
    the test dynasty exists.
    """
    # Initialize database connection and schema
    db_conn = DatabaseConnection(test_db_path)
    db_conn.ensure_dynasty_exists(test_dynasty_id)

    # Return DatabaseAPI instance
    return DatabaseAPI(test_db_path)


@pytest.fixture
def event_database_api(test_db_path, test_dynasty_id):
    """
    Provides EventDatabaseAPI instance for inserting test events.
    """
    # Ensure dynasty exists first
    db_conn = DatabaseConnection(test_db_path)
    db_conn.ensure_dynasty_exists(test_dynasty_id)

    return EventDatabaseAPI(test_db_path)


class TestCountPlayoffEvents:
    """Test count_playoff_events() method."""

    def test_zero_playoff_events(self, database_api, test_dynasty_id, test_season):
        """Test counting when no playoff events exist."""
        count = database_api.count_playoff_events(
            dynasty_id=test_dynasty_id,
            season_year=test_season
        )

        assert count == 0

    def test_single_playoff_event(self, database_api, event_database_api,
                                   test_dynasty_id, test_season):
        """Test counting a single playoff event."""
        # Create and insert playoff event
        game_event = GameEvent(
            away_team_id=9,
            home_team_id=7,
            game_date=datetime(2025, 1, 13),
            week=19,
            dynasty_id=test_dynasty_id,
            game_id=f'playoff_{test_season}_wild_card_1',
            season=test_season,
            season_type='playoffs'
        )
        event_database_api.insert_event(game_event)

        count = database_api.count_playoff_events(
            dynasty_id=test_dynasty_id,
            season_year=test_season
        )

        assert count == 1

    def test_multiple_playoff_events(self, database_api, event_database_api,
                                     test_dynasty_id, test_season):
        """Test counting multiple playoff events (Wild Card round)."""
        # Insert 6 Wild Card games (3 AFC + 3 NFC)
        playoff_games = [
            (f'playoff_{test_season}_wild_card_1', 7, 9),   # NFC game 1
            (f'playoff_{test_season}_wild_card_2', 8, 10),  # NFC game 2
            (f'playoff_{test_season}_wild_card_3', 11, 12), # NFC game 3
            (f'playoff_{test_season}_wild_card_4', 1, 2),   # AFC game 1
            (f'playoff_{test_season}_wild_card_5', 3, 4),   # AFC game 2
            (f'playoff_{test_season}_wild_card_6', 5, 6),   # AFC game 3
        ]

        for game_id, home_team, away_team in playoff_games:
            game_event = GameEvent(
                away_team_id=away_team,
                home_team_id=home_team,
                game_date=datetime(2025, 1, 13),
                week=19,
                dynasty_id=test_dynasty_id,
                game_id=game_id,
                season=test_season,
                season_type='playoffs'
            )
            event_database_api.insert_event(game_event)

        count = database_api.count_playoff_events(
            dynasty_id=test_dynasty_id,
            season_year=test_season
        )

        assert count == 6

    def test_full_playoff_bracket(self, database_api, event_database_api,
                                  test_dynasty_id, test_season):
        """Test counting all playoff rounds (Wild Card through Super Bowl)."""
        # Wild Card: 6 games
        for i in range(1, 7):
            game_event = GameEvent(
                away_team_id=i + 10,
                home_team_id=i,
                game_date=datetime(2025, 1, 13),
                week=19,
                dynasty_id=test_dynasty_id,
                game_id=f'playoff_{test_season}_wild_card_{i}',
                season=test_season,
                season_type='playoffs'
            )
            event_database_api.insert_event(game_event)

        # Divisional: 4 games
        for i in range(1, 5):
            game_event = GameEvent(
                away_team_id=i + 5,
                home_team_id=i,
                game_date=datetime(2025, 1, 20),
                week=20,
                dynasty_id=test_dynasty_id,
                game_id=f'playoff_{test_season}_divisional_{i}',
                season=test_season,
                season_type='playoffs'
            )
            event_database_api.insert_event(game_event)

        # Conference: 2 games
        for i in range(1, 3):
            game_event = GameEvent(
                away_team_id=i + 2,
                home_team_id=i,
                game_date=datetime(2025, 1, 27),
                week=21,
                dynasty_id=test_dynasty_id,
                game_id=f'playoff_{test_season}_conference_{i}',
                season=test_season,
                season_type='playoffs'
            )
            event_database_api.insert_event(game_event)

        # Super Bowl: 1 game
        game_event = GameEvent(
            away_team_id=2,
            home_team_id=1,
            game_date=datetime(2025, 2, 10),
            week=22,
            dynasty_id=test_dynasty_id,
            game_id=f'playoff_{test_season}_super_bowl',
            season=test_season,
            season_type='playoffs'
        )
        event_database_api.insert_event(game_event)

        count = database_api.count_playoff_events(
            dynasty_id=test_dynasty_id,
            season_year=test_season
        )

        # Total: 6 + 4 + 2 + 1 = 13 playoff games
        assert count == 13

    def test_regular_season_games_excluded(self, database_api, event_database_api,
                                           test_dynasty_id, test_season):
        """Test that regular season games are not counted as playoff events."""
        # Insert regular season games
        for week in range(1, 19):
            game_event = GameEvent(
                away_team_id=9,
                home_team_id=7,
                game_date=datetime(2024, 9, week),
                week=week,
                dynasty_id=test_dynasty_id,
                game_id=f'regular_{test_season}_week_{week}_game_1',
                season=test_season,
                season_type='regular_season'
            )
            event_database_api.insert_event(game_event)

        # Insert playoff game
        game_event = GameEvent(
            away_team_id=9,
            home_team_id=7,
            game_date=datetime(2025, 1, 13),
            week=19,
            dynasty_id=test_dynasty_id,
            game_id=f'playoff_{test_season}_wild_card_1',
            season=test_season,
            season_type='playoffs'
        )
        event_database_api.insert_event(game_event)

        count = database_api.count_playoff_events(
            dynasty_id=test_dynasty_id,
            season_year=test_season
        )

        # Should only count the 1 playoff game, not the 18 regular season games
        assert count == 1


class TestDynastyIsolation:
    """Test dynasty isolation for playoff event counting."""

    def test_different_dynasties_isolated(self, database_api, event_database_api,
                                         test_season):
        """Test that playoff events are isolated by dynasty."""
        dynasty_1 = "dynasty_1"
        dynasty_2 = "dynasty_2"

        # Ensure both dynasties exist
        db_conn = database_api.db_connection
        db_conn.ensure_dynasty_exists(dynasty_1)
        db_conn.ensure_dynasty_exists(dynasty_2)

        # Insert 3 playoff games in dynasty 1
        for i in range(1, 4):
            game_event = GameEvent(
                away_team_id=i + 10,
                home_team_id=i,
                game_date=datetime(2025, 1, 13),
                week=19,
                dynasty_id=dynasty_1,
                game_id=f'playoff_{test_season}_wild_card_{i}',
                season=test_season,
                season_type='playoffs'
            )
            event_database_api.insert_event(game_event)

        # Insert 5 playoff games in dynasty 2
        for i in range(1, 6):
            game_event = GameEvent(
                away_team_id=i + 10,
                home_team_id=i,
                game_date=datetime(2025, 1, 13),
                week=19,
                dynasty_id=dynasty_2,
                game_id=f'playoff_{test_season}_wild_card_{i}',
                season=test_season,
                season_type='playoffs'
            )
            event_database_api.insert_event(game_event)

        # Verify isolation
        count_1 = database_api.count_playoff_events(dynasty_id=dynasty_1, season_year=test_season)
        count_2 = database_api.count_playoff_events(dynasty_id=dynasty_2, season_year=test_season)

        assert count_1 == 3
        assert count_2 == 5

    def test_same_game_id_different_dynasties(self, database_api, event_database_api,
                                              test_season):
        """Test that same game_id in different dynasties doesn't cause conflicts."""
        dynasty_1 = "dynasty_1"
        dynasty_2 = "dynasty_2"

        # Ensure both dynasties exist
        db_conn = database_api.db_connection
        db_conn.ensure_dynasty_exists(dynasty_1)
        db_conn.ensure_dynasty_exists(dynasty_2)

        # Insert same game_id in dynasty 1
        game_event_1 = GameEvent(
            away_team_id=9,
            home_team_id=7,
            game_date=datetime(2025, 1, 13),
            week=19,
            dynasty_id=dynasty_1,
            game_id=f'playoff_{test_season}_wild_card_1',
            season=test_season,
            season_type='playoffs'
        )
        event_database_api.insert_event(game_event_1)

        # Insert same game_id in dynasty 2
        game_event_2 = GameEvent(
            away_team_id=9,
            home_team_id=7,
            game_date=datetime(2025, 1, 13),
            week=19,
            dynasty_id=dynasty_2,
            game_id=f'playoff_{test_season}_wild_card_1',
            season=test_season,
            season_type='playoffs'
        )
        event_database_api.insert_event(game_event_2)

        # Each dynasty should count only its own game
        count_1 = database_api.count_playoff_events(dynasty_id=dynasty_1, season_year=test_season)
        count_2 = database_api.count_playoff_events(dynasty_id=dynasty_2, season_year=test_season)

        assert count_1 == 1
        assert count_2 == 1


class TestSeasonFiltering:
    """Test season filtering for playoff event counting."""

    def test_different_seasons_isolated(self, database_api, event_database_api,
                                       test_dynasty_id):
        """Test that playoff events are filtered by season."""
        season_2024 = 2024
        season_2025 = 2025

        # Insert 3 playoff games in 2024
        for i in range(1, 4):
            game_event = GameEvent(
                away_team_id=i + 10,
                home_team_id=i,
                game_date=datetime(2024, 1, 13),
                week=19,
                dynasty_id=test_dynasty_id,
                game_id=f'playoff_{season_2024}_wild_card_{i}',
                season=season_2024,
                season_type='playoffs'
            )
            event_database_api.insert_event(game_event)

        # Insert 5 playoff games in 2025
        for i in range(1, 6):
            game_event = GameEvent(
                away_team_id=i + 10,
                home_team_id=i,
                game_date=datetime(2025, 1, 13),
                week=19,
                dynasty_id=test_dynasty_id,
                game_id=f'playoff_{season_2025}_wild_card_{i}',
                season=season_2025,
                season_type='playoffs'
            )
            event_database_api.insert_event(game_event)

        # Verify season filtering
        count_2024 = database_api.count_playoff_events(
            dynasty_id=test_dynasty_id,
            season_year=season_2024
        )
        count_2025 = database_api.count_playoff_events(
            dynasty_id=test_dynasty_id,
            season_year=season_2025
        )

        assert count_2024 == 3
        assert count_2025 == 5

    def test_no_events_in_future_season(self, database_api, event_database_api,
                                       test_dynasty_id, test_season):
        """Test counting playoff events for a season with no events."""
        # Insert playoff game in current season
        game_event = GameEvent(
            away_team_id=9,
            home_team_id=7,
            game_date=datetime(2025, 1, 13),
            week=19,
            dynasty_id=test_dynasty_id,
            game_id=f'playoff_{test_season}_wild_card_1',
            season=test_season,
            season_type='playoffs'
        )
        event_database_api.insert_event(game_event)

        # Check future season (no games scheduled yet)
        count_future = database_api.count_playoff_events(
            dynasty_id=test_dynasty_id,
            season_year=test_season + 1
        )

        assert count_future == 0
