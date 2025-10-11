"""
Depth Chart Database API

Database API layer for depth chart CRUD operations.
All operations respect dynasty isolation and work with team_rosters.depth_chart_order field.
"""

from typing import List, Dict, Any, Optional
import sqlite3
import json
from database.connection import DatabaseConnection
from depth_chart.depth_chart_manager import DepthChartManager
from depth_chart.depth_chart_validator import DepthChartValidator
from depth_chart.depth_chart_types import UNASSIGNED_DEPTH_ORDER, POSITION_REQUIREMENTS
from constants.position_hierarchy import PositionHierarchy


class DepthChartAPI:
    """Database API for depth chart management."""

    def __init__(self, db_path: str):
        """
        Initialize depth chart API.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.db_connection = DatabaseConnection(db_path)
        self.manager = DepthChartManager(db_path)
        self.validator = DepthChartValidator()

    # =======================
    # Core Retrieval Methods
    # =======================

    def get_position_depth_chart(
        self,
        dynasty_id: str,
        team_id: int,
        position: str
    ) -> List[Dict[str, Any]]:
        """
        Get depth chart for a specific position, ordered by depth_chart_order.

        Uses position hierarchy to match players. For example:
        - Searching for "left_guard" will return players with "left_guard" OR "guard"
        - Searching for "quarterback" will return only quarterbacks

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)
            position: Position (e.g., 'quarterback', 'running_back', 'left_guard')

        Returns:
            List of player dicts ordered by depth_chart_order
        """
        query = """
            SELECT
                p.player_id,
                p.first_name || ' ' || p.last_name as player_name,
                p.number as jersey_number,
                p.positions,
                p.attributes,
                tr.depth_chart_order
            FROM players p
            JOIN team_rosters tr
                ON p.dynasty_id = tr.dynasty_id
                AND p.player_id = tr.player_id
            WHERE p.dynasty_id = ?
                AND p.team_id = ?
                AND tr.roster_status = 'active'
            ORDER BY tr.depth_chart_order, p.number
        """

        roster = self.db_connection.execute_query(query, (dynasty_id, team_id))

        # Get all positions that match the requested position (using hierarchy)
        # Example: "left_guard" should match both "left_guard" and "guard" players
        matching_positions = self._get_positions_matching_query(position)

        # Filter by position and extract overall rating
        position_players = []
        for player in roster:
            # Parse positions array (stored in positions column, not attributes)
            positions = json.loads(player['positions'])
            attrs = json.loads(player['attributes'])

            # Check if player's primary position matches any of our target positions
            if positions and positions[0] in matching_positions:
                position_players.append({
                    'player_id': player['player_id'],
                    'player_name': player['player_name'],
                    'depth_order': player['depth_chart_order'],
                    'overall': attrs.get('overall', 0),
                    'position': position  # Use requested position for consistency
                })

        return position_players

    def _get_positions_matching_query(self, position: str) -> List[str]:
        """
        Get all positions that should match a position query using hierarchy.

        For specific positions (like "left_guard"), includes the position itself
        plus any generic parent positions (like "guard").

        Args:
            position: Position to query

        Returns:
            List of positions to match

        Examples:
            >>> _get_positions_matching_query("left_guard")
            ["left_guard", "guard"]
            >>> _get_positions_matching_query("quarterback")
            ["quarterback"]
        """
        matching = [position]  # Always include the position itself

        # Get parent position if exists
        parent = PositionHierarchy.get_parent(position)

        # Keep adding parents until we hit a generic category (offense/defense/special_teams)
        while parent and parent not in ['offense', 'defense', 'special_teams']:
            matching.append(parent)
            parent = PositionHierarchy.get_parent(parent)

        return matching

    def get_full_depth_chart(
        self,
        dynasty_id: str,
        team_id: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get complete depth chart for all positions.

        Uses position hierarchy to aggregate players. For example:
        - Players with position "tackle" will appear in both "left_tackle" and "right_tackle"
        - Players with position "guard" will appear in both "left_guard" and "right_guard"

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)

        Returns:
            Dict mapping position -> list of player dicts
        """
        # Get all roster players
        query = """
            SELECT
                p.player_id,
                p.first_name || ' ' || p.last_name as player_name,
                p.number as jersey_number,
                p.positions,
                p.attributes,
                tr.depth_chart_order
            FROM players p
            JOIN team_rosters tr
                ON p.dynasty_id = tr.dynasty_id
                AND p.player_id = tr.player_id
            WHERE p.dynasty_id = ?
                AND p.team_id = ?
                AND tr.roster_status = 'active'
            ORDER BY tr.depth_chart_order, p.number
        """

        roster = self.db_connection.execute_query(query, (dynasty_id, team_id))

        # Group by position using hierarchy
        depth_chart = {}

        for player in roster:
            # Parse positions
            positions = json.loads(player['positions'])
            attrs = json.loads(player['attributes'])

            if not positions:
                continue

            primary_position = positions[0]

            # Get all positions this player should appear under (using hierarchy)
            # Example: "guard" player should appear under "left_guard" and "right_guard"
            matching_positions = self._get_matching_positions_for_player(primary_position)

            for position in matching_positions:
                if position not in depth_chart:
                    depth_chart[position] = []

                depth_chart[position].append({
                    'player_id': player['player_id'],
                    'player_name': player['player_name'],
                    'depth_order': player['depth_chart_order'],
                    'overall': attrs.get('overall', 0),
                    'position': primary_position  # Store original position
                })

        return depth_chart

    def _get_matching_positions_for_player(self, primary_position: str) -> List[str]:
        """
        Get all positions a player should appear under based on hierarchy.

        For generic positions (like "guard", "tackle"), returns all child positions.
        For specific positions (like "left_guard"), returns just that position.

        Args:
            primary_position: Player's primary position

        Returns:
            List of positions this player should appear under

        Examples:
            >>> _get_matching_positions_for_player("guard")
            ["guard", "left_guard", "right_guard"]
            >>> _get_matching_positions_for_player("left_guard")
            ["left_guard"]
        """
        # Get all child positions (includes the position itself if no children)
        children = PositionHierarchy.get_children(primary_position)

        if children:
            # Generic position with children - include self + all children
            return [primary_position] + children
        else:
            # Specific position with no children - just return self
            return [primary_position]

    def get_starter(
        self,
        dynasty_id: str,
        team_id: int,
        position: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the starter (depth_chart_order = 1) for a specific position.

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)
            position: Position (e.g., 'QB')

        Returns:
            Player dict or None if no starter assigned
        """
        position_depth = self.get_position_depth_chart(dynasty_id, team_id, position)

        starters = [p for p in position_depth if p['depth_order'] == 1]

        return starters[0] if starters else None

    def get_backups(
        self,
        dynasty_id: str,
        team_id: int,
        position: str
    ) -> List[Dict[str, Any]]:
        """
        Get all backups (depth_chart_order > 1) for a position, ordered by depth.

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)
            position: Position (e.g., 'QB')

        Returns:
            List of backup player dicts
        """
        position_depth = self.get_position_depth_chart(dynasty_id, team_id, position)

        return [p for p in position_depth if p['depth_order'] > 1 and p['depth_order'] != UNASSIGNED_DEPTH_ORDER]

    # =============================
    # Depth Chart Modification Methods
    # =============================

    def set_starter(
        self,
        dynasty_id: str,
        team_id: int,
        player_id: int,
        position: str
    ) -> bool:
        """
        Set a player as starter for their position (depth_chart_order = 1).

        Behavior:
        - Sets target player's depth_chart_order to 1
        - Shifts previous starter to depth_chart_order = 2
        - Validates player plays this position

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)
            player_id: Player ID to set as starter
            position: Position (e.g., 'QB')

        Returns:
            True if successful, False otherwise
        """
        # Validate player plays this position
        if not self.manager.validate_player_position(dynasty_id, team_id, player_id, position):
            print(f"[ERROR] Player {player_id} does not play {position}")
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Step 1: Get current starter (if exists)
            current_depth = self.get_position_depth_chart(dynasty_id, team_id, position)
            current_starter = [p for p in current_depth if p['depth_order'] == 1]

            # Step 2: Shift current starter to backup (order 2)
            if current_starter and current_starter[0]['player_id'] != player_id:
                cursor.execute('''
                    UPDATE team_rosters
                    SET depth_chart_order = 2
                    WHERE dynasty_id = ? AND team_id = ? AND player_id = ?
                ''', (dynasty_id, team_id, current_starter[0]['player_id']))

            # Step 3: Set new player as starter (order 1)
            cursor.execute('''
                UPDATE team_rosters
                SET depth_chart_order = 1
                WHERE dynasty_id = ? AND team_id = ? AND player_id = ?
            ''', (dynasty_id, team_id, player_id))

            conn.commit()
            print(f"✅ Set player {player_id} as starter for {position}")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Failed to set starter: {e}")
            return False
        finally:
            conn.close()

    def set_backup(
        self,
        dynasty_id: str,
        team_id: int,
        player_id: int,
        position: str,
        backup_order: int = 2
    ) -> bool:
        """
        Set a player as backup at specific depth (default = 2).

        Behavior:
        - Sets player's depth_chart_order to specified backup_order
        - Shifts players at/below that order down by 1
        - Does NOT affect the starter (order 1)

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)
            player_id: Player ID
            position: Position (e.g., 'QB')
            backup_order: Depth chart order (default 2 = first backup)

        Returns:
            True if successful, False otherwise
        """
        # Validate player plays this position
        if not self.manager.validate_player_position(dynasty_id, team_id, player_id, position):
            print(f"[ERROR] Player {player_id} does not play {position}")
            return False

        if backup_order < 2:
            print(f"[ERROR] backup_order must be >= 2 (use set_starter for depth 1)")
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get current position depth chart
            current_depth = self.get_position_depth_chart(dynasty_id, team_id, position)

            # Shift players at/below backup_order down by 1
            for p in current_depth:
                if p['depth_order'] >= backup_order and p['player_id'] != player_id:
                    cursor.execute('''
                        UPDATE team_rosters
                        SET depth_chart_order = depth_chart_order + 1
                        WHERE dynasty_id = ? AND team_id = ? AND player_id = ?
                    ''', (dynasty_id, team_id, p['player_id']))

            # Set player at specified backup order
            cursor.execute('''
                UPDATE team_rosters
                SET depth_chart_order = ?
                WHERE dynasty_id = ? AND team_id = ? AND player_id = ?
            ''', (backup_order, dynasty_id, team_id, player_id))

            conn.commit()
            print(f"✅ Set player {player_id} as backup #{backup_order} for {position}")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Failed to set backup: {e}")
            return False
        finally:
            conn.close()

    def swap_depth_positions(
        self,
        dynasty_id: str,
        team_id: int,
        player1_id: int,
        player2_id: int
    ) -> bool:
        """
        Swap depth chart positions between two players on same position.

        Validates both players play same position before swapping.

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)
            player1_id: First player ID
            player2_id: Second player ID

        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get both players' current depth chart orders
            query = """
                SELECT player_id, depth_chart_order
                FROM team_rosters
                WHERE dynasty_id = ? AND team_id = ? AND player_id IN (?, ?)
            """

            cursor.execute(query, (dynasty_id, team_id, player1_id, player2_id))
            results = cursor.fetchall()

            if len(results) != 2:
                print(f"[ERROR] Could not find both players on roster")
                return False

            player1_order = next(r[1] for r in results if r[0] == player1_id)
            player2_order = next(r[1] for r in results if r[0] == player2_id)

            # Swap depth orders atomically using temp value
            TEMP_ORDER = -1

            cursor.execute('''
                UPDATE team_rosters
                SET depth_chart_order = ?
                WHERE dynasty_id = ? AND team_id = ? AND player_id = ?
            ''', (TEMP_ORDER, dynasty_id, team_id, player1_id))

            cursor.execute('''
                UPDATE team_rosters
                SET depth_chart_order = ?
                WHERE dynasty_id = ? AND team_id = ? AND player_id = ?
            ''', (player1_order, dynasty_id, team_id, player2_id))

            cursor.execute('''
                UPDATE team_rosters
                SET depth_chart_order = ?
                WHERE dynasty_id = ? AND team_id = ? AND player_id = ?
            ''', (player2_order, dynasty_id, team_id, player1_id))

            conn.commit()
            print(f"✅ Swapped depth positions: {player1_id} ↔ {player2_id}")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Failed to swap positions: {e}")
            return False
        finally:
            conn.close()

    def reorder_position_depth(
        self,
        dynasty_id: str,
        team_id: int,
        position: str,
        ordered_player_ids: List[int]
    ) -> bool:
        """
        Complete reordering of depth chart for a position.

        Sets depth_chart_order sequentially (1, 2, 3, ...) based on ordered_player_ids list.
        First player in list becomes starter (order 1).

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)
            position: Position (e.g., 'QB')
            ordered_player_ids: List of player IDs in desired depth order

        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Validate all players play this position
            for player_id in ordered_player_ids:
                if not self.manager.validate_player_position(dynasty_id, team_id, player_id, position):
                    print(f"[ERROR] Player {player_id} does not play {position}")
                    return False

            # Set depth orders sequentially
            for i, player_id in enumerate(ordered_player_ids):
                depth_order = i + 1  # 1-indexed

                cursor.execute('''
                    UPDATE team_rosters
                    SET depth_chart_order = ?
                    WHERE dynasty_id = ? AND team_id = ? AND player_id = ?
                ''', (depth_order, dynasty_id, team_id, player_id))

            conn.commit()
            print(f"✅ Reordered {position} depth chart: {len(ordered_player_ids)} players")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Failed to reorder depth chart: {e}")
            return False
        finally:
            conn.close()

    def remove_from_depth_chart(
        self,
        dynasty_id: str,
        team_id: int,
        player_id: int
    ) -> bool:
        """
        Remove player from depth chart (set depth_chart_order to 99).

        Compacts remaining players' depth orders.

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)
            player_id: Player ID

        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Set player's depth_chart_order to UNASSIGNED_DEPTH_ORDER
            cursor.execute('''
                UPDATE team_rosters
                SET depth_chart_order = ?
                WHERE dynasty_id = ? AND team_id = ? AND player_id = ?
            ''', (UNASSIGNED_DEPTH_ORDER, dynasty_id, team_id, player_id))

            conn.commit()
            print(f"✅ Removed player {player_id} from depth chart")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Failed to remove from depth chart: {e}")
            return False
        finally:
            conn.close()

    # ====================
    # Batch Operations
    # ====================

    def auto_generate_depth_chart(
        self,
        dynasty_id: str,
        team_id: int,
        connection: Optional[sqlite3.Connection] = None
    ) -> bool:
        """
        Automatically generate depth chart based on player overalls.

        For each position, orders players by overall rating (highest first)
        and assigns depth_chart_order sequentially.

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)
            connection: Optional existing database connection (for transactions)

        Returns:
            True if successful, False otherwise
        """
        # Use provided connection or create new one
        conn = connection if connection else sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        owns_connection = connection is None  # Track if we should commit/close

        try:
            # Query roster directly using the provided connection
            query = """
                SELECT
                    p.player_id,
                    p.first_name || ' ' || p.last_name as player_name,
                    p.positions,
                    p.attributes
                FROM players p
                JOIN team_rosters tr
                    ON p.dynasty_id = tr.dynasty_id
                    AND p.player_id = tr.player_id
                WHERE p.dynasty_id = ?
                    AND p.team_id = ?
                    AND tr.roster_status = 'active'
            """

            cursor.execute(query, (dynasty_id, team_id))
            roster = cursor.fetchall()

            # Group by position using hierarchy (inline logic to avoid another method call)
            depth_chart = {}

            for player in roster:
                player_id, player_name, positions_json, attrs_json = player

                # Parse JSON
                positions = json.loads(positions_json)
                attrs = json.loads(attrs_json)

                if not positions:
                    continue

                primary_position = positions[0]
                overall = attrs.get('overall', 0)

                # Get all positions this player should appear under
                children = PositionHierarchy.get_children(primary_position)
                matching_positions = [primary_position] + children if children else [primary_position]

                for position in matching_positions:
                    if position not in depth_chart:
                        depth_chart[position] = []

                    depth_chart[position].append({
                        'player_id': player_id,
                        'overall': overall
                    })

            # Now assign depth chart orders
            for position, players in depth_chart.items():
                # Sort by overall (highest first)
                sorted_players = sorted(players, key=lambda p: p['overall'], reverse=True)

                # Assign sequential depth orders
                for i, player in enumerate(sorted_players):
                    depth_order = i + 1

                    cursor.execute('''
                        UPDATE team_rosters
                        SET depth_chart_order = ?
                        WHERE dynasty_id = ? AND team_id = ? AND player_id = ?
                    ''', (depth_order, dynasty_id, team_id, player['player_id']))

            # Only commit if we created the connection
            if owns_connection:
                conn.commit()
            print(f"✅ Auto-generated depth chart for team {team_id}")
            return True

        except Exception as e:
            # Only rollback if we created the connection
            if owns_connection:
                conn.rollback()
            print(f"[ERROR] Failed to auto-generate depth chart for team {team_id}: {e}")
            print(f"[DEBUG] Connection provided: {connection is not None}, Owns connection: {owns_connection}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Only close if we created the connection
            if owns_connection:
                conn.close()

    def reset_position_depth_chart(
        self,
        dynasty_id: str,
        team_id: int,
        position: str
    ) -> bool:
        """
        Reset a single position's depth chart to auto-generated (by overall).

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)
            position: Position (e.g., 'QB')

        Returns:
            True if successful, False otherwise
        """
        position_players = self.get_position_depth_chart(dynasty_id, team_id, position)

        if not position_players:
            print(f"[WARNING] No players found for position {position}")
            return True  # Nothing to reset

        # Sort by overall
        sorted_players = sorted(position_players, key=lambda p: p['overall'], reverse=True)

        # Reorder using reorder_position_depth
        ordered_ids = [p['player_id'] for p in sorted_players]
        return self.reorder_position_depth(dynasty_id, team_id, position, ordered_ids)

    def clear_depth_chart(
        self,
        dynasty_id: str,
        team_id: int
    ) -> bool:
        """
        Set all players on team to depth_chart_order = 99 (unassigned).

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID (1-32)

        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE team_rosters
                SET depth_chart_order = ?
                WHERE dynasty_id = ? AND team_id = ?
            ''', (UNASSIGNED_DEPTH_ORDER, dynasty_id, team_id))

            rows_affected = cursor.rowcount
            conn.commit()
            print(f"✅ Cleared depth chart for team {team_id} ({rows_affected} players)")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Failed to clear depth chart: {e}")
            return False
        finally:
            conn.close()

    # ====================
    # Validation Methods
    # ====================

    def validate_depth_chart(
        self,
        dynasty_id: str,
        team_id: int
    ) -> Dict[str, List[str]]:
        """
        Validate entire depth chart and return issues.

        Returns:
            Dict with 'errors' and 'warnings' lists
        """
        full_depth_chart = self.get_full_depth_chart(dynasty_id, team_id)
        return self.validator.validate_depth_chart(dynasty_id, team_id, full_depth_chart)

    def has_starter(
        self,
        dynasty_id: str,
        team_id: int,
        position: str
    ) -> bool:
        """
        Check if position has a starter assigned.

        Returns:
            True if position has exactly one starter (depth_chart_order=1)
        """
        starter = self.get_starter(dynasty_id, team_id, position)
        return starter is not None

    def get_depth_chart_gaps(
        self,
        dynasty_id: str,
        team_id: int
    ) -> Dict[str, int]:
        """
        Identify positions without starters.

        Returns:
            Dict mapping position -> gap count (0 = has starter, 1 = missing starter)
        """
        full_depth_chart = self.get_full_depth_chart(dynasty_id, team_id)
        return self.validator.get_depth_chart_gaps(full_depth_chart)

    # =========================
    # Position Constraint Methods
    # =========================

    def get_position_requirements(self) -> Dict[str, Dict[str, int]]:
        """
        Get minimum/recommended depth chart sizes per position.

        Returns:
            Dict mapping position -> {'minimum': int, 'recommended': int}
        """
        return self.manager.get_position_requirements()

    def check_depth_chart_compliance(
        self,
        dynasty_id: str,
        team_id: int
    ) -> Dict[str, bool]:
        """
        Check if depth chart meets minimum requirements.

        Returns:
            Dict mapping position -> compliance status (True/False)
        """
        full_depth_chart = self.get_full_depth_chart(dynasty_id, team_id)
        return self.validator.check_depth_chart_compliance(full_depth_chart)
