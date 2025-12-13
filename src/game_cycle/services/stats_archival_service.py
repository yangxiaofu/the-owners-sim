"""
Stats Archival Service for game_cycle.

Handles season-end statistics archival including:
- Immediate deletion of play-by-play grades (biggest space saver)
- CSV export of game-level data before deletion
- 2-season retention window management

This is the game_cycle equivalent of statistics_archiver.py,
designed to work with the stage-based season flow.
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.services.csv_export_service import CSVExportService, SeasonExportResult

logger = logging.getLogger(__name__)


@dataclass
class ArchivalResult:
    """Result of an archival operation."""
    success: bool
    dynasty_id: str
    season: int
    operation: str  # 'delete_play_grades', 'archive_game_data', 'full_archival'
    rows_deleted: int = 0
    rows_exported: int = 0
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SeasonArchivalSummary:
    """Summary of all archival operations for a season transition."""
    dynasty_id: str
    completed_season: int
    current_season: int
    play_grades_deleted: int = 0
    seasons_archived: List[int] = field(default_factory=list)
    export_results: List[SeasonExportResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    success: bool = True


class StatsArchivalService:
    """
    Service for managing statistics archival during season rollover.

    Archival Pipeline (called at start of new season):
    1. DELETE player_play_grades for completed season (immediate, no CSV)
    2. Check retention window (2 seasons)
    3. For seasons beyond retention:
       a. Export to CSV
       b. Validate export
       c. Delete from database

    Usage:
        service = StatsArchivalService(db_path, dynasty_id)

        # During season rollover (playoffs complete → training camp)
        summary = service.archive_completed_season(
            completed_season=2025,
            current_season=2026
        )
    """

    DEFAULT_RETENTION_SEASONS = 2  # Keep current + 1 prior season

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        retention_seasons: int = DEFAULT_RETENTION_SEASONS,
        archives_root: Optional[str] = None
    ):
        """
        Initialize the archival service.

        Args:
            db_path: Path to game_cycle database
            dynasty_id: Dynasty identifier
            retention_seasons: Number of seasons to keep in database (default: 2)
            archives_root: Root directory for CSV archives (default: data/archives)
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.retention_seasons = retention_seasons
        self.archives_root = archives_root
        # Lazy initialization - don't create GameCycleDatabase here
        # as it applies schema which may conflict with test databases
        self._csv_export_service = None

    @property
    def csv_export_service(self) -> CSVExportService:
        """Lazy initialization of CSV export service."""
        if self._csv_export_service is None:
            self._csv_export_service = CSVExportService(self.db_path, self.archives_root)
        return self._csv_export_service

    # ========================================================================
    # TOLLGATE 3: Immediate Play Grades Deletion
    # ========================================================================

    def delete_play_grades_for_season(self, season: int) -> ArchivalResult:
        """
        Immediately delete all play-by-play grades for a completed season.

        This is the biggest space saver (~48 MB per season, 800K+ rows).
        Called right after playoffs complete, before any other archival.

        The player_play_grades table stores granular per-play grades that are
        only needed for in-season analysis. Once the season ends, we only need
        the aggregated game-level and season-level grades.

        Args:
            season: Season year to delete play grades for

        Returns:
            ArchivalResult with deletion count
        """
        logger.info(
            f"[PLAY_GRADES_DELETE] Starting deletion for dynasty={self.dynasty_id}, "
            f"season={season}"
        )

        try:
            conn = sqlite3.connect(self.db_path)

            # Check if table exists first
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='player_play_grades'"
            )
            if not cursor.fetchone():
                logger.info("[PLAY_GRADES_DELETE] Table player_play_grades does not exist, skipping")
                conn.close()
                return ArchivalResult(
                    success=True,
                    dynasty_id=self.dynasty_id,
                    season=season,
                    operation='delete_play_grades',
                    rows_deleted=0
                )

            # Count rows before deletion
            cursor = conn.execute("""
                SELECT COUNT(*) FROM player_play_grades ppg
                JOIN games g ON ppg.game_id = g.game_id AND ppg.dynasty_id = g.dynasty_id
                WHERE ppg.dynasty_id = ? AND g.season = ?
            """, (self.dynasty_id, season))
            count_before = cursor.fetchone()[0]

            if count_before == 0:
                logger.info(f"[PLAY_GRADES_DELETE] No play grades found for season {season}")
                conn.close()
                return ArchivalResult(
                    success=True,
                    dynasty_id=self.dynasty_id,
                    season=season,
                    operation='delete_play_grades',
                    rows_deleted=0
                )

            # Delete play grades for this season
            # player_play_grades doesn't have a direct season column,
            # so we join with games to filter by season
            cursor = conn.execute("""
                DELETE FROM player_play_grades
                WHERE dynasty_id = ? AND game_id IN (
                    SELECT game_id FROM games
                    WHERE dynasty_id = ? AND season = ?
                )
            """, (self.dynasty_id, self.dynasty_id, season))

            rows_deleted = cursor.rowcount
            conn.commit()
            conn.close()

            logger.info(
                f"[PLAY_GRADES_DELETE] Deleted {rows_deleted} play grades for season {season} "
                f"(expected {count_before})"
            )

            return ArchivalResult(
                success=True,
                dynasty_id=self.dynasty_id,
                season=season,
                operation='delete_play_grades',
                rows_deleted=rows_deleted
            )

        except Exception as e:
            logger.error(f"[PLAY_GRADES_DELETE] Failed: {e}", exc_info=True)
            return ArchivalResult(
                success=False,
                dynasty_id=self.dynasty_id,
                season=season,
                operation='delete_play_grades',
                error_message=str(e)
            )

    # ========================================================================
    # TOLLGATE 4: Game Data Archival (2-Season Retention)
    # ========================================================================

    def archive_old_game_data(self, current_season: int) -> List[ArchivalResult]:
        """
        Archive and delete game-level data older than the retention window.

        Process for each season beyond retention:
        1. Export to CSV (player_game_stats, player_game_grades, box_scores)
        2. Validate export checksums and row counts
        3. Delete from database

        Args:
            current_season: Current season year (used to calculate cutoff)

        Returns:
            List of ArchivalResult for each archived season
        """
        results = []
        archive_cutoff = current_season - self.retention_seasons

        logger.info(
            f"[ARCHIVE_GAME_DATA] Checking for seasons to archive. "
            f"current={current_season}, retention={self.retention_seasons}, "
            f"cutoff={archive_cutoff}"
        )

        # Get seasons that have game data
        seasons_with_data = self._get_seasons_with_game_data()

        if not seasons_with_data:
            logger.info("[ARCHIVE_GAME_DATA] No seasons with game data found")
            return results

        # Find seasons that should be archived (older than cutoff)
        seasons_to_archive = [s for s in seasons_with_data if s <= archive_cutoff]

        if not seasons_to_archive:
            logger.info(
                f"[ARCHIVE_GAME_DATA] No seasons to archive. "
                f"Oldest season: {min(seasons_with_data)}, cutoff: {archive_cutoff}"
            )
            return results

        logger.info(f"[ARCHIVE_GAME_DATA] Archiving seasons: {seasons_to_archive}")

        for season in sorted(seasons_to_archive):
            result = self._archive_single_season(season)
            results.append(result)

            if not result.success:
                logger.error(
                    f"[ARCHIVE_GAME_DATA] Failed to archive season {season}, "
                    f"stopping archival process"
                )
                break

        return results

    def _archive_single_season(self, season: int) -> ArchivalResult:
        """
        Archive a single season: export to CSV, validate, then delete.

        Args:
            season: Season year to archive

        Returns:
            ArchivalResult with export and deletion details
        """
        logger.info(f"[ARCHIVE_SEASON] Archiving season {season}")

        try:
            # Step 1: Export to CSV
            export_result = self.csv_export_service.export_season(
                self.dynasty_id, season
            )

            if not export_result.success:
                return ArchivalResult(
                    success=False,
                    dynasty_id=self.dynasty_id,
                    season=season,
                    operation='archive_game_data',
                    rows_exported=export_result.total_rows,
                    error_message=export_result.error_message
                )

            # Step 2: Validate export
            if not self.csv_export_service.validate_export(export_result):
                return ArchivalResult(
                    success=False,
                    dynasty_id=self.dynasty_id,
                    season=season,
                    operation='archive_game_data',
                    rows_exported=export_result.total_rows,
                    error_message="Export validation failed"
                )

            # Step 3: Validate against database
            if not self.csv_export_service.validate_against_database(
                self.dynasty_id, season, export_result
            ):
                return ArchivalResult(
                    success=False,
                    dynasty_id=self.dynasty_id,
                    season=season,
                    operation='archive_game_data',
                    rows_exported=export_result.total_rows,
                    error_message="Database row count mismatch"
                )

            # Step 4: Delete from database
            rows_deleted = self._delete_game_data_for_season(season)

            logger.info(
                f"[ARCHIVE_SEASON] Season {season} archived successfully. "
                f"Exported {export_result.total_rows} rows, deleted {rows_deleted} rows"
            )

            return ArchivalResult(
                success=True,
                dynasty_id=self.dynasty_id,
                season=season,
                operation='archive_game_data',
                rows_exported=export_result.total_rows,
                rows_deleted=rows_deleted
            )

        except Exception as e:
            logger.error(f"[ARCHIVE_SEASON] Failed: {e}", exc_info=True)
            return ArchivalResult(
                success=False,
                dynasty_id=self.dynasty_id,
                season=season,
                operation='archive_game_data',
                error_message=str(e)
            )

    def _delete_game_data_for_season(self, season: int) -> int:
        """
        Delete game-level data for a season from all tables.

        Deletes from:
        - player_game_stats
        - player_game_grades
        - box_scores

        Note: Does NOT delete games table entries (needed for standings/schedule reference)

        Args:
            season: Season year to delete

        Returns:
            Total rows deleted across all tables
        """
        conn = sqlite3.connect(self.db_path)
        total_deleted = 0

        try:
            # Get game_ids for this season
            cursor = conn.execute("""
                SELECT game_id FROM games
                WHERE dynasty_id = ? AND season = ?
            """, (self.dynasty_id, season))
            game_ids = [row[0] for row in cursor.fetchall()]

            if not game_ids:
                conn.close()
                return 0

            # Delete from player_game_stats
            cursor = conn.execute("""
                DELETE FROM player_game_stats
                WHERE dynasty_id = ? AND game_id IN (
                    SELECT game_id FROM games WHERE dynasty_id = ? AND season = ?
                )
            """, (self.dynasty_id, self.dynasty_id, season))
            total_deleted += cursor.rowcount
            logger.info(f"  Deleted {cursor.rowcount} player_game_stats rows")

            # Delete from player_game_grades
            cursor = conn.execute("""
                DELETE FROM player_game_grades
                WHERE dynasty_id = ? AND season = ?
            """, (self.dynasty_id, season))
            total_deleted += cursor.rowcount
            logger.info(f"  Deleted {cursor.rowcount} player_game_grades rows")

            # Delete from box_scores
            cursor = conn.execute("""
                DELETE FROM box_scores
                WHERE dynasty_id = ? AND game_id IN (
                    SELECT game_id FROM games WHERE dynasty_id = ? AND season = ?
                )
            """, (self.dynasty_id, self.dynasty_id, season))
            total_deleted += cursor.rowcount
            logger.info(f"  Deleted {cursor.rowcount} box_scores rows")

            conn.commit()

        finally:
            conn.close()

        return total_deleted

    def _get_seasons_with_game_data(self) -> List[int]:
        """Get all seasons that have game data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT DISTINCT season FROM games
            WHERE dynasty_id = ?
            ORDER BY season ASC
        """, (self.dynasty_id,))
        seasons = [row[0] for row in cursor.fetchall()]
        conn.close()
        return seasons

    # ========================================================================
    # TOLLGATE 5: Full Season Archival (called at season rollover)
    # ========================================================================

    def archive_completed_season(
        self,
        completed_season: int,
        current_season: int
    ) -> SeasonArchivalSummary:
        """
        Full archival pipeline for season rollover.

        Called at the start of Training Camp (new season), this method:
        1. Deletes play grades for the completed season (immediate, no CSV)
        2. Archives old game data beyond retention window (CSV + delete)

        Args:
            completed_season: Season that just ended (playoffs complete)
            current_season: New season starting (training camp)

        Returns:
            SeasonArchivalSummary with all operation results
        """
        logger.info(
            f"[SEASON_ARCHIVAL] Starting archival for dynasty={self.dynasty_id}. "
            f"completed={completed_season}, current={current_season}"
        )

        summary = SeasonArchivalSummary(
            dynasty_id=self.dynasty_id,
            completed_season=completed_season,
            current_season=current_season
        )

        # Step 1: Delete play grades for completed season (biggest space saver)
        play_grades_result = self.delete_play_grades_for_season(completed_season)

        if play_grades_result.success:
            summary.play_grades_deleted = play_grades_result.rows_deleted
        else:
            summary.errors.append(
                f"Play grades deletion failed: {play_grades_result.error_message}"
            )
            summary.success = False
            # Continue anyway - play grades deletion is not critical

        # Step 2: Archive old game data (if beyond retention window)
        archive_results = self.archive_old_game_data(current_season)

        for result in archive_results:
            if result.success:
                summary.seasons_archived.append(result.season)
            else:
                summary.errors.append(
                    f"Archive failed for season {result.season}: {result.error_message}"
                )
                summary.success = False

        logger.info(
            f"[SEASON_ARCHIVAL] Complete. Play grades deleted: {summary.play_grades_deleted}, "
            f"Seasons archived: {summary.seasons_archived}, "
            f"Success: {summary.success}"
        )

        return summary

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_archival_status(self) -> dict:
        """
        Get current archival status for this dynasty.

        Returns:
            Dictionary with status information
        """
        conn = sqlite3.connect(self.db_path)

        # Get seasons with game data
        cursor = conn.execute("""
            SELECT DISTINCT season FROM games
            WHERE dynasty_id = ?
            ORDER BY season
        """, (self.dynasty_id,))
        seasons_with_games = [row[0] for row in cursor.fetchall()]

        # Count play grades
        cursor = conn.execute("""
            SELECT COUNT(*) FROM player_play_grades
            WHERE dynasty_id = ?
        """, (self.dynasty_id,))
        result = cursor.fetchone()
        play_grades_count = result[0] if result else 0

        # Count game stats
        cursor = conn.execute("""
            SELECT COUNT(*) FROM player_game_stats
            WHERE dynasty_id = ?
        """, (self.dynasty_id,))
        result = cursor.fetchone()
        game_stats_count = result[0] if result else 0

        conn.close()

        return {
            'dynasty_id': self.dynasty_id,
            'retention_seasons': self.retention_seasons,
            'seasons_with_game_data': seasons_with_games,
            'play_grades_count': play_grades_count,
            'game_stats_count': game_stats_count,
            'estimated_play_grades_mb': play_grades_count * 60 / 1_000_000,  # ~60 bytes/row
        }