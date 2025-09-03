"""
Clock management system for coaching archetypes.

This module provides clock management strategies for different coaching archetypes,
allowing for realistic tempo variations in play execution.
"""

from game_engine.coaching.clock.clock_strategy_manager import ClockStrategyManager
from game_engine.coaching.clock.base_strategy import ClockStrategy
from game_engine.coaching.clock.context import GameContext
from game_engine.coaching.clock.strategies import (
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