"""
Rating-based valuation factor.

Simple, high-confidence factor that uses overall rating to determine
tier and AAV with within-tier scaling.
"""

from typing import Dict, Any

from contract_valuation.models import FactorResult
from contract_valuation.context import ValuationContext
from contract_valuation.factors.base import ValueFactor


class RatingFactor(ValueFactor):
    """
    Valuation factor based on overall player rating.

    Uses tier thresholds to map rating to market rate, then applies
    within-tier scaling based on exact rating position.

    Tier Thresholds:
    - Elite: 90-99
    - Quality: 80-89
    - Starter: 70-79
    - Backup: 0-69

    Confidence: 0.85 (rating is reliable but doesn't capture nuances)
    """

    # Within-tier scaling range
    TIER_SCALE_MIN = 0.90
    TIER_SCALE_MAX = 1.15

    # Tier rating ranges
    TIER_RANGES = {
        "elite": (90, 99),
        "quality": (80, 89),
        "starter": (70, 79),
        "backup": (0, 69),
    }

    # Cap percentage fallback for unknown positions
    CAP_PCT_BY_TIER = {
        "elite": 0.05,      # 5% of cap
        "quality": 0.025,   # 2.5% of cap
        "starter": 0.01,    # 1% of cap
        "backup": 0.001,    # 0.1% of cap
    }

    @property
    def factor_name(self) -> str:
        """Return factor identifier."""
        return "rating"

    def calculate(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext
    ) -> FactorResult:
        """
        Calculate AAV based on overall rating.

        Args:
            player_data: Must contain 'position' and 'overall_rating' (0-99)
            context: Market context with position rates

        Returns:
            FactorResult with AAV estimate and 0.85 confidence

        Raises:
            ValueError: If position or overall_rating missing/invalid
        """
        self.validate_player_data(player_data)
        self._validate_rating_data(player_data)

        position = player_data["position"].upper()
        rating = player_data["overall_rating"]

        # Determine tier
        tier = self.get_position_tier(position, rating, context)

        # Get base market rate
        base_rate = context.get_market_rate(position, tier)

        # Fallback for unknown positions: use cap percentage
        if base_rate is None:
            base_rate = self._calculate_fallback_rate(context, tier)
            fallback_used = True
        else:
            fallback_used = False

        # Apply within-tier scaling
        scaled_aav = self._apply_tier_scaling(base_rate, rating, tier)

        breakdown = {
            "position": position,
            "rating": rating,
            "tier": tier,
            "base_rate": base_rate,
            "scale_factor": round(self._get_scale_factor(rating, tier), 3),
            "fallback_used": fallback_used,
            "final_aav": scaled_aav,
        }

        return FactorResult(
            name=self.factor_name,
            raw_value=scaled_aav,
            confidence=0.85,
            breakdown=breakdown,
        )

    def _validate_rating_data(self, player_data: Dict[str, Any]) -> None:
        """Validate rating-specific required fields."""
        if "overall_rating" not in player_data:
            raise ValueError("Missing required field: overall_rating")

        rating = player_data["overall_rating"]
        if not isinstance(rating, int) or not 0 <= rating <= 99:
            raise ValueError(f"overall_rating must be int 0-99, got {rating}")

    def _calculate_fallback_rate(self, context: ValuationContext, tier: str) -> int:
        """Calculate fallback rate using cap percentage."""
        cap_pct = self.CAP_PCT_BY_TIER.get(tier, 0.01)
        return int(context.salary_cap * cap_pct)

    def _get_scale_factor(self, rating: int, tier: str) -> float:
        """
        Calculate within-tier scaling factor.

        Maps rating position within tier to scale range.
        Higher rating within tier = higher scale factor.
        """
        tier_min, tier_max = self.TIER_RANGES.get(tier, (0, 99))
        tier_range = tier_max - tier_min

        if tier_range == 0:
            return 1.0

        # Position within tier (0.0 to 1.0)
        position_in_tier = (rating - tier_min) / tier_range

        # Map to scale range
        scale_range = self.TIER_SCALE_MAX - self.TIER_SCALE_MIN
        scale_factor = self.TIER_SCALE_MIN + (position_in_tier * scale_range)

        return scale_factor

    def _apply_tier_scaling(self, base_rate: int, rating: int, tier: str) -> int:
        """Apply within-tier scaling to base rate."""
        scale_factor = self._get_scale_factor(rating, tier)
        return int(base_rate * scale_factor)
