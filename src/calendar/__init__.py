"""
Calendar System

A simple, focused calendar system for tracking dates and managing events.
Provides core functionality for date progression, event scheduling, and event retrieval.
"""

from .calendar_manager import CalendarManager
from .event import Event
from .event_store import EventStore

__all__ = [
    'CalendarManager',
    'Event',
    'EventStore'
]