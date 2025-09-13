"""
Placeholder Events

Simple placeholder implementations for event types that will be developed later.
These events just print simulation messages when executed, allowing the calendar
manager to be tested with various event types before full implementations exist.
"""

from datetime import datetime
from typing import List

from .base_simulation_event import BaseSimulationEvent, SimulationResult, EventType


class TrainingEvent(BaseSimulationEvent):
    """
    Placeholder training event for team practice sessions.
    
    In the future, this will simulate:
    - Player skill development
    - Injury risk during practice
    - Team chemistry building
    - Fatigue accumulation
    """
    
    def __init__(self, date: datetime, team_id: int, training_type: str = "practice"):
        """
        Initialize training event
        
        Args:
            date: When this training occurs
            team_id: Which team is training
            training_type: Type of training (practice, walkthrough, etc.)
        """
        self.training_type = training_type
        super().__init__(
            date=date,
            event_name=f"Team {team_id} {training_type}",
            involved_teams=[team_id],
            duration_hours=2.0  # Typical practice duration
        )
    
    def simulate(self) -> SimulationResult:
        """Simulate training event - placeholder implementation"""
        print(f"simulate training: {self.event_name} on {self.date.strftime('%Y-%m-%d')}")
        
        return SimulationResult(
            event_type=EventType.TRAINING,
            event_name=self.event_name,
            date=self.date,
            teams_affected=self.involved_teams,
            duration_hours=self.duration_hours,
            success=True,
            metadata={
                "training_type": self.training_type,
                "placeholder": True,
                "message": f"Training simulation placeholder for team {self.involved_teams[0]}"
            }
        )
    
    def get_event_type(self) -> EventType:
        return EventType.TRAINING


class ScoutingEvent(BaseSimulationEvent):
    """
    Placeholder scouting event for player evaluation activities.
    
    In the future, this will simulate:
    - College prospect evaluation
    - Opponent team analysis
    - Player performance assessment
    - Draft board updates
    """
    
    def __init__(self, date: datetime, team_id: int, scouting_target: str = "prospects"):
        """
        Initialize scouting event
        
        Args:
            date: When this scouting occurs
            team_id: Which team is doing the scouting
            scouting_target: What/who is being scouted
        """
        self.scouting_target = scouting_target
        super().__init__(
            date=date,
            event_name=f"Team {team_id} scouting {scouting_target}",
            involved_teams=[team_id],
            duration_hours=8.0  # Full day scouting
        )
    
    def simulate(self) -> SimulationResult:
        """Simulate scouting event - placeholder implementation"""
        print(f"simulate scouting: {self.event_name} on {self.date.strftime('%Y-%m-%d')}")
        
        return SimulationResult(
            event_type=EventType.SCOUTING,
            event_name=self.event_name,
            date=self.date,
            teams_affected=self.involved_teams,
            duration_hours=self.duration_hours,
            success=True,
            metadata={
                "scouting_target": self.scouting_target,
                "placeholder": True,
                "message": f"Scouting simulation placeholder for team {self.involved_teams[0]}"
            }
        )
    
    def get_event_type(self) -> EventType:
        return EventType.SCOUTING


class RestDayEvent(BaseSimulationEvent):
    """
    Placeholder rest day event for team recovery and administrative work.
    
    In the future, this will simulate:
    - Player recovery and healing
    - Administrative tasks
    - Team meetings and film study
    - Equipment maintenance
    """
    
    def __init__(self, date: datetime, team_id: int, rest_type: str = "team_rest"):
        """
        Initialize rest day event
        
        Args:
            date: When this rest day occurs
            team_id: Which team is resting
            rest_type: Type of rest day activity
        """
        self.rest_type = rest_type
        super().__init__(
            date=date,
            event_name=f"Team {team_id} {rest_type}",
            involved_teams=[team_id],
            duration_hours=4.0  # Half day administrative work
        )
    
    def simulate(self) -> SimulationResult:
        """Simulate rest day event - placeholder implementation"""
        print(f"simulate rest day: {self.event_name} on {self.date.strftime('%Y-%m-%d')}")
        
        return SimulationResult(
            event_type=EventType.REST_DAY,
            event_name=self.event_name,
            date=self.date,
            teams_affected=self.involved_teams,
            duration_hours=self.duration_hours,
            success=True,
            metadata={
                "rest_type": self.rest_type,
                "placeholder": True,
                "message": f"Rest day simulation placeholder for team {self.involved_teams[0]}"
            }
        )
    
    def get_event_type(self) -> EventType:
        return EventType.REST_DAY


class AdministrativeEvent(BaseSimulationEvent):
    """
    Placeholder administrative event for front office activities.
    
    In the future, this will simulate:
    - Trade negotiations
    - Free agent signings
    - Contract negotiations
    - Draft preparations
    """
    
    def __init__(self, date: datetime, team_id: int, admin_type: str = "front_office"):
        """
        Initialize administrative event
        
        Args:
            date: When this administrative work occurs
            team_id: Which team's front office is working
            admin_type: Type of administrative work
        """
        self.admin_type = admin_type
        super().__init__(
            date=date,
            event_name=f"Team {team_id} {admin_type}",
            involved_teams=[team_id],
            duration_hours=6.0  # Business day administrative work
        )
    
    def simulate(self) -> SimulationResult:
        """Simulate administrative event - placeholder implementation"""
        print(f"simulate administrative: {self.event_name} on {self.date.strftime('%Y-%m-%d')}")
        
        return SimulationResult(
            event_type=EventType.ADMINISTRATIVE,
            event_name=self.event_name,
            date=self.date,
            teams_affected=self.involved_teams,
            duration_hours=self.duration_hours,
            success=True,
            metadata={
                "admin_type": self.admin_type,
                "placeholder": True,
                "message": f"Administrative simulation placeholder for team {self.involved_teams[0]}"
            }
        )
    
    def get_event_type(self) -> EventType:
        return EventType.ADMINISTRATIVE