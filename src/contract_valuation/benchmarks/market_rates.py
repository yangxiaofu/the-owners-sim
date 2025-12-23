"""
Market rates by position and tier for contract valuation.

Provides AAV lookup for all 25 NFL positions with cap inflation
adjustments and position demand multipliers.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path
import json


@dataclass
class PositionMarketRate:
    """
    Market rates for a single position across all tiers.

    Attributes:
        position: Position abbreviation (e.g., "QB")
        backup: AAV for backup-tier players
        starter: AAV for starter-tier players
        quality: AAV for quality-tier players
        elite: AAV for elite-tier players
        market_heat: Position demand multiplier (0.85-1.15)
    """

    position: str
    backup: int
    starter: int
    quality: int
    elite: int
    market_heat: float = 1.0

    def get_rate(self, tier: str) -> int:
        """
        Get rate for a specific tier.

        Args:
            tier: Contract tier ("backup", "starter", "quality", "elite")

        Returns:
            AAV in dollars
        """
        tier_map = {
            "backup": self.backup,
            "starter": self.starter,
            "quality": self.quality,
            "elite": self.elite,
        }
        return tier_map.get(tier.lower(), self.starter)


class MarketRates:
    """
    Centralized NFL market rates by position and tier.

    Provides AAV lookup for all 25 positions with cap inflation
    adjustments and position demand multipliers.

    Usage:
        rates = MarketRates(season=2025)
        aav = rates.get_rate("QB", "elite")  # 50_000_000
        aav_2026 = rates.get_rate("QB", "elite", season=2026)  # Adjusted
        heat = rates.get_market_heat("RB")  # 0.92
    """

    # Base season for market rates (without inflation)
    BASE_SEASON = 2025

    # Annual cap inflation rate (approximately 7-10% historically)
    CAP_INFLATION_RATE = 0.08

    # Position group mappings for positions without direct rates
    POSITION_GROUPS: Dict[str, str] = {
        "LOLB": "EDGE",
        "ROLB": "EDGE",
        "LE": "EDGE",
        "RE": "EDGE",
        "MLB": "LB",
        "FS": "S",
        "SS": "S",
        # Note: LT, RT, LG, RG have their own rates, not mapped
    }

    # All 25 positions from CLAUDE.md
    ALL_POSITIONS = {
        "QB", "RB", "FB", "WR", "TE",
        "LT", "LG", "C", "RG", "RT",
        "LE", "DT", "RE",
        "LOLB", "MLB", "ROLB",
        "CB", "FS", "SS",
        "K", "P", "KR", "PR", "LS",
        "EDGE",
        # Additional generic positions
        "OT", "OG", "LB", "S",
    }

    def __init__(self, season: int = 2025):
        """
        Initialize market rates.

        Args:
            season: Season year for rate calculations
        """
        self._season = season
        self._rates = self._load_default_rates()

    def get_rate(
        self,
        position: str,
        tier: str = "starter",
        season: Optional[int] = None,
    ) -> Optional[int]:
        """
        Get market AAV for position and tier.

        Args:
            position: Player position (e.g., "QB", "LOLB")
            tier: Contract tier ("backup", "starter", "quality", "elite")
            season: Optional season for inflation adjustment

        Returns:
            AAV in dollars, or None if position not found
        """
        rate_position = self.get_position_with_rates(position)
        if rate_position not in self._rates:
            return None

        pos_rate = self._rates[rate_position]
        base_aav = pos_rate.get_rate(tier)

        target_season = season if season is not None else self._season
        if target_season != self.BASE_SEASON:
            base_aav = self.adjust_for_inflation(base_aav, target_season)

        return base_aav

    def get_all_rates(self, position: str) -> Optional[PositionMarketRate]:
        """
        Get all tier rates for a position.

        Args:
            position: Player position

        Returns:
            PositionMarketRate or None if not found
        """
        rate_position = self.get_position_with_rates(position)
        return self._rates.get(rate_position)

    def get_market_heat(self, position: str) -> float:
        """
        Get market heat multiplier for position demand.

        Args:
            position: Player position

        Returns:
            Multiplier (0.85-1.15 range typically)
        """
        rate_position = self.get_position_with_rates(position)
        pos_rate = self._rates.get(rate_position)
        if pos_rate:
            return pos_rate.market_heat
        return 1.0

    def get_position_with_rates(self, position: str) -> str:
        """
        Get the position key that has market rates.

        Maps specific positions to groups if needed.

        Args:
            position: Player position

        Returns:
            Position key with market rates
        """
        upper = position.upper()

        # Check direct rates first
        if upper in self._rates:
            return upper

        # Check position group mappings
        if upper in self.POSITION_GROUPS:
            return self.POSITION_GROUPS[upper]

        return upper

    def adjust_for_inflation(self, base_aav: int, target_season: int) -> int:
        """
        Adjust AAV for cap inflation.

        Args:
            base_aav: Base AAV (from BASE_SEASON)
            target_season: Target season year

        Returns:
            Inflation-adjusted AAV
        """
        years_diff = target_season - self.BASE_SEASON
        if years_diff == 0:
            return base_aav

        multiplier = (1 + self.CAP_INFLATION_RATE) ** years_diff
        return int(base_aav * multiplier)

    def get_tier_for_rating(self, rating: int) -> str:
        """
        Map overall rating to contract tier.

        Args:
            rating: Overall player rating (0-99)

        Returns:
            Contract tier string
        """
        if rating >= 90:
            return "elite"
        elif rating >= 80:
            return "quality"
        elif rating >= 70:
            return "starter"
        else:
            return "backup"

    def has_rates(self, position: str) -> bool:
        """
        Check if position has market rates.

        Args:
            position: Player position

        Returns:
            True if rates exist (directly or via mapping)
        """
        rate_position = self.get_position_with_rates(position)
        return rate_position in self._rates

    @staticmethod
    def _load_default_rates() -> Dict[str, PositionMarketRate]:
        """
        Load hardcoded 2025 market rates.

        Returns:
            Dict mapping position -> PositionMarketRate
        """
        return {
            # Premium Positions
            "QB": PositionMarketRate(
                "QB", 3_000_000, 15_000_000, 35_000_000, 50_000_000, 1.10
            ),
            "EDGE": PositionMarketRate(
                "EDGE", 3_000_000, 10_000_000, 18_000_000, 28_000_000, 1.08
            ),
            "WR": PositionMarketRate(
                "WR", 2_000_000, 8_000_000, 18_000_000, 28_000_000, 1.03
            ),
            "CB": PositionMarketRate(
                "CB", 2_000_000, 8_000_000, 15_000_000, 22_000_000, 1.05
            ),
            # Offensive Line
            "OT": PositionMarketRate(
                "OT", 2_000_000, 10_000_000, 18_000_000, 25_000_000, 1.02
            ),
            "LT": PositionMarketRate(
                "LT", 2_500_000, 12_000_000, 20_000_000, 27_000_000, 1.05
            ),
            "RT": PositionMarketRate(
                "RT", 2_000_000, 9_000_000, 16_000_000, 23_000_000, 1.00
            ),
            "OG": PositionMarketRate(
                "OG", 1_500_000, 6_000_000, 12_000_000, 18_000_000, 0.98
            ),
            "LG": PositionMarketRate(
                "LG", 1_500_000, 6_000_000, 12_000_000, 18_000_000, 0.98
            ),
            "RG": PositionMarketRate(
                "RG", 1_500_000, 6_000_000, 12_000_000, 18_000_000, 0.98
            ),
            "C": PositionMarketRate(
                "C", 1_500_000, 6_000_000, 12_000_000, 16_000_000, 0.98
            ),
            # Skill Positions
            "RB": PositionMarketRate(
                "RB", 1_000_000, 4_000_000, 8_000_000, 14_000_000, 0.92
            ),
            "TE": PositionMarketRate(
                "TE", 1_500_000, 6_000_000, 12_000_000, 18_000_000, 1.00
            ),
            "FB": PositionMarketRate(
                "FB", 1_000_000, 2_000_000, 3_500_000, 5_000_000, 0.85
            ),
            # Defensive Line
            "DT": PositionMarketRate(
                "DT", 2_000_000, 8_000_000, 14_000_000, 22_000_000, 1.00
            ),
            # Linebackers
            "LB": PositionMarketRate(
                "LB", 2_000_000, 8_000_000, 14_000_000, 20_000_000, 0.95
            ),
            # Secondary
            "S": PositionMarketRate(
                "S", 1_500_000, 6_000_000, 12_000_000, 16_000_000, 1.00
            ),
            # Special Teams
            "K": PositionMarketRate(
                "K", 1_000_000, 3_000_000, 5_000_000, 7_000_000, 0.90
            ),
            "P": PositionMarketRate(
                "P", 1_000_000, 2_500_000, 4_000_000, 5_500_000, 0.90
            ),
            "LS": PositionMarketRate(
                "LS", 500_000, 1_000_000, 1_500_000, 2_000_000, 0.85
            ),
        }


def load_nfl_contracts(filepath: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Load real NFL contract examples from JSON.

    Args:
        filepath: Path to nfl_contracts.json (default: module directory)

    Returns:
        List of contract dictionaries

    Raises:
        FileNotFoundError: If JSON file not found
        json.JSONDecodeError: If JSON is invalid
    """
    if filepath is None:
        filepath = Path(__file__).parent / "nfl_contracts.json"

    with open(filepath, "r") as f:
        data = json.load(f)

    return data.get("contracts", [])


def get_contract_metadata(filepath: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load metadata from NFL contracts JSON.

    Args:
        filepath: Path to nfl_contracts.json

    Returns:
        Metadata dictionary with source, last_updated, cap_year
    """
    if filepath is None:
        filepath = Path(__file__).parent / "nfl_contracts.json"

    with open(filepath, "r") as f:
        data = json.load(f)

    return data.get("metadata", {})
