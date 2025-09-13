"""
Base Simulation Event

Abstract base class defining the interface for all simulatable events in the calendar system.
Every event type (games, training, scouting, etc.) must implement the simulate() method.

Now supports enhanced result types while maintaining backward compatibility.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

# Import the enhanced result types
try:
    from ..results.base_result import SimulationResult, EventType, AnySimulationResult
    ENHANCED_RESULTS_AVAILABLE = True
except ImportError:
    # Fallback to local definitions for backward compatibility
    ENHANCED_RESULTS_AVAILABLE = False
    
    class EventType(Enum):
        """Types of simulatable events"""
        GAME = "game"
        TRAINING = "training" 
        SCOUTING = "scouting"
        REST_DAY = "rest_day"
        ADMINISTRATIVE = "administrative"

    @dataclass
    class SimulationResult:
        """Base result class for all event simulations"""
        event_type: EventType
        event_name: str
        date: datetime
        teams_affected: List[int]
        duration_hours: float
        success: bool = True
        error_message: Optional[str] = None
        metadata: Dict[str, Any] = None
        
        def __post_init__(self):
            if self.metadata is None:
                self.metadata = {}
    
    # Type alias for backward compatibility
    AnySimulationResult = SimulationResult


class BaseSimulationEvent(ABC):
    """
    Abstract base class for all simulatable events in the calendar system.
    
    All events must implement the simulate() method which returns a SimulationResult.
    The calendar manager uses this interface to execute any type of event uniformly.
    """
    
    def __init__(self, date: datetime, event_name: str, involved_teams: List[int], 
                 duration_hours: float = 1.0):
        """
        Initialize base simulation event
        
        Args:
            date: When this event is scheduled
            event_name: Human-readable name for this event
            involved_teams: List of team IDs that participate in this event
            duration_hours: How many hours this event takes (default: 1.0)
        """
        self.date = date
        self.event_name = event_name
        self.involved_teams = involved_teams
        self.duration_hours = duration_hours
        self.event_id = self._generate_event_id()
    
    @abstractmethod
    def simulate(self) -> AnySimulationResult:
        """
        Execute this event's simulation logic.
        
        This is the core method that must be implemented by all event types.
        It should contain all the logic for simulating this specific event type.
        
        Returns:
            AnySimulationResult: Result of the simulation with outcome data
            Can be SimulationResult (base) or any enhanced result type like GameResult, TrainingResult, etc.
        """
        pass
    
    @abstractmethod
    def get_event_type(self) -> EventType:
        """
        Return the type of this event.
        
        Returns:
            EventType: The category this event belongs to
        """
        pass
    
    def can_coexist_with(self, other: 'BaseSimulationEvent') -> bool:
        """
        Check if this event can happen on the same day as another event.
        
        Default implementation prevents teams from being in multiple events
        on the same day, but subclasses can override for more complex logic.
        
        Args:
            other: Another event to check compatibility with
            
        Returns:
            bool: True if events can happen on same day, False otherwise
        """
        # Check for team conflicts (teams can't be in multiple events same day)
        return not bool(set(self.involved_teams) & set(other.involved_teams))
    
    def get_duration(self) -> timedelta:
        """
        Get the duration of this event as a timedelta.
        
        Returns:
            timedelta: How long this event takes
        """
        return timedelta(hours=self.duration_hours)
    
    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        """
        Validate that this event can be executed.
        
        Default implementation just checks basic requirements.
        Subclasses can override for more specific validation.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not self.involved_teams:
            return False, "Event must involve at least one team"
        
        if self.duration_hours <= 0:
            return False, "Event duration must be positive"
            
        return True, None
    
    def _generate_event_id(self) -> str:
        """
        Generate unique identifier for this event.
        
        Returns:
            str: Unique event ID based on date, teams, and event name
        """
        team_ids = "_".join(str(team_id) for team_id in sorted(self.involved_teams))
        date_str = self.date.strftime("%Y%m%d")
        return f"{date_str}_{team_ids}_{self.event_name.replace(' ', '_')}"
    
    def __str__(self) -> str:
        """String representation of the event"""
        teams_str = ", ".join(str(team_id) for team_id in self.involved_teams)
        return f"{self.event_name} on {self.date.strftime('%Y-%m-%d')} (Teams: {teams_str})"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return (f"{self.__class__.__name__}(date={self.date}, "
                f"event_name='{self.event_name}', "
                f"teams={self.involved_teams}, "
                f"duration={self.duration_hours}h)")
    
    def __eq__(self, other) -> bool:
        """Event equality based on event ID"""
        return isinstance(other, BaseSimulationEvent) and self.event_id == other.event_id
    
    def __hash__(self) -> int:
        """Hash based on event ID for use in sets/dicts"""
        return hash(self.event_id)