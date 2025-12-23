"""
Scouting-based valuation factor.

Synthesizes "scouting grades" from position-specific attributes
since no explicit grades exist in the player data.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from contract_valuation.models import FactorResult
from contract_valuation.context import ValuationContext
from contract_valuation.factors.base import ValueFactor


class ScoutingFactor(ValueFactor):
    """
    Valuation factor based on synthesized scouting grades.

    Analyzes position-specific attributes, physical traits, and mental
    attributes to produce a composite grade that maps to AAV.

    Young players (<27) weight potential higher, veterans weight
    current ability higher.

    Confidence: 0.65 base + 0.01 per key attribute found,
                -0.05 for young players (more projection uncertainty)
    """

    # Position-specific key attributes
    POSITION_KEY_ATTRS = {
        "QB": ["accuracy", "arm_strength", "pocket_presence", "composure", "vision"],
        "RB": ["speed", "elusiveness", "vision", "carrying", "acceleration"],
        "WR": ["speed", "hands", "route_running", "release", "acceleration"],
        "TE": ["blocking", "hands", "speed", "route_running", "strength"],
        "OT": ["pass_blocking", "run_blocking", "strength", "footwork", "awareness"],
        "LT": ["pass_blocking", "run_blocking", "strength", "footwork", "awareness"],
        "RT": ["pass_blocking", "run_blocking", "strength", "footwork", "awareness"],
        "OG": ["run_blocking", "pass_blocking", "strength", "awareness", "power"],
        "LG": ["run_blocking", "pass_blocking", "strength", "awareness", "power"],
        "RG": ["run_blocking", "pass_blocking", "strength", "awareness", "power"],
        "C": ["pass_blocking", "run_blocking", "awareness", "strength", "leadership"],
        "EDGE": ["pass_rush", "speed", "strength", "finesse_moves", "power_moves"],
        "LE": ["pass_rush", "speed", "strength", "finesse_moves", "power_moves"],
        "RE": ["pass_rush", "speed", "strength", "finesse_moves", "power_moves"],
        "LOLB": ["pass_rush", "coverage", "speed", "tackling", "awareness"],
        "ROLB": ["pass_rush", "coverage", "speed", "tackling", "awareness"],
        "DT": ["block_shedding", "strength", "power_moves", "tackling", "awareness"],
        "MLB": ["tackling", "coverage", "awareness", "speed", "pursuit"],
        "LB": ["tackling", "coverage", "awareness", "speed", "pursuit"],
        "CB": ["coverage", "speed", "press", "agility", "ball_skills"],
        "S": ["coverage", "tackling", "speed", "awareness", "zone_coverage"],
        "FS": ["coverage", "speed", "awareness", "ball_skills", "range"],
        "SS": ["tackling", "coverage", "strength", "awareness", "run_support"],
        "K": ["kick_power", "kick_accuracy", "composure", "consistency"],
        "P": ["kick_power", "kick_accuracy", "composure", "consistency"],
    }

    # Physical attributes for all positions
    PHYSICAL_ATTRS = ["speed", "strength", "agility", "stamina", "acceleration"]

    # Mental attributes for all positions
    MENTAL_ATTRS = ["awareness", "discipline", "composure", "experience", "football_iq"]

    # Young player threshold
    YOUNG_AGE_THRESHOLD = 27

    # Tier thresholds for composite grade
    GRADE_THRESHOLDS = {
        "elite": 88,
        "quality": 78,
        "starter": 68,
        "backup": 0,
    }

    @property
    def factor_name(self) -> str:
        """Return factor identifier."""
        return "scouting"

    def calculate(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext
    ) -> FactorResult:
        """
        Calculate AAV based on synthesized scouting grades.

        Args:
            player_data: Must contain 'position'
                        Should contain 'attributes' dict
                        Optional: 'age', 'birthdate', 'potential'
            context: Market context with position rates

        Returns:
            FactorResult with AAV estimate

        Raises:
            ValueError: If required fields missing
        """
        self.validate_player_data(player_data)

        position = player_data["position"].upper()
        attributes = player_data.get("attributes", {})

        # Handle case where attributes is not a dict or is empty
        if not isinstance(attributes, dict) or not attributes:
            return self._fallback_result(player_data, context)

        # Extract age and potential
        age = self._extract_age(player_data, context)
        potential = attributes.get("potential", 75)
        overall = attributes.get("overall", 75)

        # Calculate component grades
        position_grade = self._grade_position_attributes(position, attributes)
        physical_grade = self._grade_physical(attributes)
        mental_grade = self._grade_mental(attributes)

        # Calculate upside for young players
        upside = self._calculate_upside(overall, potential, age)

        # Weight grades based on age
        is_young = age is not None and age < self.YOUNG_AGE_THRESHOLD
        composite = self._calculate_composite(
            position_grade, physical_grade, mental_grade,
            potential, upside, is_young
        )

        # Map composite to tier
        tier = self._grade_to_tier(composite)

        # Get market rate for tier
        base_rate = context.get_market_rate(position, tier)
        if base_rate is None:
            base_rate = self._calculate_fallback_rate(context, tier)

        # Apply composite scaling within tier
        final_aav = self._apply_composite_scaling(base_rate, composite, tier)

        # Calculate confidence
        confidence = self._calculate_confidence(position, attributes, is_young)

        breakdown = {
            "position": position,
            "age": age,
            "is_young": is_young,
            "overall": overall,
            "potential": potential,
            "position_grade": round(position_grade, 1),
            "physical_grade": round(physical_grade, 1),
            "mental_grade": round(mental_grade, 1),
            "upside": round(upside, 1),
            "composite_grade": round(composite, 1),
            "tier": tier,
            "base_rate": base_rate,
            "final_aav": final_aav,
        }

        return FactorResult(
            name=self.factor_name,
            raw_value=final_aav,
            confidence=confidence,
            breakdown=breakdown,
        )

    def _extract_age(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext
    ) -> Optional[int]:
        """Extract player age from age field or birthdate."""
        if "age" in player_data:
            age = player_data["age"]
            if isinstance(age, int) and 18 <= age <= 50:
                return age

        birthdate = player_data.get("birthdate")
        if birthdate:
            try:
                if isinstance(birthdate, str):
                    birth = datetime.strptime(birthdate, "%Y-%m-%d")
                    reference_date = datetime(context.season, 9, 1)
                    age = (reference_date - birth).days // 365
                    if 18 <= age <= 50:
                        return age
            except (ValueError, TypeError):
                pass

        return None

    def _grade_position_attributes(
        self,
        position: str,
        attributes: Dict[str, Any]
    ) -> float:
        """
        Grade position-specific attributes.

        Returns average of key attributes for position.
        Uses overall as fallback if key attributes missing.
        """
        key_attrs = self.POSITION_KEY_ATTRS.get(position, [])
        if not key_attrs:
            return attributes.get("overall", 75)

        values = []
        for attr in key_attrs:
            if attr in attributes and isinstance(attributes[attr], (int, float)):
                values.append(attributes[attr])

        if not values:
            return attributes.get("overall", 75)

        return sum(values) / len(values)

    def _grade_physical(self, attributes: Dict[str, Any]) -> float:
        """Grade physical attributes."""
        values = []
        for attr in self.PHYSICAL_ATTRS:
            if attr in attributes and isinstance(attributes[attr], (int, float)):
                values.append(attributes[attr])

        if not values:
            return attributes.get("overall", 75)

        return sum(values) / len(values)

    def _grade_mental(self, attributes: Dict[str, Any]) -> float:
        """Grade mental attributes."""
        values = []
        for attr in self.MENTAL_ATTRS:
            if attr in attributes and isinstance(attributes[attr], (int, float)):
                values.append(attributes[attr])

        if not values:
            return attributes.get("overall", 75)

        return sum(values) / len(values)

    def _calculate_upside(
        self,
        overall: int,
        potential: int,
        age: Optional[int]
    ) -> float:
        """
        Calculate upside/projection score.

        Higher for young players with high potential relative to current.
        """
        if age is None or age >= self.YOUNG_AGE_THRESHOLD:
            return overall  # Established players = current ability

        # Gap between potential and current
        potential_gap = max(0, potential - overall)

        # Years to develop (assuming 27 is peak for projection)
        years_to_develop = max(0, self.YOUNG_AGE_THRESHOLD - age)

        # Upside is current + portion of gap they can close
        development_factor = min(1.0, years_to_develop * 0.15)
        upside = overall + (potential_gap * development_factor)

        return min(99, upside)

    def _calculate_composite(
        self,
        position_grade: float,
        physical_grade: float,
        mental_grade: float,
        potential: int,
        upside: float,
        is_young: bool
    ) -> float:
        """
        Calculate weighted composite grade.

        Young players weight potential/upside more heavily.
        Veterans weight current ability more heavily.
        """
        if is_young:
            # Young player weights: position 35%, physical 20%, mental 10%,
            # potential 20%, upside 15%
            composite = (
                position_grade * 0.35 +
                physical_grade * 0.20 +
                mental_grade * 0.10 +
                potential * 0.20 +
                upside * 0.15
            )
        else:
            # Veteran weights: position 45%, physical 25%, mental 20%,
            # potential 10%
            composite = (
                position_grade * 0.45 +
                physical_grade * 0.25 +
                mental_grade * 0.20 +
                potential * 0.10
            )

        return composite

    def _grade_to_tier(self, composite: float) -> str:
        """Map composite grade to tier."""
        if composite >= self.GRADE_THRESHOLDS["elite"]:
            return "elite"
        elif composite >= self.GRADE_THRESHOLDS["quality"]:
            return "quality"
        elif composite >= self.GRADE_THRESHOLDS["starter"]:
            return "starter"
        else:
            return "backup"

    def _calculate_fallback_rate(self, context: ValuationContext, tier: str) -> int:
        """Calculate fallback rate using cap percentage."""
        cap_pcts = {
            "elite": 0.05,
            "quality": 0.025,
            "starter": 0.01,
            "backup": 0.001,
        }
        cap_pct = cap_pcts.get(tier, 0.01)
        return int(context.salary_cap * cap_pct)

    def _apply_composite_scaling(
        self,
        base_rate: int,
        composite: float,
        tier: str
    ) -> int:
        """Apply scaling within tier based on composite grade."""
        tier_ranges = {
            "elite": (88, 99),
            "quality": (78, 87),
            "starter": (68, 77),
            "backup": (50, 67),
        }

        tier_min, tier_max = tier_ranges.get(tier, (50, 99))
        tier_range = tier_max - tier_min

        if tier_range <= 0:
            return base_rate

        # Position within tier (0.0 to 1.0)
        clamped_composite = max(tier_min, min(tier_max, composite))
        position_in_tier = (clamped_composite - tier_min) / tier_range

        # Scale from 0.90x to 1.10x
        scale_factor = 0.90 + (position_in_tier * 0.20)

        return int(base_rate * scale_factor)

    def _calculate_confidence(
        self,
        position: str,
        attributes: Dict[str, Any],
        is_young: bool
    ) -> float:
        """
        Calculate confidence based on available attributes.

        Base 0.65 + 0.01 per key attribute found - 0.05 for young players.
        """
        base_confidence = 0.65

        # Count available key attributes
        key_attrs = self.POSITION_KEY_ATTRS.get(position, [])
        found_count = sum(1 for attr in key_attrs if attr in attributes)
        attr_bonus = min(0.15, found_count * 0.01)

        # Young player penalty (more projection uncertainty)
        young_penalty = 0.05 if is_young else 0.0

        confidence = base_confidence + attr_bonus - young_penalty
        return max(0.35, min(0.85, confidence))

    def _fallback_result(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext
    ) -> FactorResult:
        """Return fallback result when no attributes available."""
        position = player_data["position"].upper()

        # Use position average as fallback
        base_rate = context.get_market_rate(position, "starter")
        if base_rate is None:
            base_rate = int(context.salary_cap * 0.01)

        return FactorResult(
            name=self.factor_name,
            raw_value=base_rate,
            confidence=0.35,
            breakdown={
                "position": position,
                "no_attributes": True,
                "fallback_tier": "starter",
                "base_rate": base_rate,
                "final_aav": base_rate,
            },
        )
