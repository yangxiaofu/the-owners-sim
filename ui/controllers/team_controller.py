"""
Team Controller for The Owner's Sim UI

Mediates between Team View and team management components.
Provides access to team roster, salary cap, depth chart, and coaching staff.
"""

from typing import List, Dict, Any, Optional

from ui.domain_models.team_data_model import TeamDataModel


class TeamController:
    """
    Controller for Team view operations.

    Manages team roster, cap summary, depth chart, and coaching staff access.
    Follows the pattern: View → Controller → Domain Model → Database API
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize team controller.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year (default: 2025)
        """
        self.data_model = TeamDataModel(db_path, dynasty_id, season)

    def get_team_roster(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get team roster with all player data.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of player dictionaries with position, attributes, contract info
        """
        return self.data_model.get_team_roster(team_id)

    def get_cap_summary(self, team_id: int) -> Dict[str, Any]:
        """
        Get salary cap summary for team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with cap_total, cap_used, cap_available, top_51_status
        """
        return self.data_model.get_cap_summary(team_id)

    def get_depth_chart(self, team_id: int) -> Dict[str, Any]:
        """
        Get depth chart for team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with position-grouped player depth chart (empty dict for now)
        """
        return self.data_model.get_depth_chart(team_id)

    def get_coaching_staff(self, team_id: int) -> Dict[str, Any]:
        """
        Get coaching staff for team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with head coach, coordinators, position coaches (empty dict for now)
        """
        return self.data_model.get_coaching_staff(team_id)

    def get_dynasty_team_id(self) -> Optional[int]:
        """
        Get the user's team ID for this dynasty.

        Returns:
            Team ID (1-32) if dynasty has a user team, None for commissioner mode
        """
        return self.data_model.get_dynasty_team_id()

    def get_dynasty_info(self) -> Dict[str, Any]:
        """
        Get dynasty information.

        Returns:
            Dict with dynasty_id and season
        """
        return {
            "dynasty_id": self.data_model.dynasty_id,
            "season": self.data_model.season
        }
