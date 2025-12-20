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
                name="Archive Stats",
                description="Archiving previous season statistics",
                handler=self._archive_stats,
                required=False  # Non-critical - season can start without archival
            ),
            InitStep(
                name="Calculate Awards",
                description="Calculating NFL awards for completed season",
                handler=self._calculate_awards,
                required=False  # Non-critical - season can start without awards
            ),
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
            InitStep(
                name="Fill Roster Holes",
                description="GMs sign free agents to fill critical position gaps",
                handler=self._fill_roster_holes,
                required=True
            ),
            InitStep(
                name="Reinitialize Depth Charts",
                description="Reordering rosters by overall rating after offseason changes",
                handler=self._reinitialize_depth_charts,
                required=True
            ),
            # ============================================================
            # Future steps - uncomment/add as features are implemented:
            # ============================================================
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

        Uses ScheduleService to create game events in the events table,
        then assigns primetime slots via PrimetimeScheduler.
        """
        from .schedule_service import ScheduleService
        from .primetime_scheduler import PrimetimeScheduler
        from ..database.connection import GameCycleDatabase

        try:
            service = ScheduleService(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._to_season
            )
            games_created = service.generate_schedule(clear_existing=True)

            # Assign primetime slots (TNF, SNF, MNF) after schedule generation
            from ..database.game_slots_api import GameSlotsAPI

            db = GameCycleDatabase(self._db_path)
            try:
                game_slots_api = GameSlotsAPI(db)
                game_events = game_slots_api.get_games_for_primetime_assignment(
                    self._dynasty_id, self._to_season
                )

                primetime_scheduler = PrimetimeScheduler(db, self._dynasty_id)
                assignments = primetime_scheduler.assign_primetime_games(
                    season=self._to_season,
                    games=game_events,
                    super_bowl_winner_id=None
                )
                primetime_scheduler.save_assignments(self._to_season, assignments)
            finally:
                db.close()

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

    def _archive_stats(self) -> Dict[str, Any]:
        """
        Archive previous season statistics.

        This step:
        1. Deletes play-by-play grades for the completed season (biggest space saver)
        2. Archives game-level data older than 2 seasons to CSV and deletes from DB

        Space savings: ~48 MB per season (from play grades deletion alone)
        """
        from .stats_archival_service import StatsArchivalService

        try:
            archival_service = StatsArchivalService(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                retention_seasons=2  # Keep current + 1 prior season
            )

            summary = archival_service.archive_completed_season(
                completed_season=self._from_season,
                current_season=self._to_season
            )

            if summary.success:
                message_parts = [f"Stats archived for season {self._from_season}"]
                if summary.play_grades_deleted > 0:
                    message_parts.append(f"Play grades deleted: {summary.play_grades_deleted:,}")
                if summary.seasons_archived:
                    message_parts.append(f"Seasons archived to CSV: {summary.seasons_archived}")

                return {
                    "success": True,
                    "message": ". ".join(message_parts)
                }
            else:
                return {
                    "success": False,
                    "message": f"Archival had errors: {summary.errors}"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to archive stats: {e}"
            }

    def _calculate_awards(self) -> Dict[str, Any]:
        """
        Calculate NFL awards for the completed season.

        Includes:
        - 6 major awards (MVP, OPOY, DPOY, OROY, DROY, CPOY)
        - All-Pro teams (44 players: 22 First Team + 22 Second Team)
        - Pro Bowl rosters (AFC/NFC)
        - Statistical leaders (top 10 in 15 categories)

        This step is idempotent - if awards already exist, it skips calculation.
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Calculating awards for {self._from_season}...")

        try:
            from .awards_service import AwardsService

            service = AwardsService(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._from_season  # Completed season
            )

            # Idempotent: Skip if already calculated
            if service.awards_already_calculated():
                logger.info(f"  Awards already exist for {self._from_season}")
                return {
                    "success": True,
                    "skipped": True,
                    "message": f"Awards already calculated for {self._from_season}"
                }

            # 1. Major Awards (6)
            results = service.calculate_all_awards()
            winners = {
                k: v.winner.player_name if v.winner else None
                for k, v in results.items()
            }

            # Log winners
            for award_id, winner_name in winners.items():
                logger.info(f"  {award_id.upper()}: {winner_name or 'No winner'}")

            # 2. All-Pro Teams (44 players)
            all_pro = service.select_all_pro_teams()
            logger.info(f"  All-Pro: {all_pro.total_selections} selections")

            # 3. Pro Bowl Rosters
            pro_bowl = service.select_pro_bowl_rosters()
            logger.info(f"  Pro Bowl: {pro_bowl.total_selections} selections")

            # 4. Statistical Leaders
            stat_leaders = service.record_statistical_leaders()
            logger.info(f"  Stat Leaders: {stat_leaders.total_recorded} entries")

            logger.info(f"Awards complete for {self._from_season}")

            return {
                "success": True,
                "season": self._from_season,
                "awards_calculated": len(results),
                "all_pro_selections": all_pro.total_selections,
                "pro_bowl_selections": pro_bowl.total_selections,
                "stat_leaders_recorded": stat_leaders.total_recorded,
                "winners": winners,
                "message": f"Calculated {len(results)} awards, {all_pro.total_selections} All-Pro, "
                          f"{pro_bowl.total_selections} Pro Bowl for {self._from_season}"
            }

        except Exception as e:
            logger.error(f"Awards calculation failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Awards calculation failed for {self._from_season}: {e}"
            }

    def _fill_roster_holes(self) -> Dict[str, Any]:
        """
        Fill critical roster holes by signing free agents.

        When teams are missing essential positions (QB, RB, WR, etc.), the GM
        automatically signs the best available free agent to fill the gap.
        This ensures all teams can simulate games without position-related crashes.

        Uses the same position minimums and groupings as RosterCutsService.
        """
        import logging
        from database.player_roster_api import PlayerRosterAPI
        from .free_agency_service import FreeAgencyService
        from .roster_cuts_service import RosterCutsService

        logger = logging.getLogger(__name__)
        logger.info("Checking all teams for roster holes...")

        roster_api = PlayerRosterAPI(self._db_path)
        fa_service = FreeAgencyService(
            db_path=self._db_path,
            dynasty_id=self._dynasty_id,
            season=self._to_season
        )

        # Position minimums and groupings from RosterCutsService
        POSITION_MINIMUMS = RosterCutsService.POSITION_MINIMUMS
        OL_POSITIONS = RosterCutsService.OL_POSITIONS
        DL_POSITIONS = RosterCutsService.DL_POSITIONS
        DB_POSITIONS = RosterCutsService.DB_POSITIONS
        LB_POSITIONS = RosterCutsService.LB_POSITIONS
        RB_POSITIONS = RosterCutsService.RB_POSITIONS
        WR_POSITIONS = RosterCutsService.WR_POSITIONS
        TE_POSITIONS = RosterCutsService.TE_POSITIONS

        # Position group to free agent search position mapping
        POSITION_GROUP_TO_SEARCH = {
            'quarterback': ['quarterback'],
            'running_back': ['running_back', 'fullback'],
            'wide_receiver': ['wide_receiver'],
            'tight_end': ['tight_end'],
            'offensive_line': ['left_tackle', 'right_tackle', 'left_guard', 'right_guard', 'center'],
            'defensive_line': ['defensive_end', 'defensive_tackle'],
            'linebacker': ['linebacker', 'outside_linebacker', 'inside_linebacker'],
            'defensive_back': ['cornerback', 'safety', 'free_safety', 'strong_safety'],
            'kicker': ['kicker'],
            'punter': ['punter']
        }

        total_signings = 0
        teams_with_holes = 0

        for team_id in range(1, 33):
            try:
                # Get active roster for this team
                roster = roster_api.get_team_roster(
                    dynasty_id=self._dynasty_id,
                    team_id=team_id,
                    roster_status='active'
                )

                # Count players by position group
                position_counts = {group: 0 for group in POSITION_MINIMUMS}

                for player in roster:
                    positions = player.get("positions", [])
                    if isinstance(positions, str):
                        import json
                        positions = json.loads(positions)
                    pos = positions[0].lower() if positions else ""

                    if pos == 'quarterback':
                        position_counts['quarterback'] += 1
                    elif pos in RB_POSITIONS:
                        position_counts['running_back'] += 1
                    elif pos in WR_POSITIONS:
                        position_counts['wide_receiver'] += 1
                    elif pos in TE_POSITIONS:
                        position_counts['tight_end'] += 1
                    elif pos in OL_POSITIONS:
                        position_counts['offensive_line'] += 1
                    elif pos in DL_POSITIONS:
                        position_counts['defensive_line'] += 1
                    elif pos in LB_POSITIONS:
                        position_counts['linebacker'] += 1
                    elif pos in DB_POSITIONS:
                        position_counts['defensive_back'] += 1
                    elif pos == 'kicker':
                        position_counts['kicker'] += 1
                    elif pos == 'punter':
                        position_counts['punter'] += 1

                # Find and fill holes
                team_signings = 0
                for group, minimum in POSITION_MINIMUMS.items():
                    current = position_counts.get(group, 0)
                    needed = minimum - current

                    if needed > 0:
                        if team_signings == 0:
                            teams_with_holes += 1
                        logger.info(f"  Team {team_id}: Need {needed} {group}(s)")

                        # Get free agents at this position
                        search_positions = POSITION_GROUP_TO_SEARCH.get(group, [])
                        for _ in range(needed):
                            signed = False
                            for search_pos in search_positions:
                                free_agents = fa_service.get_free_agents(
                                    position=search_pos,
                                    limit=5
                                )

                                if free_agents:
                                    # Sign the best available
                                    best_fa = free_agents[0]
                                    result = fa_service.sign_free_agent(
                                        player_id=best_fa['player_id'],
                                        team_id=team_id,
                                        player_info=best_fa,
                                        skip_preference_check=True  # Mandatory fill
                                    )

                                    if result.get('success'):
                                        logger.info(
                                            f"    Signed {best_fa.get('name', 'Unknown')} "
                                            f"({search_pos}) to team {team_id}"
                                        )
                                        team_signings += 1
                                        total_signings += 1
                                        signed = True
                                        break

                            if not signed:
                                logger.warning(
                                    f"    No {group} available to sign for team {team_id}"
                                )

            except Exception as e:
                logger.error(f"Failed to fill roster holes for team {team_id}: {e}")

        logger.info(
            f"✅ Roster hole fill complete: {total_signings} signings "
            f"across {teams_with_holes} teams"
        )

        return {
            "success": True,
            "message": f"Filled {total_signings} roster holes across {teams_with_holes} teams"
        }

    def _reinitialize_depth_charts(self) -> Dict[str, Any]:
        """
        Reinitialize depth charts for all 32 teams based on overall ratings.

        After offseason roster changes (draft, FA, trades, cuts), new players
        have depth_chart_order=99 (default). This step reorders all position
        groups by overall rating to ensure valid depth charts for game simulation.

        Uses DepthChartAPI.auto_generate_depth_chart() for each team (DRY).
        """
        import logging
        from depth_chart.depth_chart_api import DepthChartAPI

        logger = logging.getLogger(__name__)
        logger.info("Reinitializing depth charts after offseason roster changes...")

        depth_chart_api = DepthChartAPI(self._db_path)
        teams_updated = 0
        errors = []

        for team_id in range(1, 33):
            try:
                success = depth_chart_api.auto_generate_depth_chart(
                    dynasty_id=self._dynasty_id,
                    team_id=team_id
                )
                if success:
                    teams_updated += 1
                else:
                    errors.append(f"Team {team_id}: auto_generate returned False")
            except Exception as e:
                logger.warning(f"Failed to regenerate depth chart for team {team_id}: {e}")
                errors.append(f"Team {team_id}: {str(e)}")

        logger.info(f"✅ Depth charts reinitialized for {teams_updated}/32 teams")

        if errors:
            logger.warning(f"Depth chart errors: {errors}")

        return {
            "success": teams_updated == 32,
            "message": f"Depth charts reinitialized for {teams_updated}/32 teams"
        }

    # ========================================================================
    # Future Step Handlers (uncomment and implement as needed)
    # ========================================================================

    # def _age_players(self) -> Dict[str, Any]:
    #     """Age all players by 1 year."""
    #     return {"success": True, "message": "All players aged by 1 year"}

    # def _process_contracts(self) -> Dict[str, Any]:
    #     """Process contract year decrements and expirations."""
    #     return {"success": True, "message": "Contracts processed"}