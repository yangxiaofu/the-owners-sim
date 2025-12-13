"""
Random Events - Rare NFL Events at Realistic Rates

Models rare events that occur during NFL games at statistically realistic
probabilities. These events add unpredictability and excitement to simulated games.

Event Probabilities (based on NFL data):
- Blocked punt: 0.8% per punt attempt
- Muffed punt return: 2% per punt return
- Fumbled snap: 0.5% per play
- Defensive TD on turnover: 15% when turnover occurs
- Safety on sack: 0.3% per sack in own end zone

Usage:
    checker = RandomEventChecker()

    # Check for blocked punt
    if checker.check_blocked_punt():
        # Handle blocked punt
        pass

    # Check for muffed return
    if checker.check_muffed_return():
        # Handle muffed return (turnover)
        pass
"""

import random
from enum import Enum
from typing import Optional


class RandomEventType(Enum):
    """Types of random events that can occur during plays"""
    BLOCKED_PUNT = "blocked_punt"
    MUFFED_PUNT_RETURN = "muffed_punt_return"
    FUMBLED_SNAP = "fumbled_snap"
    DEFENSIVE_TD_ON_TURNOVER = "defensive_td_on_turnover"
    SAFETY_ON_SACK = "safety_on_sack"


# NFL-realistic event probabilities (based on historical data)
EVENT_PROBABILITIES = {
    RandomEventType.BLOCKED_PUNT: 0.008,           # 0.8% per punt attempt (~13 blocked punts per season)
    RandomEventType.MUFFED_PUNT_RETURN: 0.02,      # 2% per punt return (~30 muffed returns per season)
    RandomEventType.FUMBLED_SNAP: 0.005,           # 0.5% per play (very rare, ~50 per season)
    RandomEventType.DEFENSIVE_TD_ON_TURNOVER: 0.15,  # 15% when turnover occurs (~80 defensive TDs per season)
    RandomEventType.SAFETY_ON_SACK: 0.003,         # 0.3% per sack in own end zone (~1-2 safeties per season)
}


class RandomEventChecker:
    """
    Checks for random rare events at realistic NFL rates.

    Can be initialized with a random seed for testing reproducibility.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize random event checker.

        Args:
            seed: Optional random seed for reproducible testing
        """
        if seed is not None:
            random.seed(seed)

    def check_event(self, event_type: RandomEventType) -> bool:
        """
        Roll dice for random event occurrence.

        Args:
            event_type: Type of event to check

        Returns:
            True if event occurs, False otherwise
        """
        probability = EVENT_PROBABILITIES.get(event_type, 0.0)
        return random.random() < probability

    def check_blocked_punt(self) -> bool:
        """
        Check if punt is blocked (0.8% probability).

        Returns:
            True if punt is blocked (occurs ~13 times per NFL season)
        """
        return self.check_event(RandomEventType.BLOCKED_PUNT)

    def check_muffed_return(self) -> bool:
        """
        Check if punt return is muffed (2% probability).

        Returns:
            True if return is muffed (occurs ~30 times per NFL season)
        """
        return self.check_event(RandomEventType.MUFFED_PUNT_RETURN)

    def check_fumbled_snap(self) -> bool:
        """
        Check if snap is fumbled (0.5% probability).

        Returns:
            True if snap is fumbled (very rare, ~50 times per NFL season)
        """
        return self.check_event(RandomEventType.FUMBLED_SNAP)

    def check_defensive_td(self) -> bool:
        """
        Check if turnover results in defensive touchdown (15% probability).

        Should only be called when a turnover has already occurred.

        Returns:
            True if turnover results in defensive TD (~80 defensive TDs per NFL season)
        """
        return self.check_event(RandomEventType.DEFENSIVE_TD_ON_TURNOVER)

    def check_safety_on_sack(self, field_position: int) -> bool:
        """
        Check if sack results in safety (0.3% probability in own end zone).

        Only possible when offensive team is in own end zone (field_position <= 2).

        Args:
            field_position: Yards from own goal line (0-100)

        Returns:
            True if sack results in safety (very rare, ~1-2 per NFL season)
        """
        # Safety only possible in own end zone
        if field_position > 2:
            return False
        return self.check_event(RandomEventType.SAFETY_ON_SACK)

    def get_event_probability(self, event_type: RandomEventType) -> float:
        """
        Get probability for a specific event type.

        Args:
            event_type: Type of event to query

        Returns:
            Probability (0.0-1.0) for the event
        """
        return EVENT_PROBABILITIES.get(event_type, 0.0)

    def __repr__(self):
        """Debug representation"""
        return "RandomEventChecker(NFL-realistic probabilities)"
