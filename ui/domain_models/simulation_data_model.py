"""
Simulation Data Model for The Owner's Sim UI

Domain model for simulation state management and persistence.
Encapsulates all dynasty_state database operations and business logic.

Architecture:
    SimulationController (UI layer)
        ↓ uses
    SimulationDataModel (THIS - business logic + data access)
        ↓ queries
    DynastyStateAPI (database layer)

Responsibilities:
    ✅ OWN: DynastyStateAPI instance
    ✅ DO: State retrieval, persistence, validation, initialization
    ✅ RETURN: Clean data structures (dicts, primitives)
    ❌ NO: Qt dependencies, UI concerns, SeasonCycleController ownership
"""

from typing import Dict, Any, Optional
from datetime import date
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from database.dynasty_state_api import DynastyStateAPI


class SimulationDataModel:
    """
    Domain model for simulation state management.

    Owns DynastyStateAPI and encapsulates all business logic for:
    - Loading simulation state from database
    - Saving simulation state to database
    - State initialization and validation
    - Date validation and suspicious date detection

    This model does NOT own SeasonCycleController - that stays in SimulationController.
    It only manages dynasty_state database operations.
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize simulation data model.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year (optional, used only for new dynasty creation)
                    NOTE: After initialization, use the season property which is the
                    SINGLE SOURCE OF TRUTH loaded from database via get_latest_state()
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self._initialization_season = season  # Only used for new dynasty creation

        # Own the DynastyStateAPI instance (domain models own their APIs)
        self.dynasty_api = DynastyStateAPI(db_path)

    @property
    def season(self) -> int:
        """
        Current season year (SINGLE SOURCE OF TRUTH).

        Queries database using get_latest_state() which automatically
        retrieves the most recent season without requiring a season filter.
        This ensures the UI always displays the current season year, even
        immediately after season transitions.

        Returns:
            int: Current season year from database, or initialization season for new dynasties
        """
        state = self.dynasty_api.get_latest_state(self.dynasty_id)
        return state['season'] if state else self._initialization_season

    def get_state(self) -> Optional[Dict[str, Any]]:
        """
        Load current simulation state from database.

        Uses get_latest_state() which automatically retrieves the most recent
        season without requiring a season filter. This ensures we always get
        the current state even after season transitions.

        Returns:
            Dict with:
                - current_date: str (YYYY-MM-DD)
                - current_phase: str (REGULAR_SEASON, PLAYOFFS, OFFSEASON)
                - current_week: Optional[int]
                - season: int (current season year)
                - last_simulated_game_id: Optional[str]
            or None if no state exists
        """
        return self.dynasty_api.get_latest_state(self.dynasty_id)

    def save_state(
        self,
        current_date: str,
        current_phase: str,
        current_week: Optional[int] = None,
        last_simulated_game_id: Optional[str] = None
    ) -> bool:
        """
        Save current simulation state to database.

        Args:
            current_date: Date string (YYYY-MM-DD)
            current_phase: REGULAR_SEASON, PLAYOFFS, or OFFSEASON
            current_week: Current week number (optional)
            last_simulated_game_id: ID of last simulated game (optional)

        Returns:
            True if save successful, False otherwise
        """
        success = self.dynasty_api.update_state(
            dynasty_id=self.dynasty_id,
            season=self.season,
            current_date=current_date,
            current_phase=current_phase,
            current_week=current_week,
            last_simulated_game_id=last_simulated_game_id
        )

        if not success:
            print(f"[ERROR SimulationDataModel] Failed to save dynasty state for {self.dynasty_id} season {self.season}")

        return success

    def initialize_state(
        self,
        start_date: Optional[str] = None,
        start_week: int = 1,
        start_phase: str = "REGULAR_SEASON"
    ) -> Dict[str, Any]:
        """
        Initialize or restore simulation state.

        If state exists in database, loads it. Otherwise creates fresh state.
        Performs date validation to detect suspicious dates.

        Args:
            start_date: Optional start date (YYYY-MM-DD). If None, uses season start
            start_week: Starting week number (default: 1)
            start_phase: Starting phase (default: REGULAR_SEASON)

        Returns:
            Dict with:
                - current_date: str
                - current_phase: str
                - current_week: int
                - is_new: bool (True if newly initialized)
                - warnings: List[str] (any validation warnings)
        """
        print(f"[DEBUG SimulationDataModel] initialize_state() called for dynasty '{self.dynasty_id}', season {self.season}")

        # Try to load existing state
        state = self.get_state()
        warnings = []

        if state:
            # State exists - load and validate it
            current_date_str = state['current_date']
            current_phase = state['current_phase']
            current_week = state['current_week']

            print(f"[DEBUG SimulationDataModel] Found existing state:")
            print(f"  current_date: {current_date_str}")
            print(f"  current_phase: {current_phase}")
            print(f"  current_week: {current_week}")

            # Perform date validation
            date_warnings = self._validate_date(current_date_str)
            warnings.extend(date_warnings)

            return {
                'current_date': current_date_str,
                'current_phase': current_phase,
                'current_week': current_week,
                'is_new': False,
                'warnings': warnings
            }
        else:
            # No state exists - initialize new state
            if start_date is None:
                # Default to first Thursday in September
                start_date = f"{self.season}-09-05"

            print(f"[DEBUG SimulationDataModel] NO existing state found, creating new state:")
            print(f"  start_date: {start_date}")
            print(f"  start_phase: {start_phase}")
            print(f"  start_week: {start_week}")

            # Save initial state
            success = self.save_state(start_date, start_phase, start_week)
            if not success:
                print(f"[ERROR SimulationDataModel] Failed to save initial state!")
                warnings.append("Failed to save initial dynasty state to database")

            return {
                'current_date': start_date,
                'current_phase': start_phase,
                'current_week': start_week,
                'is_new': True,
                'warnings': warnings
            }

    def _validate_date(self, date_str: str) -> list[str]:
        """
        Validate simulation date and detect suspicious dates.

        NFL seasons start in September, so dates exactly matching real-time
        dates in Oct/Nov/Dec are suspicious and suggest incorrect initialization.

        Args:
            date_str: Date string to validate (YYYY-MM-DD)

        Returns:
            List of warning messages (empty if no issues)
        """
        warnings = []

        try:
            sim_date_parts = date_str.split('-')
            if len(sim_date_parts) != 3:
                warnings.append(f"Invalid date format: {date_str} (expected YYYY-MM-DD)")
                return warnings

            sim_year = int(sim_date_parts[0])
            sim_month = int(sim_date_parts[1])
            sim_day = int(sim_date_parts[2])

            # Check if simulation date exactly matches real-time date
            today = date.today()
            if (sim_year == today.year and
                sim_month == today.month and
                sim_day == today.day):

                warnings.append(
                    f"Simulation date {date_str} matches real-time date! "
                    f"This suggests dynasty_state was incorrectly initialized. "
                    f"Expected season start: {self.season}-09-05"
                )

        except (ValueError, IndexError) as e:
            warnings.append(f"Date validation error for {date_str}: {str(e)}")

        return warnings

    def get_current_date(self) -> Optional[str]:
        """
        Get current simulation date.

        Returns:
            Date string (YYYY-MM-DD) or None if no state exists
        """
        state = self.get_state()
        return state['current_date'] if state else None

    def get_current_phase(self) -> Optional[str]:
        """
        Get current season phase.

        Returns:
            Phase string (REGULAR_SEASON, PLAYOFFS, OFFSEASON) or None if no state exists
        """
        state = self.get_state()
        return state['current_phase'] if state else None

    def get_current_week(self) -> Optional[int]:
        """
        Get current week number.

        Returns:
            Week number or None if no state exists or not applicable
        """
        state = self.get_state()
        return state['current_week'] if state else None

    def delete_state(self) -> int:
        """
        Delete current dynasty state.

        Useful for resetting/reinitializing a dynasty.

        Returns:
            Number of rows deleted
        """
        return self.dynasty_api.delete_state(self.dynasty_id, self.season)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get complete simulation state summary.

        Returns:
            Dict with all state information plus metadata:
                - date: str
                - phase: str
                - week: Optional[int]
                - season: int
                - dynasty_id: str
                - exists: bool (whether state exists in DB)
        """
        state = self.get_state()

        if state:
            return {
                'date': state['current_date'],
                'phase': state['current_phase'],
                'week': state['current_week'],
                'season': self.season,
                'dynasty_id': self.dynasty_id,
                'exists': True
            }
        else:
            return {
                'date': None,
                'phase': None,
                'week': None,
                'season': self.season,
                'dynasty_id': self.dynasty_id,
                'exists': False
            }
