"""
Season Controller for The Owner's Sim UI

Mediates between Season View and simulation engine components.
Provides access to team data, standings, and season management.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ui.domain_models.season_data_model import SeasonDataModel
from team_management.teams.team_loader import Team


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
        self.data_model = SeasonDataModel(db_path, dynasty_id, season)

    def get_all_teams(self) -> List[Team]:
        """
        Get all 32 NFL teams with metadata.

        Returns:
            List of Team objects with city, nickname, division, conference, etc.
        """
        return self.data_model.get_all_teams()

    def get_team_by_id(self, team_id: int) -> Optional[Team]:
        """
        Get team by numerical ID.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Team object or None if not found
        """
        return self.data_model.get_team_by_id(team_id)

    def get_teams_by_division(self, conference: str, division: str) -> List[Team]:
        """
        Get teams by division.

        Args:
            conference: 'AFC' or 'NFC'
            division: 'East', 'North', 'South', or 'West'

        Returns:
            List of Team objects in the division
        """
        return self.data_model.get_teams_by_division(conference, division)

    def get_teams_by_conference(self, conference: str) -> List[Team]:
        """
        Get teams by conference.

        Args:
            conference: 'AFC' or 'NFC'

        Returns:
            List of Team objects in the conference
        """
        return self.data_model.get_teams_by_conference(conference)

    def get_team_standings(self) -> Dict[str, Any]:
        """
        Get current standings from database.

        Returns:
            Standings data structure with division/conference standings.
            Returns empty dict if no season initialized in database.
        """
        return self.data_model.get_team_standings()

    def get_team_record(self, team_id: int) -> Optional[Dict[str, int]]:
        """
        Get win-loss-tie record for a specific team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with 'wins', 'losses', 'ties' or None if no data available
        """
        return self.data_model.get_team_record(team_id)

    def has_season_data(self) -> bool:
        """
        Check if season data exists in database.

        Returns:
            True if standings data exists, False otherwise
        """
        return self.data_model.has_season_data()

    def get_dynasty_info(self) -> Dict[str, str]:
        """
        Get dynasty information.

        Returns:
            Dict with dynasty_id and season
        """
        return self.data_model.get_dynasty_info()

    def generate_initial_schedule(self, season_start_date: Optional[datetime] = None) -> Tuple[bool, Optional[str]]:
        """
        Generate initial season schedule for a new dynasty.

        Creates a complete 272-game NFL season schedule and initializes dynasty state.
        Should be called once when creating a new dynasty.

        Args:
            season_start_date: Season start datetime (defaults to Sept 5, 8:00 PM)

        Returns:
            Tuple of (success, error_message)
            - (True, None) if successful
            - (False, "error message") if failed
        """
        return self.data_model.generate_initial_schedule(season_start_date)
