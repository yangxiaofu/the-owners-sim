"""
GM valuation style definitions.

Provides the GMStyle enum that maps GM personality traits
to valuation factor weights.
"""

from enum import Enum
from typing import TYPE_CHECKING, Optional

from contract_valuation.models import FactorWeights

if TYPE_CHECKING:
    from team_management.gm_archetype import GMArchetype


class GMStyle(Enum):
    """
    GM valuation style classification.

    Determines how different valuation factors are weighted
    when calculating player contract values.

    Styles:
    - ANALYTICS_HEAVY: Trusts stats and metrics most
    - SCOUT_FOCUSED: Trusts scouting reports and eye test
    - BALANCED: Even weighting across all factors
    - MARKET_DRIVEN: Follows market rates closely

    Each style maps to a FactorWeights configuration.
    """

    ANALYTICS_HEAVY = "analytics_heavy"
    SCOUT_FOCUSED = "scout_focused"
    BALANCED = "balanced"
    MARKET_DRIVEN = "market_driven"

    def get_weights(self) -> FactorWeights:
        """
        Get the factor weights for this GM style.

        Returns:
            FactorWeights instance configured for this style
        """
        if self == GMStyle.ANALYTICS_HEAVY:
            return FactorWeights.create_analytics_heavy()
        elif self == GMStyle.SCOUT_FOCUSED:
            return FactorWeights.create_scout_focused()
        elif self == GMStyle.MARKET_DRIVEN:
            return FactorWeights.create_market_driven()
        else:
            return FactorWeights.create_balanced()

    def get_description(self) -> str:
        """
        Get human-readable description of this style.

        Returns:
            Description string explaining the style's approach
        """
        descriptions = {
            GMStyle.ANALYTICS_HEAVY: (
                "Heavily weights statistical performance and advanced metrics. "
                "May undervalue intangibles but rarely overpays for declining players."
            ),
            GMStyle.SCOUT_FOCUSED: (
                "Trusts scouting reports and the eye test over raw numbers. "
                "May find hidden gems but also prone to narrative-driven valuations."
            ),
            GMStyle.BALANCED: (
                "Considers all factors evenly without strong biases. "
                "Produces market-rate valuations with moderate risk."
            ),
            GMStyle.MARKET_DRIVEN: (
                "Closely tracks comparable contracts and market trends. "
                "Rarely over or underpays but may miss value opportunities."
            ),
        }
        return descriptions.get(self, "Unknown style")

    @classmethod
    def from_archetype(cls, archetype: "GMArchetype") -> "GMStyle":
        """
        Determine GM style from archetype traits.

        Analyzes the GM's analytics_preference, scouting_preference,
        and market_awareness traits to classify their valuation style.

        Args:
            archetype: GMArchetype instance with valuation traits

        Returns:
            GMStyle that best matches the archetype's tendencies
        """
        # Get trait values with defaults if not present
        analytics = getattr(archetype, "analytics_preference", 0.5)
        scouting = getattr(archetype, "scouting_preference", 0.5)
        market = getattr(archetype, "market_awareness", 0.5)

        # Find dominant trait
        max_trait = max(analytics, scouting, market)
        threshold = 0.6  # Must exceed this to be considered dominant

        if max_trait < threshold:
            # No dominant trait, use balanced
            return cls.BALANCED

        if analytics == max_trait and analytics >= threshold:
            return cls.ANALYTICS_HEAVY
        elif scouting == max_trait and scouting >= threshold:
            return cls.SCOUT_FOCUSED
        elif market == max_trait and market >= threshold:
            return cls.MARKET_DRIVEN
        else:
            return cls.BALANCED

    @classmethod
    def from_string(cls, style_str: str) -> Optional["GMStyle"]:
        """
        Create GMStyle from string value.

        Args:
            style_str: Style identifier (e.g., "analytics_heavy")

        Returns:
            GMStyle if valid, None otherwise
        """
        try:
            return cls(style_str)
        except ValueError:
            return None