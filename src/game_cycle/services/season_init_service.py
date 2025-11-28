"""
Season Initialization Service - Pipeline for initializing a new season.

Provides an extendable pipeline of initialization steps that run when
transitioning from offseason to a new season. Each step has a name,
description, handler, and required flag.

To extend:
1. Add a handler method (e.g., _archive_stats)
2. Add an InitStep to self._steps list
"""

from dataclasses import dataclass
from typing import Callable, List, Dict, Any
from enum import Enum


class StepStatus(Enum):
    """Status of an initialization step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class InitStep:
    """A single initialization step in the pipeline."""
    name: str
    description: str
    handler: Callable[[], Dict[str, Any]]  # Returns {"success": bool, "message": str}
    required: bool = True


@dataclass
class StepResult:
    """Result of executing a step."""
    step_name: str
    status: StepStatus
    message: str


class SeasonInitializationService:
    """
    Pipeline service for initializing a new season.

    Runs a series of steps in order, tracking progress and results.
    Easily extendable by adding new steps to the pipeline.

    Usage:
        service = SeasonInitializationService(db_path, dynasty_id, 2025, 2026)
        results = service.run_all()
        for result in results:
            print(f"{result.step_name}: {result.status.value}")
    """

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        from_season: int,
        to_season: int
    ):
        """
        Initialize the service.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            from_season: The season being completed (e.g., 2025)
            to_season: The new season starting (e.g., 2026)
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._from_season = from_season
        self._to_season = to_season

        # Define pipeline steps (order matters)
        self._steps: List[InitStep] = [
            InitStep(
                name="Reset Team Records",
                description="Resetting all team records to 0-0",
                handler=self._reset_team_records,
                required=True
            ),
            InitStep(
                name="Generate Schedule",
                description="Creating regular season schedule",
                handler=self._generate_schedule,
                required=True
            ),
            InitStep(
                name="Generate Draft Class",
                description="Creating prospects for upcoming draft",
                handler=self._generate_draft_class,
                required=True
            ),
            InitStep(
                name="Apply Cap Rollover",
                description="Rolling unused cap space to new season",
                handler=self._apply_cap_rollover,
                required=True
            ),
            # ============================================================
            # Future steps - uncomment/add as features are implemented:
            # ============================================================
            # InitStep(
            #     name="Archive Stats",
            #     description="Archiving previous season statistics",
            #     handler=self._archive_stats,
            #     required=False
            # ),
            # InitStep(
            #     name="Age Players",
            #     description="Aging all players by 1 year",
            #     handler=self._age_players,
            #     required=True
            # ),
            # InitStep(
            #     name="Process Contracts",
            #     description="Processing contract year decrements",
            #     handler=self._process_contracts,
            #     required=True
            # ),
        ]

    def run_all(self) -> List[StepResult]:
        """
        Run all steps in the pipeline.

        Returns:
            List of StepResult objects with status and message for each step.
            If a required step fails, remaining steps are not executed.
        """
        results = []

        for step in self._steps:
            result = self._run_step(step)
            results.append(result)

            # Stop on required step failure
            if result.status == StepStatus.FAILED and step.required:
                # Mark remaining steps as skipped
                remaining_idx = self._steps.index(step) + 1
                for remaining_step in self._steps[remaining_idx:]:
                    results.append(StepResult(
                        step_name=remaining_step.name,
                        status=StepStatus.SKIPPED,
                        message="Skipped due to previous failure"
                    ))
                break

        return results

    def _run_step(self, step: InitStep) -> StepResult:
        """
        Execute a single step.

        Args:
            step: The InitStep to execute

        Returns:
            StepResult with status and message
        """
        try:
            result = step.handler()
            success = result.get("success", False)
            message = result.get("message", "")

            return StepResult(
                step_name=step.name,
                status=StepStatus.COMPLETED if success else StepStatus.FAILED,
                message=message
            )
        except Exception as e:
            return StepResult(
                step_name=step.name,
                status=StepStatus.FAILED,
                message=str(e)
            )

    # ========================================================================
    # Step Handlers
    # ========================================================================

    def _reset_team_records(self) -> Dict[str, Any]:
        """
        Create fresh standings for all 32 teams for the new season.

        Uses UnifiedDatabaseAPI.standings_reset() to insert 0-0-0 records.
        """
        from database.unified_api import UnifiedDatabaseAPI

        try:
            api = UnifiedDatabaseAPI(self._db_path, self._dynasty_id)
            success = api.standings_reset(
                season=self._to_season,
                season_type='regular_season'
            )

            if success:
                return {
                    "success": True,
                    "message": f"Created standings for all 32 teams for season {self._to_season}"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to reset team records for season {self._to_season}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to reset team records: {e}"
            }

    def _generate_schedule(self) -> Dict[str, Any]:
        """
        Generate the regular season schedule for the new season.

        Uses ScheduleService to create game events in the events table.
        """
        from .schedule_service import ScheduleService

        try:
            service = ScheduleService(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._to_season
            )
            games_created = service.generate_schedule(clear_existing=True)

            return {
                "success": True,
                "message": f"Created {games_created} games for {self._to_season} season"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to generate schedule: {e}"
            }

    def _generate_draft_class(self) -> Dict[str, Any]:
        """
        Generate new draft class for the upcoming season.

        Creates 224 prospects and initializes draft order.
        """
        from .draft_service import DraftService

        try:
            draft_service = DraftService(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._to_season  # New season year
            )

            # This creates draft class if it doesn't exist (224 prospects)
            draft_service.ensure_draft_class_exists(draft_year=self._to_season)

            # Generate draft order based on standings
            draft_service.ensure_draft_order_exists()

            return {
                "success": True,
                "message": f"Draft class generated for {self._to_season}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to generate draft class: {e}"
            }

    def _apply_cap_rollover(self) -> Dict[str, Any]:
        """
        Apply cap rollover for all 32 teams when transitioning seasons.

        NFL Rule: Unlimited rollover - all unused cap carries over to next season.
        New season cap = Base cap + Rollover amount
        """
        from .cap_helper import CapHelper

        try:
            # Use from_season to calculate unused cap from completed season
            cap_helper = CapHelper(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._from_season
            )

            total_rollover = 0
            teams_processed = 0

            for team_id in range(1, 33):
                try:
                    rollover = cap_helper.apply_rollover_to_new_season(
                        team_id=team_id,
                        from_season=self._from_season,
                        to_season=self._to_season
                    )
                    total_rollover += rollover
                    teams_processed += 1
                except Exception as team_error:
                    # Log but continue with other teams
                    import logging
                    logging.warning(f"Failed to apply rollover for team {team_id}: {team_error}")

            avg_rollover = total_rollover // teams_processed if teams_processed > 0 else 0

            return {
                "success": teams_processed == 32,
                "message": f"Cap rollover applied for {teams_processed} teams. "
                          f"Total: ${total_rollover:,}, Avg: ${avg_rollover:,}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to apply cap rollover: {e}"
            }

    # ========================================================================
    # Future Step Handlers (uncomment and implement as needed)
    # ========================================================================

    # def _archive_stats(self) -> Dict[str, Any]:
    #     """Archive previous season statistics."""
    #     return {"success": True, "message": f"Stats archived for season {self._from_season}"}

    # def _age_players(self) -> Dict[str, Any]:
    #     """Age all players by 1 year."""
    #     return {"success": True, "message": "All players aged by 1 year"}

    # def _process_contracts(self) -> Dict[str, Any]:
    #     """Process contract year decrements and expirations."""
    #     return {"success": True, "message": "Contracts processed"}