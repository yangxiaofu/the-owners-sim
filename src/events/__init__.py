"""
Events Module

Polymorphic event system for NFL simulation.

This module provides a generic event interface that allows different event types
(GameEvent, MediaEvent, TradeEvent, etc.) to be stored and retrieved through
a unified API.

Key Components:
- BaseEvent: Abstract interface all events must implement
- GameEvent: Wraps FullGameSimulator for NFL game simulation
- EventDatabaseAPI: Generic persistence layer for all event types

Usage:
    from events import GameEvent, EventDatabaseAPI

    # Create a game event
    game = GameEvent(away_team_id=22, home_team_id=23,
                     game_date=datetime.now(), week=1)

    # Store in database
    event_db = EventDatabaseAPI("data/database/events.db")
    event_db.insert_event(game)

    # Retrieve all events for a game
    all_events = event_db.get_events_by_game_id("game_20241215_22_at_23")

    # Execute events polymorphically
    for event_data in all_events:
        event = GameEvent.from_database(event_data)
        result = event.simulate()
        print(f"Event {event.event_id}: {result.success}")
"""

from events.base_event import BaseEvent, EventResult, EventMetadata
from events.game_event import GameEvent
from events.scouting_event import ScoutingEvent
from events.event_database_api import EventDatabaseAPI

# Public API
__all__ = [
    # Base interfaces
    'BaseEvent',
    'EventResult',
    'EventMetadata',

    # Concrete event types
    'GameEvent',
    'ScoutingEvent',

    # Database API
    'EventDatabaseAPI',
]

# Version
__version__ = '1.1.0'  # Updated for hybrid storage pattern
