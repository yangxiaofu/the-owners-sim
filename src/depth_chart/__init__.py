"""
Depth Chart System

Complete depth chart management system for NFL teams.

Main Components:
- DepthChartAPI: Database API layer for CRUD operations
- DepthChartManager: Business logic layer
- DepthChartValidator: Position validation and requirements
- POSITION_REQUIREMENTS: Minimum/recommended depth per position

Usage:
    from depth_chart import DepthChartAPI

    api = DepthChartAPI("data/database/nfl_simulation.db")

    # Set starter
    api.set_starter(dynasty_id="my_dynasty", team_id=22, player_id=1234, position="QB")

    # Get position depth chart
    qb_depth = api.get_position_depth_chart(dynasty_id="my_dynasty", team_id=22, position="QB")

    # Auto-generate depth chart
    api.auto_generate_depth_chart(dynasty_id="my_dynasty", team_id=22)
"""

from depth_chart.depth_chart_api import DepthChartAPI
from depth_chart.depth_chart_manager import DepthChartManager
from depth_chart.depth_chart_validator import DepthChartValidator
from depth_chart.depth_chart_types import (
    POSITION_REQUIREMENTS,
    UNASSIGNED_DEPTH_ORDER,
    OFFENSE_POSITIONS,
    DEFENSE_POSITIONS,
    SPECIAL_TEAMS_POSITIONS
)

__all__ = [
    'DepthChartAPI',
    'DepthChartManager',
    'DepthChartValidator',
    'POSITION_REQUIREMENTS',
    'UNASSIGNED_DEPTH_ORDER',
    'OFFENSE_POSITIONS',
    'DEFENSE_POSITIONS',
    'SPECIAL_TEAMS_POSITIONS',
]
