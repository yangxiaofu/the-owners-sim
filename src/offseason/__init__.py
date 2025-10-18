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
"""

from offseason.offseason_phases import OffseasonPhase
from offseason.offseason_controller import OffseasonController

__all__ = [
    'OffseasonPhase',
    'OffseasonController',
]
