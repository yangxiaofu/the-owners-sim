"""
Playoffs to Offseason Handler

Handles the transition from PLAYOFFS phase to OFFSEASON phase.

This handler is responsible for:
1. Determining the Super Bowl champion
2. Generating comprehensive season summary (champion, final standings, awards)
3. Scheduling offseason events (draft, free agency, training camp, etc.)
4. Updating database to reflect offseason phase
5. Supporting rollback on failure

Architecture:
- Uses dependency injection for all external operations
- Maintains rollback state for transaction safety
- Provides detailed logging for debugging
- Stores season summary for later retrieval

Usage:
    handler = PlayoffsToOffseasonHandler(
        get_super_bowl_winner=lambda: playoff_controller.get_champion(),
        schedule_offseason_events=lambda year: event_scheduler.schedule_offseason(year),
        generate_season_summary=lambda: summarizer.generate_summary(),
        update_database_phase=lambda phase: db.update_phase(phase),
        dynasty_id="my_dynasty",
        season_year=2024,
        verbose_logging=True
    )

    transition = PhaseTransition(from_phase="PLAYOFFS", to_phase="OFFSEASON")
    result = handler.execute(transition)
    print(f"Champion: {result['champion_team_id']}")
"""

from typing import Any, Dict, Callable, Optional, List
import logging
from datetime import datetime

from ..models import PhaseTransition
from src.calendar.season_phase_tracker import SeasonPhase
from src.offseason.draft_order_service import DraftOrderService, TeamRecord
from src.database.draft_order_database_api import DraftOrderDatabaseAPI, DraftPick
from src.database.api import DatabaseAPI
from src.events.milestone_event import create_draft_order_milestone
from src.calendar.date_models import Date


class PlayoffsToOffseasonHandler:
    """
    Handles PLAYOFFS → OFFSEASON transition.

    This handler orchestrates the end of the playoff phase and the beginning
    of the offseason. It captures the season's conclusion (Super Bowl winner),
    generates a comprehensive season summary, and schedules all offseason events
    (draft, free agency, training camp, etc.).

    Responsibilities:
    1. Determine Super Bowl winner from playoff results
    2. Generate season summary (champion, final standings, playoff results, awards)
    3. Schedule offseason events (draft, free agency, training camp deadlines)
    4. Update database phase to OFFSEASON
    5. Support rollback if any step fails

    Attributes:
        _get_super_bowl_winner: Callable that returns Super Bowl champion team ID
        _schedule_offseason_events: Callable that schedules offseason events for given year
        _generate_season_summary: Callable that generates comprehensive season summary
        _update_database_phase: Callable that updates database phase
        _dynasty_id: Dynasty identifier for isolation
        _season_year: Current season year
        _verbose_logging: Enable detailed logging output
        _season_summary: Stored season summary (None until execute runs)
        _rollback_state: Stored state for rollback operations
        _logger: Logger instance for this handler
    """

    def __init__(
        self,
        get_super_bowl_winner: Callable[[], int],
        schedule_offseason_events: Callable[[int], None],
        generate_season_summary: Callable[[], Dict[str, Any]],
        update_database_phase: Callable[[str, int], None],  # FIX: Add season_year parameter
        dynasty_id: str,
        season_year: int,
        verbose_logging: bool = False,
        # New dependencies for draft order calculation
        get_regular_season_standings: Optional[Callable[[], List[Dict[str, Any]]]] = None,
        get_playoff_bracket: Optional[Callable[[], Dict[str, Any]]] = None,
        schedule_event: Optional[Callable[[Any], None]] = None,
        database_path: Optional[str] = None
    ):
        """
        Initialize PlayoffsToOffseasonHandler with injectable dependencies.

        Args:
            get_super_bowl_winner: Callable that returns Super Bowl champion team ID
                Example: lambda: playoff_controller.get_super_bowl_winner()
            schedule_offseason_events: Callable that schedules offseason events for given year
                Example: lambda year: event_scheduler.schedule_offseason_events(year)
            generate_season_summary: Callable that generates comprehensive season summary
                Example: lambda: season_summarizer.generate_summary()
                Expected return format:
                {
                    "champion_team_id": 7,
                    "runner_up_team_id": 15,
                    "final_standings": [...],
                    "playoff_results": {...},
                    "awards": {...},
                    "season_stats": {...}
                }
            update_database_phase: Callable that updates database phase
                Example: lambda phase: dynasty_state_api.update_phase(phase)
            dynasty_id: Dynasty identifier for isolation
            season_year: Current season year (e.g., 2024)
            verbose_logging: Enable detailed logging output (default: False)
            get_regular_season_standings: Optional callable that returns regular season standings
                Example: lambda: db.standings_get(season=season_year, season_type="regular_season")
            get_playoff_bracket: Optional callable that returns playoff bracket with results
                Example: lambda: playoff_controller.get_current_bracket()
            schedule_event: Optional callable that schedules an event to the calendar
                Example: lambda event: event_db.schedule_event(event)
            database_path: Optional path to database for draft order persistence

        Raises:
            ValueError: If any required callable is None
            ValueError: If dynasty_id is empty
            ValueError: If season_year is invalid (< 1920)
        """
        if not get_super_bowl_winner:
            raise ValueError("get_super_bowl_winner callable is required")
        if not schedule_offseason_events:
            raise ValueError("schedule_offseason_events callable is required")
        if not generate_season_summary:
            raise ValueError("generate_season_summary callable is required")
        if not update_database_phase:
            raise ValueError("update_database_phase callable is required")
        if not dynasty_id:
            raise ValueError("dynasty_id cannot be empty")
        if season_year < 1920:
            raise ValueError(f"Invalid season_year: {season_year} (must be >= 1920)")

        self._get_super_bowl_winner = get_super_bowl_winner
        self._schedule_offseason_events = schedule_offseason_events
        self._generate_season_summary = generate_season_summary
        self._update_database_phase = update_database_phase
        self._dynasty_id = dynasty_id
        self._season_year = season_year
        self._verbose_logging = verbose_logging

        # Draft order calculation dependencies
        self._get_regular_season_standings = get_regular_season_standings
        self._get_playoff_bracket = get_playoff_bracket
        self._schedule_event = schedule_event
        self._database_path = database_path or "data/database/nfl_simulation.db"

        # Initialize DatabaseAPI for SOS calculations
        self._db_api = DatabaseAPI(self._database_path)

        # State storage
        self._season_summary: Optional[Dict[str, Any]] = None
        self._rollback_state: Dict[str, Any] = {}

        # Logger setup
        self._logger = logging.getLogger(__name__)
        if verbose_logging:
            self._logger.setLevel(logging.DEBUG)

    def execute(
        self,
        transition: PhaseTransition,
        season_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute PLAYOFFS → OFFSEASON transition.

        **Phase 4: Dynamic Handlers** - Now accepts season_year at execution time
        for maximum flexibility and testability. If not provided, uses the year
        specified at construction.

        This method orchestrates the complete transition from playoffs to offseason:
        1. Saves rollback state (current phase)
        2. Determines Super Bowl winner
        3. Generates comprehensive season summary
        4. Schedules offseason events (draft, free agency, training camp)
        5. Updates database phase to OFFSEASON

        The method is transactional - if any step fails, rollback can restore
        the previous state.

        Args:
            transition: PhaseTransition object containing from_phase and to_phase
            season_year: Optional season year to use for this transition.
                If not provided, uses the year from construction.
                This allows the same handler instance to be reused
                for multiple years (Phase 4: Dynamic Handlers).

        Returns:
            Dict containing transition results:
            {
                "success": True,
                "champion_team_id": 7,
                "season_summary": {...},
                "offseason_events_scheduled": True,
                "database_updated": True,
                "timestamp": "2024-02-11T20:30:00"
            }

        Raises:
            ValueError: If transition phases are invalid
            RuntimeError: If any transition step fails

        Example:
            >>> transition = PhaseTransition(from_phase="PLAYOFFS", to_phase="OFFSEASON")
            >>> result = handler.execute(transition)
            >>> print(f"Champion: Team {result['champion_team_id']}")
            Champion: Team 7
        """
        # Phase 4: Use execution-time year if provided, otherwise use constructor year
        effective_year = season_year if season_year is not None else self._season_year

        self._log_info(
            f"Starting PLAYOFFS → OFFSEASON transition for dynasty {self._dynasty_id}, "
            f"season {effective_year}"
        )

        # Validate transition
        if transition.from_phase != SeasonPhase.PLAYOFFS:
            raise ValueError(f"Invalid from_phase: {transition.from_phase.value} (expected PLAYOFFS)")
        if transition.to_phase != SeasonPhase.OFFSEASON:
            raise ValueError(f"Invalid to_phase: {transition.to_phase.value} (expected OFFSEASON)")

        try:
            # Step 1: Save rollback state
            self._save_rollback_state(transition)
            self._log_debug("Rollback state saved")

            # Step 2: Determine Super Bowl winner
            champion_team_id = self._get_super_bowl_winner()
            self._log_info(f"Super Bowl champion: Team {champion_team_id}")

            if champion_team_id is None:
                raise RuntimeError("Failed to determine Super Bowl winner")

            # Step 3: Generate season summary
            self._log_debug("Generating season summary...")
            self._season_summary = self._generate_season_summary()

            if not self._season_summary:
                raise RuntimeError("Failed to generate season summary")

            self._log_info(
                f"Season summary generated: Champion={self._season_summary.get('champion_team_id')}, "
                f"Runner-up={self._season_summary.get('runner_up_team_id')}"
            )

            # Step 4: Calculate and save draft order (if dependencies available)
            draft_order_calculated = False
            if self._can_calculate_draft_order():
                try:
                    self._log_debug("Calculating draft order...")
                    draft_order_calculated = self._calculate_and_save_draft_order(effective_year)
                    if draft_order_calculated:
                        self._log_info("Draft order calculated and saved successfully")
                    else:
                        # FAIL-LOUD: Raise exception instead of continuing silently
                        error_msg = (
                            "Draft order calculation failed. Cannot proceed to offseason without valid draft order. "
                            "Check logs above for validation errors (expected 224 base picks)."
                        )
                        self._log_error(error_msg)
                        raise RuntimeError(error_msg)
                except RuntimeError:
                    # Re-raise RuntimeError from validation failure
                    raise
                except Exception as e:
                    # FAIL-LOUD: Raise exception for unexpected errors
                    error_msg = f"Unexpected error during draft order calculation: {e}"
                    self._log_error(error_msg)
                    raise RuntimeError(error_msg) from e

            # Step 5: Schedule offseason events
            self._log_debug(f"Scheduling offseason events for {effective_year}...")
            self._schedule_offseason_events(effective_year)
            self._log_info("Offseason events scheduled successfully")

            # Step 6: Update database phase
            self._log_debug("Updating database phase to OFFSEASON...")
            self._update_database_phase("OFFSEASON", effective_year)  # FIX: Pass season_year
            self._log_info("Database phase updated to OFFSEASON")

            # Build result
            result = {
                "success": True,
                "champion_team_id": champion_team_id,
                "season_summary": self._season_summary,
                "draft_order_calculated": draft_order_calculated,
                "offseason_events_scheduled": True,
                "database_updated": True,
                "timestamp": datetime.now().isoformat(),
                "dynasty_id": self._dynasty_id,
                "season_year": effective_year
            }

            self._log_info("PLAYOFFS → OFFSEASON transition completed successfully")
            return result

        except Exception as e:
            self._log_error(f"Transition failed: {e}")
            raise RuntimeError(f"Failed to execute PLAYOFFS → OFFSEASON transition: {e}") from e

    def rollback(self, transition: PhaseTransition) -> None:
        """
        Rollback PLAYOFFS → OFFSEASON transition.

        This method attempts to restore the system to its pre-transition state
        if the transition fails. It uses the saved rollback state to restore
        the database phase.

        Rollback operations:
        1. Restore database phase to PLAYOFFS
        2. Clear season summary
        3. Clear rollback state

        Note: This does NOT unschedule offseason events (they remain scheduled
        but inactive until the phase is transitioned again).

        Args:
            transition: PhaseTransition object containing from_phase and to_phase

        Raises:
            RuntimeError: If rollback fails

        Example:
            >>> try:
            ...     result = handler.execute(transition)
            ... except RuntimeError:
            ...     handler.rollback(transition)
            ...     print("Transition rolled back")
        """
        self._log_info(f"Rolling back PLAYOFFS → OFFSEASON transition for dynasty {self._dynasty_id}")

        try:
            # Restore database phase
            if "previous_phase" in self._rollback_state:
                previous_phase = self._rollback_state["previous_phase"]
                self._log_debug(f"Restoring database phase to {previous_phase}...")
                self._update_database_phase(previous_phase)
                self._log_info(f"Database phase restored to {previous_phase}")

            # Clear season summary
            self._season_summary = None
            self._log_debug("Season summary cleared")

            # Clear rollback state
            self._rollback_state.clear()
            self._log_debug("Rollback state cleared")

            self._log_info("Rollback completed successfully")

        except Exception as e:
            self._log_error(f"Rollback failed: {e}")
            raise RuntimeError(f"Failed to rollback PLAYOFFS → OFFSEASON transition: {e}") from e

    def get_season_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get the generated season summary.

        Returns the season summary that was generated during the execute() call.
        Returns None if execute() has not been called yet or if it failed.

        Returns:
            Dict containing season summary with keys:
            - champion_team_id: Super Bowl winner
            - runner_up_team_id: Super Bowl runner-up
            - final_standings: Final regular season standings
            - playoff_results: Complete playoff bracket results
            - awards: Season awards (MVP, OPOY, DPOY, etc.)
            - season_stats: League-wide statistics

            Returns None if no summary is available.

        Example:
            >>> result = handler.execute(transition)
            >>> summary = handler.get_season_summary()
            >>> if summary:
            ...     print(f"Champion: Team {summary['champion_team_id']}")
        """
        return self._season_summary

    def _save_rollback_state(self, transition: PhaseTransition) -> None:
        """
        Save rollback state before making changes.

        Stores the current phase so it can be restored if the transition fails.

        Args:
            transition: PhaseTransition object containing current phase info
        """
        self._rollback_state = {
            "previous_phase": transition.from_phase,
            "timestamp": datetime.now().isoformat()
        }
        self._log_debug(f"Rollback state: {self._rollback_state}")

    def _can_calculate_draft_order(self) -> bool:
        """
        Check if all dependencies are available for draft order calculation.

        Returns:
            True if draft order can be calculated, False otherwise
        """
        return all([
            self._get_regular_season_standings is not None,
            self._get_playoff_bracket is not None,
            self._schedule_event is not None
        ])

    def _calculate_and_save_draft_order(self, season_year: int) -> bool:
        """
        Calculate draft order from regular season standings and playoff results,
        save to database, and schedule the draft order milestone event.

        Args:
            season_year: Current season year (draft will be for season_year + 1)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Step 1: Get regular season standings
            self._log_debug("Fetching regular season standings...")
            standings_data = self._get_regular_season_standings()

            if not standings_data or len(standings_data) != 32:
                self._log_error(f"Invalid standings data: expected 32 teams, got {len(standings_data) if standings_data else 0}")
                return False

            # Convert to TeamRecord objects
            standings = []
            for team_data in standings_data:
                standings.append(TeamRecord(
                    team_id=team_data['team_id'],
                    wins=team_data['wins'],
                    losses=team_data['losses'],
                    ties=team_data['ties'],
                    win_percentage=team_data.get('win_percentage',
                                                  team_data['wins'] / (team_data['wins'] + team_data['losses'] + team_data['ties'])
                                                  if (team_data['wins'] + team_data['losses'] + team_data['ties']) > 0 else 0.0)
                ))

            # Step 2: Get playoff bracket and extract losers
            self._log_debug("Fetching playoff bracket...")
            bracket = self._get_playoff_bracket()

            playoff_results = self._extract_playoff_results(bracket)
            if not playoff_results:
                self._log_error("Failed to extract playoff results from bracket")
                return False

            # Step 3: Calculate draft order
            self._log_debug("Calculating draft order...")
            draft_year = season_year + 1
            draft_service = DraftOrderService(dynasty_id=self._dynasty_id, season_year=draft_year)

            # Calculate real strength of schedule for all teams
            self._log_info("Calculating strength of schedule for draft order tiebreakers...")

            for team in standings:
                try:
                    # Query database for team's regular season opponents
                    opponents = self._db_api.get_team_opponents(
                        dynasty_id=self._dynasty_id,
                        team_id=team.team_id,
                        season=season_year,
                        season_type="regular_season"
                    )

                    if opponents:
                        # Calculate real SOS using opponent records
                        sos = draft_service.calculate_strength_of_schedule(
                            team_id=team.team_id,
                            all_standings=standings,
                            schedule=opponents
                        )
                        self._log_debug(f"Team {team.team_id} SOS: {sos:.3f} (based on {len(opponents)} opponents)")
                    else:
                        # Fall back to 0.500 if no opponents found
                        self._log_warning(f"No opponents found for team {team.team_id}, using default SOS 0.500")
                        draft_service._sos_cache[team.team_id] = 0.500

                except Exception as e:
                    # Graceful failure: log error and use default
                    self._log_error(f"Error calculating SOS for team {team.team_id}: {e}")
                    draft_service._sos_cache[team.team_id] = 0.500

            self._log_info("Strength of schedule calculations complete")

            draft_picks = draft_service.calculate_draft_order(standings, playoff_results)

            if not draft_picks or len(draft_picks) != 224:
                self._log_error(f"Invalid draft order: expected 224 base picks (compensatory picks not yet implemented), got {len(draft_picks) if draft_picks else 0}")
                return False

            # Step 4: Save to database
            self._log_debug(f"Saving {len(draft_picks)} draft picks to database...")
            draft_db_api = DraftOrderDatabaseAPI(self._database_path)

            # Convert to DraftPick objects
            db_picks = []
            for pick in draft_picks:
                db_picks.append(DraftPick(
                    pick_id=None,  # Auto-generated
                    dynasty_id=self._dynasty_id,
                    season=draft_year,
                    round_number=pick.round_number,
                    pick_in_round=pick.pick_in_round,
                    overall_pick=pick.overall_pick,
                    original_team_id=pick.original_team_id,
                    current_team_id=pick.team_id,
                    player_id=None,
                    draft_class_id=None,
                    is_executed=False,
                    is_compensatory=False,
                    comp_round_end=False,
                    acquired_via_trade=False,
                    trade_date=None,
                    original_trade_id=None
                ))

            success = draft_db_api.save_draft_order(db_picks)
            if not success:
                self._log_error("Failed to save draft order to database")
                return False

            # Step 5: Create and schedule draft order milestone event
            self._log_debug("Creating draft order milestone event...")

            # Calculate milestone date (2 weeks after Super Bowl, around mid-February)
            milestone_date = Date(draft_year, 2, 15)

            milestone_event = create_draft_order_milestone(
                season_year=draft_year,
                event_date=milestone_date,
                dynasty_id=self._dynasty_id,
                total_picks=224  # Base picks only (compensatory picks not yet implemented)
            )

            if self._schedule_event:
                self._schedule_event(milestone_event)
                self._log_info(f"Draft order milestone scheduled for {milestone_date}")

            return True

        except Exception as e:
            self._log_error(f"Error calculating draft order: {e}", exc_info=True)
            return False

    def _extract_playoff_results(self, bracket: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract playoff losers from bracket for draft order calculation.

        Args:
            bracket: Playoff bracket dictionary with round brackets

        Returns:
            Dictionary with playoff results in format expected by DraftOrderService:
            {
                'wild_card_losers': List[int],  # 6 teams
                'divisional_losers': List[int],  # 4 teams
                'conference_losers': List[int],  # 2 teams
                'super_bowl_loser': int,
                'super_bowl_winner': int
            }
            Returns None if extraction fails
        """
        try:
            results = {
                'wild_card_losers': [],
                'divisional_losers': [],
                'conference_losers': [],
                'super_bowl_loser': None,
                'super_bowl_winner': None
            }

            # Helper function to get losers from game results
            def get_losers_from_games(games_list):
                losers = []
                for game in games_list:
                    # Game dict has away_team_id, home_team_id, away_score, home_score
                    if 'away_score' in game and 'home_score' in game:
                        if game['away_score'] < game['home_score']:
                            losers.append(game['away_team_id'])
                        elif game['home_score'] < game['away_score']:
                            losers.append(game['home_team_id'])
                return losers

            # Query database for actual game results with scores
            # Wild Card round - get game results from database
            wc_games = self._db_api.get_playoff_games_by_round(
                dynasty_id=self._dynasty_id,
                season=self._season_year,
                round_name='wild_card'
            )
            results['wild_card_losers'] = get_losers_from_games(wc_games)

            # Divisional round
            div_games = self._db_api.get_playoff_games_by_round(
                dynasty_id=self._dynasty_id,
                season=self._season_year,
                round_name='divisional'
            )
            results['divisional_losers'] = get_losers_from_games(div_games)

            # Conference Championship round
            conf_games = self._db_api.get_playoff_games_by_round(
                dynasty_id=self._dynasty_id,
                season=self._season_year,
                round_name='conference'
            )
            results['conference_losers'] = get_losers_from_games(conf_games)

            # Super Bowl
            sb_games = self._db_api.get_playoff_games_by_round(
                dynasty_id=self._dynasty_id,
                season=self._season_year,
                round_name='super_bowl'
            )
            if sb_games and len(sb_games) > 0:
                sb_game = sb_games[0]
                if sb_game['away_score'] < sb_game['home_score']:
                    results['super_bowl_loser'] = sb_game['away_team_id']
                    results['super_bowl_winner'] = sb_game['home_team_id']
                elif sb_game['home_score'] < sb_game['away_score']:
                    results['super_bowl_loser'] = sb_game['home_team_id']
                    results['super_bowl_winner'] = sb_game['away_team_id']

            # Validate counts
            if len(results['wild_card_losers']) != 6:
                self._log_error(f"Expected 6 wild card losers, got {len(results['wild_card_losers'])}")
                return None
            if len(results['divisional_losers']) != 4:
                self._log_error(f"Expected 4 divisional losers, got {len(results['divisional_losers'])}")
                return None
            if len(results['conference_losers']) != 2:
                self._log_error(f"Expected 2 conference losers, got {len(results['conference_losers'])}")
                return None
            if results['super_bowl_loser'] is None or results['super_bowl_winner'] is None:
                self._log_error("Super Bowl loser or winner not found in bracket")
                return None

            return results

        except Exception as e:
            self._log_error(f"Error extracting playoff results: {e}", exc_info=True)
            return None

    def _log_debug(self, message: str) -> None:
        """Log debug message if verbose logging is enabled."""
        if self._verbose_logging:
            self._logger.debug(f"[PlayoffsToOffseasonHandler] {message}")

    def _log_info(self, message: str) -> None:
        """Log info message."""
        self._logger.info(f"[PlayoffsToOffseasonHandler] {message}")

    def _log_warning(self, message: str) -> None:
        """Log warning message."""
        self._logger.warning(f"[PlayoffsToOffseasonHandler] {message}")

    def _log_error(self, message: str, exc_info: bool = False) -> None:
        """Log error message."""
        self._logger.error(f"[PlayoffsToOffseasonHandler] {message}", exc_info=exc_info)
