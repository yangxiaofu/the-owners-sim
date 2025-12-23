"""
Abstract base class for owner pressure modifiers.

Provides the interface that all pressure modifiers must implement.
Pressure modifiers adjust valuations based on team/GM situational factors.
"""

from abc import ABC, abstractmethod
from typing import Tuple

from contract_valuation.context import OwnerContext


class PressureModifier(ABC):
    """
    Abstract base class for owner pressure modifiers.

    Pressure modifiers adjust base AAV values based on situational
    factors like job security, win-now urgency, and budget constraints.

    Subclasses must implement:
    - modifier_name: Unique identifier for this modifier
    - calculate_pressure_level(): Compute 0.0-1.0 pressure score
    - apply(): Adjust AAV and return explanation

    Example implementations:
    - JobSecurityModifier: Pressure from GM's job security
    - WinNowModifier: Pressure to win championships now
    - BudgetModifier: Pressure from owner budget stance
    """

    @property
    @abstractmethod
    def modifier_name(self) -> str:
        """
        Unique identifier for this modifier.

        Used for audit trails and debugging.
        Should be lowercase with underscores (e.g., "job_security", "win_now").

        Returns:
            Modifier identifier string
        """
        pass

    @abstractmethod
    def calculate_pressure_level(self, context: OwnerContext) -> float:
        """
        Calculate the pressure level from this modifier.

        Args:
            context: Owner/situational context with job security,
                    philosophies, and constraints

        Returns:
            Pressure level from 0.0 (no pressure) to 1.0 (maximum pressure).
            Higher pressure typically leads to higher valuations (overpaying).
        """
        pass

    @abstractmethod
    def apply(
        self,
        base_aav: int,
        context: OwnerContext
    ) -> Tuple[int, str]:
        """
        Apply pressure adjustment to base AAV.

        Args:
            base_aav: Pre-adjustment AAV in dollars
            context: Owner/situational context

        Returns:
            Tuple of:
            - adjusted_aav: Post-adjustment AAV in dollars
            - description: Human-readable explanation of adjustment
                          (e.g., "Hot seat pressure: +12% ($1.2M)")
        """
        pass

    def clamp_adjustment(
        self,
        adjustment_pct: float,
        min_pct: float = -0.20,
        max_pct: float = 0.25
    ) -> float:
        """
        Clamp adjustment percentage to reasonable bounds.

        Utility method to prevent extreme adjustments.

        Args:
            adjustment_pct: Raw adjustment percentage
            min_pct: Minimum allowed adjustment (default -20%)
            max_pct: Maximum allowed adjustment (default +25%)

        Returns:
            Clamped adjustment percentage
        """
        return max(min_pct, min(max_pct, adjustment_pct))

    def format_adjustment_description(
        self,
        modifier_name: str,
        adjustment_pct: float,
        adjustment_dollars: int
    ) -> str:
        """
        Format a human-readable adjustment description.

        Utility method for consistent description formatting.

        Args:
            modifier_name: Name of the modifier
            adjustment_pct: Percentage adjustment (e.g., 0.12 for +12%)
            adjustment_dollars: Dollar adjustment

        Returns:
            Formatted description string
        """
        sign = "+" if adjustment_pct >= 0 else ""
        pct_str = f"{sign}{adjustment_pct * 100:.1f}%"

        if abs(adjustment_dollars) >= 1_000_000:
            dollar_str = f"${adjustment_dollars / 1_000_000:.1f}M"
        else:
            dollar_str = f"${adjustment_dollars:,}"

        return f"{modifier_name}: {pct_str} ({dollar_str})"