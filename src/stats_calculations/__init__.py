"""
Statistical Calculations module for The Owner's Sim.

Provides statistical calculation functions and utilities for NFL simulation.
Renamed from 'statistics' to 'stats_calculations' to avoid conflict with Python's built-in statistics module.
"""

from .calculations import (
    calculate_passer_rating,
    calculate_yards_per_carry,
    calculate_catch_rate,
    calculate_yards_per_reception,
    calculate_yards_per_attempt,
    calculate_fg_percentage,
    calculate_xp_percentage,
    safe_divide,
)

__all__ = [
    "calculate_passer_rating",
    "calculate_yards_per_carry",
    "calculate_catch_rate",
    "calculate_yards_per_reception",
    "calculate_yards_per_attempt",
    "calculate_fg_percentage",
    "calculate_xp_percentage",
    "safe_divide",
]
