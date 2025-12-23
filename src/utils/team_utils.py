"""
Team Utilities.

Centralized team data access with built-in caching to reduce I/O overhead.
Provides consistent team name loading across all views.

Caching Strategy:
- Class-level cache for team names (dict[int, str])
- Dynasty-aware caching (invalidate on dynasty change)
- Automatic fallback: cache → database → JSON
"""

import json
import logging
import os
import sqlite3
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TeamCache:
    """
    In-memory cache for team data.

    Caches team names to avoid repeated database/file I/O.
    Automatically invalidates when dynasty changes.
    """

    _team_names_cache: Dict[int, str] = {}
    _dynasty_id_cache: Optional[str] = None

    @classmethod
    def get_team_names(
        cls,
        dynasty_id: Optional[str] = None,
        db_path: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[int, str]:
        """
        Get all team names as a dict mapping team_id -> name.

        Args:
            dynasty_id: Dynasty identifier (used for cache invalidation)
            db_path: Path to game_cycle database (optional)
            use_cache: Whether to use cached data (default True)

        Returns:
            Dict mapping team_id (int) to team name (str)

        Examples:
            >>> names = TeamCache.get_team_names()
            >>> names[1]
            'Buffalo Bills'
            >>> names[22]
            'Detroit Lions'
        """
        # Return cached data if same dynasty and cache is enabled
        if (
            use_cache
            and cls._team_names_cache
            and (dynasty_id is None or cls._dynasty_id_cache == dynasty_id)
        ):
            logger.debug(f"Using cached team names ({len(cls._team_names_cache)} teams)")
            return cls._team_names_cache.copy()

        # Load fresh data
        logger.debug("Loading team names (cache miss or disabled)")

        # Try database first (if db_path provided)
        if db_path:
            team_names = cls._load_from_database(db_path)
            if team_names:
                cls._team_names_cache = team_names
                cls._dynasty_id_cache = dynasty_id
                logger.debug(f"Loaded {len(team_names)} team names from database")
                return team_names.copy()

        # Fallback to JSON
        team_names = cls._load_from_json()
        if team_names:
            cls._team_names_cache = team_names
            cls._dynasty_id_cache = dynasty_id
            logger.debug(f"Loaded {len(team_names)} team names from JSON")
            return team_names.copy()

        # Last resort: empty dict
        logger.warning("No team names loaded (database and JSON both failed)")
        return {}

    @classmethod
    def get_team_name(
        cls,
        team_id: int,
        dynasty_id: Optional[str] = None,
        db_path: Optional[str] = None,
        use_cache: bool = True
    ) -> str:
        """
        Get a single team name by ID.

        Args:
            team_id: Team ID (1-32)
            dynasty_id: Dynasty identifier (optional, for caching)
            db_path: Path to game_cycle database (optional)
            use_cache: Whether to use cached data (default True)

        Returns:
            Team name string, or f"Team {team_id}" if not found

        Examples:
            >>> TeamCache.get_team_name(1)
            'Buffalo Bills'
            >>> TeamCache.get_team_name(999)
            'Team 999'
        """
        team_names = cls.get_team_names(dynasty_id, db_path, use_cache)
        return team_names.get(team_id, f"Team {team_id}")

    @classmethod
    def invalidate(cls):
        """
        Clear the cache.

        Call this when dynasty changes or team data is updated.
        """
        cls._team_names_cache.clear()
        cls._dynasty_id_cache = None
        logger.debug("Team name cache invalidated")

    @classmethod
    def _load_from_database(cls, db_path: str) -> Dict[int, str]:
        """
        Load team names from game_cycle database.

        Args:
            db_path: Path to database file

        Returns:
            Dict mapping team_id -> name, or empty dict on error
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT team_id, name FROM teams")
            team_names = {row[0]: row[1] for row in cursor.fetchall()}

            conn.close()
            return team_names if team_names else {}

        except Exception as e:
            logger.warning(f"Failed to load team names from database: {e}")
            return {}

    @classmethod
    def _load_from_json(cls) -> Dict[int, str]:
        """
        Load team names from JSON file as fallback.

        Returns:
            Dict mapping team_id -> name, or empty dict on error
        """
        try:
            # Find teams.json relative to this file
            # Path: src/utils/team_utils.py -> src/data/teams.json
            current_dir = os.path.dirname(__file__)
            json_path = os.path.join(current_dir, "..", "data", "teams.json")
            json_path = os.path.normpath(json_path)

            if not os.path.exists(json_path):
                logger.warning(f"teams.json not found at {json_path}")
                return {}

            with open(json_path, 'r') as f:
                data = json.load(f)

            teams_data = data.get('teams', {})
            team_names = {
                int(team_id): team_info.get('full_name', f"Team {team_id}")
                for team_id, team_info in teams_data.items()
            }

            return team_names

        except Exception as e:
            logger.warning(f"Failed to load team names from JSON: {e}")
            return {}


# ============================================
# Convenience Functions
# ============================================

def get_all_team_names(
    dynasty_id: Optional[str] = None,
    db_path: Optional[str] = None,
    use_cache: bool = True
) -> Dict[int, str]:
    """
    Get all team names.

    Convenience wrapper around TeamCache.get_team_names().

    Args:
        dynasty_id: Dynasty identifier (optional, for caching)
        db_path: Path to game_cycle database (optional)
        use_cache: Whether to use cached data (default True)

    Returns:
        Dict mapping team_id (int) to team name (str)
    """
    return TeamCache.get_team_names(dynasty_id, db_path, use_cache)


def get_team_name(
    team_id: int,
    dynasty_id: Optional[str] = None,
    db_path: Optional[str] = None,
    use_cache: bool = True
) -> str:
    """
    Get a single team name by ID.

    Convenience wrapper around TeamCache.get_team_name().

    Args:
        team_id: Team ID (1-32)
        dynasty_id: Dynasty identifier (optional, for caching)
        db_path: Path to game_cycle database (optional)
        use_cache: Whether to use cached data (default True)

    Returns:
        Team name string, or f"Team {team_id}" if not found
    """
    return TeamCache.get_team_name(team_id, dynasty_id, db_path, use_cache)


def invalidate_team_cache():
    """
    Invalidate the team name cache.

    Call this when dynasty changes or team data is updated.
    """
    TeamCache.invalidate()
