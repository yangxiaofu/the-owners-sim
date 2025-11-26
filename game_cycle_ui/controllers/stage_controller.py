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
        user_team_id: int = 1,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)

        self._database_path = database_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._user_team_id = user_team_id

        # Backend controller with dynasty context
        self._backend = BackendStageController(
            db_path=database_path,
            dynasty_id=dynasty_id,
            season=season
        )

        # View reference (set by main window)
        self._view = None

        # Track user decisions for interactive stages
        self._user_decisions: Dict[int, str] = {}  # {player_id: "resign"|"release"} for re-signing
        self._fa_decisions: Dict[int, str] = {}    # {player_id: "sign"} for free agency

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

    # ========================================================================
    # Offseason Stage Support (Re-signing, Free Agency, etc.)
    # ========================================================================

    def set_offseason_view(self, offseason_view):
        """
        Connect to the offseason view for interactive stages.

        Args:
            offseason_view: OffseasonView instance
        """
        self._offseason_view = offseason_view

        # Connect signals for re-signing decisions
        offseason_view.player_resigned.connect(self._on_player_resigned)
        offseason_view.player_released.connect(self._on_player_released)

        # Connect signals for free agency decisions
        offseason_view.player_signed_fa.connect(self._on_fa_player_signed)

        # Process button
        offseason_view.process_stage_requested.connect(self._on_process_offseason_stage)

        # Connect draft signals
        offseason_view.prospect_drafted.connect(self._on_prospect_drafted)
        offseason_view.simulate_to_pick_requested.connect(self._on_simulate_to_pick)
        offseason_view.auto_draft_all_requested.connect(self._on_auto_draft_all)

        # Set user team ID in draft view
        draft_view = offseason_view.get_draft_view()
        draft_view.set_user_team_id(self._user_team_id)

        # Connect draft history round filter
        draft_view.round_filter_changed.connect(self._on_history_round_filter_changed)

    def _on_player_resigned(self, player_id: int):
        """Track user's re-sign decision."""
        self._user_decisions[player_id] = "resign"

    def _on_player_released(self, player_id: int):
        """Track user's release decision."""
        self._user_decisions[player_id] = "release"

    def _on_fa_player_signed(self, player_id: int):
        """Track user's free agency signing decision."""
        self._fa_decisions[player_id] = "sign"

    def _on_process_offseason_stage(self):
        """Process current offseason stage when user clicks Process button."""
        stage = self.current_stage
        if stage is None or stage.phase != SeasonPhase.OFFSEASON:
            self.error_occurred.emit("Not in offseason phase")
            return

        try:
            # Build context with user decisions
            context = {
                "dynasty_id": self._dynasty_id,
                "season": self._season,
                "user_team_id": self._user_team_id,
                "db_path": self._database_path,
                "user_decisions": self._user_decisions.copy(),  # Re-signing decisions
                "fa_decisions": self._fa_decisions.copy(),      # Free agency decisions
            }

            # Execute via backend with context
            result = self._backend.execute_current_stage(extra_context=context)

            # Show result summary
            if self._view:
                result_dict = {
                    "stage_name": result.stage.display_name,
                    "games_played": result.games_played,
                    "events_processed": result.events_processed,
                    "errors": result.errors,
                    "success": result.success,
                }
                self._view.show_execution_result(result_dict)

            # Clear decisions for next stage
            self._user_decisions.clear()
            self._fa_decisions.clear()

            # Auto-advance if successful
            if result.can_advance:
                self._advance_to_next()

            self.execution_complete.emit(result_dict)

        except Exception as e:
            error_msg = f"Offseason stage execution failed: {e}"
            self.error_occurred.emit(error_msg)
            if self._view:
                self._view.set_status(error_msg, is_error=True)

    def get_user_decisions(self) -> Dict[int, str]:
        """Get current re-signing decisions (for debugging)."""
        return self._user_decisions.copy()

    def clear_user_decisions(self):
        """Clear all re-signing decisions."""
        self._user_decisions.clear()

    def get_fa_decisions(self) -> Dict[int, str]:
        """Get current free agency signing decisions (for debugging)."""
        return self._fa_decisions.copy()

    def clear_fa_decisions(self):
        """Clear all free agency decisions."""
        self._fa_decisions.clear()

    # ========================================================================
    # Draft Stage Support
    # ========================================================================

    def _on_prospect_drafted(self, prospect_id: int):
        """
        Handle user's draft selection.

        Args:
            prospect_id: The selected prospect's ID
        """
        stage = self.current_stage
        if stage is None or stage.stage_type != StageType.OFFSEASON_DRAFT:
            self.error_occurred.emit("Not in draft stage")
            return

        try:
            # Build context with user's pick
            context = {
                "dynasty_id": self._dynasty_id,
                "season": self._season,
                "user_team_id": self._user_team_id,
                "db_path": self._database_path,
                "draft_decisions": {self._get_current_pick_number(): prospect_id},
            }

            # Execute draft pick via backend
            result = self._backend.execute_current_stage(extra_context=context)

            # Refresh the draft view with updated data
            self._refresh_draft_view()

            # Check if draft is complete
            if result.can_advance:
                self._advance_to_next()

        except Exception as e:
            error_msg = f"Draft pick failed: {e}"
            self.error_occurred.emit(error_msg)
            if self._view:
                self._view.set_status(error_msg, is_error=True)

    def _on_simulate_to_pick(self):
        """Simulate AI picks until user's next turn."""
        stage = self.current_stage
        if stage is None or stage.stage_type != StageType.OFFSEASON_DRAFT:
            self.error_occurred.emit("Not in draft stage")
            return

        try:
            # Build context for sim-to-pick mode
            context = {
                "dynasty_id": self._dynasty_id,
                "season": self._season,
                "user_team_id": self._user_team_id,
                "db_path": self._database_path,
                "sim_to_user_pick": True,  # Signal to sim until user's turn
            }

            # Execute via backend
            result = self._backend.execute_current_stage(extra_context=context)

            # Refresh the draft view
            self._refresh_draft_view()

            # Check if draft is complete
            if result.can_advance:
                self._advance_to_next()

        except Exception as e:
            error_msg = f"Draft simulation failed: {e}"
            self.error_occurred.emit(error_msg)
            if self._view:
                self._view.set_status(error_msg, is_error=True)

    def _on_auto_draft_all(self):
        """Auto-draft all remaining picks."""
        stage = self.current_stage
        if stage is None or stage.stage_type != StageType.OFFSEASON_DRAFT:
            self.error_occurred.emit("Not in draft stage")
            return

        try:
            # Build context for auto-complete mode
            context = {
                "dynasty_id": self._dynasty_id,
                "season": self._season,
                "user_team_id": self._user_team_id,
                "db_path": self._database_path,
                "auto_complete": True,
            }

            # Execute via backend
            result = self._backend.execute_current_stage(extra_context=context)

            # Show result summary
            if self._view:
                result_dict = {
                    "stage_name": result.stage.display_name,
                    "games_played": result.games_played,
                    "events_processed": result.events_processed,
                    "errors": result.errors,
                    "success": result.success,
                }
                self._view.show_execution_result(result_dict)

            # Refresh draft view to show complete state
            self._refresh_draft_view()

            # Auto-advance since draft is complete
            if result.can_advance:
                self._advance_to_next()

            self.execution_complete.emit(result_dict)

        except Exception as e:
            error_msg = f"Auto-draft failed: {e}"
            self.error_occurred.emit(error_msg)
            if self._view:
                self._view.set_status(error_msg, is_error=True)

    def _refresh_draft_view(self):
        """Refresh the draft view with current draft state."""
        if not hasattr(self, "_offseason_view"):
            return

        # Get fresh preview data
        preview = self._backend.get_stage_preview()

        # Update draft view
        draft_view = self._offseason_view.get_draft_view()

        prospects = preview.get("prospects", [])
        if prospects:
            draft_view.set_prospects(prospects)

        draft_view.set_current_pick(preview.get("current_pick"))
        draft_progress = preview.get("draft_progress", {})
        draft_view.set_draft_progress(
            draft_progress.get("picks_made", 0),
            draft_progress.get("total_picks", 224)
        )

        draft_history = preview.get("draft_history", [])
        if draft_history:
            draft_view.set_draft_history(draft_history)

        # Check if draft is complete
        if preview.get("draft_complete", False):
            draft_view.set_draft_complete()

    def _get_current_pick_number(self) -> int:
        """Get the current overall pick number."""
        preview = self._backend.get_stage_preview()
        current_pick = preview.get("current_pick", {})
        return current_pick.get("overall_pick", 1)

    def _on_history_round_filter_changed(self, round_filter: Optional[int]):
        """
        Handle draft history round filter change.

        Args:
            round_filter: Round number (1-7) or None for all rounds
        """
        if not hasattr(self, "_offseason_view"):
            return

        try:
            # Get DraftService to fetch filtered history
            from src.game_cycle.services.draft_service import DraftService

            draft_service = DraftService(
                db_path=self._database_path,
                dynasty_id=self._dynasty_id,
                season=self._season
            )

            # Get filtered draft history
            history = draft_service.get_draft_history(
                round_filter=round_filter,
                limit=100
            )

            # Update draft view with filtered history
            draft_view = self._offseason_view.get_draft_view()
            draft_view.set_draft_history(history)

        except Exception as e:
            self.error_occurred.emit(f"Failed to filter draft history: {e}")
