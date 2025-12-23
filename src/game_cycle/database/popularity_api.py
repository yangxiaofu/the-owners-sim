"""
Popularity API for game_cycle.

Handles database operations for the Player Popularity System including:
- Weekly popularity scores (Performance × Visibility × Market formula)
- Popularity trends and tier classification
- Popularity events (audit trail)

Part of Milestone 16: Player Popularity.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from .connection import GameCycleDatabase

logger = logging.getLogger(__name__)


# ============================================
# Enums
# ============================================

class PopularityTier(Enum):
    """Player popularity tier classification."""

    TRANSCENDENT = "TRANSCENDENT"  # 90-100: Household names, league-wide recognition
    STAR = "STAR"  # 75-89: Well-known players, fan favorites
    KNOWN = "KNOWN"  # 50-74: Recognized by dedicated fans
    ROLE_PLAYER = "ROLE_PLAYER"  # 25-49: Known to team fans, less visibility
    UNKNOWN = "UNKNOWN"  # 0-24: Limited recognition

    @staticmethod
    def from_score(score: float) -> 'PopularityTier':
        """
        Classify popularity tier based on score.

        Args:
            score: Popularity score (0-100)

        Returns:
            PopularityTier enum
        """
        if score >= 90:
            return PopularityTier.TRANSCENDENT
        elif score >= 75:
            return PopularityTier.STAR
        elif score >= 50:
            return PopularityTier.KNOWN
        elif score >= 25:
            return PopularityTier.ROLE_PLAYER
        else:
            return PopularityTier.UNKNOWN


class PopularityTrend(Enum):
    """Player popularity trend direction."""

    RISING = "RISING"  # +5 or more over 4 weeks
    FALLING = "FALLING"  # -5 or more over 4 weeks
    STABLE = "STABLE"  # Within ±5 over 4 weeks


# ============================================
# Dataclasses
# ============================================

@dataclass
class PopularityScore:
    """Represents a player's popularity score for a specific week."""
    id: int
    dynasty_id: str
    player_id: int
    season: int
    week: int
    popularity_score: float
    performance_score: float
    visibility_multiplier: float
    market_multiplier: float
    week_change: Optional[float]
    trend: str
    tier: str
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'dynasty_id': self.dynasty_id,
            'player_id': self.player_id,
            'season': self.season,
            'week': self.week,
            'popularity_score': self.popularity_score,
            'performance_score': self.performance_score,
            'visibility_multiplier': self.visibility_multiplier,
            'market_multiplier': self.market_multiplier,
            'week_change': self.week_change,
            'trend': self.trend,
            'tier': self.tier,
            'created_at': self.created_at,
        }


@dataclass
class PopularityEvent:
    """Represents a popularity-impacting event."""
    id: int
    dynasty_id: str
    player_id: int
    season: int
    week: int
    event_type: str
    impact: float
    description: Optional[str]
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'dynasty_id': self.dynasty_id,
            'player_id': self.player_id,
            'season': self.season,
            'week': self.week,
            'event_type': self.event_type,
            'impact': self.impact,
            'description': self.description,
            'created_at': self.created_at,
        }


# ============================================
# PopularityAPI Class
# ============================================

class PopularityAPI:
    """
    API for Player Popularity System database operations.

    Handles:
    - Popularity score CRUD (weekly tracking)
    - Top players queries (leaderboards)
    - Historical trends (4-week rolling)
    - Tier filtering (TRANSCENDENT, STAR, etc.)
    - Popularity events (audit trail)

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
    # POPULARITY SCORES
    # ==========================================

    def save_popularity_score(
        self,
        dynasty_id: str,
        player_id: int,
        season: int,
        week: int,
        popularity_score: float,
        performance_score: float,
        visibility_multiplier: float,
        market_multiplier: float,
        week_change: Optional[float] = None,
        trend: Optional[str] = None,
        tier: Optional[str] = None
    ) -> int:
        """
        Insert or update a player's popularity score for a week.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID
            season: Season year
            week: Week number
            popularity_score: Final popularity score (0-100)
            performance_score: Base performance score (0-100)
            visibility_multiplier: Visibility factor (0.5-3.0)
            market_multiplier: Market size factor (0.8-2.0)
            week_change: Change from previous week (optional)
            trend: Trend direction ('RISING', 'FALLING', 'STABLE') (optional)
            tier: Popularity tier (optional, auto-calculated if None)

        Returns:
            ID of saved record

        Raises:
            ValueError: If scores are out of valid range
        """
        # Validate ranges
        if not (0 <= popularity_score <= 100):
            raise ValueError(f"popularity_score must be 0-100, got {popularity_score}")
        if not (0 <= performance_score <= 100):
            raise ValueError(f"performance_score must be 0-100, got {performance_score}")
        if not (0.5 <= visibility_multiplier <= 3.0):
            raise ValueError(f"visibility_multiplier must be 0.5-3.0, got {visibility_multiplier}")
        if not (0.8 <= market_multiplier <= 2.0):
            raise ValueError(f"market_multiplier must be 0.8-2.0, got {market_multiplier}")

        # Auto-calculate tier if not provided
        if tier is None:
            tier = PopularityTier.from_score(popularity_score).value

        logger.debug(
            f"Saving popularity score: player={player_id}, season={season}, "
            f"week={week}, score={popularity_score:.1f}, tier={tier}"
        )

        cursor = self.db.execute(
            """INSERT OR REPLACE INTO player_popularity
               (dynasty_id, player_id, season, week, popularity_score,
                performance_score, visibility_multiplier, market_multiplier,
                week_change, trend, tier)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id, player_id, season, week, popularity_score,
                performance_score, visibility_multiplier, market_multiplier,
                week_change, trend, tier
            )
        )
        return cursor.lastrowid

    def get_popularity_score(
        self,
        dynasty_id: str,
        player_id: int,
        season: int,
        week: int
    ) -> Optional[PopularityScore]:
        """
        Get a player's popularity score for a specific week.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID
            season: Season year
            week: Week number

        Returns:
            PopularityScore if found, None otherwise
        """
        row = self.db.query_one(
            """SELECT id, dynasty_id, player_id, season, week, popularity_score,
                      performance_score, visibility_multiplier, market_multiplier,
                      week_change, trend, tier, created_at
               FROM player_popularity
               WHERE dynasty_id = ? AND player_id = ? AND season = ? AND week = ?""",
            (dynasty_id, player_id, season, week)
        )
        return self._row_to_popularity_score(row) if row else None

    def get_top_players(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        limit: int = 10
    ) -> List[PopularityScore]:
        """
        Get top N most popular players for a week.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            limit: Max number of players to return (default 10)

        Returns:
            List of PopularityScore sorted by popularity_score descending
        """
        logger.debug(
            f"Querying top {limit} popular players: dynasty={dynasty_id}, "
            f"season={season}, week={week}"
        )

        rows = self.db.query_all(
            """SELECT id, dynasty_id, player_id, season, week, popularity_score,
                      performance_score, visibility_multiplier, market_multiplier,
                      week_change, trend, tier, created_at
               FROM player_popularity
               WHERE dynasty_id = ? AND season = ? AND week = ?
               ORDER BY popularity_score DESC
               LIMIT ?""",
            (dynasty_id, season, week, limit)
        )

        logger.debug(f"Query returned {len(rows)} popular players")
        return [self._row_to_popularity_score(row) for row in rows]

    def get_popularity_trend(
        self,
        dynasty_id: str,
        player_id: int,
        season: int,
        weeks: int = 4
    ) -> List[PopularityScore]:
        """
        Get a player's popularity history for trend analysis.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID
            season: Season year
            weeks: Number of recent weeks to retrieve (default 4)

        Returns:
            List of PopularityScore sorted by week ascending
        """
        rows = self.db.query_all(
            """SELECT id, dynasty_id, player_id, season, week, popularity_score,
                      performance_score, visibility_multiplier, market_multiplier,
                      week_change, trend, tier, created_at
               FROM player_popularity
               WHERE dynasty_id = ? AND player_id = ? AND season = ?
               ORDER BY week DESC
               LIMIT ?""",
            (dynasty_id, player_id, season, weeks)
        )
        # Reverse to get ascending order (oldest to newest)
        return [self._row_to_popularity_score(row) for row in reversed(rows)]

    def get_players_by_tier(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        tier: str
    ) -> List[PopularityScore]:
        """
        Get all players in a specific popularity tier.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            tier: Popularity tier ('TRANSCENDENT', 'STAR', 'KNOWN', 'ROLE_PLAYER', 'UNKNOWN')

        Returns:
            List of PopularityScore in the tier, sorted by score descending
        """
        rows = self.db.query_all(
            """SELECT id, dynasty_id, player_id, season, week, popularity_score,
                      performance_score, visibility_multiplier, market_multiplier,
                      week_change, trend, tier, created_at
               FROM player_popularity
               WHERE dynasty_id = ? AND season = ? AND week = ? AND tier = ?
               ORDER BY popularity_score DESC""",
            (dynasty_id, season, week, tier)
        )
        return [self._row_to_popularity_score(row) for row in rows]

    def get_team_popularity_summary(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        team_id: int
    ) -> Dict[str, Any]:
        """
        Get team popularity summary (star power).

        NOTE: This query requires joining with the players table which is in
        nfl_simulation.db (legacy database). This method is a placeholder for
        future cross-database queries.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            team_id: Team ID (1-32)

        Returns:
            Dictionary with tier counts and top player
        """
        # TODO: Implement once cross-database query pattern is established
        # For now, return empty summary
        logger.warning(
            "get_team_popularity_summary requires cross-database query "
            "(game_cycle.db + nfl_simulation.db). Not yet implemented."
        )
        return {
            'team_id': team_id,
            'tier_counts': {},
            'top_player': None
        }

    # ==========================================
    # POPULARITY EVENTS
    # ==========================================

    def save_popularity_event(
        self,
        dynasty_id: str,
        player_id: int,
        season: int,
        week: int,
        event_type: str,
        impact: float,
        description: Optional[str] = None
    ) -> int:
        """
        Log a popularity event (audit trail).

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID
            season: Season year
            week: Week number
            event_type: Event type ('HEADLINE', 'AWARD', 'MILESTONE', 'SOCIAL_SPIKE', 'INJURY', etc.)
            impact: Positive or negative impact value
            description: Event description (optional)

        Returns:
            ID of saved event
        """
        logger.debug(
            f"Saving popularity event: player={player_id}, type={event_type}, "
            f"impact={impact:+.1f}, week={week}"
        )

        cursor = self.db.execute(
            """INSERT INTO player_popularity_events
               (dynasty_id, player_id, season, week, event_type, impact, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dynasty_id, player_id, season, week, event_type, impact, description)
        )
        return cursor.lastrowid

    def get_popularity_events(
        self,
        dynasty_id: str,
        player_id: int,
        season: int,
        week: Optional[int] = None
    ) -> List[PopularityEvent]:
        """
        Get popularity events for a player.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID
            season: Season year
            week: Optional week filter

        Returns:
            List of PopularityEvent sorted by created_at descending
        """
        if week is not None:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, player_id, season, week, event_type,
                          impact, description, created_at
                   FROM player_popularity_events
                   WHERE dynasty_id = ? AND player_id = ? AND season = ? AND week = ?
                   ORDER BY created_at DESC""",
                (dynasty_id, player_id, season, week)
            )
        else:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, player_id, season, week, event_type,
                          impact, description, created_at
                   FROM player_popularity_events
                   WHERE dynasty_id = ? AND player_id = ? AND season = ?
                   ORDER BY created_at DESC""",
                (dynasty_id, player_id, season)
            )
        return [self._row_to_popularity_event(row) for row in rows]

    def get_weekly_events_summary(
        self,
        dynasty_id: str,
        season: int,
        week: int
    ) -> Dict[str, int]:
        """
        Get summary of popularity events for a week.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number

        Returns:
            Dictionary with event type counts
        """
        rows = self.db.query_all(
            """SELECT event_type, COUNT(*) as count
               FROM player_popularity_events
               WHERE dynasty_id = ? AND season = ? AND week = ?
               GROUP BY event_type""",
            (dynasty_id, season, week)
        )

        return {row['event_type']: row['count'] for row in rows}

    # ==========================================
    # DELETION METHODS (for testing)
    # ==========================================

    def clear_player_popularity(
        self,
        dynasty_id: str,
        player_id: int
    ) -> Dict[str, int]:
        """
        Clear all popularity data for a player.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID

        Returns:
            Dictionary with counts of deleted records per table
        """
        counts = {}

        cursor = self.db.execute(
            "DELETE FROM player_popularity WHERE dynasty_id = ? AND player_id = ?",
            (dynasty_id, player_id)
        )
        counts['popularity_scores'] = cursor.rowcount

        cursor = self.db.execute(
            "DELETE FROM player_popularity_events WHERE dynasty_id = ? AND player_id = ?",
            (dynasty_id, player_id)
        )
        counts['popularity_events'] = cursor.rowcount

        return counts

    def clear_season_popularity(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[str, int]:
        """
        Clear all popularity data for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dictionary with counts of deleted records per table
        """
        counts = {}

        cursor = self.db.execute(
            "DELETE FROM player_popularity WHERE dynasty_id = ? AND season = ?",
            (dynasty_id, season)
        )
        counts['popularity_scores'] = cursor.rowcount

        cursor = self.db.execute(
            "DELETE FROM player_popularity_events WHERE dynasty_id = ? AND season = ?",
            (dynasty_id, season)
        )
        counts['popularity_events'] = cursor.rowcount

        return counts

    # ==========================================
    # PRIVATE HELPER METHODS
    # ==========================================

    def _row_to_popularity_score(self, row) -> PopularityScore:
        """Convert database row to PopularityScore dataclass."""
        return PopularityScore(
            id=row['id'],
            dynasty_id=row['dynasty_id'],
            player_id=row['player_id'],
            season=row['season'],
            week=row['week'],
            popularity_score=row['popularity_score'],
            performance_score=row['performance_score'],
            visibility_multiplier=row['visibility_multiplier'],
            market_multiplier=row['market_multiplier'],
            week_change=row['week_change'],
            trend=row['trend'],
            tier=row['tier'],
            created_at=row['created_at'],
        )

    def _row_to_popularity_event(self, row) -> PopularityEvent:
        """Convert database row to PopularityEvent dataclass."""
        return PopularityEvent(
            id=row['id'],
            dynasty_id=row['dynasty_id'],
            player_id=row['player_id'],
            season=row['season'],
            week=row['week'],
            event_type=row['event_type'],
            impact=row['impact'],
            description=row['description'],
            created_at=row['created_at'],
        )
