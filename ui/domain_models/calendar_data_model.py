"""
Calendar Data Model - Domain Model Pattern Reference Implementation

This module demonstrates the Domain Model pattern for The Owner's Sim UI architecture.

ARCHITECTURE PATTERN:
-------------------
The domain model serves as an intermediary layer between the UI Controller and the
database/business logic layer. It provides the following benefits:

1. SEPARATION OF CONCERNS
   - Controller: UI orchestration only (no business logic, no database access)
   - Domain Model: Business logic and database access
   - View: Display and user interaction only

2. TESTABILITY
   - Domain models can be tested independently without Qt/UI dependencies
   - Controllers become thin orchestrators that are easier to test
   - Clear contracts between layers

3. REUSABILITY
   - Business logic can be shared across multiple controllers/views
   - Database access patterns are centralized
   - No duplication of query logic

4. MAINTAINABILITY
   - Changes to business logic don't require controller changes
   - Database schema changes are isolated to domain models
   - Clear ownership of responsibilities

USAGE EXAMPLE:
-------------
    # In controller __init__:
    self.data_model = CalendarDataModel(
        db_path="data/database/nfl_simulation.db",
        dynasty_id="chiefs_dynasty",
        season=2025
    )

    # In controller methods:
    events = self.data_model.get_events_for_month(2025, 9)
    current_date = self.data_model.get_current_simulation_date()

IMPLEMENTATION NOTES:
--------------------
- NO Qt dependencies (can be tested without UI)
- NO UI concerns (colors, formatting, widgets)
- Returns clean data structures (dicts, lists)
- Owns all database API instances
- Contains all business logic and query patterns
- Type-hinted for clarity and IDE support
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from events.event_database_api import EventDatabaseAPI
from database.api import DatabaseAPI
from database.dynasty_state_api import DynastyStateAPI


class CalendarDataModel:
    """
    Domain model for calendar data access and business logic.

    This class demonstrates the Domain Model pattern by:
    - Owning all database API instances (EventDatabaseAPI, DatabaseAPI, DynastyStateAPI)
    - Encapsulating all business logic for calendar operations
    - Providing clean, testable interfaces without UI dependencies
    - Serving as a reference implementation for other domain models

    Responsibilities:
    - Query events from multiple database tables (events, games)
    - Merge and deduplicate event data from different sources
    - Convert database records to standardized event format
    - Handle date range calculations and timestamp conversions
    - Manage dynasty-specific data isolation

    Attributes:
        dynasty_id: Dynasty identifier for data isolation
        season: Current season year
        event_api: Event database API instance (owned by model)
        database_api: General database API instance (owned by model)
        dynasty_api: Dynasty state API instance (owned by model)
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize calendar data model.

        The domain model OWNS all database API instances. This ensures:
        - Single source of truth for database connections
        - Consistent dynasty/season context across queries
        - Clear ownership of data access responsibilities

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year (default: 2025)
        """
        self.dynasty_id = dynasty_id
        self.season = season

        # Domain model OWNS the database APIs
        # Controllers delegate all data access to this model
        self.event_api = EventDatabaseAPI(db_path)
        self.database_api = DatabaseAPI(db_path)
        self.dynasty_api = DynastyStateAPI(db_path)

    def get_events_for_month(
        self,
        year: int,
        month: int,
        event_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get filtered events for a specific month (both scheduled and completed).

        BUSINESS LOGIC:
        --------------
        This method demonstrates complex business logic that belongs in a domain model:

        1. Query multiple data sources (events table + games table)
        2. Merge data from different sources into unified format
        3. Deduplicate records (avoid showing same game twice)
        4. Convert timestamps between different formats
        5. Apply dynasty-specific filtering
        6. Sort and return standardized data structure

        WHY THIS BELONGS IN DOMAIN MODEL:
        ---------------------------------
        - Complex database queries involving multiple tables
        - Business rules (deduplication, format conversion)
        - No UI concerns (returns plain data structures)
        - Reusable across different controllers/views
        - Testable without Qt dependencies

        IMPLEMENTATION DETAILS:
        ----------------------
        Queries both events table (scheduled) and games table (completed) to provide
        a complete calendar view. Events that haven't been played yet come from events,
        while completed games come from games table with results.

        Args:
            year: Year to query
            month: Month to query (1-12)
            event_types: Optional list of event types to filter by
                        (e.g., ['GAME', 'DEADLINE', 'WINDOW'])
                        If None, returns all event types

        Returns:
            List of event dictionaries matching the criteria, ordered by timestamp.
            Each dict contains: event_id, event_type, timestamp, game_id, data

            Data structure:
            {
                'event_id': str,
                'event_type': str,
                'timestamp': int (milliseconds) or datetime,
                'game_id': str (optional),
                'dynasty_id': str,
                'data': {
                    'parameters': {...},
                    'results': {...},
                    'metadata': {...}
                }
            }
        """
        # Calculate first and last day of month
        # Use timedelta to avoid importing stdlib calendar (shadowed by src/calendar)
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(seconds=1)

        # Convert datetime to milliseconds for timestamp query
        start_ms = int(first_day.timestamp() * 1000)
        end_ms = int(last_day.timestamp() * 1000)

        all_items = []

        # 1. Get scheduled events from events table
        if event_types:
            # Query each event type separately with dynasty isolation
            for event_type in event_types:
                events = self.event_api.get_events_by_dynasty_and_timestamp(
                    dynasty_id=self.dynasty_id,
                    start_timestamp_ms=start_ms,
                    end_timestamp_ms=end_ms,
                    event_type=event_type
                )
                all_items.extend(events)
        else:
            # Query all event types with dynasty isolation
            events = self.event_api.get_events_by_dynasty_and_timestamp(
                dynasty_id=self.dynasty_id,
                start_timestamp_ms=start_ms,
                end_timestamp_ms=end_ms
            )
            all_items.extend(events)

        # 2. Get completed games from games table
        # Only if GAME events are being requested (or all events)
        if not event_types or 'GAME' in event_types:
            completed_games = self.database_api.get_games_by_date_range(
                dynasty_id=self.dynasty_id,
                start_timestamp_ms=start_ms,
                end_timestamp_ms=end_ms
            )

            # Convert game records to event-like format for calendar display
            for game in completed_games:
                # Skip if this game already exists in events (avoid duplicates)
                game_id = game['game_id']
                if any(e.get('game_id') == game_id for e in all_items):
                    continue

                # Convert game to event format
                game_event = {
                    'event_id': f"completed_{game_id}",
                    'event_type': 'GAME',
                    'timestamp': game['game_date'],  # Use game_date timestamp
                    'game_id': game_id,
                    'dynasty_id': self.dynasty_id,
                    'data': {
                        'parameters': {
                            'home_team_id': game['home_team_id'],
                            'away_team_id': game['away_team_id'],
                            'week': game['week'],
                            'season': game['season'],
                            'season_type': game['season_type'],
                            'game_type': game['game_type']
                        },
                        'results': {
                            'home_score': game['home_score'],
                            'away_score': game['away_score'],
                            'total_plays': game['total_plays'],
                            'game_duration_minutes': game['game_duration_minutes'],
                            'overtime_periods': game['overtime_periods'],
                            'completed': True  # Mark as completed
                        },
                        'metadata': {
                            'description': f"Week {game['week']}: Completed Game"
                        }
                    }
                }
                all_items.append(game_event)

        # Sort all items by timestamp (handle both datetime and milliseconds)
        def get_sort_key(item):
            """Convert timestamp to sortable format."""
            ts = item['timestamp']
            if isinstance(ts, datetime):
                return ts.timestamp()  # Convert to float seconds
            elif isinstance(ts, (int, float)):
                return ts / 1000.0  # Convert milliseconds to seconds
            else:
                return 0  # Fallback for unexpected types

        all_items.sort(key=get_sort_key)

        return all_items

    def get_current_simulation_date(self) -> Optional[str]:
        """
        Get current simulation date from dynasty_state table.

        BUSINESS LOGIC:
        --------------
        This method encapsulates database query logic for simulation state.

        WHY THIS BELONGS IN DOMAIN MODEL:
        ---------------------------------
        - Direct database query (dynasty_state table)
        - No UI concerns
        - Reusable across multiple controllers
        - Testable without Qt

        Returns:
            Current simulation date as string (YYYY-MM-DD) or None if not found
        """
        return self.dynasty_api.get_current_date(self.dynasty_id, self.season)

    def get_event_details(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full event details by ID.

        BUSINESS LOGIC:
        --------------
        Handles both regular event IDs and synthetic event IDs:
        - Regular event IDs: Query events table directly
        - Synthetic event IDs (starts with "completed_"): Reconstruct from games table

        Args:
            event_id: Unique identifier of the event

        Returns:
            Event dictionary if found, None if not found.
            Dict contains: event_id, event_type, timestamp, game_id, data
        """
        # Check if this is a synthetic event_id from completed games
        if event_id.startswith('completed_'):
            # Extract game_id from synthetic event_id: "completed_game_20250908_1_at_12" -> "game_20250908_1_at_12"
            game_id = event_id.replace('completed_', '', 1)

            # Query games table directly
            query = '''
                SELECT
                    game_id,
                    game_date,
                    season,
                    week,
                    season_type,
                    game_type,
                    home_team_id,
                    away_team_id,
                    home_score,
                    away_score,
                    total_plays,
                    game_duration_minutes,
                    overtime_periods
                FROM games
                WHERE game_id = ? AND dynasty_id = ?
            '''

            results = self.database_api.db_connection.execute_query(
                query,
                (game_id, self.dynasty_id)
            )

            if not results or len(results) == 0:
                return None

            game = results[0]

            # Reconstruct event structure (same format as get_events_for_month)
            return {
                'event_id': event_id,
                'event_type': 'GAME',
                'timestamp': game['game_date'],
                'game_id': game_id,
                'dynasty_id': self.dynasty_id,
                'data': {
                    'parameters': {
                        'home_team_id': game['home_team_id'],
                        'away_team_id': game['away_team_id'],
                        'week': game['week'],
                        'season': game['season'],
                        'season_type': game['season_type'],
                        'game_type': game['game_type']
                    },
                    'results': {
                        'home_score': game['home_score'],
                        'away_score': game['away_score'],
                        'winner_id': None,  # Could calculate from scores if needed
                        'winner_name': None,
                        'total_plays': game['total_plays'],
                        'total_drives': None,  # Not stored in games table
                        'game_duration_minutes': game['game_duration_minutes'],
                        'simulation_time': None,  # Not stored in games table
                        'overtime_periods': game['overtime_periods'],
                        'completed': True
                    },
                    'metadata': {
                        'matchup_description': f"Week {game['week']}: Team {game['away_team_id']} @ Team {game['home_team_id']}",
                        'is_playoff_game': game['season_type'] == 'playoffs',
                        'game_id': game_id
                    }
                }
            }

        # Regular event_id - query events table
        return self.event_api.get_event_by_id(event_id)

    def get_dynasty_info(self) -> Dict[str, str]:
        """
        Get dynasty information.

        Returns:
            Dict with dynasty_id and season as strings
        """
        return {
            'dynasty_id': self.dynasty_id,
            'season': str(self.season)
        }
