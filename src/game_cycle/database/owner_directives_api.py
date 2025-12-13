"""
Owner Directives API - Database operations for owner strategic guidance.

Part of Milestone 13: Owner Review.
Handles CRUD operations for owner directives with dynasty isolation.
"""

import json
from typing import Optional, Dict, Any, List

from .connection import GameCycleDatabase
from ..models.owner_directives import OwnerDirectives


class OwnerDirectivesAPI:
    """
    API for owner directives database operations.

    Handles:
    - Saving/loading owner directives
    - Managing win targets, position priorities, wishlists
    - JSON serialization for list fields
    - Follows dynasty isolation pattern

    All operations require dynasty_id for data isolation.
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db

    def get_directives(
        self,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> Optional[OwnerDirectives]:
        """
        Get owner directives for a team/season.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            season: Season year

        Returns:
            OwnerDirectives if found, None otherwise
        """
        row = self.db.query_one(
            """SELECT * FROM owner_directives
               WHERE dynasty_id = ? AND team_id = ? AND season = ?""",
            (dynasty_id, team_id, season)
        )
        if not row:
            return None
        return self._row_to_directives(row)

    def save_directives(self, directives: OwnerDirectives) -> bool:
        """
        Save or update owner directives.

        Uses INSERT OR REPLACE for upsert behavior.

        Args:
            directives: OwnerDirectives to save

        Returns:
            True if successful
        """
        self.db.execute(
            """INSERT OR REPLACE INTO owner_directives
               (dynasty_id, team_id, season, target_wins, priority_positions,
                fa_wishlist, draft_wishlist, draft_strategy, fa_philosophy,
                max_contract_years, max_guaranteed_percent,
                team_philosophy, budget_stance, protected_player_ids,
                expendable_player_ids, owner_notes, trust_gm, modified_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (
                directives.dynasty_id,
                directives.team_id,
                directives.season,
                directives.target_wins,
                json.dumps(directives.priority_positions) if directives.priority_positions else None,
                json.dumps(directives.fa_wishlist) if directives.fa_wishlist else None,
                json.dumps(directives.draft_wishlist) if directives.draft_wishlist else None,
                directives.draft_strategy,
                directives.fa_philosophy,
                directives.max_contract_years,
                directives.max_guaranteed_percent,
                directives.team_philosophy,
                directives.budget_stance,
                json.dumps(directives.protected_player_ids) if directives.protected_player_ids else '[]',
                json.dumps(directives.expendable_player_ids) if directives.expendable_player_ids else '[]',
                directives.owner_notes,
                1 if directives.trust_gm else 0,
            )
        )
        return True

    def save_directives_dict(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        directives: Dict[str, Any]
    ) -> bool:
        """
        Save owner directives from a dictionary.

        Convenience method for backwards compatibility.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            directives: Dict with directive fields

        Returns:
            True if successful
        """
        owner_directives = OwnerDirectives(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            target_wins=directives.get("target_wins"),
            priority_positions=directives.get("priority_positions", []),
            fa_wishlist=directives.get("fa_wishlist", []),
            draft_wishlist=directives.get("draft_wishlist", []),
            draft_strategy=directives.get("draft_strategy", "balanced"),
            fa_philosophy=directives.get("fa_philosophy", "balanced"),
            max_contract_years=directives.get("max_contract_years", 5),
            max_guaranteed_percent=directives.get("max_guaranteed_percent", 0.75),
            team_philosophy=directives.get("team_philosophy", "maintain"),
            budget_stance=directives.get("budget_stance", "moderate"),
            protected_player_ids=directives.get("protected_player_ids", []),
            expendable_player_ids=directives.get("expendable_player_ids", []),
            owner_notes=directives.get("owner_notes", ""),
            trust_gm=directives.get("trust_gm", False),
        )
        return self.save_directives(owner_directives)

    def clear_directives(
        self,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> int:
        """
        Delete directives for a team/season.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year

        Returns:
            Number of rows deleted (0 or 1)
        """
        cursor = self.db.execute(
            """DELETE FROM owner_directives
               WHERE dynasty_id = ? AND team_id = ? AND season = ?""",
            (dynasty_id, team_id, season)
        )
        return cursor.rowcount

    def get_all_directives_for_season(
        self,
        dynasty_id: str,
        season: int
    ) -> Dict[int, OwnerDirectives]:
        """
        Get directives for all teams in a season.

        Useful for AI GM behavior during offseason processing.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dict mapping team_id to OwnerDirectives
        """
        rows = self.db.query_all(
            """SELECT * FROM owner_directives
               WHERE dynasty_id = ? AND season = ?""",
            (dynasty_id, season)
        )

        result = {}
        for row in rows:
            directives = self._row_to_directives(row)
            result[directives.team_id] = directives

        return result

    def _row_to_directives(self, row) -> OwnerDirectives:
        """Convert database row to OwnerDirectives."""
        # Helper to safely get column value (sqlite3.Row doesn't have .get())
        def get_col(name, default=None):
            try:
                return row[name] if row[name] is not None else default
            except (KeyError, IndexError):
                return default

        # Parse protected/expendable player IDs (JSON arrays)
        protected_ids = []
        protected_json = get_col('protected_player_ids')
        if protected_json:
            try:
                protected_ids = json.loads(protected_json)
            except (json.JSONDecodeError, TypeError):
                protected_ids = []

        expendable_ids = []
        expendable_json = get_col('expendable_player_ids')
        if expendable_json:
            try:
                expendable_ids = json.loads(expendable_json)
            except (json.JSONDecodeError, TypeError):
                expendable_ids = []

        return OwnerDirectives(
            dynasty_id=row['dynasty_id'],
            team_id=row['team_id'],
            season=row['season'],
            target_wins=row['target_wins'],
            priority_positions=json.loads(row['priority_positions']) if row['priority_positions'] else [],
            fa_wishlist=json.loads(row['fa_wishlist']) if row['fa_wishlist'] else [],
            draft_wishlist=json.loads(row['draft_wishlist']) if row['draft_wishlist'] else [],
            draft_strategy=row['draft_strategy'] or 'balanced',
            fa_philosophy=row['fa_philosophy'] or 'balanced',
            max_contract_years=row['max_contract_years'] or 5,
            max_guaranteed_percent=row['max_guaranteed_percent'] or 0.75,
            team_philosophy=get_col('team_philosophy', 'maintain'),
            budget_stance=get_col('budget_stance', 'moderate'),
            protected_player_ids=protected_ids,
            expendable_player_ids=expendable_ids,
            owner_notes=get_col('owner_notes', ''),
            trust_gm=bool(get_col('trust_gm', 0)),
        )
