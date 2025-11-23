"""
Draft Events

Central module for all NFL draft-related events.

This module re-exports all draft event classes for convenient importing.
Each event class is defined in its own module for better organization.
"""

# Import all draft event classes
from .draft_pick_event import DraftPickEvent
from .udfa_signing_event import UDFASigningEvent
from .draft_trade_event import DraftTradeEvent
from .draft_day_event import DraftDayEvent

# Re-export for backward compatibility
__all__ = [
    'DraftPickEvent',
    'UDFASigningEvent',
    'DraftTradeEvent',
    'DraftDayEvent',
]
