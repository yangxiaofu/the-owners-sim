"""
GM Weight Calculator for interpolated factor weights.

Produces interpolated FactorWeights based on GM archetype traits,
enabling nuanced weight distributions rather than discrete style presets.
"""

from dataclasses import dataclass
from typing import Dict, Any, TYPE_CHECKING

from contract_valuation.models import FactorWeights
from contract_valuation.gm_influence.styles import GMStyle

if TYPE_CHECKING:
    from team_management.gm_archetype import GMArchetype


@dataclass
class WeightCalculationResult:
    """
    Result of GM weight calculation.

    Contains interpolated factor weights plus metadata about
    the calculation for transparency and debugging.

    Attributes:
        weights: Calculated factor weights (sum to 1.0)
        dominant_style: Closest matching GMStyle for categorization
        rationale: Human-readable explanation of weight distribution
        trait_breakdown: Original trait values used in calculation
    """

    weights: FactorWeights
    dominant_style: GMStyle
    rationale: str
    trait_breakdown: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "weights": self.weights.to_dict(),
            "dominant_style": self.dominant_style.value,
            "rationale": self.rationale,
            "trait_breakdown": self.trait_breakdown.copy(),
        }


class GMWeightCalculator:
    """
    Calculate customized factor weights from GM archetype traits.

    Uses interpolation to produce weights that reflect the specific
    trait values rather than jumping to 1 of 4 discrete presets.

    Constants:
        BASE_RATING_WEIGHT: Fixed weight for rating factor (0.15)
        MIN_WEIGHT_FLOOR: Minimum weight for each variable factor (0.05)
        ADJUSTABLE_PORTION: Portion of weights distributed among 3 factors (0.85)
    """

    BASE_RATING_WEIGHT = 0.15
    MIN_WEIGHT_FLOOR = 0.05
    ADJUSTABLE_PORTION = 0.85  # 1.0 - 0.15 (rating)
    DOMINANT_THRESHOLD = 0.55

    def calculate_weights(self, archetype: "GMArchetype") -> WeightCalculationResult:
        """
        Calculate customized factor weights from GM archetype.

        Args:
            archetype: GMArchetype instance with valuation traits

        Returns:
            WeightCalculationResult with interpolated weights
        """
        # Step 1: Extract traits with defaults
        analytics = self._get_trait(archetype, "analytics_preference")
        scouting = self._get_trait(archetype, "scouting_preference")
        market = self._get_trait(archetype, "market_awareness")

        trait_breakdown = {
            "analytics_preference": analytics,
            "scouting_preference": scouting,
            "market_awareness": market,
        }

        # Step 2: Normalize traits to sum to 1.0
        normalized = self._normalize_traits(analytics, scouting, market)

        # Step 3: Interpolate weights
        weights = self._interpolate_weights(
            normalized["analytics"],
            normalized["scouting"],
            normalized["market"],
        )

        # Step 4: Determine dominant style for categorization
        dominant_style = self._determine_dominant_style(analytics, scouting, market)

        # Step 5: Generate human-readable rationale
        rationale = self._generate_rationale(
            weights, dominant_style, analytics, scouting, market
        )

        return WeightCalculationResult(
            weights=weights,
            dominant_style=dominant_style,
            rationale=rationale,
            trait_breakdown=trait_breakdown,
        )

    def _get_trait(self, archetype: "GMArchetype", trait_name: str) -> float:
        """
        Safely extract a trait value from the archetype.

        Args:
            archetype: GMArchetype instance
            trait_name: Name of the trait to extract

        Returns:
            Trait value (0.0-1.0) or 0.5 default if missing
        """
        value = getattr(archetype, trait_name, 0.5)
        if not isinstance(value, (int, float)):
            return 0.5
        return max(0.0, min(1.0, float(value)))

    def _normalize_traits(
        self, analytics: float, scouting: float, market: float
    ) -> Dict[str, float]:
        """
        Normalize traits to sum to 1.0 for relative influence.

        Handles edge case where all traits are zero by returning
        equal distribution.

        Args:
            analytics: Analytics preference (0.0-1.0)
            scouting: Scouting preference (0.0-1.0)
            market: Market awareness (0.0-1.0)

        Returns:
            Dict with normalized values summing to 1.0
        """
        total = analytics + scouting + market

        if total == 0:
            # All zeros = equal distribution
            return {
                "analytics": 1.0 / 3.0,
                "scouting": 1.0 / 3.0,
                "market": 1.0 / 3.0,
            }

        return {
            "analytics": analytics / total,
            "scouting": scouting / total,
            "market": market / total,
        }

    def _interpolate_weights(
        self,
        normalized_analytics: float,
        normalized_scouting: float,
        normalized_market: float,
    ) -> FactorWeights:
        """
        Calculate interpolated factor weights.

        Algorithm:
        1. Reserve BASE_RATING_WEIGHT (0.15) for rating factor
        2. Reserve MIN_WEIGHT_FLOOR (0.05) for each of 3 factors
        3. Distribute remaining (0.70) based on normalized traits

        Args:
            normalized_analytics: Normalized analytics trait (sums to 1.0 with others)
            normalized_scouting: Normalized scouting trait
            normalized_market: Normalized market trait

        Returns:
            FactorWeights with interpolated values
        """
        # Remaining after minimum floors (3 * 0.05 = 0.15)
        remaining = self.ADJUSTABLE_PORTION - (3 * self.MIN_WEIGHT_FLOOR)  # 0.70

        # Calculate each weight = floor + (remaining * normalized_trait)
        stats_weight = self.MIN_WEIGHT_FLOOR + (remaining * normalized_analytics)
        scouting_weight = self.MIN_WEIGHT_FLOOR + (remaining * normalized_scouting)
        market_weight = self.MIN_WEIGHT_FLOOR + (remaining * normalized_market)
        rating_weight = self.BASE_RATING_WEIGHT

        # Round to avoid floating point issues
        stats_weight = round(stats_weight, 4)
        scouting_weight = round(scouting_weight, 4)
        market_weight = round(market_weight, 4)
        rating_weight = round(rating_weight, 4)

        # Ensure sum is exactly 1.0 by adjusting largest weight
        total = stats_weight + scouting_weight + market_weight + rating_weight
        if abs(total - 1.0) > 0.0001:
            # Adjust stats_weight to compensate
            diff = 1.0 - total
            stats_weight = round(stats_weight + diff, 4)

        return FactorWeights(
            stats_weight=stats_weight,
            scouting_weight=scouting_weight,
            market_weight=market_weight,
            rating_weight=rating_weight,
        )

    def _determine_dominant_style(
        self, analytics: float, scouting: float, market: float
    ) -> GMStyle:
        """
        Determine which GMStyle best matches the traits.

        Uses a 0.55 threshold (slightly lower than GMStyle's 0.6)
        for more sensitive categorization.

        Args:
            analytics: Raw analytics preference
            scouting: Raw scouting preference
            market: Raw market awareness

        Returns:
            GMStyle that best matches the trait distribution
        """
        max_trait = max(analytics, scouting, market)

        if max_trait < self.DOMINANT_THRESHOLD:
            return GMStyle.BALANCED

        if analytics == max_trait:
            return GMStyle.ANALYTICS_HEAVY
        elif scouting == max_trait:
            return GMStyle.SCOUT_FOCUSED
        elif market == max_trait:
            return GMStyle.MARKET_DRIVEN
        else:
            return GMStyle.BALANCED

    def _generate_rationale(
        self,
        weights: FactorWeights,
        dominant_style: GMStyle,
        analytics: float,
        scouting: float,
        market: float,
    ) -> str:
        """
        Generate human-readable explanation of weight distribution.

        Args:
            weights: Calculated factor weights
            dominant_style: Determined dominant style
            analytics: Raw analytics preference
            scouting: Raw scouting preference
            market: Raw market awareness

        Returns:
            Human-readable rationale string
        """
        # Style intro phrases
        style_intros = {
            GMStyle.ANALYTICS_HEAVY: "Analytics-focused GM prioritizes",
            GMStyle.SCOUT_FOCUSED: "Scout-focused GM emphasizes",
            GMStyle.BALANCED: "Balanced GM considers",
            GMStyle.MARKET_DRIVEN: "Market-driven GM follows",
        }

        # Primary factor based on highest weight
        weight_map = {
            "statistical performance": weights.stats_weight,
            "scouting reports": weights.scouting_weight,
            "market comparables": weights.market_weight,
        }
        primary_factor = max(weight_map, key=weight_map.get)
        primary_weight = weight_map[primary_factor]

        # Secondary factor (second highest)
        remaining = {k: v for k, v in weight_map.items() if k != primary_factor}
        secondary_factor = max(remaining, key=remaining.get)

        # Format percentages
        stats_pct = int(weights.stats_weight * 100)
        scouting_pct = int(weights.scouting_weight * 100)
        market_pct = int(weights.market_weight * 100)
        rating_pct = int(weights.rating_weight * 100)

        # Dominant trait context
        max_raw = max(analytics, scouting, market)
        if max_raw < self.DOMINANT_THRESHOLD:
            trait_context = "No dominant preference leads to balanced weighting."
        elif analytics == max_raw:
            trait_context = f"Strong analytics preference ({int(analytics * 100)}%) drives valuation."
        elif scouting == max_raw:
            trait_context = f"Strong scouting preference ({int(scouting * 100)}%) drives valuation."
        else:
            trait_context = f"Strong market awareness ({int(market * 100)}%) drives valuation."

        # Build rationale
        intro = style_intros.get(dominant_style, "GM considers")
        rationale = (
            f"{intro} {primary_factor} ({stats_pct}% stats weight) with secondary "
            f"emphasis on {secondary_factor}. Weight distribution: Stats {stats_pct}%, "
            f"Scouting {scouting_pct}%, Market {market_pct}%, Rating {rating_pct}%. "
            f"{trait_context}"
        )

        return rationale