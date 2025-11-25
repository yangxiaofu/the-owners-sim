"""
Game Cycle UI Package

Separate UI for the stage-based game cycle system.
Uses src/game_cycle backend instead of the day-by-day calendar system.
"""

from game_cycle_ui.main_window import GameCycleMainWindow

__all__ = ["GameCycleMainWindow"]