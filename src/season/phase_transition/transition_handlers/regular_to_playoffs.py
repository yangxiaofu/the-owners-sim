"""
Regular Season to Playoffs Handler

Handles the transition from REGULAR_SEASON phase to PLAYOFFS phase.

This handler orchestrates the critical transition from regular season to playoffs by:
1. Retrieving final regular season standings from the database
2. Using the playoff seeder to create a valid playoff bracket
3. Creating a playoff controller with the seeded bracket
4. Updating the database to reflect the playoffs phase
5. Supporting rollback if any step fails

Dependencies are injected as callables to maintain testability and flexibility.
"""

from typing import Any, Dict, Callable, Optional
import logging
from ..models import PhaseTransition


class RegularToPlayoffsHandler:
    """
    Handles REGULAR_SEASON → PLAYOFFS transition.

    This handler is responsible for orchestrating the transition from the regular
    season to the playoffs. It retrieves final standings, seeds the playoff bracket,
    creates a playoff controller, and updates the database phase.

    Responsibilities:
    1. Get final regular season standings from database
    2. Seed playoff bracket using PlayoffSeeder
    3. Create playoff controller with seeded bracket
    4. Update database to PLAYOFFS phase
    5. Support rollback on failure

    Attributes:
        _get_standings: Callable to retrieve standings (dynasty_id, year) -> standings dict
        _seed_playoffs: Callable to seed playoffs (standings dict) -> seeding dict
        _create_playoff_controller: Callable to create controller (seeding dict) -> controller
        _update_database_phase: Callable to update database phase (phase_name) -> None
        _dynasty_id: Dynasty context for this handler
        _season_year: Season year for this handler
        _verbose_logging: Whether to enable verbose debug logging
        _rollback_data: Stored data for rollback operations
    """

    def __init__(
        self,
        get_standings: Callable[[str, int], Dict[str, Any]],
        seed_playoffs: Callable[[Dict[str, Any]], Dict[str, Any]],
        create_playoff_controller: Callable[[Dict[str, Any]], Any],
        update_database_phase: Callable[[str], None],
        dynasty_id: str,
        season_year: int,
        verbose_logging: bool = False
    ):
        """
        Initialize the regular season to playoffs transition handler.

        Args:
            get_standings: Function to retrieve standings from database.
                           Takes (dynasty_id: str, year: int) -> Dict[str, Any]
                           Should return standings data structure suitable for seeding.
            seed_playoffs: Function to seed playoff bracket from standings.
                          Takes (standings: Dict[str, Any]) -> Dict[str, Any]
                          Should return seeding data with team assignments per seed.
            create_playoff_controller: Function to create playoff controller.
                                      Takes (seeding: Dict[str, Any]) -> Any
                                      Should return initialized playoff controller instance.
            update_database_phase: Function to update database phase.
                                  Takes (phase_name: str) -> None
                                  Should persist phase change to database.
            dynasty_id: Dynasty context for this transition
            season_year: Season year for this transition
            verbose_logging: If True, enables detailed debug logging (default: False)

        Raises:
            ValueError: If dynasty_id is empty or season_year is invalid
        """
        if not dynasty_id:
            raise ValueError("dynasty_id cannot be empty")
        if season_year < 1920:  # NFL founded in 1920
            raise ValueError(f"Invalid season year: {season_year}")

        self._get_standings = get_standings
        self._seed_playoffs = seed_playoffs
        self._create_playoff_controller = create_playoff_controller
        self._update_database_phase = update_database_phase
        self._dynasty_id = dynasty_id
        self._season_year = season_year
        self._verbose_logging = verbose_logging
        self._rollback_data: Dict[str, Any] = {}
        self._logger = logging.getLogger(__name__)

    def execute(self, transition: PhaseTransition) -> Any:
        """
        Execute the REGULAR_SEASON → PLAYOFFS transition.

        This method orchestrates the full transition process:
        1. Saves rollback state (previous phase for recovery)
        2. Retrieves final regular season standings from database
        3. Seeds playoff bracket using the standings data
        4. Creates playoff controller with seeded bracket
        5. Updates database to PLAYOFFS phase

        The method follows a transactional approach where rollback data is saved
        before each operation to enable recovery if any step fails.

        Args:
            transition: PhaseTransition model containing transition metadata

        Returns:
            Any: The created playoff controller instance (ready for simulation)

        Raises:
            ValueError: If transition is invalid (wrong from_phase or to_phase)
            RuntimeError: If standings retrieval fails
            RuntimeError: If playoff seeding fails
            RuntimeError: If controller creation fails
            RuntimeError: If database update fails

        Example:
            >>> handler = RegularToPlayoffsHandler(...)
            >>> transition = PhaseTransition(from_phase="REGULAR_SEASON", to_phase="PLAYOFFS")
            >>> playoff_controller = handler.execute(transition)
            >>> # playoff_controller is now ready for playoff simulation
        """
        # Validate transition
        if transition.from_phase != "REGULAR_SEASON":
            raise ValueError(
                f"Invalid from_phase: {transition.from_phase}. "
                f"Expected 'REGULAR_SEASON'"
            )
        if transition.to_phase != "PLAYOFFS":
            raise ValueError(
                f"Invalid to_phase: {transition.to_phase}. "
                f"Expected 'PLAYOFFS'"
            )

        if self._verbose_logging:
            self._logger.info(
                f"Starting REGULAR_SEASON → PLAYOFFS transition for "
                f"dynasty '{self._dynasty_id}', season {self._season_year}"
            )

        # Step 1: Save rollback state
        self._rollback_data = {
            "previous_phase": transition.from_phase,
            "dynasty_id": self._dynasty_id,
            "season_year": self._season_year
        }

        if self._verbose_logging:
            self._logger.debug(f"Saved rollback state: {self._rollback_data}")

        try:
            # Step 2: Get final regular season standings
            if self._verbose_logging:
                self._logger.info(
                    f"Retrieving final standings for dynasty '{self._dynasty_id}', "
                    f"season {self._season_year}"
                )

            standings = self._get_standings(self._dynasty_id, self._season_year)

            if not standings:
                raise RuntimeError(
                    f"Failed to retrieve standings for dynasty '{self._dynasty_id}', "
                    f"season {self._season_year}. Standings data is empty."
                )

            if self._verbose_logging:
                self._logger.debug(f"Retrieved standings: {len(standings)} teams")

            # Step 3: Seed playoffs using standings
            if self._verbose_logging:
                self._logger.info("Seeding playoff bracket from standings")

            seeding = self._seed_playoffs(standings)

            if not seeding:
                raise RuntimeError(
                    "Playoff seeding failed. Seeding data is empty."
                )

            if self._verbose_logging:
                self._logger.debug(f"Playoff seeding complete: {seeding.keys()}")

            # Step 4: Create playoff controller with seeded bracket
            if self._verbose_logging:
                self._logger.info("Creating playoff controller with seeded bracket")

            playoff_controller = self._create_playoff_controller(seeding)

            if playoff_controller is None:
                raise RuntimeError(
                    "Failed to create playoff controller. Controller is None."
                )

            if self._verbose_logging:
                self._logger.debug("Playoff controller created successfully")

            # Step 5: Update database to PLAYOFFS phase
            if self._verbose_logging:
                self._logger.info("Updating database phase to PLAYOFFS")

            self._update_database_phase("PLAYOFFS")

            if self._verbose_logging:
                self._logger.info(
                    "REGULAR_SEASON → PLAYOFFS transition completed successfully"
                )

            return playoff_controller

        except Exception as e:
            self._logger.error(
                f"Failed to execute REGULAR_SEASON → PLAYOFFS transition: {e}"
            )
            # Note: Rollback is handled by the caller (TransitionOrchestrator)
            # We just re-raise the exception after logging
            raise

    def rollback(self, transition: PhaseTransition) -> None:
        """
        Rollback the REGULAR_SEASON → PLAYOFFS transition.

        This method attempts to reverse the transition by restoring the database
        to the REGULAR_SEASON phase. It uses the rollback data saved during
        execute() to restore the previous state.

        Rollback is a best-effort operation. If rollback fails, the system may be
        in an inconsistent state and may require manual intervention.

        Args:
            transition: PhaseTransition model containing transition metadata

        Raises:
            RuntimeError: If rollback data is missing or rollback fails

        Example:
            >>> handler = RegularToPlayoffsHandler(...)
            >>> try:
            ...     playoff_controller = handler.execute(transition)
            ... except Exception:
            ...     handler.rollback(transition)  # Restore previous state
        """
        if not self._rollback_data:
            raise RuntimeError(
                "Cannot rollback: No rollback data available. "
                "execute() may not have been called or rollback data was cleared."
            )

        previous_phase = self._rollback_data.get("previous_phase")

        if not previous_phase:
            raise RuntimeError(
                "Cannot rollback: previous_phase not found in rollback data"
            )

        if self._verbose_logging:
            self._logger.warning(
                f"Rolling back REGULAR_SEASON → PLAYOFFS transition. "
                f"Restoring phase to '{previous_phase}'"
            )

        try:
            # Restore database to previous phase
            self._update_database_phase(previous_phase)

            if self._verbose_logging:
                self._logger.info(
                    f"Rollback successful. Phase restored to '{previous_phase}'"
                )

            # Clear rollback data after successful rollback
            self._rollback_data.clear()

        except Exception as e:
            self._logger.error(
                f"Failed to rollback REGULAR_SEASON → PLAYOFFS transition: {e}"
            )
            self._logger.error(
                "System may be in an inconsistent state. Manual intervention may be required."
            )
            raise RuntimeError(
                f"Rollback failed: {e}. System may be in an inconsistent state."
            ) from e
