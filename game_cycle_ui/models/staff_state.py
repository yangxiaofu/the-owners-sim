"""
Staff State Model - Encapsulates state for a single staff member (GM or HC).

Consolidates scattered instance variables into a single, testable data structure.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class StaffState:
    """
    Encapsulates state for a single staff member (GM or HC).

    Attributes:
        is_fired: Whether the staff member has been fired
        candidates: List of candidate dicts for replacement
        selected_id: ID of the selected replacement candidate
    """
    is_fired: bool = False
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    selected_id: Optional[str] = None

    def reset(self):
        """Reset to initial state (keep current staff)."""
        self.is_fired = False
        self.candidates = []
        self.selected_id = None

    def fire(self):
        """Mark staff as fired."""
        self.is_fired = True

    def hire(self, candidate_id: str):
        """Select a new hire."""
        self.selected_id = candidate_id

    def is_decision_complete(self) -> bool:
        """
        Check if staff decision is complete.

        Returns:
            True if keeping current staff OR hired a replacement
        """
        return not self.is_fired or self.selected_id is not None
