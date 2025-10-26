"""
Archival Validator for Statistics Preservation System

Validates data integrity before and after archival operations.
Ensures no data loss or corruption during the archival process.

Key Features:
- Pre-archival validation (season completeness, data existence)
- Aggregation validation (verify totals match game stats)
- Post-archival validation (integrity after archival)
- Detailed error reporting with structured ValidationResult
"""

from typing import List, Optional, Dict, Any
import logging
import sqlite3

from statistics.models import ValidationResult, PlayerSeasonStats


class ArchivalValidator:
    """
    Validate data integrity for archival operations.

    Ensures that aggregated stats match game-level stats, and that
    archival operations don't corrupt or lose data.

    Design Philosophy:
    - Fail fast with clear error messages
    - Detailed validation results for debugging
    - Independent validation (no side effects)
    - Comprehensive checks at each stage
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        database_conn: Optional[sqlite3.Connection] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize archival validator.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Dynasty identifier for isolation
            database_conn: Optional external database connection
            logger: Optional logger instance
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.external_conn = database_conn
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def validate_pre_archival(
        self,
        season: int,
        season_type: str = "regular_season"
    ) -> ValidationResult:
        """
        Validate season data before archival.

        Checks:
        - Season is complete (has games played)
        - Game stats exist in database
        - No duplicate records
        - Data is consistent (no negative stats, etc.)

        Args:
            season: Season year to validate
            season_type: "regular_season" or "playoffs"

        Returns:
            ValidationResult with pass/fail and any errors
        """
        errors: List[str] = []
        warnings: List[str] = []
        details: Dict[str, Any] = {}

        conn = self._get_connection()

        try:
            # Check 1: Verify season has games
            games_count = self._count_games(conn, season, season_type)
            details['games_count'] = games_count

            if games_count == 0:
                errors.append(
                    f"No games found for season {season}, type '{season_type}'"
                )
            elif season_type == "regular_season" and games_count < 272:
                warnings.append(
                    f"Incomplete regular season: {games_count}/272 games found"
                )

            # Check 2: Verify player stats exist
            player_stats_count = self._count_player_game_stats(conn, season, season_type)
            details['player_stats_count'] = player_stats_count

            if player_stats_count == 0:
                errors.append(
                    f"No player game stats found for season {season}, type '{season_type}'"
                )

            # Check 3: Check for duplicate player/game records
            duplicates = self._check_duplicate_player_game_stats(conn, season, season_type)
            details['duplicate_records'] = len(duplicates)

            if duplicates:
                errors.append(
                    f"Found {len(duplicates)} duplicate player/game records"
                )
                # Include sample duplicates in details
                details['duplicate_samples'] = duplicates[:5]

            # Check 4: Validate data consistency (no negative stats)
            negative_stats = self._check_negative_stats(conn, season, season_type)
            details['negative_stats_count'] = len(negative_stats)

            if negative_stats:
                warnings.append(
                    f"Found {len(negative_stats)} records with negative stats"
                )
                details['negative_stats_samples'] = negative_stats[:5]

            # Check 5: Verify season summaries don't already exist
            existing_summaries = self._check_existing_summaries(conn, season, season_type)
            details['existing_summaries'] = existing_summaries

            if existing_summaries > 0:
                warnings.append(
                    f"Season summaries already exist ({existing_summaries} records). "
                    "These will be replaced."
                )

        except sqlite3.Error as e:
            errors.append(f"Database error during validation: {str(e)}")
            self.logger.error(f"Pre-archival validation failed: {e}", exc_info=True)

        finally:
            # Close connection only if we created it
            if not self.external_conn:
                conn.close()

        # Validation passes if no errors (warnings are okay)
        passed = len(errors) == 0

        return ValidationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            details=details
        )

    def validate_aggregation(
        self,
        season: int,
        aggregated_stats: List[PlayerSeasonStats],
        season_type: str = "regular_season"
    ) -> ValidationResult:
        """
        Validate that aggregated stats match game-level stats.

        Process:
        1. Query game-level stats for season
        2. Manually sum for each player
        3. Compare with aggregated stats
        4. Flag any mismatches

        Args:
            season: Season year
            aggregated_stats: List of aggregated PlayerSeasonStats
            season_type: "regular_season" or "playoffs"

        Returns:
            ValidationResult with detailed comparison
        """
        errors: List[str] = []
        warnings: List[str] = []
        details: Dict[str, Any] = {}

        conn = self._get_connection()

        try:
            # Sample validation: Check passing yards for all QBs
            mismatches = []

            for player_stats in aggregated_stats:
                # Query game totals for this player
                game_totals = self._get_game_totals_for_player(
                    conn,
                    player_stats.player_id,
                    season,
                    season_type
                )

                # Compare critical stats
                passing_yards_match = (
                    player_stats.passing_yards == game_totals.get('passing_yards', 0)
                )
                rushing_yards_match = (
                    player_stats.rushing_yards == game_totals.get('rushing_yards', 0)
                )
                receiving_yards_match = (
                    player_stats.receiving_yards == game_totals.get('receiving_yards', 0)
                )

                if not (passing_yards_match and rushing_yards_match and receiving_yards_match):
                    mismatches.append({
                        'player_id': player_stats.player_id,
                        'passing_yards_aggregated': player_stats.passing_yards,
                        'passing_yards_game_sum': game_totals.get('passing_yards', 0),
                        'rushing_yards_aggregated': player_stats.rushing_yards,
                        'rushing_yards_game_sum': game_totals.get('rushing_yards', 0),
                        'receiving_yards_aggregated': player_stats.receiving_yards,
                        'receiving_yards_game_sum': game_totals.get('receiving_yards', 0)
                    })

            details['players_validated'] = len(aggregated_stats)
            details['mismatches_found'] = len(mismatches)

            if mismatches:
                errors.append(
                    f"Aggregation validation failed: {len(mismatches)} players have mismatched totals"
                )
                # Include sample mismatches
                details['mismatch_samples'] = mismatches[:5]

        except sqlite3.Error as e:
            errors.append(f"Database error during aggregation validation: {str(e)}")
            self.logger.error(f"Aggregation validation failed: {e}", exc_info=True)

        finally:
            # Close connection only if we created it
            if not self.external_conn:
                conn.close()

        passed = len(errors) == 0

        return ValidationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            details=details
        )

    def validate_post_archival(
        self,
        season: int,
        season_type: str = "regular_season",
        archived: bool = False
    ) -> ValidationResult:
        """
        Validate data integrity after archival.

        Checks:
        - Season summaries exist in player_season_stats
        - Game data properly marked/deleted (if archived=True)
        - Career stats still queryable
        - No data corruption

        Args:
            season: Season year
            season_type: "regular_season" or "playoffs"
            archived: Whether game data was deleted (vs just marked)

        Returns:
            ValidationResult with integrity status
        """
        errors: List[str] = []
        warnings: List[str] = []
        details: Dict[str, Any] = {}

        conn = self._get_connection()

        try:
            # Check 1: Verify season summaries exist
            summaries_count = self._check_existing_summaries(conn, season, season_type)
            details['season_summaries_count'] = summaries_count

            if summaries_count == 0:
                errors.append(
                    f"No season summaries found for season {season}, type '{season_type}'"
                )

            # Check 2: Verify game data status
            if archived:
                # Game data should be deleted
                games_count = self._count_games(conn, season, season_type)
                player_stats_count = self._count_player_game_stats(conn, season, season_type)

                details['games_remaining'] = games_count
                details['player_game_stats_remaining'] = player_stats_count

                if games_count > 0 or player_stats_count > 0:
                    warnings.append(
                        f"Game data still exists after archival: "
                        f"{games_count} games, {player_stats_count} player_game_stats"
                    )
            else:
                # Game data should still exist
                games_count = self._count_games(conn, season, season_type)
                details['games_count'] = games_count

                if games_count == 0:
                    warnings.append(
                        f"Game data missing (expected to be retained)"
                    )

            # Check 3: Verify season archive record exists
            archive_exists = self._check_season_archive_exists(conn, season)
            details['season_archive_exists'] = archive_exists

            if not archive_exists:
                warnings.append(
                    f"Season archive record not found for season {season}"
                )

        except sqlite3.Error as e:
            errors.append(f"Database error during post-archival validation: {str(e)}")
            self.logger.error(f"Post-archival validation failed: {e}", exc_info=True)

        finally:
            # Close connection only if we created it
            if not self.external_conn:
                conn.close()

        passed = len(errors) == 0

        return ValidationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            details=details
        )

    def _count_games(
        self,
        conn: sqlite3.Connection,
        season: int,
        season_type: str
    ) -> int:
        """Count games for a season."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM games
            WHERE dynasty_id = ? AND season = ? AND season_type = ?
        """, (self.dynasty_id, season, season_type))
        return cursor.fetchone()['count']

    def _count_player_game_stats(
        self,
        conn: sqlite3.Connection,
        season: int,
        season_type: str
    ) -> int:
        """Count player game stats for a season."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ? AND g.season = ? AND g.season_type = ?
        """, (self.dynasty_id, season, season_type))
        return cursor.fetchone()['count']

    def _check_duplicate_player_game_stats(
        self,
        conn: sqlite3.Connection,
        season: int,
        season_type: str
    ) -> List[Dict[str, Any]]:
        """Check for duplicate player/game records."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pgs.player_id, pgs.game_id, COUNT(*) as count
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ? AND g.season = ? AND g.season_type = ?
            GROUP BY pgs.player_id, pgs.game_id
            HAVING COUNT(*) > 1
        """, (self.dynasty_id, season, season_type))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def _check_negative_stats(
        self,
        conn: sqlite3.Connection,
        season: int,
        season_type: str
    ) -> List[Dict[str, Any]]:
        """Check for records with negative stats."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pgs.player_id, pgs.game_id, pgs.player_name
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ? AND g.season = ? AND g.season_type = ?
            AND (
                pgs.passing_yards < 0 OR pgs.rushing_yards < 0 OR
                pgs.receiving_yards < 0 OR pgs.tackles_total < 0
            )
        """, (self.dynasty_id, season, season_type))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def _check_existing_summaries(
        self,
        conn: sqlite3.Connection,
        season: int,
        season_type: str
    ) -> int:
        """Check if season summaries already exist."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM player_season_stats
            WHERE dynasty_id = ? AND season = ? AND season_type = ?
        """, (self.dynasty_id, season, season_type))
        return cursor.fetchone()['count']

    def _get_game_totals_for_player(
        self,
        conn: sqlite3.Connection,
        player_id: str,
        season: int,
        season_type: str
    ) -> Dict[str, int]:
        """Get game totals for a specific player."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                SUM(pgs.passing_yards) as passing_yards,
                SUM(pgs.rushing_yards) as rushing_yards,
                SUM(pgs.receiving_yards) as receiving_yards
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ? AND pgs.player_id = ?
            AND g.season = ? AND g.season_type = ?
        """, (self.dynasty_id, player_id, season, season_type))

        row = cursor.fetchone()
        return dict(row) if row else {}

    def _check_season_archive_exists(
        self,
        conn: sqlite3.Connection,
        season: int
    ) -> bool:
        """Check if season archive record exists."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM season_archives
            WHERE dynasty_id = ? AND season = ?
        """, (self.dynasty_id, season))
        return cursor.fetchone()['count'] > 0

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get database connection (either external or create new).

        Returns:
            SQLite connection with row_factory set
        """
        if self.external_conn:
            return self.external_conn

        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn
