"""
Game Slots API - Database operations for game slot management.

Provides methods for querying games for primetime assignment and
retrieving slot assignments. Follows the service layer pattern
where database operations are isolated in API classes.
"""

import json
from typing import Dict, List, Optional

from .connection import GameCycleDatabase


class GameSlotsAPI:
    """Database operations for game slot management."""

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize the API.

        Args:
            db: GameCycleDatabase instance
        """
        self._db = db

    def get_games_for_primetime_assignment(
        self, dynasty_id: str, season: int
    ) -> List[Dict]:
        """
        Get games in nested format for PrimetimeScheduler.

        Tries events table first (new NFLScheduleGenerator format with game_id like
        'regular_2025_1_1'), then falls back to games table (legacy format with
        game_id like 'game_20250904_5_at_9').

        The PrimetimeScheduler expects games in the format:
        {"game_id": ..., "data": {"parameters": {"week": ..., "home_team_id": ..., "away_team_id": ...}}}

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            List of games in nested event format
        """
        # Try events table first (NFLScheduleGenerator creates events with regular_YEAR_WEEK_NUM format)
        rows = self._db.query_all(
            """SELECT game_id, data
               FROM events
               WHERE dynasty_id = ?
                 AND event_type = 'GAME'
                 AND game_id LIKE ?""",
            (dynasty_id, f"regular_{season}_%")
        )

        if rows:
            result = []
            for row in rows:
                data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
                params = data.get("parameters", {})

                # Only include regular season games for the specified season
                if params.get("season") == season and params.get("season_type") == "regular_season":
                    result.append({
                        "game_id": row["game_id"],
                        "data": data  # Already in nested format with parameters
                    })
            return result

        # Fallback: Query games table (legacy format with game_YYYYMMDD_away_at_home)
        # This handles dynasties created before NFLScheduleGenerator was integrated
        rows = self._db.query_all(
            """SELECT game_id, week, home_team_id, away_team_id
               FROM games
               WHERE dynasty_id = ? AND season = ? AND season_type = 'regular_season'""",
            (dynasty_id, season)
        )

        return [
            {
                "game_id": row["game_id"],
                "data": {
                    "parameters": {
                        "week": row["week"],
                        "home_team_id": row["home_team_id"],
                        "away_team_id": row["away_team_id"]
                    },
                    "metadata": {
                        "is_divisional": False,  # Not available from games table
                        "is_conference": False
                    }
                }
            }
            for row in rows
        ]

    def get_slot_for_game(
        self, dynasty_id: str, game_id: str
    ) -> Optional[str]:
        """
        Get the slot assignment for a specific game.

        Args:
            dynasty_id: Dynasty identifier
            game_id: Game identifier

        Returns:
            Slot name (e.g., 'TNF', 'SNF', 'MNF') or None if not assigned
        """
        row = self._db.query_one(
            """SELECT slot FROM game_slots
               WHERE dynasty_id = ? AND game_id = ?""",
            (dynasty_id, game_id)
        )
        return row["slot"] if row else None

    def get_all_slots_for_season(
        self, dynasty_id: str, season: int
    ) -> Dict[str, str]:
        """
        Get all game_id -> slot mappings for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dictionary mapping game_id to slot name
        """
        rows = self._db.query_all(
            """SELECT game_id, slot FROM game_slots
               WHERE dynasty_id = ? AND season = ?""",
            (dynasty_id, season)
        )
        return {row["game_id"]: row["slot"] for row in rows}