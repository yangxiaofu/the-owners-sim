"""
Social Posts API for game_cycle.

Handles all social post database operations including:
- Post creation and retrieval
- Chronological feed queries with filters
- Pagination support

Part of Milestone 14: Social Media & Fan Reactions.
"""

import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Union

from .connection import GameCycleDatabase
from ..models.social_event_types import SocialEventType, SocialSentiment


# ============================================
# Data Classes
# ============================================

@dataclass
class SocialPost:
    """Represents a social media post from a personality."""
    id: int
    dynasty_id: str
    personality_id: int
    season: int
    week: int
    post_text: str
    event_type: str  # 'GAME_RESULT', 'TRADE', 'SIGNING', etc.
    sentiment: float  # -1.0 to 1.0
    likes: int
    retweets: int
    event_metadata: Dict[str, Any]  # JSON: {game_id: 123, score: "31-17"}
    created_at: Optional[str] = None

    # Joined data (from personality table)
    handle: Optional[str] = None  # @AlwaysBelievinBill
    display_name: Optional[str] = None  # "Always Believin' Bill"
    personality_type: Optional[str] = None  # 'FAN', 'BEAT_REPORTER', etc.
    team_id: Optional[int] = None


# ============================================
# Social Posts API
# ============================================

class SocialPostsAPI:
    """
    API for social post operations in game_cycle.

    Handles:
    - Post CRUD operations
    - Chronological feed queries (latest first)
    - Filtering by team, event type, sentiment
    - Pagination support (limit/offset)

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

    def create_post(
        self,
        dynasty_id: str,
        personality_id: int,
        season: int,
        week: int,
        post_text: str,
        event_type: Union[str, SocialEventType],
        sentiment: float,
        likes: int = 0,
        retweets: int = 0,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Create a new social media post.

        Args:
            dynasty_id: Dynasty identifier
            personality_id: ID of posting personality
            season: Season year
            week: Week number
            post_text: Post content
            event_type: SocialEventType enum or string ('GAME_RESULT', 'TRADE', etc.)
            sentiment: Post sentiment (-1.0 to 1.0)
            likes: Number of likes (default: 0)
            retweets: Number of retweets (default: 0)
            event_metadata: Optional JSON metadata about the event

        Returns:
            ID of created post

        Raises:
            ValueError: If validation fails
        """
        # Convert enum to string if needed (backward compatible)
        event_type_str = event_type.value if isinstance(event_type, SocialEventType) else event_type

        # Validation
        valid_types = {e.value for e in SocialEventType}
        if event_type_str not in valid_types:
            raise ValueError(f"Invalid event_type: {event_type_str}")
        if not (-1.0 <= sentiment <= 1.0):
            raise ValueError(f"sentiment must be between -1.0 and 1.0: {sentiment}")
        if likes < 0:
            raise ValueError(f"likes cannot be negative: {likes}")
        if retweets < 0:
            raise ValueError(f"retweets cannot be negative: {retweets}")
        if not post_text.strip():
            raise ValueError("post_text cannot be empty")

        metadata_json = json.dumps(event_metadata) if event_metadata else None

        cursor = self.db.execute(
            """INSERT INTO social_posts
               (dynasty_id, personality_id, season, week, post_text, event_type,
                sentiment, likes, retweets, event_metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id, personality_id, season, week, post_text, event_type_str,
                sentiment, likes, retweets, metadata_json
            )
        )
        return cursor.lastrowid

    # ==========================================
    # READ - FEED QUERIES
    # ==========================================

    def get_rolling_feed(
        self,
        dynasty_id: str,
        season: int,
        week: Optional[int],
        limit: int = 20,
        offset: int = 0,
        team_filter: Optional[int] = None,
        event_type_filter: Optional[str] = None,
        sentiment_filter: Optional[str] = None  # 'POSITIVE', 'NEGATIVE', 'NEUTRAL'
    ) -> List[SocialPost]:
        """
        Get chronological feed of posts for a season/week (latest first).

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number (None = all weeks for season)
            limit: Max posts to return (default: 20)
            offset: Pagination offset (default: 0)
            team_filter: Optional team ID to filter by
            event_type_filter: Optional event type filter
            sentiment_filter: Optional sentiment filter ('POSITIVE', 'NEGATIVE', 'NEUTRAL')

        Returns:
            List of SocialPost objects with personality data joined
        """
        # Build WHERE clauses
        where_clauses = ["sp.dynasty_id = ?", "sp.season = ?"]
        params: List[Any] = [dynasty_id, season]

        # Handle week filter (NULL-safe SQL)
        if week is not None:
            where_clauses.append("sp.week = ?")
            params.append(week)
        # If week is None, don't add week filter (returns all weeks for season)

        if team_filter is not None:
            where_clauses.append("pers.team_id = ?")
            params.append(team_filter)

        if event_type_filter:
            where_clauses.append("sp.event_type = ?")
            params.append(event_type_filter)

        if sentiment_filter:
            if sentiment_filter == 'POSITIVE':
                where_clauses.append("sp.sentiment > 0.3")
            elif sentiment_filter == 'NEGATIVE':
                where_clauses.append("sp.sentiment < -0.3")
            elif sentiment_filter == 'NEUTRAL':
                where_clauses.append("sp.sentiment BETWEEN -0.3 AND 0.3")

        where_sql = " AND ".join(where_clauses)
        params.extend([limit, offset])

        query = f"""
            SELECT sp.id, sp.dynasty_id, sp.personality_id, sp.season, sp.week,
                   sp.post_text, sp.event_type, sp.sentiment, sp.likes, sp.retweets,
                   sp.event_metadata, sp.created_at,
                   pers.handle, pers.display_name, pers.personality_type, pers.team_id
            FROM social_posts sp
            INNER JOIN social_personalities pers ON sp.personality_id = pers.id
            WHERE {where_sql}
            ORDER BY sp.created_at DESC
            LIMIT ? OFFSET ?
        """

        rows = self.db.query_all(query, tuple(params))
        return [self._row_to_post(row) for row in rows]

    def get_multi_week_feed(
        self,
        dynasty_id: str,
        season: int,
        start_week: int,
        end_week: int,
        limit: int = 50,
        offset: int = 0,
        team_filter: Optional[int] = None,
        event_type_filter: Optional[str] = None
    ) -> List[SocialPost]:
        """
        Get posts across multiple weeks (for "recent activity" views).

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            start_week: Starting week (inclusive)
            end_week: Ending week (inclusive)
            limit: Max posts to return
            offset: Pagination offset
            team_filter: Optional team ID filter
            event_type_filter: Optional event type filter

        Returns:
            List of SocialPost objects ordered by created_at DESC
        """
        where_clauses = [
            "sp.dynasty_id = ?",
            "sp.season = ?",
            "sp.week BETWEEN ? AND ?"
        ]
        params: List[Any] = [dynasty_id, season, start_week, end_week]

        if team_filter is not None:
            where_clauses.append("pers.team_id = ?")
            params.append(team_filter)

        if event_type_filter:
            where_clauses.append("sp.event_type = ?")
            params.append(event_type_filter)

        where_sql = " AND ".join(where_clauses)
        params.extend([limit, offset])

        query = f"""
            SELECT sp.id, sp.dynasty_id, sp.personality_id, sp.season, sp.week,
                   sp.post_text, sp.event_type, sp.sentiment, sp.likes, sp.retweets,
                   sp.event_metadata, sp.created_at,
                   pers.handle, pers.display_name, pers.personality_type, pers.team_id
            FROM social_posts sp
            INNER JOIN social_personalities pers ON sp.personality_id = pers.id
            WHERE {where_sql}
            ORDER BY sp.created_at DESC
            LIMIT ? OFFSET ?
        """

        rows = self.db.query_all(query, tuple(params))
        return [self._row_to_post(row) for row in rows]

    def get_posts_by_stage(
        self,
        dynasty_id: str,
        season: int,
        stage_type: "StageType",  # Forward reference to avoid circular import
        limit: int = 20,
        offset: int = 0,
        team_filter: Optional[int] = None,
        event_type_filter: Optional[Union[str, SocialEventType]] = None,
        sentiment_filter: Optional[Union[str, SocialSentiment]] = None
    ) -> List[SocialPost]:
        """
        Get posts for a specific stage (uses week mapping from Stage).

        This is the stage-aware version of get_rolling_feed().
        Maps stage_type to week number via Stage.week_number property.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            stage_type: StageType enum (e.g., OFFSEASON_HONORS, WILD_CARD)
            limit: Max posts to return (default: 20)
            offset: Pagination offset (default: 0)
            team_filter: Optional team ID filter
            event_type_filter: Optional event type (SocialEventType or string)
            sentiment_filter: Optional sentiment (SocialSentiment or string)

        Returns:
            List of SocialPost objects for that stage's week

        Example:
            # Get posts from Honors week (week 23)
            posts = api.get_posts_by_stage(
                dynasty_id, 2025, StageType.OFFSEASON_HONORS
            )
        """
        from ..stage_definitions import Stage

        # Map stage to week using Stage.week_number property
        stage = Stage(stage_type=stage_type, season_year=season)
        week = stage.week_number

        # Note: week can be None for some stages - get_rolling_feed() handles this
        # by returning all posts for the season when week is None

        # Convert enums to strings if needed
        event_type_str = None
        if event_type_filter:
            event_type_str = (
                event_type_filter.value
                if isinstance(event_type_filter, SocialEventType)
                else event_type_filter
            )

        sentiment_str = None
        if sentiment_filter:
            sentiment_str = (
                sentiment_filter.value
                if isinstance(sentiment_filter, SocialSentiment)
                else sentiment_filter
            )

        # Use existing get_rolling_feed() with mapped week
        return self.get_rolling_feed(
            dynasty_id=dynasty_id,
            season=season,
            week=week,
            limit=limit,
            offset=offset,
            team_filter=team_filter,
            event_type_filter=event_type_str,
            sentiment_filter=sentiment_str
        )

    def get_posts_by_personality(
        self,
        personality_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> List[SocialPost]:
        """
        Get recent posts from a specific personality.

        Args:
            personality_id: Personality ID
            limit: Max posts to return
            offset: Pagination offset

        Returns:
            List of SocialPost objects ordered by created_at DESC
        """
        rows = self.db.query_all(
            """SELECT sp.id, sp.dynasty_id, sp.personality_id, sp.season, sp.week,
                      sp.post_text, sp.event_type, sp.sentiment, sp.likes, sp.retweets,
                      sp.event_metadata, sp.created_at,
                      pers.handle, pers.display_name, pers.personality_type, pers.team_id
               FROM social_posts sp
               INNER JOIN social_personalities pers ON sp.personality_id = pers.id
               WHERE sp.personality_id = ?
               ORDER BY sp.created_at DESC
               LIMIT ? OFFSET ?""",
            (personality_id, limit, offset)
        )
        return [self._row_to_post(row) for row in rows]

    def get_event_posts(
        self,
        dynasty_id: str,
        event_type: str,
        event_metadata_filter: Dict[str, Any]
    ) -> List[SocialPost]:
        """
        Get all posts about a specific event (e.g., game_id=123).

        Note: This does a JSON search which may be slow for large datasets.
        Use sparingly or add specific methods for common queries.

        Args:
            dynasty_id: Dynasty identifier
            event_type: Event type to filter
            event_metadata_filter: Key-value pairs to match in JSON (e.g., {"game_id": 123})

        Returns:
            List of SocialPost objects
        """
        # For now, get all posts of this event type and filter in Python
        # (SQLite JSON querying is limited without json1 extension)
        rows = self.db.query_all(
            """SELECT sp.id, sp.dynasty_id, sp.personality_id, sp.season, sp.week,
                      sp.post_text, sp.event_type, sp.sentiment, sp.likes, sp.retweets,
                      sp.event_metadata, sp.created_at,
                      pers.handle, pers.display_name, pers.personality_type, pers.team_id
               FROM social_posts sp
               INNER JOIN social_personalities pers ON sp.personality_id = pers.id
               WHERE sp.dynasty_id = ? AND sp.event_type = ?
               ORDER BY sp.created_at DESC""",
            (dynasty_id, event_type)
        )

        posts = [self._row_to_post(row) for row in rows]

        # Filter by metadata in Python
        if event_metadata_filter:
            filtered_posts = []
            for post in posts:
                if all(post.event_metadata.get(k) == v for k, v in event_metadata_filter.items()):
                    filtered_posts.append(post)
            return filtered_posts

        return posts

    def get_post_by_id(
        self,
        post_id: int
    ) -> Optional[SocialPost]:
        """
        Get a single post by ID.

        Args:
            post_id: Post ID

        Returns:
            SocialPost or None if not found
        """
        row = self.db.query_one(
            """SELECT sp.id, sp.dynasty_id, sp.personality_id, sp.season, sp.week,
                      sp.post_text, sp.event_type, sp.sentiment, sp.likes, sp.retweets,
                      sp.event_metadata, sp.created_at,
                      pers.handle, pers.display_name, pers.personality_type, pers.team_id
               FROM social_posts sp
               INNER JOIN social_personalities pers ON sp.personality_id = pers.id
               WHERE sp.id = ?""",
            (post_id,)
        )
        return self._row_to_post(row) if row else None

    # ==========================================
    # READ - AGGREGATES
    # ==========================================

    def count_posts(
        self,
        dynasty_id: str,
        season: Optional[int] = None,
        week: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> int:
        """
        Count total posts with optional filters.

        Args:
            dynasty_id: Dynasty identifier
            season: Optional season filter
            week: Optional week filter
            event_type: Optional event type filter

        Returns:
            Count of posts
        """
        where_clauses = ["dynasty_id = ?"]
        params: List[Any] = [dynasty_id]

        if season is not None:
            where_clauses.append("season = ?")
            params.append(season)

        if week is not None:
            where_clauses.append("week = ?")
            params.append(week)

        if event_type:
            where_clauses.append("event_type = ?")
            params.append(event_type)

        where_sql = " AND ".join(where_clauses)

        row = self.db.query_one(
            f"SELECT COUNT(*) as count FROM social_posts WHERE {where_sql}",
            tuple(params)
        )
        return row['count'] if row else 0

    def get_top_posts(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        limit: int = 10,
        sort_by: str = 'engagement'  # 'engagement', 'likes', 'retweets'
    ) -> List[SocialPost]:
        """
        Get top posts by engagement for a week.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            limit: Max posts to return
            sort_by: Sort criteria ('engagement', 'likes', 'retweets')

        Returns:
            List of SocialPost objects
        """
        if sort_by == 'engagement':
            order_by = "(sp.likes + sp.retweets * 3) DESC"  # Weight retweets higher
        elif sort_by == 'likes':
            order_by = "sp.likes DESC"
        elif sort_by == 'retweets':
            order_by = "sp.retweets DESC"
        else:
            raise ValueError(f"Invalid sort_by: {sort_by}")

        query = f"""
            SELECT sp.id, sp.dynasty_id, sp.personality_id, sp.season, sp.week,
                   sp.post_text, sp.event_type, sp.sentiment, sp.likes, sp.retweets,
                   sp.event_metadata, sp.created_at,
                   pers.handle, pers.display_name, pers.personality_type, pers.team_id
            FROM social_posts sp
            INNER JOIN social_personalities pers ON sp.personality_id = pers.id
            WHERE sp.dynasty_id = ? AND sp.season = ? AND sp.week = ?
            ORDER BY {order_by}
            LIMIT ?
        """

        rows = self.db.query_all(query, (dynasty_id, season, week, limit))
        return [self._row_to_post(row) for row in rows]

    # ==========================================
    # UPDATE
    # ==========================================

    def update_engagement(
        self,
        post_id: int,
        likes: int,
        retweets: int
    ) -> bool:
        """
        Update engagement counts for a post.

        Args:
            post_id: Post ID
            likes: New like count
            retweets: New retweet count

        Returns:
            True if updated, False if not found

        Raises:
            ValueError: If counts are negative
        """
        if likes < 0 or retweets < 0:
            raise ValueError("Engagement counts cannot be negative")

        cursor = self.db.execute(
            """UPDATE social_posts
               SET likes = ?, retweets = ?
               WHERE id = ?""",
            (likes, retweets, post_id)
        )
        return cursor.rowcount > 0

    # ==========================================
    # DELETE
    # ==========================================

    def delete_post(
        self,
        post_id: int
    ) -> bool:
        """
        Delete a single post.

        Args:
            post_id: Post ID

        Returns:
            True if deleted, False if not found
        """
        cursor = self.db.execute(
            """DELETE FROM social_posts WHERE id = ?""",
            (post_id,)
        )
        return cursor.rowcount > 0

    def delete_posts_by_week(
        self,
        dynasty_id: str,
        season: int,
        week: int
    ) -> int:
        """
        Delete all posts for a specific week.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number

        Returns:
            Number of posts deleted
        """
        cursor = self.db.execute(
            """DELETE FROM social_posts
               WHERE dynasty_id = ? AND season = ? AND week = ?""",
            (dynasty_id, season, week)
        )
        return cursor.rowcount

    def delete_all_posts(
        self,
        dynasty_id: str
    ) -> int:
        """
        Delete all posts in a dynasty.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Number of posts deleted
        """
        cursor = self.db.execute(
            """DELETE FROM social_posts WHERE dynasty_id = ?""",
            (dynasty_id,)
        )
        return cursor.rowcount

    # ==========================================
    # CONVERTERS
    # ==========================================

    def _row_to_post(self, row: Dict[str, Any]) -> SocialPost:
        """Convert database row to SocialPost dataclass."""
        # Convert sqlite3.Row to dict if needed
        if not isinstance(row, dict):
            row = dict(row)

        # Parse event_metadata JSON
        metadata = {}
        if row.get('event_metadata'):
            try:
                metadata = json.loads(row['event_metadata'])
            except (json.JSONDecodeError, TypeError):
                metadata = {}

        return SocialPost(
            id=row['id'],
            dynasty_id=row['dynasty_id'],
            personality_id=row['personality_id'],
            season=row['season'],
            week=row['week'],
            post_text=row['post_text'],
            event_type=row['event_type'],
            sentiment=row['sentiment'],
            likes=row['likes'],
            retweets=row['retweets'],
            event_metadata=metadata,
            created_at=row.get('created_at'),
            handle=row.get('handle'),
            display_name=row.get('display_name'),
            personality_type=row.get('personality_type'),
            team_id=row.get('team_id')
        )
