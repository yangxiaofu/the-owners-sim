"""
Clock management system for coaching archetypes.

This module provides clock management strategies for different coaching archetypes,
allowing for realistic tempo variations in play execution.
"""

from .clock_strategy_manager import ClockStrategyManager
from .base_strategy import ClockStrategy
from .context import GameContext
from .strategies import (
    RunHeavyStrategy,
    AirRaidStrategy,
    WestCoastStrategy,
    BalancedStrategy,
    CLOCK_STRATEGIES
)

__all__ = [
    'ClockStrategyManager',
    'ClockStrategy',
    'GameContext',
    'RunHeavyStrategy',
    'AirRaidStrategy', 
    'WestCoastStrategy',
    'BalancedStrategy',
    'CLOCK_STRATEGIES'
]