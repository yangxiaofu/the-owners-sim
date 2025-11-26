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

from src.game_cycle import Stage, StageType
from .resigning_view import ResigningView
from .free_agency_view import FreeAgencyView
from .draft_view import DraftView
from .roster_cuts_view import RosterCutsView
from .waiver_wire_view import WaiverWireView
from .training_camp_view import TrainingCampView


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
    process_stage_requested = Signal()  # Emitted when user clicks Process button

    # Draft signals (forward from DraftView)
    prospect_drafted = Signal(int)  # prospect_id
    simulate_to_pick_requested = Signal()
    auto_draft_all_requested = Signal()

    # Roster cuts signals (forward from RosterCutsView)
    player_cut = Signal(int)  # player_id
    get_suggestions_requested = Signal()

    # Waiver wire signals (forward from WaiverWireView)
    waiver_claim_submitted = Signal(int)  # player_id
    waiver_claim_cancelled = Signal(int)  # player_id

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
        header_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 4px;")

        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)

        # Stage name (large)
        self.stage_label = QLabel("Offseason")
        self.stage_label.setFont(QFont("Arial", 20, QFont.Bold))
        header_layout.addWidget(self.stage_label)

        # Description
        self.description_label = QLabel("")
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #666;")
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

        parent_layout.addWidget(header_frame)

    def _create_stacked_views(self, parent_layout: QVBoxLayout):
        """Create the stacked widget with sub-views for each stage."""
        self.stack = QStackedWidget()

        # Re-signing view (index 0)
        self.resigning_view = ResigningView()
        self.resigning_view.player_resigned.connect(self.player_resigned.emit)
        self.resigning_view.player_released.connect(self.player_released.emit)
        self.stack.addWidget(self.resigning_view)

        # Free Agency view (index 1)
        self.free_agency_view = FreeAgencyView()
        self.free_agency_view.player_signed.connect(self.player_signed_fa.emit)
        self.stack.addWidget(self.free_agency_view)

        # Draft view (index 2)
        self.draft_view = DraftView()
        self.draft_view.prospect_drafted.connect(self.prospect_drafted.emit)
        self.draft_view.simulate_to_pick_requested.connect(self.simulate_to_pick_requested.emit)
        self.draft_view.auto_draft_all_requested.connect(self.auto_draft_all_requested.emit)
        self.stack.addWidget(self.draft_view)

        # Roster Cuts view (index 3)
        self.roster_cuts_view = RosterCutsView()
        self.roster_cuts_view.player_cut.connect(self.player_cut.emit)
        self.roster_cuts_view.get_suggestions_requested.connect(self.get_suggestions_requested.emit)
        self.stack.addWidget(self.roster_cuts_view)

        # Waiver Wire view (index 4)
        self.waiver_wire_view = WaiverWireView()
        self.waiver_wire_view.claim_submitted.connect(self.waiver_claim_submitted.emit)
        self.waiver_wire_view.claim_cancelled.connect(self.waiver_claim_cancelled.emit)
        self.stack.addWidget(self.waiver_wire_view)

        # Training Camp view (index 5)
        self.training_camp_view = TrainingCampView()
        self.training_camp_view.continue_clicked.connect(self.process_stage_requested.emit)
        self.stack.addWidget(self.training_camp_view)

        # Preseason placeholder (index 6)
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

        # Show process button by default (hidden for draft which has its own controls)
        self.process_button.setVisible(True)

        if stage_type == StageType.OFFSEASON_RESIGNING:
            self.stack.setCurrentIndex(0)
            expiring_players = preview_data.get("expiring_players", [])
            if expiring_players:
                self.resigning_view.set_expiring_players(expiring_players)
            else:
                self.resigning_view.show_no_expiring_message()

        elif stage_type == StageType.OFFSEASON_FREE_AGENCY:
            self.stack.setCurrentIndex(1)
            free_agents = preview_data.get("free_agents", [])
            if free_agents:
                self.free_agency_view.set_free_agents(free_agents)
            else:
                self.free_agency_view.show_no_free_agents_message()
            # Update cap space if available
            cap_space = preview_data.get("cap_space", 0)
            self.free_agency_view.set_cap_space(cap_space)

        elif stage_type == StageType.OFFSEASON_DRAFT:
            self.stack.setCurrentIndex(2)
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

        elif stage_type == StageType.OFFSEASON_ROSTER_CUTS:
            self.stack.setCurrentIndex(3)
            # Populate roster cuts data
            roster_data = preview_data.get("roster_cuts_data", {})
            if roster_data:
                self.roster_cuts_view.set_roster_data(roster_data)
            else:
                # Show with empty data
                self.roster_cuts_view.set_roster_data({
                    "roster": preview_data.get("roster", []),
                    "current_size": preview_data.get("current_size", 0),
                    "target_size": preview_data.get("target_size", 53),
                    "cuts_needed": preview_data.get("cuts_needed", 0),
                    "ai_suggestions": preview_data.get("ai_suggestions", []),
                    "protected_players": preview_data.get("protected_players", [])
                })

        elif stage_type == StageType.OFFSEASON_WAIVER_WIRE:
            self.stack.setCurrentIndex(4)
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

        elif stage_type == StageType.OFFSEASON_TRAINING_CAMP:
            self.stack.setCurrentIndex(5)
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
            self.stack.setCurrentIndex(6)

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

    def get_waiver_wire_view(self) -> WaiverWireView:
        """Get the waiver wire view for direct access."""
        return self.waiver_wire_view

    def get_training_camp_view(self) -> TrainingCampView:
        """Get the training camp view for direct access."""
        return self.training_camp_view

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
