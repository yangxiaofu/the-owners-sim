"""
Simulation Controller for The Owner's Sim UI

Mediates between UI and SeasonCycleController.
Manages simulation advancement (day/week) and state tracking.
"""

from typing import Dict, Any, Optional
from datetime import datetime, date
from PySide6.QtCore import QObject, Signal
import sys
import os
import logging

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from season.season_cycle_controller import SeasonCycleController

# Use try/except to handle both production and test imports
from src.calendar.date_models import Date
from src.calendar.season_phase_tracker import SeasonPhase
from src.config.simulation_settings import SimulationSettings
from src.events.event_database_api import EventDatabaseAPI

from ui.domain_models.simulation_data_model import SimulationDataModel

# Import fail-loud exceptions and validators (Phase 4)
from src.database.sync_exceptions import (
    CalendarSyncPersistenceException,
    CalendarSyncDriftException
)
from src.database.sync_validators import SyncValidator


class SimulationController(QObject):
    """
    Controller for season simulation operations.

    Wraps SeasonCycleController and provides UI-friendly API for:
    - Advancing simulation by day/week
    - Tracking current date and phase
    - Persisting simulation state to database
    - Emitting signals for UI updates

    Signals:
        date_changed: Emitted when simulation date advances
        games_played: Emitted after games are simulated
        phase_changed: Emitted when entering new phase (playoffs, offseason)
    """

    # Qt signals for UI updates
    date_changed = Signal(str)  # (date_str)
    games_played = Signal(list)  # (game_results)
    phase_changed = Signal(str, str)  # (old_phase, new_phase)

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize simulation controller.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier
            season: Current season year (optional, used only for new dynasty creation)
                    NOTE: After initialization, use the season property which proxies
                    to SimulationDataModel.season (SINGLE SOURCE OF TRUTH)
        """
        super().__init__()

        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self._initialization_season = season  # Only used for new dynasty creation

        # ============ SIMULATION SPEED SETTINGS ============
        # Read from centralized config (src/config/simulation_settings.py)
        # Change settings there to control performance vs realism tradeoffs
        self.fast_mode = SimulationSettings.SKIP_GAME_SIMULATION
        self.skip_transactions = SimulationSettings.SKIP_TRANSACTION_AI
        self.skip_offseason_events = SimulationSettings.SKIP_OFFSEASON_EVENTS
        # ===================================================

        # Phase 4: Setup logging for fail-loud validation
        self._logger = logging.getLogger(__name__)
        print(f"[DYNASTY_TRACE] SimulationController.__init__(): dynasty_id={dynasty_id}")

        # Domain model for state persistence and retrieval
        self.state_model = SimulationDataModel(db_path, dynasty_id, season)

        # Event database API for draft day detection
        self.event_db = EventDatabaseAPI(db_path)

        # Load current state from database FIRST (establishes current_date_str, current_phase, current_week)
        self._load_state()

        # Initialize season cycle controller with the loaded state
        self._init_season_controller()

        # Phase 4: Initialize sync validator (will be ready after season_controller init)
        self._sync_validator = None  # Initialized lazily when calendar_manager is available

    @property
    def season(self) -> int:
        """
        Current season year (proxied from state model).

        This property delegates to SimulationDataModel.season which is the
        SINGLE SOURCE OF TRUTH loaded from database via get_latest_state().

        Returns:
            int: Current season year from database
        """
        return self.state_model.season

    def _init_season_controller(self):
        """Initialize or restore SeasonCycleController using already-loaded state."""
        # Use the current_date_str that was already loaded by _load_state()
        # This ensures calendar and controller state are synchronized
        start_date = Date.from_string(self.current_date_str)

        # Convert loaded phase string to SeasonPhase enum
        # (SeasonPhase already imported at module level)
        if self.loaded_phase == 'PLAYOFFS' or self.loaded_phase == 'playoffs':
            initial_phase = SeasonPhase.PLAYOFFS
        elif self.loaded_phase == 'OFFSEASON' or self.loaded_phase == 'offseason':
            initial_phase = SeasonPhase.OFFSEASON
        elif self.loaded_phase == 'PRESEASON' or self.loaded_phase == 'preseason':
            initial_phase = SeasonPhase.PRESEASON
        else:
            initial_phase = SeasonPhase.REGULAR_SEASON

        # Pass initial_phase to constructor so it starts in correct phase
        # This prevents regular season game scheduling when loading mid-playoffs
        # Phase 2: No season_year parameter - SeasonCycleController loads from database (SINGLE SOURCE OF TRUTH)
        self.season_controller = SeasonCycleController(
            database_path=self.db_path,
            dynasty_id=self.dynasty_id,
            # season_year removed - Phase 2: loads from database automatically
            start_date=start_date,
            initial_phase=initial_phase,
            enable_persistence=True,
            verbose_logging=True,  # Enable for player stats debugging
            fast_mode=self.fast_mode,  # Skip game simulation
            skip_transactions=self.skip_transactions,  # Skip transaction AI
            skip_offseason_events=self.skip_offseason_events  # Skip offseason event processing
        )

        # No more manual phase synchronization needed - handled by constructor!

    def _get_state_from_db(self) -> Optional[Dict[str, Any]]:
        """
        Load current simulation state from database.

        Returns:
            Dict with current_date, current_phase, current_week or None
        """
        return self.state_model.get_state()

    def _get_sync_validator(self) -> SyncValidator:
        """
        Lazy initialization of sync validator.

        Returns:
            SyncValidator instance

        Raises:
            RuntimeError: If calendar manager not available
        """
        if not self._sync_validator:
            # Get calendar manager from season controller
            calendar_manager = getattr(self.season_controller, 'calendar_manager', None)

            if not calendar_manager:
                raise RuntimeError(
                    "Cannot create sync validator: calendar_manager not available. "
                    "Ensure SeasonCycleController is fully initialized."
                )

            self._sync_validator = SyncValidator(
                state_model=self.state_model,
                calendar_manager=calendar_manager,
                max_acceptable_drift=3  # 3 days threshold
            )

        return self._sync_validator

    def _save_state_to_db(
        self,
        current_date: str,
        current_phase: str,
        current_week: Optional[int] = None
    ):
        """
        Save current simulation state to database with fail-loud validation.

        This method implements the fix for CALENDAR-DRIFT-2025-001 by replacing
        silent failures with exceptions.

        Args:
            current_date: Date string (YYYY-MM-DD)
            current_phase: REGULAR_SEASON, PLAYOFFS, or OFFSEASON
            current_week: Current week number (optional)

        Raises:
            CalendarSyncPersistenceException: If database write fails
            CalendarSyncDriftException: If post-write verification detects drift

        Phase 4 Changes:
        - BEFORE: Printed error and returned None (silent failure)
        - AFTER: Raises CalendarSyncPersistenceException (fail-loud)
        """
        # Attempt database write
        success = self.state_model.save_state(
            current_date=current_date,
            current_phase=current_phase,
            current_week=current_week
        )

        # Phase 4: FAIL-LOUD instead of silent failure
        if not success:
            self._logger.error(
                f"Failed to persist dynasty state to database!\n"
                f"  Date: {current_date}\n"
                f"  Phase: {current_phase}\n"
                f"  Week: {current_week}\n"
                f"  Dynasty: {self.dynasty_id}"
            )

            # Raise exception instead of just printing
            raise CalendarSyncPersistenceException(
                operation="dynasty_state_update",
                sync_point="_save_state_to_db",
                state_info={
                    "current_date": current_date,
                    "current_phase": current_phase,
                    "current_week": current_week,
                    "dynasty_id": self.dynasty_id,
                    "season": self.season
                }
            )

        # Phase 4: Post-sync verification (optional but recommended)
        try:
            validator = self._get_sync_validator()
            post_result = validator.verify_post_sync(current_date, current_phase)

            if not post_result.valid:
                self._logger.warning(
                    f"Post-sync verification detected issues: {post_result.issues}"
                )

                # If drift detected, raise drift exception
                if post_result.drift > 0:
                    raise CalendarSyncDriftException(
                        calendar_date=post_result.actual_calendar_date,
                        db_date=current_date,
                        drift_days=post_result.drift,
                        sync_point="_save_state_to_db_post_verification",
                        state_info={
                            "expected_date": current_date,
                            "expected_phase": current_phase,
                            "actual_phase": post_result.actual_phase,
                            "dynasty_id": self.dynasty_id
                        }
                    )

        except RuntimeError:
            # Sync validator not available (calendar manager not initialized)
            # This is acceptable during early initialization
            self._logger.debug("Sync validator not available for post-sync verification")
            pass

    def _load_state(self):
        """Load and cache current state."""
        # Use model's initialize_state which handles validation and defaults
        state_info = self.state_model.initialize_state()

        # Cache state values for quick access
        self.current_date_str = state_info['current_date']
        self.current_week = state_info['current_week']

        # Cache loaded phase - will be applied to SeasonCycleController after it's created
        self.loaded_phase = state_info.get('current_phase', 'REGULAR_SEASON')

    def advance_day(self) -> Dict[str, Any]:
        """
        Advance simulation by 1 day.

        Executes all events scheduled for the day (games, deadlines, etc.),
        updates database state, and emits signals for UI refresh.

        Returns:
            Dictionary with:
            {
                "success": bool,
                "date": str,
                "phase": str,
                "games_played": int,
                "results": List[Dict],
                "message": str
            }
        """
        try:
            # Call season controller advance_day
            result = self.season_controller.advance_day()

            if result.get('success', False):
                # Extract date and phase
                new_date = result.get('date', self.current_date_str)
                new_phase = result.get('current_phase', self.season_controller.phase_state.phase.value)
                games = result.get('results', [])

                # Check for phase transition
                if new_phase != self.season_controller.phase_state.phase.value:
                    old_phase = self.season_controller.phase_state.phase.value
                    self.phase_changed.emit(old_phase, new_phase)

                # Update state
                self.current_date_str = new_date

                # Save to database
                self._save_state_to_db(new_date, new_phase, self.current_week)

                # Emit signals
                self.date_changed.emit(new_date)

                if games:
                    self.games_played.emit(games)

                return {
                    "success": True,
                    "date": new_date,
                    "phase": new_phase,
                    "games_played": len(games),
                    "results": games,
                    "message": f"Simulated {new_date}: {len(games)} games played"
                }
            else:
                return {
                    "success": False,
                    "date": self.current_date_str,
                    "phase": self.season_controller.phase_state.phase.value,
                    "games_played": 0,
                    "results": [],
                    "message": result.get('message', 'Simulation failed')
                }

        except Exception as e:
            return {
                "success": False,
                "date": self.current_date_str,
                "phase": self.season_controller.phase_state.phase.value,
                "games_played": 0,
                "results": [],
                "message": f"Error: {str(e)}"
            }

    def advance_week(self) -> Dict[str, Any]:
        """
        Advance simulation by 1 week.

        Returns:
            Dictionary with week summary
        """
        try:
            result = self.season_controller.advance_week()

            if result.get('success', False):
                new_date = result.get('date', self.current_date_str)
                new_phase = result.get('current_phase', self.season_controller.phase_state.phase.value)

                self.current_date_str = new_date

                # Increment week
                if self.season_controller.phase_state.phase.value == "regular_season":
                    self.current_week += 1

                self._save_state_to_db(new_date, new_phase, self.current_week)

                self.date_changed.emit(new_date)

                return result

            return result

        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

    def get_current_date(self) -> str:
        """
        Get current simulation date.

        Returns:
            Date string in YYYY-MM-DD format
        """
        return self.current_date_str

    def get_current_phase(self) -> str:
        """
        Get current season phase.

        Returns:
            "REGULAR_SEASON", "PLAYOFFS", or "OFFSEASON"
        """
        return self.season_controller.phase_state.phase.value

    def get_current_week(self) -> Optional[int]:
        """
        Get current week number (preseason and regular season).

        Returns:
            Week number or None if in playoffs/offseason
        """
        current_phase = self.season_controller.phase_state.phase.value
        # Show week number for both preseason and regular season
        if current_phase in ["preseason", "regular_season"]:
            return self.current_week
        return None

    def get_next_milestone_name(self) -> str:
        """
        Get display name for next offseason milestone.

        Returns:
            Display name for UI button (e.g., "Franchise Tags", "Free Agency", "Draft")
        """
        return self.season_controller.get_next_offseason_milestone_name()

    def check_for_draft_day_event(self) -> Optional[Dict[str, Any]]:
        """
        Check if today's date has a draft day event.

        This method allows the UI layer to intercept draft day events BEFORE
        simulation runs, enabling interactive draft dialog to launch.

        Returns:
            Event dict if draft day found, None otherwise:
            {
                'event_id': int,
                'event_type': 'DRAFT_DAY',
                'event_date': str,
                'season': int,
                'dynasty_id': str,
                ...
            }
        """
        try:
            current_date = self.get_current_date()

            # Query events for today
            events = self.event_db.get_events_by_date(
                date=current_date,
                dynasty_id=self.dynasty_id
            )

            # Check for draft day event
            for event in events:
                if event.get('event_type') == 'DRAFT_DAY':
                    self._logger.info(
                        f"Draft day event detected: {current_date}, season {event.get('season')}"
                    )
                    return event

            return None

        except Exception as e:
            self._logger.error(f"Error checking for draft day event: {e}")
            return None

    def advance_to_end_of_phase(self, progress_callback=None) -> Dict[str, Any]:
        """
        Simulate until end of current phase (phase transition detected).

        Stops at phase boundaries to give user control (review brackets, make decisions).

        Args:
            progress_callback: Optional callback(week_num, games_played) for progress updates

        Returns:
            Summary dict with simulation results:
            {
                'start_date': str,
                'end_date': str,
                'weeks_simulated': int,
                'total_games': int,
                'starting_phase': str,
                'ending_phase': str,
                'phase_transition': bool,
                'success': bool,
                'message': str
            }
        """
        try:
            # Call backend with progress callback
            summary = self.season_controller.simulate_to_phase_end(
                progress_callback=progress_callback
            )

            if summary.get('success', False):
                # Update cached state
                self.current_date_str = summary['end_date']

                # Save to database
                self._save_state_to_db(
                    self.current_date_str,
                    self.season_controller.phase_state.phase.value,
                    self.current_week
                )

                # Emit signals for UI refresh
                self.date_changed.emit(self.current_date_str)

                # Add friendly message
                # Detect if this is a milestone stop (offseason) vs phase completion
                if 'milestone_reached' in summary:
                    # Offseason milestone stop - show milestone name
                    summary['message'] = (
                        f"Stopped at: {summary['milestone_reached']}\n"
                        f"Milestone Date: {summary['milestone_date']}\n"
                        f"Days Advanced: {summary.get('days_simulated', 0)}"
                    )
                else:
                    # Phase completion - show phase name
                    phase_name = summary['starting_phase'].replace('_', ' ').title()
                    summary['message'] = (
                        f"{phase_name} complete! "
                        f"{summary['weeks_simulated']} weeks simulated, "
                        f"{summary['total_games']} games played."
                    )

            return summary

        except Exception as e:
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'start_date': self.current_date_str,
                'end_date': self.current_date_str,
                'weeks_simulated': 0,
                'total_games': 0,
                'starting_phase': self.season_controller.phase_state.phase.value,
                'ending_phase': self.season_controller.phase_state.phase.value,
                'phase_transition': False
            }

    def simulate_to_new_season(self) -> Dict[str, Any]:
        """
        Simulate remainder of current season (all phases) until new season starts.

        Completes all remaining phases (regular season → playoffs → offseason)
        and stops at the start of the next season.

        Returns:
            Summary dict with simulation results:
            {
                'start_date': str,
                'end_date': str,
                'weeks_simulated': int,
                'total_games': int,
                'starting_phase': str,
                'ending_phase': str,
                'success': bool,
                'message': str
            }
        """
        try:
            # Call backend method (no progress callback for now)
            summary = self.season_controller.simulate_to_new_season()

            if summary.get('success', False):
                # Update cached state
                self.current_date_str = summary['end_date']

                # Save to database
                self._save_state_to_db(
                    self.current_date_str,
                    summary['ending_phase'],
                    self.current_week
                )

                # Emit signal for UI refresh
                self.date_changed.emit(self.current_date_str)

            return summary

        except Exception as e:
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'start_date': self.current_date_str,
                'end_date': self.current_date_str,
                'weeks_simulated': 0,
                'total_games': 0,
                'starting_phase': self.season_controller.phase_state.phase.value,
                'ending_phase': self.season_controller.phase_state.phase.value
            }

    def get_simulation_state(self) -> Dict[str, Any]:
        """
        Get complete simulation state.

        Returns:
            Dict with date, phase, week, and other metadata
        """
        return {
            "date": self.current_date_str,
            "phase": self.season_controller.phase_state.phase.value,
            "week": self.current_week,
            "season": self.season,  # Uses property (SSOT from database)
            "dynasty_id": self.dynasty_id
        }

    def get_transaction_debug_data(self) -> list:
        """
        Get collected transaction AI debug data from last simulation.

        Returns debug information collected during daily transaction evaluation,
        including probability calculations, proposal generation details, and
        filter results for all 32 teams.

        Returns:
            List of debug data dicts (one per team evaluation), empty list if no data
        """
        try:
            # Access TransactionAIManager through season_controller
            if hasattr(self.season_controller, '_transaction_ai'):
                return self.season_controller._transaction_ai._debug_data
        except Exception as e:
            print(f"[WARNING] Failed to get transaction debug data: {e}")

        return []

    def clear_transaction_debug_data(self) -> None:
        """
        Clear transaction AI debug data.

        Call this after viewing debug logs to prevent memory buildup
        during long simulations.
        """
        try:
            # Access TransactionAIManager through season_controller
            if hasattr(self.season_controller, '_transaction_ai'):
                self.season_controller._transaction_ai.clear_debug_data()
        except Exception as e:
            print(f"[WARNING] Failed to clear transaction debug data: {e}")
