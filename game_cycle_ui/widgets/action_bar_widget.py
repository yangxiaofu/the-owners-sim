"""
ActionBarWidget - Navigation and context bar for the main window.

Provides:
- Back button for navigation history
- Breadcrumb trail showing current location
- Next action button with stage-aware suggestions
"""

from typing import Optional, Dict

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QFont

from game_cycle import Stage, StageType
from game_cycle_ui.theme import (
    ESPN_CARD_BG,
    ESPN_BORDER,
    ESPN_TEXT_SECONDARY,
    NEUTRAL_BUTTON_STYLE,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
    DANGER_BUTTON_STYLE,
    FontSizes,
)


# View key to display name mapping
VIEW_DISPLAY_NAMES = {
    "season": "Season",
    "schedule": "Schedule",
    "playoffs": "Playoffs",
    "roster": "Roster",
    "injuries": "Injuries",
    "standings": "Standings",
    "stats": "Stats",
    "grades": "Grades",
    "owner": "Owner",
    "finances": "Finances",
    "inbox": "Inbox",
    "news": "News",
    "transactions": "Transactions",
    "offseason_overview": "Offseason",
    "season_recap": "Season Recap",
}


class ActionBarWidget(QWidget):
    """
    Action bar widget with back button, breadcrumbs, and next action button.

    Signals:
        back_clicked: Emitted when back button is clicked
        next_action_clicked(str): Emitted when next action button is clicked (target view key)
    """

    back_clicked = Signal()
    next_action_clicked = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._current_stage: Optional[Stage] = None
        self._current_view_key: str = "season"

        self._setup_ui()
        self._setup_animations()

    def _setup_ui(self):
        """Setup the action bar UI."""
        self.setStyleSheet(f"""
            QWidget {{
                background: {ESPN_CARD_BG};
                border-bottom: 1px solid {ESPN_BORDER};
            }}
        """)
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # Back button (left)
        self._back_btn = QPushButton("← Back")
        self._back_btn.setStyleSheet(NEUTRAL_BUTTON_STYLE)
        self._back_btn.setEnabled(False)
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self.back_clicked.emit)
        layout.addWidget(self._back_btn)

        # Breadcrumb trail (center-left)
        self._breadcrumb = QLabel("📍 Game Day > Season")
        self._breadcrumb.setStyleSheet(f"""
            color: {ESPN_TEXT_SECONDARY};
            font-size: {FontSizes.BODY};
            background: transparent;
        """)
        layout.addWidget(self._breadcrumb)

        # Spacer to push next action button to the right
        layout.addStretch()

        # Next action button (right)
        self._next_btn = QPushButton("Continue ▶")
        self._next_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(self._on_next_action_clicked)
        layout.addWidget(self._next_btn)

    def _setup_animations(self):
        """Setup pulsing animation for next action button."""
        # Note: QPropertyAnimation with opacity doesn't work well with QPushButton
        # Using a timer-based approach instead for visual pulsing effect
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_next_button)
        self._pulse_state = True
        self._pulse_timer.start(1000)  # Pulse every second

    def _pulse_next_button(self):
        """Pulse the next action button opacity."""
        # Simple pulse effect by toggling font weight
        if self._pulse_state:
            font = self._next_btn.font()
            font.setBold(True)
            self._next_btn.setFont(font)
        else:
            font = self._next_btn.font()
            font.setBold(False)
            self._next_btn.setFont(font)
        self._pulse_state = not self._pulse_state

    def _on_next_action_clicked(self):
        """Handle next action button click."""
        # Get target view from stage mapping (will be implemented via stage_action_mapping.py)
        from game_cycle_ui.widgets.stage_action_mapping import get_action_for_stage

        if self._current_stage:
            action_config = get_action_for_stage(self._current_stage.stage_type)
            target_view = action_config.get("target_view", "season")
            self.next_action_clicked.emit(target_view)
        else:
            # Fallback: navigate to season view
            self.next_action_clicked.emit("season")

    def update_from_stage(self, stage: Optional[Stage], current_view: str):
        """
        Update action bar based on current stage and view.

        Args:
            stage: Current game stage
            current_view: Current view key (e.g., "season", "roster")
        """
        self._current_stage = stage
        self._current_view_key = current_view

        # Update breadcrumb
        self._update_breadcrumb(current_view)

        # Update next action button
        if stage:
            self._update_next_action(stage)

    def _update_breadcrumb(self, view_key: str):
        """Update breadcrumb trail based on current view."""
        # Get category from navigation structure
        from game_cycle_ui.widgets.category_nav_bar import NAVIGATION_STRUCTURE

        category = None
        view_name = VIEW_DISPLAY_NAMES.get(view_key, "Unknown")

        # Find which category contains this view
        for cat_name, cat_config in NAVIGATION_STRUCTURE.items():
            items = cat_config.get("items", [])
            for display_name, vk in items:
                if vk == view_key:
                    category = cat_name
                    break
            if category:
                break

        if category:
            breadcrumb_text = f"📍 {category} > {view_name}"
        else:
            breadcrumb_text = f"📍 {view_name}"

        # Add stage context if available
        if self._current_stage:
            stage_display = self._get_stage_display(self._current_stage)
            if stage_display:
                breadcrumb_text += f" > {stage_display}"

        self._breadcrumb.setText(breadcrumb_text)

    def _get_stage_display(self, stage: Stage) -> str:
        """Get display name for current stage."""
        if stage.stage_type.name.startswith("REGULAR_WEEK_"):
            week_num = stage.stage_type.name.replace("REGULAR_WEEK_", "")
            return f"Week {week_num}"
        elif stage.stage_type == StageType.WILD_CARD:
            return "Wild Card"
        elif stage.stage_type == StageType.DIVISIONAL:
            return "Divisional"
        elif stage.stage_type == StageType.CONFERENCE_CHAMPIONSHIP:
            return "Conference Championship"
        elif stage.stage_type == StageType.SUPER_BOWL:
            return "Super Bowl"
        elif stage.stage_type.name.startswith("OFFSEASON_"):
            offseason_name = stage.stage_type.name.replace("OFFSEASON_", "").replace("_", " ").title()
            return offseason_name
        return ""

    def _update_next_action(self, stage: Stage):
        """Update next action button based on stage."""
        from game_cycle_ui.widgets.stage_action_mapping import get_action_for_stage

        action_config = get_action_for_stage(stage.stage_type)
        action_text = action_config.get("text", "Continue")
        action_style = action_config.get("style", "primary")

        self._next_btn.setText(action_text)

        # Apply style based on urgency
        if action_style == "urgent":
            self._next_btn.setStyleSheet(DANGER_BUTTON_STYLE)
        elif action_style == "action":
            self._next_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        else:
            self._next_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)

    def enable_back_button(self, enabled: bool, previous_view_name: str = ""):
        """
        Enable or disable the back button.

        Args:
            enabled: True to enable, False to disable
            previous_view_name: Display name of previous view for tooltip
        """
        self._back_btn.setEnabled(enabled)
        if enabled and previous_view_name:
            self._back_btn.setToolTip(f"Back to {previous_view_name}")
        else:
            self._back_btn.setToolTip("")

    def get_view_display_name(self, view_key: str) -> str:
        """Get display name for a view key."""
        return VIEW_DISPLAY_NAMES.get(view_key, view_key.replace("_", " ").title())
