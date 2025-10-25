"""
Transition Handlers Package

Contains handlers for specific phase transitions.

Each handler is responsible for:
1. Executing the transition logic (side effects)
2. Saving state for rollback
3. Rolling back on failure

Available Handlers:
- RegularToPlayoffsHandler: REGULAR_SEASON → PLAYOFFS
- PlayoffsToOffseasonHandler: PLAYOFFS → OFFSEASON
- OffseasonToPreseasonHandler: OFFSEASON → PRESEASON (new season)
"""

from .regular_to_playoffs import RegularToPlayoffsHandler
from .playoffs_to_offseason import PlayoffsToOffseasonHandler
from .offseason_to_preseason import OffseasonToPreseasonHandler

__all__ = [
    'RegularToPlayoffsHandler',
    'PlayoffsToOffseasonHandler',
    'OffseasonToPreseasonHandler',
]
