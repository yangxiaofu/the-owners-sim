"""
Season Transition Service

Orchestrates complete year transition during offseason-to-preseason phase changes.
Coordinates season year increment, contract transitions, and draft class preparation.

Part of Milestone 1: Complete Multi-Year Season Cycle implementation.
"""

import logging
import time
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.contract_transition_service import ContractTransitionService
    from src.services.draft_preparation_service import DraftPreparationService
    from src.season.season_year_synchronizer import SeasonYearSynchronizer


class SeasonTransitionService:
    """
    Service for orchestrating complete year transitions.

    Responsibilities:
    - Coordinate season year increment via SeasonYearSynchronizer
    - Trigger contract year increments and expirations
    - Trigger draft class generation for new season
    - Provide unified result reporting

    Follows service extraction pattern from Phase 3 (TransactionService).
    Uses dependency injection for testability.

    Execution Order (Critical Dependencies):
    1. Increment season year (2024 → 2025) via synchronizer
    2. Handle contract transitions (increment years, detect expirations)
    3. Prepare draft class for new season (generate 300 prospects)
    """

    def __init__(
        self,
        contract_service: "ContractTransitionService",
        draft_service: "DraftPreparationService",
        dynasty_id: str
    ):
        """
        Initialize season transition orchestrator.

        Args:
            contract_service: ContractTransitionService instance
            draft_service: DraftPreparationService instance
            dynasty_id: Dynasty context for isolation

        Note: SeasonYearSynchronizer is passed per-call to execute_year_transition()
              because it's bound to SeasonCycleController lifecycle.
        """
        self.contract_service = contract_service
        self.draft_service = draft_service
        self.dynasty_id = dynasty_id
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute_year_transition(
        self,
        old_year: int,
        new_year: int,
        synchronizer: "SeasonYearSynchronizer"
    ) -> Dict[str, Any]:
        """
        Execute complete year transition orchestration.

        This is the PRIMARY method called by OffseasonToPreseasonHandler.
        Coordinates all year transition operations in correct order.

        Execution Steps:
        1. Increment season year atomically (synchronizer.synchronize_year)
        2. Increment contract years and detect expirations
        3. Generate draft class for new season

        Per user choice: Synchronous execution (blocks for ~5-10 seconds total)
        Per user choice: Fail loudly (exceptions propagate to caller)

        Args:
            old_year: Previous season year (e.g., 2024)
            new_year: New season year (e.g., 2025)
            synchronizer: SeasonYearSynchronizer instance for atomic year update

        Returns:
            Dict with:
                - old_year: Previous year
                - new_year: New year
                - year_increment_success: Boolean
                - contract_transition: ContractTransitionService result dict
                - draft_preparation: DraftPreparationService result dict
                - total_duration_seconds: Total execution time
                - steps_completed: List of completed step names

        Raises:
            Exception: If any step fails (fail loudly per user choice)

        Example:
            result = season_transition_service.execute_year_transition(
                old_year=2024,
                new_year=2025,
                synchronizer=self.synchronizer
            )
        """
        self.logger.info(
            f"\n{'='*80}\n"
            f"[SEASON_TRANSITION] Starting year transition: {old_year} → {new_year}\n"
            f"  Dynasty: {self.dynasty_id}\n"
            f"{'='*80}"
        )

        start_time = time.time()
        steps_completed = []
        results = {
            'old_year': old_year,
            'new_year': new_year,
            'year_increment_success': False,
            'contract_transition': None,
            'draft_preparation': None,
            'total_duration_seconds': 0.0,
            'steps_completed': steps_completed
        }

        try:
            # ============================================================
            # STEP 1: Increment Season Year (Atomic Synchronization)
            # ============================================================
            self.logger.info(f"[SEASON_TRANSITION] Step 1/3: Incrementing season year...")
            step1_start = time.time()

            # Use synchronizer to atomically update year across all components
            synchronizer.synchronize_year(
                new_year=new_year,
                reason=f"OFFSEASON→PRESEASON transition ({old_year}→{new_year})"
            )

            step1_duration = time.time() - step1_start
            results['year_increment_success'] = True
            steps_completed.append('year_increment')

            self.logger.info(
                f"[SEASON_TRANSITION] ✓ Step 1 complete ({step1_duration:.2f}s)\n"
                f"  Season year: {old_year} → {new_year}"
            )

            # ============================================================
            # STEP 2: Contract Transitions (Increment + Expirations)
            # ============================================================
            self.logger.info(
                f"[SEASON_TRANSITION] Step 2/3: Processing contract transitions..."
            )
            step2_start = time.time()

            # Increment contracts and handle expirations
            contract_result = self.contract_service.increment_all_contracts(
                season_year=new_year
            )

            step2_duration = time.time() - step2_start
            results['contract_transition'] = contract_result
            steps_completed.append('contract_transition')

            self.logger.info(
                f"[SEASON_TRANSITION] ✓ Step 2 complete ({step2_duration:.2f}s)\n"
                f"  Total contracts: {contract_result['total_contracts']}\n"
                f"  Still active: {contract_result['still_active']}\n"
                f"  Expired: {contract_result['expired_count']}"
            )

            # ============================================================
            # STEP 3: Draft Class Preparation
            # ============================================================
            self.logger.info(
                f"[SEASON_TRANSITION] Step 3/3: Preparing draft class for {new_year}..."
            )
            step3_start = time.time()

            # Generate draft class for upcoming season (synchronous)
            draft_result = self.draft_service.prepare_draft_class(
                season_year=new_year,
                size=300
            )

            step3_duration = time.time() - step3_start
            results['draft_preparation'] = draft_result
            steps_completed.append('draft_preparation')

            self.logger.info(
                f"[SEASON_TRANSITION] ✓ Step 3 complete ({step3_duration:.2f}s)\n"
                f"  Draft class: {draft_result['draft_class_id']}\n"
                f"  Prospects: {draft_result['total_players']}\n"
                f"  Already existed: {draft_result['already_existed']}"
            )

            # ============================================================
            # TRANSITION COMPLETE
            # ============================================================
            total_duration = time.time() - start_time
            results['total_duration_seconds'] = total_duration

            self.logger.info(
                f"\n{'='*80}\n"
                f"[SEASON_TRANSITION] ✅ Year transition complete!\n"
                f"  Old year: {old_year}\n"
                f"  New year: {new_year}\n"
                f"  Total duration: {total_duration:.2f}s\n"
                f"  Steps completed: {len(steps_completed)}/3\n"
                f"{'='*80}\n"
            )

            return results

        except Exception as e:
            # Fail loudly per user choice - let exception propagate
            total_duration = time.time() - start_time
            results['total_duration_seconds'] = total_duration

            self.logger.error(
                f"\n{'='*80}\n"
                f"[SEASON_TRANSITION] ❌ Year transition FAILED\n"
                f"  Old year: {old_year}\n"
                f"  New year: {new_year}\n"
                f"  Failed after: {total_duration:.2f}s\n"
                f"  Steps completed: {steps_completed}\n"
                f"  Error: {e}\n"
                f"{'='*80}\n",
                exc_info=True
            )

            # Re-raise exception (fail loudly)
            raise

    def validate_year_transition_state(
        self,
        expected_year: int,
        synchronizer: "SeasonYearSynchronizer"
    ) -> Dict[str, Any]:
        """
        Validate that year transition completed successfully.

        Checks:
        - Synchronizer current year matches expected year
        - Draft class exists for expected year
        - Contracts are in expected state

        Args:
            expected_year: Expected season year after transition
            synchronizer: SeasonYearSynchronizer to query

        Returns:
            Dict with validation results:
                - year_matches: Boolean
                - draft_class_exists: Boolean
                - all_valid: Boolean (True if all checks pass)
        """
        self.logger.debug(
            f"[SEASON_TRANSITION] Validating year transition state for {expected_year}"
        )

        # Check year synchronizer state
        current_year = synchronizer.get_current_year()
        year_matches = (current_year == expected_year)

        # Check draft class existence
        draft_exists = self.draft_service.validate_draft_class_exists(expected_year)

        all_valid = year_matches and draft_exists

        results = {
            'expected_year': expected_year,
            'current_year': current_year,
            'year_matches': year_matches,
            'draft_class_exists': draft_exists,
            'all_valid': all_valid
        }

        if all_valid:
            self.logger.info(
                f"[SEASON_TRANSITION] ✓ Year transition state valid for {expected_year}"
            )
        else:
            self.logger.warning(
                f"[SEASON_TRANSITION] ⚠️  Year transition state invalid:\n"
                f"  Expected year: {expected_year}\n"
                f"  Current year: {current_year} (match: {year_matches})\n"
                f"  Draft class exists: {draft_exists}"
            )

        return results
