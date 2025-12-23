"""
Abstract base class for valuation factors.

Provides the interface that all valuation factors must implement.
Each factor produces an independent AAV estimate based on different data sources.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from contract_valuation.models import FactorResult
from contract_valuation.context import ValuationContext


class ValueFactor(ABC):
    """
    Abstract base class for contract valuation factors.

    Each factor analyzes different aspects of a player to produce
    an AAV estimate. The engine combines these using GM-determined weights.

    Subclasses must implement:
    - factor_name: Unique identifier for this factor
    - calculate(): Produce a FactorResult with AAV estimate

    Example implementations:
    - StatsBasedFactor: Uses statistical performance metrics
    - ScoutingFactor: Uses scouting grades and eye test
    - MarketFactor: Uses comparable contracts
    - RatingFactor: Uses overall player rating
    """

    @property
    @abstractmethod
    def factor_name(self) -> str:
        """
        Unique identifier for this factor.

        Used as key in factor_contributions dict and for audit trails.
        Should be lowercase with underscores (e.g., "stats_based", "scouting").

        Returns:
            Factor identifier string
        """
        pass

    @abstractmethod
    def calculate(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext
    ) -> FactorResult:
        """
        Calculate AAV estimate from this factor's perspective.

        Args:
            player_data: Player information dict containing:
                - player_id: int
                - name: str
                - position: str
                - age: int
                - overall_rating: int (0-99)
                - stats: Dict[str, Any] (season statistics)
                - scouting_grades: Dict[str, int] (optional)
                - contract_year: bool (optional)
            context: Market context with cap, rates, and season info

        Returns:
            FactorResult with:
            - name: Same as factor_name
            - raw_value: AAV estimate in dollars
            - confidence: 0.0-1.0 reliability score
            - breakdown: Calculation audit trail

        Raises:
            ValueError: If required player_data fields are missing
        """
        pass

    def validate_player_data(self, player_data: Dict[str, Any]) -> None:
        """
        Validate that required player data fields are present.

        Args:
            player_data: Player information dict

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ["player_id", "name", "position"]
        missing = [f for f in required_fields if f not in player_data]
        if missing:
            raise ValueError(f"Missing required player_data fields: {missing}")

    def get_position_tier(
        self,
        position: str,
        rating: int,
        context: ValuationContext
    ) -> str:
        """
        Determine contract tier based on position and rating.

        Utility method for factors that need tier classification.

        Args:
            position: Player position (e.g., "QB", "WR")
            rating: Overall rating (0-99)
            context: Market context (unused but available for future)

        Returns:
            Tier string: "backup", "starter", "quality", or "elite"
        """
        if rating >= 90:
            return "elite"
        elif rating >= 80:
            return "quality"
        elif rating >= 70:
            return "starter"
        else:
            return "backup"