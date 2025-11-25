"""
Stage Controller - Main orchestrator for stage-based progression.

Dynasty-First Architecture:
- Requires dynasty_id for all operations
- Uses production database APIs (DatabaseAPI, DynastyStateAPI)
- Uses production StandingsStore instead of custom standings manager
- Shares database with main.py (nfl_simulation.db)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Protocol

from .stage_definitions import Stage, StageType, SeasonPhase
from .handlers.regular_season import RegularSeasonHandler
from .handlers.playoffs import PlayoffHandler
from .handlers.offseason import OffseasonHandler


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
            db_path="path/to/nfl_simulation.db",
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
            db_path: Path to production database (nfl_simulation.db)
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

        self._current_stage: Optional[Stage] = None
        self._initialized = False

    @property
    def dynasty_id(self) -> str:
        """Get current dynasty ID."""
        return self._dynasty_id

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
            starting_stage = StageType.PRESEASON_WEEK_1

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

    def execute_current_stage(self) -> StageResult:
        """
        Execute all events/games for the current stage.

        Returns:
            StageResult with execution details
        """
        # DEBUG: Log execution start
        print(f"[DEBUG StageController] execute_current_stage() called")
        print(f"[DEBUG StageController] dynasty_id={self._dynasty_id}, season={self._season}")
        print(f"[DEBUG StageController] db_path={self._db_path}")

        stage = self.current_stage
        print(f"[DEBUG StageController] current_stage={stage}")

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
                next_stage=stage.next_stage() if can_advance else None
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

        Returns:
            The new current stage, or None if cannot advance
        """
        current = self.current_stage
        if current is None:
            return None

        next_stage = current.next_stage()
        if next_stage is None:
            return None

        self._current_stage = next_stage
        self._save_current_stage(next_stage)
        return next_stage

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
        """Get current standings for UI display as a flat list."""
        from team_management.teams.team_loader import TeamDataLoader

        # Use UnifiedDatabaseAPI to get standings
        standings_data = self._unified_api.standings_get(
            season=self._season,
            season_type="regular_season"
        )

        # Load team data for abbreviations
        team_loader = TeamDataLoader()

        # Transform complex standings into flat list for UI
        result = []
        overall = standings_data.get("overall", [])

        for item in overall:
            team_id = item.get("team_id")
            standing = item.get("standing")

            if standing is None:
                continue

            # Get team abbreviation
            team = team_loader.get_team_by_id(team_id)
            abbreviation = team.abbreviation if team else f"T{team_id}"

            # Calculate win percentage
            wins = standing.wins
            losses = standing.losses
            ties = standing.ties
            total_games = wins + losses + ties
            win_pct = f"{standing.win_percentage:.3f}" if total_games > 0 else ".000"

            # Calculate point differential
            point_diff = standing.points_for - standing.points_against

            result.append({
                "team_id": team_id,
                "abbreviation": abbreviation,
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "win_pct": win_pct,
                "point_diff": point_diff,
                "points_for": standing.points_for,
                "points_against": standing.points_against,
            })

        return result

    def _build_context(self) -> Dict[str, Any]:
        """Build execution context for handlers."""
        # Get user team ID from dynasty info
        dynasty_info = self._dynasty_db_api.get_dynasty_by_id(self._dynasty_id)
        user_team_id = dynasty_info.get('team_id', 1) if dynasty_info else 1

        return {
            "dynasty_id": self._dynasty_id,
            "season": self._season,
            "db_path": self._db_path,
            "unified_api": self._unified_api,
            "dynasty_state_api": self._dynasty_state_api,
            "user_team_id": user_team_id,
        }

    def _get_handler(self, phase: SeasonPhase) -> Optional[StageHandler]:
        """Get the handler for a season phase."""
        if phase == SeasonPhase.REGULAR_SEASON:
            return self._regular_season_handler
        elif phase == SeasonPhase.PLAYOFFS:
            return self._playoff_handler
        elif phase == SeasonPhase.OFFSEASON:
            return self._offseason_handler
        # Preseason handler not implemented yet
        return None

    def _load_current_stage(self) -> Optional[Stage]:
        """Load current stage from dynasty_state."""
        state = self._dynasty_state_api.get_current_state(
            dynasty_id=self._dynasty_id,
            season=self._season
        )

        if state is None:
            return None

        # Map phase string to SeasonPhase
        phase_str = state.get('current_phase', 'regular_season')
        week = state.get('current_week', 1)

        # Determine stage type from phase and week
        if phase_str == 'preseason':
            stage_type = StageType[f"PRESEASON_WEEK_{week}"]
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
            # Map offseason week to stage type
            offseason_stages = [
                StageType.OFFSEASON_RESIGNING,
                StageType.OFFSEASON_FREE_AGENCY,
                StageType.OFFSEASON_DRAFT,
                StageType.OFFSEASON_ROSTER_CUTS,
                StageType.OFFSEASON_TRAINING_CAMP,
                StageType.OFFSEASON_PRESEASON
            ]
            stage_idx = min(week - 1, len(offseason_stages) - 1)
            stage_type = offseason_stages[stage_idx]
        else:
            # Default to Week 1
            stage_type = StageType.REGULAR_WEEK_1

        return Stage(
            stage_type=stage_type,
            season_year=self._season,
            completed=False
        )

    def _save_current_stage(self, stage: Stage) -> None:
        """Save current stage to dynasty_state."""
        # Map stage to phase and week
        phase_name = stage.phase.name.lower()
        week = stage.week_number or 1

        # Get current date from state or generate one
        state = self._dynasty_state_api.get_current_state(
            dynasty_id=self._dynasty_id,
            season=self._season
        )

        current_date = state.get('current_date') if state else f"{self._season}-09-01"

        # Update dynasty state
        self._dynasty_state_api.update_state(
            dynasty_id=self._dynasty_id,
            season=self._season,
            current_date=current_date,
            current_phase=phase_name,
            current_week=week
        )
