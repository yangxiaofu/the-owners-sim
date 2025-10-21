"""
Team Needs Analyzer

Analyzes team roster to identify positional weaknesses and priorities.
Used by AI to make intelligent free agency and draft decisions.
"""

from typing import List, Dict, Any, Tuple
from enum import Enum
import json

from database.player_roster_api import PlayerRosterAPI
from depth_chart.depth_chart_api import DepthChartAPI
from salary_cap.cap_database_api import CapDatabaseAPI


class NeedUrgency(Enum):
    """Priority levels for positional needs."""
    CRITICAL = 5  # No starter or starter < 70 overall
    HIGH = 4      # Starter 70-75 overall or no backup
    MEDIUM = 3    # Starter 75-80 overall or weak depth
    LOW = 2       # Starter 80-85 overall, adequate depth
    NONE = 1      # Starter 85+ overall, good depth


class TeamNeedsAnalyzer:
    """
    Analyzes team roster to identify positional needs.

    Evaluates:
    - Starter quality (overall rating)
    - Depth quality and quantity
    - Age and contract status
    - Position importance (QB > RB, etc.)
    """

    # Position value tiers (affects urgency calculations)
    TIER_1_POSITIONS = ['quarterback', 'defensive_end', 'left_tackle', 'right_tackle']
    TIER_2_POSITIONS = ['wide_receiver', 'cornerback', 'center']
    TIER_3_POSITIONS = ['running_back', 'linebacker', 'safety', 'left_guard', 'right_guard']
    TIER_4_POSITIONS = ['tight_end', 'defensive_tackle']

    # Minimum acceptable starter ratings by tier
    STARTER_THRESHOLDS = {
        1: 75,  # Premium positions need 75+ starter
        2: 72,  # Important positions need 72+ starter
        3: 70,  # Standard positions need 70+ starter
        4: 68   # Lower value positions need 68+ starter
    }

    def __init__(self, database_path: str, dynasty_id: str):
        """
        Initialize team needs analyzer.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Dynasty identifier for isolation
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id

        self.player_api = PlayerRosterAPI(database_path)
        self.depth_chart_api = DepthChartAPI(database_path)
        self.cap_api = CapDatabaseAPI(database_path)

    def analyze_team_needs(
        self,
        team_id: int,
        season: int,
        include_future_contracts: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Analyze team roster and return prioritized list of needs.

        Args:
            team_id: Team ID (1-32)
            season: Current season year
            include_future_contracts: Consider upcoming free agents

        Returns:
            List of need dicts sorted by urgency (highest first):
            [
                {
                    'position': 'quarterback',
                    'urgency': NeedUrgency.CRITICAL,
                    'urgency_score': 5,
                    'starter_overall': 65,
                    'depth_count': 1,
                    'avg_depth_overall': 60,
                    'starter_leaving': False,
                    'reason': 'No quality starter (65 overall)'
                },
                ...
            ]
        """
        needs = []

        # Get full depth chart
        depth_chart = self.depth_chart_api.get_full_depth_chart(
            dynasty_id=self.dynasty_id,
            team_id=team_id
        )

        # Get expiring contracts if requested
        expiring_players = []
        if include_future_contracts:
            expiring_contracts = self.cap_api.get_pending_free_agents(
                team_id=team_id,
                season=season,
                dynasty_id=self.dynasty_id
            )
            expiring_players = [p['player_id'] for p in expiring_contracts]

        # Analyze each important position
        important_positions = (
            self.TIER_1_POSITIONS +
            self.TIER_2_POSITIONS +
            self.TIER_3_POSITIONS +
            self.TIER_4_POSITIONS
        )

        for position in important_positions:
            need = self._analyze_position_need(
                position=position,
                depth_chart=depth_chart,
                expiring_players=expiring_players
            )

            if need['urgency'] != NeedUrgency.NONE:
                needs.append(need)

        # Sort by urgency (highest first), then by position tier
        needs.sort(
            key=lambda x: (x['urgency_score'], -self._get_position_tier(x['position'])),
            reverse=True
        )

        return needs

    def _analyze_position_need(
        self,
        position: str,
        depth_chart: Dict[str, List[Dict]],
        expiring_players: List[int]
    ) -> Dict[str, Any]:
        """
        Analyze need for a specific position.

        Args:
            position: Position name
            depth_chart: Full team depth chart
            expiring_players: List of player IDs with expiring contracts

        Returns:
            Need dict with urgency and details
        """
        position_players = depth_chart.get(position, [])

        # Sort by depth order
        position_players.sort(key=lambda p: p['depth_order'])

        # Get starter (depth_order = 1)
        starter = next((p for p in position_players if p['depth_order'] == 1), None)

        # Get backups (depth_order > 1 and < 99)
        backups = [p for p in position_players if 1 < p['depth_order'] < 99]

        # Calculate metrics
        starter_overall = starter['overall'] if starter else 0
        depth_count = len(backups)
        avg_depth_overall = sum(p['overall'] for p in backups) / len(backups) if backups else 0

        # Check if starter is leaving
        starter_leaving = starter and starter['player_id'] in expiring_players

        # Determine urgency
        urgency, reason = self._calculate_urgency(
            position=position,
            starter_overall=starter_overall,
            depth_count=depth_count,
            avg_depth_overall=avg_depth_overall,
            starter_leaving=starter_leaving
        )

        return {
            'position': position,
            'urgency': urgency,
            'urgency_score': urgency.value,
            'starter_overall': starter_overall,
            'depth_count': depth_count,
            'avg_depth_overall': avg_depth_overall,
            'starter_leaving': starter_leaving,
            'reason': reason
        }

    def _calculate_urgency(
        self,
        position: str,
        starter_overall: int,
        depth_count: int,
        avg_depth_overall: float,
        starter_leaving: bool
    ) -> Tuple[NeedUrgency, str]:
        """
        Calculate urgency level for a position need.

        Args:
            position: Position name
            starter_overall: Starter's overall rating
            depth_count: Number of backups
            avg_depth_overall: Average overall of backups
            starter_leaving: Whether starter contract is expiring

        Returns:
            (urgency_level, reason_string)
        """
        tier = self._get_position_tier(position)
        threshold = self.STARTER_THRESHOLDS[tier]

        # CRITICAL: No starter or starter well below threshold
        if starter_overall == 0:
            return NeedUrgency.CRITICAL, f"No starter at {position}"

        if starter_overall < threshold - 5:
            return NeedUrgency.CRITICAL, f"Starter well below standard ({starter_overall} overall)"

        # CRITICAL: Starter leaving and no adequate replacement
        if starter_leaving and (depth_count == 0 or avg_depth_overall < threshold - 5):
            return NeedUrgency.CRITICAL, f"Starter leaving, no replacement ({starter_overall} overall)"

        # HIGH: Starter below threshold
        if starter_overall < threshold:
            return NeedUrgency.HIGH, f"Starter below standard ({starter_overall} overall)"

        # HIGH: Starter leaving but have backup
        if starter_leaving:
            return NeedUrgency.HIGH, f"Starter leaving ({starter_overall} overall)"

        # HIGH: No depth
        if depth_count == 0:
            return NeedUrgency.HIGH, f"No backup depth"

        # MEDIUM: Starter decent but weak depth
        if starter_overall < threshold + 5 and avg_depth_overall < threshold - 5:
            return NeedUrgency.MEDIUM, f"Weak depth behind starter"

        # MEDIUM: Starter good but no depth
        if depth_count < 2 and tier <= 2:  # Premium positions need depth
            return NeedUrgency.MEDIUM, f"Insufficient depth"

        # LOW: Starter good, adequate depth
        if starter_overall >= threshold + 5 and starter_overall < 85:
            return NeedUrgency.LOW, f"Starter solid, could upgrade depth"

        # NONE: Starter great, good depth
        return NeedUrgency.NONE, f"Position well-staffed"

    def _get_position_tier(self, position: str) -> int:
        """Get position tier (1-4, lower is more important)."""
        if position in self.TIER_1_POSITIONS:
            return 1
        elif position in self.TIER_2_POSITIONS:
            return 2
        elif position in self.TIER_3_POSITIONS:
            return 3
        else:
            return 4

    def get_top_needs(
        self,
        team_id: int,
        season: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get top N positional needs for quick reference.

        Args:
            team_id: Team ID (1-32)
            season: Current season year
            limit: Number of top needs to return

        Returns:
            List of top needs
        """
        all_needs = self.analyze_team_needs(team_id, season)
        return all_needs[:limit]
