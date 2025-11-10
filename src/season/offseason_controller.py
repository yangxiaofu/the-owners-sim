"""
Offseason Controller

Manages daily operations during the offseason phase including event execution,
roster management, and calendar advancement.

This controller is part of the season cycle orchestration system and handles
the offseason phase after the Super Bowl concludes.
"""

import logging
from typing import Dict, Any, Optional

from src.calendar.calendar_component import CalendarComponent
from src.calendar.simulation_executor import SimulationExecutor
from src.calendar.phase_state import PhaseState
from src.events.event_database_api import EventDatabaseAPI


class OffseasonController:
    """
    Controller for offseason phase operations.

    Handles daily event execution during the offseason including:
    - Franchise tags
    - Free agency
    - Draft
    - Roster cuts
    - Offseason deadlines

    This controller is responsible for:
    - Executing scheduled offseason events
    - Advancing the calendar day-by-day
    - Tracking offseason progress
    - Preparing for phase transitions to next season
    """

    def __init__(
        self,
        calendar: CalendarComponent,
        event_db: EventDatabaseAPI,
        database_path: str,
        dynasty_id: str,
        season_year: int,
        phase_state: PhaseState,
        enable_persistence: bool = True,
        verbose_logging: bool = False,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize offseason controller.

        Args:
            calendar: Calendar component for date tracking
            event_db: Event database API for event queries
            database_path: Path to SQLite database
            dynasty_id: Unique dynasty identifier
            season_year: Current NFL season year
            phase_state: Shared phase state tracking current season phase
            enable_persistence: Whether to persist simulation results
            verbose_logging: Whether to print detailed progress messages
            logger: Optional logger instance
        """
        self.calendar = calendar
        self.event_db = event_db
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.season_year = season_year
        self.phase_state = phase_state
        self.enable_persistence = enable_persistence
        self.verbose_logging = verbose_logging
        self.logger = logger or logging.getLogger(__name__)

        # Track days simulated in offseason
        self.days_simulated = 0

    def advance_day(self) -> Dict[str, Any]:
        """
        Advance offseason by one day.

        Executes any scheduled offseason events for the current day and
        advances the calendar. Offseason events include franchise tags,
        free agency signings, draft selections, roster cuts, and deadlines.

        Returns:
            Dictionary with simulation results containing:
            - date: Current date (str)
            - games_played: Number of games (always 0 in offseason)
            - events_triggered: List of events executed
            - results: List of game results (always empty in offseason)
            - current_phase: Current season phase
            - phase_transition: Phase transition info if occurred
            - success: Whether advancement succeeded
            - message: Status message
        """
        # Execute any scheduled offseason events for this day
        try:
            current_date = self.calendar.get_current_date()

            if self.verbose_logging:
                print(f"\n[OFFSEASON_DAY] Advancing offseason day: {current_date}")

            # Create SimulationExecutor to trigger events
            executor = SimulationExecutor(
                calendar=self.calendar,
                event_db=self.event_db,
                database_path=self.database_path,
                dynasty_id=self.dynasty_id,
                enable_persistence=self.enable_persistence,
                season_year=self.season_year,
                phase_state=self.phase_state,
                verbose_logging=True,  # Enable diagnostic output for event filtering
            )

            # Simulate events for current day
            event_results = executor.simulate_day(current_date)

            # Advance calendar
            self.calendar.advance(1)
            self.days_simulated += 1

            if self.verbose_logging:
                print(
                    f"[OFFSEASON_DAY] Calendar advanced successfully to: {self.calendar.get_current_date()}"
                )

            # Note: Phase transitions are handled by SeasonCycleController
            # This controller only handles daily operations within offseason phase

            return {
                "date": str(current_date),
                "games_played": 0,
                "events_triggered": event_results.get("events_executed", []),
                "results": [],
                "current_phase": self.phase_state.phase.value,
                "phase_transition": None,  # Handled by parent controller
                "success": True,
                "message": f"Offseason day complete. {len(event_results.get('events_executed', []))} events triggered.",
            }

        except Exception as e:
            self.logger.error(f"Error during offseason day advancement: {e}")
            # Fallback to basic advancement
            self.calendar.advance(1)
            self.days_simulated += 1

            return {
                "date": str(self.calendar.get_current_date()),
                "games_played": 0,
                "results": [],
                "current_phase": "offseason",
                "phase_transition": None,
                "success": True,
                "message": "Season complete. No more games to simulate.",
            }

    def get_days_simulated(self) -> int:
        """Get number of days simulated in offseason."""
        return self.days_simulated

    def get_current_date(self) -> str:
        """Get current calendar date."""
        return str(self.calendar.get_current_date())
