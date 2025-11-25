"""
Stage handlers for different phases of the season.

Each handler implements the StageHandler protocol to execute
stage-specific logic.
"""

from .regular_season import RegularSeasonHandler
from .playoffs import PlayoffHandler
from .offseason import OffseasonHandler

__all__ = [
    "RegularSeasonHandler",
    "PlayoffHandler",
    "OffseasonHandler",
]