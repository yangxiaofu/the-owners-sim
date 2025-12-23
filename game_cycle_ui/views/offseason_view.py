"""
Offseason View - Container view for all offseason stages.

Uses a stacked widget to show the appropriate sub-view based on
the current offseason stage (re-signing, free agency, draft, etc.).
"""

from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QStackedWidget, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from game_cycle import Stage, StageType
from game_cycle.stage_definitions import ROSTER_LIMITS
from game_cycle_ui.theme import SECONDARY_BUTTON_STYLE, Typography, FontSizes, TextColors
from .resigning_view import ResigningView
from .free_agency_view import FreeAgencyView
from .draft_view import DraftView
from .roster_cuts_view import RosterCutsView
from .waiver_wire_view import WaiverWireView
from .training_camp_view import TrainingCampView
from .franchise_tag_view import FranchiseTagView
from .trading_view import TradingView
from .preseason_view import PreseasonView


class OffseasonView(QWidget):
    """
    Container view for all offseason stages.

    Switches between sub-views based on the current stage:
    - Re-signing: ResigningView with expiring contracts table
    - Free Agency: FreeAgencyView with available free agents
    - Draft: DraftView with prospect selection
    - Preseason W1/W2/W3: RosterCutsView with staged cuts (90→85→80→53)
    - Waiver Wire: WaiverWireView with priority-based claims
    - Training Camp: TrainingCampView with player development results
    """

    # Signals
    player_resigned = Signal(int)  # Forward from ResigningView
    player_released = Signal(int)  # Forward from ResigningView
    player_signed_fa = Signal(int)  # Forward from FreeAgencyView
    player_unsigned_fa = Signal(int)  # Forward from FreeAgencyView (unsign toggle)
    process_stage_requested = Signal()  # Emitted when user clicks Process button

    # Draft signals (forward from DraftView)
    prospect_drafted = Signal(int)  # prospect_id
    simulate_to_pick_requested = Signal()
    auto_draft_all_requested = Signal()

    # Roster cuts signals (forward from RosterCutsView)
    player_cut = Signal(int, bool)  # player_id, use_june_1
    get_suggestions_requested = Signal()

    # Waiver wire signals (forward from WaiverWireView)
    waiver_claim_submitted = Signal(int)  # player_id
    waiver_claim_cancelled = Signal(int)  # player_id

    # Franchise tag signals (forward from FranchiseTagView)
    tag_applied = Signal(int, str)  # player_id, tag_type ("franchise" or "transition")
    tag_proposal_approved = Signal(str)  # proposal_id
    tag_proposal_rejected = Signal(str, str)  # proposal_id, notes

    # Re-signing GM proposals signal (Tollgate 6)
    resigning_proposals_reviewed = Signal(list)  # List of (proposal_id, approved: bool)

    # Cap relief signals (forward from ResigningView)
    resigning_restructure_completed = Signal(int, int)  # contract_id, cap_savings
    resigning_early_cut_completed = Signal(int, int, int)  # player_id, dead_money, cap_savings

    # Trading GM proposals signals (Tollgate 8)
    trade_proposal_approved = Signal(str)   # proposal_id
    trade_proposal_rejected = Signal(str)   # proposal_id

    # Free Agency GM proposal signals (Tollgate 7)
    fa_proposal_approved = Signal(str)   # proposal_id
    fa_proposal_rejected = Signal(str)   # proposal_id
    fa_proposal_retracted = Signal(str)  # proposal_id (undo support)

    # Draft GM proposal signals (Tollgate 9)
    draft_proposal_approved = Signal(str)   # proposal_id
    draft_proposal_rejected = Signal(str)   # proposal_id
    draft_alternative_requested = Signal(str, int)  # proposal_id, prospect_id

    # Stage advancement signal
    advance_requested = Signal()  # Request to advance to next stage

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_stage: Optional[Stage] = None
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header with stage name and description
        self._create_header(layout)

        # Stacked widget for different stage views
        self._create_stacked_views(layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create the header section with stage name and description."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_frame.setStyleSheet("background-color: #1e3a5f; border-radius: 4px;")

        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 6, 12, 6)
        header_layout.setSpacing(4)

        # Stage name (compact)
        self.stage_label = QLabel("Offseason")
        self.stage_label.setFont(Typography.H3)
        self.stage_label.setStyleSheet("color: white;")
        header_layout.addWidget(self.stage_label)

        # Description (compact)
        self.description_label = QLabel("")
        self.description_label.setFont(Typography.SMALL)
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #e0e0e0;")
        header_layout.addWidget(self.description_label)

        # Process button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.process_button = QPushButton("Process Stage")
        self.process_button.setMinimumHeight(32)
        self.process_button.setMinimumWidth(180)
        self.process_button.setFont(Typography.BODY)
        self.process_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.process_button.clicked.connect(self._on_process_clicked)
        button_layout.addWidget(self.process_button)

        button_layout.addStretch()
        header_layout.addLayout(button_layout)

        self.header_frame = header_frame  # Store as instance variable
        parent_layout.addWidget(self.header_frame)

    def _create_stacked_views(self, parent_layout: QVBoxLayout):
        """Create the stacked widget with sub-views for each stage."""
        self.stack = QStackedWidget()

        # Franchise Tag view (index 0) - FIRST offseason stage
        self.franchise_tag_view = FranchiseTagView()
        self.franchise_tag_view.tag_applied.connect(self.tag_applied.emit)
        self.franchise_tag_view.proposal_approved.connect(self.tag_proposal_approved.emit)
        self.franchise_tag_view.proposal_rejected.connect(self.tag_proposal_rejected.emit)
        self.stack.addWidget(self.franchise_tag_view)

        # Re-signing view (index 1)
        self.resigning_view = ResigningView()
        self.resigning_view.player_resigned.connect(self.player_resigned.emit)
        self.resigning_view.player_released.connect(self.player_released.emit)
        self.resigning_view.cap_validation_changed.connect(self._on_cap_validation_changed)
        # Tollgate 6: Forward GM proposal decisions
        self.resigning_view.proposals_reviewed.connect(self.resigning_proposals_reviewed.emit)
        # Cap relief signals
        self.resigning_view.restructure_completed.connect(self.resigning_restructure_completed.emit)
        self.resigning_view.early_cut_completed.connect(self.resigning_early_cut_completed.emit)
        self.stack.addWidget(self.resigning_view)

        # Free Agency view (index 2)
        self.free_agency_view = FreeAgencyView()
        self.free_agency_view.player_signed.connect(self.player_signed_fa.emit)
        self.free_agency_view.player_unsigned.connect(self.player_unsigned_fa.emit)
        self.free_agency_view.cap_validation_changed.connect(self._on_fa_cap_validation_changed)
        # Tollgate 7: Forward GM FA signing proposal signals
        self.free_agency_view.proposal_approved.connect(self.fa_proposal_approved.emit)
        self.free_agency_view.proposal_rejected.connect(self.fa_proposal_rejected.emit)
        self.free_agency_view.proposal_retracted.connect(self.fa_proposal_retracted.emit)
        self.stack.addWidget(self.free_agency_view)

        # Trading view (index 3) - GM trade proposals (Tollgate 8)
        self.trading_view = TradingView()
        self.trading_view.cap_validation_changed.connect(self._on_trading_cap_validation_changed)
        self.trading_view.proposal_approved.connect(self.trade_proposal_approved.emit)
        self.trading_view.proposal_rejected.connect(self.trade_proposal_rejected.emit)
        self.stack.addWidget(self.trading_view)

        # Draft view (index 4)
        self.draft_view = DraftView()
        self.draft_view.prospect_drafted.connect(self.prospect_drafted.emit)
        self.draft_view.simulate_to_pick_requested.connect(self.simulate_to_pick_requested.emit)
        self.draft_view.auto_draft_all_requested.connect(self.auto_draft_all_requested.emit)
        # Tollgate 9: Forward GM proposal signals
        self.draft_view.proposal_approved.connect(self.draft_proposal_approved.emit)
        self.draft_view.proposal_rejected.connect(self.draft_proposal_rejected.emit)
        self.draft_view.alternative_requested.connect(self.draft_alternative_requested.emit)
        # Forward advance stage signal
        self.draft_view.advance_requested.connect(self.advance_requested.emit)
        self.stack.addWidget(self.draft_view)

        # Roster Cuts view (index 5)
        self.roster_cuts_view = RosterCutsView()
        self.roster_cuts_view.player_cut.connect(self.player_cut.emit)
        self.roster_cuts_view.get_suggestions_requested.connect(self.get_suggestions_requested.emit)
        self.roster_cuts_view.cap_validation_changed.connect(self._on_roster_cuts_cap_validation)
        self.stack.addWidget(self.roster_cuts_view)

        # Waiver Wire view (index 6)
        self.waiver_wire_view = WaiverWireView()
        self.waiver_wire_view.claim_submitted.connect(self.waiver_claim_submitted.emit)
        self.waiver_wire_view.claim_cancelled.connect(self.waiver_claim_cancelled.emit)
        self.stack.addWidget(self.waiver_wire_view)

        # Training Camp view (index 7)
        self.training_camp_view = TrainingCampView()
        self.training_camp_view.continue_clicked.connect(self.process_stage_requested.emit)
        self.stack.addWidget(self.training_camp_view)

        # Preseason view (index 8) - game simulation for W1/W2/W3
        self.preseason_view = PreseasonView()
        self.preseason_view.advance_requested.connect(self.advance_requested.emit)
        self.preseason_view.game_selected.connect(self._on_preseason_game_selected)
        self.stack.addWidget(self.preseason_view)

        parent_layout.addWidget(self.stack, stretch=1)

    def set_stage(self, stage: Stage, preview_data: Dict[str, Any]):
        """
        Update the view for the current offseason stage.

        Args:
            stage: The current offseason stage
            preview_data: Preview data from OffseasonHandler.get_stage_preview()
        """
        self._current_stage = stage

        # Store dynasty context for BoxScoreDialog (needed for preseason games)
        self._dynasty_id = preview_data.get("dynasty_id")
        self._db_path = preview_data.get("db_path")

        # Update header
        stage_name = preview_data.get("stage_name", stage.display_name)
        description = preview_data.get("description", "")

        self.stage_label.setText(stage_name)
        self.description_label.setText(description)

        # Get stage type for switching logic
        stage_type = stage.stage_type

        # Update process button text based on stage
        if stage_type == StageType.OFFSEASON_PRESEASON_W1:
            self.process_button.setText("Process Preseason Week 1")
        elif stage_type == StageType.OFFSEASON_PRESEASON_W2:
            self.process_button.setText("Process Preseason Week 2")
        elif stage_type == StageType.OFFSEASON_PRESEASON_W3:
            self.process_button.setText("Process Preseason Week 3")
        elif stage_type == StageType.OFFSEASON_ROSTER_CUTS:
            self.process_button.setText("Finalize Roster Cuts")
        else:
            self.process_button.setText(f"Process {stage.display_name}")
        self.process_button.setEnabled(True)

        # Switch to appropriate sub-view

        # Always show header for all offseason stages
        self.header_frame.setVisible(True)

        # Show process button by default
        # Hidden for: Draft (has own controls), Free Agency (has wave controls)
        if stage_type in (StageType.OFFSEASON_DRAFT, StageType.OFFSEASON_FREE_AGENCY):
            self.process_button.setVisible(False)
        else:
            self.process_button.setVisible(True)

        if stage_type == StageType.OFFSEASON_FRANCHISE_TAG:
            self.stack.setCurrentIndex(0)
            taggable_players = preview_data.get("taggable_players", [])
            tag_used = preview_data.get("tag_used", False)

            self.franchise_tag_view.set_taggable_players(taggable_players)

            self.franchise_tag_view.set_tag_used(tag_used)

            # Update season info for cap labels
            current_season = preview_data.get("current_season", 2025)
            next_season = preview_data.get("next_season", 2026)
            self.franchise_tag_view.set_season_info(current_season, next_season)

            # Update cap data if available (current season - reference)
            cap_data = preview_data.get("cap_data")
            if cap_data:
                self.franchise_tag_view.set_cap_data(cap_data)

            # Update projected next-year cap (where tag actually counts)
            projected_cap_data = preview_data.get("projected_cap_data")
            if projected_cap_data:
                self.franchise_tag_view.set_projected_cap_data(projected_cap_data)

            # Set GM proposal if available (Tollgate 5)
            gm_proposals = preview_data.get("gm_proposals", [])
            gm_proposal = gm_proposals[0] if gm_proposals else None
            self.franchise_tag_view.set_gm_proposal(gm_proposal)

        elif stage_type == StageType.OFFSEASON_RESIGNING:
            self.stack.setCurrentIndex(1)

            # Use consolidated data update method
            from game_cycle_ui.models.stage_data import ResigningStageData

            # Get all required data from preview
            cap_data = preview_data.get("cap_data", {})
            all_player_recs = preview_data.get("all_player_recommendations", [])
            roster_players = preview_data.get("roster_players", [])
            expiring_ids = preview_data.get("expiring_player_ids", set())

            # Restructure proposals are loaded separately by _handle_resigning_stage
            # (not in preview_data), so start with empty list
            stage_data = ResigningStageData(
                recommendations=all_player_recs,
                restructure_proposals=[],  # Loaded separately by stage_controller
                cap_data=cap_data,
                roster_players=roster_players,
                expiring_ids=expiring_ids,
                is_reevaluation=False
            )
            self.resigning_view.update_stage_data(stage_data)

            # Legacy fallback for old format (if all_player_recs empty)
            if not all_player_recs:
                gm_proposals = preview_data.get("gm_proposals", [])
                if gm_proposals:
                    self.resigning_view.set_gm_proposals(gm_proposals)

        elif stage_type == StageType.OFFSEASON_FREE_AGENCY:
            self.stack.setCurrentIndex(2)
            free_agents = preview_data.get("free_agents", [])
            if free_agents:
                self.free_agency_view.set_free_agents(free_agents)
            else:
                self.free_agency_view.show_no_free_agents_message()
            # Update cap data if available
            cap_data = preview_data.get("cap_data")
            if cap_data:
                self.free_agency_view.set_cap_data(cap_data)
            # Initialize wave controls (triggers _enable_wave_mode())
            wave_state = preview_data.get("wave_state", {})
            if wave_state:
                self.free_agency_view.set_wave_info(
                    wave=wave_state.get("current_wave", 0),
                    wave_name=wave_state.get("wave_name", ""),
                    day=wave_state.get("current_day", 1),
                    days_total=wave_state.get("days_in_wave", 1),
                )
            # Load owner directives on initial entry (mirrors pattern in stage_controller.py:1372-1374)
            owner_directives = preview_data.get("owner_directives")
            if owner_directives and hasattr(self.free_agency_view, 'set_owner_directives'):
                self.free_agency_view.set_owner_directives(owner_directives)

        elif stage_type == StageType.OFFSEASON_TRADING:
            self.stack.setCurrentIndex(3)
            # Populate trading data
            self.trading_view.set_trading_data(preview_data)
            # Update cap data if available
            cap_data = preview_data.get("cap_data")
            if cap_data:
                self.trading_view.set_cap_data(cap_data)

        elif stage_type == StageType.OFFSEASON_DRAFT:
            self.stack.setCurrentIndex(4)
            # Hide the process button for draft (draft has its own controls)
            self.process_button.setVisible(False)
            # Populate draft data
            prospects = preview_data.get("prospects", [])
            current_pick = preview_data.get("current_pick")
            draft_progress = preview_data.get("draft_progress", {})
            draft_history = preview_data.get("draft_history", [])

            if prospects:
                self.draft_view.set_prospects(prospects)
            else:
                self.draft_view.show_no_prospects_message()

            self.draft_view.set_current_pick(current_pick)
            self.draft_view.set_draft_progress(
                draft_progress.get("picks_made", 0),
                draft_progress.get("total_picks", 224)
            )
            if draft_history:
                self.draft_view.set_draft_history(draft_history)

            # Check if draft is complete
            if preview_data.get("draft_complete", False):
                self.draft_view.set_draft_complete()
            # Update cap data if available
            cap_data = preview_data.get("cap_data")
            if cap_data:
                self.draft_view.set_cap_data(cap_data)

            # Tollgate 9: Set GM proposal if available
            gm_proposals = preview_data.get("gm_proposals", [])
            gm_proposal = gm_proposals[0] if gm_proposals else None
            trust_gm = preview_data.get("trust_gm", False)
            self.draft_view.set_gm_proposal(gm_proposal, trust_gm)

        elif stage_type in (StageType.OFFSEASON_PRESEASON_W1,
                            StageType.OFFSEASON_PRESEASON_W2,
                            StageType.OFFSEASON_PRESEASON_W3):
            # Use PreseasonView (index 8) for game simulation
            self.stack.setCurrentIndex(8)

            # Set context for BoxScoreDialog access
            user_team_id = preview_data.get("user_team_id", 1)
            # Always set context (use preview_data as fallback if needed)
            self.preseason_view.set_context(
                dynasty_id=self._dynasty_id or preview_data.get("dynasty_id"),
                db_path=self._db_path or preview_data.get("db_path"),
                season=stage.season_year,
                user_team_id=user_team_id
            )

            # Determine week number
            if stage_type == StageType.OFFSEASON_PRESEASON_W1:
                week = 1
            elif stage_type == StageType.OFFSEASON_PRESEASON_W2:
                week = 2
            else:  # OFFSEASON_PRESEASON_W3
                week = 3

            # Configure preseason view for this week
            self.preseason_view.set_week(week)

            # Fallback: if database fetch failed (0 games), use preview_data
            games_count = len(self.preseason_view._games)
            print(f"[OffseasonView] After set_week({week}), view has {games_count} games")
            if games_count == 0:
                print(f"[OffseasonView] WARNING: Fallback triggered - using preview_data")
                preseason_games = preview_data.get("preseason_games", [])
                print(f"[OffseasonView] preview_data has {len(preseason_games)} games")
                if preseason_games:
                    self.preseason_view.set_games(preseason_games)
                    print(f"[OffseasonView] Set games from preview_data")
            else:
                print(f"[OffseasonView] Database fetch succeeded, not using fallback")

            # Set roster status (all weeks just show current roster size)
            current_size = preview_data.get("roster_count", preview_data.get("current_size", 90))
            self.preseason_view.set_roster_status(current_size, 90)

        elif stage_type == StageType.OFFSEASON_ROSTER_CUTS:
            # Final roster cuts - dedicated view (index 5)
            self.stack.setCurrentIndex(5)

            # Refresh roster cuts view with current data
            self.roster_cuts_view.refresh_roster()

            # Update process button
            self.process_button.setVisible(True)
            self.process_button.setText("Finalize Roster Cuts")

        elif stage_type == StageType.OFFSEASON_WAIVER_WIRE:
            self.stack.setCurrentIndex(6)
            # Populate waiver wire data
            waiver_data = preview_data.get("waiver_data", {})
            if waiver_data:
                self.waiver_wire_view.set_waiver_data(waiver_data)
            else:
                self.waiver_wire_view.set_waiver_data({
                    "waiver_players": preview_data.get("waiver_players", []),
                    "user_priority": preview_data.get("user_priority", 16),
                    "user_claims": preview_data.get("user_claims", []),
                    "roster_players": preview_data.get("roster_players", []),
                    "expiring_player_ids": preview_data.get("expiring_player_ids", [])
                })
            # Show no waivers message if empty
            if not preview_data.get("waiver_players") and not preview_data.get("waiver_data", {}).get("waiver_players"):
                self.waiver_wire_view.show_no_waivers_message()
            # Update cap data if available
            cap_data = preview_data.get("cap_data")
            if cap_data:
                self.waiver_wire_view.set_cap_data(cap_data)

        elif stage_type == StageType.OFFSEASON_TRAINING_CAMP:
            self.stack.setCurrentIndex(7)
            # Hide the process button (training camp view has its own continue button)
            self.process_button.setVisible(False)

            # Set user team ID for default filter
            user_team_id = preview_data.get("user_team_id", 1)
            self.training_camp_view.set_user_team_id(user_team_id)

            # Populate with training camp results
            training_camp_results = preview_data.get("training_camp_results")
            if training_camp_results:
                self.training_camp_view.set_training_camp_data(training_camp_results)

        else:
            # Default to first view
            self.stack.setCurrentIndex(0)

    def get_resigning_view(self) -> ResigningView:
        """Get the re-signing view for direct access."""
        return self.resigning_view

    def get_free_agency_view(self) -> FreeAgencyView:
        """Get the free agency view for direct access."""
        return self.free_agency_view

    def get_draft_view(self) -> DraftView:
        """Get the draft view for direct access."""
        return self.draft_view

    def get_roster_cuts_view(self) -> RosterCutsView:
        """Get the roster cuts view for direct access."""
        return self.roster_cuts_view

    def set_db_path(self, db_path: str):
        """Set database path for contract lookups (forwarded to child views)."""
        self.roster_cuts_view.set_db_path(db_path)
        self.resigning_view.set_db_path(db_path)
        self.franchise_tag_view.set_db_path(db_path)

    def get_waiver_wire_view(self) -> WaiverWireView:
        """Get the waiver wire view for direct access."""
        return self.waiver_wire_view

    def get_training_camp_view(self) -> TrainingCampView:
        """Get the training camp view for direct access."""
        return self.training_camp_view

    def get_franchise_tag_view(self) -> FranchiseTagView:
        """Get the franchise tag view for direct access."""
        return self.franchise_tag_view

    def get_trading_view(self) -> TradingView:
        """Get the trading view for direct access."""
        return self.trading_view

    def _on_process_clicked(self):
        """Handle process button click."""
        self.process_button.setEnabled(False)
        self.process_button.setText("Processing...")

        # For re-signing stage, collect extension decisions and emit them
        if self._current_stage and self._current_stage.stage_type == StageType.OFFSEASON_RESIGNING:
            decisions = self.resigning_view.get_extension_decisions()
            if decisions:
                # Emit decisions for batch processing
                self.resigning_proposals_reviewed.emit(decisions)
                return

        # For other stages, just emit the generic process signal
        self.process_stage_requested.emit()

    def set_process_enabled(self, enabled: bool):
        """Enable/disable the process button."""
        self.process_button.setEnabled(enabled)
        if enabled and self._current_stage:
            self.process_button.setText(f"Process {self._current_stage.display_name}")

    def _on_cap_validation_changed(self, is_valid: bool, over_cap_amount: int):
        """
        Show cap warning but don't block progression (NFL-style).

        In the real NFL, teams can be over the cap during the offseason.
        Cap compliance is enforced before Training Camp via roster cuts.
        """
        # Only show tooltip if we're in the re-signing stage
        if self._current_stage and self._current_stage.stage_type == StageType.OFFSEASON_RESIGNING:
            # Don't disable button - NFL allows over-cap during offseason
            if not is_valid:
                self.process_button.setToolTip(
                    f"Warning: Over cap by ${over_cap_amount:,}. "
                    "You'll need to cut players before Training Camp."
                )
            else:
                self.process_button.setToolTip("")

    def _on_fa_cap_validation_changed(self, is_valid: bool, over_cap_amount: int):
        """
        Show cap warning but don't block progression (NFL-style).

        In the real NFL, teams can be over the cap during the offseason.
        Cap compliance is enforced before Training Camp via roster cuts.
        """
        # Only show tooltip if we're in the free agency stage
        if self._current_stage and self._current_stage.stage_type == StageType.OFFSEASON_FREE_AGENCY:
            # Don't disable button - NFL allows over-cap during offseason
            if not is_valid:
                self.process_button.setToolTip(
                    f"Warning: Over cap by ${over_cap_amount:,}. "
                    "You'll need to cut players before Training Camp."
                )
            else:
                self.process_button.setToolTip("")

    def _on_trading_cap_validation_changed(self, is_valid: bool, over_cap_amount: int):
        """
        Show cap warning but don't block trading (NFL-style).

        In the real NFL, teams can be over the cap during the offseason.
        Cap compliance is enforced before Training Camp via roster cuts.
        """
        # Only show tooltip if we're in the trading stage
        if self._current_stage and self._current_stage.stage_type == StageType.OFFSEASON_TRADING:
            # Don't disable button - NFL allows over-cap during offseason
            if not is_valid:
                self.process_button.setToolTip(
                    f"Warning: Over cap by ${over_cap_amount:,}. "
                    "You'll need to cut players before Training Camp."
                )
            else:
                self.process_button.setToolTip("")

    def _on_roster_cuts_cap_validation(self, is_compliant: bool, over_cap_amount: int):
        """
        Validate roster cuts stage for progression.

        Allow processing if:
        1. No cuts needed (roster already at or below target), OR
        2. Cap compliant (can advance to next stage), OR
        3. There are pending cuts marked (let user process them even if still over cap)

        This allows users to make progress by processing marked cuts even when
        they need multiple rounds of cuts to become cap-compliant.
        """
        if self._current_stage and self._current_stage.stage_type in (
            StageType.OFFSEASON_PRESEASON_W1,
            StageType.OFFSEASON_PRESEASON_W2,
            StageType.OFFSEASON_PRESEASON_W3,
            StageType.OFFSEASON_ROSTER_CUTS
        ):
            # Check roster size requirement first
            cuts_needed = self.roster_cuts_view.get_cuts_needed()
            has_pending_cuts = bool(self.roster_cuts_view.get_cut_player_ids())

            # If no cuts needed, can always advance (roster already under target)
            if cuts_needed <= 0:
                can_process = True
                self.process_button.setEnabled(True)
                self.process_button.setToolTip("Roster is at or below target. Ready to advance.")
                return

            # Otherwise, enable if cap compliant OR there are pending cuts to process
            can_process = is_compliant or has_pending_cuts

            self.process_button.setEnabled(can_process)
            if not is_compliant:
                if has_pending_cuts:
                    self.process_button.setToolTip(
                        f"Warning: Still over cap by ${over_cap_amount:,} after these cuts. "
                        "Process cuts to continue, then cut more players to become cap-compliant."
                    )
                else:
                    self.process_button.setToolTip(
                        f"Must be under salary cap to proceed. "
                        f"Over by ${over_cap_amount:,} - cut more players."
                    )
            else:
                self.process_button.setToolTip("")

    def _on_preseason_game_selected(self, game_id: str):
        """Handle preseason game selection - show box score."""
        from game_cycle_ui.dialogs import BoxScoreDialog

        # Need dynasty_id and db_path from parent
        if not hasattr(self, '_dynasty_id') or not hasattr(self, '_db_path'):
            print("[OffseasonView] Cannot show box score - missing dynasty/db context")
            return

        dialog = BoxScoreDialog(
            game_id=game_id,
            dynasty_id=self._dynasty_id,
            db_path=self._db_path,
            parent=self
        )
        dialog.exec()
