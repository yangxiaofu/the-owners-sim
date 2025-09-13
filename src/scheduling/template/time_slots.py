"""
Minimal time slot definitions for NFL scheduling.

YAGNI: Just the basic time slots we need. No complex metadata,
no network assignments, no special requirements.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class TimeSlot(Enum):
    """Basic NFL time slots"""
    THURSDAY_NIGHT = "TNF"
    SUNDAY_EARLY = "SUN_1PM" 
    SUNDAY_LATE = "SUN_4PM"
    SUNDAY_NIGHT = "SNF"
    MONDAY_NIGHT = "MNF"


@dataclass
class GameSlot:
    """A single game slot in the schedule"""
    week: int
    time_slot: TimeSlot
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    
    @property
    def is_assigned(self) -> bool:
        """Check if this slot has been assigned a game"""
        return self.home_team_id is not None and self.away_team_id is not None
    
    @property
    def game_id(self) -> str:
        """Get unique identifier for this game"""
        if self.is_assigned:
            return f"W{self.week:02d}_{self.away_team_id}@{self.home_team_id}"
        return f"W{self.week:02d}_EMPTY_{self.time_slot.value}"
    
    @property
    def is_primetime(self) -> bool:
        """Check if this is a primetime slot"""
        return self.time_slot in [TimeSlot.THURSDAY_NIGHT, TimeSlot.SUNDAY_NIGHT, TimeSlot.MONDAY_NIGHT]
    
    def assign_game(self, home_team_id: int, away_team_id: int) -> None:
        """Assign a game to this slot"""
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
    
    def clear_assignment(self) -> None:
        """Clear the game assignment from this slot"""
        self.home_team_id = None
        self.away_team_id = None
    
    def __str__(self) -> str:
        """String representation of the game slot"""
        if self.is_assigned:
            return f"Week {self.week} {self.time_slot.value}: {self.away_team_id} @ {self.home_team_id}"
        return f"Week {self.week} {self.time_slot.value}: EMPTY"