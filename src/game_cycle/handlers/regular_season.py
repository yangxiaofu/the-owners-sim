"""
Regular Season Handler - Executes regular season weeks.

Dynasty-First Architecture:
- All dependencies come via context dict
- Uses UnifiedDatabaseAPI for all database operations
- No constructor injection of database/API objects

Performance Optimization:
- Game simulations run in parallel using ThreadPoolExecutor
- Database writes remain sequential (SQLite single-writer limitation)
- Achieves 4-6x speedup for weekly game execution
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging
import random

from ..stage_definitions import Stage, StageType
from ..game_result_generator import generate_instant_result
from ..services.game_simulator_service import GameSimulatorService, SimulationMode

logger = logging.getLogger(__name__)


@dataclass
class GameSimContext:
    """
    Context for parallel game simulation.

    Contains all data needed to simulate a single game without database access.
    Used to pass game info to worker threads and collect results.
    """
    game: Dict[str, Any]      # Original game event from database
    game_id_for_db: str       # Unique game ID for persistence
    home_team_id: int
    away_team_id: int
    event_id: Optional[str]   # Event ID for updating events table
    season: int
    week: int


class RegularSeasonHandler:
    """
    Handler for regular season stages (Week 1-18).

    Executes all games scheduled for the week and updates standings.

    Dynasty-First: All operations use dynasty_id from context.
    Dependencies come via context dict, not constructor injection.
    """

    def __init__(self):
        """Initialize the handler (no dependencies - all via context)."""
        pass

    def _get_db_path(self, context: Dict[str, Any]) -> Optional[str]:
        """Extract database path from context.

        Checks db_path first, falls back to unified_api.database_path.

        Args:
            context: Execution context

        Returns:
            Database path string or None if unavailable
        """
        if db_path := context.get("db_path"):
            return db_path
        if unified_api := context.get("unified_api"):
            return unified_api.database_path
        return None

    def _build_box_score_dict(
        self,
        team_stats: Dict[str, Any],
        player_stats: List[Dict[str, Any]],
        team_id: int
    ) -> Dict[str, Any]:
        """Build box score dict from team stats with fallback to player stats.

        Team stats (from simulation) include first_downs, 3rd/4th down, TOP,
        penalties - data that cannot be derived from player stats alone.

        Player stats aggregation provides basic yards/turnovers as fallback.

        Args:
            team_stats: Dict from GameSimulationResult.home_team_stats or away_team_stats
            player_stats: List of player stat dicts from simulation
            team_id: Team ID to aggregate for

        Returns:
            Dict ready for box_scores_insert()
        """
        from ..database.box_scores_api import BoxScoresAPI

        # Start with player stats aggregation (provides yards, TDs, turnovers)
        box = BoxScoresAPI.aggregate_from_player_stats(player_stats, team_id)

        # Override with team stats if available (maps field names correctly)
        if team_stats:
            box['first_downs'] = team_stats.get('first_downs', 0)
            box['third_down_att'] = team_stats.get('third_down_attempts', 0)
            box['third_down_conv'] = team_stats.get('third_down_conversions', 0)
            box['fourth_down_att'] = team_stats.get('fourth_down_attempts', 0)
            box['fourth_down_conv'] = team_stats.get('fourth_down_conversions', 0)
            box['time_of_possession'] = int(team_stats.get('time_of_possession_seconds', 0))
            box['penalties'] = team_stats.get('penalties', 0)
            box['penalty_yards'] = team_stats.get('penalty_yards', 0)

        return box

    def _simulate_single_game(
        self,
        ctx: GameSimContext,
        game_simulator: GameSimulatorService,
        simulation_mode: SimulationMode
    ) -> Tuple[GameSimContext, Any]:
        """
        Simulate a single game (pure computation, no DB writes).

        This method is designed to run in a thread pool. It performs only
        the simulation logic without any database access.

        Args:
            ctx: Game context with all required info
            game_simulator: Shared simulator service instance
            simulation_mode: INSTANT or FULL simulation mode

        Returns:
            Tuple of (context, simulation_result) for later persistence
        """
        sim_result = game_simulator.simulate_game(
            game_id=ctx.game_id_for_db,
            home_team_id=ctx.home_team_id,
            away_team_id=ctx.away_team_id,
            mode=simulation_mode,
            season=ctx.season,
            week=ctx.week,
            is_playoff=False
        )
        return (ctx, sim_result)

    def _persist_game_result(
        self,
        ctx: GameSimContext,
        sim_result: Any,
        unified_api: Any,
        simulation_mode: SimulationMode,
        dynasty_id: str,
        db_path: str
    ) -> Dict[str, Any]:
        """
        Persist a single game result to database.

        This method handles all sequential database writes for a game:
        - Game result insertion
        - Player stats persistence
        - Box score persistence
        - Event update
        - Injury recording
        - Standings updates
        - Headline generation

        Args:
            ctx: Game context
            sim_result: Simulation result to persist
            unified_api: Database API instance
            simulation_mode: For logging purposes
            dynasty_id: Dynasty identifier
            db_path: Database path for services

        Returns:
            Dictionary with game result info for return to caller
        """
        home_score = sim_result.home_score
        away_score = sim_result.away_score

        # Record result using UnifiedDatabaseAPI (games table for results)
        # MUST insert game FIRST because player_game_stats has FK to games
        unified_api.games_insert_result({
            "game_id": ctx.game_id_for_db,
            "season": ctx.season,
            "week": ctx.week,
            "season_type": "regular_season",
            "game_type": "regular",
            "game_date": int(time.time() * 1000),
            "home_team_id": ctx.home_team_id,
            "away_team_id": ctx.away_team_id,
            "home_score": home_score,
            "away_score": away_score,
            "total_plays": sim_result.total_plays,
            "game_duration_minutes": sim_result.game_duration_minutes,
            "overtime_periods": sim_result.overtime_periods,
        })

        # Persist player stats from simulation
        try:
            if sim_result.player_stats:
                stats_count = unified_api.stats_insert_game_stats(
                    game_id=ctx.game_id_for_db,
                    season=ctx.season,
                    week=ctx.week,
                    season_type="regular_season",
                    player_stats=sim_result.player_stats
                )
                mode_label = "full sim" if simulation_mode == SimulationMode.FULL else "instant"
                logger.debug("Inserted %d player stats (%s) for game %s", stats_count, mode_label, ctx.game_id_for_db)
        except Exception as e:
            logger.warning("Failed to persist stats for game %s: %s", ctx.game_id_for_db, e)

        # Persist play-by-play data (if drives available from FULL simulation)
        if hasattr(sim_result, 'drives') and sim_result.drives:
            try:
                from ..database.play_by_play_api import PlayByPlayAPI
                pbp_api = PlayByPlayAPI(db_path)
                drive_count = pbp_api.insert_drives_batch(dynasty_id, ctx.game_id_for_db, sim_result.drives)
                play_count = pbp_api.insert_plays_batch(
                    dynasty_id, ctx.game_id_for_db, sim_result.drives,
                    home_team_id=ctx.home_team_id, away_team_id=ctx.away_team_id
                )
                logger.debug("Persisted %d drives, %d plays for game %s", drive_count, play_count, ctx.game_id_for_db)
            except Exception as e:
                logger.warning("Failed to persist play-by-play for game %s: %s", ctx.game_id_for_db, e)

        # Persist box scores
        try:
            home_box = self._build_box_score_dict(
                sim_result.home_team_stats,
                sim_result.player_stats,
                ctx.home_team_id
            )
            away_box = self._build_box_score_dict(
                sim_result.away_team_stats,
                sim_result.player_stats,
                ctx.away_team_id
            )
            unified_api.box_scores_insert(
                game_id=ctx.game_id_for_db,
                home_team_id=ctx.home_team_id,
                away_team_id=ctx.away_team_id,
                home_box=home_box,
                away_box=away_box
            )
            logger.debug("Inserted box scores for game %s", ctx.game_id_for_db)
        except Exception as e:
            logger.warning("Failed to persist box scores for game %s: %s", ctx.game_id_for_db, e)

        # Update event in events table
        if ctx.event_id:
            unified_api.events_update_game_result(ctx.event_id, home_score, away_score)

        # Record injuries
        game_injuries = []
        if sim_result.injuries:
            from ..services.injury_service import InjuryService
            injury_service = InjuryService(db_path, dynasty_id, ctx.season)
            for injury in sim_result.injuries:
                injury_service.record_injury(injury)
                game_injuries.append({
                    'player_id': injury.player_id,
                    'player_name': injury.player_name,
                    'team_id': injury.team_id,
                    'injury_type': injury.injury_type.value,
                    'weeks_out': injury.weeks_out,
                    'severity': injury.severity.value
                })
            if game_injuries:
                logger.debug("Recorded %d injuries for game %s", len(game_injuries), ctx.game_id_for_db)

        # Update standings
        self._update_standings_for_game(
            dynasty_id, ctx.season,
            ctx.home_team_id, ctx.away_team_id,
            home_score, away_score,
            overtime_periods=sim_result.overtime_periods
        )

        # Generate headline
        self._generate_game_headline(
            db_path=db_path,
            dynasty_id=dynasty_id,
            season=ctx.season,
            week=ctx.week,
            game_id=ctx.game_id_for_db,
            home_team_id=ctx.home_team_id,
            away_team_id=ctx.away_team_id,
            home_score=home_score,
            away_score=away_score,
            sim_result=sim_result
        )

        # Build result for return
        game_result_to_include = sim_result if simulation_mode == SimulationMode.FULL else None

        return {
            "game_id": ctx.game.get("game_id"),
            "home_team_id": ctx.home_team_id,
            "away_team_id": ctx.away_team_id,
            "home_score": home_score,
            "away_score": away_score,
            "injuries": game_injuries,
            "game_result": game_result_to_include,
        }

    def execute(self, stage: Stage, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute all games for the week.

        Args:
            stage: The current week stage
            context: Execution context with:
                - dynasty_id: Dynasty identifier
                - season: Season year
                - unified_api: UnifiedDatabaseAPI instance
                - db_path: Database path (for generation services)

        Returns:
            Dictionary with games_played, events_processed, etc.
        """
        unified_api = context["unified_api"]
        season = context["season"]
        dynasty_id = context.get("dynasty_id", "unknown")
        week_number = self._get_week_number(stage.stage_type)

        # Initialize services
        db_path = self._get_db_path(context)

        # Initialize unified game simulator
        game_simulator = GameSimulatorService(db_path, dynasty_id)

        # Get simulation mode from context (default: INSTANT for backwards compatibility)
        mode_str = context.get("simulation_mode", "instant")
        simulation_mode = SimulationMode.FULL if mode_str == "full" else SimulationMode.INSTANT

        # WEEK 1 HOOK: Generate draft class and free agents at season start
        if week_number == 1:
            self._trigger_season_start_generation(context)

        # Generate preview headlines for notable upcoming games (rivalries, divisional, etc.)
        if db_path:
            self._generate_preview_headlines(
                db_path=db_path,
                dynasty_id=dynasty_id,
                season=season,
                week=week_number
            )

        # Process weekly injuries: recoveries and practice injuries
        weekly_injury_results = self._process_weekly_injuries(context, week_number)

        logger.debug("execute() called: dynasty_id=%s, season=%s, week=%s, db_path=%s",
                     dynasty_id, season, week_number, unified_api.database_path)

        games_played = []
        events_processed = []

        # Get all games for this week from EVENTS table (schedule is stored there)
        # The games table is for storing RESULTS after simulation
        games = unified_api.events_get_games_by_week(season, week_number)

        logger.debug("events_get_games_by_week returned %d games", len(games))

        if not games:
            # No games found - handle gracefully
            # Week 18: Schedule generator creates 17 weeks, so Week 18 has 0 games
            # This is expected - advance to playoffs
            if week_number == 18:
                logger.debug("Week 18 has no games (17-week schedule) - advancing to playoffs")
                events_processed.append(f"Week {week_number}: Regular season complete - advancing to playoffs")
            else:
                logger.debug("No games found for week %d - returning early", week_number)
                events_processed.append(f"Week {week_number}: No games in database")
            return {
                "games_played": games_played,
                "events_processed": events_processed,
                "week": week_number,
            }

        # ============================================================
        # PHASE 1: Collect games to simulate
        # ============================================================
        games_to_simulate: List[GameSimContext] = []
        for game in games:
            # Skip already played games (have scores)
            if game.get("home_score") is not None:
                logger.debug("Skipping already played game: %s", game.get('game_id'))
                continue

            home_team_id = game.get("home_team_id")
            away_team_id = game.get("away_team_id")
            event_id = game.get("event_id")
            game_id = game.get("game_id")

            # Use consistent game_id for both game result and stats
            game_id_for_db = game_id or f"gc_{season}_{week_number}_{home_team_id}_{away_team_id}"

            games_to_simulate.append(GameSimContext(
                game=game,
                game_id_for_db=game_id_for_db,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                event_id=event_id,
                season=season,
                week=week_number
            ))

        if not games_to_simulate:
            logger.debug("No games to simulate for week %d", week_number)
            return {
                "games_played": games_played,
                "events_processed": [f"Week {week_number}: No unplayed games"],
                "week": week_number,
            }

        # ============================================================
        # PHASE 2: Parallel simulation (CPU-bound computation)
        # ============================================================
        # ThreadPoolExecutor is used because:
        # - Game simulation reads JSON files (I/O bound)
        # - Avoids pickle overhead of ProcessPoolExecutor
        # - Shared game_simulator instance across threads
        # - 4 workers = good balance for 16 games
        sim_start = time.time()
        sim_results: List[Tuple[GameSimContext, Any]] = []

        # Use parallel execution for multiple games, sequential for single game
        if len(games_to_simulate) > 1:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(
                        self._simulate_single_game, ctx, game_simulator, simulation_mode
                    )
                    for ctx in games_to_simulate
                ]
                # Collect results as they complete
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        sim_results.append(result)
                    except Exception as e:
                        logger.error("Game simulation failed: %s", e)
        else:
            # Single game - run directly without thread overhead
            for ctx in games_to_simulate:
                result = self._simulate_single_game(ctx, game_simulator, simulation_mode)
                sim_results.append(result)

        sim_elapsed = time.time() - sim_start
        logger.info("Simulated %d games in %.2f seconds (parallel)",
                   len(sim_results), sim_elapsed)

        # ============================================================
        # PHASE 3: Sequential database writes (SQLite single-writer)
        # ============================================================
        # Database writes MUST be sequential due to:
        # - SQLite allows only ONE writer at a time
        # - Foreign key constraints (games → player_game_stats → box_scores)
        # - Standings updates modify shared table rows
        persist_start = time.time()
        for ctx, sim_result in sim_results:
            game_result = self._persist_game_result(
                ctx=ctx,
                sim_result=sim_result,
                unified_api=unified_api,
                simulation_mode=simulation_mode,
                dynasty_id=dynasty_id,
                db_path=db_path
            )
            games_played.append(game_result)

        persist_elapsed = time.time() - persist_start
        logger.info("Persisted %d game results in %.2f seconds (sequential)",
                   len(games_played), persist_elapsed)

        events_processed.append(f"Week {week_number}: {len(games_played)} games simulated")

        # Collect all injuries from all games this week
        all_injuries = []
        for game in games_played:
            all_injuries.extend(game.get("injuries", []))

        # Update award race tracking (week 10+)
        award_race_tracked = self._update_award_race_tracking(db_path, dynasty_id, season, week_number)

        # Evaluate flex scheduling (weeks 10-15 flex weeks 12-17)
        flex_results = self._evaluate_flex_scheduling(context, week_number, season)

        # Generate power rankings for the week (Media Coverage - Milestone 12)
        power_rankings_count = self._generate_power_rankings(db_path, dynasty_id, season, week_number)

        return {
            "games_played": games_played,
            "events_processed": events_processed,
            "week": week_number,
            "injuries": all_injuries,
            "practice_injuries": weekly_injury_results.get("practice_injuries", []),
            "players_returning": weekly_injury_results.get("players_returning", []),
            "award_race_tracked": award_race_tracked,
            "flex_changes": flex_results,
            "power_rankings_updated": power_rankings_count,
        }

    def _update_standings_for_game(
        self,
        dynasty_id: str,
        season: int,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int,
        overtime_periods: int = 0
    ) -> None:
        """Update standings for both teams after a game.

        Uses StandingsAPI which updates the game_cycle database.
        This properly tracks all record types:
        - Overall W-L-T
        - Division record (games vs same division teams)
        - Conference record (games vs same conference teams)
        - Home/Away records
        - Points for/against

        Also updates head-to-head records and rivalry intensity.
        """
        from team_management.teams.team_loader import TeamDataLoader
        from game_cycle.database.connection import GameCycleDatabase
        from game_cycle.database.standings_api import StandingsAPI

        # Load team data for division/conference detection
        team_loader = TeamDataLoader()
        home_team = team_loader.get_team_by_id(home_team_id)
        away_team = team_loader.get_team_by_id(away_team_id)

        # Determine game type
        is_divisional = (
            home_team.division == away_team.division and
            home_team.conference == away_team.conference
        )
        is_conference = home_team.conference == away_team.conference

        # Use StandingsAPI with game_cycle database
        gc_db = GameCycleDatabase()
        standings_api = StandingsAPI(gc_db)
        standings_api.update_from_game(
            dynasty_id=dynasty_id,
            season=season,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
            is_divisional=is_divisional,
            is_conference=is_conference
        )

        # Update head-to-head record (Milestone 11, Tollgate 2)
        from game_cycle.database.head_to_head_api import HeadToHeadAPI
        h2h_api = HeadToHeadAPI(gc_db)
        h2h_api.update_after_game(
            dynasty_id=dynasty_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
            season=season,
            is_playoff=False
        )

        # Update rivalry intensity (Milestone 11, Tollgate 6)
        from game_cycle.services.rivalry_service import RivalryService
        rivalry_service = RivalryService(gc_db)
        rivalry_service.update_rivalry_after_game(
            dynasty_id=dynasty_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
            overtime_periods=overtime_periods,
            is_playoff=False,
        )

    def can_advance(self, stage: Stage, context: Dict[str, Any]) -> bool:
        """
        Check if all games for the week have been played.

        For simplicity, we return True after execute() runs.

        Args:
            stage: The current week stage
            context: Execution context

        Returns:
            True if all games complete (or no games scheduled)
        """
        # After execute(), week is complete
        return True

    def _build_standings_lookup(self, standings_data: Dict[str, Any]) -> Dict[int, Any]:
        """Build a team_id -> standing lookup from standings data."""
        standings_lookup = {}
        for item in standings_data.get("overall", []):
            team_id = item.get("team_id")
            standing = item.get("standing")
            if team_id and standing:
                standings_lookup[team_id] = standing
        return standings_lookup

    def _build_matchups(
        self,
        games: List[Dict[str, Any]],
        standings_lookup: Dict[int, Any],
        team_id_key: str = "team_id"
    ) -> List[Dict[str, Any]]:
        """
        Build matchup list from games with standings info.

        Args:
            games: List of game dicts with home_team_id, away_team_id
            standings_lookup: team_id -> standing mapping
            team_id_key: Key name for team ID in output ("id" or "team_id")

        Returns:
            List of matchup dicts ready for UI display
        """
        from team_management.teams.team_loader import TeamDataLoader
        team_loader = TeamDataLoader()

        matchups = []
        for game in games:
            home_team_id = game.get("home_team_id")
            away_team_id = game.get("away_team_id")

            home_standing = standings_lookup.get(home_team_id)
            away_standing = standings_lookup.get(away_team_id)

            home_team = team_loader.get_team_by_id(home_team_id)
            away_team = team_loader.get_team_by_id(away_team_id)

            matchups.append({
                "game_id": game.get("game_id"),
                "home_team": {
                    team_id_key: home_team_id,
                    "name": home_team.full_name if home_team else f"Team {home_team_id}",
                    "abbreviation": home_team.abbreviation if home_team else "???",
                    "record": f"{home_standing.wins if home_standing else 0}-{home_standing.losses if home_standing else 0}",
                },
                "away_team": {
                    team_id_key: away_team_id,
                    "name": away_team.full_name if away_team else f"Team {away_team_id}",
                    "abbreviation": away_team.abbreviation if away_team else "???",
                    "record": f"{away_standing.wins if away_standing else 0}-{away_standing.losses if away_standing else 0}",
                },
                "is_played": game.get("home_score") is not None,
                "home_score": game.get("home_score"),
                "away_score": game.get("away_score"),
            })
        return matchups

    def get_week_preview(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get preview of the week's matchups.

        Args:
            stage: The week stage
            context: Execution context

        Returns:
            Preview with matchups, standings implications, etc.
        """
        unified_api = context["unified_api"]
        season = context["season"]
        week_number = self._get_week_number(stage.stage_type)

        games = unified_api.events_get_games_by_week(season, week_number)
        standings_data = unified_api.standings_get(season)
        standings_lookup = self._build_standings_lookup(standings_data)
        matchups = self._build_matchups(games, standings_lookup, team_id_key="id")

        return {
            "week": week_number,
            "matchups": matchups,
            "game_count": len(games),
            "played_count": sum(1 for m in matchups if m["is_played"]),
        }

    def get_week_preview_for_week(
        self,
        week_number: int,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get preview for a specific week (for navigation).

        Unlike get_week_preview(), this takes a week number directly
        instead of requiring a Stage object. Used for browsing past/future weeks.

        Args:
            week_number: Week number (1-22, includes playoff weeks 19-22)
            context: Execution context

        Returns:
            Preview with matchups for the specified week
        """
        # Route playoff weeks to dedicated handler
        if week_number > 18:
            return self._get_playoff_week_preview(week_number, context)

        unified_api = context["unified_api"]
        season = context["season"]

        games = unified_api.events_get_games_by_week(season, week_number)
        standings_data = unified_api.standings_get(season)
        standings_lookup = self._build_standings_lookup(standings_data)
        matchups = self._build_matchups(games, standings_lookup)

        # Get teams on bye for this week (Milestone 11, Tollgate 3)
        teams_on_bye = []
        try:
            from ..database.bye_week_api import ByeWeekAPI
            from ..database.connection import GameCycleDatabase
            dynasty_id = context.get("dynasty_id")
            if dynasty_id:
                db_path = self._get_db_path(context)
                gc_db = GameCycleDatabase(db_path)
                bye_api = ByeWeekAPI(gc_db)
                teams_on_bye = bye_api.get_teams_on_bye(dynasty_id, season, week_number)
        except Exception as e:
            logger.debug("Could not get bye weeks: %s", e)

        return {
            "week": week_number,
            "matchups": matchups,
            "game_count": len(games),
            "played_count": sum(1 for m in matchups if m["is_played"]),
            "teams_on_bye": teams_on_bye,
        }

    def _get_playoff_week_preview(
        self,
        week_number: int,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get preview for a playoff week (19-22).

        Queries the games table for playoff games instead of the events table.
        Playoff weeks map to:
            19 = Wild Card
            20 = Divisional
            21 = Conference Championship
            22 = Super Bowl

        Args:
            week_number: Playoff week (19-22)
            context: Execution context

        Returns:
            Preview with matchups for the specified playoff week
        """
        unified_api = context["unified_api"]
        season = context["season"]

        # Get playoff games from games table (not events table)
        games = unified_api.games_get_by_week(season, week_number, season_type="playoffs")
        standings_data = unified_api.standings_get(season)
        standings_lookup = self._build_standings_lookup(standings_data)
        matchups = self._build_matchups(games, standings_lookup)

        return {
            "week": week_number,
            "matchups": matchups,
            "game_count": len(games),
            "played_count": sum(1 for m in matchups if m["is_played"]),
        }

    def _get_week_number(self, stage_type: StageType) -> int:
        """Extract week number from stage type."""
        # REGULAR_WEEK_1 -> 1, REGULAR_WEEK_18 -> 18
        name = stage_type.name
        if name.startswith("REGULAR_WEEK_"):
            return int(name.replace("REGULAR_WEEK_", ""))
        return 0

    def _trigger_season_start_generation(self, context: Dict[str, Any]) -> None:
        """
        Trigger draft class and free agent generation at season start.

        Called at Week 1 of each season. Generates:
        - Draft class for NEXT year (e.g., 2026 draft class when 2025 season starts)
        - Free agents for the current offseason pool

        Idempotent - safe to call multiple times (checks if already generated).

        Args:
            context: Execution context with dynasty_id, season, db_path
        """
        dynasty_id = context.get("dynasty_id", "unknown")
        season = context.get("season", 2025)
        db_path = context.get("db_path")

        if not db_path:
            # Try to get from unified_api
            unified_api = context.get("unified_api")
            if unified_api:
                db_path = unified_api.database_path

        if not db_path:
            logger.warning("No db_path in context, skipping generation")
            return

        next_draft_year = season + 1

        logger.info("Week 1 - Triggering season start generation")
        logger.info("Dynasty: %s, Season: %s", dynasty_id, season)

        # Generate next year's draft class (idempotent)
        try:
            from ..services.draft_service import DraftService

            draft_service = DraftService(db_path, dynasty_id, season)
            draft_result = draft_service.ensure_draft_class_exists(draft_year=next_draft_year)

            if draft_result.get("generated"):
                logger.info("Generated %s draft class: %d prospects",
                          next_draft_year, draft_result['prospect_count'])
            elif draft_result.get("exists"):
                logger.info("%s draft class already exists: %d prospects",
                          next_draft_year, draft_result['prospect_count'])
            elif draft_result.get("error"):
                logger.warning("Draft class generation failed: %s", draft_result['error'])
        except Exception as e:
            logger.error("Draft class generation error: %s", e)

        # Generate free agents for the pool (idempotent - only adds if pool is low)
        try:
            from ..services.free_agent_generator import FreeAgentGenerator

            fa_generator = FreeAgentGenerator(db_path, dynasty_id, season)

            # Check existing count
            existing_count = fa_generator.get_existing_free_agent_count()

            # Only generate if pool is below threshold
            if existing_count < 50:
                target = 50 - existing_count
                fa_result = fa_generator.generate_free_agents(count=target)

                if fa_result.get("success"):
                    logger.info("Generated %d free agents (pool was %d, now %d)",
                              fa_result['count'], existing_count, existing_count + fa_result['count'])
            else:
                logger.info("Free agent pool already has %d players", existing_count)
        except Exception as e:
            logger.error("Free agent generation error: %s", e)

    def _process_weekly_injuries(
        self,
        context: Dict[str, Any],
        week_number: int
    ) -> Dict[str, Any]:
        """
        Process injury recoveries and practice injuries at the start of each week.

        Called before games are simulated. Handles:
        1. Checking for practice injuries across all 32 teams
        2. Processing injury recoveries (clearing healed injuries)

        Args:
            context: Execution context with dynasty_id, season, db_path
            week_number: Current week number (1-18)

        Returns:
            Dictionary with practice_injuries and players_returning lists
        """
        from ..services.injury_service import InjuryService

        dynasty_id = context.get("dynasty_id", "unknown")
        season = context.get("season", 2025)
        db_path = self._get_db_path(context)

        if not db_path:
            return {"practice_injuries": [], "players_returning": []}

        results = {
            "practice_injuries": [],
            "players_returning": [],
        }

        injury_service = InjuryService(db_path, dynasty_id, season)

        # 1. Check for practice injuries across all 32 teams
        for team_id in range(1, 33):
            practice_injury = self._roll_practice_injury(
                context=context,
                team_id=team_id,
                week=week_number
            )
            if practice_injury:
                injury_service.record_injury(practice_injury)
                results["practice_injuries"].append({
                    "player_id": practice_injury.player_id,
                    "player_name": practice_injury.player_name,
                    "team_id": practice_injury.team_id,
                    "injury_type": practice_injury.injury_type.value,
                    "weeks_out": practice_injury.weeks_out,
                    "severity": practice_injury.severity.value,
                })
                logger.info("Practice injury: %s (%s) - %d weeks",
                          practice_injury.player_name, practice_injury.injury_type.value,
                          practice_injury.weeks_out)

        # 2. Process injury recoveries
        recovered = injury_service.check_injury_recovery(week_number)
        for injury in recovered:
            # Calculate actual weeks out
            actual_weeks = week_number - injury.week_occurred
            injury_service.clear_injury(injury.injury_id, actual_weeks)
            results["players_returning"].append({
                "player_id": injury.player_id,
                "player_name": injury.player_name,
                "team_id": injury.team_id,
                "injury_type": injury.injury_type.value,
                "actual_weeks_out": actual_weeks,
            })
            logger.info("Player returning: %s (missed %d weeks)",
                      injury.player_name, actual_weeks)

        # 3. Process AI IR management (after week 1)
        user_team_id = context.get("user_team_id", 1)
        if week_number > 1:
            ir_results = injury_service.process_ai_ir_management(
                user_team_id=user_team_id,
                current_week=week_number
            )
            results["ir_placements"] = ir_results.get("ir_placements", [])
            results["ir_activations"] = ir_results.get("ir_activations", [])

            # Log IR events
            for event in ir_results.get("events", []):
                logger.info("%s", event)

            if ir_results.get("total_placements", 0) > 0:
                logger.info("Week %d: %d IR placements",
                          week_number, ir_results['total_placements'])
            if ir_results.get("total_activations", 0) > 0:
                logger.info("Week %d: %d IR activations",
                          week_number, ir_results['total_activations'])

        # Log summary
        if results["practice_injuries"]:
            logger.info("Week %d: %d practice injuries",
                      week_number, len(results['practice_injuries']))
        if results["players_returning"]:
            logger.info("Week %d: %d players returning from injury",
                      week_number, len(results['players_returning']))

        return results

    def _roll_practice_injury(
        self,
        context: Dict[str, Any],
        team_id: int,
        week: int
    ) -> Optional["Injury"]:
        """
        Roll for a practice injury on a team.

        Practice injuries occur at ~1.5% rate per team per week.
        Practice injuries are typically less severe (MINOR or MODERATE).

        Args:
            context: Execution context
            team_id: Team to roll for
            week: Current week number

        Returns:
            Injury instance if injury occurred, None otherwise
        """
        from ..services.injury_service import InjuryService

        # Practice injury rate: ~1.5% per team per week
        # This results in ~0.5 practice injuries per week across the league
        PRACTICE_INJURY_RATE = 0.015

        if random.random() >= PRACTICE_INJURY_RATE:
            return None

        # Get a random active player from the team
        player = self._get_random_active_player(context, team_id)
        if not player:
            return None

        dynasty_id = context.get("dynasty_id", "unknown")
        season = context.get("season", 2025)
        db_path = self._get_db_path(context)

        if not db_path:
            return None

        injury_service = InjuryService(db_path, dynasty_id, season)

        # Generate the practice injury
        # Practice injuries have lower probability modifier (0.3x) built into
        # InjuryService.calculate_injury_probability()
        return injury_service.generate_injury(
            player=player,
            week=week,
            occurred_during="practice",
            game_id=None
        )

    def _get_random_active_player(
        self,
        context: Dict[str, Any],
        team_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get a random active player from a team for practice injury roll.

        Excludes players already injured.

        Args:
            context: Execution context
            team_id: Team ID

        Returns:
            Player dictionary or None if no active players
        """
        import json
        import sqlite3

        dynasty_id = context.get("dynasty_id", "unknown")
        db_path = self._get_db_path(context)

        if not db_path:
            return None

        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get active players not currently injured
            cursor.execute("""
                SELECT
                    p.player_id,
                    p.first_name,
                    p.last_name,
                    p.team_id,
                    p.positions,
                    p.attributes,
                    p.birthdate
                FROM players p
                JOIN team_rosters tr
                    ON p.dynasty_id = tr.dynasty_id
                    AND p.player_id = tr.player_id
                LEFT JOIN player_injuries pi
                    ON p.dynasty_id = pi.dynasty_id
                    AND p.player_id = pi.player_id
                    AND pi.is_active = 1
                WHERE p.dynasty_id = ?
                    AND p.team_id = ?
                    AND tr.roster_status = 'active'
                    AND pi.injury_id IS NULL
            """, (dynasty_id, team_id))

            rows = cursor.fetchall()

            if not rows:
                return None

            # Select random player
            row = random.choice(rows)

            # Parse JSON fields
            positions = json.loads(row['positions']) if row['positions'] else []
            attributes = json.loads(row['attributes']) if row['attributes'] else {}

            return {
                'player_id': row['player_id'],
                'first_name': row['first_name'],
                'last_name': row['last_name'],
                'team_id': row['team_id'],
                'positions': positions,
                'attributes': attributes,
                'birthdate': row['birthdate'],
            }

    def _update_award_race_tracking(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        week_number: int
    ) -> int:
        """
        Update award race tracking for performance optimization.

        Tracks top performers starting at week 10 to reduce end-of-season
        award calculation time. Creates a pre-filtered pool of candidates.

        Args:
            db_path: Database path
            dynasty_id: Dynasty identifier
            season: Season year
            week_number: Current week number (1-18)

        Returns:
            Number of players tracked (0 if week < 10)
        """
        try:
            from ..services.awards.award_race_tracker import AwardRaceTracker

            tracker = AwardRaceTracker(db_path, dynasty_id, season)

            if not tracker.should_track(week_number):
                return 0

            logger.info("Award race: Starting tracking for week %d", week_number)
            count = tracker.update_tracking(week_number)

            if count > 0:
                logger.info("Award race: Tracked %d players for week %d", count, week_number)
            else:
                logger.warning("Award race: No candidates tracked for week %d (check season grades)", week_number)

            return count

        except Exception as e:
            import traceback
            # Award tracking is non-critical - don't crash the game cycle
            logger.error("Award race tracking failed: %s", e)
            traceback.print_exc()
            return 0

    def _evaluate_flex_scheduling(
        self,
        context: Dict[str, Any],
        current_week: int,
        season: int,
    ) -> Dict[str, Any]:
        """
        Evaluate and apply flex scheduling after week completion.

        Called after weeks 10-15 to flex weeks 12-17.
        (12-day notice = ~2 weeks ahead)

        Args:
            context: Execution context
            current_week: Week that just completed
            season: Season year

        Returns:
            Dictionary with flex evaluation results
        """
        # Only evaluate during flex window (weeks 10-15 can flex weeks 12-17)
        if current_week < 10 or current_week > 15:
            return {"evaluated": False, "reason": "outside_flex_window"}

        target_week = current_week + 2  # 12-day notice
        if target_week > 17:
            return {"evaluated": False, "reason": "no_remaining_flex_weeks"}

        dynasty_id = context.get("dynasty_id", "unknown")
        db_path = self._get_db_path(context)

        if not db_path:
            return {"evaluated": False, "reason": "no_db_path"}

        try:
            from ..database.connection import GameCycleDatabase
            from ..services.flex_scheduler import FlexScheduler, FLEX_THRESHOLD

            gc_db = GameCycleDatabase(db_path)
            flex_scheduler = FlexScheduler(gc_db, dynasty_id)

            # Get recommendations
            recommendations = flex_scheduler.evaluate_flex_opportunities(
                season, current_week, target_week
            )

            if not recommendations:
                logger.info("Flex scheduling: No flex candidates for week %d", target_week)
                return {
                    "evaluated": True,
                    "target_week": target_week,
                    "recommendations": 0,
                    "flexed": [],
                }

            # Execute flex for recommendations meeting threshold
            flexed_games = []
            for rec in recommendations:
                if rec.appeal_delta >= FLEX_THRESHOLD:
                    success = flex_scheduler.execute_flex(season, rec)
                    if success:
                        flexed_games.append({
                            "game_in": rec.game_to_flex_in,
                            "game_out": rec.game_to_flex_out,
                            "slot": rec.target_slot.value,
                            "reason": rec.reason,
                            "appeal_delta": rec.appeal_delta,
                        })
                        logger.info("Flex scheduling: Flexed game into %s for week %d (%s)",
                                  rec.target_slot.value, target_week, rec.reason)

            if flexed_games:
                logger.info("Flex scheduling: %d games flexed for week %d",
                          len(flexed_games), target_week)

            return {
                "evaluated": True,
                "target_week": target_week,
                "recommendations": len(recommendations),
                "flexed": flexed_games,
            }

        except Exception as e:
            import traceback
            # Flex scheduling is non-critical - don't crash the game cycle
            logger.error("Flex scheduling failed: %s", e)
            traceback.print_exc()
            return {"evaluated": False, "reason": f"error: {str(e)}"}

    def _generate_game_headline(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        week: int,
        game_id: str,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int,
        sim_result
    ) -> None:
        """
        Generate and persist headline for completed game.

        Integrates HeadlineGenerator service with game simulation flow.
        Headlines are persisted to media_headlines table for display in
        the Media Coverage UI.

        Non-critical: Errors are logged but do not fail game simulation.

        Args:
            db_path: Database path
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            game_id: Game identifier
            home_team_id: Home team ID
            away_team_id: Away team ID
            home_score: Home team final score
            away_score: Away team final score
            sim_result: SimulationResult with game details
        """
        try:
            from ..services.headline_generator import HeadlineGenerator
            from ..database.media_coverage_api import MediaCoverageAPI
            from ..database.connection import GameCycleDatabase

            # Determine winner/loser
            if home_score > away_score:
                winner_id, loser_id = home_team_id, away_team_id
                winner_score, loser_score = home_score, away_score
            else:
                winner_id, loser_id = away_team_id, home_team_id
                winner_score, loser_score = away_score, home_score

            # Build game data for headline generation
            game_data = {
                "game_id": game_id,
                "week": week,
                "winner_id": winner_id,
                "loser_id": loser_id,
                "winner_score": winner_score,
                "loser_score": loser_score,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "is_playoff": False,
                "overtime_periods": getattr(sim_result, 'overtime_periods', 0),
            }

            # Generate headline
            generator = HeadlineGenerator(db_path, dynasty_id, season)
            headline = generator.generate_game_headline(game_data, include_body_text=True)

            if not headline:
                logger.warning("No headline generated for game %s", game_id)
                return

            # Persist to database
            gc_db = GameCycleDatabase(db_path)
            try:
                media_api = MediaCoverageAPI(gc_db)
                media_api.save_headline(
                    dynasty_id=dynasty_id,
                    season=season,
                    week=week,
                    headline_data={
                        'headline_type': headline.headline_type.value if hasattr(headline.headline_type, 'value') else str(headline.headline_type),
                        'headline': headline.headline,
                        'subheadline': headline.subheadline,
                        'body_text': headline.body_text,
                        'sentiment': headline.sentiment.value if hasattr(headline.sentiment, 'value') else str(headline.sentiment),
                        'priority': headline.priority,
                        'team_ids': [home_team_id, away_team_id],
                        'player_ids': headline.player_ids or [],
                        'game_id': game_id,
                        'metadata': headline.metadata or {}
                    }
                )
                logger.info("Generated headline for game %s: %s...", game_id, headline.headline[:50])
            finally:
                gc_db.close()

        except Exception as e:
            # Log but don't fail game simulation for headline errors
            logger.warning("Failed to generate headline for game %s: %s", game_id, e)

    def _generate_power_rankings(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        week: int
    ) -> int:
        """
        Generate and persist power rankings after week completion.

        Power rankings are calculated based on:
        - Win-loss record
        - Point differential
        - Recent performance
        - Strength of victory
        - Quality wins

        Non-critical: Errors are logged but do not fail game simulation.

        Args:
            db_path: Database path
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number

        Returns:
            Number of teams ranked (32 on success, 0 on failure)
        """
        try:
            from ..services.power_rankings_service import PowerRankingsService

            service = PowerRankingsService(db_path, dynasty_id, season)
            rankings = service.calculate_and_save_rankings(week)

            if rankings:
                logger.info("Generated power rankings for week %d: %d teams ranked",
                          week, len(rankings))
                return len(rankings)
            else:
                logger.warning("No power rankings generated for week %d", week)
                return 0

        except Exception as e:
            # Log but don't fail game simulation for power rankings errors
            logger.warning("Failed to generate power rankings for week %d: %s", week, e)
            return 0

    def _generate_preview_headlines(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        week: int
    ) -> int:
        """
        Generate and persist preview headlines for upcoming notable games.

        Preview headlines are generated for games that meet criticality threshold:
        - Rivalry games (intensity >= 50)
        - Divisional games
        - Games with playoff implications
        - Head-to-head winning streaks (3+ games)

        Non-critical: Errors are logged but do not fail game simulation.

        Args:
            db_path: Database path
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number to preview

        Returns:
            Number of preview headlines generated (0 on failure)
        """
        try:
            from ..services.headline_generator import HeadlineGenerator
            from ..database.connection import GameCycleDatabase
            from ..database.media_coverage_api import MediaCoverageAPI

            generator = HeadlineGenerator(db_path, dynasty_id, season)
            previews = generator.generate_preview_headlines(
                week=week,
                min_priority_boost=20  # Only notable games
            )

            if not previews:
                logger.debug("No preview headlines generated for week %d", week)
                return 0

            # Persist previews
            gc_db = GameCycleDatabase(db_path)
            try:
                media_api = MediaCoverageAPI(gc_db)
                for preview in previews:
                    media_api.save_headline(
                        dynasty_id=dynasty_id,
                        season=season,
                        week=week,
                        headline_data={
                            'headline_type': 'PREVIEW',
                            'headline': preview.headline,
                            'subheadline': preview.subheadline,
                            'body_text': preview.body_text,
                            'sentiment': preview.sentiment,
                            'priority': preview.priority,
                            'team_ids': preview.team_ids,
                            'game_id': preview.game_id,
                            'metadata': preview.metadata
                        }
                    )
            finally:
                gc_db.close()

            logger.info("Generated %d preview headlines for week %d",
                       len(previews), week)
            return len(previews)

        except Exception as e:
            # Log but don't fail game simulation for preview errors
            logger.warning("Failed to generate preview headlines for week %d: %s", week, e)
            return 0