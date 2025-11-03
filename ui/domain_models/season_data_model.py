"""
Season Data Model for The Owner's Sim UI

Domain model that encapsulates season data access, team management, and standings retrieval.
Owns all database API instances and provides clean data access interface for controllers.

Architecture:
    View Layer → Controller Layer → Domain Model Layer (THIS) → Database APIs

Responsibilities:
    - OWN: Database API instances (TeamDataLoader, DatabaseAPI, EventDatabaseAPI, etc.)
    - DO: All season data access, team queries, standings retrieval, schedule generation
    - RETURN: Clean DTOs/dicts to controllers
    - NO: Qt dependencies, UI concerns, user interaction handling
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from team_management.teams.team_loader import TeamDataLoader, Team
from database.api import DatabaseAPI
from events.event_database_api import EventDatabaseAPI
from database.connection import DatabaseConnection
from database.dynasty_state_api import DynastyStateAPI
from scheduling import RandomScheduleGenerator


class SeasonDataModel:
    """
    Domain model for season data access and team management.

    Encapsulates all business logic related to:
    - Team data retrieval (all teams, by ID, by division, by conference)
    - Standings access with error handling
    - Season state checking (has_season_data)
    - Schedule generation with dynasty state initialization
    - Team record queries

    This model owns all database API instances and provides a clean interface
    for controllers to access season-related data without direct database coupling.
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize season data model.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year (default: 2025)
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        # Initialize all database API instances (model owns these)
        self.team_loader = TeamDataLoader()
        self.db_api = DatabaseAPI(db_path)
        self.event_api = EventDatabaseAPI(db_path)
        self.db_connection = DatabaseConnection(db_path)
        self.dynasty_api = DynastyStateAPI(db_path)

    # ==================== Team Data Access ====================

    def get_all_teams(self) -> List[Team]:
        """
        Get all 32 NFL teams with complete metadata.

        Returns:
            List of Team objects containing:
            - team_id (1-32)
            - city, nickname, abbreviation
            - division, conference
            - colors (primary, secondary, tertiary)
            - stadium information
        """
        return self.team_loader.get_all_teams()

    def get_team_by_id(self, team_id: int) -> Optional[Team]:
        """
        Get team by numerical ID.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Team object with complete metadata, or None if not found

        Example:
            team = model.get_team_by_id(22)  # Detroit Lions
            if team:
                print(f"{team.city} {team.nickname}")
        """
        return self.team_loader.get_team_by_id(team_id)

    def get_teams_by_division(self, conference: str, division: str) -> List[Team]:
        """
        Get all teams in a specific division.

        Args:
            conference: 'AFC' or 'NFC'
            division: 'East', 'North', 'South', or 'West'

        Returns:
            List of Team objects in the specified division (4 teams)

        Example:
            nfc_north = model.get_teams_by_division('NFC', 'North')
            # Returns: Lions, Packers, Vikings, Bears
        """
        return self.team_loader.get_teams_by_division(conference, division)

    def get_teams_by_conference(self, conference: str) -> List[Team]:
        """
        Get all teams in a conference.

        Args:
            conference: 'AFC' or 'NFC'

        Returns:
            List of Team objects in the conference (16 teams)

        Example:
            afc_teams = model.get_teams_by_conference('AFC')
            # Returns all 16 AFC teams
        """
        return self.team_loader.get_teams_by_conference(conference)

    # ==================== Standings and Records ====================

    def get_team_standings(self) -> Dict[str, Any]:
        """
        Get current standings from database with comprehensive error handling.

        Queries the database for current season standings by dynasty and season.
        Handles missing data gracefully (e.g., season not initialized yet).

        Returns:
            Standings data structure organized by division/conference:
            {
                'AFC_East': {
                    'teams': [TeamStanding, ...],
                    'division': 'East',
                    'conference': 'AFC'
                },
                'NFC_North': { ... },
                ...
            }

            Returns empty dict {} if:
            - Season not initialized in database
            - No standings data exists for dynasty/season
            - Database query fails

        Note:
            This method prints error details to console but does not raise exceptions,
            allowing UI to handle missing data gracefully.
        """
        try:
            standings = self.db_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season
            )
            return standings
        except Exception as e:
            # Gracefully handle missing data - season might not be initialized yet
            print(f"[ERROR SeasonDataModel] No standings data available: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_team_record(self, team_id: int) -> Optional[Dict[str, int]]:
        """
        Get win-loss-tie record for a specific team.

        Searches through standings data to find the team's current record.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dictionary with team record:
            {
                'wins': int,
                'losses': int,
                'ties': int
            }

            Returns None if:
            - No standings data exists
            - Team not found in standings
            - Season not initialized

        Example:
            record = model.get_team_record(22)  # Detroit Lions
            if record:
                print(f"{record['wins']}-{record['losses']}-{record['ties']}")
        """
        standings = self.get_team_standings()

        if not standings:
            return None

        # Search through all divisions for this team
        for division_name, division_data in standings.items():
            if isinstance(division_data, dict) and 'teams' in division_data:
                for team_standing in division_data['teams']:
                    if team_standing.team_id == team_id:
                        return {
                            'wins': team_standing.wins,
                            'losses': team_standing.losses,
                            'ties': team_standing.ties
                        }

        return None

    def has_season_data(self) -> bool:
        """
        Check if season data exists in database.

        Convenience method to determine if the current dynasty/season
        has been initialized with standings data.

        Returns:
            True if standings data exists, False otherwise

        Use Cases:
            - Determine if "New Season" or "Continue Season" should be shown
            - Check if schedule generation is needed
            - Validate dynasty initialization state
        """
        standings = self.get_team_standings()
        return bool(standings)

    # ==================== Schedule Generation ====================

    def generate_initial_schedule(self, season_start_date: Optional[datetime] = None) -> Tuple[bool, Optional[str]]:
        """
        Generate initial season schedule for a new dynasty.

        Creates a complete 272-game NFL season schedule (17 weeks × 16 games per week)
        and initializes dynasty state with the season start date.

        This method should be called once when creating a new dynasty. It:
        1. Initializes dynasty_state table with season start date
        2. Checks if schedule already exists (prevents duplicates)
        3. Generates 272 game events using RandomScheduleGenerator
        4. Stores events in event database with dynasty isolation

        Args:
            season_start_date: Optional datetime for season start
                              Defaults to Sept 4, 12:00 AM (one day before first games)
                              This allows Sept 5 games to be simulated immediately

        Returns:
            Tuple[bool, Optional[str]]:
                - (True, None) if successful (schedule created or already exists)
                - (False, "error message") if generation failed

        Notes:
            - ALWAYS initializes dynasty_state (even if schedule exists)
            - Prevents race conditions where SimulationController creates state with wrong date
            - Safe to call multiple times (idempotent if schedule exists)

        Example:
            success, error = model.generate_initial_schedule()
            if success:
                print("Schedule ready!")
            else:
                print(f"Failed: {error}")
        """
        try:
            # Use default season start date if not provided (Aug 1, 12:00 AM)
            # Start dynasty at beginning of preseason
            if not season_start_date:
                season_start_date = datetime(self.season, 8, 1, 0, 0)

            # ALWAYS initialize dynasty state with season start date
            # This ensures dynasty_state exists even if schedule already generated
            # Prevents race condition where SimulationController creates it with wrong date
            self._initialize_dynasty_state(season_start_date)

            # Check if schedule already exists (avoid duplicate generation)
            existing_games = self.event_api.get_events_by_dynasty(
                dynasty_id=self.dynasty_id,
                event_type="GAME"
            )

            if existing_games:
                return (True, None)  # Schedule already exists, nothing to do

            # Create schedule generator
            generator = RandomScheduleGenerator(
                event_db=self.event_api,
                dynasty_id=self.dynasty_id
            )

            # === STEP 1: Generate PRESEASON schedule (48 games, 3 weeks) ===
            print(f"📅 Generating preseason schedule ({self.season})...")
            preseason_events = generator.generate_preseason(
                season_year=self.season,
                start_date=None  # Uses calculated preseason start (~3.5 weeks before regular season)
            )

            if not preseason_events:
                return (False, "Preseason schedule generation returned no events")

            print(f"✅ Preseason schedule generated: {len(preseason_events)} games")

            # === STEP 2: Generate REGULAR SEASON schedule (272 games, 17 weeks) ===
            print(f"📅 Generating regular season schedule ({self.season})...")
            schedule_events = generator.generate_season(
                season_year=self.season,
                start_date=None  # Uses dynamic Labor Day calculation (first Thursday after Labor Day)
            )

            if schedule_events:
                return (True, None)
            else:
                return (False, "Schedule generation returned no events")

        except Exception as e:
            error_msg = f"Failed to generate schedule: {str(e)}"
            print(f"[ERROR SeasonDataModel] {error_msg}")
            import traceback
            traceback.print_exc()
            return (False, error_msg)

    def _initialize_dynasty_state(self, season_start_date: datetime):
        """
        Initialize dynasty_state table with season start date.

        Uses DynastyStateAPI to safely initialize state with:
        - Defensive deletion of existing state (prevents duplicates)
        - Verification of successful write
        - Proper error handling

        Args:
            season_start_date: Season start datetime

        Notes:
            - Converts datetime to YYYY-MM-DD string format
            - Uses DynastyStateAPI.initialize_state() for safe initialization
            - Prints error to console if initialization fails
            - Does not raise exceptions (allows graceful failure)
        """
        # Convert datetime to YYYY-MM-DD string
        date_str = season_start_date.strftime('%Y-%m-%d')

        # Use DynastyStateAPI to initialize state (includes defensive delete + verification)
        # Start phase is PRESEASON because season_start_date is August 1 (preseason start)
        # Regular season starts in early September
        success = self.dynasty_api.initialize_state(
            dynasty_id=self.dynasty_id,
            season=self.season,
            start_date=date_str,
            start_week=1,
            start_phase='preseason'  # August 1 start = preseason, not regular season
        )

        if not success:
            print(f"[ERROR SeasonDataModel] Dynasty state initialization FAILED!")

    # ==================== Metadata Access ====================

    def get_dynasty_info(self) -> Dict[str, str]:
        """
        Get dynasty metadata.

        Returns:
            Dictionary containing:
            {
                'dynasty_id': str,  # Dynasty identifier
                'season': str       # Season year (e.g., '2025')
            }

        Example:
            info = model.get_dynasty_info()
            print(f"Dynasty: {info['dynasty_id']}, Season: {info['season']}")
        """
        return {
            'dynasty_id': self.dynasty_id,
            'season': str(self.season)
        }
