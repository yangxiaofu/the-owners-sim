"""
Playoffs to Offseason Handler

Handles the transition from PLAYOFFS phase to OFFSEASON phase.

This handler is responsible for:
1. Determining the Super Bowl champion
2. Generating comprehensive season summary (champion, final standings, awards)
3. Scheduling offseason events (draft, free agency, training camp, etc.)
4. Updating database to reflect offseason phase
5. Supporting rollback on failure

Architecture:
- Uses dependency injection for all external operations
- Maintains rollback state for transaction safety
- Provides detailed logging for debugging
- Stores season summary for later retrieval

Usage:
    handler = PlayoffsToOffseasonHandler(
        get_super_bowl_winner=lambda: playoff_controller.get_champion(),
        schedule_offseason_events=lambda year: event_scheduler.schedule_offseason(year),
        generate_season_summary=lambda: summarizer.generate_summary(),
        update_database_phase=lambda phase: db.update_phase(phase),
        dynasty_id="my_dynasty",
        season_year=2024,
        verbose_logging=True
    )

    transition = PhaseTransition(from_phase="PLAYOFFS", to_phase="OFFSEASON")
    result = handler.execute(transition)
    print(f"Champion: {result['champion_team_id']}")
"""

from typing import Any, Dict, Callable, Optional
import logging
from datetime import datetime

from ..models import PhaseTransition


class PlayoffsToOffseasonHandler:
    """
    Handles PLAYOFFS → OFFSEASON transition.

    This handler orchestrates the end of the playoff phase and the beginning
    of the offseason. It captures the season's conclusion (Super Bowl winner),
    generates a comprehensive season summary, and schedules all offseason events
    (draft, free agency, training camp, etc.).

    Responsibilities:
    1. Determine Super Bowl winner from playoff results
    2. Generate season summary (champion, final standings, playoff results, awards)
    3. Schedule offseason events (draft, free agency, training camp deadlines)
    4. Update database phase to OFFSEASON
    5. Support rollback if any step fails

    Attributes:
        _get_super_bowl_winner: Callable that returns Super Bowl champion team ID
        _schedule_offseason_events: Callable that schedules offseason events for given year
        _generate_season_summary: Callable that generates comprehensive season summary
        _update_database_phase: Callable that updates database phase
        _dynasty_id: Dynasty identifier for isolation
        _season_year: Current season year
        _verbose_logging: Enable detailed logging output
        _season_summary: Stored season summary (None until execute runs)
        _rollback_state: Stored state for rollback operations
        _logger: Logger instance for this handler
    """

    def __init__(
        self,
        get_super_bowl_winner: Callable[[], int],
        schedule_offseason_events: Callable[[int], None],
        generate_season_summary: Callable[[], Dict[str, Any]],
        update_database_phase: Callable[[str], None],
        dynasty_id: str,
        season_year: int,
        verbose_logging: bool = False
    ):
        """
        Initialize PlayoffsToOffseasonHandler with injectable dependencies.

        Args:
            get_super_bowl_winner: Callable that returns Super Bowl champion team ID
                Example: lambda: playoff_controller.get_super_bowl_winner()
            schedule_offseason_events: Callable that schedules offseason events for given year
                Example: lambda year: event_scheduler.schedule_offseason_events(year)
            generate_season_summary: Callable that generates comprehensive season summary
                Example: lambda: season_summarizer.generate_summary()
                Expected return format:
                {
                    "champion_team_id": 7,
                    "runner_up_team_id": 15,
                    "final_standings": [...],
                    "playoff_results": {...},
                    "awards": {...},
                    "season_stats": {...}
                }
            update_database_phase: Callable that updates database phase
                Example: lambda phase: dynasty_state_api.update_phase(phase)
            dynasty_id: Dynasty identifier for isolation
            season_year: Current season year (e.g., 2024)
            verbose_logging: Enable detailed logging output (default: False)

        Raises:
            ValueError: If any required callable is None
            ValueError: If dynasty_id is empty
            ValueError: If season_year is invalid (< 1920)
        """
        if not get_super_bowl_winner:
            raise ValueError("get_super_bowl_winner callable is required")
        if not schedule_offseason_events:
            raise ValueError("schedule_offseason_events callable is required")
        if not generate_season_summary:
            raise ValueError("generate_season_summary callable is required")
        if not update_database_phase:
            raise ValueError("update_database_phase callable is required")
        if not dynasty_id:
            raise ValueError("dynasty_id cannot be empty")
        if season_year < 1920:
            raise ValueError(f"Invalid season_year: {season_year} (must be >= 1920)")

        self._get_super_bowl_winner = get_super_bowl_winner
        self._schedule_offseason_events = schedule_offseason_events
        self._generate_season_summary = generate_season_summary
        self._update_database_phase = update_database_phase
        self._dynasty_id = dynasty_id
        self._season_year = season_year
        self._verbose_logging = verbose_logging

        # State storage
        self._season_summary: Optional[Dict[str, Any]] = None
        self._rollback_state: Dict[str, Any] = {}

        # Logger setup
        self._logger = logging.getLogger(__name__)
        if verbose_logging:
            self._logger.setLevel(logging.DEBUG)

    def execute(self, transition: PhaseTransition) -> Dict[str, Any]:
        """
        Execute PLAYOFFS → OFFSEASON transition.

        This method orchestrates the complete transition from playoffs to offseason:
        1. Saves rollback state (current phase)
        2. Determines Super Bowl winner
        3. Generates comprehensive season summary
        4. Schedules offseason events (draft, free agency, training camp)
        5. Updates database phase to OFFSEASON

        The method is transactional - if any step fails, rollback can restore
        the previous state.

        Args:
            transition: PhaseTransition object containing from_phase and to_phase

        Returns:
            Dict containing transition results:
            {
                "success": True,
                "champion_team_id": 7,
                "season_summary": {...},
                "offseason_events_scheduled": True,
                "database_updated": True,
                "timestamp": "2024-02-11T20:30:00"
            }

        Raises:
            ValueError: If transition phases are invalid
            RuntimeError: If any transition step fails

        Example:
            >>> transition = PhaseTransition(from_phase="PLAYOFFS", to_phase="OFFSEASON")
            >>> result = handler.execute(transition)
            >>> print(f"Champion: Team {result['champion_team_id']}")
            Champion: Team 7
        """
        self._log_info(f"Starting PLAYOFFS → OFFSEASON transition for dynasty {self._dynasty_id}")

        # Validate transition
        if transition.from_phase != "PLAYOFFS":
            raise ValueError(f"Invalid from_phase: {transition.from_phase} (expected PLAYOFFS)")
        if transition.to_phase != "OFFSEASON":
            raise ValueError(f"Invalid to_phase: {transition.to_phase} (expected OFFSEASON)")

        try:
            # Step 1: Save rollback state
            self._save_rollback_state(transition)
            self._log_debug("Rollback state saved")

            # Step 2: Determine Super Bowl winner
            champion_team_id = self._get_super_bowl_winner()
            self._log_info(f"Super Bowl champion: Team {champion_team_id}")

            if champion_team_id is None:
                raise RuntimeError("Failed to determine Super Bowl winner")

            # Step 3: Generate season summary
            self._log_debug("Generating season summary...")
            self._season_summary = self._generate_season_summary()

            if not self._season_summary:
                raise RuntimeError("Failed to generate season summary")

            self._log_info(
                f"Season summary generated: Champion={self._season_summary.get('champion_team_id')}, "
                f"Runner-up={self._season_summary.get('runner_up_team_id')}"
            )

            # Step 4: Schedule offseason events
            self._log_debug(f"Scheduling offseason events for {self._season_year}...")
            self._schedule_offseason_events(self._season_year)
            self._log_info("Offseason events scheduled successfully")

            # Step 5: Update database phase
            self._log_debug("Updating database phase to OFFSEASON...")
            self._update_database_phase("OFFSEASON")
            self._log_info("Database phase updated to OFFSEASON")

            # Build result
            result = {
                "success": True,
                "champion_team_id": champion_team_id,
                "season_summary": self._season_summary,
                "offseason_events_scheduled": True,
                "database_updated": True,
                "timestamp": datetime.now().isoformat(),
                "dynasty_id": self._dynasty_id,
                "season_year": self._season_year
            }

            self._log_info("PLAYOFFS → OFFSEASON transition completed successfully")
            return result

        except Exception as e:
            self._log_error(f"Transition failed: {e}")
            raise RuntimeError(f"Failed to execute PLAYOFFS → OFFSEASON transition: {e}") from e

    def rollback(self, transition: PhaseTransition) -> None:
        """
        Rollback PLAYOFFS → OFFSEASON transition.

        This method attempts to restore the system to its pre-transition state
        if the transition fails. It uses the saved rollback state to restore
        the database phase.

        Rollback operations:
        1. Restore database phase to PLAYOFFS
        2. Clear season summary
        3. Clear rollback state

        Note: This does NOT unschedule offseason events (they remain scheduled
        but inactive until the phase is transitioned again).

        Args:
            transition: PhaseTransition object containing from_phase and to_phase

        Raises:
            RuntimeError: If rollback fails

        Example:
            >>> try:
            ...     result = handler.execute(transition)
            ... except RuntimeError:
            ...     handler.rollback(transition)
            ...     print("Transition rolled back")
        """
        self._log_info(f"Rolling back PLAYOFFS → OFFSEASON transition for dynasty {self._dynasty_id}")

        try:
            # Restore database phase
            if "previous_phase" in self._rollback_state:
                previous_phase = self._rollback_state["previous_phase"]
                self._log_debug(f"Restoring database phase to {previous_phase}...")
                self._update_database_phase(previous_phase)
                self._log_info(f"Database phase restored to {previous_phase}")

            # Clear season summary
            self._season_summary = None
            self._log_debug("Season summary cleared")

            # Clear rollback state
            self._rollback_state.clear()
            self._log_debug("Rollback state cleared")

            self._log_info("Rollback completed successfully")

        except Exception as e:
            self._log_error(f"Rollback failed: {e}")
            raise RuntimeError(f"Failed to rollback PLAYOFFS → OFFSEASON transition: {e}") from e

    def get_season_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get the generated season summary.

        Returns the season summary that was generated during the execute() call.
        Returns None if execute() has not been called yet or if it failed.

        Returns:
            Dict containing season summary with keys:
            - champion_team_id: Super Bowl winner
            - runner_up_team_id: Super Bowl runner-up
            - final_standings: Final regular season standings
            - playoff_results: Complete playoff bracket results
            - awards: Season awards (MVP, OPOY, DPOY, etc.)
            - season_stats: League-wide statistics

            Returns None if no summary is available.

        Example:
            >>> result = handler.execute(transition)
            >>> summary = handler.get_season_summary()
            >>> if summary:
            ...     print(f"Champion: Team {summary['champion_team_id']}")
        """
        return self._season_summary

    def _save_rollback_state(self, transition: PhaseTransition) -> None:
        """
        Save rollback state before making changes.

        Stores the current phase so it can be restored if the transition fails.

        Args:
            transition: PhaseTransition object containing current phase info
        """
        self._rollback_state = {
            "previous_phase": transition.from_phase,
            "timestamp": datetime.now().isoformat()
        }
        self._log_debug(f"Rollback state: {self._rollback_state}")

    def _log_debug(self, message: str) -> None:
        """Log debug message if verbose logging is enabled."""
        if self._verbose_logging:
            self._logger.debug(f"[PlayoffsToOffseasonHandler] {message}")

    def _log_info(self, message: str) -> None:
        """Log info message."""
        self._logger.info(f"[PlayoffsToOffseasonHandler] {message}")

    def _log_error(self, message: str) -> None:
        """Log error message."""
        self._logger.error(f"[PlayoffsToOffseasonHandler] {message}")
