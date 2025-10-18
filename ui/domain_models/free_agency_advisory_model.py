"""
Free Agency Advisory Data Model for The Owner's Sim UI

Business logic layer for free agency target recommendations.

Phase 1: Placeholder with mock data
Phase 2: Full implementation with FA market analysis
"""

from typing import List, Dict, Any
import sys
import os

# Add parent directories to path
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)


class FreeAgencyAdvisoryModel:
    """
    Domain model for free agency advisory operations.

    Provides:
    - Priority FA targets by need level
    - Market value estimates
    - Scouting director recommendations

    Controllers delegate to this layer for FA advisory access.
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize free agency advisory model.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        # TODO Phase 2: Initialize database APIs
        # self.fa_pool_api = FreeAgentPoolAPI(database_path=db_path)
        # self.scouting_model = ScoutingDataModel(db_path, dynasty_id, season)

    def get_fa_targets_by_priority(self) -> Dict[str, Any]:
        """
        Get FA targets organized by priority level.

        Returns:
            Dict with critical, moderate, and optional priority targets
        """
        # TODO Phase 2: Implement FA pool analysis and priority ranking
        # return self._rank_fa_targets_by_need()

        # Phase 1: Mock data
        return {
            "critical": {
                "position": "Offensive Line (LG)",
                "rationale": "Starter void, QB protection critical",
                "targets": [
                    {
                        "name": "Q. Nelson",
                        "overall": 92,
                        "est_cost": 18_000_000,
                        "note": "Elite guard, top priority",
                        "fit_score": 98
                    },
                    {
                        "name": "C. Lindstrom",
                        "overall": 88,
                        "est_cost": 14_000_000,
                        "note": "Solid fit for zone scheme",
                        "fit_score": 92
                    }
                ]
            },
            "moderate": {
                "position": "Linebacker depth",
                "rationale": "Depth chart thin, need veteran presence",
                "targets": [
                    {
                        "name": "B. Wagner",
                        "overall": 85,
                        "est_cost": 8_000_000,
                        "note": "Veteran leader, strong coverage",
                        "fit_score": 85
                    }
                ]
            },
            "optional": {
                "position": "Special teams specialists",
                "rationale": "Can address in late draft rounds",
                "targets": []
            }
        }

    def estimate_market_value(self, player_overall: int, position: str, years_pro: int) -> int:
        """
        Estimate FA market value for player.

        Args:
            player_overall: Player overall rating (0-99)
            position: Position abbreviation
            years_pro: Years of professional experience

        Returns:
            Estimated annual market value in dollars
        """
        # TODO Phase 2: Implement sophisticated market value estimation
        # Consider position scarcity, recent contracts, team cap situations

        # Phase 1: Simple estimation
        base_value = 1_000_000
        if player_overall >= 90:
            base_value = 20_000_000
        elif player_overall >= 85:
            base_value = 12_000_000
        elif player_overall >= 80:
            base_value = 8_000_000
        elif player_overall >= 75:
            base_value = 5_000_000

        return base_value
