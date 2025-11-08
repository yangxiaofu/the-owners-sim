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
        print(f"[CALENDAR_DEBUG] Querying events table: dynasty={self.dynasty_id}, year={year}, month={month}")
        print(f"[CALENDAR_DEBUG] Timestamp range: {start_ms} to {end_ms}")
        print(f"[CALENDAR_DEBUG] Event types filter: {event_types}")

        if event_types:
            # Query each event type separately with dynasty isolation
            for event_type in event_types:
                events = self.event_api.get_events_by_dynasty_and_timestamp(
                    dynasty_id=self.dynasty_id,
                    start_timestamp_ms=start_ms,
                    end_timestamp_ms=end_ms,
                    event_type=event_type
                )
                print(f"[CALENDAR_DEBUG] Events table returned {len(events)} events for type '{event_type}'")
                all_items.extend(events)
        else:
            # Query all event types with dynasty isolation
            events = self.event_api.get_events_by_dynasty_and_timestamp(
                dynasty_id=self.dynasty_id,
                start_timestamp_ms=start_ms,
                end_timestamp_ms=end_ms
            )
            print(f"[CALENDAR_DEBUG] Events table returned {len(events)} events (all types)")
            all_items.extend(events)

        print(f"[CALENDAR_DEBUG] Total events from events table: {len(all_items)}")
        for i, event in enumerate(all_items[:5]):  # Show first 5
            print(f"  Event {i+1}: game_id={event.get('game_id', 'N/A')}, type={event.get('event_type', 'N/A')}")

        # 2. Get completed games from games table (for historical game data)
        if not event_types or 'GAME' in event_types:
            print(f"[CALENDAR_DEBUG] Querying games table for completed games...")
            completed_games = self.database_api.get_games_by_date_range(
                dynasty_id=self.dynasty_id,
                start_timestamp_ms=start_ms,
                end_timestamp_ms=end_ms
            )

            # Convert sqlite3.Row objects to dicts for .get() compatibility
            completed_games = [dict(game) for game in completed_games]
            print(f"[CALENDAR_DEBUG] Games table returned {len(completed_games)} completed games")
            for i, game in enumerate(completed_games[:5]):  # Show first 5
                print(f"  Game {i+1}: game_id={game.get('game_id', 'N/A')}, season_type={game.get('season_type', 'N/A')}")

            # Track BOTH game_ids and event_ids for robust deduplication (O(1) lookup)
            # This handles cases where:
            # 1. Events have event_id = game_id (scheduled games)
            # 2. Events have event_id = "completed_{game_id}" (from games table)
            # 3. Events have different event_id but same game_id
            seen_game_ids = {e.get('game_id') for e in all_items if e.get('game_id')}
            seen_event_ids = {e.get('event_id') for e in all_items if e.get('event_id')}
            print(f"[CALENDAR_DEBUG] Deduplication: {len(seen_game_ids)} game_ids, {len(seen_event_ids)} event_ids already seen from events table")

            # Convert game records to event-like format for calendar display
            games_added_from_table = 0
            games_skipped_duplicate = 0
            for game in completed_games:
                game_id = game.get('game_id')
                computed_event_id = f"completed_{game_id}"

                # Skip if ANY of these conditions are true (comprehensive deduplication):
                # 1. game_id already exists (same game from events table)
                # 2. computed_event_id already exists (duplicate from games table)
                # 3. game_id exists as event_id (scheduled game in events table where event_id == game_id)
                if (game_id in seen_game_ids or
                    computed_event_id in seen_event_ids or
                    game_id in seen_event_ids):
                    games_skipped_duplicate += 1
                    print(f"[CALENDAR_DEBUG] Skipping duplicate: game_id={game_id} (already in events)")
                    continue

                # Mark as seen to prevent duplicates within this loop
                seen_game_ids.add(game_id)
                seen_event_ids.add(computed_event_id)
                games_added_from_table += 1

                # Convert game to event format
                # Build event from game data with proper structure
                game_event = {
                    'event_id': f"completed_{game_id}",
                    'event_type': 'GAME',
                    'timestamp': game.get('game_date'),
                    'game_id': game_id,
                    'dynasty_id': self.dynasty_id,
                    'data': {
                        'parameters': {
                            'away_team_id': game.get('away_team_id'),
                            'home_team_id': game.get('home_team_id'),
                            'week': game.get('week'),
                            'season_type': game.get('season_type', 'regular')
                        },
                        'results': {
                            'away_score': game.get('away_score'),
                            'home_score': game.get('home_score'),
                            'winner_team_id': game.get('winner_team_id')
                        },
                        'metadata': {
                            'completed': True,
                            'source': 'games_table'
                        }
                    }
                }
                all_items.append(game_event)

            print(f"[CALENDAR_DEBUG] Games from games table: {games_added_from_table} added, {games_skipped_duplicate} skipped (duplicates)")
            print(f"[CALENDAR_DEBUG] Final item count before sorting: {len(all_items)}")

        # FINAL SAFETY CHECK: Deduplicate all_items by game_id to ensure no duplicates slip through
        # This handles edge cases where duplicates might come from multiple sources
        items_before_final_dedup = len(all_items)
        seen_final = set()
        deduplicated_items = []
        for item in all_items:
            game_id = item.get('game_id')
            event_id = item.get('event_id')
            # Use game_id as primary identifier, event_id as fallback
            identifier = game_id if game_id else event_id
            if identifier and identifier not in seen_final:
                seen_final.add(identifier)
                deduplicated_items.append(item)
            elif not identifier:
                # No identifier - keep it (non-game event)
                deduplicated_items.append(item)
            else:
                print(f"[CALENDAR_DEBUG] Final dedup: Removed duplicate {identifier}")

        all_items = deduplicated_items
        items_removed_final = items_before_final_dedup - len(all_items)
        if items_removed_final > 0:
            print(f"[CALENDAR_DEBUG] Final deduplication removed {items_removed_final} duplicate(s)")

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

        print(f"[CALENDAR_DEBUG] Returning {len(all_items)} total events for {year}-{month:02d}")
        # Show first 10 items with their game_ids
        for i, item in enumerate(all_items[:10]):
            ts = item.get('timestamp')
            if isinstance(ts, datetime):
                ts_str = ts.strftime('%Y-%m-%d %H:%M')
            elif isinstance(ts, (int, float)):
                ts_str = datetime.fromtimestamp(ts / 1000.0).strftime('%Y-%m-%d %H:%M')
            else:
                ts_str = 'unknown'
            print(f"  Item {i+1}: game_id={item.get('game_id', 'N/A')[:30]}, type={item.get('event_type')}, time={ts_str}")

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
        Query events table directly for event details. All game events
        (both scheduled and completed) are stored in the events table with
        complete data including results.

        Args:
            event_id: Unique identifier of the event

        Returns:
            Event dictionary if found, None if not found.
            Dict contains: event_id, event_type, timestamp, game_id, data
        """
        # Query events table for event details
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
