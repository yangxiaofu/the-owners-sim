"""
Team Registry Module

Provides dynasty-specific team data management for consistent team ID/name mappings.
"""

from .dynasty_team_registry import (
    DynastyTeamRegistry,
    TeamInfo,
    get_registry,
    initialize_dynasty_teams
)

__all__ = [
    'DynastyTeamRegistry',
    'TeamInfo', 
    'get_registry',
    'initialize_dynasty_teams'
]