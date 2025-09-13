"""
Base Result Classes

Enhanced base simulation result system that supports event-specific result types
while maintaining backward compatibility with the existing SimulationResult interface.
"""

from abc import ABC
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class EventType(Enum):
    """Types of simulatable events"""
    GAME = "game"
    TRAINING = "training" 
    SCOUTING = "scouting"
    REST_DAY = "rest_day"
    ADMINISTRATIVE = "administrative"


@dataclass
class SimulationResult:
    """
    Base result class for all event simulations.
    
    This is the base class that maintains backward compatibility while allowing
    for event-specific subclasses with additional data and functionality.
    """
    event_type: EventType
    event_name: str
    date: datetime
    teams_affected: List[int]
    duration_hours: float
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get_summary(self) -> str:
        """Get a human-readable summary of this result"""
        status = "SUCCESS" if self.success else "FAILED"
        return f"{self.event_name} ({self.event_type.value}) - {status}"
    
    def get_affected_teams_str(self) -> str:
        """Get comma-separated string of affected team IDs"""
        return ", ".join(str(team_id) for team_id in self.teams_affected)
    
    def has_metadata_key(self, key: str) -> bool:
        """Check if specific metadata key exists"""
        return key in self.metadata
    
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get metadata value with optional default"""
        return self.metadata.get(key, default)
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add or update metadata entry"""
        self.metadata[key] = value
    
    def is_success(self) -> bool:
        """Convenience method to check success status"""
        return self.success
    
    def is_failure(self) -> bool:
        """Convenience method to check failure status"""
        return not self.success


@dataclass
class ProcessingContext:
    """
    Context information available to result processors.
    
    Contains season state, calendar information, and other context
    that processors might need to make decisions.
    """
    current_date: datetime
    season_week: int
    season_phase: str  # "preseason", "regular_season", "playoffs", "offseason"
    current_standings: Optional[Dict[int, Dict[str, Any]]] = None
    team_states: Optional[Dict[int, Dict[str, Any]]] = None
    league_settings: Optional[Dict[str, Any]] = None
    
    def get_team_state(self, team_id: int) -> Dict[str, Any]:
        """Get current state for a specific team"""
        if self.team_states and team_id in self.team_states:
            return self.team_states[team_id]
        return {}
    
    def get_team_standing(self, team_id: int) -> Dict[str, Any]:
        """Get current standings data for a specific team"""
        if self.current_standings and team_id in self.current_standings:
            return self.current_standings[team_id]
        return {"wins": 0, "losses": 0, "ties": 0}


@dataclass
class ProcessingResult:
    """
    Result of processing a simulation result.
    
    Contains information about what was updated, what statistics were generated,
    and any side effects that occurred during processing.
    """
    processed_successfully: bool
    processing_type: str
    teams_updated: List[int] = field(default_factory=list)
    statistics_generated: Dict[str, Any] = field(default_factory=dict)
    state_changes: Dict[str, Any] = field(default_factory=dict)
    side_effects: List[str] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    
    def add_statistic(self, key: str, value: Any) -> None:
        """Add a generated statistic"""
        self.statistics_generated[key] = value
    
    def add_state_change(self, key: str, value: Any) -> None:
        """Record a state change that occurred"""
        self.state_changes[key] = value
    
    def add_side_effect(self, description: str) -> None:
        """Record a side effect that occurred"""
        self.side_effects.append(description)
    
    def add_error(self, error: str) -> None:
        """Record an error during processing"""
        self.error_messages.append(error)
        self.processed_successfully = False
    
    def get_summary(self) -> str:
        """Get summary of processing results"""
        status = "SUCCESS" if self.processed_successfully else "FAILED"
        teams = len(self.teams_updated)
        stats = len(self.statistics_generated)
        changes = len(self.state_changes)
        return f"Processing {status}: {teams} teams updated, {stats} stats, {changes} state changes"


# Type aliases for better type hints
AnySimulationResult = Union[SimulationResult, 'GameResult', 'TrainingResult', 'ScoutingResult', 'AdministrativeResult', 'RestResult']