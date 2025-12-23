"""
Win-now pressure modifier.

Adjusts valuations based on team's championship window status.
Win-now teams pay premium for proven veterans.
"""

from typing import Tuple, Optional

from contract_valuation.context import OwnerContext
from contract_valuation.owner_pressure.base import PressureModifier


class WinNowModifier(PressureModifier):
    """
    Pressure modifier based on team's championship window status.

    Win-now teams pay premium for proven veterans who can contribute immediately.
    Rebuilding teams value youth and potential, discounting established veterans.

    Player Age Categories:
        - Young (< 26): Premium in rebuild, neutral/discount in win-now
        - Prime (26-30): Premium in win-now, neutral in rebuild
        - Veteran (31+): Significant premium in win-now, discount in rebuild

    Team Philosophies:
        - "win_now": +5% to +12% for veterans, -5% for young players
        - "maintain": ±3% based on age
        - "rebuild": -10% for veterans, +8% for young players
    """

    # Age category thresholds
    YOUNG_AGE_MAX = 25
    PRIME_AGE_MAX = 30

    # Philosophy -> pressure level mapping
    PHILOSOPHY_PRESSURE = {
        "win_now": 0.9,
        "maintain": 0.5,
        "rebuild": 0.2,
    }

    # Adjustment matrix: philosophy -> age_category -> adjustment_pct
    ADJUSTMENT_MATRIX = {
        "win_now": {
            "young": -0.05,     # -5% - win-now teams discount young players
            "prime": 0.05,      # +5% - premium for prime contributors
            "veteran": 0.12,    # +12% - big premium for proven veterans
        },
        "maintain": {
            "young": 0.03,      # +3% - slight premium for development
            "prime": 0.0,       # 0% - market rate for prime
            "veteran": -0.03,   # -3% - slight discount for aging
        },
        "rebuild": {
            "young": 0.08,      # +8% - premium for youth/development
            "prime": -0.03,     # -3% - discount for established players
            "veteran": -0.10,   # -10% - significant discount for veterans
        },
    }

    # Win-now mode boost
    WIN_NOW_MODE_BOOST = 0.1

    @property
    def modifier_name(self) -> str:
        """Return modifier identifier."""
        return "win_now"

    def calculate_pressure_level(self, context: OwnerContext) -> float:
        """
        Calculate win-now pressure level from team philosophy.

        Args:
            context: Owner context with team_philosophy and win_now_mode

        Returns:
            Pressure level 0.0-1.0 (higher = more urgency)
        """
        base_pressure = self.PHILOSOPHY_PRESSURE.get(context.team_philosophy, 0.5)

        # Boost if explicitly in win-now mode
        if context.win_now_mode:
            base_pressure = min(1.0, base_pressure + self.WIN_NOW_MODE_BOOST)

        return base_pressure

    def apply(
        self,
        base_aav: int,
        context: OwnerContext,
        player_age: Optional[int] = None
    ) -> Tuple[int, str]:
        """
        Apply win-now pressure adjustment to AAV.

        Args:
            base_aav: Pre-adjustment AAV in dollars
            context: Owner context with team philosophy
            player_age: Player's age (required for age-based adjustments)

        Returns:
            Tuple of (adjusted_aav, description)
        """
        # If no age provided, no adjustment
        if player_age is None:
            return base_aav, "Win-now: No age provided, no adjustment"

        age_category = self._get_age_category(player_age)
        adjustment_pct = self._get_adjustment(context.team_philosophy, age_category)

        # Clamp adjustment
        adjustment_pct = self.clamp_adjustment(adjustment_pct)

        # Calculate adjusted AAV
        adjustment_dollars = int(base_aav * adjustment_pct)
        adjusted_aav = base_aav + adjustment_dollars

        # Format description
        description = self._format_description(
            context.team_philosophy,
            age_category,
            player_age,
            adjustment_pct,
            adjustment_dollars
        )

        return adjusted_aav, description

    def _get_age_category(self, age: int) -> str:
        """
        Categorize player by age.

        Args:
            age: Player's age

        Returns:
            Age category: "young", "prime", or "veteran"
        """
        if age <= self.YOUNG_AGE_MAX:
            return "young"
        elif age <= self.PRIME_AGE_MAX:
            return "prime"
        else:
            return "veteran"

    def _get_adjustment(self, philosophy: str, age_category: str) -> float:
        """
        Look up adjustment from philosophy/age matrix.

        Args:
            philosophy: Team philosophy ("win_now", "maintain", "rebuild")
            age_category: Player age category ("young", "prime", "veteran")

        Returns:
            Adjustment percentage
        """
        philosophy_adjustments = self.ADJUSTMENT_MATRIX.get(philosophy, self.ADJUSTMENT_MATRIX["maintain"])
        return philosophy_adjustments.get(age_category, 0.0)

    def _format_description(
        self,
        philosophy: str,
        age_category: str,
        player_age: int,
        adjustment_pct: float,
        adjustment_dollars: int
    ) -> str:
        """
        Format human-readable description.

        Args:
            philosophy: Team philosophy
            age_category: Player age category
            player_age: Actual player age
            adjustment_pct: Percentage adjustment applied
            adjustment_dollars: Dollar adjustment

        Returns:
            Description string
        """
        philosophy_labels = {
            "win_now": "Win-now team",
            "maintain": "Maintaining team",
            "rebuild": "Rebuilding team",
        }
        philosophy_label = philosophy_labels.get(philosophy, "Team")

        category_labels = {
            "young": "young prospect",
            "prime": "prime-age player",
            "veteran": "veteran",
        }
        age_label = category_labels.get(age_category, "player")

        base_desc = self.format_adjustment_description(
            f"{philosophy_label} ({age_label}, age {player_age})",
            adjustment_pct,
            adjustment_dollars
        )
        return base_desc

    def get_breakdown(
        self,
        context: OwnerContext,
        base_aav: int,
        player_age: Optional[int] = None
    ) -> dict:
        """
        Get detailed breakdown for audit trail.

        Args:
            context: Owner context
            base_aav: Base AAV before adjustment
            player_age: Player's age

        Returns:
            Detailed breakdown dictionary
        """
        pressure = self.calculate_pressure_level(context)

        if player_age is None:
            return {
                "modifier_name": self.modifier_name,
                "pressure_level": round(pressure, 3),
                "team_philosophy": context.team_philosophy,
                "win_now_mode": context.win_now_mode,
                "player_age": None,
                "age_category": None,
                "base_aav": base_aav,
                "adjustment_pct": 0.0,
                "adjustment_dollars": 0,
                "adjusted_aav": base_aav,
                "rationale": "No player age provided",
            }

        age_category = self._get_age_category(player_age)
        adjustment_pct = self._get_adjustment(context.team_philosophy, age_category)
        adjustment_pct = self.clamp_adjustment(adjustment_pct)
        adjustment_dollars = int(base_aav * adjustment_pct)
        adjusted_aav = base_aav + adjustment_dollars

        # Generate rationale
        if context.team_philosophy == "win_now":
            if age_category == "veteran":
                rationale = "Win-now team pays premium for proven veteran production"
            elif age_category == "prime":
                rationale = "Win-now team pays premium for prime contributors"
            else:
                rationale = "Win-now team discounts young unproven players"
        elif context.team_philosophy == "rebuild":
            if age_category == "veteran":
                rationale = "Rebuilding team discounts veterans nearing end of career"
            elif age_category == "young":
                rationale = "Rebuilding team pays premium for youth and potential"
            else:
                rationale = "Rebuilding team offers slight discount for established players"
        else:
            rationale = "Maintaining team offers market-rate adjustments based on age"

        return {
            "modifier_name": self.modifier_name,
            "pressure_level": round(pressure, 3),
            "team_philosophy": context.team_philosophy,
            "win_now_mode": context.win_now_mode,
            "player_age": player_age,
            "age_category": age_category,
            "base_aav": base_aav,
            "adjustment_pct": round(adjustment_pct, 4),
            "adjustment_dollars": adjustment_dollars,
            "adjusted_aav": adjusted_aav,
            "rationale": rationale,
        }