"""
Stage Controller for Game Cycle UI.

Thin controller connecting StageView to the game cycle backend.

Dynasty-First Architecture:
- Requires dynasty_id for all operations
- Passes dynasty context to backend StageController
"""

from typing import Optional, Dict, Any, List

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from game_cycle import Stage, StageType, SeasonPhase
from game_cycle.stage_controller import StageController as BackendStageController


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
    season_started = Signal()  # Emitted when offseason ends and new season begins
    ir_action_complete = Signal(bool, str)  # success, message - for IR operations
    awards_calculated = Signal()  # Emitted after OFFSEASON_HONORS - UI should show awards
    owner_stage_ready = Signal()  # Emitted when entering OFFSEASON_OWNER - UI should show owner view
    super_bowl_completed = Signal(dict, dict)  # super_bowl_result, season_awards - show results dialog

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
        self._fa_decisions: Dict[int, str] = {}    # {player_id: "sign"} for free agency (legacy)
        self._tag_decision: Optional[Dict] = None  # {"player_id": X, "tag_type": "franchise"|"transition"}
        self._cut_decisions: Dict[int, bool] = {}  # {player_id: use_june_1} for roster cuts
        self._draft_direction = None  # Owner's draft strategy (Phase 1)

        # Wave-based Free Agency controller (Milestone 8 - SoC)
        # Created lazily in set_offseason_view() for proper DI
        self._fa_controller = None

    @property
    def dynasty_id(self) -> str:
        """Get current dynasty ID."""
        return self._dynasty_id

    def set_simulation_mode(self, mode: str) -> None:
        """
        Set simulation mode for game execution.

        Args:
            mode: "instant" for fast mock stats, "full" for play-by-play simulation

        The mode is stored in the backend controller and passed to handlers
        via the execution context.
        """
        self._backend.set_simulation_mode(mode)
        if self._view:
            mode_label = "Full Sim" if mode == "full" else "Instant"
            self._view.set_status(f"Simulation mode: {mode_label}")

    @property
    def season(self) -> int:
        """Get current season from stage (single source of truth)."""
        stage = self.current_stage
        if stage:
            return stage.season_year
        return self._season  # Fallback only if no stage

    def set_view(self, view):
        """Connect to the view."""
        self._view = view

        # Connect signals
        view.stage_advance_requested.connect(self.execute_current_stage)
        view.skip_to_playoffs_requested.connect(self._on_skip_to_playoffs)
        view.skip_to_offseason_requested.connect(self._on_skip_to_offseason)
        view.week_navigation_requested.connect(self._on_week_navigation)

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

            # Update week navigation state for regular season and playoffs
            if stage.phase == SeasonPhase.REGULAR_SEASON:
                week_number = preview.get("week", 1)
                self._view.set_week_navigation_state(week_number, week_number)
                self._view.set_week_navigation_visible(True)
            elif stage.phase == SeasonPhase.PLAYOFFS:
                # Map playoff stage to week number (19-22)
                playoff_week_map = {
                    StageType.WILD_CARD: 19,
                    StageType.DIVISIONAL: 20,
                    StageType.CONFERENCE_CHAMPIONSHIP: 21,
                    StageType.SUPER_BOWL: 22,
                }
                week_number = playoff_week_map.get(stage.stage_type, 19)
                self._view.set_week_navigation_state(week_number, week_number)
                self._view.set_week_navigation_visible(True)
            else:
                # Hide week navigation during offseason
                self._view.set_week_navigation_visible(False)

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

                # Store GameResult objects for play-by-play access (Phase 1)
                if result.games_played:
                    self._view.store_game_results(result.games_played)

            # Auto-advance if successful
            if result.can_advance:
                # Special case: OFFSEASON_HONORS - don't auto-advance, show awards first
                if stage.stage_type == StageType.OFFSEASON_HONORS:
                    # Emit signal so main window can show awards tab
                    self.awards_calculated.emit()
                    # Don't auto-advance - user must click "Continue" after viewing awards
                # Special case: OFFSEASON_OWNER - don't auto-advance, show owner view
                elif stage.stage_type == StageType.OFFSEASON_OWNER:
                    # Emit signal so main window can show owner view tab
                    self.owner_stage_ready.emit()
                    # Don't auto-advance - user must click "Continue" after owner decisions
                elif stage.stage_type.name.startswith('REGULAR_SEASON_WEEK'):
                    # Check for IR activations before advancing (regular season only)
                    # Extract week number from stage
                    week_number = stage.stage_number
                    ir_shown = self.check_and_show_ir_activations(week_number)
                    # Note: If IR UI is shown, user must complete it before advancing
                    # The view's signals will hide it and then we can advance
                    if not ir_shown:
                        # No IR activations needed, proceed with auto-advance
                        self._advance_to_next()
                else:
                    # Not regular season or honors, proceed with normal auto-advance
                    self._advance_to_next()

            self.execution_complete.emit(result_dict)

        except Exception as e:
            # Restore cursor on error (in case view set it)
            QApplication.restoreOverrideCursor()

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

    def advance_stage(self):
        """
        Advance to the next stage without executing the current stage.

        Used after OFFSEASON_HONORS when the user has finished viewing awards
        and clicks Continue - the stage was already executed, now we just need
        to advance to Franchise Tag.
        """
        stage = self._backend.advance_to_next_stage()
        if stage:
            self.stage_changed.emit(stage)
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

        Reads ONLY from playoff_bracket table - no fallback.
        If playoff_bracket is empty, placeholders are generated from standings.

        Raises:
            Exception: If database query fails (no silent fallback)

        Returns:
            Dict with:
                - season: int
                - wild_card: List of game dicts
                - divisional: List of game dicts
                - conference: List of game dicts
                - super_bowl: List of game dicts
        """
        from team_management.teams.team_loader import TeamDataLoader
        from game_cycle.database.connection import GameCycleDatabase
        from game_cycle.database.playoff_bracket_api import PlayoffBracketAPI

        team_loader = TeamDataLoader()

        # Use current stage's season year (single source of truth)
        stage = self.current_stage
        current_season = stage.season_year if stage else self._season

        bracket = {
            "season": current_season,
            "wild_card": [],
            "divisional": [],
            "conference": [],
            "super_bowl": [],
        }

        # Read from playoff_bracket table with dynasty/season isolation
        # No fallback - playoff_bracket table is the single source of truth
        db = GameCycleDatabase()  # Uses default game_cycle.db
        api = PlayoffBracketAPI(db)

        for round_name in ["wild_card", "divisional", "conference", "super_bowl"]:
            matchups = api.get_matchups_for_round(
                self._dynasty_id, current_season, round_name
            )

            for matchup in matchups:
                # higher_seed = home team, lower_seed = away team
                home_team_id = matchup.higher_seed
                away_team_id = matchup.lower_seed
                home_score = matchup.home_score
                away_score = matchup.away_score
                winner_id = matchup.winner

                # Get team info
                home_team = team_loader.get_team_by_id(home_team_id)
                away_team = team_loader.get_team_by_id(away_team_id)

                is_played = winner_id is not None

                # Calculate seed numbers based on playoff bracket structure
                home_seed = self._get_team_seed(home_team_id, matchup.conference)
                away_seed = self._get_team_seed(away_team_id, matchup.conference)

                # Generate consistent game_id for box score lookup
                game_id = f"playoff_{current_season}_{round_name}_{home_team_id}_{away_team_id}"

                game_data = {
                    "game_id": game_id,  # Required for box score double-click
                    "home_team": {
                        "id": home_team_id,
                        "abbrev": home_team.abbreviation if home_team else f"T{home_team_id}",
                        "name": home_team.full_name if home_team else f"Team {home_team_id}",
                        "seed": home_seed,
                    },
                    "away_team": {
                        "id": away_team_id,
                        "abbrev": away_team.abbreviation if away_team else f"T{away_team_id}",
                        "name": away_team.full_name if away_team else f"Team {away_team_id}",
                        "seed": away_seed,
                    },
                    "home_score": home_score,
                    "away_score": away_score,
                    "is_played": is_played,
                    "winner_id": winner_id,
                    "is_placeholder": False,  # Real game from database
                }

                bracket[round_name].append(game_data)

        # Generate placeholders for empty future rounds
        bracket = self._add_bracket_placeholders(bracket, current_season)
        return bracket

    def _get_team_seed(self, team_id: int, conference: str) -> str:
        """
        Get the playoff seed number for a team.

        Uses cached seeding data or calculates from standings.
        """
        # For Super Bowl, seeds don't apply in the same way
        if conference == "SUPER_BOWL":
            return ""

        try:
            # Use PlayoffSeeder to get accurate seeding
            from playoff_system.playoff_seeder import PlayoffSeeder
            from database.unified_api import UnifiedDatabaseAPI

            stage = self.current_stage
            current_season = stage.season_year if stage else self._season

            unified_api = UnifiedDatabaseAPI(self._database_path, self._dynasty_id)
            seeder = PlayoffSeeder()

            standings_data = unified_api.standings_get(current_season)

            # Build standings dict
            standings_dict = {}
            for item in standings_data.get('overall', []):
                tid = item.get('team_id')
                standing = item.get('standing')
                if tid and standing:
                    standings_dict[tid] = standing

            seeding = seeder.calculate_seeding(standings_dict, season=current_season, week=18)

            # Get seeds for the conference
            if conference == "AFC":
                conf_seeds = seeding.afc.seeds
            else:
                conf_seeds = seeding.nfc.seeds

            # Find the team's seed
            for i, seed in enumerate(conf_seeds):
                if seed.team_id == team_id:
                    return str(i + 1)

            return ""
        except Exception:
            return ""

    def _get_playoff_bracket_from_games(self, current_season: int) -> Dict[str, Any]:
        """
        Legacy method to get bracket from games table.

        Used as fallback when playoff_bracket table is empty.
        """
        from team_management.teams.team_loader import TeamDataLoader
        from database.unified_api import UnifiedDatabaseAPI

        team_loader = TeamDataLoader()
        unified_api = UnifiedDatabaseAPI(self._database_path, self._dynasty_id)

        bracket = {
            "season": current_season,
            "wild_card": [],
            "divisional": [],
            "conference": [],
            "super_bowl": [],
        }

        round_configs = [
            ("wild_card", 19),
            ("divisional", 20),
            ("conference", 21),
            ("super_bowl", 22),
        ]

        for round_name, week in round_configs:
            games = unified_api.games_get_by_week(
                season=current_season,
                week=week,
                season_type="playoffs"
            )

            for game in games:
                home_team_id = game.get("home_team_id")
                away_team_id = game.get("away_team_id")
                home_score = game.get("home_score")
                away_score = game.get("away_score")

                home_team = team_loader.get_team_by_id(home_team_id)
                away_team = team_loader.get_team_by_id(away_team_id)

                is_played = home_score is not None and away_score is not None
                winner_id = None
                if is_played:
                    winner_id = home_team_id if home_score > away_score else away_team_id

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
                    "is_placeholder": False,  # Real game from database
                }

                bracket[round_name].append(game_data)

        return bracket

    def _add_bracket_placeholders(self, bracket: Dict[str, Any], season: int) -> Dict[str, Any]:
        """
        Add placeholder entries for empty future rounds.

        Shows the bracket structure with TBD for unknown matchups.
        """
        # Get #1 seeds for divisional placeholders
        seed_1_afc, seed_1_nfc = self._get_top_seeds(season)

        # If wild_card is empty but we're in playoffs, add placeholders
        if not bracket["wild_card"]:
            bracket["wild_card"] = self._generate_wild_card_placeholders(season)

        # If divisional is empty but we're in playoffs, add placeholders
        if not bracket["divisional"]:
            bracket["divisional"] = self._generate_divisional_placeholders(
                bracket["wild_card"], seed_1_afc, seed_1_nfc
            )

        # If conference is empty, add placeholders
        if not bracket["conference"]:
            bracket["conference"] = self._generate_conference_placeholders()

        # If super_bowl is empty, add placeholder
        if not bracket["super_bowl"]:
            bracket["super_bowl"] = self._generate_super_bowl_placeholder()

        return bracket

    def _get_top_seeds(self, season: int) -> tuple:
        """Get #1 seeds for AFC and NFC."""
        try:
            from playoff_system.playoff_seeder import PlayoffSeeder
            from database.unified_api import UnifiedDatabaseAPI
            from team_management.teams.team_loader import TeamDataLoader

            unified_api = UnifiedDatabaseAPI(self._database_path, self._dynasty_id)
            seeder = PlayoffSeeder()
            team_loader = TeamDataLoader()

            standings_data = unified_api.standings_get(season)
            standings_dict = {}
            for item in standings_data.get('overall', []):
                tid = item.get('team_id')
                standing = item.get('standing')
                if tid and standing:
                    standings_dict[tid] = standing

            if not standings_dict:
                return (None, None)

            seeding = seeder.calculate_seeding(standings_dict, season=season, week=18)

            afc_1_id = seeding.afc.seeds[0].team_id if seeding.afc.seeds else None
            nfc_1_id = seeding.nfc.seeds[0].team_id if seeding.nfc.seeds else None

            afc_1_team = team_loader.get_team_by_id(afc_1_id) if afc_1_id else None
            nfc_1_team = team_loader.get_team_by_id(nfc_1_id) if nfc_1_id else None

            afc_1 = {
                "id": afc_1_id,
                "abbrev": afc_1_team.abbreviation if afc_1_team else "AFC #1",
                "name": afc_1_team.full_name if afc_1_team else "AFC #1 Seed",
                "seed": "1"
            } if afc_1_id else None

            nfc_1 = {
                "id": nfc_1_id,
                "abbrev": nfc_1_team.abbreviation if nfc_1_team else "NFC #1",
                "name": nfc_1_team.full_name if nfc_1_team else "NFC #1 Seed",
                "seed": "1"
            } if nfc_1_id else None

            return (afc_1, nfc_1)
        except Exception:
            return (None, None)

    def _generate_wild_card_placeholders(self, season: int) -> List[Dict[str, Any]]:
        """
        Generate Wild Card matchup placeholders using playoff seeding.

        Creates 6 matchups: 3 per conference (#2 vs #7, #3 vs #6, #4 vs #5)
        """
        from playoff_system.playoff_seeder import PlayoffSeeder
        from database.unified_api import UnifiedDatabaseAPI
        from team_management.teams.team_loader import TeamDataLoader

        team_loader = TeamDataLoader()
        placeholders = []

        try:
            unified_api = UnifiedDatabaseAPI(self._database_path, self._dynasty_id)
            seeder = PlayoffSeeder()

            standings_data = unified_api.standings_get(season)
            standings_dict = {}
            for item in standings_data.get('overall', []):
                tid = item.get('team_id')
                standing = item.get('standing')
                if tid and standing:
                    standings_dict[tid] = standing

            seeding = seeder.calculate_seeding(standings_dict, season=season, week=18)

            # Wild Card matchups: #2 vs #7, #3 vs #6, #4 vs #5
            matchup_pairs = [(2, 7), (3, 6), (4, 5)]

            for conference, seeds_list in [("AFC", seeding.afc.seeds), ("NFC", seeding.nfc.seeds)]:
                if len(seeds_list) < 7:
                    continue

                for higher_idx, lower_idx in matchup_pairs:
                    higher_seed = seeds_list[higher_idx - 1]  # 0-indexed
                    lower_seed = seeds_list[lower_idx - 1]

                    higher_team = team_loader.get_team_by_id(higher_seed.team_id)
                    lower_team = team_loader.get_team_by_id(lower_seed.team_id)

                    placeholders.append({
                        "home_team": {
                            "id": higher_seed.team_id,
                            "abbrev": higher_team.abbreviation if higher_team else f"#{higher_idx}",
                            "name": higher_team.full_name if higher_team else f"{conference} #{higher_idx}",
                            "seed": str(higher_idx),
                        },
                        "away_team": {
                            "id": lower_seed.team_id,
                            "abbrev": lower_team.abbreviation if lower_team else f"#{lower_idx}",
                            "name": lower_team.full_name if lower_team else f"{conference} #{lower_idx}",
                            "seed": str(lower_idx),
                        },
                        "home_score": None,
                        "away_score": None,
                        "is_played": False,
                        "is_placeholder": True,
                        "winner_id": None,
                    })

        except Exception as e:
            print(f"[StageUIController] Error generating wild card placeholders: {e}")
            # Return empty list - UI will show generic placeholders

        return placeholders

    def _generate_divisional_placeholders(
        self,
        wild_card_games: List[Dict],
        seed_1_afc: Optional[Dict],
        seed_1_nfc: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """Generate Divisional round placeholders."""
        placeholders = []

        # AFC Divisional (2 games)
        # Game 1: #1 seed vs lowest remaining WC winner
        placeholders.append({
            "home_team": seed_1_afc or {"id": None, "abbrev": "#1 AFC", "name": "AFC #1 Seed", "seed": "1"},
            "away_team": {"id": None, "abbrev": "TBD", "name": "Lowest AFC WC Winner", "seed": "?"},
            "home_score": None,
            "away_score": None,
            "is_played": False,
            "is_placeholder": True,
            "winner_id": None,
        })
        # Game 2: Other two WC winners
        placeholders.append({
            "home_team": {"id": None, "abbrev": "TBD", "name": "Higher AFC WC Winner", "seed": "?"},
            "away_team": {"id": None, "abbrev": "TBD", "name": "Lower AFC WC Winner", "seed": "?"},
            "home_score": None,
            "away_score": None,
            "is_played": False,
            "is_placeholder": True,
            "winner_id": None,
        })

        # NFC Divisional (2 games)
        placeholders.append({
            "home_team": seed_1_nfc or {"id": None, "abbrev": "#1 NFC", "name": "NFC #1 Seed", "seed": "1"},
            "away_team": {"id": None, "abbrev": "TBD", "name": "Lowest NFC WC Winner", "seed": "?"},
            "home_score": None,
            "away_score": None,
            "is_played": False,
            "is_placeholder": True,
            "winner_id": None,
        })
        placeholders.append({
            "home_team": {"id": None, "abbrev": "TBD", "name": "Higher NFC WC Winner", "seed": "?"},
            "away_team": {"id": None, "abbrev": "TBD", "name": "Lower NFC WC Winner", "seed": "?"},
            "home_score": None,
            "away_score": None,
            "is_played": False,
            "is_placeholder": True,
            "winner_id": None,
        })

        return placeholders

    def _generate_conference_placeholders(self) -> List[Dict[str, Any]]:
        """Generate Conference Championship placeholders."""
        return [
            {
                "home_team": {"id": None, "abbrev": "TBD", "name": "AFC Div Winner 1", "seed": "?"},
                "away_team": {"id": None, "abbrev": "TBD", "name": "AFC Div Winner 2", "seed": "?"},
                "home_score": None,
                "away_score": None,
                "is_played": False,
                "is_placeholder": True,
                "winner_id": None,
            },
            {
                "home_team": {"id": None, "abbrev": "TBD", "name": "NFC Div Winner 1", "seed": "?"},
                "away_team": {"id": None, "abbrev": "TBD", "name": "NFC Div Winner 2", "seed": "?"},
                "home_score": None,
                "away_score": None,
                "is_played": False,
                "is_placeholder": True,
                "winner_id": None,
            },
        ]

    def _generate_super_bowl_placeholder(self) -> List[Dict[str, Any]]:
        """Generate Super Bowl placeholder."""
        return [{
            "home_team": {"id": None, "abbrev": "AFC", "name": "AFC Champion", "seed": ""},
            "away_team": {"id": None, "abbrev": "NFC", "name": "NFC Champion", "seed": ""},
            "home_score": None,
            "away_score": None,
            "is_played": False,
            "is_placeholder": True,
            "winner_id": None,
        }]

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
        """Skip directly to offseason without simulating games."""
        try:
            # Use the fast-skip backend method
            new_stage = self._backend.jump_to_offseason()

            # Refresh UI to show offseason stage
            self.refresh()

            # Log success
            print(f"[UI] Jumped to offseason: {new_stage.display_name}")

        except Exception as e:
            # Show error dialog if skip fails
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self._view,
                "Skip Failed",
                f"Failed to skip to offseason:\n{str(e)}"
            )
            print(f"[ERROR] Skip to offseason failed: {e}")

    def _on_week_navigation(self, week_number: int):
        """
        Handle week navigation request from view.

        Args:
            week_number: Week to display (1-22, includes playoff weeks 19-22)
        """
        stage = self.current_stage
        if stage is None:
            return

        # Allow navigation during regular season and playoffs
        if stage.phase not in (SeasonPhase.REGULAR_SEASON, SeasonPhase.PLAYOFFS):
            return

        try:
            # Get the RegularSeasonHandler to fetch preview for the requested week
            # (it handles both regular season 1-18 and playoff weeks 19-22)
            from game_cycle.handlers.regular_season import RegularSeasonHandler
            from database.unified_api import UnifiedDatabaseAPI

            # Build context
            unified_api = UnifiedDatabaseAPI(self._database_path, self._dynasty_id)
            context = {
                "dynasty_id": self._dynasty_id,
                "season": stage.season_year,
                "unified_api": unified_api,
            }

            # Get preview for the requested week
            handler = RegularSeasonHandler()
            preview = handler.get_week_preview_for_week(week_number, context)

            # Update the view with the preview
            if self._view:
                self._view.set_preview(preview)

        except Exception as e:
            print(f"[StageUIController] Error navigating to week {week_number}: {e}")
            self.error_occurred.emit(f"Failed to load week {week_number}")

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

        # Connect signals for free agency decisions (sign and unsign)
        offseason_view.player_signed_fa.connect(self._on_fa_player_signed)
        offseason_view.player_unsigned_fa.connect(self._on_fa_player_unsigned)

        # Connect franchise tag signal
        offseason_view.tag_applied.connect(self._on_tag_applied)

        # Connect roster cuts signal
        offseason_view.player_cut.connect(self._on_player_cut)

        # Process button
        offseason_view.process_stage_requested.connect(self._on_process_offseason_stage)

        # Connect draft signals
        offseason_view.prospect_drafted.connect(self._on_prospect_drafted)
        offseason_view.simulate_to_pick_requested.connect(self._on_simulate_to_pick)
        offseason_view.auto_draft_all_requested.connect(self._on_auto_draft_all)

        # Set user team ID in draft view
        draft_view = offseason_view.get_draft_view()
        draft_view.set_user_team_id(self._user_team_id)

        # Set team context for draft direction dialog (Phase 2)
        draft_view.set_team_context(
            season=self._season,
            dynasty_id=self._dynasty_id,
            db_path=self._database_path
        )

        # Set user team ID in training camp view
        training_camp_view = offseason_view.get_training_camp_view()
        training_camp_view.set_user_team_id(self._user_team_id)

        # Connect draft history round filter
        draft_view.round_filter_changed.connect(self._on_history_round_filter_changed)

        # Connect draft direction signal (Phase 1)
        draft_view.draft_direction_changed.connect(self._on_draft_direction_changed)

        # Create and connect wave-based Free Agency controller (Milestone 8 - SoC)
        from .free_agency_controller import FreeAgencyUIController
        self._fa_controller = FreeAgencyUIController(
            backend=self._backend,
            dynasty_id=self._dynasty_id,
            season=self._season,
            user_team_id=self._user_team_id,
            db_path=self._database_path,
            parent=self
        )
        fa_view = offseason_view.get_free_agency_view()
        self._fa_controller.connect_view(fa_view)

        # Connect wave button execution signals
        self._fa_controller.execution_complete.connect(self._on_fa_wave_executed)
        self._fa_controller.error_occurred.connect(self._on_fa_wave_error)

    def _on_player_resigned(self, player_id: int):
        """Track user's re-sign decision and refresh cap display."""
        self._user_decisions[player_id] = "resign"
        self._refresh_cap_display_with_pending()

    def _on_player_released(self, player_id: int):
        """Track user's release decision and refresh cap display."""
        self._user_decisions[player_id] = "release"
        self._refresh_cap_display_with_pending()

    def _refresh_cap_display_with_pending(self):
        """Refresh cap display accounting for pending re-sign decisions."""
        if not hasattr(self, "_offseason_view") or not self._offseason_view:
            return

        stage = self.current_stage
        if not stage or stage.stage_type != StageType.OFFSEASON_RESIGNING:
            return

        try:
            # Get base cap data from handler
            preview = self._backend.get_stage_preview()
            cap_data = preview.get("cap_data", {})

            # Calculate pending cap impact from user decisions
            pending_cap_hit = self._calculate_pending_cap_hit(preview)

            # Add pending info to cap_data
            cap_data["pending_spending"] = pending_cap_hit
            available = cap_data.get("available_space", 0)
            projected = available - pending_cap_hit
            cap_data["projected_available"] = projected

            # Add over-cap validation flags
            cap_data["is_over_cap"] = projected < 0
            cap_data["over_cap_amount"] = abs(projected) if projected < 0 else 0

            # Update the view
            resigning_view = self._offseason_view.get_resigning_view()
            resigning_view.set_cap_data(cap_data)

        except Exception as e:
            print(f"[StageUIController] Error refreshing cap display: {e}")

    def _calculate_pending_cap_hit(self, preview: Dict[str, Any]) -> int:
        """
        Calculate total cap hit from pending re-sign decisions.

        Uses the pre-calculated estimated_year1_cap_hit from preview data,
        which accurately reflects the Year 1 cap impact of new contracts.
        Falls back to estimated_aav for backwards compatibility.
        """
        total = 0
        expiring_players = preview.get("expiring_players", [])

        # Build lookup by player_id
        player_lookup = {p.get("player_id"): p for p in expiring_players}

        for player_id, decision in self._user_decisions.items():
            if decision == "resign":
                player = player_lookup.get(player_id)
                if player:
                    # Use Year 1 cap hit for accurate projection
                    # Falls back to AAV if year1 cap hit not available
                    total += player.get("estimated_year1_cap_hit", player.get("estimated_aav", 0))

        return total

    def _on_player_cut(self, player_id: int, use_june_1: bool):
        """Track user's roster cut decision."""
        self._cut_decisions[player_id] = use_june_1

    def _on_fa_player_signed(self, player_id: int):
        """Track user's free agency signing decision and refresh cap display."""
        self._fa_decisions[player_id] = "sign"
        self._refresh_fa_cap_display_with_pending()

    def _on_fa_player_unsigned(self, player_id: int):
        """Remove player from pending free agency signings and refresh cap display."""
        self._fa_decisions.pop(player_id, None)
        self._refresh_fa_cap_display_with_pending()

    def _refresh_fa_cap_display_with_pending(self):
        """Refresh Free Agency cap display with pending signing impact."""
        if not hasattr(self, "_offseason_view") or not self._offseason_view:
            return

        stage = self.current_stage
        if not stage or stage.stage_type != StageType.OFFSEASON_FREE_AGENCY:
            return

        try:
            # Get base cap data and free agents list from preview
            preview = self._backend.get_stage_preview()
            cap_data = preview.get("cap_data", {})
            available = cap_data.get("available_space", 0)

            # Calculate pending cap hit from signed free agents
            pending_cap_hit = self._calculate_fa_pending_cap_hit(preview)
            projected = available - pending_cap_hit

            # Update the view with projected cap
            fa_view = self._offseason_view.get_free_agency_view()
            fa_view.set_projected_cap(projected)

        except Exception as e:
            print(f"[StageUIController] Error refreshing FA cap display: {e}")

    def _calculate_fa_pending_cap_hit(self, preview: Dict[str, Any]) -> int:
        """
        Calculate total cap hit from pending free agent signings.

        Uses estimated_aav from free agent data.
        """
        total = 0
        free_agents = preview.get("free_agents", [])

        # Build lookup by player_id
        fa_lookup = {fa.get("player_id"): fa for fa in free_agents}

        for player_id in self._fa_decisions.keys():
            fa = fa_lookup.get(player_id)
            if fa:
                estimated_aav = fa.get("estimated_aav", 0)
                total += estimated_aav

        return total

    def _refresh_fa_wave_display(self):
        """Refresh FA view with updated wave state after processing."""
        if not hasattr(self, "_offseason_view") or not self._offseason_view:
            return

        try:
            # Get fresh preview data with wave state
            preview = self._backend.get_stage_preview()

            # Update FA view via the dedicated controller
            if self._fa_controller:
                self._fa_controller.refresh_view(preview)

            # Get FA view reference
            fa_view = self._offseason_view.get_free_agency_view()

            # CRITICAL FIX: Explicitly update wave header
            # This ensures the header updates even if refresh_view doesn't
            wave_state = preview.get("wave_state", {})
            if wave_state and hasattr(fa_view, 'set_wave_info'):
                fa_view.set_wave_info(
                    wave=wave_state.get("current_wave", 0),
                    wave_name=wave_state.get("wave_name", ""),
                    day=wave_state.get("current_day", 1),
                    days_total=wave_state.get("days_in_wave", 1),
                )

            # Also update the free agents list
            free_agents = preview.get("free_agents", [])
            if free_agents and hasattr(fa_view, 'set_free_agents'):
                fa_view.set_free_agents(free_agents)

            # Update cap data
            cap_data = preview.get("cap_data", {})
            if cap_data and hasattr(fa_view, 'set_cap_data'):
                fa_view.set_cap_data(cap_data)

        except Exception as e:
            print(f"[StageUIController] Error refreshing FA wave display: {e}")

    def _on_fa_wave_executed(self, result_dict: Dict[str, Any]):
        """
        Handle wave action execution from FA controller.

        Called when user clicks wave control buttons (Process Day, Process Wave).

        Args:
            result_dict: Execution result with stage_name, events_processed, success, can_advance
        """
        # Show execution result in main view
        if self._view:
            self._view.show_execution_result(result_dict)

        # Get fresh preview to update all UI elements
        preview = self._backend.get_stage_preview()

        # Update OffseasonView header (white section at top)
        if self._offseason_view and preview:
            stage_name = preview.get("stage_name", "Free Agency")
            description = preview.get("description", "")
            self._offseason_view.stage_label.setText(stage_name)
            self._offseason_view.description_label.setText(description)

        # Check if wave completed - show results dialog if user had activity
        wave_state = preview.get("wave_state", {})
        print(f"[DEBUG StageUIController] Preview wave_state: {wave_state}")
        current_wave = wave_state.get("current_wave", 0)
        wave_complete = wave_state.get("wave_complete", False)
        print(f"[DEBUG StageUIController] Wave check: current_wave={current_wave}, wave_complete={wave_complete}")
        print(f"[DEBUG StageUIController] Dialog check: wave_complete={wave_complete}, wave_advanced={result_dict.get('wave_advanced')}, user_signings={len(result_dict.get('user_signings', []))}, user_lost_bids={len(result_dict.get('user_lost_bids', []))}")

        if result_dict.get("wave_advanced"):
            user_signings = result_dict.get("user_signings", [])
            user_lost_bids = result_dict.get("user_lost_bids", [])

            # Only show dialog if user had offers pending
            if user_signings or user_lost_bids:
                from game_cycle_ui.dialogs.wave_results_dialog import WaveResultsDialog

                dialog_data = {
                    "wave_name": wave_state.get("wave_name", "Unknown Wave"),
                    "user_signings": user_signings,
                    "user_lost_bids": user_lost_bids,
                    "pending_offers": wave_state.get("pending_offers", 0),
                }

                dialog = WaveResultsDialog(dialog_data, parent=self._view)
                dialog.exec()

        # Check if Wave 3 just completed - show message about Draft requirement
        if current_wave == 3 and wave_complete:
            from PySide6.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setWindowTitle("Wave 3 Complete")
            msg.setIcon(QMessageBox.Information)
            msg.setText("<b>Wave 3 (Depth Players) Complete!</b>")
            msg.setInformativeText(
                "All offers have been resolved.\n\n"
                "The NFL Draft will begin next.\n"
                "After the Draft, Post-Draft Free Agency (Wave 4) will become available.\n\n"
                "Click OK to proceed to Draft."
            )
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()

            # Force stage advancement to Draft
            self._advance_to_next()
            return  # Exit early - don't re-enable process button

        # Refresh FA wave display with updated state
        self._refresh_fa_wave_display()

        # Auto-advance if stage is complete
        if result_dict.get("can_advance"):
            self._advance_to_next()
        else:
            # Not auto-advancing - re-enable process button
            if hasattr(self, "_offseason_view") and self._offseason_view:
                self._offseason_view.set_process_enabled(True)

    def _on_fa_wave_error(self, error_msg: str):
        """
        Handle wave action error from FA controller.

        Args:
            error_msg: Error message from wave execution
        """
        self.error_occurred.emit(f"Wave action failed: {error_msg}")

    # ========================================================================
    # Franchise Tag Support
    # ========================================================================

    def _on_tag_applied(self, player_id: int, tag_type: str):
        """
        Handle franchise/transition tag application with cap validation.

        Args:
            player_id: ID of player to tag
            tag_type: "franchise" or "transition"
        """
        from game_cycle.services.cap_helper import CapHelper

        stage = self.current_stage
        if stage is None or stage.stage_type != StageType.OFFSEASON_FRANCHISE_TAG:
            self._show_tag_error("Not in franchise tag stage")
            return

        # Get tag cost from the taggable players data
        preview = self._backend.get_stage_preview()
        taggable = preview.get("taggable_players", [])
        player_data = next((p for p in taggable if p.get("player_id") == player_id), None)

        if not player_data:
            self._show_tag_error("Player not found in taggable list")
            self._reset_tag_ui_state()
            return

        # Get tag cost based on type
        if tag_type == "franchise":
            tag_cost = player_data.get("franchise_tag_cost", 0)
        else:
            tag_cost = player_data.get("transition_tag_cost", 0)

        # Validate against NEXT season's cap (tags count against new league year)
        next_season = stage.season_year + 1
        cap_helper = CapHelper(self._database_path, self._dynasty_id, next_season)

        is_valid, error_msg = cap_helper.validate_franchise_tag(
            team_id=self._user_team_id,
            tag_cost=tag_cost
        )

        if not is_valid:
            self._show_tag_error(error_msg)
            self._reset_tag_ui_state()
            return

        # Store decision and execute
        self._tag_decision = {"player_id": player_id, "tag_type": tag_type}
        self._execute_tag_decision()

    def _show_tag_error(self, message: str):
        """Show error message dialog for tag operations."""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(None, "Cannot Apply Tag", message)

    def _reset_tag_ui_state(self):
        """Reset franchise tag UI state after a failed attempt."""
        if hasattr(self, "_offseason_view") and self._offseason_view:
            franchise_tag_view = self._offseason_view.get_franchise_tag_view()
            franchise_tag_view.set_tag_used(False)

    def _execute_tag_decision(self):
        """Execute the tag decision via backend."""
        if not self._tag_decision:
            return

        stage = self.current_stage
        if stage is None:
            return

        try:
            # Build context with tag decision
            context = {
                "dynasty_id": self._dynasty_id,
                "season": stage.season_year,
                "user_team_id": self._user_team_id,
                "db_path": self._database_path,
                "tag_decision": self._tag_decision,
            }

            # Execute via backend
            result = self._backend.execute_current_stage(extra_context=context)

            # Show result
            if self._view:
                result_dict = {
                    "stage_name": result.stage.display_name,
                    "events_processed": result.events_processed,
                    "success": result.success,
                }
                self._view.show_execution_result(result_dict)

            # Clear decision
            self._tag_decision = None

            # Refresh view to show updated state
            self._refresh_franchise_tag_view()

        except Exception as e:
            error_msg = f"Tag application failed: {e}"
            self.error_occurred.emit(error_msg)
            self._reset_tag_ui_state()

    def _refresh_franchise_tag_view(self):
        """Refresh the franchise tag view after a tag is applied."""
        if not hasattr(self, "_offseason_view"):
            return

        # Get fresh preview data
        preview = self._backend.get_stage_preview()

        # Update franchise tag view
        franchise_tag_view = self._offseason_view.get_franchise_tag_view()

        taggable_players = preview.get("taggable_players", [])
        if taggable_players:
            franchise_tag_view.set_taggable_players(taggable_players)
        else:
            franchise_tag_view.show_no_taggable_message()

        franchise_tag_view.set_tag_used(preview.get("tag_used", False))

        # Update cap data
        cap_data = preview.get("cap_data")
        if cap_data:
            franchise_tag_view.set_cap_data(cap_data)

        projected_cap_data = preview.get("projected_cap_data")
        if projected_cap_data:
            franchise_tag_view.set_projected_cap_data(projected_cap_data)

    def _on_process_offseason_stage(self):
        """Process current offseason stage when user clicks Process button."""
        stage = self.current_stage
        if stage is None or stage.phase != SeasonPhase.OFFSEASON:
            self.error_occurred.emit("Not in offseason phase")
            return

        try:
            # Build base context with user decisions
            # Use stage.season_year as single source of truth
            context = {
                "dynasty_id": self._dynasty_id,
                "season": stage.season_year,
                "user_team_id": self._user_team_id,
                "db_path": self._database_path,
                "user_decisions": self._user_decisions.copy(),  # Re-signing decisions
                # Roster cut decisions: list of dicts with player_id and use_june_1
                "roster_cut_decisions": [
                    {"player_id": pid, "use_june_1": use_june_1}
                    for pid, use_june_1 in self._cut_decisions.items()
                ],
            }

            # For FA stage, ALWAYS use wave-based path (not legacy _fa_decisions)
            # Removed has_pending_actions() check - clicking "Process FA" should always do something
            if stage.stage_type == StageType.OFFSEASON_FREE_AGENCY and self._fa_controller:
                # Build wave context with any pending actions
                context = self._fa_controller.build_context(context)

                # DEFAULT ACTION: If no control flags set, advance the wave
                # This ensures clicking "Process FA" always advances even without offers
                wave_control = context.get("wave_control", {})
                if not wave_control.get("advance_day") and not wave_control.get("advance_wave"):
                    context.setdefault("wave_control", {})["advance_wave"] = True
            else:
                # Legacy path: use _fa_decisions dict (for non-FA stages or no FA controller)
                context["fa_decisions"] = self._fa_decisions.copy()

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
            self._cut_decisions.clear()

            # Clear FA controller's pending actions (wave-based)
            if self._fa_controller:
                self._fa_controller.clear_pending()

            # Auto-advance if successful
            if result.can_advance:
                self._advance_to_next()

                # Check if we transitioned out of offseason (preseason → new season)
                new_stage = self.current_stage
                if new_stage and new_stage.phase != SeasonPhase.OFFSEASON:
                    # Emit signal to switch to Season tab
                    self.season_started.emit()
            else:
                # Not auto-advancing (e.g., wave-based FA) - re-enable process button
                if hasattr(self, "_offseason_view") and self._offseason_view:
                    self._offseason_view.set_process_enabled(True)
                    # Refresh FA view with updated wave state if in FA stage
                    if stage.stage_type == StageType.OFFSEASON_FREE_AGENCY:
                        self._refresh_fa_wave_display()

            self.execution_complete.emit(result_dict)

        except Exception as e:
            error_msg = f"Offseason stage execution failed: {e}"
            self.error_occurred.emit(error_msg)
            if self._view:
                self._view.set_status(error_msg, is_error=True)
            # Re-enable button on error so user can try again
            if hasattr(self, "_offseason_view") and self._offseason_view:
                self._offseason_view.set_process_enabled(True)

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

    def _on_draft_direction_changed(self, direction):
        """
        Handle draft direction changes from the view.

        Args:
            direction: DraftDirection object from the dialog
        """
        self._draft_direction = direction
        print(f"[UI Controller] Draft direction updated: {direction.strategy.value}")

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
                "draft_direction": self._draft_direction,  # Owner's strategy
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
                "draft_direction": self._draft_direction,  # Owner's strategy
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
            from game_cycle.services.draft_service import DraftService

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

    # ========================================================================
    # Injury/IR Management Support (Tollgate 6)
    # ========================================================================

    def get_injury_data_for_team(self, team_id: int) -> Dict[str, Any]:
        """
        Fetch injury data for display in InjuryReportView.

        Args:
            team_id: Team to get injury data for

        Returns:
            Dict with active_injuries, ir_players, ir_slots_remaining, etc.
        """
        from game_cycle.services.injury_service import InjuryService
        from team_management.teams.team_loader import get_team_by_id

        try:
            # Use stage season if available
            stage = self.current_stage
            season = stage.season_year if stage else self._season

            injury_service = InjuryService(
                db_path=self._database_path,
                dynasty_id=self._dynasty_id,
                season=season
            )

            # Get active injuries (not on IR)
            all_active = injury_service.get_active_injuries(team_id=team_id)
            active_injuries = [
                self._prepare_injury_for_view(inj, team_id)
                for inj in all_active
                if not inj.on_ir
            ]

            # Get players on IR
            ir_players_list = injury_service.get_players_on_ir(team_id=team_id)
            ir_players = [
                self._prepare_injury_for_view(inj, team_id)
                for inj in ir_players_list
            ]

            # Get IR slots remaining
            slots_remaining = injury_service.get_ir_return_slots_remaining(team_id)

            # Get current week
            current_week = self._get_current_week_from_stage()

            # Get roster count for activation eligibility display
            from database.player_roster_api import PlayerRosterAPI
            roster_api = PlayerRosterAPI(self._database_path)
            roster_count = roster_api.get_roster_count(self._dynasty_id, team_id)

            # Get team name
            team = get_team_by_id(team_id)
            team_name = f"{team.city} {team.nickname}" if team else f"Team {team_id}"

            return {
                "team_id": team_id,
                "team_name": team_name,
                "active_injuries": active_injuries,
                "ir_players": ir_players,
                "ir_slots_remaining": slots_remaining,
                "current_week": current_week,
                "is_user_team": team_id == self._user_team_id,
                "roster_count": roster_count,
            }

        except Exception as e:
            print(f"[StageUIController] Error fetching injury data: {e}")
            # Return empty data structure on error
            return {
                "team_id": team_id,
                "team_name": f"Team {team_id}",
                "active_injuries": [],
                "ir_players": [],
                "ir_slots_remaining": 8,
                "current_week": 1,
                "is_user_team": team_id == self._user_team_id,
                "roster_count": 0,
            }

    def _prepare_injury_for_view(self, injury, team_id: int) -> Dict[str, Any]:
        """
        Prepare an Injury object for the view.

        The view expects injury data as a dict with an 'injury' key containing
        the Injury dataclass and a 'position' key for the player's position.
        """
        from database.unified_api import UnifiedDatabaseAPI

        # Get player position from database
        position = ""
        try:
            unified_api = UnifiedDatabaseAPI(self._database_path, self._dynasty_id)
            player_data = unified_api.player_get_by_id(injury.player_id)
            if player_data:
                position = player_data.get("position", "")
        except Exception:
            pass

        return {
            "injury": injury,
            "position": position,
        }

    def _get_current_week_from_stage(self) -> int:
        """Get current week number from stage."""
        stage = self.current_stage
        if stage is None:
            return 1

        if stage.phase == SeasonPhase.REGULAR_SEASON:
            # Extract week number from stage
            preview = self._backend.get_stage_preview()
            return preview.get("week", 1)
        elif stage.phase == SeasonPhase.PLAYOFFS:
            # Map playoff stage to week
            playoff_week_map = {
                StageType.WILD_CARD: 19,
                StageType.DIVISIONAL: 20,
                StageType.CONFERENCE_CHAMPIONSHIP: 21,
                StageType.SUPER_BOWL: 22,
            }
            return playoff_week_map.get(stage.stage_type, 19)
        else:
            # Offseason - return 0 or last week
            return 0

    def place_player_on_ir(self, player_id: int, injury_id: int):
        """
        Place a player on Injured Reserve.

        Emits ir_action_complete signal with result.

        Args:
            player_id: Player to place on IR
            injury_id: The injury record ID
        """
        from game_cycle.services.injury_service import InjuryService

        try:
            stage = self.current_stage
            season = stage.season_year if stage else self._season

            injury_service = InjuryService(
                db_path=self._database_path,
                dynasty_id=self._dynasty_id,
                season=season
            )

            success = injury_service.place_on_ir(player_id, injury_id)

            if success:
                self.ir_action_complete.emit(True, "Player placed on IR successfully")
            else:
                self.ir_action_complete.emit(
                    False,
                    "Failed to place on IR. Injury must be 4+ weeks."
                )

        except Exception as e:
            self.ir_action_complete.emit(False, f"Error: {str(e)}")

    def activate_player_from_ir(self, player_id: int):
        """
        Activate a player from Injured Reserve.

        Uses one IR-return slot. Emits ir_action_complete signal with result.

        Args:
            player_id: Player to activate
        """
        from game_cycle.services.injury_service import InjuryService

        try:
            stage = self.current_stage
            season = stage.season_year if stage else self._season
            current_week = self._get_current_week_from_stage()

            injury_service = InjuryService(
                db_path=self._database_path,
                dynasty_id=self._dynasty_id,
                season=season
            )

            success = injury_service.activate_from_ir(player_id, current_week)

            if success:
                self.ir_action_complete.emit(True, "Player activated from IR")
            else:
                # Check why it failed
                slots = injury_service.get_ir_return_slots_remaining(
                    self._user_team_id
                )
                if slots == 0:
                    self.ir_action_complete.emit(
                        False,
                        "No IR return slots remaining (8/8 used)"
                    )
                else:
                    self.ir_action_complete.emit(
                        False,
                        "Player not eligible for IR activation yet (4 game minimum)"
                    )

        except Exception as e:
            self.ir_action_complete.emit(False, f"Error: {str(e)}")

    # =========================================================================
    # IR Activation Roster Management (Milestone 5 Enhancement)
    # =========================================================================

    def set_ir_activation_view(self, ir_activation_view):
        """
        Connect to the IR activation view for weekly roster management.

        Args:
            ir_activation_view: IRActivationView instance
        """
        self._ir_activation_view = ir_activation_view

        # Connect signals
        ir_activation_view.activations_complete.connect(self._on_ir_activations_complete)
        ir_activation_view.skip_all.connect(self._on_ir_skip_all)

    def check_and_show_ir_activations(self, current_week: int) -> bool:
        """
        Check if any IR activations are needed and show UI if applicable.

        Called after regular season week processing, before advancing to next week.
        This is a conditional micro-stage that only appears when IR players are eligible.

        Args:
            current_week: Current week number

        Returns:
            True if IR activation UI was shown (blocking), False if skipped
        """
        from game_cycle.services.injury_service import InjuryService
        from team_management.teams.team_loader import get_all_teams

        try:
            injury_service = InjuryService(
                db_path=self._database_path,
                dynasty_id=self._dynasty_id,
                season=self.season
            )

            # 1. Process AI teams first (automatic, no UI)
            all_teams = get_all_teams()
            ai_team_ids = [t.team_id for t in all_teams if t.team_id != self._user_team_id]

            ai_result = injury_service.process_ai_ir_activations(ai_team_ids, current_week)

            if ai_result["total_activations"] > 0:
                self._logger.info(
                    f"AI teams activated {ai_result['total_activations']} players from IR "
                    f"(cut {ai_result['total_cuts']} players)"
                )

            # 2. Check if user team has eligible IR players
            eligible_players = injury_service.get_weekly_ir_eligible_players(
                self._user_team_id, current_week
            )

            if not eligible_players:
                return False  # No eligible players, skip micro-stage

            # 3. Get cut candidates and roster info
            cut_candidates = injury_service.get_cut_candidates_for_activation(
                self._user_team_id, len(eligible_players)
            )

            ir_slots_remaining = injury_service.get_ir_return_slots_remaining(self._user_team_id)

            # Get roster count
            import sqlite3
            conn = sqlite3.connect(self._database_path, timeout=30.0)
            try:
                roster_count = conn.execute("""
                    SELECT COUNT(*) as cnt
                    FROM team_rosters
                    WHERE dynasty_id = ? AND team_id = ? AND roster_status = 'active'
                """, (self._dynasty_id, self._user_team_id)).fetchone()[0]
            finally:
                conn.close()

            # 4. Load data into view and show
            if hasattr(self, '_ir_activation_view'):
                self._ir_activation_view.load_data(
                    eligible_players=eligible_players,
                    cut_candidates=cut_candidates,
                    current_week=current_week,
                    ir_slots_remaining=ir_slots_remaining,
                    roster_count=roster_count
                )
                self._ir_activation_view.show()
                return True  # UI shown, will block until user makes decision
            else:
                self._logger.warning("IR activation view not set, skipping user IR activations")
                return False

        except Exception as e:
            self._logger.error(f"Error in check_and_show_ir_activations: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _on_ir_activations_complete(self, data: dict):
        """
        Handle completion of IR activation decisions.

        Args:
            data: {
                "activations": List[{player_to_activate: int, player_to_cut: int}],
                "current_week": int
            }
        """
        from game_cycle.services.injury_service import InjuryService

        try:
            injury_service = InjuryService(
                db_path=self._database_path,
                dynasty_id=self._dynasty_id,
                season=self.season
            )

            # Execute batch activations
            result = injury_service.execute_batch_ir_activations(
                team_id=self._user_team_id,
                activations=data["activations"],
                current_week=data["current_week"]
            )

            # Hide the IR activation view
            if hasattr(self, '_ir_activation_view'):
                self._ir_activation_view.hide()

            # Show result message
            if result["success"]:
                activated_names = ", ".join(result["activations"])
                cut_names = ", ".join(result["cuts"])
                message = (
                    f"Successfully activated {len(result['activations'])} player(s) from IR:\n"
                    f"Activated: {activated_names}\n"
                    f"Cut: {cut_names}"
                )
                self._logger.info(message)
                if self._view:
                    self._view.set_status(f"IR activations complete: {len(result['activations'])} activated")
            else:
                error_msg = "\n".join(result["errors"])
                self._logger.error(f"IR activation failed: {error_msg}")
                if self._view:
                    self._view.set_status(f"IR activation failed: {error_msg}")

            # Advance to next stage after IR activation completes
            self._advance_to_next()

        except Exception as e:
            self._logger.error(f"Error processing IR activations: {e}")
            import traceback
            traceback.print_exc()

    def _on_ir_skip_all(self):
        """Handle user choosing to skip all IR activations this week."""
        self._logger.info("User skipped all IR activations for this week")

        # Hide the IR activation view
        if hasattr(self, '_ir_activation_view'):
            self._ir_activation_view.hide()

        if self._view:
            self._view.set_status("IR activations skipped - players remain on IR")

        # Advance to next stage after skipping
        self._advance_to_next()
