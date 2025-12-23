"""
Budget stance pressure modifier.

Adjusts valuations based on owner's spending philosophy and constraints.
"""

from typing import Tuple, Dict, Any, List

from contract_valuation.context import OwnerContext
from contract_valuation.owner_pressure.base import PressureModifier


class BudgetStanceModifier(PressureModifier):
    """
    Pressure modifier based on owner's spending philosophy and constraints.

    Applies owner-level budget multiplier and can enforce contract constraints
    (max_contract_years, max_guaranteed_pct).

    Budget Philosophies:
        - "aggressive": +15% budget flexibility (1.15x multiplier)
        - "balanced": Market rate (1.00x multiplier)
        - "conservative": -10% budget constraint (0.90x multiplier)

    Constraint Enforcement:
        - Warns if proposed contract exceeds max_contract_years
        - Caps guaranteed_pct at owner's max_guaranteed_pct
    """

    # Philosophy -> pressure level mapping
    PHILOSOPHY_PRESSURE = {
        "aggressive": 0.8,    # High spending pressure
        "balanced": 0.5,      # Moderate
        "conservative": 0.2,  # Low spending, value-focused
    }

    @property
    def modifier_name(self) -> str:
        """Return modifier identifier."""
        return "budget_stance"

    def calculate_pressure_level(self, context: OwnerContext) -> float:
        """
        Calculate budget pressure level from owner philosophy.

        Args:
            context: Owner context with owner_philosophy

        Returns:
            Pressure level 0.0-1.0 (higher = more spending)
        """
        return self.PHILOSOPHY_PRESSURE.get(context.owner_philosophy, 0.5)

    def apply(
        self,
        base_aav: int,
        context: OwnerContext
    ) -> Tuple[int, str]:
        """
        Apply budget stance adjustment to AAV.

        Args:
            base_aav: Pre-adjustment AAV in dollars
            context: Owner context with owner philosophy

        Returns:
            Tuple of (adjusted_aav, description)
        """
        # Get budget multiplier from context
        multiplier = context.get_budget_multiplier()
        adjustment_pct = multiplier - 1.0

        # Clamp adjustment
        adjustment_pct = self.clamp_adjustment(adjustment_pct)

        # Recalculate multiplier after clamping
        multiplier = 1.0 + adjustment_pct

        # Calculate adjusted AAV
        adjusted_aav = int(base_aav * multiplier)
        adjustment_dollars = adjusted_aav - base_aav

        # Format description
        description = self._format_description(
            context.owner_philosophy,
            adjustment_pct,
            adjustment_dollars
        )

        return adjusted_aav, description

    def get_max_years(self, context: OwnerContext) -> int:
        """
        Get maximum contract years allowed by owner.

        Args:
            context: Owner context with constraint

        Returns:
            Maximum contract years (1-7)
        """
        return context.max_contract_years

    def get_max_guaranteed_pct(self, context: OwnerContext) -> float:
        """
        Get maximum guaranteed percentage allowed by owner.

        Args:
            context: Owner context with constraint

        Returns:
            Maximum guaranteed percentage (0.0-1.0)
        """
        return context.max_guaranteed_pct

    def validate_constraints(
        self,
        proposed_years: int,
        proposed_guaranteed_pct: float,
        context: OwnerContext
    ) -> Dict[str, Any]:
        """
        Validate proposed contract against owner constraints.

        Args:
            proposed_years: Proposed contract length
            proposed_guaranteed_pct: Proposed guarantee percentage
            context: Owner context with constraints

        Returns:
            Dictionary with validation results and violations
        """
        max_years = self.get_max_years(context)
        max_guaranteed = self.get_max_guaranteed_pct(context)

        years_valid = proposed_years <= max_years
        guaranteed_valid = proposed_guaranteed_pct <= max_guaranteed

        violations: List[str] = []
        if not years_valid:
            violations.append("years_exceeded")
        if not guaranteed_valid:
            violations.append("guaranteed_exceeded")

        return {
            "years_valid": years_valid,
            "guaranteed_valid": guaranteed_valid,
            "proposed_years": proposed_years,
            "max_years": max_years,
            "proposed_guaranteed_pct": proposed_guaranteed_pct,
            "max_guaranteed_pct": max_guaranteed,
            "violations": violations,
            "is_valid": years_valid and guaranteed_valid,
        }

    def _format_description(
        self,
        philosophy: str,
        adjustment_pct: float,
        adjustment_dollars: int
    ) -> str:
        """
        Format human-readable description.

        Args:
            philosophy: Owner philosophy
            adjustment_pct: Percentage adjustment applied
            adjustment_dollars: Dollar adjustment

        Returns:
            Description string
        """
        philosophy_labels = {
            "aggressive": "Aggressive owner (willing to overpay)",
            "balanced": "Balanced owner (market rate)",
            "conservative": "Conservative owner (value-focused)",
        }
        philosophy_label = philosophy_labels.get(philosophy, "Owner")

        return self.format_adjustment_description(
            philosophy_label,
            adjustment_pct,
            adjustment_dollars
        )

    def get_breakdown(self, context: OwnerContext, base_aav: int) -> dict:
        """
        Get detailed breakdown for audit trail.

        Args:
            context: Owner context
            base_aav: Base AAV before adjustment

        Returns:
            Detailed breakdown dictionary
        """
        pressure = self.calculate_pressure_level(context)
        multiplier = context.get_budget_multiplier()
        adjustment_pct = multiplier - 1.0
        adjustment_pct = self.clamp_adjustment(adjustment_pct)
        multiplier = 1.0 + adjustment_pct
        adjusted_aav = int(base_aav * multiplier)
        adjustment_dollars = adjusted_aav - base_aav

        # Generate rationale
        if context.owner_philosophy == "aggressive":
            rationale = "Aggressive owner willing to overpay for talent"
        elif context.owner_philosophy == "conservative":
            rationale = "Conservative owner seeks value deals with lower guarantees"
        else:
            rationale = "Balanced owner targets market-rate deals"

        return {
            "modifier_name": self.modifier_name,
            "pressure_level": round(pressure, 3),
            "owner_philosophy": context.owner_philosophy,
            "budget_multiplier": round(multiplier, 4),
            "base_aav": base_aav,
            "adjustment_pct": round(adjustment_pct, 4),
            "adjustment_dollars": adjustment_dollars,
            "adjusted_aav": adjusted_aav,
            "max_contract_years": context.max_contract_years,
            "max_guaranteed_pct": context.max_guaranteed_pct,
            "rationale": rationale,
        }