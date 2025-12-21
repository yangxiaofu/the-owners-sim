"""
Player Stats API for game_cycle.

Provides player statistics for both individual games and aggregated seasons.
Includes game stats retrieval for media coverage and player detail views.
"""

import sqlite3
from typing import Dict, Any, Optional, List


class PlayerSeasonStatsAPI:
    """
    API for retrieving aggregated player season statistics.

    Follows the same pattern as TeamSeasonStatsAPI, joining player_game_stats
    with games to filter by season.
    """

    def __init__(self, db_path: str):
        """
        Initialize the API.

        Args:
            db_path: Path to the game_cycle database
        """
        self._db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_team_player_stats(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        season_type: str = 'regular_season'
    ) -> Dict[int, Dict[str, Any]]:
        """
        Get aggregated season stats for all players on a team.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            season_type: 'regular_season' or 'playoffs'

        Returns:
            Dict mapping player_id (int) -> stats dict
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    CAST(pgs.player_id AS INTEGER) as player_id,
                    MAX(pgs.player_name) as player_name,
                    SUM(pgs.passing_yards) as passing_yards,
                    SUM(pgs.passing_tds) as passing_tds,
                    SUM(pgs.passing_attempts) as passing_attempts,
                    SUM(pgs.passing_completions) as passing_completions,
                    SUM(pgs.passing_interceptions) as passing_interceptions,
                    SUM(pgs.rushing_yards) as rushing_yards,
                    SUM(pgs.rushing_tds) as rushing_tds,
                    SUM(pgs.rushing_attempts) as rushing_attempts,
                    SUM(pgs.receptions) as receptions,
                    SUM(pgs.receiving_yards) as receiving_yards,
                    SUM(pgs.receiving_tds) as receiving_tds,
                    SUM(pgs.targets) as targets,
                    SUM(pgs.tackles_total) as tackles_total,
                    SUM(pgs.tackles_solo) as tackles_solo,
                    SUM(pgs.tackles_assist) as tackles_assist,
                    SUM(pgs.sacks) as sacks,
                    SUM(pgs.interceptions) as interceptions,
                    SUM(pgs.passes_defended) as passes_defended,
                    SUM(pgs.forced_fumbles) as forced_fumbles,
                    SUM(pgs.fumbles_recovered) as fumbles_recovered,
                    SUM(pgs.field_goals_made) as field_goals_made,
                    SUM(pgs.field_goals_attempted) as field_goals_attempted,
                    SUM(pgs.extra_points_made) as extra_points_made,
                    SUM(pgs.extra_points_attempted) as extra_points_attempted,
                    SUM(pgs.punts) as punts,
                    SUM(pgs.punt_yards) as punt_yards,
                    COUNT(DISTINCT pgs.game_id) as games_played
                FROM player_game_stats pgs
                JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
                WHERE pgs.dynasty_id = ? AND g.season = ? AND pgs.team_id = ?
                  AND pgs.season_type = ?
                GROUP BY pgs.player_id
                """,
                (dynasty_id, season, team_id, season_type)
            )

            results = {}
            for row in cursor.fetchall():
                player_id = row['player_id']
                results[player_id] = {
                    'player_id': player_id,
                    'player_name': row['player_name'] or f"Player {player_id}",
                    'passing_yards': row['passing_yards'] or 0,
                    'passing_tds': row['passing_tds'] or 0,
                    'passing_attempts': row['passing_attempts'] or 0,
                    'passing_completions': row['passing_completions'] or 0,
                    'passing_interceptions': row['passing_interceptions'] or 0,
                    'rushing_yards': row['rushing_yards'] or 0,
                    'rushing_tds': row['rushing_tds'] or 0,
                    'rushing_attempts': row['rushing_attempts'] or 0,
                    'receptions': row['receptions'] or 0,
                    'receiving_yards': row['receiving_yards'] or 0,
                    'receiving_tds': row['receiving_tds'] or 0,
                    'targets': row['targets'] or 0,
                    'tackles_total': row['tackles_total'] or 0,
                    'tackles_solo': row['tackles_solo'] or 0,
                    'tackles_assist': row['tackles_assist'] or 0,
                    'sacks': row['sacks'] or 0,
                    'interceptions': row['interceptions'] or 0,
                    'passes_defended': row['passes_defended'] or 0,
                    'forced_fumbles': row['forced_fumbles'] or 0,
                    'fumbles_recovered': row['fumbles_recovered'] or 0,
                    'field_goals_made': row['field_goals_made'] or 0,
                    'field_goals_attempted': row['field_goals_attempted'] or 0,
                    'extra_points_made': row['extra_points_made'] or 0,
                    'extra_points_attempted': row['extra_points_attempted'] or 0,
                    'punts': row['punts'] or 0,
                    'punt_yards': row['punt_yards'] or 0,
                    'games_played': row['games_played'] or 0,
                }
            return results
        finally:
            conn.close()

    def get_player_season_stats(
        self,
        dynasty_id: str,
        player_id: int,
        season: int,
        season_type: str = 'regular_season'
    ) -> Dict[str, Any]:
        """
        Get aggregated season stats for a single player.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID
            season: Season year
            season_type: 'regular_season' or 'playoffs'

        Returns:
            Stats dict or empty dict if no stats found
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    SUM(pgs.passing_yards) as passing_yards,
                    SUM(pgs.passing_tds) as passing_tds,
                    SUM(pgs.passing_attempts) as passing_attempts,
                    SUM(pgs.passing_completions) as passing_completions,
                    SUM(pgs.passing_interceptions) as passing_interceptions,
                    SUM(pgs.rushing_yards) as rushing_yards,
                    SUM(pgs.rushing_tds) as rushing_tds,
                    SUM(pgs.rushing_attempts) as rushing_attempts,
                    SUM(pgs.receptions) as receptions,
                    SUM(pgs.receiving_yards) as receiving_yards,
                    SUM(pgs.receiving_tds) as receiving_tds,
                    SUM(pgs.targets) as targets,
                    SUM(pgs.tackles_total) as tackles_total,
                    SUM(pgs.sacks) as sacks,
                    SUM(pgs.interceptions) as interceptions,
                    SUM(pgs.field_goals_made) as field_goals_made,
                    SUM(pgs.field_goals_attempted) as field_goals_attempted,
                    SUM(pgs.punts) as punts,
                    SUM(pgs.punt_yards) as punt_yards,
                    COUNT(DISTINCT pgs.game_id) as games_played
                FROM player_game_stats pgs
                JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
                WHERE pgs.dynasty_id = ? AND CAST(pgs.player_id AS INTEGER) = ?
                  AND g.season = ? AND pgs.season_type = ?
                """,
                (dynasty_id, player_id, season, season_type)
            )

            row = cursor.fetchone()
            if not row or row['games_played'] is None:
                return {}

            return {
                'player_id': player_id,
                'passing_yards': row['passing_yards'] or 0,
                'passing_tds': row['passing_tds'] or 0,
                'passing_attempts': row['passing_attempts'] or 0,
                'passing_completions': row['passing_completions'] or 0,
                'passing_interceptions': row['passing_interceptions'] or 0,
                'rushing_yards': row['rushing_yards'] or 0,
                'rushing_tds': row['rushing_tds'] or 0,
                'rushing_attempts': row['rushing_attempts'] or 0,
                'receptions': row['receptions'] or 0,
                'receiving_yards': row['receiving_yards'] or 0,
                'receiving_tds': row['receiving_tds'] or 0,
                'targets': row['targets'] or 0,
                'tackles_total': row['tackles_total'] or 0,
                'sacks': row['sacks'] or 0,
                'interceptions': row['interceptions'] or 0,
                'field_goals_made': row['field_goals_made'] or 0,
                'field_goals_attempted': row['field_goals_attempted'] or 0,
                'punts': row['punts'] or 0,
                'punt_yards': row['punt_yards'] or 0,
                'games_played': row['games_played'] or 0,
            }
        finally:
            conn.close()

    def get_player_game_stats(
        self,
        dynasty_id: str,
        game_id: str,
        player_id: int,
        season_type: str = 'regular_season'
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single player's stats for a specific game.

        This method is used by media coverage to display player stats
        in headlines and articles.

        Args:
            dynasty_id: Dynasty identifier
            game_id: Game identifier
            player_id: Player ID
            season_type: 'regular_season', 'playoffs', or 'preseason'

        Returns:
            Stats dict with all game stats, or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    player_name, position,
                    passing_yards, passing_tds, passing_interceptions,
                    passing_attempts, passing_completions, passing_rating,
                    rushing_yards, rushing_tds, rushing_attempts,
                    receptions, receiving_yards, receiving_tds, targets,
                    tackles_total, tackles_solo, tackles_assist,
                    sacks, interceptions, passes_defended,
                    field_goals_made, field_goals_attempted,
                    extra_points_made, extra_points_attempted,
                    punts, punt_yards
                FROM player_game_stats
                WHERE dynasty_id = ? AND game_id = ?
                  AND CAST(player_id AS INTEGER) = ? AND season_type = ?
                LIMIT 1
                """,
                (dynasty_id, game_id, player_id, season_type)
            )

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'player_id': player_id,
                'name': row['player_name'] or f"Player {player_id}",
                'position': row['position'] or "PLAYER",
                'stats': {
                    'passing_yards': row['passing_yards'] or 0,
                    'passing_tds': row['passing_tds'] or 0,
                    'passing_interceptions': row['passing_interceptions'] or 0,
                    'passing_attempts': row['passing_attempts'] or 0,
                    'passing_completions': row['passing_completions'] or 0,
                    'passer_rating': row['passing_rating'] or 0.0,
                    'rushing_yards': row['rushing_yards'] or 0,
                    'rushing_tds': row['rushing_tds'] or 0,
                    'rushing_attempts': row['rushing_attempts'] or 0,
                    'receptions': row['receptions'] or 0,
                    'receiving_yards': row['receiving_yards'] or 0,
                    'receiving_tds': row['receiving_tds'] or 0,
                    'targets': row['targets'] or 0,
                    'tackles_total': row['tackles_total'] or 0,
                    'tackles_solo': row['tackles_solo'] or 0,
                    'tackles_assist': row['tackles_assist'] or 0,
                    'sacks': row['sacks'] or 0,
                    'interceptions': row['interceptions'] or 0,
                    'passes_defended': row['passes_defended'] or 0,
                    'field_goals_made': row['field_goals_made'] or 0,
                    'field_goals_attempted': row['field_goals_attempted'] or 0,
                    'extra_points_made': row['extra_points_made'] or 0,
                    'extra_points_attempted': row['extra_points_attempted'] or 0,
                    'punts': row['punts'] or 0,
                    'punt_yards': row['punt_yards'] or 0,
                }
            }
        finally:
            conn.close()

    def get_game_top_performers(
        self,
        dynasty_id: str,
        game_id: str,
        limit: int = 5,
        season_type: str = 'regular_season'
    ) -> list[Dict[str, Any]]:
        """
        Get top performers from a game across both teams.

        Used for game recaps and highlight reels.

        Args:
            dynasty_id: Dynasty identifier
            game_id: Game identifier
            limit: Max number of performers to return
            season_type: Season type

        Returns:
            List of player stats dicts sorted by fantasy points desc
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    CAST(player_id AS INTEGER) as player_id,
                    player_name, position, team_id,
                    passing_yards, passing_tds, passing_interceptions,
                    rushing_yards, rushing_tds, rushing_attempts,
                    receptions, receiving_yards, receiving_tds, targets,
                    tackles_total, sacks, interceptions, passes_defended,
                    fantasy_points
                FROM player_game_stats
                WHERE dynasty_id = ? AND game_id = ? AND season_type = ?
                ORDER BY fantasy_points DESC, player_id ASC
                LIMIT ?
                """,
                (dynasty_id, game_id, season_type, limit)
            )

            results = []
            for row in cursor.fetchall():
                results.append({
                    'player_id': row['player_id'],
                    'name': row['player_name'] or f"Player {row['player_id']}",
                    'position': row['position'] or "PLAYER",
                    'team_id': row['team_id'],
                    'stats': {
                        'passing_yards': row['passing_yards'] or 0,
                        'passing_tds': row['passing_tds'] or 0,
                        'passing_interceptions': row['passing_interceptions'] or 0,
                        'rushing_yards': row['rushing_yards'] or 0,
                        'rushing_tds': row['rushing_tds'] or 0,
                        'rushing_attempts': row['rushing_attempts'] or 0,
                        'receptions': row['receptions'] or 0,
                        'receiving_yards': row['receiving_yards'] or 0,
                        'receiving_tds': row['receiving_tds'] or 0,
                        'targets': row['targets'] or 0,
                        'tackles_total': row['tackles_total'] or 0,
                        'sacks': row['sacks'] or 0,
                        'interceptions': row['interceptions'] or 0,
                        'passes_defended': row['passes_defended'] or 0,
                        'fantasy_points': row['fantasy_points'] or 0.0,
                    }
                })
            return results
        finally:
            conn.close()

    def get_weekly_top_performers(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        limit: int = 5,
        season_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top performers across all teams for a specific week.

        Aggregates stats for players who played in multiple games during the week
        (rare but possible with makeup games). Ranks by fantasy_points.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number (1-18 for regular, 19-22 for playoffs)
            limit: Max number of performers to return (default 5)
            season_type: Filter by 'regular_season' or 'playoffs'.
                        If None, returns all games regardless of type.

        Returns:
            List of player stats dicts sorted by fantasy points desc:
            [
                {
                    'player_id': int,
                    'player_name': str,
                    'position': str,
                    'team_id': int,
                    'passing_yards': int,
                    'passing_tds': int,
                    'passing_completions': int,
                    'passing_attempts': int,
                    'passing_interceptions': int,
                    'passing_rating': float,
                    'rushing_yards': int,
                    'rushing_tds': int,
                    'rushing_attempts': int,
                    'receiving_yards': int,
                    'receiving_tds': int,
                    'receptions': int,
                    'targets': int,
                    'tackles_total': int,
                    'sacks': float,
                    'interceptions': int,
                    'forced_fumbles': int,
                    'passes_defended': int,
                    'fantasy_points': float,
                },
                # ... up to limit players
            ]
        """
        conn = self._get_connection()
        try:
            # Build WHERE clause dynamically
            where_conditions = [
                "pgs.dynasty_id = ?",
                "g.season = ?",  # Filter by season to avoid cross-season data
                "g.week = ?"
            ]
            params = [dynasty_id, season, week]

            # Add season_type filter if specified
            if season_type is not None:
                where_conditions.append("pgs.season_type = ?")
                params.append(season_type)

            where_clause = " AND ".join(where_conditions)

            query = f"""
                SELECT
                    CAST(pgs.player_id AS INTEGER) as player_id,
                    pgs.player_name,
                    pgs.position,
                    CAST(pgs.team_id AS INTEGER) as team_id,
                    SUM(pgs.passing_yards) as passing_yards,
                    SUM(pgs.passing_tds) as passing_tds,
                    SUM(pgs.passing_completions) as passing_completions,
                    SUM(pgs.passing_attempts) as passing_attempts,
                    SUM(pgs.passing_interceptions) as passing_interceptions,
                    AVG(pgs.passing_rating) as passing_rating,
                    SUM(pgs.rushing_yards) as rushing_yards,
                    SUM(pgs.rushing_tds) as rushing_tds,
                    SUM(pgs.rushing_attempts) as rushing_attempts,
                    SUM(pgs.receiving_yards) as receiving_yards,
                    SUM(pgs.receiving_tds) as receiving_tds,
                    SUM(pgs.receptions) as receptions,
                    SUM(pgs.targets) as targets,
                    SUM(pgs.tackles_total) as tackles_total,
                    SUM(pgs.sacks) as sacks,
                    SUM(pgs.interceptions) as interceptions,
                    SUM(pgs.forced_fumbles) as forced_fumbles,
                    SUM(pgs.passes_defended) as passes_defended,
                    SUM(pgs.fantasy_points) as fantasy_points
                FROM player_game_stats pgs
                JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
                WHERE {where_clause}
                GROUP BY pgs.player_id
                ORDER BY fantasy_points DESC, player_id ASC
                LIMIT ?
            """

            params.append(limit)
            cursor = conn.execute(query, tuple(params))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'player_id': row['player_id'],
                    'name': row['player_name'] or f"Player {row['player_id']}",
                    'position': row['position'] or "PLAYER",
                    'team_id': row['team_id'],
                    'passing_yards': row['passing_yards'] or 0,
                    'passing_tds': row['passing_tds'] or 0,
                    'passing_completions': row['passing_completions'] or 0,
                    'passing_attempts': row['passing_attempts'] or 0,
                    'passing_interceptions': row['passing_interceptions'] or 0,
                    'passing_rating': row['passing_rating'] or 0.0,
                    'rushing_yards': row['rushing_yards'] or 0,
                    'rushing_tds': row['rushing_tds'] or 0,
                    'rushing_attempts': row['rushing_attempts'] or 0,
                    'receiving_yards': row['receiving_yards'] or 0,
                    'receiving_tds': row['receiving_tds'] or 0,
                    'receptions': row['receptions'] or 0,
                    'targets': row['targets'] or 0,
                    'tackles_total': row['tackles_total'] or 0,
                    'sacks': row['sacks'] or 0.0,
                    'interceptions': row['interceptions'] or 0,
                    'forced_fumbles': row['forced_fumbles'] or 0,
                    'passes_defended': row['passes_defended'] or 0,
                    'fantasy_points': row['fantasy_points'] or 0.0,
                })
            return results
        finally:
            conn.close()

    def get_season_top_performers(
        self,
        dynasty_id: str,
        season: int,
        limit: int = 5,
        include_playoffs: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get top performers across all teams for entire season.

        Aggregates all games in the season. Ranks by total fantasy_points.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            limit: Max number of performers to return (default 5)
            include_playoffs: If True, includes playoff stats in totals.
                             If False, only regular season stats.

        Returns:
            Same format as get_weekly_top_performers()
        """
        conn = self._get_connection()
        try:
            # Build WHERE clause dynamically
            where_conditions = [
                "pgs.dynasty_id = ?",
                "g.season = ?"
            ]
            params = [dynasty_id, season]

            # Filter by season type if needed
            if not include_playoffs:
                where_conditions.append("pgs.season_type = 'regular_season'")

            where_clause = " AND ".join(where_conditions)

            query = f"""
                SELECT
                    CAST(pgs.player_id AS INTEGER) as player_id,
                    pgs.player_name,
                    pgs.position,
                    CAST(pgs.team_id AS INTEGER) as team_id,
                    SUM(pgs.passing_yards) as passing_yards,
                    SUM(pgs.passing_tds) as passing_tds,
                    SUM(pgs.passing_completions) as passing_completions,
                    SUM(pgs.passing_attempts) as passing_attempts,
                    SUM(pgs.passing_interceptions) as passing_interceptions,
                    AVG(pgs.passing_rating) as passing_rating,
                    SUM(pgs.rushing_yards) as rushing_yards,
                    SUM(pgs.rushing_tds) as rushing_tds,
                    SUM(pgs.rushing_attempts) as rushing_attempts,
                    SUM(pgs.receiving_yards) as receiving_yards,
                    SUM(pgs.receiving_tds) as receiving_tds,
                    SUM(pgs.receptions) as receptions,
                    SUM(pgs.targets) as targets,
                    SUM(pgs.tackles_total) as tackles_total,
                    SUM(pgs.sacks) as sacks,
                    SUM(pgs.interceptions) as interceptions,
                    SUM(pgs.forced_fumbles) as forced_fumbles,
                    SUM(pgs.passes_defended) as passes_defended,
                    SUM(pgs.fantasy_points) as fantasy_points
                FROM player_game_stats pgs
                JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
                WHERE {where_clause}
                GROUP BY pgs.player_id
                ORDER BY fantasy_points DESC, player_id ASC
                LIMIT ?
            """

            params.append(limit)
            cursor = conn.execute(query, tuple(params))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'player_id': row['player_id'],
                    'name': row['player_name'] or f"Player {row['player_id']}",
                    'position': row['position'] or "PLAYER",
                    'team_id': row['team_id'],
                    'passing_yards': row['passing_yards'] or 0,
                    'passing_tds': row['passing_tds'] or 0,
                    'passing_completions': row['passing_completions'] or 0,
                    'passing_attempts': row['passing_attempts'] or 0,
                    'passing_interceptions': row['passing_interceptions'] or 0,
                    'passing_rating': row['passing_rating'] or 0.0,
                    'rushing_yards': row['rushing_yards'] or 0,
                    'rushing_tds': row['rushing_tds'] or 0,
                    'rushing_attempts': row['rushing_attempts'] or 0,
                    'receiving_yards': row['receiving_yards'] or 0,
                    'receiving_tds': row['receiving_tds'] or 0,
                    'receptions': row['receptions'] or 0,
                    'targets': row['targets'] or 0,
                    'tackles_total': row['tackles_total'] or 0,
                    'sacks': row['sacks'] or 0.0,
                    'interceptions': row['interceptions'] or 0,
                    'forced_fumbles': row['forced_fumbles'] or 0,
                    'passes_defended': row['passes_defended'] or 0,
                    'fantasy_points': row['fantasy_points'] or 0.0,
                })
            return results
        finally:
            conn.close()
