"""
Game Cycle - Stage-based season progression system.

This module replaces the day-by-day calendar cycling with a simpler
stage-based approach where simulation advances through meaningful
phases: weeks during regular season, rounds during playoffs, and
distinct periods during the offseason.
"""

from .stage_definitions import Stage, StageType, SeasonPhase, ROSTER_LIMITS, INTERACTIVE_OFFSEASON_STAGES
from .stage_controller import StageController

__all__ = [
    "Stage",
    "StageType",
    "SeasonPhase",
    "StageController",
    "ROSTER_LIMITS",
    "INTERACTIVE_OFFSEASON_STAGES",
]