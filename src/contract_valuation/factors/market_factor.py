"""
Market-based valuation factor.

Applies market heat multipliers based on position demand,
contract year premiums, and within-tier rating adjustments.
"""

from typing import Dict, Any

from contract_valuation.models import FactorResult
from contract_valuation.context import ValuationContext
from contract_valuation.factors.base import ValueFactor


class MarketFactor(ValueFactor):
    """
    Valuation factor based on market conditions and position demand.

    Applies position-specific heat multipliers reflecting current
    market demand trends, with adjustments for contract year and
    rating position within tier.

    Confidence: 0.90 (market rates are objective), 0.80 for fallback positions
    """

    # Position heat multipliers reflecting market demand (calibrated to NFL 2024)
    MARKET_HEAT = {
        # Premium positions (increased ~10% to match NFL market)
        "QB": 1.20,    # Premium position, always in demand
        "EDGE": 1.18,  # Elite pass rushers command premium
        "LT": 1.15,    # Protect the QB's blind side
        "WR": 1.15,    # Top receivers getting premium deals
        "CB": 1.12,    # Cover corners increasingly valuable
        "RT": 1.12,    # Right tackles valued more now
        # Neutral positions (adjusted up)
        "OT": 1.10,    # Tackle generally valuable
        "DT": 1.08,    # Defensive interior
        "TE": 1.05,    # Tight ends trending up
        "LB": 1.05,    # Off-ball linebackers
        "S": 1.02,     # Safety
        "OG": 1.02,    # Guards
        "C": 1.00,     # Centers
        # Devalued positions (less severe)
        "RB": 1.00,    # RB devaluation still exists but less severe
        "P": 0.95,     # Punters less market heat
        "K": 0.95,     # Kickers less market heat
    }

    # Position group mappings for edge cases
    POSITION_GROUPS = {
        "LOLB": "EDGE",
        "ROLB": "EDGE",
        "LE": "EDGE",
        "RE": "EDGE",
        "MLB": "LB",
        "LG": "OG",
        "RG": "OG",
        "RT": "OT",
        "FS": "S",
        "SS": "S",
    }

    # Contract year premium
    CONTRACT_YEAR_PREMIUM = 1.05

    # Within-tier rating adjustment range (0.92x to 1.08x)
    RATING_ADJ_MIN = 0.92
    RATING_ADJ_MAX = 1.08

    # Tier rating thresholds
    TIER_RANGES = {
        "elite": (90, 99),
        "quality": (80, 89),
        "starter": (70, 79),
        "backup": (0, 69),
    }

    # Cap percentage fallback for unknown positions
    CAP_PCT_BY_TIER = {
        "elite": 0.05,
        "quality": 0.025,
        "starter": 0.01,
        "backup": 0.001,
    }

    @property
    def factor_name(self) -> str:
        """Return factor identifier."""
        return "market"

    def calculate(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext
    ) -> FactorResult:
        """
        Calculate AAV based on market conditions.

        Args:
            player_data: Must contain 'position', 'overall_rating'
                        Optional: 'contract_year' (bool)
            context: Market context with position rates

        Returns:
            FactorResult with AAV estimate and confidence

        Raises:
            ValueError: If required fields missing
        """
        self.validate_player_data(player_data)
        self._validate_market_data(player_data)

        position = player_data["position"].upper()
        rating = player_data["overall_rating"]
        contract_year = player_data.get("contract_year", False)

        # Map position to group if needed
        mapped_position = self.POSITION_GROUPS.get(position, position)

        # Determine tier
        tier = self.get_position_tier(position, rating, context)

        # Get base market rate
        base_rate = context.get_market_rate(mapped_position, tier)
        if base_rate is None:
            # Try original position
            base_rate = context.get_market_rate(position, tier)

        # Fallback for unknown positions
        if base_rate is None:
            base_rate = self._calculate_fallback_rate(context, tier)
            fallback_used = True
            confidence = 0.80
        else:
            fallback_used = False
            confidence = 0.90

        # Apply market heat multiplier
        heat = self._get_position_heat(mapped_position)
        heated_rate = base_rate * heat

        # Apply contract year premium
        if contract_year:
            heated_rate *= self.CONTRACT_YEAR_PREMIUM

        # Apply within-tier rating adjustment
        rating_adj = self._get_rating_adjustment(rating, tier)
        final_aav = int(heated_rate * rating_adj)

        breakdown = {
            "position": position,
            "mapped_position": mapped_position,
            "rating": rating,
            "tier": tier,
            "base_rate": base_rate,
            "market_heat": heat,
            "contract_year": contract_year,
            "contract_year_premium": self.CONTRACT_YEAR_PREMIUM if contract_year else 1.0,
            "rating_adjustment": round(rating_adj, 3),
            "fallback_used": fallback_used,
            "final_aav": final_aav,
        }

        return FactorResult(
            name=self.factor_name,
            raw_value=final_aav,
            confidence=confidence,
            breakdown=breakdown,
        )

    def _validate_market_data(self, player_data: Dict[str, Any]) -> None:
        """Validate market-specific required fields."""
        if "overall_rating" not in player_data:
            raise ValueError("Missing required field: overall_rating")

        rating = player_data["overall_rating"]
        if not isinstance(rating, int) or not 0 <= rating <= 99:
            raise ValueError(f"overall_rating must be int 0-99, got {rating}")

    def _get_position_heat(self, position: str) -> float:
        """Get market heat multiplier for position."""
        return self.MARKET_HEAT.get(position, 1.0)

    def _calculate_fallback_rate(self, context: ValuationContext, tier: str) -> int:
        """Calculate fallback rate using cap percentage."""
        cap_pct = self.CAP_PCT_BY_TIER.get(tier, 0.01)
        return int(context.salary_cap * cap_pct)

    def _get_rating_adjustment(self, rating: int, tier: str) -> float:
        """
        Calculate within-tier rating adjustment.

        Higher rating within tier = higher adjustment factor.
        """
        tier_min, tier_max = self.TIER_RANGES.get(tier, (0, 99))
        tier_range = tier_max - tier_min

        if tier_range == 0:
            return 1.0

        # Position within tier (0.0 to 1.0)
        position_in_tier = (rating - tier_min) / tier_range

        # Map to adjustment range
        adj_range = self.RATING_ADJ_MAX - self.RATING_ADJ_MIN
        adjustment = self.RATING_ADJ_MIN + (position_in_tier * adj_range)

        return adjustment
