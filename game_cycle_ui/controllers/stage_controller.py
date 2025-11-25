"""
Stage Controller for Game Cycle UI.

Thin controller connecting StageView to the game cycle backend.

Dynasty-First Architecture:
- Requires dynasty_id for all operations
- Passes dynasty context to backend StageController
"""

from typing import Optional, Dict, Any, List

from PySide6.QtCore import QObject, Signal

from src.game_cycle import Stage, StageType, SeasonPhase
from src.game_cycle.stage_controller import StageController as BackendStageController


class StageUIController(QObject):
    """
    UI Controller for stage-based progression.

    Connects the StageView to the backend StageController.
    Follows thin controller pattern - delegates to backend.

    Dynasty context (dynasty_id, season) is required and flows
    through to all backend operations.

    Signals:
        stage_changed: Emitted when current stage changes
        execution_complete: Emitted when stage execution finishes
        error_occurred: Emitted on errors
    """

    stage_changed = Signal(object)  # Stage
    execution_complete = Signal(dict)  # Result dict
    error_occurred = Signal(str)  # Error message

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        season: int = 2025,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)

        self._database_path = database_path
        self._dynasty_id = dynasty_id
        self._season = season

        # Backend controller with dynasty context
        self._backend = BackendStageController(
            db_path=database_path,
            dynasty_id=dynasty_id,
            season=season
        )

        # View reference (set by main window)
        self._view = None

    @property
    def dynasty_id(self) -> str:
        """Get current dynasty ID."""
        return self._dynasty_id

    @property
    def season(self) -> int:
        """Get current season."""
        return self._season

    def set_view(self, view):
        """Connect to the view."""
        self._view = view

        # Connect signals
        view.stage_advance_requested.connect(self.execute_current_stage)
        view.skip_to_playoffs_requested.connect(self._on_skip_to_playoffs)
        view.skip_to_offseason_requested.connect(self._on_skip_to_offseason)

        # Initial update
        self.refresh()

    @property
    def current_stage(self) -> Optional[Stage]:
        """Get current stage from backend."""
        return self._backend.current_stage

    def refresh(self):
        """Refresh view with current state."""
        # Initialize if not already done
        if not self._backend.is_initialized():
            self._backend.initialize(season_year=self._season, skip_preseason=True)

        stage = self.current_stage

        if self._view and stage:
            self._view.set_current_stage(stage)
            preview = self._backend.get_stage_preview()
            self._view.set_preview(preview)
            self._view.set_advance_enabled(True)

            # Update standings in view
            standings = self._backend.get_standings()
            self._view.set_standings(standings)

        if stage:
            self.stage_changed.emit(stage)

    def execute_current_stage(self):
        """Execute the current stage (simulate games/process events)."""
        stage = self.current_stage
        if stage is None:
            self.error_occurred.emit("No current stage")
            return

        try:
            # Execute stage via backend
            result = self._backend.execute_current_stage()

            if self._view:
                # Convert StageResult to dict for view
                result_dict = {
                    "stage_name": result.stage.display_name,
                    "games_played": result.games_played,
                    "events_processed": result.events_processed,
                    "errors": result.errors,
                    "success": result.success,
                }
                self._view.show_execution_result(result_dict)

            # Auto-advance if successful
            if result.can_advance:
                self._advance_to_next()

            self.execution_complete.emit(result_dict)

        except Exception as e:
            error_msg = f"Stage execution failed: {e}"
            self.error_occurred.emit(error_msg)
            if self._view:
                self._view.set_status(error_msg, is_error=True)
                self._view.set_advance_enabled(True)

    def _advance_to_next(self):
        """Advance to the next stage."""
        current = self.current_stage
        next_stage = self._backend.advance_to_next_stage()

        if next_stage:
            # Successfully advanced to next stage
            self.refresh()
        else:
            # End of season - start new year
            current_year = current.season_year if current else self._season
            new_year = current_year + 1

            if self._view:
                self._view.set_status(f"Season {current_year} complete! Starting {new_year} season...")

            # Start new season
            self._backend.start_new_season(new_year, skip_preseason=True)
            self._season = new_year
            self.refresh()

    def start_new_season(self, year: int, skip_preseason: bool = True):
        """Start a new season."""
        stage = self._backend.start_new_season(year, skip_preseason)
        self._season = year
        self.refresh()
        return stage

    def jump_to_stage(self, stage_type: StageType):
        """Jump to a specific stage (for testing/debugging)."""
        stage = self._backend.jump_to_stage(stage_type)
        self.refresh()
        return stage

    def get_stage_preview(self) -> Dict[str, Any]:
        """Get preview of current stage."""
        return self._backend.get_stage_preview()

    def get_standings(self) -> List[Dict[str, Any]]:
        """Get current standings."""
        return self._backend.get_standings()

    def get_playoff_bracket(self) -> Dict[str, Any]:
        """
        Get complete playoff bracket data for all rounds.

        Returns:
            Dict with:
                - season: int
                - wild_card: List of game dicts
                - divisional: List of game dicts
                - conference: List of game dicts
                - super_bowl: List of game dicts
        """
        from team_management.teams.team_loader import TeamDataLoader
        from database.unified_api import UnifiedDatabaseAPI

        team_loader = TeamDataLoader()

        # Use the backend's unified API
        unified_api = UnifiedDatabaseAPI(self._database_path, self._dynasty_id)

        bracket = {
            "season": self._season,
            "wild_card": [],
            "divisional": [],
            "conference": [],
            "super_bowl": [],
        }

        # Week mapping: 19=Wild Card, 20=Divisional, 21=Conference, 22=Super Bowl
        round_configs = [
            ("wild_card", 19),
            ("divisional", 20),
            ("conference", 21),
            ("super_bowl", 22),
        ]

        for round_name, week in round_configs:
            # Get games from the games table (results) for this playoff week
            games = unified_api.games_get_by_week(
                season=self._season,
                week=week,
                season_type="playoffs"
            )

            for game in games:
                home_team_id = game.get("home_team_id")
                away_team_id = game.get("away_team_id")
                home_score = game.get("home_score")
                away_score = game.get("away_score")

                # Get team info
                home_team = team_loader.get_team_by_id(home_team_id)
                away_team = team_loader.get_team_by_id(away_team_id)

                is_played = home_score is not None and away_score is not None
                winner_id = None
                if is_played:
                    winner_id = home_team_id if home_score > away_score else away_team_id

                # Build game data
                game_data = {
                    "home_team": {
                        "id": home_team_id,
                        "abbrev": home_team.abbreviation if home_team else f"T{home_team_id}",
                        "name": home_team.full_name if home_team else f"Team {home_team_id}",
                        "seed": game.get("home_seed", ""),
                    },
                    "away_team": {
                        "id": away_team_id,
                        "abbrev": away_team.abbreviation if away_team else f"T{away_team_id}",
                        "name": away_team.full_name if away_team else f"Team {away_team_id}",
                        "seed": game.get("away_seed", ""),
                    },
                    "home_score": home_score,
                    "away_score": away_score,
                    "is_played": is_played,
                    "winner_id": winner_id,
                }

                bracket[round_name].append(game_data)

        return bracket

    def get_offseason_preview(self) -> Dict[str, Any]:
        """
        Get preview data for the current offseason stage.

        Returns:
            Dict with stage preview data from OffseasonHandler.get_stage_preview()
        """
        stage = self.current_stage
        if stage is None or stage.phase != SeasonPhase.OFFSEASON:
            return {
                "stage_name": "Offseason",
                "description": "",
                "is_interactive": False,
            }

        return self._backend.get_stage_preview()

    def _on_skip_to_playoffs(self):
        """Skip to playoffs by simulating remaining regular season."""
        # Simulate all remaining regular season weeks
        while True:
            stage = self.current_stage
            if stage is None or stage.phase != SeasonPhase.REGULAR_SEASON:
                break

            result = self._backend.execute_current_stage()
            if result.can_advance:
                self._backend.advance_to_next_stage()
            else:
                break

        self.refresh()

    def _on_skip_to_offseason(self):
        """Skip to offseason by simulating remaining games."""
        # Simulate through playoffs
        while True:
            stage = self.current_stage
            if stage is None or stage.phase == SeasonPhase.OFFSEASON:
                break

            result = self._backend.execute_current_stage()
            if result.can_advance:
                self._backend.advance_to_next_stage()
            else:
                break

        self.refresh()
