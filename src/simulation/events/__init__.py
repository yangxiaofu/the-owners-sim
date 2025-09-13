"""
Simulation Events Package

Event implementations for the calendar-based simulation system.
Includes both actual implementations (GameSimulationEvent) and placeholders.
"""

from .base_simulation_event import BaseSimulationEvent, SimulationResult, EventType
from .placeholder_events import TrainingEvent, ScoutingEvent, RestDayEvent, AdministrativeEvent

__all__ = [
    'BaseSimulationEvent',
    'SimulationResult', 
    'EventType',
    'TrainingEvent',
    'ScoutingEvent',
    'RestDayEvent',
    'AdministrativeEvent'
]