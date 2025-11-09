"""
Preseason to Regular Season Handler

Handles the transition from PRESEASON phase to REGULAR_SEASON phase.

This handler is responsible for:
1. Updating database to reflect regular_season phase
2. Logging the transition
3. Supporting rollback on failure

Architecture:
- Uses dependency injection for all external operations
- Maintains rollback state for transaction safety
- Provides detailed logging for debugging

Usage:
    handler = PreseasonToRegularSeasonHandler(
        update_database_phase=lambda phase: db.update_phase(phase),
        dynasty_id="my_dynasty",
        season_year=2024,
        verbose_logging=True
    )

    transition = PhaseTransition(from_phase="PRESEASON", to_phase="REGULAR_SEASON")
    result = handler.execute(transition)
"""

from typing import Any, Dict, Callable, Optional
import logging
from datetime import datetime

from ..models import PhaseTransition
from src.calendar.season_phase_tracker import SeasonPhase


class PreseasonToRegularSeasonHandler:
    """
    Handles PRESEASON → REGULAR_SEASON transition.

    This handler orchestrates the transition from preseason to regular season.
    It's a simple transition that primarily updates the phase state and logs
    the transition.

    Responsibilities:
    1. Update database phase to REGULAR_SEASON
    2. Log transition for debugging
    3. Support rollback if any step fails

    Attributes:
        _update_database_phase: Callable that updates database phase
        _dynasty_id: Dynasty identifier for isolation
        _season_year: Current season year
        _verbose_logging: Enable detailed logging output
        _rollback_state: Stored state for rollback operations
        _logger: Logger instance for this handler
    """

    def __init__(
        self,
        update_database_phase: Callable[[str], None],
        dynasty_id: str,
        season_year: int,
        verbose_logging: bool = False
    ):
        """
        Initialize PreseasonToRegularSeasonHandler with injectable dependencies.

        Args:
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
        if not update_database_phase:
            raise ValueError("update_database_phase callable is required")
        if not dynasty_id:
            raise ValueError("dynasty_id cannot be empty")
        if season_year < 1920:
            raise ValueError(f"Invalid season_year: {season_year} (must be >= 1920)")

        self._update_database_phase = update_database_phase
        self._dynasty_id = dynasty_id
        self._season_year = season_year
        self._verbose_logging = verbose_logging

        # State storage
        self._rollback_state: Dict[str, Any] = {}

        # Logger setup
        self._logger = logging.getLogger(__name__)
        if verbose_logging:
            self._logger.setLevel(logging.DEBUG)

    def execute(
        self,
        transition: PhaseTransition,
        season_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute PRESEASON → REGULAR_SEASON transition.

        **Phase 4: Dynamic Handlers** - Now accepts season_year at execution time
        for maximum flexibility and testability. If not provided, uses the year
        specified at construction.

        This method orchestrates the complete transition from preseason to regular season:
        1. Saves rollback state (current phase)
        2. Updates database phase to REGULAR_SEASON
        3. Logs completion

        The method is transactional - if any step fails, rollback can restore
        the previous state.

        Args:
            transition: PhaseTransition object containing from_phase and to_phase
            season_year: Optional season year to use for this transition.
                If not provided, uses the year from construction.
                This allows the same handler instance to be reused
                for multiple years (Phase 4: Dynamic Handlers).

        Returns:
            Dict containing transition results:
            {
                "success": True,
                "database_updated": True,
                "timestamp": "2024-09-05T12:00:00",
                "dynasty_id": "my_dynasty",
                "season_year": 2024
            }

        Raises:
            ValueError: If transition phases are invalid
            RuntimeError: If any transition step fails

        Example:
            >>> transition = PhaseTransition(from_phase="PRESEASON", to_phase="REGULAR_SEASON")
            >>> result = handler.execute(transition)
            >>> print(f"Success: {result['success']}")
            Success: True
        """
        # Phase 4: Use execution-time year if provided, otherwise use constructor year
        effective_year = season_year if season_year is not None else self._season_year

        self._log_info(
            f"Starting PRESEASON → REGULAR_SEASON transition for dynasty {self._dynasty_id}, "
            f"season {effective_year}"
        )

        # Validate transition
        if transition.from_phase != SeasonPhase.PRESEASON:
            raise ValueError(f"Invalid from_phase: {transition.from_phase.value} (expected PRESEASON)")
        if transition.to_phase != SeasonPhase.REGULAR_SEASON:
            raise ValueError(f"Invalid to_phase: {transition.to_phase.value} (expected REGULAR_SEASON)")

        try:
            # Step 1: Save rollback state
            self._save_rollback_state(transition)
            self._log_debug("Rollback state saved")

            # Step 2: Update database phase
            self._log_debug("Updating database phase to REGULAR_SEASON...")
            self._update_database_phase("REGULAR_SEASON")
            self._log_info("Database phase updated to REGULAR_SEASON")

            # Build result
            result = {
                "success": True,
                "database_updated": True,
                "timestamp": datetime.now().isoformat(),
                "dynasty_id": self._dynasty_id,
                "season_year": effective_year
            }

            self._log_info("PRESEASON → REGULAR_SEASON transition completed successfully")
            return result

        except Exception as e:
            self._log_error(f"Transition failed: {e}")
            raise RuntimeError(f"Failed to execute PRESEASON → REGULAR_SEASON transition: {e}") from e

    def rollback(self, transition: PhaseTransition) -> None:
        """
        Rollback PRESEASON → REGULAR_SEASON transition.

        This method attempts to restore the system to its pre-transition state
        if the transition fails. It uses the saved rollback state to restore
        the database phase.

        Rollback operations:
        1. Restore database phase to PRESEASON
        2. Clear rollback state

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
        self._log_info(f"Rolling back PRESEASON → REGULAR_SEASON transition for dynasty {self._dynasty_id}")

        try:
            # Restore database phase
            if "previous_phase" in self._rollback_state:
                previous_phase = self._rollback_state["previous_phase"]
                self._log_debug(f"Restoring database phase to {previous_phase}...")
                self._update_database_phase(previous_phase)
                self._log_info(f"Database phase restored to {previous_phase}")

            # Clear rollback state
            self._rollback_state.clear()
            self._log_debug("Rollback state cleared")

            self._log_info("Rollback completed successfully")

        except Exception as e:
            self._log_error(f"Rollback failed: {e}")
            raise RuntimeError(f"Failed to rollback PRESEASON → REGULAR_SEASON transition: {e}") from e

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
            self._logger.debug(f"[PreseasonToRegularSeasonHandler] {message}")

    def _log_info(self, message: str) -> None:
        """Log info message."""
        self._logger.info(f"[PreseasonToRegularSeasonHandler] {message}")

    def _log_error(self, message: str) -> None:
        """Log error message."""
        self._logger.error(f"[PreseasonToRegularSeasonHandler] {message}")
