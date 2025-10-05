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

        # Domain model for state persistence and retrieval
        self.state_model = SimulationDataModel(db_path, dynasty_id, season)

        # Initialize season cycle controller
        self._init_season_controller()

        # Load current state from database
        self._load_state()

    def _init_season_controller(self):
        """Initialize or restore SeasonCycleController."""
        # Get current state from database via model
        state = self.state_model.get_state()

        if state:
            # Restore from saved state
            start_date = Date.from_string(state['current_date'])
        else:
            # Start new season
            start_date = Date(self.season, 9, 5)  # First Thursday in September

        self.season_controller = SeasonCycleController(
            database_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season_year=self.season,
            start_date=start_date,
            enable_persistence=True,
            verbose_logging=False
        )

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
        self.current_phase = state_info['current_phase']
        self.current_week = state_info['current_week']

        # Print any validation warnings from model
        if state_info['warnings']:
            for warning in state_info['warnings']:
                print(f"[WARNING SimulationController] {warning}")

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
                new_phase = result.get('current_phase', self.current_phase)
                games = result.get('results', [])

                # Check for phase transition
                if new_phase != self.current_phase:
                    old_phase = self.current_phase
                    self.phase_changed.emit(old_phase, new_phase)

                # Update state
                self.current_date_str = new_date
                self.current_phase = new_phase

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
                    "phase": self.current_phase,
                    "games_played": 0,
                    "results": [],
                    "message": result.get('message', 'Simulation failed')
                }

        except Exception as e:
            return {
                "success": False,
                "date": self.current_date_str,
                "phase": self.current_phase,
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
                new_phase = result.get('current_phase', self.current_phase)

                self.current_date_str = new_date
                self.current_phase = new_phase

                # Increment week
                if self.current_phase == "REGULAR_SEASON":
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
        return self.current_phase

    def get_current_week(self) -> Optional[int]:
        """
        Get current week number (regular season only).

        Returns:
            Week number or None if not in regular season
        """
        return self.current_week if self.current_phase == "REGULAR_SEASON" else None

    def get_simulation_state(self) -> Dict[str, Any]:
        """
        Get complete simulation state.

        Returns:
            Dict with date, phase, week, and other metadata
        """
        return {
            "date": self.current_date_str,
            "phase": self.current_phase,
            "week": self.current_week,
            "season": self.season,
            "dynasty_id": self.dynasty_id
        }
