"""
Phase Boundary Detector

Centralized phase boundary detection and date calculation for calendar system.
Extracts and consolidates date boundary logic from SeasonCycleController.

Responsibilities:
- Find first/last game dates for any phase
- Calculate phase start dates (from milestone or calculated)
- Calculate phase transition dates (e.g., playoffs start)
- Cache results for performance
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import logging

from src.calendar.date_models import Date
from src.calendar.season_phase_tracker import SeasonPhase
from src.season.season_constants import SeasonConstants, PhaseNames, GameIDPrefixes
from src.events.event_database_api import EventDatabaseAPI
from src.database.unified_api import UnifiedDatabaseAPI


class PhaseBoundaryDetector:
    """
    Centralized phase boundary detection and date calculation.

    This class consolidates all phase boundary logic that was previously
    scattered across SeasonCycleController, providing a single source of
    truth for phase date calculations.

    Key Features:
    - Query first/last game dates for any phase
    - Calculate phase start dates from milestones or by calculation
    - Calculate playoff start dates with Wild Card weekend adjustment
    - Performance caching to minimize database queries
    - Support for both EventDatabaseAPI and UnifiedDatabaseAPI

    Example:
        detector = PhaseBoundaryDetector(
            event_db=event_db,
            dynasty_id="my_dynasty",
            season_year=2024
        )

        # Get playoff start date (Wild Card Saturday)
        playoff_start = detector.get_playoff_start_date()

        # Get regular season date range
        start, end = detector.get_phase_date_range(SeasonPhase.REGULAR_SEASON)
    """

    def __init__(
        self,
        event_db: EventDatabaseAPI,
        dynasty_id: str,
        season_year: int,
        db: Optional[UnifiedDatabaseAPI] = None,
        calendar: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
        cache_results: bool = True
    ):
        """
        Initialize phase boundary detector.

        Args:
            event_db: Event database API for querying game events
            dynasty_id: Dynasty context for isolation
            season_year: NFL season year (e.g., 2024 for 2024-25 season)
            db: Optional unified database API (if available)
            calendar: Optional calendar manager for milestone queries
            logger: Optional logger instance
            cache_results: Whether to cache query results for performance
        """
        self.event_db = event_db
        self.dynasty_id = dynasty_id
        self.season_year = season_year
        self.db = db
        self.calendar = calendar
        self.logger = logger or logging.getLogger(__name__)
        self.cache_results = cache_results

        # Cache dictionary: {cache_key: result}
        self._cache: Dict[str, Any] = {} if cache_results else None

        self.logger.info(
            f"PhaseBoundaryDetector initialized for dynasty={dynasty_id}, "
            f"season_year={season_year}, caching={'enabled' if cache_results else 'disabled'}"
        )

    def get_last_game_date(self, phase: SeasonPhase) -> Date:
        """
        Find the date of the last scheduled game in a phase.

        Args:
            phase: Season phase to query

        Returns:
            Date of the last game in the phase

        Raises:
            ValueError: If no games found for the phase
        """
        cache_key = f"last_game_{phase.value}_{self.season_year}"

        # Check cache first
        if self.cache_results and cache_key in self._cache:
            self.logger.debug(f"Cache hit for {cache_key}")
            return self._cache[cache_key]

        # Get all games for this phase
        games = self._get_phase_games(phase, completed_only=False)

        if not games:
            # FAIL LOUDLY - No fallback dates allowed
            error_msg = (
                f"CRITICAL ERROR: No games found for phase '{phase.value}' in season {self.season_year}!\n"
                f"This indicates a schema mismatch or missing game data.\n"
                f"Dynasty: {self.dynasty_id}\n"
                f"Check that game events are stored with correct parameters (season vs season_year)."
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # Find game with maximum timestamp
        last_game = max(games, key=lambda g: g.get('timestamp'))
        timestamp = last_game.get('timestamp')

        # Convert timestamp to Date (timestamp is already a datetime object from EventDatabaseAPI)
        result = self._timestamp_to_date(timestamp)

        self.logger.info(
            f"Last {phase.value} game date: {result} "
            f"(game_id={last_game.get('game_id', 'unknown')})"
        )

        # Cache result
        if self.cache_results:
            self._cache[cache_key] = result

        return result

    def get_first_game_date(self, phase: SeasonPhase) -> Date:
        """
        Find the date of the first scheduled game in a phase.

        Args:
            phase: Season phase to query

        Returns:
            Date of the first game in the phase

        Raises:
            ValueError: If no games found for the phase
        """
        cache_key = f"first_game_{phase.value}_{self.season_year}"

        # Check cache first
        if self.cache_results and cache_key in self._cache:
            self.logger.debug(f"Cache hit for {cache_key}")
            return self._cache[cache_key]

        # Get all games for this phase
        games = self._get_phase_games(phase, completed_only=False)

        if not games:
            # FAIL LOUDLY - No fallback dates allowed
            error_msg = (
                f"CRITICAL ERROR: No games found for phase '{phase.value}' in season {self.season_year}!\n"
                f"This indicates a schema mismatch or missing game data.\n"
                f"Dynasty: {self.dynasty_id}\n"
                f"Check that game events are stored with correct parameters (season vs season_year)."
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # Find game with minimum timestamp
        first_game = min(games, key=lambda g: g.get('timestamp'))
        timestamp = first_game.get('timestamp')

        # Convert timestamp to Date (timestamp is already a datetime object from EventDatabaseAPI)
        result = self._timestamp_to_date(timestamp)

        self.logger.info(
            f"First {phase.value} game date: {result} "
            f"(game_id={first_game.get('game_id', 'unknown')})"
        )

        # Cache result
        if self.cache_results:
            self._cache[cache_key] = result

        return result

    def get_phase_start_date(
        self,
        phase: SeasonPhase,
        season_year: Optional[int] = None,
        use_milestone: bool = True
    ) -> Date:
        """
        Calculate the start date for a phase.

        This method tries multiple strategies in order:
        1. Query milestone event from calendar (if use_milestone=True)
        2. Query first game date for the phase
        3. Calculate based on phase-specific rules

        Args:
            phase: Season phase to get start date for
            season_year: Optional season year override (defaults to self.season_year)
            use_milestone: Whether to check for milestone events

        Returns:
            Calculated or queried phase start date
        """
        year = season_year or self.season_year
        cache_key = f"phase_start_{phase.value}_{year}_milestone_{use_milestone}"

        # Check cache first
        if self.cache_results and cache_key in self._cache:
            self.logger.debug(f"Cache hit for {cache_key}")
            return self._cache[cache_key]

        result = None

        # Strategy 1: Check for milestone event (if calendar available)
        if use_milestone and self.calendar:
            try:
                # Query milestone event name based on phase
                milestone_names = {
                    SeasonPhase.PRESEASON: "preseason_start",
                    SeasonPhase.REGULAR_SEASON: "regular_season_start",
                    SeasonPhase.PLAYOFFS: "playoffs_start",
                    SeasonPhase.OFFSEASON: "offseason_start"
                }

                milestone_name = milestone_names.get(phase)
                if milestone_name:
                    # Query calendar for milestone event
                    # (Implementation depends on calendar API - placeholder for now)
                    self.logger.debug(f"Checking for milestone: {milestone_name}")
                    # result = self.calendar.get_milestone_date(milestone_name)
            except Exception as e:
                self.logger.debug(f"Milestone query failed: {e}")

        # Strategy 2: Query first game date
        if not result:
            try:
                result = self.get_first_game_date(phase)
            except Exception as e:
                self.logger.debug(f"First game date query failed: {e}")

        # Strategy 3: Calculate based on phase rules
        if not result:
            if phase == SeasonPhase.PLAYOFFS:
                result = self._calculate_playoff_start()
            elif phase == SeasonPhase.PRESEASON:
                result = self._calculate_preseason_start(year)
            else:
                # FAIL LOUDLY - No fallback dates allowed
                error_msg = (
                    f"CRITICAL ERROR: Cannot determine start date for phase '{phase.value}'!\n"
                    f"No milestone, no games, and no calculation method available.\n"
                    f"Dynasty: {self.dynasty_id}, Season: {year}"
                )
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        self.logger.info(f"Phase start date for {phase.value}: {result}")

        # Cache result
        if self.cache_results:
            self._cache[cache_key] = result

        return result

    def get_playoff_start_date(self) -> Date:
        """
        Calculate the Wild Card Saturday date (first day of playoffs).

        NFL playoff structure:
        - Regular season ends (Week 18 Sunday)
        - 14-day delay
        - Wild Card weekend starts on Saturday

        Returns:
            Date of Wild Card Saturday
        """
        cache_key = f"playoff_start_{self.season_year}"

        # Check cache first
        if self.cache_results and cache_key in self._cache:
            self.logger.debug(f"Cache hit for {cache_key}")
            return self._cache[cache_key]

        result = self._calculate_playoff_start()

        # Cache result
        if self.cache_results:
            self._cache[cache_key] = result

        return result

    def get_phase_date_range(self, phase: SeasonPhase) -> Tuple[Date, Date]:
        """
        Get the complete date range for a phase.

        Args:
            phase: Season phase to query

        Returns:
            Tuple of (first_game_date, last_game_date)
        """
        cache_key = f"phase_range_{phase.value}_{self.season_year}"

        # Check cache first
        if self.cache_results and cache_key in self._cache:
            self.logger.debug(f"Cache hit for {cache_key}")
            return self._cache[cache_key]

        first_date = self.get_first_game_date(phase)
        last_date = self.get_last_game_date(phase)

        result = (first_date, last_date)

        self.logger.info(
            f"Phase date range for {phase.value}: {first_date} to {last_date} "
            f"({first_date.days_until(last_date)} days)"
        )

        # Cache result
        if self.cache_results:
            self._cache[cache_key] = result

        return result

    def invalidate_cache(self, season_year: Optional[int] = None) -> None:
        """
        Clear cached results for a specific season year or all years.

        Args:
            season_year: Optional season year to clear (None = clear all)
        """
        if not self.cache_results or not self._cache:
            return

        if season_year is None:
            # Clear entire cache
            count = len(self._cache)
            self._cache.clear()
            self.logger.info(f"Cache cleared ({count} entries)")
        else:
            # Clear only entries for specific season year
            keys_to_remove = [k for k in self._cache.keys() if str(season_year) in k]
            for key in keys_to_remove:
                del self._cache[key]
            self.logger.info(f"Cache cleared for season_year={season_year} ({len(keys_to_remove)} entries)")

    def get_completed_games_count(self, phase: SeasonPhase) -> int:
        """
        Get count of completed games in a specific phase.

        A game is considered "completed" if it has results stored in its data.

        Args:
            phase: Season phase to count games for

        Returns:
            Number of completed games in the phase

        Example:
            >>> detector.get_completed_games_count(SeasonPhase.REGULAR_SEASON)
            272  # All 272 regular season games played
        """
        cache_key = f"completed_count_{phase.value}_{self.season_year}"

        # Check cache first
        if self.cache_results and cache_key in self._cache:
            self.logger.debug(f"Cache hit for {cache_key}")
            return self._cache[cache_key]

        # Query completed games only
        games = self._get_phase_games(phase, completed_only=True)
        count = len(games)

        self.logger.info(f"Completed games in {phase.value}: {count}")

        # Cache result
        if self.cache_results:
            self._cache[cache_key] = count

        return count

    @staticmethod
    def derive_season_year(date: Date) -> int:
        """
        Derive NFL season year from calendar date.

        **SINGLE SOURCE OF TRUTH** for year-from-date conversion.

        NFL Season Year Definition:
        - Season year = year when that season's preseason started
        - Preseason starts in early August (typically Aug 1-10)
        - Season year boundary: August 1st

        Examples:
            >>> PhaseBoundaryDetector.derive_season_year(Date(2025, 8, 1))
            2025  # preseason of 2025 season
            >>> PhaseBoundaryDetector.derive_season_year(Date(2025, 12, 25))
            2025  # regular season of 2025 season
            >>> PhaseBoundaryDetector.derive_season_year(Date(2026, 1, 15))
            2025  # playoffs of 2025 season (in calendar year 2026)
            >>> PhaseBoundaryDetector.derive_season_year(Date(2026, 3, 15))
            2025  # offseason after 2025 season
            >>> PhaseBoundaryDetector.derive_season_year(Date(2026, 7, 31))
            2025  # still in 2025 offseason
            >>> PhaseBoundaryDetector.derive_season_year(Date(2026, 8, 1))
            2026  # preseason of NEW 2026 season

        Args:
            date: Calendar date to derive season year from

        Returns:
            NFL season year (year when that season's preseason started)

        Design Notes:
            - Season year boundary: August 1st
            - If month >= 8 (Aug-Dec): use current calendar year
            - If month < 8 (Jan-Jul): use previous calendar year (still in previous season)
            - This method should be used anywhere season year needs to be derived from a date
            - Consolidates logic that was previously scattered across multiple modules
        """
        # Season year boundary: August 1st
        # If month >= 8 (Aug-Dec): use current calendar year
        # If month < 8 (Jan-Jul): use previous calendar year (still in previous season)
        if date.month >= 8:
            return date.year
        else:
            return date.year - 1

    # ==================== Private Helper Methods ====================

    def _get_phase_games(
        self,
        phase: SeasonPhase,
        completed_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Query all game events for a specific phase.

        Args:
            phase: Season phase to query
            completed_only: Whether to filter for completed games only

        Returns:
            List of game event dictionaries
        """
        # Map SeasonPhase to database phase name
        phase_map = {
            SeasonPhase.PRESEASON: PhaseNames.PRESEASON,
            SeasonPhase.REGULAR_SEASON: PhaseNames.REGULAR_SEASON,
            SeasonPhase.PLAYOFFS: PhaseNames.PLAYOFFS,
            SeasonPhase.OFFSEASON: PhaseNames.OFFSEASON
        }

        phase_name = phase_map.get(phase)
        if not phase_name:
            self.logger.warning(f"Unknown phase: {phase}")
            return []

        # Query all GAME events for this dynasty
        all_games = self.event_db.get_events_by_dynasty(
            dynasty_id=self.dynasty_id,
            event_type="GAME"
        )

        # Filter for this phase and season year
        phase_games = [
            game for game in all_games
            if self._is_game_in_phase(game, phase) and
               game.get('data', {}).get('parameters', {}).get('season') == self.season_year
        ]

        # Filter for completed games if requested
        if completed_only:
            phase_games = [
                game for game in phase_games
                if game.get('data', {}).get('status') == 'completed'
            ]

        self.logger.debug(
            f"Found {len(phase_games)} {'completed ' if completed_only else ''}"
            f"games for phase {phase.value} in season {self.season_year}"
        )

        return phase_games

    def _is_game_in_phase(self, game_event: Dict[str, Any], phase: SeasonPhase) -> bool:
        """
        Check if a game event belongs to a specific phase.

        Uses game_id prefix and season_type metadata to determine phase.

        Args:
            game_event: Game event dictionary
            phase: Season phase to check

        Returns:
            True if game belongs to the phase
        """
        game_id = game_event.get('game_id', '')
        params = game_event.get('data', {}).get('parameters', {})
        season_type = params.get('season_type', '')
        week = params.get('week', 0)

        if phase == SeasonPhase.PRESEASON:
            # Preseason games have "preseason_" prefix OR season_type='preseason'
            # Typically weeks 1-4
            return (
                game_id.startswith(GameIDPrefixes.PRESEASON) or
                season_type == PhaseNames.PRESEASON or
                (season_type == '' and 1 <= week <= 4 and game_id.startswith('preseason'))
            )

        elif phase == SeasonPhase.REGULAR_SEASON:
            # Regular season games:
            # - NOT playoff or preseason prefix
            # - season_type='regular_season' OR weeks 1-18 without special prefix
            return (
                not game_id.startswith(GameIDPrefixes.PLAYOFF) and
                not game_id.startswith(GameIDPrefixes.PRESEASON) and
                (season_type in [PhaseNames.REGULAR_SEASON, 'regular'] or
                 (1 <= week <= SeasonConstants.REGULAR_SEASON_WEEKS))
            )

        elif phase == SeasonPhase.PLAYOFFS:
            # Playoff games have "playoff_" prefix
            return game_id.startswith(GameIDPrefixes.PLAYOFF)

        elif phase == SeasonPhase.OFFSEASON:
            # Offseason has no games (return False for all)
            return False

        return False

    def _calculate_playoff_start(self) -> Date:
        """
        Calculate Wild Card Saturday based on last regular season game.

        Algorithm:
        1. Get last regular season game date
        2. Add 14-day playoff delay
        3. Adjust to next Saturday (weekday 5)

        Returns:
            Calculated Wild Card Saturday date
        """
        # Get last regular season game date
        last_regular_season = self.get_last_game_date(SeasonPhase.REGULAR_SEASON)

        # Add playoff delay (14 days)
        date_after_delay = last_regular_season.add_days(SeasonConstants.PLAYOFF_DELAY_DAYS)

        # Adjust to Saturday (weekday 5)
        # Python weekday: Monday=0, Tuesday=1, ..., Saturday=5, Sunday=6
        py_date = date_after_delay.to_python_date()
        current_weekday = py_date.weekday()
        target_weekday = SeasonConstants.WILD_CARD_WEEKDAY  # Saturday = 5

        # Calculate days to add to reach Saturday
        if current_weekday <= target_weekday:
            days_to_add = target_weekday - current_weekday
        else:
            # Already past Saturday, go to next Saturday
            days_to_add = 7 - (current_weekday - target_weekday)

        # Safety check to prevent infinite loops
        if days_to_add > SeasonConstants.DATE_ADJUSTMENT_SAFETY_LIMIT:
            self.logger.warning(
                f"Date adjustment exceeds safety limit: {days_to_add} days. "
                f"Using unadjusted date."
            )
            days_to_add = 0

        wild_card_saturday = date_after_delay.add_days(days_to_add)

        self.logger.info(
            f"Playoff start calculation: last_regular_season={last_regular_season}, "
            f"after_delay={date_after_delay}, wild_card_saturday={wild_card_saturday}"
        )

        return wild_card_saturday

    def _calculate_preseason_start(self, season_year: int) -> Date:
        """
        Calculate preseason start date based on NFL schedule patterns.

        NFL preseason typically starts in early August.
        This is a fallback calculation when no scheduled games exist.

        Args:
            season_year: Season year to calculate for

        Returns:
            Estimated preseason start date
        """
        # NFL preseason typically starts first week of August
        # Use August 1st as a reasonable default
        preseason_start = Date(year=season_year, month=8, day=1)

        # Adjust to Thursday (NFL preseason often starts Thursday)
        # Thursday = 3 in Python weekday
        py_date = preseason_start.to_python_date()
        current_weekday = py_date.weekday()
        target_weekday = 3  # Thursday

        if current_weekday <= target_weekday:
            days_to_add = target_weekday - current_weekday
        else:
            days_to_add = 7 - (current_weekday - target_weekday)

        result = preseason_start.add_days(days_to_add)

        self.logger.info(
            f"Preseason start calculation (fallback): {result} "
            f"(season_year={season_year})"
        )

        return result

    def _timestamp_to_date(self, timestamp: datetime) -> Date:
        """
        Convert datetime timestamp to Date object.

        Args:
            timestamp: Python datetime object

        Returns:
            Date object
        """
        return Date(
            year=timestamp.year,
            month=timestamp.month,
            day=timestamp.day
        )
