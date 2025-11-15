"""
Draft Preparation Service

Handles draft class generation triggering during offseason-to-preseason transitions.
Part of Milestone 1: Complete Multi-Year Season Cycle implementation.

Extracted from SeasonCycleController following service extraction pattern (Phase 3).
"""

import logging
import time
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.offseason.draft_manager import DraftManager
    from src.database.draft_class_api import DraftClassAPI


class DraftPreparationService:
    """
    Service for preparing draft classes for upcoming seasons.

    Responsibilities:
    - Trigger draft class generation (300 prospects)
    - Validate draft class existence
    - Wrap DraftManager for handler dependency injection

    Follows service extraction pattern from Phase 3 (TransactionService).
    Uses dependency injection for testability.
    """

    def __init__(
        self,
        draft_manager: 'DraftManager',
        draft_api: 'DraftClassAPI',
        dynasty_id: str
    ):
        """
        Initialize draft preparation service.

        Args:
            draft_manager: DraftManager instance for draft operations
            draft_api: DraftClassAPI instance for validation
            dynasty_id: Dynasty context for isolation
        """
        self.draft_manager = draft_manager
        self.draft_api = draft_api
        self.dynasty_id = dynasty_id
        self.logger = logging.getLogger(self.__class__.__name__)

    def prepare_draft_class(self, season_year: int, size: int = 300) -> Dict[str, Any]:
        """
        Generate draft class for upcoming season (synchronous, ~2-5 seconds).

        Logic:
        1. Check if draft class already exists for season_year
        2. If exists: Log warning and return existing class info
        3. If not exists: Call draft_manager.generate_draft_class(size)
        4. Validate generation succeeded
        5. Return draft class info

        Per user choice: SYNCHRONOUS operation (blocks for 2-5 seconds).
        Per user choice: FAIL LOUDLY if generation fails (don't catch exceptions).

        Args:
            season_year: Season year for draft class (e.g., 2025)
            size: Number of prospects to generate (default 300)

        Returns:
            Dict with:
                - draft_class_id: Generated class ID
                - season_year: Season year
                - total_players: Number of prospects generated
                - generation_time_seconds: How long it took
                - already_existed: Boolean (True if class already existed)

        Raises:
            ValueError: If draft class already exists (raised by DraftClassAPI)
            RuntimeError: If draft generation fails (raised by DraftClassAPI)
        """
        self.logger.info(f"Preparing draft class for season {season_year}...")

        # Check if draft class already exists
        if self.validate_draft_class_exists(season_year):
            self.logger.warning(
                f"Draft class for {season_year} already exists, skipping generation"
            )

            # Get existing class info
            existing_info = self.get_draft_class_info(season_year)

            return {
                'draft_class_id': existing_info['draft_class_id'],
                'season_year': season_year,
                'total_players': existing_info['total_prospects'],
                'generation_time_seconds': 0.0,
                'already_existed': True
            }

        # Generate new draft class
        self.logger.info(f"Generating draft class for season {season_year}...")
        print(f"[DRAFT_PREPARATION] Generating draft class for season {season_year}...")

        start_time = time.time()

        # Generate draft class (let exceptions propagate - fail loudly)
        prospects = self.draft_manager.generate_draft_class(size=size)

        generation_time = time.time() - start_time

        # Log completion
        self.logger.info(
            f"Draft class generated: {len(prospects)} prospects in {generation_time:.2f} seconds"
        )
        print(
            f"[DRAFT_PREPARATION] ✅ Draft class generated: "
            f"{len(prospects)} prospects in {generation_time:.2f} seconds"
        )

        # Log warning if generation took too long
        if generation_time > 5.0:
            self.logger.warning(
                f"Draft class generation took longer than expected: {generation_time:.2f} seconds"
            )
            print(
                f"[DRAFT_PREPARATION] ⚠️  Warning: Generation took {generation_time:.2f} seconds "
                f"(expected <5 seconds)"
            )

        # Get draft class info for return
        draft_info = self.get_draft_class_info(season_year)

        return {
            'draft_class_id': draft_info['draft_class_id'],
            'season_year': season_year,
            'total_players': len(prospects),
            'generation_time_seconds': round(generation_time, 2),
            'already_existed': False
        }

    def validate_draft_class_exists(self, season_year: int) -> bool:
        """
        Check if draft class already exists for season year.

        Uses draft_api.dynasty_has_draft_class(dynasty_id, season_year).

        Args:
            season_year: Season year to check

        Returns:
            True if draft class exists, False otherwise
        """
        exists = self.draft_api.dynasty_has_draft_class(self.dynasty_id, season_year)

        self.logger.debug(
            f"Draft class existence check for season {season_year}: {exists}"
        )

        return exists

    def get_draft_class_info(self, season_year: int) -> Optional[Dict[str, Any]]:
        """
        Get information about existing draft class.

        Uses draft_api.get_draft_class_info(dynasty_id, season_year).

        Args:
            season_year: Season year to query

        Returns:
            Dict with draft class info if exists, None otherwise
        """
        info = self.draft_api.get_draft_class_info(self.dynasty_id, season_year)

        if info:
            self.logger.debug(
                f"Retrieved draft class info for season {season_year}: "
                f"{info['total_prospects']} prospects"
            )
        else:
            self.logger.debug(f"No draft class found for season {season_year}")

        return info
