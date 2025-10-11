"""
Player Controller for The Owner's Sim UI

Thin controller for player data operations.
Delegates all business logic to PlayerDataModel.
"""

from typing import List, Dict, Any, Optional
import sys
import os

# Add parent directories to path
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

from domain_models.player_data_model import PlayerDataModel


class PlayerController:
    """
    Controller for player view operations.

    Thin orchestration layer - all business logic delegated to PlayerDataModel.
    Follows pattern: View → Controller → Domain Model → Database API
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize player controller.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year (default: 2025)
        """
        self.data_model = PlayerDataModel(db_path, dynasty_id, season)

    def get_free_agents(self) -> List[Dict[str, Any]]:
        """
        Get all free agent players.

        Returns:
            List of player dictionaries formatted for UI display
        """
        return self.data_model.get_free_agents()

    def get_team_roster(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get roster for specific team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of player dictionaries for team roster
        """
        return self.data_model.get_team_roster(team_id)

    def get_player_by_id(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Get individual player details.

        Args:
            player_id: Player ID

        Returns:
            Player dictionary or None if not found
        """
        return self.data_model.get_player_by_id(player_id)

    def get_dynasty_info(self) -> Dict[str, Any]:
        """
        Get dynasty information.

        Returns:
            Dict with dynasty_id
        """
        return self.data_model.get_dynasty_info()
