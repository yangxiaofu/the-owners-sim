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

    def get_team_contracts(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get team contracts with player information.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of contract dictionaries formatted for finances display
        """
        return self.data_model.get_team_contracts(team_id)

    def get_cap_summary(self, team_id: int) -> Dict[str, Any]:
        """
        Get salary cap summary for team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with cap_total, cap_used, cap_available, top_51_status, roster_count, etc.
        """
        return self.data_model.get_cap_summary(team_id)

    def get_depth_chart(self, team_id: int) -> Dict[str, Any]:
        """
        Get complete depth chart for team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict mapping position to sorted player list:
            {
                'quarterback': [player1, player2, ...],
                'running_back': [...],
                ...
            }
        """
        return self.data_model.get_full_depth_chart(team_id)

    def reorder_depth_chart(self, team_id: int, position: str, ordered_player_ids: List[int]) -> bool:
        """
        Reorder depth chart for a specific position.

        Args:
            team_id: Team ID (1-32)
            position: Position name (e.g., "quarterback", "running_back")
            ordered_player_ids: List of player IDs in desired depth chart order

        Returns:
            True if reorder succeeded, False otherwise
        """
        return self.data_model.reorder_position_depth_chart(team_id, position, ordered_player_ids)

    def swap_starter_with_bench(
        self,
        team_id: int,
        position: str,
        starter_id: int,
        bench_id: int
    ) -> bool:
        """
        Swap starter with bench player at same position.

        This performs a pure swap - the two players exchange their exact
        depth chart positions. The starter moves to bench, bench moves to starter.

        Args:
            team_id: Team ID (1-32)
            position: Position name (e.g., "quarterback", "running_back")
            starter_id: Current starter's player ID
            bench_id: Bench player's player ID

        Returns:
            True if swap succeeded, False otherwise
        """
        return self.data_model.swap_player_depths(team_id, starter_id, bench_id)

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
