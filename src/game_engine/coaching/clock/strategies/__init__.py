"""
Clock management strategies for different coaching archetypes.

This module provides concrete implementations of clock strategies for various
coaching philosophies, each with distinct tempo and timing characteristics.
"""

from .run_heavy_strategy import RunHeavyStrategy
from .air_raid_strategy import AirRaidStrategy  
from .west_coast_strategy import WestCoastStrategy
from .balanced_strategy import BalancedStrategy

# Strategy registry for easy instantiation by archetype name
CLOCK_STRATEGIES = {
    'run_heavy': RunHeavyStrategy,
    'air_raid': AirRaidStrategy,
    'west_coast': WestCoastStrategy,
    'balanced': BalancedStrategy,
}

__all__ = [
    'RunHeavyStrategy',
    'AirRaidStrategy', 
    'WestCoastStrategy',
    'BalancedStrategy',
    'CLOCK_STRATEGIES',
]