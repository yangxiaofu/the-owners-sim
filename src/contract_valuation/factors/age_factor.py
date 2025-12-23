"""
Age-based valuation factor.

Applies age premiums/discounts based on position peak ranges
and development curves.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from contract_valuation.models import FactorResult
from contract_valuation.context import ValuationContext
from contract_valuation.factors.base import ValueFactor


class AgeFactor(ValueFactor):
    """
    Valuation factor based on player age relative to peak performance window.

    Applies premiums for young players approaching peak and discounts
    for veterans past their prime. Uses archetype-specific peak ranges
    when available, otherwise falls back to position defaults.

    Confidence: 0.75 base, +0.05 if archetype peak range available
    """

    # Default peak age ranges by position
    DEFAULT_PEAK_AGES = {
        "QB": (28, 33),
        "RB": (24, 27),
        "WR": (26, 30),
        "TE": (26, 30),
        "OT": (27, 32),
        "OG": (26, 31),
        "C": (26, 31),
        "LT": (27, 32),
        "RT": (27, 32),
        "LG": (26, 31),
        "RG": (26, 31),
        "EDGE": (26, 30),
        "DT": (26, 30),
        "LE": (26, 30),
        "RE": (26, 30),
        "LB": (25, 29),
        "LOLB": (25, 29),
        "MLB": (25, 29),
        "ROLB": (25, 29),
        "CB": (25, 29),
        "S": (26, 30),
        "FS": (26, 30),
        "SS": (26, 30),
        "K": (28, 38),
        "P": (28, 38),
    }

    # Development curve adjustments (shifts peak window)
    CURVE_ADJUSTMENTS = {
        "early": -1,    # Peaks 1 year earlier
        "normal": 0,    # Standard peak range
        "late": 1,      # Peaks 1 year later
    }

    # Age modifiers
    PREMIUM_PER_YEAR = 0.02   # +2% per year before peak
    DISCOUNT_PER_YEAR = 0.04  # -4% per year after peak
    MAX_PREMIUM = 0.15        # Cap at +15%
    MAX_DISCOUNT = 0.30       # Cap at -30%

    # Archetypes directory
    ARCHETYPES_DIR = Path(__file__).parent.parent.parent.parent / "config" / "archetypes"

    def __init__(self, archetypes_path: Optional[Path] = None):
        """
        Initialize AgeFactor.

        Args:
            archetypes_path: Optional custom path to archetypes directory
        """
        self._archetypes_path = archetypes_path or self.ARCHETYPES_DIR
        self._archetype_cache: Dict[str, Dict[str, Any]] = {}

    @property
    def factor_name(self) -> str:
        """Return factor identifier."""
        return "age"

    def calculate(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext
    ) -> FactorResult:
        """
        Calculate AAV adjustment based on age relative to peak.

        Args:
            player_data: Must contain 'position', 'overall_rating'
                        Should contain 'age' or 'birthdate'
                        Optional: 'archetype', 'development_curve'
            context: Market context with position rates

        Returns:
            FactorResult with age-adjusted AAV estimate

        Raises:
            ValueError: If required fields missing
        """
        self.validate_player_data(player_data)
        self._validate_age_data(player_data)

        position = player_data["position"].upper()
        rating = player_data["overall_rating"]

        # Extract age
        age = self._extract_age(player_data, context)
        if age is None:
            return self._fallback_result(player_data, context)

        # Get archetype if available
        archetype = player_data.get("archetype")
        development_curve = player_data.get("development_curve", "normal")

        # Get peak age range
        peak_start, peak_end, archetype_used = self._get_peak_range(
            position, archetype, development_curve
        )

        # Calculate age modifier
        modifier = self._calculate_age_modifier(age, peak_start, peak_end)

        # Get baseline AAV from tier
        tier = self.get_position_tier(position, rating, context)
        base_rate = context.get_market_rate(position, tier)
        if base_rate is None:
            base_rate = int(context.salary_cap * 0.01)  # 1% fallback

        # Apply modifier
        final_aav = int(base_rate * (1 + modifier))

        # Confidence: higher if archetype available
        confidence = 0.80 if archetype_used else 0.75

        breakdown = {
            "position": position,
            "age": age,
            "rating": rating,
            "tier": tier,
            "archetype": archetype,
            "archetype_used": archetype_used,
            "development_curve": development_curve,
            "peak_start": peak_start,
            "peak_end": peak_end,
            "age_modifier": round(modifier, 3),
            "base_rate": base_rate,
            "final_aav": final_aav,
        }

        return FactorResult(
            name=self.factor_name,
            raw_value=final_aav,
            confidence=confidence,
            breakdown=breakdown,
        )

    def _validate_age_data(self, player_data: Dict[str, Any]) -> None:
        """Validate age-specific fields."""
        if "overall_rating" not in player_data:
            raise ValueError("Missing required field: overall_rating")

        rating = player_data["overall_rating"]
        if not isinstance(rating, int) or not 0 <= rating <= 99:
            raise ValueError(f"overall_rating must be int 0-99, got {rating}")

    def _extract_age(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext
    ) -> Optional[int]:
        """
        Extract player age from age field or birthdate.

        Args:
            player_data: Player data dict
            context: Context with current season

        Returns:
            Player age as int, or None if not determinable
        """
        # Direct age field
        if "age" in player_data:
            age = player_data["age"]
            if isinstance(age, int) and 18 <= age <= 50:
                return age

        # Calculate from birthdate
        birthdate = player_data.get("birthdate")
        if birthdate:
            try:
                if isinstance(birthdate, str):
                    birth = datetime.strptime(birthdate, "%Y-%m-%d")
                    # Use season year for age calculation
                    reference_date = datetime(context.season, 9, 1)  # Sept 1 of season
                    age = (reference_date - birth).days // 365
                    if 18 <= age <= 50:
                        return age
            except (ValueError, TypeError):
                pass

        return None

    def _get_peak_range(
        self,
        position: str,
        archetype: Optional[str],
        development_curve: str
    ) -> Tuple[int, int, bool]:
        """
        Get peak age range for position/archetype.

        Args:
            position: Player position
            archetype: Optional archetype name
            development_curve: Development curve type

        Returns:
            Tuple of (peak_start, peak_end, archetype_used)
        """
        archetype_used = False

        # Try to load archetype-specific peak range
        if archetype:
            archetype_data = self._load_archetype(archetype)
            if archetype_data and "peak_age_range" in archetype_data:
                peak_range = archetype_data["peak_age_range"]
                if isinstance(peak_range, list) and len(peak_range) == 2:
                    archetype_used = True
                    peak_start, peak_end = peak_range[0], peak_range[1]
                    # Apply development curve adjustment
                    curve_adj = self.CURVE_ADJUSTMENTS.get(development_curve, 0)
                    return peak_start + curve_adj, peak_end + curve_adj, archetype_used

        # Fall back to position defaults
        peak_start, peak_end = self.DEFAULT_PEAK_AGES.get(position, (26, 30))

        # Apply development curve adjustment
        curve_adj = self.CURVE_ADJUSTMENTS.get(development_curve, 0)
        return peak_start + curve_adj, peak_end + curve_adj, archetype_used

    def _load_archetype(self, archetype: str) -> Optional[Dict[str, Any]]:
        """
        Load archetype configuration from JSON.

        Args:
            archetype: Archetype name (e.g., "pocket_passer_qb")

        Returns:
            Archetype config dict or None if not found
        """
        if archetype in self._archetype_cache:
            return self._archetype_cache[archetype]

        archetype_file = self._archetypes_path / f"{archetype.lower()}.json"
        if archetype_file.exists():
            try:
                with open(archetype_file, "r") as f:
                    data = json.load(f)
                    self._archetype_cache[archetype] = data
                    return data
            except (json.JSONDecodeError, IOError):
                pass

        return None

    def _calculate_age_modifier(
        self,
        age: int,
        peak_start: int,
        peak_end: int
    ) -> float:
        """
        Calculate age-based value modifier.

        Args:
            age: Player's current age
            peak_start: Start of peak performance window
            peak_end: End of peak performance window

        Returns:
            Modifier as float (positive for premium, negative for discount)
        """
        if age < peak_start:
            # Young player premium
            years_before_peak = peak_start - age
            premium = years_before_peak * self.PREMIUM_PER_YEAR
            return min(self.MAX_PREMIUM, premium)
        elif age > peak_end:
            # Veteran discount
            years_after_peak = age - peak_end
            discount = years_after_peak * self.DISCOUNT_PER_YEAR
            return -min(self.MAX_DISCOUNT, discount)
        else:
            # In prime - no adjustment
            return 0.0

    def _fallback_result(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext
    ) -> FactorResult:
        """
        Return fallback result when age cannot be determined.

        Uses base market rate with low confidence.
        """
        position = player_data["position"].upper()
        rating = player_data["overall_rating"]
        tier = self.get_position_tier(position, rating, context)

        base_rate = context.get_market_rate(position, tier)
        if base_rate is None:
            base_rate = int(context.salary_cap * 0.01)

        return FactorResult(
            name=self.factor_name,
            raw_value=base_rate,
            confidence=0.50,
            breakdown={
                "position": position,
                "rating": rating,
                "tier": tier,
                "age": None,
                "age_unknown": True,
                "base_rate": base_rate,
                "final_aav": base_rate,
            },
        )
