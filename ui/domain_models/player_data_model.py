"""
Player Data Model for The Owner's Sim UI

Business logic layer for player data access.
Owns database API instances and provides clean interface for UI controllers.
"""

from typing import List, Dict, Any, Optional
import sys
import os

# Add src to path for database imports
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from database.player_roster_api import PlayerRosterAPI
from database.dynasty_state_api import DynastyStateAPI
from shared.player_utils import get_player_age


class PlayerDataModel:
    """
    Domain model for player data operations.

    Owns PlayerRosterAPI instance and provides business logic for:
    - Free agent queries
    - Team roster queries
    - Individual player lookups

    Controllers delegate to this layer for all player data access.
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize player data model.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year (for getting current date)
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season
        self.roster_api = PlayerRosterAPI(database_path=db_path)
        self.dynasty_state_api = DynastyStateAPI(db_path=db_path)

    def get_free_agents(self) -> List[Dict[str, Any]]:
        """
        Get all free agent players (team_id = 0).

        Returns:
            List of player dictionaries with formatted data for UI display
        """
        try:
            free_agents = self.roster_api.get_free_agents(self.dynasty_id)

            # Format for UI display
            formatted_agents = []
            for player in free_agents:
                formatted_agents.append(self._format_player_for_display(player))

            return formatted_agents
        except Exception as e:
            print(f"Error fetching free agents: {e}")
            return []

    def get_team_roster(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get roster for specific team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of player dictionaries for team roster
        """
        try:
            roster = self.roster_api.get_team_roster(self.dynasty_id, team_id)

            # Format for UI display
            formatted_roster = []
            for player in roster:
                formatted_roster.append(self._format_player_for_display(player))

            return formatted_roster
        except Exception as e:
            print(f"Error fetching team roster: {e}")
            return []

    def get_player_by_id(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Get individual player by ID.

        Args:
            player_id: Player ID (auto-generated integer)

        Returns:
            Player dictionary or None if not found
        """
        try:
            player = self.roster_api.get_player_by_id(self.dynasty_id, player_id)

            if player:
                return self._format_player_for_display(player)
            return None
        except Exception as e:
            print(f"Error fetching player: {e}")
            return None

    def get_dynasty_info(self) -> Dict[str, Any]:
        """
        Get dynasty information.

        Returns:
            Dict with dynasty_id
        """
        return {
            "dynasty_id": self.dynasty_id
        }

    def _format_player_for_display(self, player: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format player data for UI display.

        Args:
            player: Raw player dictionary or sqlite3.Row from database

        Returns:
            Formatted player dictionary with UI-friendly fields
        """
        import json

        # Convert sqlite3.Row to dict if needed
        if hasattr(player, 'keys'):
            player = dict(zip(player.keys(), player))

        # Parse JSON fields if they're strings
        positions = player.get('positions', '[]')
        if isinstance(positions, str):
            positions = json.loads(positions)

        attributes = player.get('attributes', '{}')
        if isinstance(attributes, str):
            attributes = json.loads(attributes)

        # Get primary position (first in list)
        primary_position = positions[0] if positions else "N/A"

        # Get overall rating from attributes
        overall = attributes.get('overall', 0)

        # Calculate age - use birthdate if available, otherwise estimate from years_pro
        years_pro = player.get('years_pro', 0)
        birthdate = player.get('birthdate')

        # Get current simulation date
        current_date = self.dynasty_state_api.get_current_date(self.dynasty_id, self.season)

        # Calculate age using utility function (handles birthdate + fallback)
        age = get_player_age(
            birthdate=birthdate,
            current_date=current_date,
            years_pro=years_pro,
            rookie_age=22
        )

        # Format player name
        first_name = player.get('first_name', '')
        last_name = player.get('last_name', '')
        full_name = f"{first_name} {last_name}"

        # Get team status
        team_id = player.get('team_id', 0)
        status = "FREE AGENT" if team_id == 0 else "ACTIVE"

        return {
            'player_id': player.get('player_id'),
            'number': player.get('number', 0),
            'name': full_name,
            'first_name': first_name,
            'last_name': last_name,
            'position': primary_position,
            'positions': positions,
            'age': age,
            'years_pro': years_pro,
            'overall': overall,
            'attributes': attributes,
            'team_id': team_id,
            'status': status,
            # Placeholder contract fields (will be populated later with contract data)
            'contract': 'N/A',
            'salary': 'N/A'
        }
