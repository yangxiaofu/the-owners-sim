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

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from season.season_cycle_controller import SeasonCycleController
from calendar.date_models import Date
from calendar.season_phase_tracker import SeasonPhase
from ui.domain_models.simulation_data_model import SimulationDataModel


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
    date_changed = Signal(str, str)  # (date_str, phase)
    games_played = Signal(list)  # (game_results)
    phase_changed = Signal(str, str)  # (old_phase, new_phase)

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize simulation controller.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier
            season: Current season year
        """
        super().__init__()

        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season
        print(f"[DYNASTY_TRACE] SimulationController.__init__(): dynasty_id={dynasty_id}")

        # Domain model for state persistence and retrieval
        self.state_model = SimulationDataModel(db_path, dynasty_id, season)

        # Load current state from database FIRST (establishes current_date_str, current_phase, current_week)
        self._load_state()

        # Initialize season cycle controller with the loaded state
        self._init_season_controller()

    def _init_season_controller(self):
        """Initialize or restore SeasonCycleController using already-loaded state."""
        # Use the current_date_str that was already loaded by _load_state()
        # This ensures calendar and controller state are synchronized
        start_date = Date.from_string(self.current_date_str)

        # Convert loaded phase string to SeasonPhase enum
        from calendar.season_phase_tracker import SeasonPhase

        if self.loaded_phase == 'PLAYOFFS' or self.loaded_phase == 'playoffs':
            initial_phase = SeasonPhase.PLAYOFFS
        elif self.loaded_phase == 'OFFSEASON' or self.loaded_phase == 'offseason':
            initial_phase = SeasonPhase.OFFSEASON
        else:
            initial_phase = SeasonPhase.REGULAR_SEASON

        # Pass initial_phase to constructor so it starts in correct phase
        # This prevents regular season game scheduling when loading mid-playoffs
        self.season_controller = SeasonCycleController(
            database_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season_year=self.season,
            start_date=start_date,
            initial_phase=initial_phase,
            enable_persistence=True,
            verbose_logging=True  # Enable for player stats debugging
        )

        # No more manual phase synchronization needed - handled by constructor!

    def _get_state_from_db(self) -> Optional[Dict[str, Any]]:
        """
        Load current simulation state from database.

        Returns:
            Dict with current_date, current_phase, current_week or None
        """
        return self.state_model.get_state()

    def _save_state_to_db(self, current_date: str, current_phase: str, current_week: Optional[int] = None):
        """
        Save current simulation state to database.

        Args:
            current_date: Date string (YYYY-MM-DD)
            current_phase: REGULAR_SEASON, PLAYOFFS, or OFFSEASON
            current_week: Current week number (optional)
        """
        success = self.state_model.save_state(
            current_date=current_date,
            current_phase=current_phase,
            current_week=current_week
        )

        if not success:
            print(f"[ERROR SimulationController] Failed to write dynasty_state!")

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
                self.date_changed.emit(new_date, new_phase)

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

                self.date_changed.emit(new_date, new_phase)

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
        Get current week number (regular season only).

        Returns:
            Week number or None if not in regular season
        """
        return self.current_week if self.season_controller.phase_state.phase.value == "regular_season" else None

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
                self.date_changed.emit(self.current_date_str, self.season_controller.phase_state.phase.value)

                # Add friendly message
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
            "season": self.season,
            "dynasty_id": self.dynasty_id
        }
