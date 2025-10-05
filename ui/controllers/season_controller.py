"""
Season Controller for The Owner's Sim UI

Mediates between Season View and simulation engine components.
Provides access to team data, standings, and season management.
"""

from typing import List, Dict, Any, Optional
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from team_management.teams.team_loader import TeamDataLoader, Team
from database.api import DatabaseAPI


class SeasonController:
    """
    Controller for Season view operations.

    Manages team data retrieval, standings access, and season state.
    Follows the pattern: View → Controller → Engine/Database
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize season controller.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year (default: 2025)
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        # Initialize data access components
        self.team_loader = TeamDataLoader()
        self.db_api = DatabaseAPI(db_path)

    def get_all_teams(self) -> List[Team]:
        """
        Get all 32 NFL teams with metadata.

        Returns:
            List of Team objects with city, nickname, division, conference, etc.
        """
        return self.team_loader.get_all_teams()

    def get_team_by_id(self, team_id: int) -> Optional[Team]:
        """
        Get team by numerical ID.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Team object or None if not found
        """
        return self.team_loader.get_team_by_id(team_id)

    def get_teams_by_division(self, conference: str, division: str) -> List[Team]:
        """
        Get teams by division.

        Args:
            conference: 'AFC' or 'NFC'
            division: 'East', 'North', 'South', or 'West'

        Returns:
            List of Team objects in the division
        """
        return self.team_loader.get_teams_by_division(conference, division)

    def get_teams_by_conference(self, conference: str) -> List[Team]:
        """
        Get teams by conference.

        Args:
            conference: 'AFC' or 'NFC'

        Returns:
            List of Team objects in the conference
        """
        return self.team_loader.get_teams_by_conference(conference)

    def get_team_standings(self) -> Dict[str, Any]:
        """
        Get current standings from database.

        Returns:
            Standings data structure with division/conference standings.
            Returns empty dict if no season initialized in database.
        """
        print(f"[DEBUG SeasonController] get_team_standings() called")
        print(f"[DEBUG SeasonController] Dynasty: {self.dynasty_id}, Season: {self.season}")

        try:
            print(f"[DEBUG SeasonController] Calling db_api.get_standings()")
            standings = self.db_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season
            )
            print(f"[DEBUG SeasonController] Standings returned: type={type(standings)}, keys={standings.keys() if standings else 'None'}")
            return standings
        except Exception as e:
            # Gracefully handle missing data - season might not be initialized yet
            print(f"[ERROR SeasonController] No standings data available: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_team_record(self, team_id: int) -> Optional[Dict[str, int]]:
        """
        Get win-loss-tie record for a specific team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with 'wins', 'losses', 'ties' or None if no data available
        """
        standings = self.get_team_standings()

        if not standings:
            return None

        # Search through divisions for this team
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

        Returns:
            True if standings data exists, False otherwise
        """
        standings = self.get_team_standings()
        return bool(standings)

    def get_dynasty_info(self) -> Dict[str, str]:
        """
        Get dynasty information.

        Returns:
            Dict with dynasty_id and season
        """
        return {
            'dynasty_id': self.dynasty_id,
            'season': str(self.season)
        }
