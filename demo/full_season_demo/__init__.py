"""
Full Season Simulation Demo

A comprehensive NFL season simulation from Week 1 through the Super Bowl,
featuring seamless phase transitions, automatic playoff seeding, and
complete statistical tracking.

Main Components:
    - full_season_sim.py: Interactive CLI interface
    - full_season_controller.py: Core orchestration logic
    - display_utils.py: Terminal UI utilities

Usage:
    cd demo/full_season_demo
    PYTHONPATH=../../src python full_season_sim.py

Features:
    - 272-game regular season (Weeks 1-18)
    - Automatic playoff seeding from standings
    - 13-game playoff tournament (Wild Card → Super Bowl)
    - Dynasty isolation with complete stat separation
    - Interactive day/week advancement
    - Comprehensive season summaries

Database:
    Location: demo/full_season_demo/data/
    Format: SQLite3 with season_type column for stat separation
    Tables: games, player_game_stats, standings, dynasties

See README.md for detailed documentation and examples.
"""

__version__ = "1.0.0"
__author__ = "The Owners Sim Team"

# Package metadata
PACKAGE_NAME = "full_season_demo"
DESCRIPTION = "Complete NFL season simulation with playoffs"

# Default configuration
DEFAULT_DATABASE_DIR = "data"
DEFAULT_SEASON_YEAR = 2024
DEFAULT_DYNASTY_PREFIX = "full_season"

# Export main components (when implemented)
__all__ = [
    "FullSeasonController",
    "FullSeasonSimulator",
]
