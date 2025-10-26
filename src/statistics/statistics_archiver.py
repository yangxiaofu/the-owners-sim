"""
Statistics Archiver - Main Orchestrator for Statistics Preservation System

Coordinates season aggregation, retention policy enforcement, and historical
data management. This is the primary entry point for archival operations.

Key Features:
- Transaction-safe archival workflow
- Automatic validation at each stage
- Dependency injection for testability
- Detailed result reporting

Usage:
    archiver = StatisticsArchiver(
        database_path="data/database/nfl_simulation.db",
        dynasty_id="my_dynasty"
    )

    # Archive completed season (called during offseason transition)
    result = archiver.archive_season(completed_season=2025)

    if result.success:
        print(f"Archived {result.player_stats_aggregated} player season stats")
    else:
        print(f"Archival failed: {result.errors}")
"""

from typing import Optional, Dict, Any
import logging
import sqlite3
import time
from datetime import datetime

from statistics.models import ArchivalResult
from statistics.season_aggregator import SeasonAggregator
from statistics.retention_policy_manager import RetentionPolicyManager
from statistics.archival_validator import ArchivalValidator


class StatisticsArchiver:
    """
    Main orchestrator for statistics preservation and archival.

    Coordinates season aggregation, retention policy enforcement,
    and historical data management.

    Design Philosophy:
    - Transaction safety: All operations wrapped in database transactions
    - Validation first: Check pre-conditions before making changes
    - Clear error handling: Return structured results, never crash
    - Dependency injection: All components injectable for testing
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        aggregator: Optional[SeasonAggregator] = None,
        policy_manager: Optional[RetentionPolicyManager] = None,
        validator: Optional[ArchivalValidator] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize archiver with dependency injection for testability.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Dynasty identifier
            aggregator: Optional custom aggregator (for testing)
            policy_manager: Optional custom policy manager (for testing)
            validator: Optional custom validator (for testing)
            logger: Optional logger instance
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Dependency injection with defaults
        self.aggregator = aggregator or SeasonAggregator(database_path, dynasty_id)
        self.policy_manager = policy_manager or RetentionPolicyManager(database_path, dynasty_id)
        self.validator = validator or ArchivalValidator(database_path, dynasty_id)

    def archive_season(
        self,
        completed_season: int,
        season_type: str = "regular_season",
        super_bowl_champion: Optional[int] = None,
        afc_champion: Optional[int] = None,
        nfc_champion: Optional[int] = None,
        awards: Optional[Dict[str, str]] = None
    ) -> ArchivalResult:
        """
        Archive a completed season (called during PLAYOFFS → OFFSEASON transition).

        Process:
        1. Validate season is complete
        2. Aggregate game stats → season summaries
        3. Create season archive record
        4. Apply retention policy (Phase 3)
        5. Validate post-archival integrity

        Args:
            completed_season: Season year that just finished (e.g., 2025)
            season_type: "regular_season" or "playoffs"
            super_bowl_champion: Optional team ID of Super Bowl champion
            afc_champion: Optional team ID of AFC champion
            nfc_champion: Optional team ID of NFC champion
            awards: Optional dict of award winners

        Returns:
            ArchivalResult with status, metrics, and any errors

        Raises:
            Does not raise - returns failure result instead
        """
        start_time = time.time()
        errors = []
        warnings = []

        self.logger.info(
            f"[ARCHIVAL_START] Season {completed_season}, type '{season_type}', "
            f"dynasty '{self.dynasty_id}'"
        )

        conn = None

        try:
            # Get database connection for transaction
            conn = sqlite3.connect(self.database_path)
            conn.row_factory = sqlite3.Row
            conn.execute("BEGIN TRANSACTION")

            # ===== STAGE 1: Pre-Archival Validation =====
            self.logger.info("[STAGE_1] Pre-archival validation...")
            validation_result = self.validator.validate_pre_archival(
                season=completed_season,
                season_type=season_type
            )

            if not validation_result.passed:
                errors.extend(validation_result.errors)
                self.logger.error(
                    f"[STAGE_1_FAILED] Pre-archival validation failed: "
                    f"{validation_result.errors}"
                )
                conn.rollback()
                return self._create_failure_result(
                    season=completed_season,
                    errors=errors,
                    warnings=warnings,
                    duration=time.time() - start_time
                )

            if validation_result.warnings:
                warnings.extend(validation_result.warnings)
                self.logger.warning(
                    f"[STAGE_1_WARNINGS] {validation_result.warnings}"
                )

            # ===== STAGE 2: Aggregate Player Stats =====
            self.logger.info("[STAGE_2] Aggregating player season stats...")
            player_stats_list = self.aggregator.aggregate_player_season_stats(
                season=completed_season,
                season_type=season_type
            )

            self.logger.info(
                f"[STAGE_2_SUCCESS] Aggregated {len(player_stats_list)} player records"
            )

            # ===== STAGE 3: Validate Aggregation =====
            self.logger.info("[STAGE_3] Validating aggregation accuracy...")
            aggregation_validation = self.validator.validate_aggregation(
                season=completed_season,
                aggregated_stats=player_stats_list,
                season_type=season_type
            )

            if not aggregation_validation.passed:
                errors.extend(aggregation_validation.errors)
                self.logger.error(
                    f"[STAGE_3_FAILED] Aggregation validation failed: "
                    f"{aggregation_validation.errors}"
                )
                conn.rollback()
                return self._create_failure_result(
                    season=completed_season,
                    errors=errors,
                    warnings=warnings,
                    duration=time.time() - start_time
                )

            self.logger.info("[STAGE_3_SUCCESS] Aggregation validation passed")

            # ===== STAGE 4: Persist Season Stats =====
            self.logger.info("[STAGE_4] Persisting season stats to database...")
            self._persist_season_stats(conn, player_stats_list, season_type)
            self.logger.info(
                f"[STAGE_4_SUCCESS] Persisted {len(player_stats_list)} records"
            )

            # ===== STAGE 5: Create Season Archive =====
            if super_bowl_champion and afc_champion and nfc_champion:
                self.logger.info("[STAGE_5] Creating season archive record...")
                season_archive = self.aggregator.create_season_archive(
                    season=completed_season,
                    super_bowl_champion=super_bowl_champion,
                    afc_champion=afc_champion,
                    nfc_champion=nfc_champion,
                    awards=awards or {}
                )
                self._persist_season_archive(conn, season_archive)
                self.logger.info("[STAGE_5_SUCCESS] Season archive created")
            else:
                self.logger.info(
                    "[STAGE_5_SKIPPED] No champions provided, skipping season archive"
                )

            # ===== STAGE 6: Apply Retention Policy (Phase 3) =====
            self.logger.info("[STAGE_6] Applying retention policy...")

            # Get retention policy
            policy = self.policy_manager.get_retention_policy()

            # Initialize deletion counters
            games_deleted = 0
            player_stats_deleted = 0

            # Check if we should delete old game data
            if policy.auto_archive and policy.policy_type == "keep_n_seasons":
                # Get seasons that should be archived (game data deleted)
                seasons_to_archive = self.policy_manager.get_seasons_to_archive(
                    current_season=completed_season
                )

                if seasons_to_archive:
                    self.logger.info(
                        f"[STAGE_6] Deleting game data for {len(seasons_to_archive)} seasons: {seasons_to_archive}"
                    )
                    games_deleted, player_stats_deleted = self._delete_archived_game_data(
                        conn, seasons_to_archive, season_type
                    )
                    self.logger.info(
                        f"[STAGE_6_SUCCESS] Deleted {games_deleted} games, {player_stats_deleted} player_game_stats"
                    )
                else:
                    self.logger.info("[STAGE_6] No seasons ready for archival yet")
            elif policy.policy_type == "keep_all":
                self.logger.info("[STAGE_6] Policy is 'keep_all', no deletion")
            elif not policy.auto_archive:
                self.logger.info("[STAGE_6] Auto-archive disabled, no deletion")
            else:
                self.logger.info(f"[STAGE_6] Policy type '{policy.policy_type}', no deletion")

            # ===== STAGE 7: Post-Archival Validation =====
            self.logger.info("[STAGE_7] Post-archival validation...")
            post_validation = self.validator.validate_post_archival(
                season=completed_season,
                season_type=season_type,
                archived=(games_deleted > 0)  # True if we deleted game data
            )

            if not post_validation.passed:
                errors.extend(post_validation.errors)
                self.logger.error(
                    f"[STAGE_7_FAILED] Post-archival validation failed: "
                    f"{post_validation.errors}"
                )
                conn.rollback()
                return self._create_failure_result(
                    season=completed_season,
                    errors=errors,
                    warnings=warnings,
                    duration=time.time() - start_time
                )

            if post_validation.warnings:
                warnings.extend(post_validation.warnings)

            self.logger.info("[STAGE_7_SUCCESS] Post-archival validation passed")

            # ===== COMMIT TRANSACTION =====
            conn.commit()

            duration = time.time() - start_time

            self.logger.info(
                f"[ARCHIVAL_COMPLETE] ✅ Season {completed_season} archived successfully "
                f"in {duration:.2f}s"
            )

            return ArchivalResult(
                success=True,
                season=completed_season,
                player_stats_aggregated=len(player_stats_list),
                game_stats_archived=player_stats_deleted,
                games_archived=games_deleted,
                validation_passed=True,
                errors=[],
                warnings=warnings,
                duration_seconds=duration,
                archived_at=datetime.now()
            )

        except Exception as e:
            self.logger.error(
                f"[ARCHIVAL_FAILED] Unexpected error: {e}",
                exc_info=True
            )

            if conn:
                conn.rollback()

            return self._create_failure_result(
                season=completed_season,
                errors=[f"Unexpected error: {str(e)}"],
                warnings=warnings,
                duration=time.time() - start_time
            )

        finally:
            if conn:
                conn.close()

    def get_archival_status(self) -> Dict[str, Any]:
        """
        Get current archival status for this dynasty.

        Returns:
            {
                'active_seasons': int,  # Seasons in hot storage
                'archived_seasons': int,  # Seasons with summaries
                'total_seasons': int,
                'retention_policy': str,
                'retention_seasons': int,
                'database_size_mb': float,
                'season_summaries_count': int
            }
        """
        conn = None

        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()

            # Get season counts
            cursor.execute("""
                SELECT COUNT(DISTINCT season) as count
                FROM player_season_stats
                WHERE dynasty_id = ?
            """, (self.dynasty_id,))
            archived_seasons = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(DISTINCT season) as count
                FROM games
                WHERE dynasty_id = ?
            """, (self.dynasty_id,))
            active_seasons = cursor.fetchone()[0]

            # Get retention policy
            policy = self.policy_manager.get_retention_policy()

            # Get summary count
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM player_season_stats
                WHERE dynasty_id = ?
            """, (self.dynasty_id,))
            summaries_count = cursor.fetchone()[0]

            return {
                'active_seasons': active_seasons,
                'archived_seasons': archived_seasons,
                'total_seasons': max(active_seasons, archived_seasons),
                'retention_policy': policy.policy_type,
                'retention_seasons': policy.retention_seasons,
                'season_summaries_count': summaries_count
            }

        except Exception as e:
            self.logger.error(f"Error getting archival status: {e}", exc_info=True)
            return {}

        finally:
            if conn:
                conn.close()

    def _persist_season_stats(
        self,
        conn: sqlite3.Connection,
        player_stats_list,
        season_type: str
    ):
        """Persist player season stats to database."""
        cursor = conn.cursor()

        for player_stats in player_stats_list:
            # Use INSERT OR REPLACE for upsert behavior
            cursor.execute("""
                INSERT OR REPLACE INTO player_season_stats (
                    dynasty_id, player_id, season, season_type, team_id, position,
                    games_played, games_started,
                    passing_yards, passing_tds, passing_completions, passing_attempts, passing_interceptions,
                    rushing_yards, rushing_tds, rushing_attempts,
                    receiving_yards, receiving_tds, receptions, targets,
                    tackles_total, tackles_solo, tackles_assists, sacks, interceptions,
                    forced_fumbles, defensive_tds,
                    field_goals_made, field_goals_attempted, extra_points_made, extra_points_attempted,
                    passer_rating, yards_per_carry, catch_rate, yards_per_reception,
                    last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                player_stats.dynasty_id, player_stats.player_id, player_stats.season, season_type,
                player_stats.team_id, player_stats.position,
                player_stats.games_played, player_stats.games_started,
                player_stats.passing_yards, player_stats.passing_tds, player_stats.passing_completions,
                player_stats.passing_attempts, player_stats.interceptions,
                player_stats.rushing_yards, player_stats.rushing_tds, player_stats.rushing_attempts,
                player_stats.receiving_yards, player_stats.receiving_tds, player_stats.receptions,
                player_stats.targets,
                player_stats.tackles_total, player_stats.tackles_solo, player_stats.tackles_assist,
                player_stats.sacks, player_stats.interceptions_def, player_stats.forced_fumbles,
                player_stats.defensive_tds,
                player_stats.field_goals_made, player_stats.field_goals_attempted,
                player_stats.extra_points_made, player_stats.extra_points_attempted,
                player_stats.passer_rating, player_stats.yards_per_carry,
                player_stats.catch_rate, player_stats.yards_per_reception
            ))

    def _persist_season_archive(self, conn: sqlite3.Connection, season_archive):
        """Persist season archive record to database."""
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO season_archives (
                dynasty_id, season, super_bowl_champion, afc_champion, nfc_champion,
                mvp_player_id, offensive_poy, defensive_poy,
                offensive_rookie_of_year, defensive_rookie_of_year, comeback_player,
                best_record_team_id, best_record_wins, best_record_losses,
                games_played, archived_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            season_archive.dynasty_id, season_archive.season,
            season_archive.super_bowl_champion, season_archive.afc_champion,
            season_archive.nfc_champion, season_archive.mvp_player_id,
            season_archive.offensive_poy, season_archive.defensive_poy,
            season_archive.offensive_rookie_of_year, season_archive.defensive_rookie_of_year,
            season_archive.comeback_player, season_archive.best_record_team_id,
            season_archive.best_record_wins, season_archive.best_record_losses,
            season_archive.games_played
        ))

    def _delete_archived_game_data(
        self,
        conn: sqlite3.Connection,
        seasons_to_archive: list,
        season_type: str
    ) -> tuple:
        """
        Delete game data for archived seasons.

        This method permanently deletes game-level detail for seasons
        beyond the retention window. Season summaries are preserved.

        Args:
            conn: Database connection (transaction managed by caller)
            seasons_to_archive: List of season years to archive
            season_type: "regular_season" or "playoffs"

        Returns:
            Tuple of (games_deleted, player_stats_deleted)
        """
        cursor = conn.cursor()

        total_games_deleted = 0
        total_player_stats_deleted = 0

        for season in seasons_to_archive:
            # Count records before deletion (for logging)
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM games
                WHERE dynasty_id = ? AND season = ? AND season_type = ?
            """, (self.dynasty_id, season, season_type))
            games_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) as count
                FROM player_game_stats pgs
                JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
                WHERE pgs.dynasty_id = ? AND g.season = ? AND g.season_type = ?
            """, (self.dynasty_id, season, season_type))
            player_stats_count = cursor.fetchone()[0]

            # Delete player_game_stats first (foreign key dependency)
            cursor.execute("""
                DELETE FROM player_game_stats
                WHERE dynasty_id = ? AND game_id IN (
                    SELECT game_id FROM games
                    WHERE dynasty_id = ? AND season = ? AND season_type = ?
                )
            """, (self.dynasty_id, self.dynasty_id, season, season_type))
            player_stats_deleted = cursor.rowcount

            # Delete games
            cursor.execute("""
                DELETE FROM games
                WHERE dynasty_id = ? AND season = ? AND season_type = ?
            """, (self.dynasty_id, season, season_type))
            games_deleted = cursor.rowcount

            self.logger.info(
                f"  Season {season}: Deleted {games_deleted}/{games_count} games, "
                f"{player_stats_deleted}/{player_stats_count} player_game_stats"
            )

            total_games_deleted += games_deleted
            total_player_stats_deleted += player_stats_deleted

        return total_games_deleted, total_player_stats_deleted

    def _create_failure_result(
        self,
        season: int,
        errors: list,
        warnings: list,
        duration: float
    ) -> ArchivalResult:
        """Create failure result with error details."""
        return ArchivalResult(
            success=False,
            season=season,
            player_stats_aggregated=0,
            game_stats_archived=0,
            games_archived=0,
            validation_passed=False,
            errors=errors,
            warnings=warnings,
            duration_seconds=duration,
            archived_at=datetime.now()
        )
