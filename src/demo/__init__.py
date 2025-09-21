"""
Demo Package

Interactive terminal demo components for the NFL season simulation system.
"""

# Simulation controllers removed with calendar system
# from .weekly_simulation_controller import WeeklySimulationController, WeekResults
from .results_display_formatter import ResultsDisplayFormatter
from .interactive_interface import InteractiveInterface

__all__ = [
    # 'WeeklySimulationController',  # Removed with calendar system
    # 'WeekResults',  # Removed with calendar system
    'ResultsDisplayFormatter',
    'InteractiveInterface'
]