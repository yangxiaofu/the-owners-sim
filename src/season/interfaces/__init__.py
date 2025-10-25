"""
Season Interfaces Package

Contains protocol definitions (interfaces) for dependency injection and testing.

These protocols allow the SeasonCycleController to depend on abstractions
rather than concrete implementations, enabling easy mocking and testing.
"""

from .schedule_generator_protocol import ScheduleGeneratorProtocol
from .season_controller_protocol import SeasonControllerProtocol
from .database_protocol import DatabaseProtocol
from .calendar_protocol import CalendarProtocol
from .playoff_status_protocol import PlayoffStatusProtocol

__all__ = [
    'ScheduleGeneratorProtocol',
    'SeasonControllerProtocol',
    'DatabaseProtocol',
    'CalendarProtocol',
    'PlayoffStatusProtocol',
]
