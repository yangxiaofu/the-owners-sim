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

    def __init__(self, db_path: str, dynasty_id: str, main_window=None):
        """
        Initialize offseason controller.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            main_window: Reference to MainWindow for season access (optional)
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.main_window = main_window

    @property
    def season(self) -> int:
        """Current season year (proxied from main window)."""
        if self.main_window is not None:
            return self.main_window.season
        return 2025  # Fallback for testing/standalone usage

    def _get_data_model(self) -> OffseasonAdvisoryModel:
        """Lazy-initialized data model with current season."""
        return OffseasonAdvisoryModel(self.db_path, self.dynasty_id, self.season)

    def get_franchise_tag_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get franchise tag recommendations with staff rationale.

        Returns:
            List of player dictionaries with tag recommendations
        """
        return self._get_data_model().get_franchise_tag_recommendations()

    def get_free_agency_strategy(self) -> Dict[str, Any]:
        """
        Get free agency strategy with priority targets.

        Returns:
            Dict with priority levels and target recommendations
        """
        return self._get_data_model().get_free_agency_strategy()

    def get_draft_prospects(self) -> List[Dict[str, Any]]:
        """
        Get draft prospects aligned to team needs.

        Returns:
            List of draft round recommendations with top prospects
        """
        return self._get_data_model().get_draft_prospects()

    def get_staff_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get staff recommendation feed timeline.

        Returns:
            List of staff recommendations with date, source, and message
        """
        return self._get_data_model().get_staff_recommendations()
