"""
Offseason Demo Domain Models

Domain models for the UI demo that query mock data from the demo database.
These models provide clean interfaces for the UI to interact with offseason,
calendar, and team data.

Architecture:
- All models use dynasty_id="ui_offseason_demo"
- All models query from the demo database path
- Models match the interface expected by existing UI views
- No UI dependencies (pure business logic and data access)

Usage:
    # In controller or demo script:
    offseason_model = OffseasonDemoDataModel(
        database_path="demo/offseason_demo/offseason_demo.db",
        dynasty_id="ui_offseason_demo",
        season_year=2025,
        user_team_id=22  # Detroit Lions
    )

    current_phase = offseason_model.get_current_phase()
    deadlines = offseason_model.get_upcoming_deadlines(5)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from offseason.offseason_controller import OffseasonController
from offseason.offseason_phases import OffseasonPhase
from events.event_database_api import EventDatabaseAPI
from database.api import DatabaseAPI
from database.dynasty_state_api import DynastyStateAPI
from salary_cap.cap_database_api import CapDatabaseAPI


class OffseasonDemoDataModel:
    """
    Domain model for offseason operations in the UI demo.

    Wraps OffseasonController to provide UI-friendly interface for
    offseason state, deadlines, and calendar advancement.

    All operations use dynasty_id="ui_offseason_demo" and query from
    the demo database initialized by setup_offseason_demo.py.

    Responsibilities:
    - Track current offseason phase
    - Manage upcoming deadlines
    - Advance calendar (day-by-day or to specific deadline)
    - Provide comprehensive state summary
    - Delegate complex operations to OffseasonController
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        season_year: int,
        user_team_id: int
    ):
        """
        Initialize offseason demo data model.

        Args:
            database_path: Path to demo database
            dynasty_id: Dynasty identifier (should be "ui_offseason_demo")
            season_year: Season year (2025)
            user_team_id: User's team ID (1-32)
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.season_year = season_year
        self.user_team_id = user_team_id

        # Initialize OffseasonController for offseason operations
        self.controller = OffseasonController(
            database_path=database_path,
            dynasty_id=dynasty_id,
            season_year=season_year,
            user_team_id=user_team_id,
            enable_persistence=True,
            verbose_logging=False  # Disable verbose output for UI
        )

    def get_current_phase(self) -> str:
        """
        Get current offseason phase.

        Returns:
            Phase name as string (e.g., "franchise_tag_period")
        """
        phase = self.controller.get_current_phase()
        return phase.value

    def get_current_phase_display_name(self) -> str:
        """
        Get human-readable current phase name.

        Returns:
            Display name (e.g., "Franchise Tag Period")
        """
        phase = self.controller.get_current_phase()
        return OffseasonPhase.get_display_name(phase)

    def get_current_date(self) -> datetime:
        """
        Get current calendar date.

        Returns:
            Current simulation date
        """
        return self.controller.get_current_date()

    def get_upcoming_deadlines(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get upcoming deadlines with days remaining.

        Args:
            limit: Maximum number of deadlines to return

        Returns:
            List of deadline dictionaries:
            {
                'type': str,
                'date': date,
                'description': str,
                'days_remaining': int
            }
        """
        return self.controller.get_upcoming_deadlines(limit=limit)

    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive current state summary.

        Returns:
            Dictionary with:
            - dynasty_id: Dynasty identifier
            - season_year: Season year
            - current_date: Current calendar date
            - current_phase: Current phase string
            - current_phase_display: Human-readable phase name
            - offseason_complete: Boolean
            - upcoming_deadlines: List of next 3 deadlines
            - actions_taken: Count of actions taken
        """
        summary = self.controller.get_state_summary()

        # Add display name for current phase
        phase = self.controller.get_current_phase()
        summary['current_phase_display'] = OffseasonPhase.get_display_name(phase)

        return summary

    def advance_day(self) -> Dict[str, Any]:
        """
        Advance calendar by 1 day and trigger events.

        Returns:
            Dictionary with:
            - new_date: Updated calendar date
            - phase_changed: Whether phase changed
            - new_phase: New phase if changed (None otherwise)
            - deadlines_passed: List of deadline types passed
            - events_triggered: List of automatic events
        """
        return self.controller.advance_day()

    def advance_to_deadline(self, deadline_type: str) -> Dict[str, Any]:
        """
        Jump calendar to next occurrence of specified deadline.

        Args:
            deadline_type: Type of deadline (e.g., "FRANCHISE_TAG_DEADLINE")

        Returns:
            Dictionary with:
            - deadline_type: Type of deadline reached
            - deadline_date: Date of deadline
            - days_advanced: Number of days advanced
            - current_phase: New current phase
            - events_triggered: List of automatic events

        Raises:
            ValueError: If deadline type not found or already passed
        """
        return self.controller.advance_to_deadline(deadline_type)

    def is_offseason_complete(self) -> bool:
        """
        Check if offseason is complete (ready for next season).

        Returns:
            True if offseason complete, False otherwise
        """
        return self.controller.is_offseason_complete()


class CalendarDemoDataModel:
    """
    Domain model for calendar operations in the UI demo.

    Provides access to scheduled events and completed games from the
    demo database for calendar display.

    Responsibilities:
    - Query events by month or date range
    - Retrieve event details by ID
    - Merge events from events table and games table
    - Filter by event type
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        season: int = 2025
    ):
        """
        Initialize calendar demo data model.

        Args:
            database_path: Path to demo database
            dynasty_id: Dynasty identifier (should be "ui_offseason_demo")
            season: Current season year
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.season = season

        # Initialize database APIs
        self.event_api = EventDatabaseAPI(database_path)
        self.database_api = DatabaseAPI(database_path)
        self.dynasty_api = DynastyStateAPI(database_path)

    def get_events_for_month(
        self,
        year: int,
        month: int,
        event_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all events for a specific month.

        Queries both events table (scheduled) and games table (completed)
        to provide complete calendar view.

        Args:
            year: Year to query
            month: Month to query (1-12)
            event_types: Optional list to filter by event type
                        (e.g., ['GAME', 'DEADLINE', 'WINDOW'])

        Returns:
            List of event dictionaries ordered by timestamp
        """
        from datetime import datetime, timedelta

        # Calculate month boundaries
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(seconds=1)

        start_ms = int(first_day.timestamp() * 1000)
        end_ms = int(last_day.timestamp() * 1000)

        all_items = []

        # Query events table with dynasty isolation
        if event_types:
            for event_type in event_types:
                events = self.event_api.get_events_by_dynasty_and_timestamp(
                    dynasty_id=self.dynasty_id,
                    start_timestamp_ms=start_ms,
                    end_timestamp_ms=end_ms,
                    event_type=event_type
                )
                all_items.extend(events)
        else:
            events = self.event_api.get_events_by_dynasty_and_timestamp(
                dynasty_id=self.dynasty_id,
                start_timestamp_ms=start_ms,
                end_timestamp_ms=end_ms
            )
            all_items.extend(events)

        # Query games table for completed games
        if not event_types or 'GAME' in event_types:
            completed_games = self.database_api.get_games_by_date_range(
                dynasty_id=self.dynasty_id,
                start_timestamp_ms=start_ms,
                end_timestamp_ms=end_ms
            )

            # Convert games to event format and deduplicate
            seen_game_ids = {e.get('game_id') for e in all_items if e.get('game_id')}

            for game in completed_games:
                game = dict(game)  # Convert sqlite3.Row to dict
                game_id = game.get('game_id')

                if game_id in seen_game_ids:
                    continue

                seen_game_ids.add(game_id)

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
                            'home_score': game.get('home_score')
                        },
                        'metadata': {
                            'completed': True,
                            'source': 'games_table'
                        }
                    }
                }
                all_items.append(game_event)

        # Sort by timestamp
        def get_sort_key(item):
            ts = item['timestamp']
            if isinstance(ts, datetime):
                return ts.timestamp()
            elif isinstance(ts, (int, float)):
                return ts / 1000.0
            else:
                return 0

        all_items.sort(key=get_sort_key)
        return all_items

    def get_events_for_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        event_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get events within a date range.

        Args:
            start_date: Start of range (inclusive)
            end_date: End of range (inclusive)
            event_types: Optional list to filter by event type

        Returns:
            List of event dictionaries ordered by timestamp
        """
        start_ms = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)

        all_items = []

        # Query events table
        if event_types:
            for event_type in event_types:
                events = self.event_api.get_events_by_dynasty_and_timestamp(
                    dynasty_id=self.dynasty_id,
                    start_timestamp_ms=start_ms,
                    end_timestamp_ms=end_ms,
                    event_type=event_type
                )
                all_items.extend(events)
        else:
            events = self.event_api.get_events_by_dynasty_and_timestamp(
                dynasty_id=self.dynasty_id,
                start_timestamp_ms=start_ms,
                end_timestamp_ms=end_ms
            )
            all_items.extend(events)

        # Query games table for completed games
        if not event_types or 'GAME' in event_types:
            completed_games = self.database_api.get_games_by_date_range(
                dynasty_id=self.dynasty_id,
                start_timestamp_ms=start_ms,
                end_timestamp_ms=end_ms
            )

            seen_game_ids = {e.get('game_id') for e in all_items if e.get('game_id')}

            for game in completed_games:
                game = dict(game)
                game_id = game.get('game_id')

                if game_id in seen_game_ids:
                    continue

                seen_game_ids.add(game_id)

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
                            'home_score': game.get('home_score')
                        },
                        'metadata': {
                            'completed': True,
                            'source': 'games_table'
                        }
                    }
                }
                all_items.append(game_event)

        # Sort by timestamp
        def get_sort_key(item):
            ts = item['timestamp']
            if isinstance(ts, datetime):
                return ts.timestamp()
            elif isinstance(ts, (int, float)):
                return ts / 1000.0
            else:
                return 0

        all_items.sort(key=get_sort_key)
        return all_items

    def get_event_details(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full details for a specific event.

        Args:
            event_id: Unique identifier of event

        Returns:
            Event dictionary if found, None otherwise
        """
        return self.event_api.get_event_by_id(event_id)

    def get_all_offseason_events(self) -> List[Dict[str, Any]]:
        """
        Get all scheduled offseason events (deadlines, windows, milestones).

        Returns:
            List of all offseason event dictionaries
        """
        # Query all events for dynasty that are not GAME events
        all_events = self.event_api.get_events_by_dynasty(
            dynasty_id=self.dynasty_id
        )

        # Filter to offseason-related events
        offseason_event_types = {
            'DEADLINE', 'WINDOW', 'MILESTONE',
            'FRANCHISE_TAG', 'UFA_SIGNING', 'PLAYER_RELEASE',
            'CONTRACT_RESTRUCTURE', 'RFA_OFFER_SHEET'
        }

        offseason_events = [
            e for e in all_events
            if e.get('event_type') in offseason_event_types
        ]

        return offseason_events


class TeamDemoDataModel:
    """
    Domain model for team data in the UI demo.

    Provides access to team information, roster, cap space, and
    upcoming free agents from the demo database.

    Responsibilities:
    - Query team metadata
    - Retrieve team roster
    - Calculate cap space
    - Identify upcoming free agents
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        season: int = 2025
    ):
        """
        Initialize team demo data model.

        Args:
            database_path: Path to demo database
            dynasty_id: Dynasty identifier (should be "ui_offseason_demo")
            season: Current season year
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.season = season

        # Initialize database APIs
        self.database_api = DatabaseAPI(database_path)
        self.cap_api = CapDatabaseAPI(database_path)

    def get_team_info(self, team_id: int) -> Dict[str, Any]:
        """
        Get team metadata (name, division, conference, etc.).

        Args:
            team_id: Team identifier (1-32)

        Returns:
            Team info dictionary
        """
        # Hard-coded team data for demo (Detroit Lions = 22)
        # In production, load from teams.json or database
        team_db = {
            22: {
                'name': 'Detroit Lions',
                'abbreviation': 'DET',
                'city': 'Detroit',
                'division': 'NFC North',
                'conference': 'NFC',
                'primary_color': '#0076B6',
                'secondary_color': '#B0B7BC'
            }
        }

        # Return default data for other teams
        team_data = team_db.get(team_id, {
            'name': f'Team {team_id}',
            'abbreviation': f'T{team_id}',
            'city': f'City {team_id}',
            'division': 'Unknown',
            'conference': 'Unknown',
            'primary_color': '#000000',
            'secondary_color': '#FFFFFF'
        })

        return {
            'team_id': team_id,
            'name': team_data['name'],
            'abbreviation': team_data['abbreviation'],
            'city': team_data['city'],
            'division': team_data['division'],
            'conference': team_data['conference'],
            'primary_color': team_data['primary_color'],
            'secondary_color': team_data['secondary_color']
        }

    def get_team_roster(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get team roster (mock data for demo).

        In production, this would query actual roster from database.
        For demo, returns placeholder roster structure.

        Args:
            team_id: Team identifier (1-32)

        Returns:
            List of player dictionaries (mock data)
        """
        # Mock roster for demo purposes
        # In production, query from players table
        return [
            {
                'player_id': f'player_{team_id}_1',
                'name': 'Starting QB',
                'position': 'QB',
                'jersey_number': 9,
                'depth_position': 1,
                'years_in_league': 5,
                'contract_years_remaining': 2,
                'contract_avg_value': 45_000_000
            },
            {
                'player_id': f'player_{team_id}_2',
                'name': 'Star RB',
                'position': 'RB',
                'jersey_number': 26,
                'depth_position': 1,
                'years_in_league': 3,
                'contract_years_remaining': 0,  # UFA
                'contract_avg_value': 8_000_000
            },
            {
                'player_id': f'player_{team_id}_3',
                'name': 'Elite WR',
                'position': 'WR',
                'jersey_number': 18,
                'depth_position': 1,
                'years_in_league': 6,
                'contract_years_remaining': 1,
                'contract_avg_value': 18_000_000
            }
        ]

    def get_team_cap_space(self, team_id: int) -> Dict[str, Any]:
        """
        Get team salary cap information.

        Uses mock data for demo ($200M cap, $170-190M used).
        In production, would query from cap_database_api.

        Args:
            team_id: Team identifier (1-32)

        Returns:
            Cap space dictionary:
            {
                'cap_limit': int,
                'cap_used': int,
                'cap_space': int,
                'top_51_total': int,
                'contracts_count': int
            }
        """
        # Mock cap data for demo
        # Vary cap usage by team_id for realism
        import random
        random.seed(team_id)  # Deterministic per team

        cap_limit = 200_000_000
        cap_used = random.randint(170_000_000, 190_000_000)

        return {
            'cap_limit': cap_limit,
            'cap_used': cap_used,
            'cap_space': cap_limit - cap_used,
            'top_51_total': cap_used,
            'contracts_count': random.randint(48, 53),
            'projected_cap_space': cap_limit - cap_used + random.randint(5_000_000, 15_000_000)
        }

    def get_team_upcoming_free_agents(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get players with expiring contracts (upcoming UFAs).

        Mock data for demo. In production, query contracts table.

        Args:
            team_id: Team identifier (1-32)

        Returns:
            List of UFA player dictionaries
        """
        # Mock UFA list for demo
        return [
            {
                'player_id': f'ufa_{team_id}_1',
                'name': 'Star RB',
                'position': 'RB',
                'age': 26,
                'years_with_team': 3,
                'last_contract_aav': 8_000_000,
                'estimated_market_value': 12_000_000,
                'priority': 'HIGH',
                'recommendation': 'Re-sign or franchise tag'
            },
            {
                'player_id': f'ufa_{team_id}_2',
                'name': 'Backup LB',
                'position': 'LB',
                'age': 29,
                'years_with_team': 4,
                'last_contract_aav': 3_500_000,
                'estimated_market_value': 4_000_000,
                'priority': 'MEDIUM',
                'recommendation': 'Let test market'
            }
        ]
