"""
Phase State - Single source of truth for season phase

Shared mutable object maintaining current phase across all simulation components.
Eliminates phase desynchronization by providing a single shared reference.
"""

from typing import Callable, List
import threading

# Use try/except to handle both production and test imports
try:
    from src.calendar.season_phase_tracker import SeasonPhase
except ModuleNotFoundError:
    from .season_phase_tracker import SeasonPhase


class PhaseState:
    """
    Single source of truth for season phase.

    Shared mutable object that all components reference.
    When phase changes, all components see the new value immediately.

    Thread-safe with optional change listeners for reactive updates.
    """

    def __init__(self, initial_phase: SeasonPhase = SeasonPhase.REGULAR_SEASON):
        """
        Initialize phase state.

        Args:
            initial_phase: Starting phase (default: REGULAR_SEASON)
        """
        self._phase = initial_phase
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

    def __str__(self) -> str:
        return f"PhaseState(phase={self.phase.value})"

    def __repr__(self) -> str:
        return str(self)
