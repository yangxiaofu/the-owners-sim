"""Phase Handler Protocol - Strategy interface for phase-specific daily operations."""
from typing import Protocol, Dict, Any


class PhaseHandler(Protocol):
    """Strategy interface for phase-specific daily operations."""

    def advance_day(self) -> Dict[str, Any]:
        """
        Execute phase-specific daily advancement logic.

        Returns:
            Dictionary with simulation results including:
            - date: str
            - games_played: int
            - results: List[Dict]
            - current_phase: str
            - success: bool
            - message: str
        """
        ...
