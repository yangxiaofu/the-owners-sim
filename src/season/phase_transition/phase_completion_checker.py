"""
Phase Completion Checker

Checks if NFL season phases are complete using injectable dependencies.

This module provides a testable phase completion checker that uses protocol-based
dependency injection instead of direct database access. This enables pure logic
testing without I/O operations.

Design Principles:
- Dependency injection via callable protocols
- Pure logic with no side effects
- Clear separation of concerns (logic vs data access)
- Testable without database

Example Usage:
    # Production usage with real database access
    checker = PhaseCompletionChecker(
        get_games_played=lambda: game_db_api.get_games_played_count(dynasty_id),
        get_current_date=lambda: calendar_manager.get_current_date(),
        get_last_regular_season_game_date=lambda: Date(2025, 1, 5),
        is_super_bowl_complete=lambda: playoff_controller.is_super_bowl_complete()
    )

    if checker.is_regular_season_complete():
        transition_to_playoffs()

    # Testing with mocks
    checker = PhaseCompletionChecker(
        get_games_played=lambda: 272,
        get_current_date=lambda: Date(2025, 1, 10),
        get_last_regular_season_game_date=lambda: Date(2025, 1, 5),
        is_super_bowl_complete=lambda: False
    )

    assert checker.is_regular_season_complete() is True
"""

from typing import Callable

# Use src. prefix to avoid collision with Python builtin calendar
try:
    from src.calendar.date_models import Date
except ModuleNotFoundError:
    # Fallback for test environment
    from src.calendar.date_models import Date


class PhaseCompletionChecker:
    """
    Checks phase completion status with testable, injectable logic.

    This class determines whether NFL season phases (regular season, playoffs)
    are complete by using injected dependency functions. This design enables
    unit testing without database access or I/O operations.

    The checker uses two complementary approaches for regular season completion:
    1. Game count (primary): 272 games = 32 teams × 17 games / 2
    2. Date check (fallback): Current date past last scheduled game

    For playoffs, completion is determined by Super Bowl completion status.

    Attributes:
        _get_games_played: Callable that returns count of completed games
        _get_current_date: Callable that returns current simulation date
        _get_last_regular_season_game_date: Callable that returns final regular season game date
        _get_last_preseason_game_date: Callable that returns final preseason game date
        _is_super_bowl_complete: Callable that checks Super Bowl completion
        _calculate_preseason_start: Callable that calculates preseason start date

    Thread Safety:
        This class is thread-safe as it contains no mutable state. All state
        is retrieved via injected callables at the time of method invocation.
    """

    # NFL season constants
    REGULAR_SEASON_GAME_COUNT = 272  # 32 teams × 17 games / 2
    PRESEASON_GAME_COUNT = 48  # 32 teams × 3 games / 2

    def __init__(
        self,
        get_games_played: Callable[[], int],
        get_current_date: Callable[[], Date],
        get_last_regular_season_game_date: Callable[[], Date],
        get_last_preseason_game_date: Callable[[], Date],
        is_super_bowl_complete: Callable[[], bool],
        calculate_preseason_start: Callable[[], Date]
    ):
        """
        Initialize with injectable dependency functions.

        This constructor accepts callable functions instead of concrete objects,
        enabling flexible dependency injection for both production and testing.

        Args:
            get_games_played: Function that returns count of games played in
                current season. Should return 0-272 for regular season.
                Example: lambda: database_api.count_completed_games(dynasty_id)

            get_current_date: Function that returns current simulation date.
                Should return Date object representing "today" in simulation.
                Example: lambda: calendar_manager.get_current_date()

            get_last_regular_season_game_date: Function that returns the date
                of the final scheduled regular season game (typically early Jan).
                Example: lambda: Date(2025, 1, 5)

            get_last_preseason_game_date: Function that returns the date
                of the final scheduled preseason game (typically early Sept).
                Example: lambda: Date(2025, 9, 3)

            is_super_bowl_complete: Function that checks if Super Bowl has been
                played and completed. Should return boolean.
                Example: lambda: playoff_controller.is_super_bowl_complete()

            calculate_preseason_start: Function that calculates the preseason
                start date for the upcoming season (typically early August).
                Example: lambda: schedule_generator.calculate_preseason_start_date()

        Raises:
            None. Validation occurs at method call time, not initialization.

        Design Notes:
            Using lambdas or bound methods allows lazy evaluation - dependencies
            are queried only when needed, not at construction time. This supports
            dynamic state changes and reduces coupling.
        """
        self._get_games_played = get_games_played
        self._get_current_date = get_current_date
        self._get_last_regular_season_game_date = get_last_regular_season_game_date
        self._get_last_preseason_game_date = get_last_preseason_game_date
        self._is_super_bowl_complete = is_super_bowl_complete
        self._calculate_preseason_start = calculate_preseason_start

    def is_regular_season_complete(self) -> bool:
        """
        Check if regular season is complete using pure logic.

        This method determines regular season completion using two complementary
        criteria (both are checked, either can trigger completion):

        1. Primary Check - Game Count:
           - NFL regular season = 32 teams × 17 games / 2 = 272 total games
           - If games_played >= 272, season is definitely complete
           - Most reliable indicator as it's based on concrete game results

        2. Fallback Check - Date Progression:
           - If current date > last scheduled game date, season should be complete
           - Handles edge cases where game counting might be unreliable
           - Ensures calendar progression triggers transition even if game count off

        The dual-criteria approach provides robustness against data inconsistencies
        while maintaining clear, testable logic.

        Returns:
            bool: True if regular season is complete (272+ games OR date past
                last game), False otherwise.

        Example:
            >>> checker.is_regular_season_complete()
            True  # If 272 games played

            >>> checker.is_regular_season_complete()
            True  # If current date is Jan 10 and last game was Jan 5

            >>> checker.is_regular_season_complete()
            False  # If 200 games played and current date is Dec 15

        Thread Safety:
            Thread-safe. No mutable state - all data retrieved via injected
            callables at invocation time.

        Performance:
            O(1) time complexity. Performs 2 function calls and 2 comparisons.
        """
        # Primary check: Game count (most reliable)
        games_played = self._get_games_played()
        if games_played >= self.REGULAR_SEASON_GAME_COUNT:
            return True

        # Fallback check: Date progression (handles edge cases)
        current_date = self._get_current_date()
        last_game_date = self._get_last_regular_season_game_date()

        # Season complete if we've passed the last scheduled game date
        return current_date > last_game_date

    def is_preseason_complete(self) -> bool:
        """
        Check if preseason is complete using pure logic.

        This method determines preseason completion using two complementary
        criteria (both are checked, either can trigger completion):

        1. Primary Check - Game Count:
           - NFL preseason = 32 teams × 3 games / 2 = 48 total games
           - If games_played >= 48, preseason is definitely complete
           - Most reliable indicator as it's based on concrete game results

        2. Fallback Check - Date Progression:
           - If current date > last scheduled preseason game date, preseason should be complete
           - Handles edge cases where game counting might be unreliable
           - Ensures calendar progression triggers transition even if game count off

        The dual-criteria approach provides robustness against data inconsistencies
        while maintaining clear, testable logic.

        Returns:
            bool: True if preseason is complete (48+ games OR date past
                last game), False otherwise.

        Example:
            >>> checker.is_preseason_complete()
            True  # If 48 games played

            >>> checker.is_preseason_complete()
            True  # If current date is Sept 5 and last game was Sept 3

            >>> checker.is_preseason_complete()
            False  # If 30 games played and current date is Aug 25

        Thread Safety:
            Thread-safe. No mutable state - all data retrieved via injected
            callables at invocation time.

        Performance:
            O(1) time complexity. Performs 2 function calls and 2 comparisons.
        """
        # Diagnostic entry
        print("\n" + "="*80)
        print("[PHASE_COMPLETION_CHECK] is_preseason_complete() called")
        print("="*80)

        # Primary check: Game count (most reliable)
        games_played = self._get_games_played()
        print(f"[PHASE_COMPLETION_CHECK] games_played: {games_played}")
        print(f"[PHASE_COMPLETION_CHECK] PRESEASON_GAME_COUNT: {self.PRESEASON_GAME_COUNT}")
        print(f"[PHASE_COMPLETION_CHECK] Check: {games_played} >= {self.PRESEASON_GAME_COUNT}? {games_played >= self.PRESEASON_GAME_COUNT}")

        if games_played >= self.PRESEASON_GAME_COUNT:
            print(f"[PHASE_COMPLETION_CHECK] ✓ PRIMARY CHECK PASSED - Preseason complete!")
            print(f"[PHASE_COMPLETION_CHECK] → Returning True")
            print("="*80 + "\n")
            return True

        # Fallback check: Date progression (handles edge cases)
        print(f"[PHASE_COMPLETION_CHECK] Primary check failed ({games_played} < {self.PRESEASON_GAME_COUNT})")
        print(f"[PHASE_COMPLETION_CHECK] Trying fallback check (date progression)...")

        current_date = self._get_current_date()
        last_game_date = self._get_last_preseason_game_date()

        print(f"[PHASE_COMPLETION_CHECK] current_date: {current_date}")
        print(f"[PHASE_COMPLETION_CHECK] last_game_date: {last_game_date}")
        print(f"[PHASE_COMPLETION_CHECK] Check: {current_date} > {last_game_date}? {current_date > last_game_date}")

        # Preseason complete if we've passed the last scheduled preseason game date
        result = current_date > last_game_date
        print(f"[PHASE_COMPLETION_CHECK] → Returning {result} (fallback check)")
        print("="*80 + "\n")
        return result

    def is_playoffs_complete(self) -> bool:
        """
        Check if playoffs are complete using pure logic.

        This method determines playoff completion by checking if the Super Bowl
        has been played. The Super Bowl is the final game of the NFL season,
        so its completion definitively marks the end of the playoff phase.

        Playoff Structure (for context):
        - Wild Card Round: 6 games (weekend 1)
        - Divisional Round: 4 games (weekend 2)
        - Conference Championships: 2 games (weekend 3)
        - Super Bowl: 1 game (weekend 4)
        - Total: 13 playoff games

        However, we only check Super Bowl completion as it's the definitive
        marker of playoff phase completion. Intermediate round completion
        is not relevant for phase transition logic.

        Returns:
            bool: True if Super Bowl has been played and completed, False otherwise.

        Example:
            >>> checker.is_playoffs_complete()
            True  # If Super Bowl completed

            >>> checker.is_playoffs_complete()
            False  # If still in Conference Championship round

        Thread Safety:
            Thread-safe. No mutable state - all data retrieved via injected
            callable at invocation time.

        Performance:
            O(1) time complexity. Performs 1 function call.

        Design Notes:
            We delegate to an injected callable rather than checking game counts
            or dates because playoff completion logic may vary based on:
            - Playoff controller implementation details
            - Database schema for playoff games
            - Business rules for "completion" (game finished vs awards given, etc.)

            By injecting this dependency, we maintain flexibility and testability.
        """
        return self._is_super_bowl_complete()

    def is_offseason_complete(self) -> bool:
        """
        Check if offseason is complete and ready for preseason using pure logic.

        This method determines offseason completion by checking if the current
        simulation date has reached or passed the preseason start date (typically
        early August). When this condition is met, the system should transition
        from OFFSEASON to PRESEASON phase and initialize the new season.

        Offseason typically includes:
        - Free agency period (March-April)
        - NFL Draft (late April)
        - Rookie mini-camp and OTAs (May-June)
        - Training camp preparation (July)
        - Preseason begins (early August)

        Returns:
            bool: True if current date >= preseason start date, False otherwise.

        Example:
            >>> # Current date is August 10, preseason starts August 5
            >>> checker.is_offseason_complete()
            True

            >>> # Current date is July 15, preseason starts August 5
            >>> checker.is_offseason_complete()
            False

        Thread Safety:
            Thread-safe. No mutable state - all data retrieved via injected
            callables at invocation time.

        Performance:
            O(1) time complexity. Performs 2 function calls and 1 comparison.

        Design Notes:
            Unlike regular season (which checks game count + date) and playoffs
            (which checks Super Bowl completion), offseason completion is purely
            date-based. The offseason has no "games" to count, so calendar
            progression is the natural completion trigger.

            The preseason start date is typically calculated as the first Thursday
            in August, which aligns with the traditional NFL preseason schedule.
        """
        current_date = self._get_current_date()
        preseason_start = self._calculate_preseason_start()

        # Debug logging to diagnose comparison issue
        print(f"\n[OFFSEASON_COMPLETE_CHECK]")
        print(f"  current_date: {current_date} (type: {type(current_date).__name__})")
        print(f"  preseason_start: {preseason_start} (type: {type(preseason_start).__name__})")
        print(f"  current_date >= preseason_start: {current_date >= preseason_start}")

        # Offseason is complete when we've reached preseason start date
        return current_date >= preseason_start
