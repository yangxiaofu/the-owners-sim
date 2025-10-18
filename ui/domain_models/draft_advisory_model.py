"""
Draft Advisory Data Model for The Owner's Sim UI

Business logic layer for draft prospect recommendations.

Phase 1: Placeholder with mock data
Phase 2: Full implementation with draft board and prospect matching
"""

from typing import List, Dict, Any
import sys
import os

# Add parent directories to path
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)


class DraftAdvisoryModel:
    """
    Domain model for draft advisory operations.

    Provides:
    - Draft prospects aligned to team needs
    - Team fit scores
    - Round-by-round recommendations

    Controllers delegate to this layer for draft advisory access.
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize draft advisory model.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        # TODO Phase 2: Initialize database APIs
        # self.draft_board_api = DraftBoardAPI(database_path=db_path)
        # self.scouting_model = ScoutingDataModel(db_path, dynasty_id, season)

    def get_prospects_by_need(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get draft prospects matched to team needs.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of round recommendations with top prospects
        """
        # TODO Phase 2: Implement draft board analysis and need matching
        # return self._match_prospects_to_needs(team_id)

        # Phase 1: Mock data
        return [
            {
                "round": 1,
                "pick": 15,
                "position_need": "Offensive Line",
                "top_prospects": [
                    {
                        "name": "O. Fashanu",
                        "position": "OT",
                        "school": "Penn St.",
                        "grade": "A",
                        "fit": 95,
                        "notes": "Elite pass protector, immediate starter"
                    },
                    {
                        "name": "J. Latham",
                        "position": "OT",
                        "school": "Alabama",
                        "grade": "A-",
                        "fit": 90,
                        "notes": "Physical run blocker, zone scheme fit"
                    },
                    {
                        "name": "T. Fautanu",
                        "position": "OG",
                        "school": "Washington",
                        "grade": "B+",
                        "fit": 88,
                        "notes": "Versatile interior lineman, high floor"
                    }
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

    def calculate_team_fit(self, prospect_id: int, team_id: int) -> int:
        """
        Calculate team fit score for prospect.

        Args:
            prospect_id: Prospect identifier
            team_id: Team ID (1-32)

        Returns:
            Team fit score (0-100)
        """
        # TODO Phase 2: Implement sophisticated fit calculation
        # Consider: scheme fit, position need, roster composition, coaching staff preferences

        # Phase 1: Mock calculation
        return 85  # Placeholder

    def get_draft_board(self, round: int = None) -> List[Dict[str, Any]]:
        """
        Get full draft board or specific round.

        Args:
            round: Optional round filter (1-7)

        Returns:
            List of prospects in draft order
        """
        # TODO Phase 2: Implement draft board database query
        # return self.draft_board_api.get_prospects(round=round)

        # Phase 1: Mock data
        return [
            {"rank": 1, "name": "C. Williams", "position": "QB", "school": "USC", "grade": "A+"},
            {"rank": 2, "name": "M. Harrison Jr.", "position": "WR", "school": "Ohio St.", "grade": "A+"},
            # ... more prospects
        ]
