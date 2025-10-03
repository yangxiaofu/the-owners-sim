"""
Interactive Playoff Simulator Package

Provides calendar-based interactive NFL playoff simulation capabilities.

Main Components:
- InteractivePlayoffSimulator: Menu-driven playoff simulation interface
- PlayoffController: Calendar-based playoff orchestration
- RandomPlayoffSeeder: Random playoff seeding generation
- Display utilities: Terminal UI formatting for playoffs

Usage:
    from demo.interactive_playoff_sim import InteractivePlayoffSimulator

    simulator = InteractivePlayoffSimulator(
        dynasty_id="my_playoffs",
        season_year=2024
    )
    simulator.run()

Or run directly:
    PYTHONPATH=src python demo/interactive_playoff_sim/interactive_playoff_sim.py
"""

from .interactive_playoff_sim import InteractivePlayoffSimulator
from .playoff_controller import PlayoffController
from .random_playoff_seeder import RandomPlayoffSeeder

__all__ = [
    'InteractivePlayoffSimulator',
    'PlayoffController',
    'RandomPlayoffSeeder',
]

__version__ = '1.0.0'
