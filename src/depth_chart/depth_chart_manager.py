"""
Depth Chart Manager

Business logic layer for depth chart operations.
Handles validation, position checking, and data transformation.
"""

from typing import List, Dict, Any, Optional
import sqlite3
from database.connection import DatabaseConnection
from depth_chart.depth_chart_types import POSITION_REQUIREMENTS, UNASSIGNED_DEPTH_ORDER
from depth_chart.depth_chart_validator import DepthChartValidator


class DepthChartManager:
    """Business logic for depth chart management."""

    def __init__(self, db_path: str):
        """
        Initialize depth chart manager.

        Args:
            db_path: Path to SQLite database
        """
        self.db_connection = DatabaseConnection(db_path)
        self.validator = DepthChartValidator()

    def validate_player_position(
        self,
        dynasty_id: str,
        team_id: int,
        player_id: int,
        position: str
    ) -> bool:
        """
        Validate that player plays the specified position.

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID
            player_id: Player ID
            position: Position to validate (e.g., 'QB')

        Returns:
            True if player plays this position, False otherwise
        """
        # Query player's positions from database
        query = """
            SELECT positions
            FROM players
            WHERE dynasty_id = ? AND player_id = ? AND team_id = ?
        """

        result = self.db_connection.execute_query(query, (dynasty_id, player_id, team_id))

        if not result:
            return False

        # Parse JSON positions array
        import json
        positions = json.loads(result[0]['positions'])

        # Check if player can play this position
        return position in positions

    def get_position_requirements(self) -> Dict[str, Dict[str, int]]:
        """
        Get minimum/recommended depth chart sizes per position.

        Returns:
            Dict mapping position -> {'minimum': int, 'recommended': int}
        """
        return POSITION_REQUIREMENTS.copy()

    def compact_depth_chart(
        self,
        players: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Compact depth chart orders to remove gaps (e.g., 1, 2, 4, 7 -> 1, 2, 3, 4).

        Args:
            players: List of player dicts with depth_chart_order

        Returns:
            List of player dicts with compacted depth_chart_order
        """
        # Sort by current depth_chart_order
        sorted_players = sorted(
            players,
            key=lambda p: (
                p.get('depth_chart_order', UNASSIGNED_DEPTH_ORDER),
                -p.get('overall', 0)  # Tiebreaker: higher overall first
            )
        )

        # Reassign sequential orders (1, 2, 3...) excluding UNASSIGNED_DEPTH_ORDER
        new_order = 1
        for player in sorted_players:
            if player.get('depth_chart_order') != UNASSIGNED_DEPTH_ORDER:
                player['depth_chart_order'] = new_order
                new_order += 1

        return sorted_players

    def get_next_available_depth_order(
        self,
        players: List[Dict[str, Any]]
    ) -> int:
        """
        Get next available depth chart order for a position.

        Args:
            players: List of player dicts for a position

        Returns:
            Next available depth order (e.g., if 1, 2, 3 exist, returns 4)
        """
        assigned_orders = [
            p.get('depth_chart_order')
            for p in players
            if p.get('depth_chart_order') != UNASSIGNED_DEPTH_ORDER
        ]

        if not assigned_orders:
            return 1  # First player on depth chart

        return max(assigned_orders) + 1

    def group_players_by_position(
        self,
        roster: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group roster by position for depth chart operations.

        Args:
            roster: List of player dicts

        Returns:
            Dict mapping position -> list of player dicts
        """
        position_groups = {}

        for player in roster:
            # Get primary position (first position in positions array)
            import json
            positions = json.loads(player['positions'])

            if not positions:
                continue

            primary_position = positions[0]

            if primary_position not in position_groups:
                position_groups[primary_position] = []

            position_groups[primary_position].append(player)

        return position_groups

    def auto_generate_position_depth_chart(
        self,
        players: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Auto-generate depth chart for a position based on overall ratings.

        Args:
            players: List of player dicts for a position

        Returns:
            List of player dicts with depth_chart_order assigned by overall rating
        """
        # Sort by overall rating (highest first)
        sorted_players = sorted(
            players,
            key=lambda p: p.get('overall', 0),
            reverse=True
        )

        # Assign sequential depth orders
        for i, player in enumerate(sorted_players):
            player['depth_chart_order'] = i + 1

        return sorted_players
