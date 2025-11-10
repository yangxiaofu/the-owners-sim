"""
Phase State - Single source of truth for season phase and year

Shared mutable object maintaining current phase and season year across all simulation components.
Eliminates phase/year desynchronization by providing a single shared reference.
"""

from typing import Callable, List
import threading
import logging

# Use try/except to handle both production and test imports
try:
    from src.calendar.season_phase_tracker import SeasonPhase
except ModuleNotFoundError:
    from .season_phase_tracker import SeasonPhase

logger = logging.getLogger(__name__)


class PhaseState:
    """
    Single source of truth for season phase and year.

    Shared mutable object that all components reference.
    When phase or year changes, all components see the new value immediately.

    Thread-safe with optional change listeners for reactive updates.
    """

    def __init__(
        self,
        initial_phase: SeasonPhase = SeasonPhase.REGULAR_SEASON,
        season_year: int = 2025
    ):
        """
        Initialize phase state.

        Args:
            initial_phase: Starting phase (default: REGULAR_SEASON)
            season_year: Starting season year (default: 2025)
        """
        self._phase = initial_phase
        self._season_year = season_year
        self._lock = threading.Lock()
        self._listeners: List[Callable[[SeasonPhase, SeasonPhase], None]] = []

    @property
    def phase(self) -> SeasonPhase:
        """Get current phase (thread-safe)."""
        with self._lock:
            return self._phase

    @phase.setter
    def phase(self, new_phase: SeasonPhase) -> None:
        """
        Set current phase (thread-safe).

        Args:
            new_phase: New phase to transition to
        """
        with self._lock:
            if new_phase == self._phase:
                return  # No change

            old_phase = self._phase
            self._phase = new_phase

            # Copy listeners outside lock to prevent deadlocks
            listeners = self._listeners.copy()

        # Notify listeners of phase change (outside lock)
        for listener in listeners:
            try:
                listener(old_phase, new_phase)
            except Exception:
                # Don't let listener errors break phase transition
                pass

    def add_listener(self, listener: Callable[[SeasonPhase, SeasonPhase], None]) -> None:
        """
        Add a listener for phase changes.

        Args:
            listener: Callback function(old_phase, new_phase)
        """
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[SeasonPhase, SeasonPhase], None]) -> None:
        """Remove a phase change listener."""
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    @property
    def season_year(self) -> int:
        """Get current season year (thread-safe)."""
        with self._lock:
            return self._season_year

    @season_year.setter
    def season_year(self, new_year: int) -> None:
        """
        Set current season year (thread-safe).

        Args:
            new_year: New season year
        """
        with self._lock:
            if new_year == self._season_year:
                return  # No change

            old_year = self._season_year
            self._season_year = new_year
            logger.info(f"PhaseState season_year updated: {old_year} → {new_year}")

    def to_dict(self) -> dict:
        """
        Return dictionary representation.

        Returns:
            Dictionary with 'current_phase' and 'season_year' keys
        """
        with self._lock:
            return {
                "current_phase": self._phase.value.upper(),
                "season_year": self._season_year
            }

    def __str__(self) -> str:
        return f"PhaseState(phase={self.phase.value}, year={self.season_year})"

    def __repr__(self) -> str:
        return str(self)
