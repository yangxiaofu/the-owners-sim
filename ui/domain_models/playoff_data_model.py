"""
Playoff Data Model - Domain model layer for playoff data access.

This module provides playoff-specific data access logic following the MVC pattern.
It owns all playoff data retrieval through the SimulationController and returns
clean data structures for UI consumption.

Architecture:
    View → Controller → Domain Model → SimulationController → SeasonCycleController

Design Principles:
    - NO Qt dependencies (pure Python)
    - Returns dicts/lists for UI consumption
    - Single source of truth through SimulationController
    - Clean separation of concerns
"""

from typing import Dict, List, Optional, Any
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from team_management.teams.team_loader import get_team_by_id


class PlayoffDataModel:
    """
    Domain model for playoff data access and business logic.

    This class provides a clean interface for retrieving playoff information
    including seeding, bracket data, round games, and playoff state. It
    abstracts away the complexity of accessing the SeasonCycleController
    and formats data for UI consumption.

    Attributes:
        simulation_controller: UI simulation controller for data access
    """

    def __init__(self, simulation_controller):
        """
        Initialize the playoff data model.

        Args:
            simulation_controller: UI's SimulationController instance
        """
        self.simulation_controller = simulation_controller

    def is_playoffs_active(self) -> bool:
        """
        Check if current season phase is playoffs.

        Returns:
            True if current phase is playoffs, False otherwise
        """
        phase = self.simulation_controller.get_current_phase()
        return phase == "playoffs"

    def get_playoff_seeding(self) -> Optional[Dict[str, Any]]:
        """
        Get complete playoff seeding for AFC and NFC.

        Returns playoff seeding with seeds 1-7 for each conference, including
        team names, records, and distinction between division winners and wildcards.

        Returns:
            Dictionary with seeding data or None if playoffs not active/available
        """
        # Check if playoffs are active
        if not self.is_playoffs_active():
            return None

        season_controller = self.simulation_controller.season_controller
        if not season_controller:
            return None

        # Get playoff bracket which contains seeding information
        bracket = season_controller.get_playoff_bracket()
        if not bracket or not bracket.get('original_seeding'):
            return None

        seeding = bracket['original_seeding']

        # Convert PlayoffSeeding object to dict for UI consumption
        return {
            'season': seeding.season,
            'week': seeding.week,
            'afc': self._format_conference_seeding(seeding.afc),
            'nfc': self._format_conference_seeding(seeding.nfc)
        }

    def _format_conference_seeding(self, conference_seeding) -> Dict[str, Any]:
        """
        Format conference seeding data for UI.

        Args:
            conference_seeding: ConferenceSeeding object

        Returns:
            Formatted dictionary with seeds, division winners, and wildcards
        """
        seeds = []
        for seed in conference_seeding.seeds:
            team = get_team_by_id(seed.team_id)
            team_name = f"{team.city} {team.nickname}" if team else f"Team {seed.team_id}"

            seeds.append({
                'seed': seed.seed,
                'team_id': seed.team_id,
                'team_name': team_name,
                'record': seed.record_string,
                'division_winner': seed.seed <= 4
            })

        return {
            'seeds': seeds,
            'division_winners': [1, 2, 3, 4],
            'wildcards': [5, 6, 7]
        }

    def get_bracket_data(self) -> Optional[Dict[str, Any]]:
        """
        Get complete playoff bracket with all rounds and matchups.

        Returns:
            Dictionary with complete bracket data or None if not available
        """
        if not self.is_playoffs_active():
            return None

        season_controller = self.simulation_controller.season_controller
        if not season_controller:
            return None

        bracket = season_controller.get_playoff_bracket()
        if not bracket:
            return None

        return {
            'current_round': bracket.get('current_round'),
            'wild_card': bracket.get('wild_card'),
            'divisional': bracket.get('divisional'),
            'conference': bracket.get('conference'),
            'super_bowl': bracket.get('super_bowl'),
            'original_seeding': bracket.get('original_seeding')
        }

    def get_round_games(self, round_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get all games for a specific playoff round.

        Args:
            round_name: Round identifier ('wild_card', 'divisional', 'conference', 'super_bowl')

        Returns:
            List of game dictionaries for the round or None if not available
        """
        if not self.is_playoffs_active():
            return None

        season_controller = self.simulation_controller.season_controller
        if not season_controller or not season_controller.playoff_controller:
            return None

        return season_controller.playoff_controller.get_round_games(round_name)
