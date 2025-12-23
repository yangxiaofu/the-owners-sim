"""
Preseason Handler - DEPRECATED.

DEPRECATED: This handler is for the old PRESEASON_WEEK_1/2/3 stages which have been
superseded by OFFSEASON_PRESEASON_W1/W2/W3 stages in the offseason flow.

Modern NFL (2024+) preseason:
- Preseason schedule is generated at end of training camp
- Games are simulated during OFFSEASON_PRESEASON_W1/W2/W3 stages
- Single cutdown date (90 → 53) after Week 3

Use OffseasonHandler for:
- OFFSEASON_PRESEASON_W1: Game simulation only
- OFFSEASON_PRESEASON_W2: Game simulation only
- OFFSEASON_PRESEASON_W3: Game simulation + final roster cuts (90 → 53)

This handler is maintained for backwards compatibility only.
"""

import warnings
from typing import Any, Dict, Optional
import logging

from ..stage_definitions import Stage, StageType
from ..services.season_init_service import SeasonInitializationService

logger = logging.getLogger(__name__)


class PreseasonHandler:
    """
    DEPRECATED: Handler for legacy preseason stages (PRESEASON_WEEK_1/2/3).

    This handler is deprecated in favor of the offseason preseason stages:
    - OFFSEASON_PRESEASON_W1/W2/W3 (handled by OffseasonHandler)

    These stages now handle both game simulation and roster cuts.
    Season initialization has been moved to end of training camp.

    This handler is kept for backwards compatibility only and will log
    deprecation warnings when used.
    """

    def __init__(self):
        """Initialize handler (no dependencies - all via context)."""
        self._season_initialized: Dict[str, bool] = {}  # Cache: dynasty_id -> initialized

    def execute(self, stage: Stage, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute preseason stage.

        Args:
            stage: Current preseason stage
            context: Execution context with dynasty_id, db_path, etc.

        Returns:
            Dict with events_processed, initialization_results (if applicable)
        """
        dynasty_id = context.get("dynasty_id")
        db_path = self._get_db_path(context)
        season = stage.season_year

        events = []
        init_results = []

        # On PRESEASON_WEEK_1 entry, initialize the season
        if stage.stage_type == StageType.PRESEASON_WEEK_1:
            cache_key = f"{dynasty_id}_{season}"

            if cache_key not in self._season_initialized:
                events.append(f"Initializing Season {season}...")

                try:
                    # from_season is the previous season (for archiving)
                    # to_season is the new season being initialized
                    init_service = SeasonInitializationService(
                        db_path=db_path,
                        dynasty_id=dynasty_id,
                        from_season=season - 1,
                        to_season=season
                    )

                    results = init_service.run_all()

                    for result in results:
                        status_icon = "✓" if result.status.value == "completed" else "✗"
                        events.append(f"{status_icon} {result.step_name}: {result.message}")
                        init_results.append({
                            "step": result.step_name,
                            "status": result.status.value,
                            "message": result.message
                        })

                    events.append(f"Season {season} ready!")
                    self._season_initialized[cache_key] = True

                except Exception as e:
                    logger.error(f"Season initialization failed: {e}")
                    events.append(f"Season initialization error: {str(e)}")
            else:
                events.append(f"Season {season} already initialized")

        # Handle preseason week (exhibition games - future enhancement)
        week_num = self._get_week_number(stage.stage_type)
        events.append(f"Preseason Week {week_num} complete")

        return {
            "games_played": [],  # Preseason games (future)
            "events_processed": events,
            "initialization_results": init_results,
        }

    def can_advance(self, stage: Stage, context: Dict[str, Any]) -> bool:
        """
        Check if preseason stage can advance.

        Preseason weeks auto-advance after execution.

        Returns:
            True (preseason stages always advance after execute)
        """
        return True

    def get_stage_preview(self, stage: Stage, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get preview data for preseason stage.

        Args:
            stage: Current preseason stage
            context: Execution context

        Returns:
            Preview dict for UI display
        """
        week_num = self._get_week_number(stage.stage_type)
        season = stage.season_year

        return {
            "stage_name": f"Preseason Week {week_num}",
            "description": f"Season {season} preseason games",
            "season": season,
            "week": week_num,
            "is_interactive": False,  # Auto-advances
        }

    def _get_db_path(self, context: Dict[str, Any]) -> Optional[str]:
        """Extract database path from context."""
        if db_path := context.get("db_path"):
            return db_path
        if unified_api := context.get("unified_api"):
            return unified_api.database_path
        return None

    def _get_week_number(self, stage_type: StageType) -> int:
        """Get week number from preseason stage type."""
        mapping = {
            StageType.PRESEASON_WEEK_1: 1,
            StageType.PRESEASON_WEEK_2: 2,
            StageType.PRESEASON_WEEK_3: 3,
        }
        return mapping.get(stage_type, 1)
