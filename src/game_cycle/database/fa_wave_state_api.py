"""
Database API for FA wave state operations.

Part of Milestone 8: Free Agency Depth.
Tracks current wave and day progression during multi-wave free agency.
"""
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class FAWaveState:
    """Represents the current state of free agency waves."""
    dynasty_id: str
    season: int
    current_wave: int
    current_day: int
    wave_complete: bool
    post_draft_available: bool
    created_at: Optional[str] = None
    modified_at: Optional[str] = None


# Wave configuration constants
WAVE_CONFIGS = {
    0: {"name": "Legal Tampering", "min_ovr": 0, "max_ovr": 99, "days": 1, "signing_allowed": False},
    1: {"name": "Wave 1 - Elite", "min_ovr": 85, "max_ovr": 99, "days": 3, "signing_allowed": True},
    2: {"name": "Wave 2 - Quality", "min_ovr": 75, "max_ovr": 84, "days": 2, "signing_allowed": True},
    3: {"name": "Wave 3 - Depth", "min_ovr": 65, "max_ovr": 74, "days": 2, "signing_allowed": True},
    4: {"name": "Post-Draft", "min_ovr": 0, "max_ovr": 99, "days": 1, "signing_allowed": True},
}


class FAWaveStateAPI:
    """API for FA wave state database operations."""

    def __init__(self, db_path: str):
        self._db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_wave_state(
        self,
        dynasty_id: str,
        season: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get current wave state for a dynasty/season.

        Returns:
            Dict with wave state or None if not initialized
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM fa_wave_state
                WHERE dynasty_id = ? AND season = ?
            ''', (dynasty_id, season))
            row = cursor.fetchone()
            if row:
                return {
                    "dynasty_id": row["dynasty_id"],
                    "season": row["season"],
                    "current_wave": row["current_wave"],
                    "current_day": row["current_day"],
                    "wave_complete": bool(row["wave_complete"]),
                    "post_draft_available": bool(row["post_draft_available"]),
                    "created_at": row["created_at"],
                    "modified_at": row["modified_at"],
                    # Add derived fields for convenience
                    "wave_name": WAVE_CONFIGS.get(row["current_wave"], {}).get("name", "Unknown"),
                    "days_in_wave": WAVE_CONFIGS.get(row["current_wave"], {}).get("days", 1),
                    "signing_allowed": WAVE_CONFIGS.get(row["current_wave"], {}).get("signing_allowed", False),
                }
            return None
        finally:
            conn.close()

    def initialize_wave_state(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[str, Any]:
        """
        Initialize wave state for a new FA period (starts at wave 0, day 1).

        Returns:
            The created wave state
        """
        conn = self._get_connection()
        try:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT OR REPLACE INTO fa_wave_state
                (dynasty_id, season, current_wave, current_day, wave_complete,
                 post_draft_available, created_at, modified_at)
                VALUES (?, ?, 0, 1, 0, 0, ?, ?)
            ''', (dynasty_id, season, now, now))
            conn.commit()
            return self.get_wave_state(dynasty_id, season)
        finally:
            conn.close()

    def advance_day(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[str, Any]:
        """
        Advance to the next day within the current wave.

        If current day equals max days for wave, marks wave_complete = True.

        Returns:
            Updated wave state
        """
        state = self.get_wave_state(dynasty_id, season)
        if not state:
            raise ValueError(f"No wave state found for dynasty {dynasty_id}, season {season}")

        current_wave = state["current_wave"]
        current_day = state["current_day"]
        max_days = WAVE_CONFIGS.get(current_wave, {}).get("days", 1)

        new_day = current_day + 1
        wave_complete = new_day > max_days

        if wave_complete:
            new_day = max_days  # Cap at max days

        conn = self._get_connection()
        try:
            conn.execute('''
                UPDATE fa_wave_state
                SET current_day = ?, wave_complete = ?, modified_at = ?
                WHERE dynasty_id = ? AND season = ?
            ''', (new_day, 1 if wave_complete else 0, datetime.now().isoformat(),
                  dynasty_id, season))
            conn.commit()
            return self.get_wave_state(dynasty_id, season)
        finally:
            conn.close()

    def advance_wave(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[str, Any]:
        """
        Advance to the next wave (resets day to 1).

        Wave 3 -> requires draft complete to move to wave 4.
        Wave 4 -> returns None (FA complete).

        Returns:
            Updated wave state, or None if FA is complete
        """
        state = self.get_wave_state(dynasty_id, season)
        if not state:
            raise ValueError(f"No wave state found for dynasty {dynasty_id}, season {season}")

        current_wave = state["current_wave"]

        # Check if moving to post-draft wave (4)
        if current_wave == 3 and not state["post_draft_available"]:
            # Can't advance to wave 4 until draft is complete
            raise ValueError("Cannot advance to post-draft wave until draft is complete")

        # Calculate next wave
        if current_wave >= 4:
            # FA complete
            return None

        # Wave 3 -> advance to wave 4 if draft is complete
        if current_wave == 3:
            if state["post_draft_available"]:
                # Draft is complete, advance to wave 4
                new_wave = 4
                conn = self._get_connection()
                try:
                    conn.execute('''
                        UPDATE fa_wave_state
                        SET current_wave = ?, current_day = 1, wave_complete = 0, modified_at = ?
                        WHERE dynasty_id = ? AND season = ?
                    ''', (new_wave, datetime.now().isoformat(), dynasty_id, season))
                    conn.commit()
                    return self.get_wave_state(dynasty_id, season)
                finally:
                    conn.close()
            else:
                # Draft not complete yet, can't advance (already checked above, but being explicit)
                raise ValueError("Cannot advance to post-draft wave until draft is complete")

        new_wave = current_wave + 1

        conn = self._get_connection()
        try:
            conn.execute('''
                UPDATE fa_wave_state
                SET current_wave = ?, current_day = 1, wave_complete = 0, modified_at = ?
                WHERE dynasty_id = ? AND season = ?
            ''', (new_wave, datetime.now().isoformat(), dynasty_id, season))
            conn.commit()
            return self.get_wave_state(dynasty_id, season)
        finally:
            conn.close()

    def enable_post_draft_wave(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[str, Any]:
        """
        Enable post-draft wave (wave 4) after draft completes.

        This sets post_draft_available = True and advances to wave 4.

        Returns:
            Updated wave state
        """
        conn = self._get_connection()
        try:
            conn.execute('''
                UPDATE fa_wave_state
                SET post_draft_available = 1, current_wave = 4, current_day = 1,
                    wave_complete = 0, modified_at = ?
                WHERE dynasty_id = ? AND season = ?
            ''', (datetime.now().isoformat(), dynasty_id, season))
            conn.commit()
            return self.get_wave_state(dynasty_id, season)
        finally:
            conn.close()

    def mark_wave_complete(
        self,
        dynasty_id: str,
        season: int
    ) -> bool:
        """Mark the current wave as complete."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                UPDATE fa_wave_state
                SET wave_complete = 1, modified_at = ?
                WHERE dynasty_id = ? AND season = ?
            ''', (datetime.now().isoformat(), dynasty_id, season))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def reset_wave_state(
        self,
        dynasty_id: str,
        season: int
    ) -> bool:
        """Reset wave state to initial (wave 0, day 1). For testing."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                UPDATE fa_wave_state
                SET current_wave = 0, current_day = 1, wave_complete = 0,
                    post_draft_available = 0, modified_at = ?
                WHERE dynasty_id = ? AND season = ?
            ''', (datetime.now().isoformat(), dynasty_id, season))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_wave_state(
        self,
        dynasty_id: str,
        season: int
    ) -> bool:
        """Delete wave state for a dynasty/season. Returns True if deleted."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                DELETE FROM fa_wave_state
                WHERE dynasty_id = ? AND season = ?
            ''', (dynasty_id, season))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def is_signing_allowed(
        self,
        dynasty_id: str,
        season: int
    ) -> bool:
        """Check if signing is allowed in current wave (not legal tampering)."""
        state = self.get_wave_state(dynasty_id, season)
        if not state:
            return False
        return state["signing_allowed"]

    def get_wave_config(self, wave: int) -> Dict[str, Any]:
        """Get configuration for a specific wave number."""
        return WAVE_CONFIGS.get(wave, {
            "name": "Unknown",
            "min_ovr": 0,
            "max_ovr": 99,
            "days": 1,
            "signing_allowed": False
        })

    def is_fa_complete(
        self,
        dynasty_id: str,
        season: int
    ) -> bool:
        """Check if all FA waves are complete (including post-draft)."""
        state = self.get_wave_state(dynasty_id, season)
        if not state:
            return False
        # FA is complete if we're on wave 4 and it's marked complete
        return state["current_wave"] == 4 and state["wave_complete"]
