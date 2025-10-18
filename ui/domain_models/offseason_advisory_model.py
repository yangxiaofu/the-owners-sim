"""
Offseason Advisory Data Model for The Owner's Sim UI

Business logic layer for offseason recommendations and advisory systems.
Orchestrates data from multiple sources to provide owner-centric insights.

Phase 1: Placeholder with mock data
Phase 2: Full implementation with database integration
"""

from typing import List, Dict, Any
import sys
import os

# Add parent directories to path
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)


class OffseasonAdvisoryModel:
    """
    Domain model for offseason advisory operations.

    Aggregates data from multiple sources to provide:
    - Franchise tag recommendations
    - Free agency strategy
    - Draft prospects aligned to team needs
    - Staff recommendation feed

    Controllers delegate to this layer for all offseason advisory access.
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize offseason advisory model.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        # TODO Phase 2: Initialize database APIs
        # self.scouting_model = ScoutingDataModel(db_path, dynasty_id, season)
        # self.fa_advisory_model = FreeAgencyAdvisoryModel(db_path, dynasty_id, season)
        # self.draft_advisory_model = DraftAdvisoryModel(db_path, dynasty_id, season)
        # self.staff_advisory_model = StaffAdvisoryModel(db_path, dynasty_id, season)

    def get_franchise_tag_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get franchise tag recommendations with staff rationale.

        Returns:
            List of player dictionaries with tag recommendations
        """
        # TODO Phase 2: Implement database query and recommendation logic
        # return self._calculate_tag_recommendations()

        # Phase 1: Mock data
        return [
            {
                "rank": 1,
                "player_name": "J. Sweat",
                "position": "DE",
                "overall": 89,
                "tag_cost": 19_700_000,
                "market_value": 22_000_000,
                "gm_rationale": "Elite pass rusher, critical to defense. Market value $22M+.",
                "coach_input": "Must keep. Top 5 in sacks last 2 years.",
                "recommendation": "APPLY TAG"
            },
            {
                "rank": 2,
                "player_name": "D. Goedert",
                "position": "TE",
                "overall": 84,
                "tag_cost": 11_300_000,
                "market_value": 10_000_000,
                "gm_rationale": "Solid starter, but could find replacement in draft.",
                "coach_input": None,
                "recommendation": "CONSIDER"
            }
        ]

    def get_free_agency_strategy(self) -> Dict[str, Any]:
        """
        Get free agency strategy with priority targets.

        Returns:
            Dict with priority levels and target recommendations
        """
        # TODO Phase 2: Implement database query and FA strategy logic
        # return self.fa_advisory_model.get_fa_strategy()

        # Phase 1: Mock data
        return {
            "critical": {
                "position": "Offensive Line (LG)",
                "targets": [
                    {"name": "Q. Nelson", "overall": 92, "est_cost": 18_000_000, "note": "Elite guard, top priority"},
                    {"name": "C. Lindstrom", "overall": 88, "est_cost": 14_000_000, "note": "Solid fit for zone scheme"}
                ]
            },
            "moderate": {
                "position": "Linebacker depth",
                "targets": [
                    {"name": "B. Wagner", "overall": 85, "est_cost": 8_000_000, "note": "Veteran leader, strong coverage"}
                ]
            },
            "optional": {
                "position": "Special teams specialists",
                "targets": [],
                "note": "Can address in late draft rounds"
            }
        }

    def get_draft_prospects(self) -> List[Dict[str, Any]]:
        """
        Get draft prospects aligned to team needs.

        Returns:
            List of draft round recommendations with top prospects
        """
        # TODO Phase 2: Implement database query and draft prospect logic
        # return self.draft_advisory_model.get_aligned_prospects()

        # Phase 1: Mock data
        return [
            {
                "round": 1,
                "pick": 15,
                "position_need": "Offensive Line",
                "top_prospects": [
                    {"name": "O. Fashanu", "position": "OT", "school": "Penn St.", "grade": "A", "fit": 95},
                    {"name": "J. Latham", "position": "OT", "school": "Alabama", "grade": "A-", "fit": 90},
                    {"name": "T. Fautanu", "position": "OG", "school": "Washington", "grade": "B+", "fit": 88}
                ]
            },
            {
                "round": 2,
                "pick": 46,
                "position_need": "Linebacker or BPA",
                "top_prospects": [],
                "note": "Scouting report available closer to draft"
            }
        ]

    def get_staff_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get staff recommendation feed timeline.

        Returns:
            List of staff recommendations with date, source, and message
        """
        # TODO Phase 2: Implement database query and staff feed logic
        # return self.staff_advisory_model.get_recent_recommendations()

        # Phase 1: Mock data
        return [
            {"date": "Mar 1", "source": "GM", "message": "Begin extension talks with J. Kelce before FA opens"},
            {"date": "Feb 28", "source": "OC", "message": "QB needs better pass protection - OL is top priority"},
            {"date": "Feb 25", "source": "DC", "message": "Consider re-signing F. Cox on 1-year vet deal"},
            {"date": "Feb 22", "source": "Scout", "message": "OL class is deep in draft, could wait until Round 2"},
            {"date": "Feb 20", "source": "GM", "message": "Target Q. Nelson in FA if cap space allows"},
            {"date": "Feb 18", "source": "DC", "message": "Need edge rusher depth - evaluate UFA market"}
        ]
