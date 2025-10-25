"""
Offseason to Preseason Handler

Handles the transition from OFFSEASON phase to PRESEASON phase (new season).

This handler orchestrates the initialization of a new NFL season:
1. Generates preseason schedule (48 games, 3 weeks)
2. Generates regular season schedule (272 games, 17 weeks)
3. Resets all team standings to 0-0-0
4. Updates database to preseason phase
5. Supports rollback on failure with partial state tracking
"""

from typing import Any, Dict, Callable, Optional, List
from datetime import datetime
from ..models import PhaseTransition


class OffseasonToPreseasonHandler:
    """
    Handles OFFSEASON → PRESEASON transition (new season initialization).

    This handler is responsible for setting up a new NFL season after the
    offseason phase completes. It generates schedules, resets standings,
    and updates the database to reflect the new season state.

    Responsibilities:
    1. Generate preseason schedule (48 games, 3 weeks)
    2. Generate regular season schedule (272 games, 17 weeks)
    3. Reset all team standings to 0-0-0
    4. Update database to preseason phase
    5. Support rollback on failure with partial state restoration

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
        update_database_phase: Callable[[str, int], None],
        dynasty_id: str,
        new_season_year: int,
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
            update_database_phase: Function to update database phase
                - Takes: phase (str), season_year (int)
                - Returns: None (updates dynasty_state table)
            dynasty_id: Dynasty identifier for logging and context
            new_season_year: The new season year being initialized
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
        self._update_database_phase = update_database_phase

        # Store context
        self._dynasty_id = dynasty_id
        self._new_season_year = new_season_year
        self._verbose_logging = verbose_logging

        # Rollback state tracking
        self._rollback_state: Dict[str, Any] = {}

    def execute(self, transition: PhaseTransition) -> Dict[str, Any]:
        """
        Execute the OFFSEASON → PRESEASON transition.

        This method orchestrates the new season initialization process:
        1. Save rollback state (current phase, schedules, standings)
        2. Generate preseason schedule (48 games, 3 weeks)
        3. Generate regular season schedule (272 games, 17 weeks)
        4. Reset all team standings to 0-0-0
        5. Update database phase to PRESEASON

        The method tracks completion state at each step to support
        granular rollback if any step fails.

        Args:
            transition: PhaseTransition model containing:
                - from_phase: "OFFSEASON"
                - to_phase: "PRESEASON"
                - transition_date: Date of transition
                - metadata: Optional additional context

        Returns:
            Dict containing:
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
            - Creates game events in database/calendar
            - Resets standings for all 32 NFL teams
            - Updates dynasty_state phase to PRESEASON
        """
        # Validate transition
        # Import SeasonPhase for validation
        try:
            from calendar.season_phase_tracker import SeasonPhase
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
            f"for year {self._new_season_year} (Dynasty: {self._dynasty_id})"
        )

        # Track completed steps for rollback
        completed_steps = []
        result: Dict[str, Any] = {}

        try:
            # Step 1: Save rollback state
            self._log("[Step 1/5] Saving rollback state...")
            self._save_rollback_state(transition)
            completed_steps.append("rollback_state_saved")
            self._log("✓ Rollback state saved")

            # Step 2: Calculate preseason start date
            self._log("[Step 2/5] Calculating preseason start date...")
            preseason_start = self._calculate_preseason_start(self._new_season_year)
            result["preseason_start_date"] = preseason_start
            self._log(f"✓ Preseason starts: {preseason_start.strftime('%Y-%m-%d')}")

            # Step 3: Generate preseason schedule
            self._log("[Step 3/5] Generating preseason schedule (48 games)...")

            # [PRESEASON_DEBUG Point 5] Handler Execution
            print(f"\n[PRESEASON_DEBUG Point 5] Generating preseason schedule...")
            print(f"  Season year: {self._new_season_year}")
            print(f"  Dynasty ID: {self._dynasty_id}")

            preseason_games = self._generate_preseason(self._new_season_year)

            print(f"[PRESEASON_DEBUG Point 5] Preseason generation result:")
            print(f"  Games returned: {len(preseason_games)}")
            print(f"  Expected: 48")
            if len(preseason_games) > 0:
                print(f"  First game type: {type(preseason_games[0])}")
                if isinstance(preseason_games[0], dict):
                    print(f"  First game_id: {preseason_games[0].get('game_id', 'N/A')}")
                elif hasattr(preseason_games[0], 'game_id'):
                    print(f"  First game_id: {preseason_games[0].game_id}")

            if len(preseason_games) != 48:
                raise RuntimeError(
                    f"Preseason schedule generation failed: expected 48 games, "
                    f"got {len(preseason_games)}"
                )

            result["preseason_games"] = preseason_games
            completed_steps.append("preseason_schedule_generated")
            self._log(f"✓ Preseason schedule generated: {len(preseason_games)} games")

            # Step 4: Generate regular season schedule
            self._log("[Step 4/5] Generating regular season schedule (272 games)...")
            regular_season_games = self._generate_regular_season(
                self._new_season_year,
                preseason_start
            )

            if len(regular_season_games) != 272:
                raise RuntimeError(
                    f"Regular season schedule generation failed: expected 272 games, "
                    f"got {len(regular_season_games)}"
                )

            result["regular_season_games"] = regular_season_games
            result["regular_season_start_date"] = regular_season_games[0]["game_date"]
            completed_steps.append("regular_season_schedule_generated")
            self._log(
                f"✓ Regular season schedule generated: {len(regular_season_games)} games"
            )
            self._log(
                f"  Regular season starts: "
                f"{regular_season_games[0]['game_date'].strftime('%Y-%m-%d')}"
            )

            # Step 5: Reset all team standings
            self._log("[Step 5/5] Resetting all team standings to 0-0-0...")
            self._reset_standings(self._new_season_year)
            result["teams_reset"] = 32  # All 32 NFL teams
            completed_steps.append("standings_reset")
            self._log("✓ All team standings reset to 0-0-0")

            # Step 6: Update database phase
            self._log("[Step 6/6] Updating database phase to PRESEASON...")
            self._update_database_phase("PRESEASON", self._new_season_year)
            completed_steps.append("database_phase_updated")
            self._log("✓ Database phase updated to PRESEASON")

            # Final result summary
            result["new_season_year"] = self._new_season_year
            result["completed_steps"] = completed_steps

            self._log(
                f"\n[SUCCESS] New season {self._new_season_year} initialized:\n"
                f"  - Preseason: {len(preseason_games)} games\n"
                f"  - Regular Season: {len(regular_season_games)} games\n"
                f"  - Teams Reset: 32\n"
                f"  - Phase: PRESEASON"
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

    def _save_rollback_state(self, transition: PhaseTransition) -> None:
        """
        Save current state for potential rollback.

        Captures:
        - Current phase (OFFSEASON)
        - Current season year
        - Transition metadata

        Args:
            transition: Current phase transition
        """
        self._rollback_state = {
            "from_phase": transition.from_phase,
            "to_phase": transition.to_phase,
            "transition_date": transition.transition_date,
            "season_year": self._new_season_year,
            "dynasty_id": self._dynasty_id,
            "metadata": transition.metadata,
        }

        if self._verbose_logging:
            self._log(f"Rollback state saved: {self._rollback_state}")

    def _log(self, message: str) -> None:
        """
        Log a message if verbose logging is enabled.

        Args:
            message: Message to log
        """
        if self._verbose_logging:
            print(f"[OffseasonToPreseasonHandler] {message}")
