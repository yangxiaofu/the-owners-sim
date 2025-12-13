"""
Database API for pending offers operations.

Part of Milestone 8: Free Agency Depth.
Tracks offers submitted during multi-wave free agency.
"""
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class PendingOffer:
    """Represents a pending offer to a free agent."""
    offer_id: Optional[int]
    dynasty_id: str
    season: int
    wave: int
    player_id: int
    offering_team_id: int
    aav: int
    total_value: int
    years: int
    guaranteed: int
    signing_bonus: int
    decision_deadline: int
    status: str = "pending"
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None


class PendingOffersAPI:
    """API for pending offers database operations."""

    VALID_STATUSES = {"pending", "accepted", "rejected", "expired", "withdrawn", "surprise"}

    def __init__(self, db_path: str):
        self._db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_offer(
        self,
        dynasty_id: str,
        season: int,
        wave: int,
        player_id: int,
        offering_team_id: int,
        aav: int,
        total_value: int,
        years: int,
        guaranteed: int,
        signing_bonus: int,
        decision_deadline: int
    ) -> int:
        """
        Create a new pending offer.

        Returns:
            offer_id of the created offer

        Raises:
            sqlite3.IntegrityError if duplicate offer exists
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                INSERT INTO pending_offers
                (dynasty_id, season, wave, player_id, offering_team_id,
                 aav, total_value, years, guaranteed, signing_bonus,
                 decision_deadline, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            ''', (
                dynasty_id, season, wave, player_id, offering_team_id,
                aav, total_value, years, guaranteed, signing_bonus,
                decision_deadline
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_offer_by_id(self, offer_id: int) -> Optional[Dict[str, Any]]:
        """Get a single offer by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM pending_offers WHERE offer_id = ?
            ''', (offer_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_offers_by_player(
        self,
        dynasty_id: str,
        player_id: int,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all offers for a specific player.

        Args:
            dynasty_id: Dynasty to filter by
            player_id: Player to get offers for
            status: Optional status filter (e.g., 'pending')

        Returns:
            List of offer dictionaries, ordered by AAV descending
        """
        conn = self._get_connection()
        try:
            if status:
                cursor = conn.execute('''
                    SELECT * FROM pending_offers
                    WHERE dynasty_id = ? AND player_id = ? AND status = ?
                    ORDER BY aav DESC
                ''', (dynasty_id, player_id, status))
            else:
                cursor = conn.execute('''
                    SELECT * FROM pending_offers
                    WHERE dynasty_id = ? AND player_id = ?
                    ORDER BY aav DESC
                ''', (dynasty_id, player_id))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_offers_by_team(
        self,
        dynasty_id: str,
        team_id: int,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all offers submitted by a team.

        Args:
            dynasty_id: Dynasty to filter by
            team_id: Team that submitted offers
            status: Optional status filter

        Returns:
            List of offer dictionaries
        """
        conn = self._get_connection()
        try:
            if status:
                cursor = conn.execute('''
                    SELECT * FROM pending_offers
                    WHERE dynasty_id = ? AND offering_team_id = ? AND status = ?
                    ORDER BY created_at DESC
                ''', (dynasty_id, team_id, status))
            else:
                cursor = conn.execute('''
                    SELECT * FROM pending_offers
                    WHERE dynasty_id = ? AND offering_team_id = ?
                    ORDER BY created_at DESC
                ''', (dynasty_id, team_id))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_wave_offers(
        self,
        dynasty_id: str,
        season: int,
        wave: int,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all offers for a specific wave.

        Args:
            dynasty_id: Dynasty to filter by
            season: Season year
            wave: Wave number (0-4)
            status: Optional status filter

        Returns:
            List of offer dictionaries
        """
        conn = self._get_connection()
        try:
            if status:
                cursor = conn.execute('''
                    SELECT * FROM pending_offers
                    WHERE dynasty_id = ? AND season = ? AND wave = ? AND status = ?
                    ORDER BY player_id, aav DESC
                ''', (dynasty_id, season, wave, status))
            else:
                cursor = conn.execute('''
                    SELECT * FROM pending_offers
                    WHERE dynasty_id = ? AND season = ? AND wave = ?
                    ORDER BY player_id, aav DESC
                ''', (dynasty_id, season, wave))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_pending_offers_count(
        self,
        dynasty_id: str,
        team_id: Optional[int] = None
    ) -> int:
        """Get count of pending offers, optionally for a specific team."""
        conn = self._get_connection()
        try:
            if team_id:
                cursor = conn.execute('''
                    SELECT COUNT(*) as cnt FROM pending_offers
                    WHERE dynasty_id = ? AND offering_team_id = ? AND status = 'pending'
                ''', (dynasty_id, team_id))
            else:
                cursor = conn.execute('''
                    SELECT COUNT(*) as cnt FROM pending_offers
                    WHERE dynasty_id = ? AND status = 'pending'
                ''', (dynasty_id,))
            return cursor.fetchone()["cnt"]
        finally:
            conn.close()

    def update_offer_status(
        self,
        offer_id: int,
        status: str
    ) -> bool:
        """
        Update the status of an offer.

        Args:
            offer_id: Offer to update
            status: New status

        Returns:
            True if update succeeded, False if offer not found

        Raises:
            ValueError if status is invalid
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {self.VALID_STATUSES}")

        conn = self._get_connection()
        try:
            resolved_at = datetime.now().isoformat() if status != "pending" else None
            cursor = conn.execute('''
                UPDATE pending_offers
                SET status = ?, resolved_at = ?
                WHERE offer_id = ?
            ''', (status, resolved_at, offer_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def bulk_update_status(
        self,
        offer_ids: List[int],
        status: str
    ) -> int:
        """
        Update status for multiple offers.

        Args:
            offer_ids: List of offer IDs to update
            status: New status for all offers

        Returns:
            Number of offers updated
        """
        if not offer_ids:
            return 0

        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")

        conn = self._get_connection()
        try:
            resolved_at = datetime.now().isoformat() if status != "pending" else None
            placeholders = ",".join("?" * len(offer_ids))
            cursor = conn.execute(f'''
                UPDATE pending_offers
                SET status = ?, resolved_at = ?
                WHERE offer_id IN ({placeholders})
            ''', [status, resolved_at] + offer_ids)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def withdraw_offer(self, offer_id: int) -> bool:
        """Withdraw an offer (set status to 'withdrawn')."""
        return self.update_offer_status(offer_id, "withdrawn")

    def get_players_with_pending_offers(
        self,
        dynasty_id: str,
        season: int,
        wave: int
    ) -> List[int]:
        """Get list of player IDs that have pending offers in a wave."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                SELECT DISTINCT player_id FROM pending_offers
                WHERE dynasty_id = ? AND season = ? AND wave = ? AND status = 'pending'
            ''', (dynasty_id, season, wave))
            return [row["player_id"] for row in cursor.fetchall()]
        finally:
            conn.close()

    def check_existing_offer(
        self,
        dynasty_id: str,
        season: int,
        wave: int,
        player_id: int,
        team_id: int
    ) -> Optional[Dict[str, Any]]:
        """Check if a team already has an offer for a player in this wave."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM pending_offers
                WHERE dynasty_id = ? AND season = ? AND wave = ?
                AND player_id = ? AND offering_team_id = ?
            ''', (dynasty_id, season, wave, player_id, team_id))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_dynasty_offers(self, dynasty_id: str) -> int:
        """Delete all offers for a dynasty. Returns count deleted."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                DELETE FROM pending_offers WHERE dynasty_id = ?
            ''', (dynasty_id,))
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def expire_old_offers(
        self,
        dynasty_id: str,
        season: int,
        wave: int,
        deadline: int
    ) -> int:
        """
        Mark offers as expired if past their decision deadline.

        Args:
            dynasty_id: Dynasty to filter by
            season: Current season
            wave: Current wave
            deadline: Current day - offers with deadline < this are expired

        Returns:
            Number of offers expired
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                UPDATE pending_offers
                SET status = 'expired', resolved_at = ?
                WHERE dynasty_id = ? AND season = ? AND wave = ?
                AND status = 'pending' AND decision_deadline < ?
            ''', (datetime.now().isoformat(), dynasty_id, season, wave, deadline))
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
