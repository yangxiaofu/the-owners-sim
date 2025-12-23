"""
Job security pressure modifier.

Adjusts valuations based on GM's job security level.
GMs on the hot seat tend to overpay for proven talent.
"""

from typing import Tuple

from contract_valuation.context import OwnerContext
from contract_valuation.owner_pressure.base import PressureModifier


class JobSecurityModifier(PressureModifier):
    """
    Pressure modifier based on GM's job security level.

    GMs on the hot seat tend to overpay for proven talent to win now,
    while secure GMs can be patient and seek value deals.

    Pressure Thresholds:
        - Secure (< 0.3): -3% to 0% discount
        - Normal (0.3-0.7): 0% adjustment
        - Hot Seat (> 0.7): +10% to +15% premium

    Guarantee Adjustments (for contract structure):
        - Secure: -5% guarantee reduction
        - Normal: 0%
        - Hot Seat: +10% to +15% guarantee increase
    """

    # Pressure thresholds
    SECURE_THRESHOLD = 0.3
    HOT_SEAT_THRESHOLD = 0.7

    # AAV adjustment ranges
    SECURE_DISCOUNT_MIN = -0.03  # -3% at pressure 0.0
    SECURE_DISCOUNT_MAX = 0.0    # 0% at pressure 0.3
    HOT_SEAT_PREMIUM_MIN = 0.10  # +10% at pressure 0.7
    HOT_SEAT_PREMIUM_MAX = 0.15  # +15% at pressure 1.0

    # Guarantee adjustment ranges
    SECURE_GUARANTEE_REDUCTION = -0.05
    HOT_SEAT_GUARANTEE_PREMIUM_MIN = 0.10
    HOT_SEAT_GUARANTEE_PREMIUM_MAX = 0.15

    @property
    def modifier_name(self) -> str:
        """Return modifier identifier."""
        return "job_security"

    def calculate_pressure_level(self, context: OwnerContext) -> float:
        """
        Calculate pressure level from job security context.

        Args:
            context: Owner context with job_security field

        Returns:
            Pressure level 0.0 (secure) to 1.0 (hot seat)
        """
        return context.job_security.calculate_security_score()

    def apply(
        self,
        base_aav: int,
        context: OwnerContext
    ) -> Tuple[int, str]:
        """
        Apply job security pressure adjustment to AAV.

        Args:
            base_aav: Pre-adjustment AAV in dollars
            context: Owner context with job security

        Returns:
            Tuple of (adjusted_aav, description)
        """
        pressure = self.calculate_pressure_level(context)
        adjustment_pct = self._calculate_adjustment(pressure)

        # Clamp adjustment
        adjustment_pct = self.clamp_adjustment(adjustment_pct)

        # Calculate adjusted AAV
        adjustment_dollars = int(base_aav * adjustment_pct)
        adjusted_aav = base_aav + adjustment_dollars

        # Format description
        description = self._format_description(pressure, adjustment_pct, adjustment_dollars)

        return adjusted_aav, description

    def _calculate_adjustment(self, pressure: float) -> float:
        """
        Calculate AAV adjustment percentage based on pressure.

        Args:
            pressure: Pressure level 0.0-1.0

        Returns:
            Adjustment percentage (e.g., -0.03 for -3%, 0.12 for +12%)
        """
        if pressure < self.SECURE_THRESHOLD:
            return self._interpolate_secure_discount(pressure)
        elif pressure <= self.HOT_SEAT_THRESHOLD:
            return 0.0
        else:
            return self._interpolate_hot_seat_premium(pressure)

    def _interpolate_secure_discount(self, pressure: float) -> float:
        """
        Interpolate discount for secure GMs.

        Linear interpolation from -3% at pressure 0.0 to 0% at pressure 0.3.

        Args:
            pressure: Pressure level (0.0 to 0.3)

        Returns:
            Discount percentage (negative value)
        """
        # At pressure 0.0: -3% discount
        # At pressure 0.3: 0% discount
        # Linear interpolation
        progress = pressure / self.SECURE_THRESHOLD
        return self.SECURE_DISCOUNT_MIN * (1.0 - progress)

    def _interpolate_hot_seat_premium(self, pressure: float) -> float:
        """
        Interpolate premium for hot seat GMs.

        Linear interpolation from +10% at pressure 0.7 to +15% at pressure 1.0.

        Args:
            pressure: Pressure level (0.7 to 1.0)

        Returns:
            Premium percentage (positive value)
        """
        # At pressure 0.7: +10% premium
        # At pressure 1.0: +15% premium
        range_size = 1.0 - self.HOT_SEAT_THRESHOLD
        progress = (pressure - self.HOT_SEAT_THRESHOLD) / range_size
        premium_range = self.HOT_SEAT_PREMIUM_MAX - self.HOT_SEAT_PREMIUM_MIN
        return self.HOT_SEAT_PREMIUM_MIN + (progress * premium_range)

    def get_guarantee_adjustment(self, context: OwnerContext) -> float:
        """
        Get guarantee percentage adjustment for contract structure.

        Hot seat GMs offer higher guarantees to attract talent.
        Secure GMs can offer lower guarantees.

        Args:
            context: Owner context with job security

        Returns:
            Guarantee adjustment percentage
        """
        pressure = self.calculate_pressure_level(context)

        if pressure < self.SECURE_THRESHOLD:
            return self.SECURE_GUARANTEE_REDUCTION
        elif pressure <= self.HOT_SEAT_THRESHOLD:
            return 0.0
        else:
            # Interpolate guarantee premium for hot seat
            range_size = 1.0 - self.HOT_SEAT_THRESHOLD
            progress = (pressure - self.HOT_SEAT_THRESHOLD) / range_size
            premium_range = self.HOT_SEAT_GUARANTEE_PREMIUM_MAX - self.HOT_SEAT_GUARANTEE_PREMIUM_MIN
            return self.HOT_SEAT_GUARANTEE_PREMIUM_MIN + (progress * premium_range)

    def _format_description(
        self,
        pressure: float,
        adjustment_pct: float,
        adjustment_dollars: int
    ) -> str:
        """
        Format human-readable description.

        Args:
            pressure: Calculated pressure level
            adjustment_pct: Percentage adjustment applied
            adjustment_dollars: Dollar adjustment

        Returns:
            Description string
        """
        # Categorize pressure
        if pressure < self.SECURE_THRESHOLD:
            category = "Secure GM"
        elif pressure <= self.HOT_SEAT_THRESHOLD:
            category = "Normal pressure"
        else:
            category = "Hot seat pressure"

        base_desc = self.format_adjustment_description(
            category, adjustment_pct, adjustment_dollars
        )
        return base_desc

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
        adjustment_pct = self._calculate_adjustment(pressure)
        adjustment_pct = self.clamp_adjustment(adjustment_pct)
        adjustment_dollars = int(base_aav * adjustment_pct)
        adjusted_aav = base_aav + adjustment_dollars

        if pressure < self.SECURE_THRESHOLD:
            category = "secure"
        elif pressure <= self.HOT_SEAT_THRESHOLD:
            category = "normal"
        else:
            category = "hot_seat"

        return {
            "modifier_name": self.modifier_name,
            "pressure_level": round(pressure, 3),
            "pressure_category": category,
            "base_aav": base_aav,
            "adjustment_pct": round(adjustment_pct, 4),
            "adjustment_dollars": adjustment_dollars,
            "adjusted_aav": adjusted_aav,
            "guarantee_adjustment_pct": round(self.get_guarantee_adjustment(context), 4),
            "job_security_inputs": {
                "tenure_years": context.job_security.tenure_years,
                "playoff_appearances": context.job_security.playoff_appearances,
                "recent_win_pct": context.job_security.recent_win_pct,
                "owner_patience": context.job_security.owner_patience,
            }
        }