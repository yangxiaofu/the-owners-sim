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


class OffseasonView(QWidget):
    """
    Container view for all offseason stages.

    Switches between sub-views based on the current stage:
    - Re-signing: ResigningView with expiring contracts table
    - Free Agency: Placeholder (coming soon)
    - Draft: Placeholder (coming soon)
    - Roster Cuts: Placeholder (coming soon)
    - Training Camp: Placeholder (coming soon)
    - Preseason: Placeholder (coming soon)
    """

    # Signals
    player_resigned = Signal(int)  # Forward from ResigningView
    player_released = Signal(int)  # Forward from ResigningView
    process_stage_requested = Signal()  # Emitted when user clicks Process button

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

        # Free Agency placeholder (index 1)
        self.fa_placeholder = self._create_placeholder_view(
            "Free Agency",
            "The Free Agency stage allows you to sign available free agents from other teams. "
            "This feature is coming in a future update."
        )
        self.stack.addWidget(self.fa_placeholder)

        # Draft placeholder (index 2)
        self.draft_placeholder = self._create_placeholder_view(
            "NFL Draft",
            "The NFL Draft stage allows you to select players from the draft class. "
            "This feature is coming in a future update."
        )
        self.stack.addWidget(self.draft_placeholder)

        # Roster Cuts placeholder (index 3)
        self.cuts_placeholder = self._create_placeholder_view(
            "Roster Cuts",
            "The Roster Cuts stage requires you to trim your roster from 90 players to the 53-man limit. "
            "This feature is coming in a future update."
        )
        self.stack.addWidget(self.cuts_placeholder)

        # Training Camp placeholder (index 4)
        self.camp_placeholder = self._create_placeholder_view(
            "Training Camp",
            "Training Camp finalizes your depth charts and prepares your team for the season. "
            "This feature is coming in a future update."
        )
        self.stack.addWidget(self.camp_placeholder)

        # Preseason placeholder (index 5)
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

        if stage_type == StageType.OFFSEASON_RESIGNING:
            self.stack.setCurrentIndex(0)
            expiring_players = preview_data.get("expiring_players", [])
            if expiring_players:
                self.resigning_view.set_expiring_players(expiring_players)
            else:
                self.resigning_view.show_no_expiring_message()

        elif stage_type == StageType.OFFSEASON_FREE_AGENCY:
            self.stack.setCurrentIndex(1)

        elif stage_type == StageType.OFFSEASON_DRAFT:
            self.stack.setCurrentIndex(2)

        elif stage_type == StageType.OFFSEASON_ROSTER_CUTS:
            self.stack.setCurrentIndex(3)

        elif stage_type == StageType.OFFSEASON_TRAINING_CAMP:
            self.stack.setCurrentIndex(4)

        elif stage_type == StageType.OFFSEASON_PRESEASON:
            self.stack.setCurrentIndex(5)

        else:
            # Default to first view
            self.stack.setCurrentIndex(0)

    def get_resigning_view(self) -> ResigningView:
        """Get the re-signing view for direct access."""
        return self.resigning_view

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
