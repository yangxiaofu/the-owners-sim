"""
Simulation Controller for The Owner's Sim UI

Mediates between UI and SeasonCycleController.
Manages simulation advancement (day/week) and state tracking.
"""

from typing import Dict, Any, Optional
from datetime import datetime, date
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QDialog
import sys
import os
import logging

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.season.season_cycle_controller import SeasonCycleController
from src.season.milestone_detector import MilestoneDetector

# Use try/except to handle both production and test imports
from src.calendar.date_models import Date
from src.calendar.season_phase_tracker import SeasonPhase
from src.config.simulation_settings import SimulationSettings
from src.events.event_database_api import EventDatabaseAPI

from ui.domain_models.simulation_data_model import SimulationDataModel
from ui.dialogs.calendar_sync_recovery_dialog import CalendarSyncRecoveryDialog

# Import fail-loud exceptions and validators (Phase 4)
from src.database.sync_exceptions import (
    CalendarSyncPersistenceException,
    CalendarSyncDriftException
)
from src.database.sync_validators import SyncValidator

# Import transaction context for atomic state persistence (ISSUE-003 fix)
from src.database.transaction_context import TransactionContext


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
    checkpoint_saved = Signal(int, str)  # (day_num, date_str) - for incremental persistence

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

        # Create milestone detector with injected dependencies for testability
        # Enable verbose=True to diagnose milestone detection issues
        self._milestone_detector = MilestoneDetector(
            get_current_date=self.get_current_date,
            get_current_phase=self.get_current_phase,
            get_events_for_date_range=self._query_events_for_date_range,
            dynasty_id=self.dynasty_id,
            verbose=True  # DIAGNOSTIC: Enable verbose logging for milestone detection
        )

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

        # DIAGNOSTIC LOGGING: Track milestone detection configuration
        print(f"\n[DEBUG UI] ===== SeasonCycleController Initialization =====")
        print(f"[DEBUG UI] skip_offseason_events value: {self.skip_offseason_events}")
        print(f"[DEBUG UI] SimulationSettings.SKIP_OFFSEASON_EVENTS: {SimulationSettings.SKIP_OFFSEASON_EVENTS}")
        print(f"[DEBUG UI] Initial phase: {initial_phase}")
        print(f"[DEBUG UI] Start date: {start_date}")
        print(f"[DEBUG UI] ====================================================\n")

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

    def _save_daily_checkpoint(
        self,
        day_num: int,
        day_result: Dict[str, Any]
    ) -> None:
        """
        Save checkpoint after each day of simulation.

        Implements incremental persistence to prevent data loss on mid-week failures.
        This method is called by the backend via checkpoint callback after each day
        is simulated during week advancement.

        Args:
            day_num: Day number (0-6) within the week
            day_result: Result dict from advance_day()

        Raises:
            CalendarSyncPersistenceException: Database write failed
            CalendarSyncDriftException: Post-save verification failed

        Implementation Notes:
            - Reuses existing _save_state_to_db() for fail-loud validation
            - Emits checkpoint_saved signal for UI progress tracking
            - Re-raises exceptions to abort week simulation on failure
        """
        try:
            # Extract state from day result
            new_date = day_result.get('date', self.get_current_date())
            new_phase = day_result.get('current_phase', self.get_current_phase())
            new_week = self.get_current_week()

            # Log checkpoint creation
            self._logger.info(
                f"Saving daily checkpoint {day_num + 1}/7: {new_date} (phase: {new_phase})"
            )

            # Use existing _save_state_to_db() method
            # This already has fail-loud validation and drift detection
            self._save_state_to_db(new_date, new_phase, new_week)

            # Emit progress signal (for UI progress bar)
            self.checkpoint_saved.emit(day_num + 1, new_date)

        except (CalendarSyncPersistenceException, CalendarSyncDriftException) as e:
            self._logger.error(
                f"Failed to save daily checkpoint {day_num + 1}/7: {e}",
                exc_info=True
            )
            # Re-raise - caller will handle recovery dialog
            raise

    def _save_state_to_db(
        self,
        current_date: str,
        current_phase: str,
        current_week: Optional[int] = None
    ):
        """
        Save current simulation state to database with fail-loud validation.

        This method implements the fix for CALENDAR-DRIFT-2025-001 (Phases 1-3)
        and ISSUE-003 (transaction boundary for atomicity).

        Database write failures now raise CalendarSyncPersistenceException instead
        of silently failing. All write operations execute within a transaction to
        ensure atomicity.

        Args:
            current_date: Date string (YYYY-MM-DD)
            current_phase: REGULAR_SEASON, PLAYOFFS, or OFFSEASON
            current_week: Current week number (optional)

        Raises:
            CalendarSyncPersistenceException: If database write fails
            CalendarSyncDriftException: If post-write verification detects drift

        Implementation Notes:
        - Phase 1: DynastyStateAPI.update_state() raises on DB errors
        - Phase 2: SimulationDataModel.save_state() propagates exceptions
        - Phase 3: Removed redundant return value checking (this method)
        - ISSUE-003 Fix: Transaction boundary ensures atomic writes
        """
        # Get database connection for transaction
        # Path: state_model -> dynasty_api -> db -> get_connection()
        db_connection = self.state_model.dynasty_api.db.get_connection()

        try:
            # Wrap state save in transaction for atomicity (ISSUE-003 fix)
            with TransactionContext(db_connection, mode='IMMEDIATE') as tx:
                # Attempt database write within transaction
                # Raises CalendarSyncPersistenceException on failure
                self.state_model.save_state(
                    current_date=current_date,
                    current_phase=current_phase,
                    current_week=current_week,
                    connection=db_connection
                )

                # Explicitly commit transaction on success
                tx.commit()

                self._logger.debug(
                    f"[TRANSACTION] Dynasty state persisted successfully: "
                    f"date={current_date}, phase={current_phase}, week={current_week}"
                )

        except Exception as e:
            # Transaction automatically rolls back on exception
            self._logger.error(
                f"[TRANSACTION] Database write failed, transaction rolled back: {e}"
            )
            raise  # Re-raise exception to maintain fail-loud behavior

        finally:
            # Close connection
            db_connection.close()

        # Post-sync verification to detect calendar-database drift
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

    def _execute_simulation_with_persistence(
        self,
        operation_name: str,
        backend_method: callable,
        hooks: Dict[str, Optional[callable]],
        extractors: Dict[str, callable],
        failure_dict_factory: callable
    ) -> Dict[str, Any]:
        """
        Template method for simulation operations with database persistence.

        This method eliminates 74% code duplication across 4 simulation methods
        by providing a common workflow with method-specific customization via hooks.

        Workflow:
        1. Call backend simulation method
        2. Extract state (date, phase) from result
        3. Update cached state
        4. Execute pre-save hook (week counter, phase checks, etc.)
        5. Persist state to database (with fail-loud validation)
        6. Execute post-save hook (emit signals)
        7. Return transformed result

        Args:
            operation_name: Operation name for logging (e.g., "advance_day")
            backend_method: Season controller method to call (e.g., self.season_controller.advance_day)
            hooks: Optional callbacks for method-specific logic:
                - 'pre_save': Called before database save, receives result dict
                - 'post_save': Called after successful save, receives result dict
            extractors: Required callbacks for data extraction:
                - 'extract_state': Extract (date, phase, week) from result -> (str, str, Optional[int])
                - 'build_success_result': Transform backend result to controller result -> Dict
            failure_dict_factory: Creates failure result dict from error message -> Dict

        Returns:
            Result dict from build_success_result or failure_dict_factory

        Raises:
            CalendarSyncPersistenceException: Database write failed
            CalendarSyncDriftException: Post-save verification detected drift
            Exception: Unexpected errors during simulation

        Example:
            result = self._execute_simulation_with_persistence(
                operation_name="advance_day",
                backend_method=self.season_controller.advance_day,
                hooks={
                    'pre_save': lambda r: self._check_phase_transition(r),
                    'post_save': lambda r: self._emit_day_signals(r)
                },
                extractors={
                    'extract_state': lambda r: (r['date'], r['phase'], self.get_current_week()),
                    'build_success_result': lambda r: {...}
                },
                failure_dict_factory=lambda msg: {'success': False, 'message': msg}
            )
        """
        try:
            # Step 1: Call backend simulation method
            result = backend_method()

            # Step 2: Check if backend operation succeeded
            if result.get('success', False):
                # Step 3: Extract state from result
                new_date, new_phase, new_week = extractors['extract_state'](result)

                # Step 4: Execute pre-save hook (method-specific logic, no cache updates)
                if hooks.get('pre_save'):
                    hooks['pre_save'](result)

                # Step 5: Persist state to database FIRST (may raise exceptions)
                # CRITICAL: Save BEFORE updating cache to prevent desynchronization
                self._save_state_to_db(new_date, new_phase, new_week)

                # Step 6: Update cached state ONLY after successful database save
                # If save failed, exception was raised and this line never executes
                self.current_date_str = new_date

                # Step 7: Execute post-save hook (signal emission)
                if hooks.get('post_save'):
                    hooks['post_save'](result)

                # Step 8: Build and return success result
                return extractors['build_success_result'](result)

            else:
                # Backend operation failed - return failure result
                message = result.get('message', 'Simulation failed')
                return failure_dict_factory(message)

        except (CalendarSyncPersistenceException, CalendarSyncDriftException) as e:
            # Calendar sync error - show recovery dialog to user
            self._logger.error(
                f"Calendar sync error in {operation_name}: {e}",
                exc_info=True
            )

            # Show recovery dialog with retry/reload/abort options
            dialog = CalendarSyncRecoveryDialog(e, parent=self.parent())

            if dialog.exec() == QDialog.Accepted:
                recovery_action = dialog.get_recovery_action()

                if recovery_action == "retry":
                    # User chose to retry - recursively call this method again
                    self._logger.info(f"User chose to retry {operation_name} operation")
                    return self._execute_simulation_with_persistence(
                        operation_name, backend_method, hooks, extractors, failure_dict_factory
                    )

                elif recovery_action == "reload":
                    # User chose to reload - revert to database state
                    self._logger.info("User chose to reload state from database")
                    self._load_state()
                    return failure_dict_factory(
                        "State reloaded from database - calendar sync error prevented"
                    )

            # User aborted or closed dialog
            self._logger.warning(f"User aborted {operation_name} after calendar sync error")
            return failure_dict_factory("Calendar sync error - operation aborted")

        except Exception as e:
            # Unexpected error - show critical error dialog
            self._logger.error(f"Unexpected error in {operation_name}: {e}", exc_info=True)
            QMessageBox.critical(
                self.parent(),
                "Critical Error",
                f"Unexpected error during {operation_name}:\n\n{str(e)}\n\n"
                f"The operation has been aborted."
            )
            return failure_dict_factory(f"Error: {str(e)}")

    def _load_state(self):
        """Load and cache current state."""
        # Use model's initialize_state which handles validation and defaults
        state_info = self.state_model.initialize_state()

        # Cache state values for quick access
        self.current_date_str = state_info['current_date']
        # Note: current_week is no longer cached - use get_current_week() to query from schedule

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
        # Define state extraction
        def extract_state(result: Dict) -> tuple:
            new_date = result.get('date', self.current_date_str)
            new_phase = result.get('current_phase', self.season_controller.phase_state.phase.value)
            current_week = self.get_current_week()  # Query from schedule database
            return (new_date, new_phase, current_week)

        # Define pre-save hook for phase transition detection
        def pre_save_hook(result: Dict) -> None:
            new_phase = result.get('current_phase', self.season_controller.phase_state.phase.value)
            if new_phase != self.season_controller.phase_state.phase.value:
                old_phase = self.season_controller.phase_state.phase.value
                self.phase_changed.emit(old_phase, new_phase)

        # Define post-save hook for signal emission
        def post_save_hook(result: Dict) -> None:
            new_date = result.get('date', self.current_date_str)
            self.date_changed.emit(new_date)

            games = result.get('results', [])
            if games:
                self.games_played.emit(games)

        # Define success result builder
        def build_success_result(result: Dict) -> Dict[str, Any]:
            new_date = result.get('date', self.current_date_str)
            new_phase = result.get('current_phase', self.season_controller.phase_state.phase.value)
            games = result.get('results', [])

            return {
                "success": True,
                "date": new_date,
                "phase": new_phase,
                "games_played": len(games),
                "results": games,
                "message": f"Simulated {new_date}: {len(games)} games played"
            }

        # Define failure result factory
        def failure_dict_factory(message: str) -> Dict[str, Any]:
            return {
                "success": False,
                "date": self.current_date_str,
                "phase": self.season_controller.phase_state.phase.value,
                "games_played": 0,
                "results": [],
                "message": message
            }

        # Execute using template method
        return self._execute_simulation_with_persistence(
            operation_name="advance_day",
            backend_method=self.season_controller.advance_day,
            hooks={
                'pre_save': pre_save_hook,
                'post_save': post_save_hook
            },
            extractors={
                'extract_state': extract_state,
                'build_success_result': build_success_result
            },
            failure_dict_factory=failure_dict_factory
        )

    def advance_week(self) -> Dict[str, Any]:
        """
        Advance simulation by 1 week with daily checkpoints.

        Implements incremental persistence by saving state after each day
        via checkpoint callback to backend. This prevents data loss on
        mid-week failures.

        Returns:
            Dictionary with week summary
        """
        # Define checkpoint callback for incremental persistence
        def checkpoint_callback(day_num: int, day_result: Dict[str, Any]) -> None:
            """Called by backend after each day is simulated."""
            self._save_daily_checkpoint(day_num, day_result)

        # DIAGNOSTIC LOGGING: Track milestone detection before advance_week
        current_phase = self.season_controller.get_current_phase()
        print(f"\n[DEBUG UI] ===== Before advance_week() =====")
        print(f"[DEBUG UI] Current date: {self.current_date_str}")
        print(f"[DEBUG UI] Current phase: {current_phase.value if current_phase else 'None'}")
        print(f"[DEBUG UI] skip_offseason_events: {self.season_controller.skip_offseason_events}")
        print(f"[DEBUG UI] ======================================\n")

        try:
            # Call backend with checkpoint callback
            result = self.season_controller.advance_week(
                checkpoint_callback=checkpoint_callback
            )

            # Final cache update
            if result.get('success', False):
                new_date = result.get('date', self.current_date_str)
                self.current_date_str = new_date

                # Emit date changed signal
                self.date_changed.emit(new_date)

            return result

        except (CalendarSyncPersistenceException, CalendarSyncDriftException) as e:
            # Calendar sync error during checkpoint - show recovery dialog
            self._logger.error(
                f"Calendar sync error during week simulation: {e}",
                exc_info=True
            )

            # Show recovery dialog with retry/reload/abort options
            dialog = CalendarSyncRecoveryDialog(e, parent=self.parent())

            if dialog.exec() == QDialog.Accepted:
                recovery_action = dialog.get_recovery_action()

                if recovery_action == "retry":
                    # User chose to retry - recursively call this method again
                    self._logger.info(f"User chose to retry week simulation")
                    return self.advance_week()

                elif recovery_action == "reload":
                    # User chose to reload - revert to database state
                    self._logger.info("User chose to reload state from database")
                    self._load_state()
                    return {
                        'success': False,
                        'message': 'State reloaded from database - week simulation aborted'
                    }

            # User aborted or closed dialog
            self._logger.warning(f"User aborted week simulation after calendar sync error")
            return {
                'success': False,
                'message': 'Calendar sync error - week simulation aborted'
            }

        except Exception as e:
            # Unexpected error - show critical error dialog
            self._logger.error(f"Unexpected error during week simulation: {e}", exc_info=True)
            QMessageBox.critical(
                self.parent(),
                "Critical Error",
                f"Unexpected error during week simulation:\n\n{str(e)}\n\n"
                f"The operation has been aborted."
            )
            return {
                'success': False,
                'message': f"Error: {str(e)}"
            }

    def advance_days(self, num_days: int) -> Dict[str, Any]:
        """
        Advance simulation by exactly N days with daily checkpoints.

        Unlike advance_week(), this method does NOT check for milestones or stop early.
        It simulates exactly the specified number of days, only stopping for phase
        transitions. Used by UI layer for fine-grained simulation control.

        Args:
            num_days: Number of days to simulate (1-365)

        Returns:
            Dictionary with simulation results:
            {
                'success': bool,
                'days_simulated': int,
                'date': str,
                'current_phase': str,
                'games_played': int,
                'num_trades': int,
                'phase_transition': Optional[Dict],
                'message': str
            }

        Raises:
            ValueError: If num_days < 1 or > 365

        Examples:
            # Simulate 3 days before Draft Day
            result = controller.advance_days(3)

            # Then handle Draft Day in UI
            # Then simulate 4 more days
            result = controller.advance_days(4)
        """
        # Define checkpoint callback for incremental persistence
        def checkpoint_callback(day_num: int, day_result: Dict[str, Any]) -> None:
            """Called by backend after each day is simulated."""
            self._save_daily_checkpoint(day_num, day_result)

        try:
            # Call backend with checkpoint callback
            result = self.season_controller.advance_days(
                num_days=num_days,
                checkpoint_callback=checkpoint_callback
            )

            # Final cache update
            if result.get('success', False):
                new_date = result.get('date', self.current_date_str)
                self.current_date_str = new_date

                # Emit date changed signal
                self.date_changed.emit(new_date)

            return result

        except (CalendarSyncPersistenceException, CalendarSyncDriftException) as e:
            # Calendar sync error during checkpoint - show recovery dialog
            self._logger.error(
                f"Calendar sync error during day simulation: {e}",
                exc_info=True
            )

            # Show recovery dialog with retry/reload/abort options
            dialog = CalendarSyncRecoveryDialog(e, parent=self.parent())

            if dialog.exec() == QDialog.Accepted:
                recovery_action = dialog.get_recovery_action()

                if recovery_action == "retry":
                    # User chose to retry - recursively call this method again
                    self._logger.info(f"User chose to retry {num_days}-day simulation")
                    return self.advance_days(num_days)

                elif recovery_action == "reload":
                    # User chose to reload - revert to database state
                    self._logger.info("User chose to reload state from database")
                    self._load_state()
                    return {
                        'success': False,
                        'message': f'State reloaded from database - {num_days}-day simulation aborted'
                    }

            # User aborted or closed dialog
            self._logger.warning(f"User aborted {num_days}-day simulation after calendar sync error")
            return {
                'success': False,
                'message': f'Calendar sync error - {num_days}-day simulation aborted'
            }

        except ValueError as e:
            # Invalid num_days parameter
            self._logger.error(f"Invalid num_days parameter: {e}")
            return {
                'success': False,
                'message': f"Invalid parameter: {str(e)}"
            }

        except Exception as e:
            # Unexpected error - show critical error dialog
            self._logger.error(f"Unexpected error during {num_days}-day simulation: {e}", exc_info=True)
            QMessageBox.critical(
                self.parent(),
                "Critical Error",
                f"Unexpected error during {num_days}-day simulation:\n\n{str(e)}\n\n"
                f"The operation has been aborted."
            )
            return {
                'success': False,
                'message': f"Error: {str(e)}"
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
        Get current week number by querying schedule database.

        Week numbers are derived from the schedules table, which maps dates to weeks.
        This eliminates manual tracking and ensures accuracy across all phases.

        Returns:
            Week number for preseason/regular season, None for playoffs/offseason
        """
        return self.state_model.get_current_week()

    def get_next_milestone_name(self) -> str:
        """
        Get display name for next offseason milestone.

        Returns:
            Display name for UI button (e.g., "Franchise Tags", "Free Agency", "Draft")
        """
        return self.season_controller.get_next_offseason_milestone_name()

    def get_next_milestone_action(self) -> Dict[str, Any]:
        """
        Get detailed action information for next offseason milestone button.

        Returns structured action data including button text, tooltip, enabled state,
        and contextual information (milestone date, days remaining, etc.).

        Returns:
            Dict with action information for UI button configuration
        """
        return self.season_controller.get_next_milestone_action()

    def _query_events_for_date_range(
        self,
        dynasty_id: str,
        start_timestamp_ms: int,
        end_timestamp_ms: int
    ) -> list:
        """
        Query events for a date range via EventDatabaseAPI.

        This is a thin wrapper around event_db.get_events_by_dynasty_and_timestamp()
        to provide the correct function signature for MilestoneDetector dependency injection.

        Args:
            dynasty_id: Dynasty identifier
            start_timestamp_ms: Start timestamp in milliseconds
            end_timestamp_ms: End timestamp in milliseconds

        Returns:
            List of event dicts from database
        """
        return self.event_db.get_events_by_dynasty_and_timestamp(
            dynasty_id=dynasty_id,
            start_timestamp_ms=start_timestamp_ms,
            end_timestamp_ms=end_timestamp_ms
        )

    def check_for_draft_day_event(self) -> Optional[Dict[str, Any]]:
        """
        Check if today's date has a draft day event that hasn't been executed yet.

        This method allows the UI layer to intercept draft day events BEFORE
        simulation runs, enabling interactive draft dialog to launch.

        Returns:
            Draft day event dict if found and not yet executed, None otherwise:
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

            # Query events for today using timestamp range
            from datetime import datetime
            start_dt = datetime.fromisoformat(current_date)
            end_dt = datetime.fromisoformat(f"{current_date}T23:59:59")
            start_ms = int(start_dt.timestamp() * 1000)
            end_ms = int(end_dt.timestamp() * 1000)

            events = self.event_db.get_events_by_dynasty_and_timestamp(
                dynasty_id=self.dynasty_id,
                start_timestamp_ms=start_ms,
                end_timestamp_ms=end_ms,
                event_type="DRAFT_DAY"
            )

            # Check for draft day event
            for event in events:
                if event.get('event_type') == 'DRAFT_DAY':
                    # Skip if already executed (results field populated)
                    if event.get('data', {}).get('results') is not None:
                        self._logger.info(f"Draft day event already executed, skipping")
                        continue

                    self._logger.info(
                        f"Draft day event detected: {current_date}, season {event.get('season')}"
                    )
                    return event

            return None

        except Exception as e:
            self._logger.error(f"Error checking for draft day event: {e}")
            return None

    def check_for_interactive_event(self) -> Optional[Dict[str, Any]]:
        """
        Check if today's date has ANY interactive milestone event.

        Interactive events pause simulation and require user interaction before proceeding.
        This includes:
        - DRAFT_DAY (already handled separately)
        - DEADLINE events: FRANCHISE_TAG, FINAL_ROSTER_CUTS, SALARY_CAP_COMPLIANCE
        - WINDOW events: FREE_AGENCY start

        This method allows the UI layer to intercept these events BEFORE simulation runs,
        enabling interactive dialogs to launch.

        Returns:
            Event dict if interactive event found, None otherwise:
            {
                'event_id': int,
                'event_type': str,
                'event_date': str,
                'data': {
                    'parameters': {
                        'deadline_type': str,  # for DEADLINE events
                        'window_name': str,    # for WINDOW events
                        'window_type': str     # for WINDOW events (START/END)
                    }
                },
                ...
            }
        """
        # Define which event types and subtypes are interactive
        INTERACTIVE_DEADLINE_TYPES = {
            'FRANCHISE_TAG',
            'FINAL_ROSTER_CUTS',
            'SALARY_CAP_COMPLIANCE'
        }

        INTERACTIVE_WINDOW_NAMES = {
            'FREE_AGENCY'  # Only START events, not END
        }

        try:
            current_date = self.get_current_date()

            # Query events for today using timestamp range
            from datetime import datetime
            start_dt = datetime.fromisoformat(current_date)
            end_dt = datetime.fromisoformat(f"{current_date}T23:59:59")
            start_ms = int(start_dt.timestamp() * 1000)
            end_ms = int(end_dt.timestamp() * 1000)

            events = self.event_db.get_events_by_dynasty_and_timestamp(
                dynasty_id=self.dynasty_id,
                start_timestamp_ms=start_ms,
                end_timestamp_ms=end_ms
            )

            # Check for interactive events
            for event in events:
                event_type = event.get('event_type')

                # Skip if already executed (results field populated)
                data = event.get('data', {})
                if data.get('results') is not None:
                    self._logger.debug(f"Event {event_type} already executed, skipping")
                    continue

                # Draft day (handled separately but included for completeness)
                if event_type == 'DRAFT_DAY':
                    return event

                # Deadline events (franchise tag, roster cuts, cap compliance)
                if event_type == 'DEADLINE':
                    params = data.get('parameters', {})
                    deadline_type = params.get('deadline_type')
                    if deadline_type in INTERACTIVE_DEADLINE_TYPES:
                        self._logger.info(
                            f"Interactive deadline event detected: {deadline_type} on {current_date}"
                        )
                        return event

                # Window events (free agency start)
                if event_type == 'WINDOW':
                    params = data.get('parameters', {})
                    window_name = params.get('window_name')
                    window_type = params.get('window_type')
                    if window_name in INTERACTIVE_WINDOW_NAMES and window_type == 'START':
                        self._logger.info(
                            f"Interactive window event detected: {window_name} {window_type} on {current_date}"
                        )
                        return event

            return None

        except Exception as e:
            self._logger.error(f"Error checking for interactive event: {e}")
            return None

    def check_upcoming_milestones(self, days_ahead: int = 7) -> Optional[Dict[str, Any]]:
        """
        Check if any interactive milestones exist in the next N days.

        This method enables UI-layer milestone detection, allowing the UI to stop
        simulation BEFORE reaching interactive events. This is the CORRECT pattern
        for MVC separation - UI checks calendar, backend just simulates.

        Delegates to MilestoneDetector service for testability.

        Args:
            days_ahead: Number of days to look ahead (default: 7 for week simulation)

        Returns:
            Dict with milestone info if found, None otherwise:
            {
                'days_until': int,           # Days until milestone (0 = today, 1 = tomorrow, etc.)
                'milestone_date': str,       # ISO date of milestone (e.g., '2025-04-24')
                'event_type': str,           # 'DRAFT_DAY', 'DEADLINE', 'WINDOW'
                'event_subtype': str,        # Specific type (e.g., 'FRANCHISE_TAG', 'FREE_AGENCY_START')
                'display_name': str,         # UI-friendly label (e.g., 'Draft Day', 'Franchise Tag')
                'event': Dict[str, Any]      # Full event dict from database
            }

        Examples:
            # Check next 7 days before simulating week
            milestone = controller.check_upcoming_milestones(days_ahead=7)
            if milestone:
                # Stop before milestone, show dialog
                days_to_sim = milestone['days_until']
                controller.advance_days(days_to_sim)  # Simulate up to milestone
                handle_milestone_dialog(milestone['event'])
            else:
                # No milestone, simulate full week
                controller.advance_week()
        """
        try:
            milestone = self._milestone_detector.check_upcoming_milestones(days_ahead)
            if milestone:
                self._logger.info(
                    f"Milestone detected: {milestone['display_name']} on {milestone['milestone_date']} "
                    f"({milestone['days_until']} days ahead)"
                )
            return milestone
        except Exception as e:
            self._logger.error(f"Error checking upcoming milestones: {e}")
            # Fail-safe: return None to allow simulation to continue
            return None

    def set_milestone_detector_verbose(self, verbose: bool) -> None:
        """
        Enable or disable verbose diagnostic logging for milestone detection.

        Use this to debug why milestone detection might be failing.

        Args:
            verbose: True to enable verbose output, False to disable
        """
        if hasattr(self, '_milestone_detector') and self._milestone_detector:
            self._milestone_detector.set_verbose(verbose)
            self._logger.info(f"Milestone detector verbose mode set to: {verbose}")

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
        # Define state extraction
        def extract_state(summary: Dict) -> tuple:
            new_date = summary['end_date']
            new_phase = self.season_controller.phase_state.phase.value
            current_week = self.get_current_week()  # Query from schedule database
            return (new_date, new_phase, current_week)

        # Define post-save hook for signal emission and milestone message
        def post_save_hook(summary: Dict) -> None:
            # Emit date changed signal
            self.date_changed.emit(self.current_date_str)

            # Add friendly message (modifies summary in-place)
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

        # Define success result builder (return summary as-is, already modified by hook)
        def build_success_result(summary: Dict) -> Dict[str, Any]:
            return summary

        # Define failure result factory
        def failure_dict_factory(message: str) -> Dict[str, Any]:
            return {
                'success': False,
                'message': message,
                'start_date': self.current_date_str,
                'end_date': self.current_date_str,
                'weeks_simulated': 0,
                'total_games': 0,
                'starting_phase': self.season_controller.phase_state.phase.value,
                'ending_phase': self.season_controller.phase_state.phase.value,
                'phase_transition': False
            }

        # Create backend method wrapper to pass progress_callback
        backend_method = lambda: self.season_controller.simulate_to_phase_end(
            progress_callback=progress_callback
        )

        # Execute using template method
        return self._execute_simulation_with_persistence(
            operation_name="advance_to_end_of_phase",
            backend_method=backend_method,
            hooks={
                'pre_save': None,
                'post_save': post_save_hook
            },
            extractors={
                'extract_state': extract_state,
                'build_success_result': build_success_result
            },
            failure_dict_factory=failure_dict_factory
        )

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
        # Define state extraction
        def extract_state(summary: Dict) -> tuple:
            new_date = summary['end_date']
            new_phase = summary['ending_phase']  # Use ending_phase from summary
            current_week = self.get_current_week()  # Query from schedule database
            return (new_date, new_phase, current_week)

        # Define post-save hook for signal emission
        def post_save_hook(summary: Dict) -> None:
            self.date_changed.emit(self.current_date_str)

        # Define success result builder (return summary as-is)
        def build_success_result(summary: Dict) -> Dict[str, Any]:
            return summary

        # Define failure result factory
        def failure_dict_factory(message: str) -> Dict[str, Any]:
            return {
                'success': False,
                'message': message,
                'start_date': self.current_date_str,
                'end_date': self.current_date_str,
                'weeks_simulated': 0,
                'total_games': 0,
                'starting_phase': self.season_controller.phase_state.phase.value,
                'ending_phase': self.season_controller.phase_state.phase.value
            }

        # Execute using template method
        return self._execute_simulation_with_persistence(
            operation_name="simulate_to_new_season",
            backend_method=self.season_controller.simulate_to_new_season,
            hooks={
                'pre_save': None,
                'post_save': post_save_hook
            },
            extractors={
                'extract_state': extract_state,
                'build_success_result': build_success_result
            },
            failure_dict_factory=failure_dict_factory
        )

    def get_simulation_state(self) -> Dict[str, Any]:
        """
        Get complete simulation state.

        Returns:
            Dict with date, phase, week, and other metadata
        """
        return {
            "date": self.current_date_str,
            "phase": self.season_controller.phase_state.phase.value,
            "week": self.get_current_week(),
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
