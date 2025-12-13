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
from .resigning_view import ResigningView
from .free_agency_view import FreeAgencyView
from .draft_view import DraftView
from .roster_cuts_view import RosterCutsView
from .waiver_wire_view import WaiverWireView
from .training_camp_view import TrainingCampView
from .franchise_tag_view import FranchiseTagView
from .trading_view import TradingView


class OffseasonView(QWidget):
    """
    Container view for all offseason stages.

    Switches between sub-views based on the current stage:
    - Re-signing: ResigningView with expiring contracts table
    - Free Agency: FreeAgencyView with available free agents
    - Draft: DraftView with prospect selection
    - Roster Cuts: RosterCutsView with cut suggestions and dead money tracking
    - Waiver Wire: WaiverWireView with priority-based claims
    - Training Camp: TrainingCampView with player development results
    - Preseason: Placeholder (coming soon)
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
        header_layout.setContentsMargins(16, 12, 16, 12)

        # Stage name (large)
        self.stage_label = QLabel("Offseason")
        self.stage_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.stage_label.setStyleSheet("color: white;")
        header_layout.addWidget(self.stage_label)

        # Description
        self.description_label = QLabel("")
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #e0e0e0;")
        header_layout.addWidget(self.description_label)

        # Process button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.process_button = QPushButton("Process Stage")
        self.process_button.setMinimumHeight(40)
        self.process_button.setMinimumWidth(200)
        self.process_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.process_button.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; border-radius: 4px; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #1565C0; }"
            "QPushButton:disabled { background-color: #ccc; }"
        )
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
        self.stack.addWidget(self.franchise_tag_view)

        # Re-signing view (index 1)
        self.resigning_view = ResigningView()
        self.resigning_view.player_resigned.connect(self.player_resigned.emit)
        self.resigning_view.player_released.connect(self.player_released.emit)
        self.resigning_view.cap_validation_changed.connect(self._on_cap_validation_changed)
        self.stack.addWidget(self.resigning_view)

        # Free Agency view (index 2)
        self.free_agency_view = FreeAgencyView()
        self.free_agency_view.player_signed.connect(self.player_signed_fa.emit)
        self.free_agency_view.player_unsigned.connect(self.player_unsigned_fa.emit)
        self.free_agency_view.cap_validation_changed.connect(self._on_fa_cap_validation_changed)
        self.stack.addWidget(self.free_agency_view)

        # Trading view (index 3) - read-only, shows GM trade activity
        self.trading_view = TradingView()
        self.trading_view.cap_validation_changed.connect(self._on_trading_cap_validation_changed)
        self.stack.addWidget(self.trading_view)

        # Draft view (index 4)
        self.draft_view = DraftView()
        self.draft_view.prospect_drafted.connect(self.prospect_drafted.emit)
        self.draft_view.simulate_to_pick_requested.connect(self.simulate_to_pick_requested.emit)
        self.draft_view.auto_draft_all_requested.connect(self.auto_draft_all_requested.emit)
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

        # Preseason placeholder (index 8)
        self.preseason_placeholder = self._create_placeholder_view(
            "Preseason",
            "The Preseason stage completes offseason preparations. Click 'Simulate' to advance to the regular season. "
            "Preseason games are coming in a future update."
        )
        self.stack.addWidget(self.preseason_placeholder)

        parent_layout.addWidget(self.stack, stretch=1)

    def _create_placeholder_view(self, title: str, message: str) -> QWidget:
        """Create a placeholder view for stages not yet implemented."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)

        # Icon or placeholder graphic
        icon_label = QLabel("Coming Soon")
        icon_label.setFont(QFont("Arial", 24, QFont.Bold))
        icon_label.setStyleSheet("color: #ccc;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # Message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setMaximumWidth(500)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet("color: #666; font-size: 14px; padding: 20px;")
        layout.addWidget(message_label)

        # Hint
        hint_label = QLabel("Click 'Simulate' or 'Process' to advance to the next stage.")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("color: #999; font-style: italic; padding-top: 20px;")
        layout.addWidget(hint_label)

        return widget

    def set_stage(self, stage: Stage, preview_data: Dict[str, Any]):
        """
        Update the view for the current offseason stage.

        Args:
            stage: The current offseason stage
            preview_data: Preview data from OffseasonHandler.get_stage_preview()
        """
        self._current_stage = stage

        # Update header
        stage_name = preview_data.get("stage_name", stage.display_name)
        description = preview_data.get("description", "")

        self.stage_label.setText(stage_name)
        self.description_label.setText(description)

        # Update process button text
        self.process_button.setText(f"Process {stage.display_name}")
        self.process_button.setEnabled(True)

        # Switch to appropriate sub-view
        stage_type = stage.stage_type

        # Hide header for Free Agency, show for all other stages
        if stage_type == StageType.OFFSEASON_FREE_AGENCY:
            self.header_frame.setVisible(False)
        else:
            self.header_frame.setVisible(True)

        # Show process button by default (hidden for draft which has its own controls)
        self.process_button.setVisible(True)

        if stage_type == StageType.OFFSEASON_FRANCHISE_TAG:
            self.stack.setCurrentIndex(0)
            taggable_players = preview_data.get("taggable_players", [])
            tag_used = preview_data.get("tag_used", False)

            if taggable_players:
                self.franchise_tag_view.set_taggable_players(taggable_players)
            else:
                self.franchise_tag_view.show_no_taggable_message()

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

        elif stage_type == StageType.OFFSEASON_RESIGNING:
            self.stack.setCurrentIndex(1)
            expiring_players = preview_data.get("expiring_players", [])
            if expiring_players:
                self.resigning_view.set_expiring_players(expiring_players)
            else:
                self.resigning_view.show_no_expiring_message()
            # Update cap data if available
            cap_data = preview_data.get("cap_data")
            if cap_data:
                self.resigning_view.set_cap_data(cap_data)

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

        elif stage_type == StageType.OFFSEASON_ROSTER_CUTS:
            self.stack.setCurrentIndex(5)
            # Populate roster cuts data
            roster_data = preview_data.get("roster_cuts_data", {})
            if roster_data:
                self.roster_cuts_view.set_roster_data(roster_data)
            else:
                # Show with data from preview (handler returns roster_count, not current_size)
                self.roster_cuts_view.set_roster_data({
                    "roster": preview_data.get("roster", []),
                    "current_size": preview_data.get("roster_count", preview_data.get("current_size", 0)),
                    "target_size": preview_data.get("target_size", 53),
                    "cuts_needed": preview_data.get("cuts_needed", 0),
                    "ai_suggestions": preview_data.get("cut_suggestions", preview_data.get("ai_suggestions", [])),
                    "protected_players": preview_data.get("protected_players", [])
                })
            # Update cap data if available
            cap_data = preview_data.get("cap_data")
            if cap_data:
                self.roster_cuts_view.set_cap_data(cap_data)

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
                    "user_claims": preview_data.get("user_claims", [])
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

        elif stage_type == StageType.OFFSEASON_PRESEASON:
            self.stack.setCurrentIndex(8)

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
        1. Cap compliant (can advance to next stage), OR
        2. There are pending cuts marked (let user process them even if still over cap)

        This allows users to make progress by processing marked cuts even when
        they need multiple rounds of cuts to become cap-compliant.
        """
        if self._current_stage and self._current_stage.stage_type == StageType.OFFSEASON_ROSTER_CUTS:
            # Check if there are pending cuts to process
            has_pending_cuts = bool(self.roster_cuts_view.get_cut_player_ids())

            # Enable if cap compliant OR there are pending cuts to process
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
