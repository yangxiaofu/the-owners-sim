"""
Events Query Builder - Centralized SQL query patterns for events table.

This module provides static methods that return properly formatted SQL queries
for the events table, with correct CAST handling for JSON field comparisons.

CRITICAL: All queries that compare JSON-extracted integers (week, season, team_id)
MUST use CAST to avoid type coercion bugs:
    CAST(json_extract(data, '$.parameters.week') AS INTEGER) = ?

Design Pattern:
- Each method returns a tuple of (query_string, description)
- Queries use parameter placeholders (?) for safety
- Dynasty isolation is enforced in all queries
- Week/season comparisons use CAST for type safety
"""

from typing import Tuple


class EventsQueryBuilder:
    """
    Static query builder for events table operations.

    Centralizes all events table query patterns to ensure:
    1. Consistent CAST usage for JSON integer comparisons
    2. Dynasty isolation in all queries
    3. Single source of truth for query patterns
    """

    @staticmethod
    def get_games_by_week(
        include_results: bool = True
    ) -> Tuple[str, str]:
        """
        Get all games for a specific week, season, and season type.

        Args:
            include_results: If True, returns full data field; if False, returns only schedule info

        Returns:
            Tuple of (query_string, description)

        Query Parameters (in order):
            - dynasty_id (str)
            - season (int)
            - week (int)
            - season_type (str): 'regular_season', 'preseason', or 'playoffs'

        Example Usage:
            query, desc = EventsQueryBuilder.get_games_by_week()
            cursor.execute(query, (dynasty_id, season, week, season_type))
        """
        if include_results:
            query = """
                SELECT event_id, game_id, data
                FROM events
                WHERE dynasty_id = ?
                AND event_type = 'GAME'
                AND CAST(json_extract(data, '$.parameters.season') AS INTEGER) = ?
                AND CAST(json_extract(data, '$.parameters.week') AS INTEGER) = ?
                AND json_extract(data, '$.parameters.season_type') = ?
                ORDER BY json_extract(data, '$.parameters.game_date'), game_id
            """
        else:
            query = """
                SELECT event_id, game_id,
                       json_extract(data, '$.parameters.home_team_id') AS home_team_id,
                       json_extract(data, '$.parameters.away_team_id') AS away_team_id,
                       json_extract(data, '$.parameters.game_date') AS game_date
                FROM events
                WHERE dynasty_id = ?
                AND event_type = 'GAME'
                AND CAST(json_extract(data, '$.parameters.season') AS INTEGER) = ?
                AND CAST(json_extract(data, '$.parameters.week') AS INTEGER) = ?
                AND json_extract(data, '$.parameters.season_type') = ?
                ORDER BY json_extract(data, '$.parameters.game_date'), game_id
            """

        description = "Get all games for a specific week"
        return query, description

    @staticmethod
    def get_games_by_season(
        include_results: bool = True
    ) -> Tuple[str, str]:
        """
        Get all games for an entire season and season type.

        Useful for copying schedules between seasons or analyzing full season data.

        Args:
            include_results: If True, returns full data field; if False, returns only schedule info

        Returns:
            Tuple of (query_string, description)

        Query Parameters (in order):
            - dynasty_id (str)
            - season (int)
            - season_type (str): 'regular_season', 'preseason', or 'playoffs'

        Example Usage:
            query, desc = EventsQueryBuilder.get_games_by_season()
            cursor.execute(query, (dynasty_id, season, season_type))
        """
        if include_results:
            query = """
                SELECT event_id, game_id, data
                FROM events
                WHERE dynasty_id = ?
                AND event_type = 'GAME'
                AND CAST(json_extract(data, '$.parameters.season') AS INTEGER) = ?
                AND json_extract(data, '$.parameters.season_type') = ?
                ORDER BY CAST(json_extract(data, '$.parameters.week') AS INTEGER), game_id
            """
        else:
            query = """
                SELECT event_id, game_id,
                       json_extract(data, '$.parameters.week') AS week,
                       json_extract(data, '$.parameters.home_team_id') AS home_team_id,
                       json_extract(data, '$.parameters.away_team_id') AS away_team_id,
                       json_extract(data, '$.parameters.game_date') AS game_date
                FROM events
                WHERE dynasty_id = ?
                AND event_type = 'GAME'
                AND CAST(json_extract(data, '$.parameters.season') AS INTEGER) = ?
                AND json_extract(data, '$.parameters.season_type') = ?
                ORDER BY CAST(json_extract(data, '$.parameters.week') AS INTEGER), game_id
            """

        description = "Get all games for an entire season"
        return query, description

    @staticmethod
    def get_game_by_id() -> Tuple[str, str]:
        """
        Get a single game by its event_id.

        Returns:
            Tuple of (query_string, description)

        Query Parameters (in order):
            - dynasty_id (str)
            - event_id (str)

        Example Usage:
            query, desc = EventsQueryBuilder.get_game_by_id()
            cursor.execute(query, (dynasty_id, event_id))
        """
        query = """
            SELECT event_id, game_id, data
            FROM events
            WHERE dynasty_id = ?
            AND event_id = ?
            AND event_type = 'GAME'
        """

        description = "Get a single game by event ID"
        return query, description

    @staticmethod
    def get_game_by_game_id() -> Tuple[str, str]:
        """
        Get a single game by its game_id.

        Note: game_id is unique within a dynasty, but event_id is globally unique.

        Returns:
            Tuple of (query_string, description)

        Query Parameters (in order):
            - dynasty_id (str)
            - game_id (str)

        Example Usage:
            query, desc = EventsQueryBuilder.get_game_by_game_id()
            cursor.execute(query, (dynasty_id, game_id))
        """
        query = """
            SELECT event_id, game_id, data
            FROM events
            WHERE dynasty_id = ?
            AND game_id = ?
            AND event_type = 'GAME'
        """

        description = "Get a single game by game ID"
        return query, description

    @staticmethod
    def get_games_by_team(
        include_results: bool = True
    ) -> Tuple[str, str]:
        """
        Get all games for a specific team in a season.

        Finds games where team is either home or away.

        Args:
            include_results: If True, returns full data field; if False, returns only schedule info

        Returns:
            Tuple of (query_string, description)

        Query Parameters (in order):
            - dynasty_id (str)
            - season (int)
            - season_type (str): 'regular_season', 'preseason', or 'playoffs'
            - team_id (int) - used twice (home and away check)

        Example Usage:
            query, desc = EventsQueryBuilder.get_games_by_team()
            cursor.execute(query, (dynasty_id, season, season_type, team_id, team_id))
        """
        if include_results:
            query = """
                SELECT event_id, game_id, data
                FROM events
                WHERE dynasty_id = ?
                AND event_type = 'GAME'
                AND CAST(json_extract(data, '$.parameters.season') AS INTEGER) = ?
                AND json_extract(data, '$.parameters.season_type') = ?
                AND (
                    CAST(json_extract(data, '$.parameters.home_team_id') AS INTEGER) = ?
                    OR CAST(json_extract(data, '$.parameters.away_team_id') AS INTEGER) = ?
                )
                ORDER BY CAST(json_extract(data, '$.parameters.week') AS INTEGER), game_id
            """
        else:
            query = """
                SELECT event_id, game_id,
                       json_extract(data, '$.parameters.week') AS week,
                       json_extract(data, '$.parameters.home_team_id') AS home_team_id,
                       json_extract(data, '$.parameters.away_team_id') AS away_team_id,
                       json_extract(data, '$.parameters.game_date') AS game_date
                FROM events
                WHERE dynasty_id = ?
                AND event_type = 'GAME'
                AND CAST(json_extract(data, '$.parameters.season') AS INTEGER) = ?
                AND json_extract(data, '$.parameters.season_type') = ?
                AND (
                    CAST(json_extract(data, '$.parameters.home_team_id') AS INTEGER) = ?
                    OR CAST(json_extract(data, '$.parameters.away_team_id') AS INTEGER) = ?
                )
                ORDER BY CAST(json_extract(data, '$.parameters.week') AS INTEGER), game_id
            """

        description = "Get all games for a specific team in a season"
        return query, description

    @staticmethod
    def get_preseason_games(
        week: int = None
    ) -> Tuple[str, str]:
        """
        Get preseason games for a dynasty and season.

        Args:
            week: If provided, filter to specific week; otherwise get all preseason games

        Returns:
            Tuple of (query_string, description)

        Query Parameters (in order):
            - dynasty_id (str)
            - season (int)
            - week (int) - only if week parameter is not None

        Example Usage:
            # All preseason games
            query, desc = EventsQueryBuilder.get_preseason_games()
            cursor.execute(query, (dynasty_id, season))

            # Specific preseason week
            query, desc = EventsQueryBuilder.get_preseason_games(week=2)
            cursor.execute(query, (dynasty_id, season, 2))
        """
        if week is not None:
            query = """
                SELECT data
                FROM events
                WHERE dynasty_id = ?
                AND event_type = 'GAME'
                AND CAST(json_extract(data, '$.parameters.season') AS INTEGER) = ?
                AND json_extract(data, '$.parameters.season_type') = 'preseason'
                AND CAST(json_extract(data, '$.parameters.week') AS INTEGER) = ?
                ORDER BY timestamp
            """
            description = "Get preseason games for a specific week"
        else:
            query = """
                SELECT data
                FROM events
                WHERE dynasty_id = ?
                AND event_type = 'GAME'
                AND CAST(json_extract(data, '$.parameters.season') AS INTEGER) = ?
                AND json_extract(data, '$.parameters.season_type') = 'preseason'
                ORDER BY CAST(json_extract(data, '$.parameters.week') AS INTEGER), timestamp
            """
            description = "Get all preseason games for a season"

        return query, description

    @staticmethod
    def get_playoff_games(
        season: int = None
    ) -> Tuple[str, str]:
        """
        Get playoff games for a dynasty.

        Args:
            season: If provided, filter to specific season; otherwise get all playoff games

        Returns:
            Tuple of (query_string, description)

        Query Parameters (in order):
            - dynasty_id (str)
            - season (int) - only if season parameter is not None

        Example Usage:
            # All playoff games
            query, desc = EventsQueryBuilder.get_playoff_games()
            cursor.execute(query, (dynasty_id,))

            # Specific season playoffs
            query, desc = EventsQueryBuilder.get_playoff_games(season=2025)
            cursor.execute(query, (dynasty_id, 2025))
        """
        if season is not None:
            query = """
                SELECT event_id, game_id, data
                FROM events
                WHERE dynasty_id = ?
                AND event_type = 'GAME'
                AND json_extract(data, '$.parameters.season_type') = 'playoffs'
                AND CAST(json_extract(data, '$.parameters.season') AS INTEGER) = ?
                ORDER BY CAST(json_extract(data, '$.parameters.week') AS INTEGER), game_id
            """
            description = "Get all playoff games for a specific season"
        else:
            query = """
                SELECT event_id, game_id, data
                FROM events
                WHERE dynasty_id = ?
                AND event_type = 'GAME'
                AND json_extract(data, '$.parameters.season_type') = 'playoffs'
                ORDER BY CAST(json_extract(data, '$.parameters.season') AS INTEGER),
                         CAST(json_extract(data, '$.parameters.week') AS INTEGER),
                         game_id
            """
            description = "Get all playoff games across all seasons"

        return query, description

    @staticmethod
    def count_games_by_criteria() -> Tuple[str, str]:
        """
        Count games matching specific criteria.

        Useful for validation and testing.

        Returns:
            Tuple of (query_string, description)

        Query Parameters (in order):
            - dynasty_id (str)
            - season (int)
            - season_type (str): 'regular_season', 'preseason', or 'playoffs'

        Example Usage:
            query, desc = EventsQueryBuilder.count_games_by_criteria()
            cursor.execute(query, (dynasty_id, season, season_type))
            count = cursor.fetchone()[0]
        """
        query = """
            SELECT COUNT(*)
            FROM events
            WHERE dynasty_id = ?
            AND event_type = 'GAME'
            AND CAST(json_extract(data, '$.parameters.season') AS INTEGER) = ?
            AND json_extract(data, '$.parameters.season_type') = ?
        """

        description = "Count games for a season and season type"
        return query, description

    @staticmethod
    def get_scheduled_games_without_results() -> Tuple[str, str]:
        """
        Get all scheduled games that haven't been played yet.

        Useful for finding upcoming games.

        Returns:
            Tuple of (query_string, description)

        Query Parameters (in order):
            - dynasty_id (str)
            - season (int)
            - season_type (str): 'regular_season', 'preseason', or 'playoffs'

        Example Usage:
            query, desc = EventsQueryBuilder.get_scheduled_games_without_results()
            cursor.execute(query, (dynasty_id, season, season_type))
        """
        query = """
            SELECT event_id, game_id, data
            FROM events
            WHERE dynasty_id = ?
            AND event_type = 'GAME'
            AND CAST(json_extract(data, '$.parameters.season') AS INTEGER) = ?
            AND json_extract(data, '$.parameters.season_type') = ?
            AND json_extract(data, '$.results') IS NULL
            ORDER BY CAST(json_extract(data, '$.parameters.week') AS INTEGER), game_id
        """

        description = "Get scheduled games without results"
        return query, description

    @staticmethod
    def get_completed_games() -> Tuple[str, str]:
        """
        Get all completed games (games with results).

        Useful for stats aggregation and historical analysis.

        Returns:
            Tuple of (query_string, description)

        Query Parameters (in order):
            - dynasty_id (str)
            - season (int)
            - season_type (str): 'regular_season', 'preseason', or 'playoffs'

        Example Usage:
            query, desc = EventsQueryBuilder.get_completed_games()
            cursor.execute(query, (dynasty_id, season, season_type))
        """
        query = """
            SELECT event_id, game_id, data
            FROM events
            WHERE dynasty_id = ?
            AND event_type = 'GAME'
            AND CAST(json_extract(data, '$.parameters.season') AS INTEGER) = ?
            AND json_extract(data, '$.parameters.season_type') = ?
            AND json_extract(data, '$.results') IS NOT NULL
            ORDER BY CAST(json_extract(data, '$.parameters.week') AS INTEGER), game_id
        """

        description = "Get completed games with results"
        return query, description

    @staticmethod
    def update_game_result() -> Tuple[str, str]:
        """
        Get current game data for updating with results.

        This is the read portion of the update operation.

        Returns:
            Tuple of (query_string, description)

        Query Parameters (in order):
            - event_id (str)
            - dynasty_id (str)

        Example Usage:
            query, desc = EventsQueryBuilder.update_game_result()
            cursor.execute(query, (event_id, dynasty_id))
        """
        query = """
            SELECT data
            FROM events
            WHERE event_id = ?
            AND dynasty_id = ?
        """

        description = "Get current game data for update"
        return query, description

    @staticmethod
    def get_all_events_by_type() -> Tuple[str, str]:
        """
        Get all events of a specific type for a dynasty.

        Generic query for any event type (GAME, DRAFT_DAY, etc.).

        Returns:
            Tuple of (query_string, description)

        Query Parameters (in order):
            - dynasty_id (str)
            - event_type (str): 'GAME', 'DRAFT_DAY', etc.

        Example Usage:
            query, desc = EventsQueryBuilder.get_all_events_by_type()
            cursor.execute(query, (dynasty_id, 'DRAFT_DAY'))
        """
        query = """
            SELECT event_id, event_type, data, timestamp
            FROM events
            WHERE dynasty_id = ?
            AND event_type = ?
            ORDER BY timestamp DESC
        """

        description = "Get all events of a specific type"
        return query, description
