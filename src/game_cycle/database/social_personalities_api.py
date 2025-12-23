"""
Social Personalities API for game_cycle.

Handles all social personality database operations including:
- Fan personalities (recurring fans with archetypes)
- Media personalities (beat reporters, analysts, hot-take pundits)

Part of Milestone 14: Social Media & Fan Reactions.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .connection import GameCycleDatabase


# ============================================
# Data Classes
# ============================================

@dataclass
class SocialPersonality:
    """Represents a recurring social media personality."""
    id: int
    dynasty_id: str
    handle: str  # @AlwaysBelievinBill
    display_name: str  # "Always Believin' Bill"
    personality_type: str  # 'FAN', 'BEAT_REPORTER', 'HOT_TAKE', 'STATS_ANALYST'
    archetype: Optional[str]  # 'OPTIMIST', 'PESSIMIST', etc. (NULL for media)
    team_id: Optional[int]  # NULL for league-wide media
    sentiment_bias: float  # -1.0 to 1.0
    posting_frequency: str  # 'ALL_EVENTS', 'WIN_ONLY', 'EMOTIONAL_MOMENTS', etc.
    created_at: Optional[str] = None


# ============================================
# Social Personality API
# ============================================

class SocialPersonalityAPI:
    """
    API for social personality operations in game_cycle.

    Handles:
    - Personality CRUD operations
    - Querying by team, type, archetype
    - Handle lookups

    All queries are dynasty-isolated for save game separation.
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db

    # ==========================================
    # CREATE
    # ==========================================

    def create_personality(
        self,
        dynasty_id: str,
        handle: str,
        display_name: str,
        personality_type: str,
        archetype: Optional[str],
        team_id: Optional[int],
        sentiment_bias: float,
        posting_frequency: str
    ) -> int:
        """
        Create a new social media personality.

        Args:
            dynasty_id: Dynasty identifier
            handle: Handle (e.g., "@AlwaysBelievinBill")
            display_name: Display name (e.g., "Always Believin' Bill")
            personality_type: 'FAN', 'BEAT_REPORTER', 'HOT_TAKE', 'STATS_ANALYST'
            archetype: Fan archetype or None for media (e.g., 'OPTIMIST', 'PESSIMIST')
            team_id: Team ID (1-32) or None for league-wide media
            sentiment_bias: Baseline sentiment (-1.0 to 1.0)
            posting_frequency: When they post ('ALL_EVENTS', 'WIN_ONLY', etc.)

        Returns:
            ID of created personality

        Raises:
            ValueError: If validation fails
            sqlite3.IntegrityError: If handle already exists in dynasty
        """
        # Validation
        if not handle.startswith('@'):
            raise ValueError(f"Handle must start with '@': {handle}")
        if personality_type not in ('FAN', 'BEAT_REPORTER', 'HOT_TAKE', 'STATS_ANALYST'):
            raise ValueError(f"Invalid personality_type: {personality_type}")
        if not (-1.0 <= sentiment_bias <= 1.0):
            raise ValueError(f"sentiment_bias must be between -1.0 and 1.0: {sentiment_bias}")
        if posting_frequency not in ('ALL_EVENTS', 'WIN_ONLY', 'LOSS_ONLY', 'EMOTIONAL_MOMENTS', 'UPSET_ONLY'):
            raise ValueError(f"Invalid posting_frequency: {posting_frequency}")

        cursor = self.db.execute(
            """INSERT INTO social_personalities
               (dynasty_id, handle, display_name, personality_type, archetype,
                team_id, sentiment_bias, posting_frequency)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id, handle, display_name, personality_type, archetype,
                team_id, sentiment_bias, posting_frequency
            )
        )
        return cursor.lastrowid

    # ==========================================
    # READ
    # ==========================================

    def get_personality_by_id(
        self,
        personality_id: int
    ) -> Optional[SocialPersonality]:
        """
        Get personality by ID.

        Args:
            personality_id: Personality ID

        Returns:
            SocialPersonality or None if not found
        """
        row = self.db.query_one(
            """SELECT id, dynasty_id, handle, display_name, personality_type, archetype,
                      team_id, sentiment_bias, posting_frequency, created_at
               FROM social_personalities
               WHERE id = ?""",
            (personality_id,)
        )
        return self._row_to_personality(row) if row else None

    def get_personality_by_handle(
        self,
        dynasty_id: str,
        handle: str
    ) -> Optional[SocialPersonality]:
        """
        Look up personality by @handle within a dynasty.

        Args:
            dynasty_id: Dynasty identifier
            handle: Handle to look up (e.g., "@AlwaysBelievinBill")

        Returns:
            SocialPersonality or None if not found
        """
        row = self.db.query_one(
            """SELECT id, dynasty_id, handle, display_name, personality_type, archetype,
                      team_id, sentiment_bias, posting_frequency, created_at
               FROM social_personalities
               WHERE dynasty_id = ? AND handle = ?""",
            (dynasty_id, handle)
        )
        return self._row_to_personality(row) if row else None

    def get_personalities_by_team(
        self,
        dynasty_id: str,
        team_id: int,
        personality_type: Optional[str] = None
    ) -> List[SocialPersonality]:
        """
        Get all personalities for a specific team.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            personality_type: Optional filter (e.g., 'FAN', 'BEAT_REPORTER')

        Returns:
            List of SocialPersonality objects
        """
        if personality_type:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, handle, display_name, personality_type, archetype,
                          team_id, sentiment_bias, posting_frequency, created_at
                   FROM social_personalities
                   WHERE dynasty_id = ? AND team_id = ? AND personality_type = ?
                   ORDER BY handle""",
                (dynasty_id, team_id, personality_type)
            )
        else:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, handle, display_name, personality_type, archetype,
                          team_id, sentiment_bias, posting_frequency, created_at
                   FROM social_personalities
                   WHERE dynasty_id = ? AND team_id = ?
                   ORDER BY handle""",
                (dynasty_id, team_id)
            )
        return [self._row_to_personality(row) for row in rows]

    def get_league_wide_personalities(
        self,
        dynasty_id: str,
        personality_type: Optional[str] = None
    ) -> List[SocialPersonality]:
        """
        Get all league-wide media personalities (team_id = NULL).

        Args:
            dynasty_id: Dynasty identifier
            personality_type: Optional filter (e.g., 'HOT_TAKE', 'STATS_ANALYST')

        Returns:
            List of SocialPersonality objects
        """
        if personality_type:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, handle, display_name, personality_type, archetype,
                          team_id, sentiment_bias, posting_frequency, created_at
                   FROM social_personalities
                   WHERE dynasty_id = ? AND team_id IS NULL AND personality_type = ?
                   ORDER BY handle""",
                (dynasty_id, personality_type)
            )
        else:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, handle, display_name, personality_type, archetype,
                          team_id, sentiment_bias, posting_frequency, created_at
                   FROM social_personalities
                   WHERE dynasty_id = ? AND team_id IS NULL
                   ORDER BY handle""",
                (dynasty_id,)
            )
        return [self._row_to_personality(row) for row in rows]

    def get_all_personalities(
        self,
        dynasty_id: str,
        personality_type: Optional[str] = None
    ) -> List[SocialPersonality]:
        """
        Get all personalities in a dynasty.

        Args:
            dynasty_id: Dynasty identifier
            personality_type: Optional filter by type

        Returns:
            List of SocialPersonality objects
        """
        if personality_type:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, handle, display_name, personality_type, archetype,
                          team_id, sentiment_bias, posting_frequency, created_at
                   FROM social_personalities
                   WHERE dynasty_id = ? AND personality_type = ?
                   ORDER BY handle""",
                (dynasty_id, personality_type)
            )
        else:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, handle, display_name, personality_type, archetype,
                          team_id, sentiment_bias, posting_frequency, created_at
                   FROM social_personalities
                   WHERE dynasty_id = ?
                   ORDER BY handle""",
                (dynasty_id,)
            )
        return [self._row_to_personality(row) for row in rows]

    def get_personalities_by_archetype(
        self,
        dynasty_id: str,
        archetype: str,
        team_id: Optional[int] = None
    ) -> List[SocialPersonality]:
        """
        Get all fan personalities with a specific archetype.

        Args:
            dynasty_id: Dynasty identifier
            archetype: Fan archetype (e.g., 'OPTIMIST', 'PESSIMIST')
            team_id: Optional team filter

        Returns:
            List of SocialPersonality objects
        """
        if team_id:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, handle, display_name, personality_type, archetype,
                          team_id, sentiment_bias, posting_frequency, created_at
                   FROM social_personalities
                   WHERE dynasty_id = ? AND archetype = ? AND team_id = ?
                   ORDER BY handle""",
                (dynasty_id, archetype, team_id)
            )
        else:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, handle, display_name, personality_type, archetype,
                          team_id, sentiment_bias, posting_frequency, created_at
                   FROM social_personalities
                   WHERE dynasty_id = ? AND archetype = ?
                   ORDER BY handle""",
                (dynasty_id, archetype)
            )
        return [self._row_to_personality(row) for row in rows]

    def count_personalities(
        self,
        dynasty_id: str,
        personality_type: Optional[str] = None
    ) -> int:
        """
        Count total personalities in dynasty.

        Args:
            dynasty_id: Dynasty identifier
            personality_type: Optional filter by type

        Returns:
            Count of personalities
        """
        if personality_type:
            row = self.db.query_one(
                """SELECT COUNT(*) as count
                   FROM social_personalities
                   WHERE dynasty_id = ? AND personality_type = ?""",
                (dynasty_id, personality_type)
            )
        else:
            row = self.db.query_one(
                """SELECT COUNT(*) as count
                   FROM social_personalities
                   WHERE dynasty_id = ?""",
                (dynasty_id,)
            )
        return row['count'] if row else 0

    # ==========================================
    # UPDATE
    # ==========================================

    def update_sentiment_bias(
        self,
        personality_id: int,
        new_bias: float
    ) -> bool:
        """
        Update a personality's sentiment bias.

        Args:
            personality_id: Personality ID
            new_bias: New sentiment bias (-1.0 to 1.0)

        Returns:
            True if updated, False if not found

        Raises:
            ValueError: If new_bias out of range
        """
        if not (-1.0 <= new_bias <= 1.0):
            raise ValueError(f"new_bias must be between -1.0 and 1.0: {new_bias}")

        cursor = self.db.execute(
            """UPDATE social_personalities
               SET sentiment_bias = ?
               WHERE id = ?""",
            (new_bias, personality_id)
        )
        return cursor.rowcount > 0

    # ==========================================
    # DELETE
    # ==========================================

    def delete_personality(
        self,
        personality_id: int
    ) -> bool:
        """
        Delete a personality (and all their posts via CASCADE).

        Args:
            personality_id: Personality ID

        Returns:
            True if deleted, False if not found
        """
        cursor = self.db.execute(
            """DELETE FROM social_personalities WHERE id = ?""",
            (personality_id,)
        )
        return cursor.rowcount > 0

    def delete_all_personalities(
        self,
        dynasty_id: str
    ) -> int:
        """
        Delete all personalities in a dynasty.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Number of personalities deleted
        """
        cursor = self.db.execute(
            """DELETE FROM social_personalities WHERE dynasty_id = ?""",
            (dynasty_id,)
        )
        return cursor.rowcount

    # ==========================================
    # CONVERTERS
    # ==========================================

    def _row_to_personality(self, row: Dict[str, Any]) -> SocialPersonality:
        """Convert database row to SocialPersonality dataclass."""
        return SocialPersonality(
            id=row['id'],
            dynasty_id=row['dynasty_id'],
            handle=row['handle'],
            display_name=row['display_name'],
            personality_type=row['personality_type'],
            archetype=row['archetype'],
            team_id=row['team_id'],
            sentiment_bias=row['sentiment_bias'],
            posting_frequency=row['posting_frequency'],
            created_at=row['created_at']
        )
