"""
Playoff Controller for The Owner's Sim UI

Mediates between Playoff View and playoff system data.
Provides access to playoff bracket, seeding, and game information.
"""

from typing import List, Dict, Any, Optional
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from ui.domain_models.playoff_data_model import PlayoffDataModel


class PlayoffController:
    """
    Controller for Playoff view operations.

    Manages playoff bracket retrieval, seeding information, and round game access.
    Follows the pattern: View → Controller → Domain Model → Database/PlayoffController

    This is a thin orchestrator that delegates ALL business logic to PlayoffDataModel.
    NO database access, NO playoff logic - pure delegation layer.
    """

    def __init__(self, simulation_controller):
        """
        Initialize playoff controller.

        Args:
            simulation_controller: SimulationController instance that owns SeasonCycleController
        """
        # Initialize domain model (handles all playoff data access and business logic)
        # Pass simulation_controller which contains all necessary context
        self.data_model = PlayoffDataModel(simulation_controller)

    def get_seeding(self) -> Optional[Dict[str, Any]]:
        """
        Get current playoff seeding information.

        Returns:
            Dict with AFC and NFC seeding data, or None if playoffs not active:
            {
                'afc': [
                    {'seed': 1, 'team_id': int, 'team_name': str, 'record': str, ...},
                    ...
                ],
                'nfc': [...]
            }
        """
        return self.data_model.get_playoff_seeding()

    def get_bracket(self) -> Optional[Dict[str, Any]]:
        """
        Get current playoff bracket structure.

        Returns:
            Dict with complete bracket data organized by round:
            {
                'wild_card': {'afc': [...], 'nfc': [...]},
                'divisional': {'afc': [...], 'nfc': [...]},
                'conference': {'afc': {...}, 'nfc': {...}},
                'super_bowl': {...}
            }
            or None if playoffs not active
        """
        return self.data_model.get_bracket_data()

    def get_round_games(self, round_name: str) -> List[Dict[str, Any]]:
        """
        Get all games for a specific playoff round.

        Args:
            round_name: Round name ('wild_card', 'divisional', 'conference', 'super_bowl')

        Returns:
            List of game dictionaries with team info, scores, and completion status:
            [
                {
                    'away_team_id': int,
                    'home_team_id': int,
                    'away_score': Optional[int],
                    'home_score': Optional[int],
                    'is_complete': bool,
                    'game_date': str,
                    ...
                },
                ...
            ]
        """
        return self.data_model.get_round_games(round_name)

    def is_active(self) -> bool:
        """
        Check if playoffs are currently active.

        Returns:
            True if current simulation phase is PLAYOFFS, False otherwise
        """
        return self.data_model.is_playoffs_active()
