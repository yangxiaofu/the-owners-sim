"""
Schedule Coordinator - Single Source of Truth for Schedule Generation.

Provides idempotent schedule generation methods that prevent duplicate games
and race conditions. Replaces the 3 on-demand generation patches scattered
across handlers.

Architecture Pattern:
    - Check-then-generate pattern (idempotent)
    - Single responsibility: coordinate schedule existence
    - Delegates actual generation to specialized services
    - Transaction-safe operations

Usage:
    coordinator = ScheduleCoordinator(db_path, dynasty_id)

    # Safe to call multiple times - only generates if missing
    coordinator.ensure_regular_season_schedule(season=2026)
    coordinator.ensure_preseason_schedule(season=2026)

    # Check methods (no side effects)
    has_regular = coordinator.has_regular_season_schedule(season=2026)
    has_preseason = coordinator.has_preseason_schedule(season=2026)

Design Goals:
    1. Idempotent: Calling ensure_*_schedule() multiple times is safe
    2. Atomic: Complete schedule (288 or 48 games) or nothing
    3. Single Source of Truth: One place to check/ensure schedules
    4. No Race Conditions: Delegates to services with proper locking
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ScheduleCoordinator:
    """
    Coordinates schedule generation across regular season and preseason.

    Provides idempotent methods to ensure schedules exist before handlers
    attempt to execute games. Replaces on-demand generation patches with
    a single, consistent API.

    Expected Game Counts (NFL 2024+ format):
        - Regular Season: 288 games (18 weeks × 16 games/week)
        - Preseason: 48 games (3 weeks × 16 games/week)

    Key Design Principles:
        - Check before generate (avoid duplicate work)
        - Delegate to specialized services (separation of concerns)
        - Log all operations (debugging/auditing)
        - Return counts (transparency)
    """

    # Expected game counts for complete schedules
    REGULAR_SEASON_TOTAL_GAMES = 272  # 17 weeks × 16 games (current implementation)
    PRESEASON_TOTAL_GAMES = 48        # 3 weeks × 16 games

    def __init__(self, db_path: str, dynasty_id: str):
        """
        Initialize the schedule coordinator.

        Args:
            db_path: Path to the game_cycle database
            dynasty_id: Dynasty identifier for event isolation
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id

    def ensure_regular_season_schedule(self, season: int) -> int:
        """
        Ensure regular season schedule exists for the given season.

        Idempotent operation - checks if schedule exists before generating.
        Safe to call multiple times. Only generates if missing or incomplete.

        Args:
            season: Season year (e.g., 2026)

        Returns:
            Number of games in database after operation (288 if complete)

        Raises:
            Exception: If schedule generation fails
        """
        if self.has_regular_season_schedule(season):
            count = self._count_games(season, 'regular_season')
            logger.info(
                f"[ScheduleCoordinator] Regular season schedule already exists for {season} "
                f"({count} games)"
            )
            return count

        logger.info(f"[ScheduleCoordinator] Generating regular season schedule for {season}")
        return self._generate_regular_season_schedule(season)

    def ensure_preseason_schedule(self, season: int) -> int:
        """
        Ensure preseason schedule exists for the given season.

        Idempotent operation - checks if schedule exists before generating.
        Safe to call multiple times. Only generates if missing or incomplete.

        Args:
            season: Season year (e.g., 2026)

        Returns:
            Number of games in database after operation (48 if complete)

        Raises:
            Exception: If schedule generation fails
        """
        if self.has_preseason_schedule(season):
            count = self._count_games(season, 'preseason')
            logger.info(
                f"[ScheduleCoordinator] Preseason schedule already exists for {season} "
                f"({count} games)"
            )
            return count

        logger.info(f"[ScheduleCoordinator] Generating preseason schedule for {season}")
        return self._generate_preseason_schedule(season)

    def has_regular_season_schedule(self, season: int) -> bool:
        """
        Check if complete regular season schedule exists.

        Args:
            season: Season year to check

        Returns:
            True if all 288 games exist, False otherwise
        """
        count = self._count_games(season, 'regular_season')
        return count == self.REGULAR_SEASON_TOTAL_GAMES

    def has_preseason_schedule(self, season: int) -> bool:
        """
        Check if complete preseason schedule exists.

        Args:
            season: Season year to check

        Returns:
            True if all 48 games exist, False otherwise
        """
        count = self._count_games(season, 'preseason')
        return count == self.PRESEASON_TOTAL_GAMES

    def _count_games(self, season: int, season_type: str) -> int:
        """
        Count games in the events table for a specific season and type.

        Uses UnifiedDatabaseAPI to query events table with proper dynasty
        isolation and JSON field extraction.

        Args:
            season: Season year (e.g., 2026)
            season_type: 'regular_season' or 'preseason'

        Returns:
            Number of game events matching criteria
        """
        from database.unified_api import UnifiedDatabaseAPI

        api = UnifiedDatabaseAPI(self._db_path, self._dynasty_id)

        # Use existing API method to get games
        games = api.events_get_games_by_season(season, season_type)
        return len(games)

    def _generate_regular_season_schedule(self, season: int) -> int:
        """
        Generate regular season schedule by delegating to ScheduleService.

        Creates 288 game events (18 weeks × 16 games) using the NFL-compliant
        scheduling algorithm or static schedule data if available.

        Args:
            season: Season year to generate

        Returns:
            Number of games created (288)

        Raises:
            Exception: If schedule generation fails
        """
        from game_cycle.services.schedule_service import ScheduleService

        service = ScheduleService(
            db_path=self._db_path,
            dynasty_id=self._dynasty_id,
            season=season
        )

        # clear_existing=True ensures clean slate (removes duplicates if any)
        # copy_from_previous=True reuses matchups from prior season when available
        games_created = service.generate_schedule(
            clear_existing=True,
            copy_from_previous=True
        )

        logger.info(
            f"[ScheduleCoordinator] Created {games_created} regular season games for {season}"
        )
        return games_created

    def _generate_preseason_schedule(self, season: int) -> int:
        """
        Generate preseason schedule by delegating to PreseasonScheduleService.

        Creates 48 game events (3 weeks × 16 games) using non-repeating,
        non-division matchups with backtracking algorithm.

        Args:
            season: Season year to generate

        Returns:
            Number of games created (48)

        Raises:
            Exception: If schedule generation fails
        """
        from game_cycle.services.preseason_schedule_service import PreseasonScheduleService

        service = PreseasonScheduleService(
            db_path=self._db_path,
            dynasty_id=self._dynasty_id,
            season=season
        )

        # clear_existing=True ensures clean slate (removes duplicates if any)
        games_created = service.generate_preseason_schedule(clear_existing=True)

        logger.info(
            f"[ScheduleCoordinator] Created {games_created} preseason games for {season}"
        )
        return games_created
