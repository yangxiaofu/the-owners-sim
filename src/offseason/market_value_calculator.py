"""
Market Value Calculator

Calculates player market values for contract negotiations.
Based on position, overall rating, age, and market trends.
"""

from typing import Dict, Any


class MarketValueCalculator:
    """
    Calculates estimated market value for player contracts.

    Based on:
    - Position market rates
    - Overall rating
    - Age curve
    - Years of experience
    - NFL market trends (2024-2025 CBA)
    """

    # Base Annual Average Value (AAV) for 85 overall player by position (in millions)
    POSITION_BASE_AAV = {
        # Tier 1: Premium positions
        'quarterback': 45.0,
        'defensive_end': 25.0,  # Edge rusher
        'left_tackle': 22.0,
        'right_tackle': 22.0,

        # Tier 2: High-value positions
        'wide_receiver': 20.0,
        'cornerback': 18.0,
        'center': 15.0,

        # Tier 3: Standard positions
        'running_back': 12.0,
        'linebacker': 14.0,
        'safety': 13.0,
        'left_guard': 14.0,
        'right_guard': 14.0,

        # Tier 4: Lower-value positions
        'tight_end': 11.0,
        'defensive_tackle': 12.0,
        'kicker': 4.0,
        'punter': 3.0
    }

    # Contract length by position (years)
    TYPICAL_CONTRACT_LENGTH = {
        'quarterback': 4,
        'defensive_end': 4,
        'left_tackle': 4,
        'right_tackle': 4,
        'wide_receiver': 3,
        'cornerback': 3,
        'running_back': 2,  # RBs get shorter deals
        'kicker': 3,
        'punter': 3
    }

    # Peak age by position
    PEAK_AGE = {
        'quarterback': 28,
        'running_back': 26,
        'wide_receiver': 27,
        'defensive_end': 27,
        'left_tackle': 28,
        'right_tackle': 28,
        'cornerback': 27,
        'kicker': 30,
        'punter': 30
    }

    def __init__(self, salary_cap: int = 255_000_000):
        """
        Initialize market value calculator.

        Args:
            salary_cap: League salary cap (default 2024 cap: $255M)
        """
        self.salary_cap = salary_cap

    def calculate_player_value(
        self,
        position: str,
        overall: int,
        age: int,
        years_pro: int
    ) -> Dict[str, Any]:
        """
        Calculate estimated market value for a player.

        Args:
            position: Player position
            overall: Overall rating (0-100)
            age: Player age
            years_pro: Years of NFL experience

        Returns:
            Dict with contract estimates:
            {
                'aav': Annual average value (millions),
                'total_value': Total contract value (millions),
                'years': Contract length,
                'guaranteed': Guaranteed money (millions),
                'signing_bonus': Signing bonus (millions),
                'guarantee_percentage': Guarantee percentage
            }
        """
        # Get base AAV for position
        base_aav = self.POSITION_BASE_AAV.get(position, 10.0)

        # Adjust for overall rating (85 overall is baseline)
        rating_multiplier = self._calculate_rating_multiplier(overall)

        # Adjust for age
        age_multiplier = self._calculate_age_multiplier(position, age)

        # Adjust for experience (rookies get less, vets get more)
        experience_multiplier = self._calculate_experience_multiplier(years_pro)

        # Calculate AAV
        aav = base_aav * rating_multiplier * age_multiplier * experience_multiplier

        # Determine contract length
        years = self.TYPICAL_CONTRACT_LENGTH.get(position, 3)

        # Adjust length for age (older players get shorter deals)
        if age > 30:
            years = min(years, 2)
        elif age > 28:
            years = min(years, 3)

        # Calculate total value
        total_value = aav * years

        # Calculate guarantees (typically 50-70% for top players, less for lower rated)
        guarantee_percentage = self._calculate_guarantee_percentage(overall, position)
        guaranteed = total_value * guarantee_percentage

        # Signing bonus (typically 30-40% of total for spread)
        signing_bonus = total_value * 0.35

        return {
            'aav': round(aav, 2),
            'total_value': round(total_value, 2),
            'years': years,
            'guaranteed': round(guaranteed, 2),
            'signing_bonus': round(signing_bonus, 2),
            'guarantee_percentage': round(guarantee_percentage * 100, 1)
        }

    def _calculate_rating_multiplier(self, overall: int) -> float:
        """
        Calculate multiplier based on overall rating.

        85 overall = 1.0x (baseline)
        95 overall = 2.0x (elite)
        75 overall = 0.5x (below average starter)
        65 overall = 0.2x (backup)
        """
        if overall >= 90:
            # Elite players (90-99): 1.5x to 2.5x
            return 1.5 + ((overall - 90) / 10) * 1.0
        elif overall >= 85:
            # Good starters (85-89): 1.0x to 1.5x
            return 1.0 + ((overall - 85) / 5) * 0.5
        elif overall >= 75:
            # Average starters (75-84): 0.5x to 1.0x
            return 0.5 + ((overall - 75) / 10) * 0.5
        elif overall >= 65:
            # Backups (65-74): 0.2x to 0.5x
            return 0.2 + ((overall - 65) / 10) * 0.3
        else:
            # Deep backups (< 65): 0.1x to 0.2x
            return 0.1 + (overall / 65) * 0.1

    def _calculate_age_multiplier(self, position: str, age: int) -> float:
        """
        Calculate multiplier based on age curve.

        Peak age = 1.0x
        Age 23 = 0.9x (upside but unproven)
        Age 32 = 0.7x (decline phase)
        Age 35+ = 0.4x (near retirement)
        """
        peak = self.PEAK_AGE.get(position, 27)

        if age <= peak:
            # Young player with upside (90-100% value)
            years_before_peak = peak - age
            if years_before_peak <= 1:
                return 1.0
            else:
                # Discount for very young (23-24 for most positions)
                return max(0.85, 1.0 - (years_before_peak * 0.05))
        else:
            # Past peak - declining value
            years_past_peak = age - peak
            if years_past_peak <= 2:
                return max(0.85, 1.0 - (years_past_peak * 0.05))
            elif years_past_peak <= 5:
                return max(0.6, 0.85 - ((years_past_peak - 2) * 0.08))
            else:
                return max(0.3, 0.6 - ((years_past_peak - 5) * 0.1))

    def _calculate_experience_multiplier(self, years_pro: int) -> float:
        """
        Calculate multiplier based on NFL experience.

        Rookies (0-1 years) on rookie contracts = N/A (separate system)
        Young players (2-4 years) = 0.9x (first big contract)
        Prime players (5-8 years) = 1.0x (peak earning)
        Veterans (9+ years) = 0.95x (slight discount for age)
        """
        if years_pro <= 1:
            return 0.8  # First contract after rookie deal
        elif years_pro <= 4:
            return 0.9  # Still building value
        elif years_pro <= 8:
            return 1.0  # Peak earning years
        else:
            return 0.95  # Veteran discount

    def _calculate_guarantee_percentage(self, overall: int, position: str) -> float:
        """
        Calculate what percentage of contract should be guaranteed.

        Elite players: 60-70%
        Good starters: 50-60%
        Average starters: 40-50%
        Backups: 20-30%
        """
        if overall >= 90:
            base = 0.65
        elif overall >= 85:
            base = 0.55
        elif overall >= 80:
            base = 0.45
        elif overall >= 75:
            base = 0.35
        else:
            base = 0.25

        # QBs and premium positions get slightly higher guarantees
        if position in ['quarterback', 'defensive_end', 'left_tackle', 'right_tackle']:
            base += 0.05

        return min(0.75, base)  # Cap at 75%

    def calculate_franchise_tag_value(
        self,
        position: str,
        season: int = 2025
    ) -> int:
        """
        Calculate franchise tag value for a position.

        Based on top 5 average at position or 120% of prior salary.

        Args:
            position: Player position
            season: Season year (unused, for future inflation calculations)

        Returns:
            Franchise tag salary (in dollars, not millions)
        """
        # Use base AAV as proxy for top-5 average
        base_aav = self.POSITION_BASE_AAV.get(position, 10.0)

        # Franchise tag is typically 120% of base for top positions
        tag_value_millions = base_aav * 1.2

        # Convert to dollars
        tag_value = int(tag_value_millions * 1_000_000)

        return tag_value
