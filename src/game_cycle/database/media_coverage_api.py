"""
Media Coverage API for game_cycle.

Handles all media coverage database operations including:
- Power rankings (weekly team rankings)
- Headlines (event-driven news content)
- Narrative arcs (multi-week storylines)
- Press quotes (coach/player quotes)

Part of Milestone 12: Media Coverage.
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from .connection import GameCycleDatabase


# ============================================
# Headline Type Categories (for display timing)
# ============================================

# Headline types for post-game content (show from previous week)
RECAP_HEADLINE_TYPES = frozenset([
    'GAME_RECAP', 'BLOWOUT', 'UPSET', 'COMEBACK',
    'MILESTONE', 'POWER_RANKING', 'STREAK',
    'DUAL_THREAT', 'PLAYER_PERFORMANCE', 'DEFENSIVE_SHOWCASE'  # Player-focused headlines
])

# Headline types for upcoming games (show for current week)
PREVIEW_HEADLINE_TYPES = frozenset(['PREVIEW'])


# ============================================
# Data Classes
# ============================================

@dataclass
class PowerRanking:
    """Represents a team's power ranking for a specific week."""
    id: int
    dynasty_id: str
    season: int
    week: int
    team_id: int
    rank: int
    previous_rank: Optional[int]
    tier: str  # 'ELITE', 'CONTENDER', 'PLAYOFF', 'BUBBLE', 'REBUILDING'
    blurb: Optional[str]
    team_name: Optional[str] = None  # Full team name (e.g., "Los Angeles Rams")
    created_at: Optional[str] = None

    @property
    def movement(self) -> str:
        """Get movement indicator (▲, ▼, or —)."""
        if self.previous_rank is None:
            return "NEW"
        diff = self.previous_rank - self.rank
        if diff > 0:
            return f"▲{diff}"
        elif diff < 0:
            return f"▼{abs(diff)}"
        return "—"

    @property
    def movement_value(self) -> int:
        """Get numeric movement value (positive = up, negative = down)."""
        if self.previous_rank is None:
            return 0
        return self.previous_rank - self.rank


@dataclass
class Headline:
    """Represents a media headline/story."""
    id: int
    dynasty_id: str
    season: int
    week: int
    headline_type: str
    headline: str
    subheadline: Optional[str]
    body_text: Optional[str]
    sentiment: Optional[str]
    priority: int
    team_ids: List[int] = field(default_factory=list)
    player_ids: List[int] = field(default_factory=list)
    game_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None


@dataclass
class NarrativeArc:
    """Represents a multi-week storyline."""
    id: int
    dynasty_id: str
    season: int
    arc_type: str
    title: str
    description: Optional[str]
    status: str  # 'ACTIVE', 'RESOLVED', 'ABANDONED'
    start_week: int
    end_week: Optional[int]
    team_id: Optional[int]
    player_id: Optional[int]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None


@dataclass
class PressQuote:
    """Represents a press quote from coach/player/analyst."""
    id: int
    dynasty_id: str
    season: int
    week: int
    quote_type: str  # 'POSTGAME', 'PRESSER', 'REACTION', 'PREDICTION'
    speaker_type: str  # 'COACH', 'PLAYER', 'GM', 'ANALYST'
    speaker_id: Optional[int]
    team_id: Optional[int]
    quote_text: str
    context: Optional[str]
    sentiment: Optional[str]
    created_at: Optional[str] = None


# ============================================
# Media Coverage API
# ============================================

class MediaCoverageAPI:
    """
    API for media coverage operations in game_cycle.

    Handles:
    - Power rankings CRUD
    - Headlines CRUD
    - Narrative arcs CRUD
    - Press quotes CRUD

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
    # POWER RANKINGS
    # ==========================================

    def save_power_rankings(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        rankings: List[Dict[str, Any]]
    ) -> int:
        """
        Save power rankings for all 32 teams for a week.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            rankings: List of dicts with keys:
                - team_id: int
                - rank: int (1-32)
                - previous_rank: Optional[int]
                - tier: str ('ELITE', 'CONTENDER', 'PLAYOFF', 'BUBBLE', 'REBUILDING')
                - blurb: Optional[str]

        Returns:
            Number of rankings saved

        Raises:
            ValueError: If rankings are invalid
        """
        if not rankings:
            raise ValueError("Rankings list cannot be empty")

        count = 0
        for r in rankings:
            self.db.execute(
                """INSERT OR REPLACE INTO power_rankings
                   (dynasty_id, season, week, team_id, rank, previous_rank, tier, blurb)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    dynasty_id, season, week,
                    r['team_id'], r['rank'], r.get('previous_rank'),
                    r['tier'], r.get('blurb')
                )
            )
            count += 1
        return count

    def get_power_rankings(
        self,
        dynasty_id: str,
        season: int,
        week: int
    ) -> List[PowerRanking]:
        """
        Get power rankings for a specific week.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number

        Returns:
            List of PowerRanking sorted by rank
        """
        rows = self.db.query_all(
            """SELECT pr.id, pr.dynasty_id, pr.season, pr.week, pr.team_id, pr.rank,
                      pr.previous_rank, pr.tier, pr.blurb, pr.created_at,
                      t.name as team_name
               FROM power_rankings pr
               LEFT JOIN teams t ON pr.team_id = t.team_id
               WHERE pr.dynasty_id = ? AND pr.season = ? AND pr.week = ?
               ORDER BY pr.rank""",
            (dynasty_id, season, week)
        )
        return [self._row_to_power_ranking(row) for row in rows]

    def get_team_ranking_history(
        self,
        dynasty_id: str,
        season: int,
        team_id: int
    ) -> List[PowerRanking]:
        """
        Get a team's ranking history across all weeks of a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            team_id: Team ID (1-32)

        Returns:
            List of PowerRanking sorted by week
        """
        rows = self.db.query_all(
            """SELECT pr.id, pr.dynasty_id, pr.season, pr.week, pr.team_id, pr.rank,
                      pr.previous_rank, pr.tier, pr.blurb, pr.created_at,
                      t.name as team_name
               FROM power_rankings pr
               LEFT JOIN teams t ON pr.team_id = t.team_id
               WHERE pr.dynasty_id = ? AND pr.season = ? AND pr.team_id = ?
               ORDER BY pr.week""",
            (dynasty_id, season, team_id)
        )
        return [self._row_to_power_ranking(row) for row in rows]

    def get_latest_team_ranking(
        self,
        dynasty_id: str,
        season: int,
        team_id: int
    ) -> Optional[PowerRanking]:
        """
        Get a team's most recent ranking.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            team_id: Team ID (1-32)

        Returns:
            PowerRanking or None if not found
        """
        row = self.db.query_one(
            """SELECT pr.id, pr.dynasty_id, pr.season, pr.week, pr.team_id, pr.rank,
                      pr.previous_rank, pr.tier, pr.blurb, pr.created_at,
                      t.name as team_name
               FROM power_rankings pr
               LEFT JOIN teams t ON pr.team_id = t.team_id
               WHERE pr.dynasty_id = ? AND pr.season = ? AND pr.team_id = ?
               ORDER BY pr.week DESC
               LIMIT 1""",
            (dynasty_id, season, team_id)
        )
        return self._row_to_power_ranking(row) if row else None

    def _row_to_power_ranking(self, row: tuple) -> PowerRanking:
        """Convert database row to PowerRanking dataclass."""
        return PowerRanking(
            id=row[0],
            dynasty_id=row[1],
            season=row[2],
            week=row[3],
            team_id=row[4],
            rank=row[5],
            previous_rank=row[6],
            tier=row[7],
            blurb=row[8],
            created_at=row[9] if len(row) > 9 else None,
            team_name=row[10] if len(row) > 10 else None
        )

    # ==========================================
    # HEADLINES
    # ==========================================

    def save_headline(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        headline_data: Dict[str, Any]
    ) -> int:
        """
        Save a single headline.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            headline_data: Dict with keys:
                - headline_type: str (required)
                - headline: str (required)
                - subheadline: Optional[str]
                - body_text: Optional[str]
                - sentiment: Optional[str]
                - priority: int (default 50)
                - team_ids: List[int]
                - player_ids: List[int]
                - game_id: Optional[str]
                - metadata: Dict

        Returns:
            ID of saved headline

        Raises:
            ValueError: If required fields missing
        """
        if 'headline_type' not in headline_data or 'headline' not in headline_data:
            raise ValueError("headline_type and headline are required")

        team_ids_json = json.dumps(headline_data.get('team_ids', []))
        player_ids_json = json.dumps(headline_data.get('player_ids', []))
        metadata_json = json.dumps(headline_data.get('metadata', {}))

        cursor = self.db.execute(
            """INSERT INTO media_headlines
               (dynasty_id, season, week, headline_type, headline, subheadline,
                body_text, sentiment, priority, team_ids, player_ids, game_id, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id, season, week,
                headline_data['headline_type'],
                headline_data['headline'],
                headline_data.get('subheadline'),
                headline_data.get('body_text'),
                headline_data.get('sentiment'),
                headline_data.get('priority', 50),
                team_ids_json,
                player_ids_json,
                headline_data.get('game_id'),
                metadata_json
            )
        )
        return cursor.lastrowid

    def save_headlines_batch(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        headlines: List[Dict[str, Any]]
    ) -> int:
        """
        Save multiple headlines efficiently.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            headlines: List of headline_data dicts

        Returns:
            Number of headlines saved
        """
        count = 0
        for h in headlines:
            self.save_headline(dynasty_id, season, week, h)
            count += 1
        return count

    def get_headlines(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        headline_type: Optional[str] = None
    ) -> List[Headline]:
        """
        Get headlines for a specific week.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            headline_type: Optional filter by type

        Returns:
            List of Headline sorted by priority (descending)
        """
        if headline_type:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, season, week, headline_type, headline,
                          subheadline, body_text, sentiment, priority,
                          team_ids, player_ids, game_id, metadata, created_at
                   FROM media_headlines
                   WHERE dynasty_id = ? AND season = ? AND week = ? AND headline_type = ?
                   ORDER BY priority DESC, created_at DESC""",
                (dynasty_id, season, week, headline_type)
            )
        else:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, season, week, headline_type, headline,
                          subheadline, body_text, sentiment, priority,
                          team_ids, player_ids, game_id, metadata, created_at
                   FROM media_headlines
                   WHERE dynasty_id = ? AND season = ? AND week = ?
                   ORDER BY priority DESC, created_at DESC""",
                (dynasty_id, season, week)
            )
        return [self._row_to_headline(row) for row in rows]

    def get_top_headlines(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        limit: int = 10
    ) -> List[Headline]:
        """
        Get top headlines by priority.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            limit: Max number of headlines to return

        Returns:
            List of top Headline sorted by priority
        """
        rows = self.db.query_all(
            """SELECT id, dynasty_id, season, week, headline_type, headline,
                      subheadline, body_text, sentiment, priority,
                      team_ids, player_ids, game_id, metadata, created_at
               FROM media_headlines
               WHERE dynasty_id = ? AND season = ? AND week = ?
               ORDER BY priority DESC, created_at DESC
               LIMIT ?""",
            (dynasty_id, season, week, limit)
        )
        return [self._row_to_headline(row) for row in rows]

    def get_headlines_for_display(
        self,
        dynasty_id: str,
        season: int,
        current_week: int,
        limit: int = 20
    ) -> List[Headline]:
        """
        Get headlines for display combining:
        - RECAP-type headlines from previous week (completed games)
        - PREVIEW headlines for current week (upcoming games)

        This ensures proper timing: showing results of completed games
        alongside previews of upcoming matchups.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            current_week: Current week number (1-18)
            limit: Max headlines to return

        Returns:
            List of Headline sorted by priority DESC, created_at DESC
        """
        # Week 1: no completed games, show only Week 1 previews
        if current_week <= 1:
            return self.get_headlines(
                dynasty_id, season, week=1, headline_type='PREVIEW'
            )[:limit]

        recap_week = current_week - 1
        recap_types_str = ','.join(f"'{t}'" for t in RECAP_HEADLINE_TYPES)

        sql = f"""
            SELECT id, dynasty_id, season, week, headline_type, headline,
                   subheadline, body_text, sentiment, priority,
                   team_ids, player_ids, game_id, metadata, created_at
            FROM media_headlines
            WHERE dynasty_id = ? AND season = ?
              AND (
                  (week = ? AND headline_type IN ({recap_types_str}))
                  OR
                  (week = ? AND headline_type = 'PREVIEW')
              )
            ORDER BY priority DESC, created_at DESC
            LIMIT ?
        """

        rows = self.db.query_all(
            sql, (dynasty_id, season, recap_week, current_week, limit)
        )
        return [self._row_to_headline(row) for row in rows]

    def get_rolling_headlines(
        self,
        dynasty_id: str,
        season: int,
        limit: int = 50
    ) -> List[Headline]:
        """
        Get rolling headlines across all weeks for a season.

        Returns most recent headlines first, regardless of week number.
        Used for "News Feed" style display during offseason/playoffs where
        headlines from multiple stages should accumulate and persist.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            limit: Max headlines to return (default 50)

        Returns:
            List of Headline sorted by created_at DESC, priority DESC
        """
        rows = self.db.query_all(
            """SELECT id, dynasty_id, season, week, headline_type, headline,
                      subheadline, body_text, sentiment, priority,
                      team_ids, player_ids, game_id, metadata, created_at
               FROM media_headlines
               WHERE dynasty_id = ? AND season = ?
               ORDER BY created_at DESC, priority DESC
               LIMIT ?""",
            (dynasty_id, season, limit)
        )
        return [self._row_to_headline(row) for row in rows]

    def get_headlines_for_team(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        team_id: int,
        limit: int = 20
    ) -> List[Headline]:
        """
        Get headlines related to a specific team.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            team_id: Team ID to filter by
            limit: Max number of headlines

        Returns:
            List of Headline involving the team
        """
        # Use JSON contains for team_ids array
        rows = self.db.query_all(
            """SELECT id, dynasty_id, season, week, headline_type, headline,
                      subheadline, body_text, sentiment, priority,
                      team_ids, player_ids, game_id, metadata, created_at
               FROM media_headlines
               WHERE dynasty_id = ? AND season = ? AND week = ?
                     AND team_ids LIKE ?
               ORDER BY priority DESC, created_at DESC
               LIMIT ?""",
            (dynasty_id, season, week, f'%{team_id}%', limit)
        )
        return [self._row_to_headline(row) for row in rows]

    def get_headline_by_id(
        self,
        dynasty_id: str,
        headline_id: int
    ) -> Optional[Headline]:
        """
        Get a specific headline by ID.

        Args:
            dynasty_id: Dynasty identifier
            headline_id: Headline ID

        Returns:
            Headline or None if not found
        """
        row = self.db.query_one(
            """SELECT id, dynasty_id, season, week, headline_type, headline,
                      subheadline, body_text, sentiment, priority,
                      team_ids, player_ids, game_id, metadata, created_at
               FROM media_headlines
               WHERE dynasty_id = ? AND id = ?""",
            (dynasty_id, headline_id)
        )
        return self._row_to_headline(row) if row else None

    def _row_to_headline(self, row: tuple) -> Headline:
        """Convert database row to Headline dataclass."""
        return Headline(
            id=row[0],
            dynasty_id=row[1],
            season=row[2],
            week=row[3],
            headline_type=row[4],
            headline=row[5],
            subheadline=row[6],
            body_text=row[7],
            sentiment=row[8],
            priority=row[9],
            team_ids=json.loads(row[10]) if row[10] else [],
            player_ids=json.loads(row[11]) if row[11] else [],
            game_id=row[12],
            metadata=json.loads(row[13]) if row[13] else {},
            created_at=row[14] if len(row) > 14 else None
        )

    # ==========================================
    # NARRATIVE ARCS
    # ==========================================

    def save_narrative_arc(
        self,
        dynasty_id: str,
        arc_data: Dict[str, Any]
    ) -> int:
        """
        Save a narrative arc.

        Args:
            dynasty_id: Dynasty identifier
            arc_data: Dict with keys:
                - season: int (required)
                - arc_type: str (required)
                - title: str (required)
                - description: Optional[str]
                - status: str (default 'ACTIVE')
                - start_week: int (required)
                - end_week: Optional[int]
                - team_id: Optional[int]
                - player_id: Optional[int]
                - metadata: Dict

        Returns:
            ID of saved arc

        Raises:
            ValueError: If required fields missing
        """
        required = ['season', 'arc_type', 'title', 'start_week']
        for field in required:
            if field not in arc_data:
                raise ValueError(f"Required field missing: {field}")

        metadata_json = json.dumps(arc_data.get('metadata', {}))

        cursor = self.db.execute(
            """INSERT INTO narrative_arcs
               (dynasty_id, season, arc_type, title, description, status,
                start_week, end_week, team_id, player_id, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id,
                arc_data['season'],
                arc_data['arc_type'],
                arc_data['title'],
                arc_data.get('description'),
                arc_data.get('status', 'ACTIVE'),
                arc_data['start_week'],
                arc_data.get('end_week'),
                arc_data.get('team_id'),
                arc_data.get('player_id'),
                metadata_json
            )
        )
        return cursor.lastrowid

    def get_active_arcs(
        self,
        dynasty_id: str,
        season: int
    ) -> List[NarrativeArc]:
        """
        Get all active narrative arcs for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            List of active NarrativeArc
        """
        rows = self.db.query_all(
            """SELECT id, dynasty_id, season, arc_type, title, description,
                      status, start_week, end_week, team_id, player_id,
                      metadata, created_at
               FROM narrative_arcs
               WHERE dynasty_id = ? AND season = ? AND status = 'ACTIVE'
               ORDER BY start_week DESC""",
            (dynasty_id, season)
        )
        return [self._row_to_narrative_arc(row) for row in rows]

    def get_arcs_by_type(
        self,
        dynasty_id: str,
        season: int,
        arc_type: str
    ) -> List[NarrativeArc]:
        """
        Get narrative arcs by type.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            arc_type: Arc type to filter by

        Returns:
            List of NarrativeArc of specified type
        """
        rows = self.db.query_all(
            """SELECT id, dynasty_id, season, arc_type, title, description,
                      status, start_week, end_week, team_id, player_id,
                      metadata, created_at
               FROM narrative_arcs
               WHERE dynasty_id = ? AND season = ? AND arc_type = ?
               ORDER BY start_week DESC""",
            (dynasty_id, season, arc_type)
        )
        return [self._row_to_narrative_arc(row) for row in rows]

    def update_arc_status(
        self,
        dynasty_id: str,
        arc_id: int,
        status: str,
        end_week: Optional[int] = None
    ) -> bool:
        """
        Update a narrative arc's status.

        Args:
            dynasty_id: Dynasty identifier
            arc_id: Arc ID to update
            status: New status ('ACTIVE', 'RESOLVED', 'ABANDONED')
            end_week: Optional week when arc ended

        Returns:
            True if updated, False if not found
        """
        if end_week is not None:
            cursor = self.db.execute(
                """UPDATE narrative_arcs
                   SET status = ?, end_week = ?
                   WHERE dynasty_id = ? AND id = ?""",
                (status, end_week, dynasty_id, arc_id)
            )
        else:
            cursor = self.db.execute(
                """UPDATE narrative_arcs
                   SET status = ?
                   WHERE dynasty_id = ? AND id = ?""",
                (status, dynasty_id, arc_id)
            )
        return cursor.rowcount > 0

    def get_team_arcs(
        self,
        dynasty_id: str,
        season: int,
        team_id: int
    ) -> List[NarrativeArc]:
        """
        Get all narrative arcs involving a team.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            team_id: Team ID

        Returns:
            List of NarrativeArc for the team
        """
        rows = self.db.query_all(
            """SELECT id, dynasty_id, season, arc_type, title, description,
                      status, start_week, end_week, team_id, player_id,
                      metadata, created_at
               FROM narrative_arcs
               WHERE dynasty_id = ? AND season = ? AND team_id = ?
               ORDER BY start_week DESC""",
            (dynasty_id, season, team_id)
        )
        return [self._row_to_narrative_arc(row) for row in rows]

    def _row_to_narrative_arc(self, row: tuple) -> NarrativeArc:
        """Convert database row to NarrativeArc dataclass."""
        return NarrativeArc(
            id=row[0],
            dynasty_id=row[1],
            season=row[2],
            arc_type=row[3],
            title=row[4],
            description=row[5],
            status=row[6],
            start_week=row[7],
            end_week=row[8],
            team_id=row[9],
            player_id=row[10],
            metadata=json.loads(row[11]) if row[11] else {},
            created_at=row[12] if len(row) > 12 else None
        )

    # ==========================================
    # PRESS QUOTES
    # ==========================================

    def save_quote(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        quote_data: Dict[str, Any]
    ) -> int:
        """
        Save a press quote.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            quote_data: Dict with keys:
                - quote_type: str (required)
                - speaker_type: str (required)
                - quote_text: str (required)
                - speaker_id: Optional[int]
                - team_id: Optional[int]
                - context: Optional[str]
                - sentiment: Optional[str]

        Returns:
            ID of saved quote

        Raises:
            ValueError: If required fields missing
        """
        required = ['quote_type', 'speaker_type', 'quote_text']
        for field in required:
            if field not in quote_data:
                raise ValueError(f"Required field missing: {field}")

        cursor = self.db.execute(
            """INSERT INTO press_quotes
               (dynasty_id, season, week, quote_type, speaker_type,
                speaker_id, team_id, quote_text, context, sentiment)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id, season, week,
                quote_data['quote_type'],
                quote_data['speaker_type'],
                quote_data.get('speaker_id'),
                quote_data.get('team_id'),
                quote_data['quote_text'],
                quote_data.get('context'),
                quote_data.get('sentiment')
            )
        )
        return cursor.lastrowid

    def get_quotes(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        quote_type: Optional[str] = None
    ) -> List[PressQuote]:
        """
        Get quotes for a specific week.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            quote_type: Optional filter by type

        Returns:
            List of PressQuote
        """
        if quote_type:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, season, week, quote_type, speaker_type,
                          speaker_id, team_id, quote_text, context, sentiment, created_at
                   FROM press_quotes
                   WHERE dynasty_id = ? AND season = ? AND week = ? AND quote_type = ?
                   ORDER BY created_at DESC""",
                (dynasty_id, season, week, quote_type)
            )
        else:
            rows = self.db.query_all(
                """SELECT id, dynasty_id, season, week, quote_type, speaker_type,
                          speaker_id, team_id, quote_text, context, sentiment, created_at
                   FROM press_quotes
                   WHERE dynasty_id = ? AND season = ? AND week = ?
                   ORDER BY created_at DESC""",
                (dynasty_id, season, week)
            )
        return [self._row_to_quote(row) for row in rows]

    def get_team_quotes(
        self,
        dynasty_id: str,
        season: int,
        team_id: int,
        limit: int = 20
    ) -> List[PressQuote]:
        """
        Get quotes related to a specific team.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            team_id: Team ID
            limit: Max quotes to return

        Returns:
            List of PressQuote for the team
        """
        rows = self.db.query_all(
            """SELECT id, dynasty_id, season, week, quote_type, speaker_type,
                      speaker_id, team_id, quote_text, context, sentiment, created_at
               FROM press_quotes
               WHERE dynasty_id = ? AND season = ? AND team_id = ?
               ORDER BY week DESC, created_at DESC
               LIMIT ?""",
            (dynasty_id, season, team_id, limit)
        )
        return [self._row_to_quote(row) for row in rows]

    def _row_to_quote(self, row: tuple) -> PressQuote:
        """Convert database row to PressQuote dataclass."""
        return PressQuote(
            id=row[0],
            dynasty_id=row[1],
            season=row[2],
            week=row[3],
            quote_type=row[4],
            speaker_type=row[5],
            speaker_id=row[6],
            team_id=row[7],
            quote_text=row[8],
            context=row[9],
            sentiment=row[10],
            created_at=row[11] if len(row) > 11 else None
        )

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def delete_week_coverage(
        self,
        dynasty_id: str,
        season: int,
        week: int
    ) -> Dict[str, int]:
        """
        Delete all media coverage for a specific week.
        Useful for regenerating coverage.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number

        Returns:
            Dict with counts of deleted items by type
        """
        counts = {}

        cursor = self.db.execute(
            "DELETE FROM power_rankings WHERE dynasty_id = ? AND season = ? AND week = ?",
            (dynasty_id, season, week)
        )
        counts['power_rankings'] = cursor.rowcount

        cursor = self.db.execute(
            "DELETE FROM media_headlines WHERE dynasty_id = ? AND season = ? AND week = ?",
            (dynasty_id, season, week)
        )
        counts['headlines'] = cursor.rowcount

        cursor = self.db.execute(
            "DELETE FROM press_quotes WHERE dynasty_id = ? AND season = ? AND week = ?",
            (dynasty_id, season, week)
        )
        counts['quotes'] = cursor.rowcount

        return counts

    def get_coverage_summary(
        self,
        dynasty_id: str,
        season: int,
        week: int
    ) -> Dict[str, int]:
        """
        Get summary of coverage generated for a week.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number

        Returns:
            Dict with counts by content type
        """
        summary = {}

        row = self.db.query_one(
            "SELECT COUNT(*) FROM power_rankings WHERE dynasty_id = ? AND season = ? AND week = ?",
            (dynasty_id, season, week)
        )
        summary['power_rankings'] = row[0] if row else 0

        row = self.db.query_one(
            "SELECT COUNT(*) FROM media_headlines WHERE dynasty_id = ? AND season = ? AND week = ?",
            (dynasty_id, season, week)
        )
        summary['headlines'] = row[0] if row else 0

        row = self.db.query_one(
            "SELECT COUNT(*) FROM press_quotes WHERE dynasty_id = ? AND season = ? AND week = ?",
            (dynasty_id, season, week)
        )
        summary['quotes'] = row[0] if row else 0

        row = self.db.query_one(
            "SELECT COUNT(*) FROM narrative_arcs WHERE dynasty_id = ? AND season = ? AND status = 'ACTIVE'",
            (dynasty_id, season)
        )
        summary['active_arcs'] = row[0] if row else 0

        return summary
