"""
Depth Chart Validator

Validates depth chart assignments and checks position requirements.
"""

from typing import Dict, List
from depth_chart.depth_chart_types import (
    POSITION_REQUIREMENTS,
    UNASSIGNED_DEPTH_ORDER,
    OFFENSE_POSITIONS,
    DEFENSE_POSITIONS,
    SPECIAL_TEAMS_POSITIONS
)


class DepthChartValidator:
    """Validates depth chart assignments and position requirements."""

    @staticmethod
    def validate_depth_chart(
        dynasty_id: str,
        team_id: int,
        position_depth_charts: Dict[str, List[Dict]]
    ) -> Dict[str, List[str]]:
        """
        Validate entire depth chart and return errors/warnings.

        Args:
            dynasty_id: Dynasty context
            team_id: Team ID
            position_depth_charts: Dict mapping position -> list of player dicts

        Returns:
            Dict with 'errors' and 'warnings' lists
        """
        errors = []
        warnings = []

        for position, players in position_depth_charts.items():
            # Check for missing starters
            starters = [p for p in players if p.get('depth_chart_order') == 1]

            if len(starters) == 0:
                errors.append(f"{position} position has no starter")
            elif len(starters) > 1:
                errors.append(f"{position} has {len(starters)} players at depth_chart_order = 1")

            # Check for unassigned players
            unassigned = [p for p in players if p.get('depth_chart_order') == UNASSIGNED_DEPTH_ORDER]
            if unassigned:
                warnings.append(f"{position} has {len(unassigned)} unassigned player(s)")

            # Check for duplicate depth orders (excluding UNASSIGNED_DEPTH_ORDER)
            depth_orders = [p['depth_chart_order'] for p in players
                          if p.get('depth_chart_order') != UNASSIGNED_DEPTH_ORDER]
            if len(depth_orders) != len(set(depth_orders)):
                errors.append(f"{position} has duplicate depth_chart_order values")

            # Check minimum requirements
            assigned_count = len([p for p in players
                                if p.get('depth_chart_order') != UNASSIGNED_DEPTH_ORDER])

            if position in POSITION_REQUIREMENTS:
                min_required = POSITION_REQUIREMENTS[position]['minimum']
                recommended = POSITION_REQUIREMENTS[position]['recommended']

                if assigned_count < min_required:
                    errors.append(
                        f"{position} has only {assigned_count} assigned player(s), "
                        f"minimum {min_required} required"
                    )
                elif assigned_count < recommended:
                    warnings.append(
                        f"{position} has only {assigned_count} assigned player(s), "
                        f"{recommended} recommended"
                    )

        return {
            'errors': errors,
            'warnings': warnings
        }

    @staticmethod
    def has_starter(players: List[Dict]) -> bool:
        """
        Check if position has a starter assigned.

        Args:
            players: List of player dicts for a position

        Returns:
            True if position has exactly one starter (depth_chart_order=1)
        """
        starters = [p for p in players if p.get('depth_chart_order') == 1]
        return len(starters) == 1

    @staticmethod
    def get_depth_chart_gaps(position_depth_charts: Dict[str, List[Dict]]) -> Dict[str, int]:
        """
        Identify positions without starters.

        Args:
            position_depth_charts: Dict mapping position -> list of player dicts

        Returns:
            Dict mapping position -> gap count (0 = has starter, 1 = missing starter)
        """
        gaps = {}

        for position, players in position_depth_charts.items():
            has_starter = DepthChartValidator.has_starter(players)
            gaps[position] = 0 if has_starter else 1

        return gaps

    @staticmethod
    def check_depth_chart_compliance(
        position_depth_charts: Dict[str, List[Dict]]
    ) -> Dict[str, bool]:
        """
        Check if depth chart meets minimum requirements for each position.

        Args:
            position_depth_charts: Dict mapping position -> list of player dicts

        Returns:
            Dict mapping position -> compliance status (True/False)
        """
        compliance = {}

        for position, players in position_depth_charts.items():
            assigned_count = len([
                p for p in players
                if p.get('depth_chart_order') != UNASSIGNED_DEPTH_ORDER
            ])

            if position in POSITION_REQUIREMENTS:
                min_required = POSITION_REQUIREMENTS[position]['minimum']
                compliance[position] = assigned_count >= min_required
            else:
                # Unknown position - just check if has starter
                compliance[position] = DepthChartValidator.has_starter(players)

        return compliance

    @staticmethod
    def is_valid_position(position: str) -> bool:
        """
        Check if position is valid NFL position.

        Args:
            position: Position string (e.g., 'QB', 'RB')

        Returns:
            True if valid position
        """
        return position in (OFFENSE_POSITIONS | DEFENSE_POSITIONS | SPECIAL_TEAMS_POSITIONS)

    @staticmethod
    def get_position_group(position: str) -> str:
        """
        Get position group (Offense/Defense/Special Teams).

        Args:
            position: Position string

        Returns:
            'Offense', 'Defense', 'Special Teams', or 'Unknown'
        """
        if position in OFFENSE_POSITIONS:
            return 'Offense'
        elif position in DEFENSE_POSITIONS:
            return 'Defense'
        elif position in SPECIAL_TEAMS_POSITIONS:
            return 'Special Teams'
        else:
            return 'Unknown'
