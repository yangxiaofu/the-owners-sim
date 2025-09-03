"""
Team Management System

This package provides a comprehensive team identification and management system
for the football simulation game engine. It addresses the critical scoreboard bug
by standardizing team ID handling across all game components.

Key Components:
- team_types: Core team identification types (TeamID, TeamSide, TeamInfo)
- team_context: Game-specific team assignments and mappings
- team_registry: Central authority for team operations
- team_mapper: High-performance team ID translation service
- team_validator: Team operation validation framework

Usage:
    from game_engine.teams import TeamID, TeamInfo, TeamContext
    from game_engine.teams.team_service_provider import TeamServiceProvider
    
    # Create team services for a game
    services = TeamServiceProvider.create_services(home_data, away_data)
    
    # Resolve team from possession
    team_id = services.registry.resolve_team_from_possession(possession_id)
"""

from .team_types import TeamID, TeamSide, TeamInfo
from .team_context import TeamContext
from .team_registry import TeamRegistry
from .team_mapper import TeamMapper
from .team_validator import TeamValidator, ValidationResult

__all__ = [
    'TeamID', 'TeamSide', 'TeamInfo', 
    'TeamContext', 'TeamRegistry', 
    'TeamMapper', 'TeamValidator', 'ValidationResult'
]