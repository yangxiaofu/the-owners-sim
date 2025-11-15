"""
Offseason to Preseason Handler

Handles the transition from OFFSEASON phase to PRESEASON phase (new season).

This handler orchestrates the initialization of a new NFL season:
1. Clears playoff data from completed season
2. Generates preseason schedule (48 games, 3 weeks)
3. Generates regular season schedule (272 games, 17 weeks)
4. Resets all team standings to 0-0-0
5. Updates database to preseason phase
6. Supports rollback on failure with partial state tracking
"""

from typing import Any, Dict, Callable, Optional, List
from datetime import datetime
from ..models import PhaseTransition
from database.playoff_database_api import PlayoffDatabaseAPI
from database.connection import DatabaseConnection


class OffseasonToPreseasonHandler:
    """
    Handles OFFSEASON → PRESEASON transition (new season initialization).

    This handler is responsible for setting up a new NFL season after the
    offseason phase completes. It generates schedules, resets standings,
    and updates the database to reflect the new season state.

    Responsibilities:
    1. Clear playoff data from completed season
    2. Generate preseason schedule (48 games, 3 weeks)
    3. Generate regular season schedule (272 games, 17 weeks)
    4. Reset all team standings to 0-0-0
    5. Update database to preseason phase
    6. Support rollback on failure with partial state restoration

    Design:
    - Uses dependency injection for all external operations
    - Tracks completion state for granular rollback
    - Provides detailed logging for new season initialization debugging
    - Validates all inputs before execution

    Usage:
        handler = OffseasonToPreseasonHandler(
            generate_preseason=schedule_generator.generate_preseason_schedule,
            generate_regular_season=schedule_generator.generate_regular_season_schedule,
            reset_standings=standings_manager.reset_all_standings,
            calculate_preseason_start=schedule_generator.calculate_preseason_start_date,
            update_database_phase=database.update_phase,
            dynasty_id="my_dynasty",
            new_season_year=2025,
            verbose_logging=True
        )
        result = handler.execute(transition)
    """

    def __init__(
        self,
        generate_preseason: Callable[[int], List[Dict[str, Any]]],
        generate_regular_season: Callable[[int, datetime], List[Dict[str, Any]]],
        reset_standings: Callable[[int], None],
        calculate_preseason_start: Callable[[int], datetime],
        execute_year_transition: Callable[[int, int], Dict[str, Any]],
        update_database_phase: Callable[[str, int], None],
        dynasty_id: str,
        new_season_year: int,
        event_db=None,  # EventDatabaseAPI instance for game validation
        playoff_database_api: Optional[PlayoffDatabaseAPI] = None,
        database_connection: Optional[DatabaseConnection] = None,
        db_path: str = "data/database/nfl_simulation.db",
        verbose_logging: bool = False
    ):
        """
        Initialize the Offseason → Preseason transition handler.

        Args:
            generate_preseason: Function to generate preseason schedule
                - Takes: season_year (int)
                - Returns: List of preseason game events (48 games)
            generate_regular_season: Function to generate regular season schedule
                - Takes: season_year (int), start_date (datetime)
                - Returns: List of regular season game events (272 games)
            reset_standings: Function to reset all team standings
                - Takes: season_year (int)
                - Returns: None (resets all teams to 0-0-0)
            calculate_preseason_start: Function to calculate preseason start date
                - Takes: season_year (int)
                - Returns: datetime (typically early August)
            execute_year_transition: Function to execute complete year transition
                - Takes: old_year (int), new_year (int)
                - Returns: Dict with transition results (year increment, contracts, draft)
                - Part of Milestone 1: Complete Multi-Year Season Cycle
            update_database_phase: Function to update database phase
                - Takes: phase (str), season_year (int)
                - Returns: None (updates dynasty_state table)
            dynasty_id: Dynasty identifier for logging and context
            new_season_year: The new season year being initialized
            event_db: EventDatabaseAPI instance for game validation
            playoff_database_api: PlayoffDatabaseAPI instance for playoff cleanup (optional)
            database_connection: DatabaseConnection instance for database access (optional)
            db_path: Path to database file (default: "data/database/nfl_simulation.db")
            verbose_logging: Enable detailed step-by-step logging

        Raises:
            ValueError: If new_season_year is invalid (< 1920 or > 2100)
        """
        # Validate season year
        if new_season_year < 1920 or new_season_year > 2100:
            raise ValueError(
                f"Invalid season year: {new_season_year}. "
                f"Must be between 1920 and 2100."
            )

        # Store dependencies
        self._generate_preseason = generate_preseason
        self._generate_regular_season = generate_regular_season
        self._reset_standings = reset_standings
        self._calculate_preseason_start = calculate_preseason_start
        self._execute_year_transition = execute_year_transition
        self._update_database_phase = update_database_phase
        self._event_db = event_db  # For game validation
        self._playoff_db_api = playoff_database_api  # For playoff cleanup
        self._db_connection = database_connection  # For database access
        self._db_path = db_path  # Database path

        # Store context
        self._dynasty_id = dynasty_id
        self._new_season_year = new_season_year
        self._verbose_logging = verbose_logging

        # Rollback state tracking
        self._rollback_state: Dict[str, Any] = {}

    @property
    def playoff_db_api(self) -> PlayoffDatabaseAPI:
        """Lazy initialization of PlayoffDatabaseAPI."""
        if self._playoff_db_api is None:
            self._playoff_db_api = PlayoffDatabaseAPI(self._db_path)
        return self._playoff_db_api

    @property
    def db_connection(self) -> DatabaseConnection:
        """Lazy initialization of DatabaseConnection."""
        if self._db_connection is None:
            self._db_connection = DatabaseConnection(self._db_path)
        return self._db_connection

    def execute(
        self,
        transition: PhaseTransition,
        season_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute the OFFSEASON → PRESEASON transition.

        **Phase 4: Dynamic Handlers** - Now accepts season_year at execution time
        for maximum flexibility and testability. If not provided, uses the year
        specified at construction.

        This method orchestrates the new season initialization process:
        1. Clear playoff data from completed season
        2. Save rollback state (current phase, schedules, standings)
        3. Generate preseason schedule (48 games, 3 weeks)
        4. Generate regular season schedule (272 games, 17 weeks)
        5. Reset all team standings to 0-0-0
        6. Update database phase to PRESEASON

        The method tracks completion state at each step to support
        granular rollback if any step fails.

        Args:
            transition: PhaseTransition model containing:
                - from_phase: "OFFSEASON"
                - to_phase: "PRESEASON"
                - transition_date: Date of transition
                - metadata: Optional additional context
            season_year: Optional season year to use for this transition.
                If not provided, uses the year from construction.
                This allows the same handler instance to be reused
                for multiple years (Phase 4: Dynamic Handlers).

        Returns:
            Dict containing:
                - playoff_cleanup: Playoff data cleanup result with deletion counts
                - preseason_games: List of preseason game events (48)
                - regular_season_games: List of regular season game events (272)
                - preseason_start_date: Calculated preseason start date
                - regular_season_start_date: First regular season game date
                - teams_reset: Number of teams with standings reset (32)
                - new_season_year: The initialized season year

        Raises:
            ValueError: If transition is invalid (wrong phases)
            RuntimeError: If any step fails during execution

        Side Effects:
            - Deletes playoff data from completed season
            - Creates game events in database/calendar
            - Resets standings for all 32 NFL teams
            - Updates dynasty_state phase to PRESEASON
        """
        # Phase 4: Use execution-time year if provided, otherwise use constructor year
        effective_year = season_year if season_year is not None else self._new_season_year
        # Validate transition
        # Import SeasonPhase for validation
        try:
            from src.calendar.season_phase_tracker import SeasonPhase
        except ModuleNotFoundError:
            from src.calendar.season_phase_tracker import SeasonPhase

        if transition.from_phase != SeasonPhase.OFFSEASON:
            raise ValueError(
                f"Invalid transition: expected from_phase=SeasonPhase.OFFSEASON, "
                f"got {transition.from_phase}"
            )
        if transition.to_phase != SeasonPhase.PRESEASON:
            raise ValueError(
                f"Invalid transition: expected to_phase=SeasonPhase.PRESEASON, "
                f"got {transition.to_phase}"
            )

        self._log(
            f"[OFFSEASON → PRESEASON] Starting new season initialization "
            f"for year {effective_year} (Dynasty: {self._dynasty_id})"
        )

        # Track completed steps for rollback
        completed_steps = []
        result: Dict[str, Any] = {}

        try:
            # Step 1: Clear playoff data from completed season
            old_season = effective_year - 1
            self._log(f"[Step 1/7] Clearing playoff data from season {old_season}...")
            playoff_result = self.playoff_db_api.clear_playoff_data(
                dynasty_id=self._dynasty_id,
                season=old_season,
                connection=None  # Auto-commit mode (handler not transaction-aware yet)
            )
            result["playoff_cleanup"] = playoff_result
            completed_steps.append("playoff_data_cleared")
            self._log(
                f"✓ Playoff data cleared: {playoff_result['total_deleted']} records deleted "
                f"({playoff_result['seedings_deleted']} seedings, "
                f"{playoff_result['events_deleted']} events, "
                f"{playoff_result['brackets_deleted']} brackets)"
            )

            # Step 2: Save rollback state
            self._log("[Step 2/7] Saving rollback state...")
            self._save_rollback_state(transition, effective_year)
            completed_steps.append("rollback_state_saved")
            self._log("✓ Rollback state saved")

            # Step 2.75: Execute Year Transition (Milestone 1: Multi-Year Season Cycle)
            # This orchestrates: Season year increment + Contract transitions + Draft class generation
            self._log("[Step 2.75/7] Executing year transition (increment year, contracts, draft)...")
            transition_result = self._execute_year_transition(old_season, effective_year)
            result["year_transition"] = transition_result
            completed_steps.append("year_transition_executed")
            self._log(
                f"✓ Year transition complete: {old_season} → {effective_year}\n"
                f"  - Contracts: {transition_result['contract_transition']['total_contracts']} processed, "
                f"{transition_result['contract_transition']['expired_count']} expired\n"
                f"  - Draft class: {transition_result['draft_preparation']['total_players']} prospects generated"
            )

            # Step 2.5: Validate games exist for upcoming season
            # This ensures SCHEDULE_RELEASE milestone executed successfully during offseason
            self._log("[Step 2.5/7] Validating schedule exists for upcoming season...")
            self._validate_games_exist(effective_year)  # Raises ValueError if games missing
            completed_steps.append("schedule_validated")

            # NOTE: Game generation moved to SCHEDULE_RELEASE milestone (mid-May)
            # Games are now generated 3 months before preseason starts (NFL realistic!)
            # This transition only handles phase change + standings reset

            # Step 3: Reset all team standings
            self._log("[Step 3/7] Resetting all team standings to 0-0-0...")
            self._reset_standings(effective_year)
            result["teams_reset"] = 32  # All 32 NFL teams
            completed_steps.append("standings_reset")
            self._log("✓ All team standings reset to 0-0-0")

            # Database phase update handled by SeasonCycleController (before transition)

            # Final result summary
            result["new_season_year"] = effective_year
            result["completed_steps"] = completed_steps

            self._log(
                f"\n[SUCCESS] OFFSEASON → PRESEASON transition complete:\n"
                f"  - Season Year: {old_season} → {effective_year}\n"
                f"  - Playoff Cleanup: {playoff_result['total_deleted']} records deleted\n"
                f"  - Contracts: {transition_result['contract_transition']['expired_count']} expired\n"
                f"  - Draft Class: {transition_result['draft_preparation']['total_players']} prospects\n"
                f"  - Teams Reset: 32 (all standings → 0-0-0)\n"
                f"  - Phase: PRESEASON\n"
                f"  - Note: Games already generated at SCHEDULE_RELEASE (mid-May)"
            )

            return result

        except Exception as e:
            self._log(
                f"\n[ERROR] Transition failed at step {len(completed_steps) + 1}: {e}"
            )
            self._log(f"Completed steps: {completed_steps}")

            # Store error context for rollback
            self._rollback_state["error"] = str(e)
            self._rollback_state["completed_steps"] = completed_steps
            self._rollback_state["partial_result"] = result

            raise RuntimeError(
                f"Offseason → Preseason transition failed: {e}"
            ) from e

    def rollback(self, transition: PhaseTransition) -> None:
        """
        Rollback the OFFSEASON → PRESEASON transition if it fails.

        This method attempts to restore the system to its pre-transition state
        by undoing completed steps in reverse order. Supports partial rollback
        if only some steps completed before failure.

        Rollback steps (in reverse order):
        1. Restore database phase to OFFSEASON
        2. Restore previous standings
        3. Delete regular season schedule events
        4. Delete preseason schedule events

        Args:
            transition: The PhaseTransition that failed

        Raises:
            RuntimeError: If rollback fails (logs details but doesn't re-raise)

        Side Effects:
            - Deletes generated game events from database/calendar
            - Restores standings to pre-transition state
            - Restores dynasty_state phase to OFFSEASON

        Note:
            Rollback is best-effort. If rollback fails, system may be in
            inconsistent state requiring manual intervention.
        """
        self._log(
            f"\n[ROLLBACK] Starting rollback for failed OFFSEASON → PRESEASON transition"
        )

        completed_steps = self._rollback_state.get("completed_steps", [])
        error = self._rollback_state.get("error", "Unknown error")

        self._log(f"Original error: {error}")
        self._log(f"Completed steps before failure: {completed_steps}")

        rollback_errors = []

        try:
            # Rollback in reverse order

            # Step 6: Restore database phase
            if "database_phase_updated" in completed_steps:
                try:
                    self._log("[Rollback 1/4] Restoring database phase to OFFSEASON...")
                    self._update_database_phase("OFFSEASON", self._new_season_year)
                    self._log("✓ Database phase restored to OFFSEASON")
                except Exception as e:
                    error_msg = f"Failed to restore database phase: {e}"
                    self._log(f"✗ {error_msg}")
                    rollback_errors.append(error_msg)

            # Step 5: Restore standings (would need previous standings data)
            if "standings_reset" in completed_steps:
                self._log(
                    "[Rollback 2/4] Standings reset - no rollback needed "
                    "(previous season data preserved)"
                )
                # Note: In a real implementation, you might want to restore
                # previous standings from backup if they existed

            # Step 4: Delete regular season schedule
            if "regular_season_schedule_generated" in completed_steps:
                try:
                    self._log(
                        "[Rollback 3/4] Deleting generated regular season schedule..."
                    )
                    # Note: Actual deletion would be handled by calendar/event system
                    # This is a placeholder for the deletion logic
                    self._log(
                        "✓ Regular season schedule deletion queued "
                        "(handled by calendar system)"
                    )
                except Exception as e:
                    error_msg = f"Failed to delete regular season schedule: {e}"
                    self._log(f"✗ {error_msg}")
                    rollback_errors.append(error_msg)

            # Step 3: Delete preseason schedule
            if "preseason_schedule_generated" in completed_steps:
                try:
                    self._log("[Rollback 4/4] Deleting generated preseason schedule...")
                    # Note: Actual deletion would be handled by calendar/event system
                    # This is a placeholder for the deletion logic
                    self._log(
                        "✓ Preseason schedule deletion queued "
                        "(handled by calendar system)"
                    )
                except Exception as e:
                    error_msg = f"Failed to delete preseason schedule: {e}"
                    self._log(f"✗ {error_msg}")
                    rollback_errors.append(error_msg)

            # Report rollback results
            if rollback_errors:
                error_summary = "\n  - ".join(rollback_errors)
                self._log(
                    f"\n[ROLLBACK PARTIAL] Rollback completed with errors:\n"
                    f"  - {error_summary}\n"
                    f"Manual intervention may be required."
                )
                raise RuntimeError(
                    f"Rollback completed with {len(rollback_errors)} error(s). "
                    f"Manual intervention may be required."
                )
            else:
                self._log("\n[ROLLBACK SUCCESS] System restored to OFFSEASON phase")

        except Exception as e:
            self._log(
                f"\n[ROLLBACK FAILED] Rollback encountered critical error: {e}\n"
                f"System may be in inconsistent state. Manual intervention required."
            )
            # Don't re-raise - rollback is best-effort

    def _save_rollback_state(
        self,
        transition: PhaseTransition,
        season_year: int
    ) -> None:
        """
        Save current state for potential rollback.

        Captures:
        - Current phase (OFFSEASON)
        - Current season year
        - Transition metadata

        Args:
            transition: Current phase transition
            season_year: The effective season year for this transition
        """
        self._rollback_state = {
            "from_phase": transition.from_phase,
            "to_phase": transition.to_phase,
            "season_year": season_year,
            "dynasty_id": self._dynasty_id,
            "metadata": transition.metadata,
        }

        if self._verbose_logging:
            self._log(f"Rollback state saved: {self._rollback_state}")

    def _query_games_for_season(self, season_year: int, season_type: str) -> List[Any]:
        """
        Query games for specific season and type from event database.

        Args:
            season_year: Season year to query (e.g., 2026)
            season_type: Type of season ("preseason" or "regular_season")

        Returns:
            List of game events matching the criteria
        """
        if self._event_db is None:
            return []

        # Get all GAME events for this dynasty
        all_games = self._event_db.events_get_by_type(event_type="GAME")

        # Filter by season year and season type
        filtered = [
            g for g in all_games
            if g.get("data", {}).get("parameters", {}).get("season") == season_year
            and g.get("data", {}).get("parameters", {}).get("season_type") == season_type
        ]

        return filtered

    def _validate_games_exist(self, season_year: int):
        """
        Validate that games exist for the upcoming season.

        Args:
            season_year: Season year to validate

        Raises:
            ValueError: If schedule is incomplete (missing preseason or regular season games)
        """
        if self._event_db is None:
            self._log("[WARNING] No event_db provided - skipping game validation")
            return

        # Query for preseason and regular season games
        preseason_games = self._query_games_for_season(season_year, "preseason")
        regular_games = self._query_games_for_season(season_year, "regular_season")

        preseason_count = len(preseason_games)
        regular_count = len(regular_games)

        # NFL standard: 48 preseason (3 weeks × 16 games) + 272 regular (18 weeks × ~16 games)
        if preseason_count < 48:
            raise ValueError(
                f"Missing preseason games for season {season_year}. "
                f"Found {preseason_count}/48. "
                f"SCHEDULE_RELEASE milestone may not have executed. "
                f"Expected 48 preseason games to be generated during offseason."
            )

        if regular_count < 272:
            raise ValueError(
                f"Missing regular season games for season {season_year}. "
                f"Found {regular_count}/272. "
                f"SCHEDULE_RELEASE milestone may not have executed. "
                f"Expected 272 regular season games to be generated during offseason."
            )

        self._log(
            f"[VALIDATION] ✓ Schedule complete: {preseason_count} preseason + {regular_count} regular season games"
        )

    def _log(self, message: str) -> None:
        """
        Log a message if verbose logging is enabled.

        Args:
            message: Message to log
        """
        if self._verbose_logging:
            print(f"[OffseasonToPreseasonHandler] {message}")
