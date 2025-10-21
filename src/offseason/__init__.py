"""
NFL Offseason Simulation Module

This module handles the complete NFL offseason cycle:
- Franchise tag period (March 1-5)
- Free agency (March 11 onwards)
- NFL Draft (late April)
- Roster cuts and finalization (August)

Main Components:
- OffseasonController: Main orchestrator for offseason phase
- OffseasonPhase: Enum defining offseason sub-phases
- DraftManager: Draft class generation and selection
- RosterManager: Roster expansion and cuts (53→90→53)
- FreeAgencyManager: Free agent pool and signings
- TeamNeedsAnalyzer: Analyzes roster weaknesses and priorities for AI decisions
- MarketValueCalculator: Calculates player contract values for AI negotiations
"""

from offseason.offseason_phases import OffseasonPhase
from offseason.offseason_controller import OffseasonController
from offseason.team_needs_analyzer import TeamNeedsAnalyzer, NeedUrgency
from offseason.market_value_calculator import MarketValueCalculator

__all__ = [
    'OffseasonPhase',
    'OffseasonController',
    'TeamNeedsAnalyzer',
    'NeedUrgency',
    'MarketValueCalculator',
]
