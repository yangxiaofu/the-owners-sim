"""
Waiver Service for Game Cycle.

Handles waiver wire claims and processing during the offseason waiver wire stage.
Implements priority-based claim system (worst record = highest priority).
"""

from typing import Dict, List, Any, Optional
import logging
import sqlite3
import json
from datetime import datetime, date

from persistence.transaction_logger import TransactionLogger


class WaiverService:
    """
    Service for waiver wire operations.

    Manages:
    - Getting waiver wire priority order (based on standings)
    - Viewing available players on waivers
    - Submitting waiver claims
    - Processing claims by priority
    - Clearing unclaimed players to free agency
    """

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int
    ):
        """
        Initialize the waiver service.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Lazy-loaded cap helper
        self._cap_helper = None

        # Transaction logger for audit trail
        self._transaction_logger = TransactionLogger(db_path)

        # Ensure waiver tables exist (migration for existing databases)
        self._ensure_tables()

    def _ensure_tables(self):
        """Create waiver tables if they don't exist (handles schema migration)."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS waiver_wire (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dynasty_id TEXT NOT NULL,
                    player_id INTEGER NOT NULL,
                    former_team_id INTEGER NOT NULL,
                    waiver_status TEXT DEFAULT 'on_waivers',
                    waiver_order INTEGER,
                    claiming_team_id INTEGER,
                    dead_money INTEGER DEFAULT 0,
                    cap_savings INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cleared_at TIMESTAMP,
                    season INTEGER NOT NULL,
                    UNIQUE(dynasty_id, player_id, season)
                );

                CREATE TABLE IF NOT EXISTS waiver_claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dynasty_id TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    waiver_id INTEGER NOT NULL,
                    player_id INTEGER NOT NULL,
                    claiming_team_id INTEGER NOT NULL,
                    claim_priority INTEGER NOT NULL,
                    claim_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    UNIQUE(dynasty_id, season, player_id, claiming_team_id)
                );

                CREATE INDEX IF NOT EXISTS idx_waiver_wire_dynasty ON waiver_wire(dynasty_id);
                CREATE INDEX IF NOT EXISTS idx_waiver_wire_status ON waiver_wire(dynasty_id, waiver_status);
                CREATE INDEX IF NOT EXISTS idx_waiver_wire_season ON waiver_wire(dynasty_id, season);
                CREATE INDEX IF NOT EXISTS idx_waiver_claims_dynasty ON waiver_claims(dynasty_id);
                CREATE INDEX IF NOT EXISTS idx_waiver_claims_player ON waiver_claims(dynasty_id, player_id);
                CREATE INDEX IF NOT EXISTS idx_waiver_claims_pending ON waiver_claims(dynasty_id, season, claim_status);
            ''')
            conn.commit()
        finally:
            conn.close()

    def _get_cap_helper(self):
        """Get or create cap helper instance.

        Uses season + 1 because during offseason waiver wire,
        cap calculations are for the NEXT league year.
        """
        if self._cap_helper is None:
            from .cap_helper import CapHelper
            # Offseason cap calculations are for NEXT season
            self._cap_helper = CapHelper(self._db_path, self._dynasty_id, self._season + 1)
        return self._cap_helper

    def get_cap_summary(self, team_id: int) -> dict:
        """
        Get salary cap summary for a team.

        Args:
            team_id: Team ID

        Returns:
            Dict with salary_cap_limit, total_spending, available_space,
            dead_money, is_compliant
        """
        return self._get_cap_helper().get_cap_summary(team_id)

    def get_waiver_priority(self) -> List[Dict[str, Any]]:
        """
        Get teams in waiver priority order (worst record first).

        Priority is based on regular season record:
        - Worst record = Priority 1 (first claim)
        - Best record = Priority 32 (last claim)

        Returns:
            List of team dicts with priority: [{team_id, team_name, wins, losses, priority}, ...]
        """
        from team_management.teams.team_loader import TeamDataLoader

        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            # Get standings sorted by worst record first
            cursor.execute(
                """
                SELECT team_id, wins, losses, ties, points_for, points_against
                FROM standings
                ORDER BY wins ASC, (points_for - points_against) ASC
                """
            )

            team_loader = TeamDataLoader()
            priority_list = []

            for priority, row in enumerate(cursor.fetchall(), start=1):
                team_id, wins, losses, ties, pf, pa = row
                team = team_loader.get_team_by_id(team_id)

                priority_list.append({
                    "team_id": team_id,
                    "team_name": team.full_name if team else f"Team {team_id}",
                    "team_abbr": team.abbreviation if team else f"T{team_id}",
                    "wins": wins,
                    "losses": losses,
                    "ties": ties,
                    "priority": priority,
                })

            return priority_list

        finally:
            conn.close()

    def get_team_priority(self, team_id: int) -> int:
        """
        Get waiver priority for a specific team.

        Args:
            team_id: Team ID

        Returns:
            Priority number (1 = highest priority, 32 = lowest)
        """
        priority_list = self.get_waiver_priority()
        for team in priority_list:
            if team["team_id"] == team_id:
                return team["priority"]
        return 32  # Default to lowest priority

    def get_available_players(self) -> List[Dict[str, Any]]:
        """
        Get all players currently on the waiver wire.

        Returns:
            List of player dicts with waiver info and player details
        """
        from database.player_roster_api import PlayerRosterAPI
        from team_management.teams.team_loader import TeamDataLoader

        roster_api = PlayerRosterAPI(self._db_path)
        team_loader = TeamDataLoader()
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT w.id, w.player_id, w.former_team_id, w.waiver_order,
                       w.dead_money, w.cap_savings, w.created_at
                FROM waiver_wire w
                WHERE w.dynasty_id = ? AND w.season = ? AND w.waiver_status = 'on_waivers'
                ORDER BY w.waiver_order ASC
                """,
                (self._dynasty_id, self._season)
            )

            waiver_players = []
            for row in cursor.fetchall():
                waiver_id, player_id, former_team_id, order, dead_money, cap_savings, created = row

                # Get player details
                player_info = roster_api.get_player_by_id(self._dynasty_id, player_id)

                if player_info:
                    positions = player_info.get("positions", [])
                    if isinstance(positions, str):
                        positions = json.loads(positions)
                    position = positions[0] if positions else ""

                    attributes = player_info.get("attributes", {})
                    if isinstance(attributes, str):
                        attributes = json.loads(attributes)
                    overall = attributes.get("overall", 0)

                    # Get former team info
                    former_team = team_loader.get_team_by_id(former_team_id)

                    # Calculate age
                    age = 0
                    birthdate = player_info.get("birthdate")
                    if birthdate:
                        try:
                            birth_year = int(birthdate.split("-")[0])
                            age = self._season - birth_year
                        except (ValueError, IndexError):
                            pass

                    waiver_players.append({
                        "waiver_id": waiver_id,
                        "player_id": player_id,
                        "name": f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip(),
                        "position": position,
                        "overall": overall,
                        "age": age,
                        "former_team_id": former_team_id,
                        "former_team_name": former_team.full_name if former_team else f"Team {former_team_id}",
                        "former_team_abbr": former_team.abbreviation if former_team else f"T{former_team_id}",
                        "waiver_order": order,
                        "dead_money": dead_money,
                        "cap_savings": cap_savings,
                        "created_at": created,
                    })

            return waiver_players

        finally:
            conn.close()

    def get_team_claims(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get pending waiver claims for a team.

        Args:
            team_id: Team ID

        Returns:
            List of pending claim dicts
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT c.id, c.player_id, c.claim_priority, c.created_at,
                       w.former_team_id
                FROM waiver_claims c
                JOIN waiver_wire w ON c.waiver_id = w.id
                WHERE c.dynasty_id = ? AND c.season = ?
                  AND c.claiming_team_id = ? AND c.claim_status = 'pending'
                """,
                (self._dynasty_id, self._season, team_id)
            )

            claims = []
            for row in cursor.fetchall():
                claim_id, player_id, priority, created, former_team_id = row
                claims.append({
                    "claim_id": claim_id,
                    "player_id": player_id,
                    "claim_priority": priority,
                    "former_team_id": former_team_id,
                    "created_at": created,
                })

            return claims

        finally:
            conn.close()

    def submit_claim(
        self,
        team_id: int,
        player_id: int
    ) -> Dict[str, Any]:
        """
        Submit a waiver claim for a player.

        Args:
            team_id: Team making the claim
            player_id: Player to claim

        Returns:
            Dict with success status and claim details
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            # Get waiver entry
            cursor.execute(
                """
                SELECT id FROM waiver_wire
                WHERE dynasty_id = ? AND player_id = ? AND season = ?
                  AND waiver_status = 'on_waivers'
                """,
                (self._dynasty_id, player_id, self._season)
            )
            waiver_row = cursor.fetchone()

            if not waiver_row:
                return {
                    "success": False,
                    "error_message": f"Player {player_id} not on waiver wire",
                }

            waiver_id = waiver_row[0]

            # Get team's priority
            priority = self.get_team_priority(team_id)

            # Check if claim already exists
            cursor.execute(
                """
                SELECT id FROM waiver_claims
                WHERE dynasty_id = ? AND season = ? AND player_id = ?
                  AND claiming_team_id = ?
                """,
                (self._dynasty_id, self._season, player_id, team_id)
            )

            if cursor.fetchone():
                return {
                    "success": False,
                    "error_message": "Claim already submitted for this player",
                }

            # Insert claim
            cursor.execute(
                """
                INSERT INTO waiver_claims (
                    dynasty_id, season, waiver_id, player_id,
                    claiming_team_id, claim_priority, claim_status
                )
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
                """,
                (self._dynasty_id, self._season, waiver_id, player_id, team_id, priority)
            )
            conn.commit()

            self._logger.info(f"Team {team_id} submitted waiver claim for player {player_id} (priority {priority})")

            return {
                "success": True,
                "claim_id": cursor.lastrowid,
                "player_id": player_id,
                "team_id": team_id,
                "priority": priority,
            }

        except sqlite3.IntegrityError as e:
            return {
                "success": False,
                "error_message": str(e),
            }
        finally:
            conn.close()

    def cancel_claim(self, team_id: int, player_id: int) -> Dict[str, Any]:
        """
        Cancel a pending waiver claim.

        Args:
            team_id: Team that submitted the claim
            player_id: Player the claim was for

        Returns:
            Dict with success status
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                DELETE FROM waiver_claims
                WHERE dynasty_id = ? AND season = ? AND player_id = ?
                  AND claiming_team_id = ? AND claim_status = 'pending'
                """,
                (self._dynasty_id, self._season, player_id, team_id)
            )
            conn.commit()

            if cursor.rowcount > 0:
                self._logger.info(f"Team {team_id} cancelled waiver claim for player {player_id}")
                return {"success": True, "player_id": player_id}
            else:
                return {"success": False, "error_message": "Claim not found"}

        finally:
            conn.close()

    def process_ai_claims(self, user_team_id: int) -> Dict[str, Any]:
        """
        AI teams submit waiver claims based on player value and team needs.

        Args:
            user_team_id: User's team ID (to skip)

        Returns:
            Dict with claims submitted
        """
        from team_management.teams.team_loader import TeamDataLoader

        team_loader = TeamDataLoader()
        all_teams = team_loader.get_all_teams()

        # Get available waiver players
        available_players = self.get_available_players()

        # Sort by overall (best players first)
        available_players.sort(key=lambda p: p.get("overall", 0), reverse=True)

        claims_submitted = []

        for team in all_teams:
            team_id = team.team_id

            # Skip user team
            if team_id == user_team_id:
                continue

            # Simple AI: claim top 2 available players if overall >= 70
            claims_made = 0
            for player in available_players:
                if claims_made >= 2:
                    break

                # Don't claim players from own former team (they already cut them)
                if player["former_team_id"] == team_id:
                    continue

                # Only claim decent players
                if player.get("overall", 0) < 70:
                    continue

                result = self.submit_claim(team_id, player["player_id"])
                if result["success"]:
                    claims_submitted.append({
                        "team_id": team_id,
                        "team_name": team.full_name,
                        "player_id": player["player_id"],
                        "player_name": player["name"],
                        "priority": result["priority"],
                    })
                    claims_made += 1

        self._logger.info(f"AI teams submitted {len(claims_submitted)} waiver claims")

        return {
            "claims": claims_submitted,
            "total_claims": len(claims_submitted),
        }

    def process_all_claims(self) -> Dict[str, Any]:
        """
        Process all waiver claims by priority order.

        For each player with claims:
        1. Find highest priority claim (lowest number = highest priority)
        2. Award player to that team
        3. Mark other claims as lost

        Returns:
            Dict with awarded claims and events
        """
        from database.player_roster_api import PlayerRosterAPI
        from team_management.teams.team_loader import TeamDataLoader

        roster_api = PlayerRosterAPI(self._db_path)
        team_loader = TeamDataLoader()
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            # Get all pending claims grouped by player
            cursor.execute(
                """
                SELECT c.id, c.player_id, c.claiming_team_id, c.claim_priority, w.id as waiver_id
                FROM waiver_claims c
                JOIN waiver_wire w ON c.waiver_id = w.id
                WHERE c.dynasty_id = ? AND c.season = ? AND c.claim_status = 'pending'
                ORDER BY c.player_id, c.claim_priority ASC
                """,
                (self._dynasty_id, self._season)
            )

            claims_by_player = {}
            for row in cursor.fetchall():
                claim_id, player_id, team_id, priority, waiver_id = row
                if player_id not in claims_by_player:
                    claims_by_player[player_id] = []
                claims_by_player[player_id].append({
                    "claim_id": claim_id,
                    "team_id": team_id,
                    "priority": priority,
                    "waiver_id": waiver_id,
                })

            awarded_claims = []
            events = []

            for player_id, claims in claims_by_player.items():
                # Sort by priority (lowest number = highest priority)
                claims.sort(key=lambda c: c["priority"])

                # Award to highest priority
                winner = claims[0]
                winning_team_id = winner["team_id"]
                waiver_id = winner["waiver_id"]

                # Get player info
                player_info = roster_api.get_player_by_id(self._dynasty_id, player_id)
                player_name = f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip() if player_info else f"Player {player_id}"

                # Get team info
                team = team_loader.get_team_by_id(winning_team_id)
                team_name = team.full_name if team else f"Team {winning_team_id}"
                team_abbr = team.abbreviation if team else f"T{winning_team_id}"

                # Move player to winning team (use same cursor to avoid lock)
                cursor.execute(
                    """
                    UPDATE players
                    SET team_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE dynasty_id = ? AND player_id = ?
                    """,
                    (winning_team_id, self._dynasty_id, player_id)
                )

                # Update team_rosters table
                cursor.execute(
                    """
                    UPDATE team_rosters
                    SET team_id = ?
                    WHERE dynasty_id = ? AND player_id = ?
                    """,
                    (winning_team_id, self._dynasty_id, player_id)
                )

                # Update waiver wire entry
                cursor.execute(
                    """
                    UPDATE waiver_wire
                    SET waiver_status = 'claimed', claiming_team_id = ?
                    WHERE id = ?
                    """,
                    (winning_team_id, waiver_id)
                )

                # Update winning claim
                cursor.execute(
                    """
                    UPDATE waiver_claims
                    SET claim_status = 'awarded', processed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (winner["claim_id"],)
                )

                # Mark losing claims
                for claim in claims[1:]:
                    cursor.execute(
                        """
                        UPDATE waiver_claims
                        SET claim_status = 'lost', processed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (claim["claim_id"],)
                    )

                awarded_claims.append({
                    "player_id": player_id,
                    "player_name": player_name,
                    "team_id": winning_team_id,
                    "team_name": team_name,
                    "priority": winner["priority"],
                })

                events.append(f"{team_abbr} claimed {player_name} off waivers (priority #{winner['priority']})")

                # Log transaction for audit trail
                self._transaction_logger.log_transaction(
                    dynasty_id=self._dynasty_id,
                    season=self._season + 1,  # Waiver is during next season's preseason
                    transaction_type="WAIVER_CLAIM",
                    player_id=player_id,
                    player_name=player_name,
                    from_team_id=None,  # From waivers
                    to_team_id=winning_team_id,
                    transaction_date=date(self._season + 1, 8, 28),  # Day after cuts (next year)
                    details={
                        "waiver_priority": winner["priority"],
                    }
                )

            conn.commit()

            self._logger.info(f"Processed waiver claims: {len(awarded_claims)} players claimed")

            return {
                "claims_awarded": awarded_claims,
                "events": events,
                "total_awarded": len(awarded_claims),
            }

        finally:
            conn.close()

    def clear_unclaimed_to_free_agency(self) -> Dict[str, Any]:
        """
        Move all unclaimed players from waiver wire to free agency.

        Returns:
            Dict with cleared players and events
        """
        from database.player_roster_api import PlayerRosterAPI

        roster_api = PlayerRosterAPI(self._db_path)
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            # Get unclaimed players
            cursor.execute(
                """
                SELECT w.id, w.player_id
                FROM waiver_wire w
                WHERE w.dynasty_id = ? AND w.season = ? AND w.waiver_status = 'on_waivers'
                """,
                (self._dynasty_id, self._season)
            )

            cleared_players = []
            for row in cursor.fetchall():
                waiver_id, player_id = row

                # Get player info
                player_info = roster_api.get_player_by_id(self._dynasty_id, player_id)
                player_name = f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip() if player_info else f"Player {player_id}"

                # Update waiver wire status
                cursor.execute(
                    """
                    UPDATE waiver_wire
                    SET waiver_status = 'cleared', cleared_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (waiver_id,)
                )

                # Player already has team_id = 0 (set when cut), so they're now free agents
                cleared_players.append({
                    "player_id": player_id,
                    "player_name": player_name,
                })

            conn.commit()

            self._logger.info(f"Cleared {len(cleared_players)} unclaimed players to free agency")

            return {
                "cleared_players": cleared_players,
                "total_cleared": len(cleared_players),
                "event": f"{len(cleared_players)} players cleared waivers to free agency",
            }

        finally:
            conn.close()