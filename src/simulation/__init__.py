"""
Simulation Package

Calendar-based daily simulation system for NFL season management.
Provides event scheduling, conflict resolution, and day-by-day simulation execution.
"""

from .calendar_manager import CalendarManager, ConflictResolution, DaySimulationResult, CalendarStats
from .events.base_simulation_event import BaseSimulationEvent, SimulationResult, EventType

__all__ = [
    'CalendarManager',
    'ConflictResolution', 
    'DaySimulationResult',
    'CalendarStats',
    'BaseSimulationEvent',
    'SimulationResult',
    'EventType'
]