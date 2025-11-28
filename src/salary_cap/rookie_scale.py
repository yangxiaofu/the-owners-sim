"""
Rookie Wage Scale Calculator

NFL rookie contracts are tied to salary cap growth. This module calculates
contract values as percentages of the cap, so they automatically scale
with cap increases across dynasty years.

Reference: 2025 cap = $255.4M
- Pick #1: ~$48.4M total (18.95% of cap)
- Pick #32: ~$12M total (4.7% of cap)
- Pick #224: ~$4M total (1.57% of cap)

Sources:
- CBS Sports: 2025 NFL Rookie Contract Projections
- Over The Cap: NFL Draft
- Pro Football Network: NFL Rookie Contracts
"""

from dataclasses import dataclass
from typing import List


@dataclass
class RookieContractValues:
    """Calculated rookie contract values."""

    total_value: int
    signing_bonus: int
    base_salaries: List[int]  # 4 years
    guaranteed_amounts: List[int]  # 4 years
    has_fifth_year_option: bool


class RookieScaleCalculator:
    """
    Calculate rookie contract values based on salary cap.

    Uses percentage-based formulas so contracts scale with cap growth.
    All percentages are derived from 2025 NFL data and remain constant -
    only the input salary cap changes year-over-year.
    """

    # Percentage of cap for total contract value by pick position
    # These percentages are derived from 2025 data and remain constant
    PICK_1_CAP_PERCENT = 0.1895  # ~18.95% of cap for #1 overall
    PICK_32_CAP_PERCENT = 0.047  # ~4.7% of cap for #32
    PICK_64_CAP_PERCENT = 0.025  # ~2.5% of cap for Round 2 end
    PICK_100_CAP_PERCENT = 0.018  # ~1.8% of cap for Round 3 end
    LATE_ROUND_CAP_PERCENT = 0.0157  # ~1.57% of cap for Rounds 4-7

    # Signing bonus as percentage of total value by round
    SIGNING_BONUS_PERCENT_R1_TOP = 0.665  # Picks 1-10
    SIGNING_BONUS_PERCENT_R1_MID = 0.55  # Picks 11-20
    SIGNING_BONUS_PERCENT_R1_LATE = 0.50  # Picks 21-32
    SIGNING_BONUS_PERCENT_R2 = 0.40
    SIGNING_BONUS_PERCENT_R3 = 0.30
    SIGNING_BONUS_PERCENT_LATE = 0.10

    # Rookie minimum salary (scales with cap at ~0.33%)
    ROOKIE_MIN_CAP_PERCENT = 0.00329  # ~$840K at $255M cap

    def __init__(self, salary_cap: int):
        """
        Initialize calculator with current salary cap.

        Args:
            salary_cap: Current year's salary cap (e.g., 255_400_000 for 2025)

        Raises:
            ValueError: If salary_cap is not a positive integer
        """
        if not isinstance(salary_cap, int) or salary_cap <= 0:
            raise ValueError(
                f"salary_cap must be a positive integer, got {salary_cap!r}"
            )

        self.salary_cap = salary_cap
        self.rookie_minimum = int(salary_cap * self.ROOKIE_MIN_CAP_PERCENT)

    def calculate_contract(self, draft_pick: int) -> RookieContractValues:
        """
        Calculate rookie contract values for a draft pick.

        Args:
            draft_pick: Overall draft pick number (1-224)

        Returns:
            RookieContractValues with all contract details

        Raises:
            ValueError: If draft_pick is out of valid range
        """
        if not isinstance(draft_pick, int) or draft_pick < 1 or draft_pick > 224:
            raise ValueError(
                f"draft_pick must be an integer between 1 and 224, got {draft_pick!r}"
            )

        # Calculate total value as percentage of cap
        total_pct = self._get_total_value_percent(draft_pick)
        total_value = int(self.salary_cap * total_pct)

        # Calculate signing bonus
        bonus_pct = self._get_signing_bonus_percent(draft_pick)
        signing_bonus = int(total_value * bonus_pct)

        # Calculate base salaries (4 years)
        base_salaries = self._calculate_base_salaries(total_value, signing_bonus)

        # Determine guarantees (Round 1 = fully guaranteed)
        has_fifth_year_option = draft_pick <= 32
        if draft_pick <= 32:
            # First-round picks: all 4 years fully guaranteed
            guaranteed_amounts = base_salaries.copy()
        else:
            # Later rounds: only signing bonus guaranteed (prorated over 4 years)
            # Base salaries are not guaranteed
            guaranteed_amounts = [0, 0, 0, 0]

        return RookieContractValues(
            total_value=total_value,
            signing_bonus=signing_bonus,
            base_salaries=base_salaries,
            guaranteed_amounts=guaranteed_amounts,
            has_fifth_year_option=has_fifth_year_option,
        )

    def _get_total_value_percent(self, pick: int) -> float:
        """Get total contract value as percentage of cap based on pick."""
        if pick == 1:
            return self.PICK_1_CAP_PERCENT
        elif pick <= 32:
            # Linear interpolation from pick 1 to pick 32
            return self._interpolate(
                pick, 1, 32, self.PICK_1_CAP_PERCENT, self.PICK_32_CAP_PERCENT
            )
        elif pick <= 64:
            return self._interpolate(
                pick, 33, 64, self.PICK_32_CAP_PERCENT, self.PICK_64_CAP_PERCENT
            )
        elif pick <= 100:
            return self._interpolate(
                pick, 65, 100, self.PICK_64_CAP_PERCENT, self.PICK_100_CAP_PERCENT
            )
        else:
            return self.LATE_ROUND_CAP_PERCENT

    def _get_signing_bonus_percent(self, pick: int) -> float:
        """Get signing bonus as percentage of total value."""
        if pick <= 10:
            return self.SIGNING_BONUS_PERCENT_R1_TOP
        elif pick <= 20:
            return self.SIGNING_BONUS_PERCENT_R1_MID
        elif pick <= 32:
            return self.SIGNING_BONUS_PERCENT_R1_LATE
        elif pick <= 64:
            return self.SIGNING_BONUS_PERCENT_R2
        elif pick <= 100:
            return self.SIGNING_BONUS_PERCENT_R3
        else:
            return self.SIGNING_BONUS_PERCENT_LATE

    def _calculate_base_salaries(self, total: int, bonus: int) -> List[int]:
        """
        Calculate 4-year base salary schedule.

        Year 1: Rookie minimum
        Years 2-4: Escalating based on remaining value after signing bonus
        """
        remaining = total - bonus

        # Year 1: rookie minimum
        # Years 2-4: escalating (25%, 35%, 40% of remaining)
        year1 = self.rookie_minimum
        year2 = int(remaining * 0.25)
        year3 = int(remaining * 0.35)
        year4 = int(remaining * 0.40)

        return [year1, year2, year3, year4]

    def _interpolate(
        self, pick: int, start: int, end: int, start_pct: float, end_pct: float
    ) -> float:
        """Linear interpolation between two pick positions."""
        progress = (pick - start) / (end - start)
        return start_pct - (progress * (start_pct - end_pct))