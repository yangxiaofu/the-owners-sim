"""
Stage Controller - Main orchestrator for stage-based progression.

Dynasty-First Architecture:
- Requires dynasty_id for all operations
- Uses production database APIs (DatabaseAPI, DynastyStateAPI)
- Uses production StandingsStore instead of custom standings manager
- Uses game_cycle.db exclusively (main2.py entry point)
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Protocol, TypedDict

logger = logging.getLogger(__name__)

from .stage_definitions import Stage, StageType, SeasonPhase, OFFSEASON_STAGES
from .handlers.regular_season import RegularSeasonHandler
from .handlers.playoffs import PlayoffHandler
from .handlers.offseason import OffseasonHandler
from .handlers.preseason import PreseasonHandler


class StageContext(TypedDict):
    """Type definition for stage execution context."""
    dynasty_id: str
    season: int
    db_path: str
    unified_api: Any  # UnifiedDatabaseAPI
    dynasty_state_api: Any  # DynastyStateAPI
    user_team_id: int
    simulation_mode: str


class StageHandler(Protocol):
    """Protocol for stage-specific handlers."""

    def execute(self, stage: Stage, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the stage and return results.

        Args:
            stage: The current stage to execute
            context: Execution context (dynasty_id, database connection, etc.)

        Returns:
            Dictionary with execution results (games played, events processed, etc.)
        """
        ...

    def can_advance(self, stage: Stage, context: Dict[str, Any]) -> bool:
        """
        Check if the stage is complete and can advance to next.

        Args:
            stage: The current stage
            context: Execution context

        Returns:
            True if stage is complete and ready to advance
        """
        ...


@dataclass
class StageResult:
    """Result of executing a stage."""
    stage: Stage
    success: bool
    games_played: List[Dict[str, Any]]
    events_processed: List[str]
    errors: List[str]
    can_advance: bool
    next_stage: Optional[Stage]
    handler_data: Dict[str, Any] = None  # Raw handler result data (FA signings, draft picks, etc.)

    def __post_init__(self):
        """Initialize handler_data to empty dict if None."""
        if self.handler_data is None:
            self.handler_data = {}

    @property
    def summary(self) -> str:
        """Human-readable summary of the stage execution."""
        parts = [f"{self.stage.display_name} ({self.stage.season_year})"]

        if self.games_played:
            parts.append(f"{len(self.games_played)} games")

        if self.events_processed:
            parts.append(f"{len(self.events_processed)} events")

        if self.errors:
            parts.append(f"{len(self.errors)} errors")

        return " | ".join(parts)


class StageController:
    """
    Main controller for stage-based season progression.

    Dynasty-First Architecture:
    - All operations require dynasty_id
    - Uses production DatabaseAPI for game/schedule queries
    - Uses production DynastyStateAPI for state tracking
    - Uses production standings APIs

    Usage:
        controller = StageController(
            db_path="data/database/game_cycle/game_cycle.db",
            dynasty_id="my_dynasty",
            season=2025
        )

        # Get current stage
        stage = controller.current_stage

        # Execute current stage (simulates all games/events for this stage)
        result = controller.execute_current_stage()

        # Advance to next stage
        if result.can_advance:
            controller.advance_to_next_stage()
    """

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int = 2025
    ):
        """
        Initialize the stage controller.

        Args:
            db_path: Path to game_cycle.db database
            dynasty_id: Dynasty identifier (REQUIRED)
            season: Season year (default: 2025)
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season

        # Import production APIs lazily to avoid circular imports
        from database.unified_api import UnifiedDatabaseAPI
        from database.dynasty_state_api import DynastyStateAPI
        from database.dynasty_database_api import DynastyDatabaseAPI

        # Use UnifiedDatabaseAPI - has all the methods we need
        self._unified_api = UnifiedDatabaseAPI(db_path, dynasty_id)
        self._dynasty_state_api = DynastyStateAPI(db_path)
        self._dynasty_db_api = DynastyDatabaseAPI(db_path)

        # Create handlers (they'll receive context with dynasty_id)
        self._regular_season_handler = RegularSeasonHandler()
        self._playoff_handler = PlayoffHandler()
        self._offseason_handler = OffseasonHandler(db_path)
        self._preseason_handler = PreseasonHandler()

        self._current_stage: Optional[Stage] = None
        self._initialized = False
        self._simulation_mode: str = "full"  # Default to full sim ("instant" or "full")
        self._progress_callback: Optional[callable] = None  # For UI progress updates

    @property
    def dynasty_id(self) -> str:
        """Get current dynasty ID."""
        return self._dynasty_id

    def set_simulation_mode(self, mode: str) -> None:
        """
        Set simulation mode for game execution.

        Args:
            mode: "instant" for fast mock stats, "full" for play-by-play simulation
        """
        if mode not in ("instant", "full"):
            raise ValueError(f"Invalid simulation mode: {mode}. Use 'instant' or 'full'.")
        self._simulation_mode = mode
        logger.info(f"Simulation mode set to: {mode}")

    def set_progress_callback(self, callback: Optional[callable]) -> None:
        """
        Set callback for progress updates during stage execution.

        Used by UI to show progress dialog during week/playoff simulation.

        Args:
            callback: Function(current: int, total: int, message: str) or None to clear
        """
        self._progress_callback = callback

    @property
    def season(self) -> int:
        """Get current season."""
        return self._season

    @property
    def current_stage(self) -> Optional[Stage]:
        """Get the current stage. Loads from dynasty_state if not cached."""
        if self._current_stage is None:
            self._current_stage = self._load_current_stage()
        return self._current_stage

    def initialize(self, season_year: int = 2025, skip_preseason: bool = True) -> Stage:
        """
        Initialize stage tracking for an existing dynasty.

        Note: Dynasty must already be created via DynastyInitializationService.
        This just initializes the stage state for game_cycle progression.

        Args:
            season_year: The NFL season year (e.g., 2025)
            skip_preseason: If True, start at Week 1 (default)

        Returns:
            The starting stage
        """
        self._season = season_year

        # Determine starting stage
        if skip_preseason:
            starting_stage = StageType.REGULAR_WEEK_1
        else:
            # Start at training camp to go through preseason weeks
            # (OFFSEASON_PRESEASON_W1/W2/W3 are part of offseason flow now)
            starting_stage = StageType.OFFSEASON_TRAINING_CAMP

        # Create the starting stage
        self._current_stage = Stage(
            stage_type=starting_stage,
            season_year=season_year,
            completed=False
        )

        # Save to dynasty_state (we track stage in dynasty_state.current_week/phase)
        self._save_current_stage(self._current_stage)
        self._initialized = True

        return self._current_stage

    def is_initialized(self) -> bool:
        """Check if stage tracking is initialized for this dynasty."""
        if self._initialized:
            return True

        # Check if we can load a stage from dynasty_state
        stage = self._load_current_stage()
        if stage is not None:
            self._initialized = True
            return True

        return False

    def execute_current_stage(
        self,
        extra_context: Optional[Dict[str, Any]] = None
    ) -> StageResult:
        """
        Execute all events/games for the current stage.

        Args:
            extra_context: Optional extra context to merge (e.g., user_decisions for offseason)

        Returns:
            StageResult with execution details
        """
        # DEBUG: Log execution start
        logger.debug("execute_current_stage() called")
        logger.debug(f"dynasty_id={self._dynasty_id}, season={self._season}")
        logger.debug(f"db_path={self._db_path}")

        stage = self.current_stage
        logger.debug(f"current_stage={stage}")

        if stage is None:
            return StageResult(
                stage=Stage(StageType.REGULAR_WEEK_1, self._season),
                success=False,
                games_played=[],
                events_processed=[],
                errors=["No current stage found. Call initialize() first."],
                can_advance=False,
                next_stage=None
            )

        context = self._build_context()

        # Merge extra context (e.g., user decisions for offseason stages)
        if extra_context:
            context.update(extra_context)

        handler = self._get_handler(stage.phase)

        if handler is None:
            # No handler - just mark as complete (for phases we haven't implemented)
            stage.completed = True
            return StageResult(
                stage=stage,
                success=True,
                games_played=[],
                events_processed=["Stage skipped (no handler)"],
                errors=[],
                can_advance=True,
                next_stage=stage.next_stage()
            )

        try:
            result = handler.execute(stage, context)
            can_advance = handler.can_advance(stage, context)

            # Mark stage as completed when execution is successful
            if can_advance:
                stage.completed = True

            return StageResult(
                stage=stage,
                success=True,
                games_played=result.get("games_played", []),
                events_processed=result.get("events_processed", []),
                errors=[],
                can_advance=can_advance,
                next_stage=stage.next_stage() if can_advance else None,
                handler_data=result  # Pass full handler result (includes FA signings, draft picks, etc.)
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return StageResult(
                stage=stage,
                success=False,
                games_played=[],
                events_processed=[],
                errors=[str(e)],
                can_advance=False,
                next_stage=None
            )

    def advance_to_next_stage(self) -> Optional[Stage]:
        """
        Advance to the next stage.

        If advancing to a playoff stage, pre-seeds the bracket so matchups
        are visible before games are executed.

        If advancing to a new season (waiver wire → Week 1), increments the
        season SSOT and verifies standings are initialized.

        Returns:
            The new current stage, or None if cannot advance
        """
        current = self.current_stage
        if current is None:
            return None

        # Get the next stage type to check for season transition
        next_stage_temp = current.next_stage()
        if next_stage_temp is None:
            return None

        # Check if we're transitioning to a new season (waiver wire → Week 1)
        is_new_season = (
            current.stage_type == StageType.OFFSEASON_WAIVER_WIRE and
            next_stage_temp.stage_type == StageType.REGULAR_WEEK_1
        )

        # If starting new season, increment the SSOT first
        if is_new_season:
            logger.info(f"Transitioning to new season, incrementing SSOT from {self._season} to {self._season + 1}")
            self._season = self._season + 1  # Increment cache

            # Update SSOT in database BEFORE creating next stage
            self._dynasty_state_api.update_season(
                dynasty_id=self._dynasty_id,
                season=self._season
            )

        # Now create the next stage with the correct season from SSOT
        next_stage = Stage(
            stage_type=next_stage_temp.stage_type,
            season_year=self._season,  # Use SSOT, not next_stage.season_year
            completed=False
        )

        self._current_stage = next_stage
        self._save_current_stage(next_stage)

        # Pre-seed playoff bracket when entering a playoff stage
        if next_stage.phase == SeasonPhase.PLAYOFFS:
            self._seed_playoff_bracket(next_stage)

        # Verify standings initialized when starting a new regular season
        if is_new_season:
            logger.info(f"Starting new season {self._season}, verifying standings initialized")
            self._verify_season_standings(self._season)

        return next_stage

    def _seed_playoff_bracket(self, stage: Stage) -> None:
        """
        Pre-seed the playoff bracket for a playoff stage.

        This creates matchups in the playoff_bracket table so they're visible
        in the UI BEFORE the user clicks Execute to simulate the games.

        Args:
            stage: The playoff stage to seed
        """
        context = self._build_context()

        try:
            result = self._playoff_handler.seed_bracket(stage, context)
            if result.get("already_seeded"):
                logger.info(f"Playoff bracket already seeded for {stage.display_name}")
            else:
                matchups = result.get("matchups", [])
                logger.info(f"Seeded playoff bracket: {len(matchups)} matchups for {stage.display_name}")
        except Exception as e:
            logger.warning(f"Failed to seed playoff bracket: {e}")
            # Don't fail the stage transition - the legacy code path will still work

    def _generate_placeholder_standings(self, season_year: int) -> None:
        """
        Generate placeholder standings for offseason testing.

        This allows jumping directly to offseason without simulating
        the regular season or playoffs. Random standings are generated
        so offseason logic (re-signing, free agency, draft order) works.

        Args:
            season_year: The season year to generate standings for
        """
        from .database.connection import GameCycleDatabase
        from .database.standings_api import StandingsAPI

        gc_db = GameCycleDatabase(self._db_path)
        standings_api = StandingsAPI(gc_db)

        created = standings_api.initialize_season_standings(
            dynasty_id=self._dynasty_id,
            season=season_year,
            placeholder=True
        )

        if created == 0:
            logger.info(f"Standings already exist for {season_year}, skipping placeholder generation")
            return

        # Also clear any existing injuries for a fresh start
        gc_db.execute(
            "DELETE FROM player_injuries WHERE dynasty_id = ? AND season = ?",
            (self._dynasty_id, season_year)
        )

        logger.info(f"Generated placeholder standings for {season_year} season (32 teams, injuries cleared)")

    def _generate_minimal_standings(self, season_year: int) -> None:
        """
        Generate minimal standings for fast offseason skip.

        Creates 0-0 records for all 32 teams without simulating games.
        This allows offseason stages (especially draft) to function.

        Args:
            season_year: The season year to generate standings for
        """
        from .database.connection import GameCycleDatabase
        from .database.standings_api import StandingsAPI

        gc_db = GameCycleDatabase(self._db_path)
        standings_api = StandingsAPI(gc_db)

        created = standings_api.initialize_season_standings(
            dynasty_id=self._dynasty_id,
            season=season_year,
            placeholder=False
        )

        if created == 0:
            logger.info(
                f"Standings already exist for {season_year}, "
                f"skipping minimal generation"
            )
            return

        logger.info(
            f"Generated minimal standings for {season_year} season "
            f"(32 teams, all 0-0 records)"
        )

    def jump_to_offseason(self) -> Stage:
        """
        Jump directly to offseason without simulating games or playoffs.

        This is a fast-skip operation that:
        1. Generates minimal standings (all teams 0-0)
        2. Sets stage to OFFSEASON_OWNER (Owner review stage)
        3. Does NOT simulate games, stats, or injuries

        Returns:
            Stage: The new offseason stage

        Raises:
            RuntimeError: If database operations fail
        """
        current_stage = self.get_current_stage()
        if current_stage is None:
            raise RuntimeError("No current stage to skip from")

        season_year = current_stage.season_year

        # Generate minimal standings if not already present
        self._generate_minimal_standings(season_year)

        # Create the offseason stage (Owner review - before Franchise Tag)
        new_stage = Stage(
            stage_type=StageType.OFFSEASON_OWNER,
            season_year=season_year,
            completed=False
        )

        # Update cached current stage BEFORE saving
        self._current_stage = new_stage

        # Save to database
        self._save_current_stage(new_stage)

        logger.info(
            f"Jumped directly to offseason for {season_year} season "
            f"(no games simulated)"
        )

        return new_stage

    def start_new_season(self, season_year: int, skip_preseason: bool = True) -> Stage:
        """
        Start a new season.

        Note: This doesn't reset the dynasty - just starts tracking a new season.
        For full season reset, use DynastyInitializationService.prepare_next_season().

        Args:
            season_year: The NFL season year (e.g., 2025)
            skip_preseason: If True, start at Week 1 instead of Preseason

        Returns:
            The starting stage
        """
        return self.initialize(season_year, skip_preseason)

    def jump_to_stage(self, stage_type: StageType) -> Stage:
        """
        Jump directly to a specific stage (useful for testing/debugging).

        Args:
            stage_type: The stage to jump to

        Returns:
            The new current stage
        """
        current = self.current_stage
        season_year = current.season_year if current else self._season

        new_stage = Stage(
            stage_type=stage_type,
            season_year=season_year,
            completed=False
        )

        self._current_stage = new_stage
        self._save_current_stage(new_stage)

        # Pre-seed playoff bracket when jumping to a playoff stage
        if new_stage.phase == SeasonPhase.PLAYOFFS:
            self._seed_playoff_bracket(new_stage)

        # Generate placeholder standings when jumping to offseason (for testing)
        if new_stage.phase == SeasonPhase.OFFSEASON:
            self._generate_placeholder_standings(season_year)

        return new_stage

    def get_stage_preview(self) -> Dict[str, Any]:
        """
        Get preview of the current stage.

        Returns:
            Preview data for UI display
        """
        stage = self.current_stage
        if stage is None:
            return {"error": "No current stage"}

        context = self._build_context()

        if stage.phase == SeasonPhase.REGULAR_SEASON:
            return self._regular_season_handler.get_week_preview(stage, context)
        elif stage.phase == SeasonPhase.PLAYOFFS:
            return self._playoff_handler.get_round_preview(stage, context)
        elif stage.phase == SeasonPhase.OFFSEASON:
            return self._offseason_handler.get_stage_preview(stage, context)
        else:
            return {
                "stage": stage.display_name,
                "phase": stage.phase.name,
                "events": [],
            }

    def get_standings(self) -> List[Dict[str, Any]]:
        """Get current standings for UI display with conference/division info.

        Reads standings from game_cycle database via StandingsAPI.
        Uses TeamDataLoader for team metadata (conference, division, abbreviation).
        """
        from .database.connection import GameCycleDatabase
        from .database.standings_api import StandingsAPI
        from team_management.teams.team_loader import TeamDataLoader

        # Use current stage's season year (single source of truth)
        stage = self.current_stage
        current_season = stage.season_year if stage else self._season

        # Query standings via StandingsAPI
        gc_db = GameCycleDatabase()
        standings_api = StandingsAPI(gc_db)
        all_standings = standings_api.get_standings(
            dynasty_id=self._dynasty_id,
            season=current_season,
            season_type='regular_season'
        )

        # Load team data for abbreviations and conference/division
        team_loader = TeamDataLoader()

        # Build standings lookup for SOS calculation
        standings_by_id = {s.team_id: s for s in all_standings}

        # Get all games to calculate Strength of Schedule
        # TODO: Move this to a games API in game_cycle database
        games = self._unified_api.games_get_results(
            season=current_season,
            season_type="regular_season"
        )

        # Build map of team_id -> list of opponents played
        team_opponents: Dict[int, List[int]] = {}
        for game in games:
            home_id = game.get("home_team_id")
            away_id = game.get("away_team_id")
            if home_id and away_id:
                team_opponents.setdefault(home_id, []).append(away_id)
                team_opponents.setdefault(away_id, []).append(home_id)

        # Transform standings into flat list for UI
        result = []

        for standing in all_standings:
            team_id = standing.team_id

            # Get team info from TeamDataLoader
            team = team_loader.get_team_by_id(team_id)
            abbreviation = team.abbreviation if team else f"T{team_id}"
            conference = team.conference if team else "AFC"
            division = team.division if team else "East"

            # Calculate win percentage
            total_games = standing.wins + standing.losses + standing.ties
            if total_games > 0:
                win_pct = f"{standing.win_percentage:.3f}"
            else:
                win_pct = ".000"

            # Calculate Strength of Schedule (SOS)
            # SOS = average win percentage of all opponents played
            opponents = team_opponents.get(team_id, [])
            if opponents:
                opp_win_pcts = []
                for opp_id in opponents:
                    opp_standing = standings_by_id.get(opp_id)
                    if opp_standing and (opp_standing.wins + opp_standing.losses + opp_standing.ties) > 0:
                        opp_win_pcts.append(opp_standing.win_percentage)
                sos = sum(opp_win_pcts) / len(opp_win_pcts) if opp_win_pcts else 0.0
            else:
                sos = 0.0

            result.append({
                "team_id": team_id,
                "abbreviation": abbreviation,
                "conference": conference,
                "division": division,
                "wins": standing.wins,
                "losses": standing.losses,
                "ties": standing.ties,
                "win_pct": win_pct,
                "point_diff": standing.point_differential,
                "points_for": standing.points_for,
                "points_against": standing.points_against,
                "div_record": f"{standing.division_wins}-{standing.division_losses}",
                "conf_record": f"{standing.conference_wins}-{standing.conference_losses}",
                "home_record": f"{standing.home_wins}-{standing.home_losses}",
                "away_record": f"{standing.away_wins}-{standing.away_losses}",
                "sos": f"{sos:.3f}",
            })

        return result

    def _build_context(self) -> StageContext:
        """Build execution context for handlers."""
        # Use current stage's season year (single source of truth)
        stage = self.current_stage
        current_season = stage.season_year if stage else self._season

        # Get user team ID from dynasty info
        # Note: Use `or 1` because .get() returns None when key exists but is NULL
        dynasty_info = self._dynasty_db_api.get_dynasty_by_id(self._dynasty_id)
        user_team_id = (dynasty_info.get('team_id') or 1) if dynasty_info else 1

        return {
            "dynasty_id": self._dynasty_id,
            "season": current_season,
            "db_path": self._db_path,
            "unified_api": self._unified_api,
            "dynasty_state_api": self._dynasty_state_api,
            "user_team_id": user_team_id,
            "simulation_mode": self._simulation_mode,
            "progress_callback": self._progress_callback,  # For UI progress updates
        }

    def _get_handler(self, phase: SeasonPhase) -> Optional[StageHandler]:
        """Get the handler for a season phase."""
        if phase == SeasonPhase.REGULAR_SEASON:
            return self._regular_season_handler
        elif phase == SeasonPhase.PLAYOFFS:
            return self._playoff_handler
        elif phase == SeasonPhase.OFFSEASON:
            return self._offseason_handler
        elif phase == SeasonPhase.PRESEASON:
            return self._preseason_handler
        return None

    def _load_current_stage(self) -> Optional[Stage]:
        """Load current stage from dynasty_state."""
        # Use get_latest_state() to get most recent season (SSOT for season)
        state = self._dynasty_state_api.get_latest_state(
            dynasty_id=self._dynasty_id
        )

        if state is None:
            return None

        # Update self._season from loaded state (fixes player aging bug)
        loaded_season = state.get('season', self._season)
        self._season = loaded_season

        # Map phase string to SeasonPhase
        phase_str = state.get('current_phase', 'regular_season')
        week = state.get('current_week', 1)

        # Determine stage type from phase and week
        if phase_str == 'preseason':
            # Map legacy 'preseason' phase to modern offseason preseason stages
            preseason_stages = [
                StageType.OFFSEASON_PRESEASON_W1,
                StageType.OFFSEASON_PRESEASON_W2,
                StageType.OFFSEASON_PRESEASON_W3
            ]
            stage_idx = min(week - 1, len(preseason_stages) - 1)
            stage_type = preseason_stages[stage_idx]
        elif phase_str == 'regular_season':
            stage_type = StageType[f"REGULAR_WEEK_{week}"]
        elif phase_str == 'playoffs':
            # Map playoff week to stage type
            playoff_stages = [
                StageType.WILD_CARD,
                StageType.DIVISIONAL,
                StageType.CONFERENCE_CHAMPIONSHIP,
                StageType.SUPER_BOWL
            ]
            stage_idx = min(week - 1, len(playoff_stages) - 1)
            stage_type = playoff_stages[stage_idx]
        elif phase_str == 'offseason':
            # Use canonical OFFSEASON_STAGES from stage_definitions
            # This ensures consistency with week_number property mapping
            stage_idx = min(week - 1, len(OFFSEASON_STAGES) - 1)
            stage_type = OFFSEASON_STAGES[stage_idx]
        else:
            # Default to Week 1
            stage_type = StageType.REGULAR_WEEK_1

        return Stage(
            stage_type=stage_type,
            season_year=loaded_season,  # Use loaded season from DB state
            completed=False
        )

    def _save_current_stage(self, stage: Stage) -> None:
        """Save current stage to dynasty_state."""
        # Map stage to phase and week
        phase_name = stage.phase.name.lower()
        week = stage.week_number or 1

        # Get current date from state or generate one
        # Use stage.season_year to ensure correct season is queried/saved
        state = self._dynasty_state_api.get_current_state(
            dynasty_id=self._dynasty_id,
            season=stage.season_year
        )

        current_date = state.get('current_date') if state else f"{stage.season_year}-09-01"

        # Update dynasty state
        self._dynasty_state_api.update_state(
            dynasty_id=self._dynasty_id,
            season=stage.season_year,
            current_date=current_date,
            current_phase=phase_name,
            current_week=week
        )

    def get_current_stage(self) -> Optional[Stage]:
        """Public API to get current stage (used by jump_to_offseason)."""
        return self.current_stage

    def _verify_season_standings(self, season: int) -> None:
        """
        Ensure standings exist and are initialized for the given season.

        Called when transitioning to a new regular season to ensure
        standings are properly initialized to 0-0 for all teams.

        This provides defensive verification and self-healing:
        - If standings exist (32 teams), logs confirmation
        - If standings are missing or incomplete, initializes them to 0-0

        Args:
            season: Season year to verify standings for

        Raises:
            Exception if standings initialization fails
        """
        from database.unified_api import UnifiedDatabaseAPI

        # UnifiedDatabaseAPI expects a database path, not a connection
        # It will create its own connection pool
        api = UnifiedDatabaseAPI(self._db_path, self._dynasty_id)

        # Check if standings exist for this season
        conn = api._get_connection()
        cursor = conn.execute(
            '''SELECT COUNT(*) FROM standings
               WHERE dynasty_id = ? AND season = ? AND season_type = ?''',
            (self._dynasty_id, season, 'regular_season')
        )
        count = cursor.fetchone()[0]

        if count < 32:
            logger.warning(f"Only {count}/32 standings records for season {season}, initializing")
            api.standings_reset(season=season, season_type='regular_season')
            logger.info(f"Initialized 0-0 standings for all 32 teams in season {season}")
        else:
            logger.info(f"Standings verified for season {season}: {count} teams")
