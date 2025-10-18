"""
Offseason Controller for The Owner's Sim UI

Thin controller for offseason advisory operations.
Delegates all business logic to OffseasonAdvisoryModel.
"""

from typing import List, Dict, Any
import sys
import os

# Add parent directories to path
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

from domain_models.offseason_advisory_model import OffseasonAdvisoryModel


class OffseasonController:
    """
    Controller for offseason view operations.

    Thin orchestration layer - all business logic delegated to OffseasonAdvisoryModel.
    Follows pattern: View → Controller → Domain Model → Database API
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize offseason controller.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year (default: 2025)
        """
        self.data_model = OffseasonAdvisoryModel(db_path, dynasty_id, season)

    def get_franchise_tag_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get franchise tag recommendations with staff rationale.

        Returns:
            List of player dictionaries with tag recommendations
        """
        return self.data_model.get_franchise_tag_recommendations()

    def get_free_agency_strategy(self) -> Dict[str, Any]:
        """
        Get free agency strategy with priority targets.

        Returns:
            Dict with priority levels and target recommendations
        """
        return self.data_model.get_free_agency_strategy()

    def get_draft_prospects(self) -> List[Dict[str, Any]]:
        """
        Get draft prospects aligned to team needs.

        Returns:
            List of draft round recommendations with top prospects
        """
        return self.data_model.get_draft_prospects()

    def get_staff_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get staff recommendation feed timeline.

        Returns:
            List of staff recommendations with date, source, and message
        """
        return self.data_model.get_staff_recommendations()
