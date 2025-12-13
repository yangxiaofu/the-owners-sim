"""
Data models for Owner's draft direction system.

This module defines the data structures for communicating the Owner's
strategic preferences to the AI GM during the NFL Draft.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class DraftStrategy(Enum):
    """
    Overall draft strategy types.

    Attributes:
        BEST_PLAYER_AVAILABLE: Always pick highest-rated prospect, ignore needs
        BALANCED: Balance talent and need (default behavior)
        NEEDS_BASED: Aggressively fill roster holes, willing to reach
        POSITION_FOCUS: Only consider specific positions (requires priorities)
    """
    BEST_PLAYER_AVAILABLE = "bpa"
    BALANCED = "balanced"
    NEEDS_BASED = "needs_based"
    POSITION_FOCUS = "position_focus"


@dataclass
class DraftDirection:
    """
    Owner's strategic direction for the draft.

    Ephemeral context - passed from UI → Handler → Service.
    Not persisted to database (cleared after draft completion).

    Attributes:
        strategy: Overall strategy type
        priority_positions: List of 1-5 positions in priority order (Phase 2)
        watchlist_prospect_ids: List of targeted prospect IDs (Phase 3)
    """
    strategy: DraftStrategy = DraftStrategy.BALANCED
    priority_positions: List[str] = field(default_factory=list)
    watchlist_prospect_ids: List[int] = field(default_factory=list)

    def validate(self) -> tuple[bool, str]:
        """
        Validate draft direction settings.

        Returns:
            (is_valid, error_message)
        """
        # Phase 2: Position Focus requires at least 1 priority
        if self.strategy == DraftStrategy.POSITION_FOCUS:
            if len(self.priority_positions) == 0:
                return (False, "Position Focus strategy requires at least 1 priority position")

        # Maximum 5 priorities allowed
        if len(self.priority_positions) > 5:
            return (False, "Maximum 5 priority positions allowed")

        return (True, "")


@dataclass
class DraftDirectionResult:
    """
    Result of applying draft direction to prospect evaluation.

    Contains both the numerical scores and human-readable explanation
    for transparency in AI decision-making.
    """
    prospect_id: int
    prospect_name: str
    original_score: float
    adjusted_score: float
    strategy_bonus: float
    position_bonus: float  # Phase 2
    watchlist_bonus: float  # Phase 3
    reach_penalty: float
    reason: str  # Human-readable explanation

    def __str__(self) -> str:
        """Format result for logging/debugging."""
        return (
            f"{self.prospect_name}: {self.original_score:.1f} → {self.adjusted_score:.1f} "
            f"(Strategy: +{self.strategy_bonus:.1f}, Position: +{self.position_bonus:.1f}, "
            f"Watchlist: +{self.watchlist_bonus:.1f}, Reach: {self.reach_penalty:.1f})"
        )
