"""
BreakingNewsWidget - ESPN-style Breaking News banner.

Part of Milestone 12: Media Coverage, Tollgate 7.7.

Displays high-priority news with:
- Animated "BREAKING" label
- Red banner styling
- Auto-scrolling text for long headlines
"""

from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont

from game_cycle_ui.theme import (
    ESPN_RED,
    ESPN_DARK_RED,
    ESPN_DARK_BG,
    ESPN_CARD_BG,
    ESPN_TEXT_PRIMARY,
    ESPN_TEXT_SECONDARY,
    ESPN_BORDER,
    Colors,
    FontSizes,
    TextColors,
)

# Convenience alias for breaking news background
ESPN_BREAKING_BG = ESPN_RED
ESPN_TEXT_WHITE = ESPN_TEXT_PRIMARY


class BreakingNewsBanner(QWidget):
    """
    ESPN-style Breaking News banner with animated label.

    Features:
    - Pulsing "BREAKING" badge
    - Scrolling headline text for long content
    - Click to view full story
    """

    clicked = Signal(int)  # headline_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._headline_data: Optional[Dict[str, Any]] = None
        self._headlines_queue: List[Dict[str, Any]] = []
        self._current_index = 0
        self._setup_ui()
        self._setup_timers()

    def _setup_ui(self):
        """Build the banner UI."""
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Hide by default until there's breaking news
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main container
        self._container = QFrame()
        self._container.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_BREAKING_BG};
                border: none;
            }}
        """)

        container_layout = QHBoxLayout(self._container)
        container_layout.setContentsMargins(12, 0, 12, 0)
        container_layout.setSpacing(12)

        # Breaking badge
        self._breaking_badge = QLabel("BREAKING")
        self._breaking_badge.setStyleSheet(f"""
            background-color: {ESPN_TEXT_WHITE};
            color: {ESPN_RED};
            font-size: {FontSizes.SMALL};
            font-weight: bold;
            padding: 4px 8px;
            border-radius: 2px;
            letter-spacing: 1px;
        """)
        self._breaking_badge.setFixedWidth(80)
        self._breaking_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self._breaking_badge)

        # Headline text
        self._headline_label = QLabel("")
        self._headline_label.setStyleSheet(f"""
            color: {TextColors.ON_DARK};
            font-size: {FontSizes.H5};
            font-weight: bold;
        """)
        self._headline_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        container_layout.addWidget(self._headline_label, 1)

        # "READ MORE" link
        self._read_more = QLabel("READ MORE")
        self._read_more.setStyleSheet(f"""
            color: {TextColors.ON_DARK};
            font-size: {FontSizes.SMALL};
            font-weight: bold;
            text-decoration: underline;
            padding-right: 8px;
        """)
        container_layout.addWidget(self._read_more)

        layout.addWidget(self._container)

    def _setup_timers(self):
        """Setup animation timers."""
        # Pulse animation for breaking badge
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_badge)
        self._pulse_visible = True

        # Rotation timer for multiple headlines
        self._rotation_timer = QTimer(self)
        self._rotation_timer.timeout.connect(self._rotate_headline)

    def _pulse_badge(self):
        """Toggle badge visibility for pulsing effect."""
        self._pulse_visible = not self._pulse_visible
        if self._pulse_visible:
            self._breaking_badge.setStyleSheet(f"""
                background-color: {ESPN_TEXT_WHITE};
                color: {ESPN_RED};
                font-size: {FontSizes.SMALL};
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 2px;
                letter-spacing: 1px;
            """)
        else:
            self._breaking_badge.setStyleSheet(f"""
                background-color: {ESPN_DARK_RED};
                color: {TextColors.ON_DARK};
                font-size: {FontSizes.SMALL};
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 2px;
                letter-spacing: 1px;
            """)

    def _rotate_headline(self):
        """Rotate to next headline in queue."""
        if not self._headlines_queue:
            return

        self._current_index = (self._current_index + 1) % len(self._headlines_queue)
        self._headline_data = self._headlines_queue[self._current_index]
        self._update_display()

    def _update_display(self):
        """Update the headline text display."""
        if not self._headline_data:
            self._headline_label.setText("")
            return

        headline = self._headline_data.get("headline", "")
        # Truncate if too long
        if len(headline) > 100:
            headline = headline[:97] + "..."
        self._headline_label.setText(headline)

    def set_breaking_news(self, headlines: List[Dict[str, Any]]):
        """
        Set breaking news headlines to display.

        Only shows headlines with priority >= 80 (high priority).

        Args:
            headlines: List of headline dictionaries
        """
        # Filter for high-priority headlines only
        breaking = [
            h for h in headlines
            if h.get("priority", 0) >= 80
            or h.get("headline_type") in ("UPSET", "TRADE", "INJURY")
        ]

        self._headlines_queue = breaking[:5]  # Max 5 rotating

        if self._headlines_queue:
            self._current_index = 0
            self._headline_data = self._headlines_queue[0]
            self._update_display()
            self.show()
            self._pulse_timer.start(800)  # Pulse every 800ms

            if len(self._headlines_queue) > 1:
                self._rotation_timer.start(5000)  # Rotate every 5 seconds
            else:
                self._rotation_timer.stop()
        else:
            self.hide()
            self._pulse_timer.stop()
            self._rotation_timer.stop()

    def set_single_headline(self, headline_data: Dict[str, Any]):
        """
        Set a single breaking news headline.

        Args:
            headline_data: Headline dictionary
        """
        self._headlines_queue = [headline_data]
        self._current_index = 0
        self._headline_data = headline_data
        self._update_display()
        self.show()
        self._pulse_timer.start(800)
        self._rotation_timer.stop()

    def clear(self):
        """Clear breaking news and hide banner."""
        self._headlines_queue = []
        self._headline_data = None
        self._headline_label.setText("")
        self.hide()
        self._pulse_timer.stop()
        self._rotation_timer.stop()

    def mousePressEvent(self, event):
        """Handle click to emit signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._headline_data:
                headline_id = self._headline_data.get("id", 0)
                self.clicked.emit(headline_id)
        super().mousePressEvent(event)


class AlertBanner(QWidget):
    """
    Simple alert banner for non-breaking updates.

    Used for:
    - Score updates
    - Injury alerts
    - Trade notifications
    """

    dismissed = Signal()

    def __init__(
        self,
        message: str,
        alert_type: str = "info",  # info, warning, success
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._message = message
        self._alert_type = alert_type
        self._setup_ui()

    def _setup_ui(self):
        """Build the alert banner UI."""
        self.setFixedHeight(36)

        # Color based on type
        colors = {
            "info": {"bg": Colors.INFO, "text": Colors.TEXT_INVERSE},
            "warning": {"bg": Colors.WARNING, "text": Colors.TEXT_INVERSE},
            "success": {"bg": Colors.SUCCESS, "text": Colors.TEXT_INVERSE},
            "breaking": {"bg": ESPN_RED, "text": Colors.TEXT_INVERSE},
        }
        style = colors.get(self._alert_type, colors["info"])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {style['bg']};
            }}
        """)

        # Icon based on type
        icons = {
            "info": "i",
            "warning": "!",
            "success": "v",
            "breaking": "!",
        }
        icon_label = QLabel(icons.get(self._alert_type, "i"))
        icon_label.setStyleSheet(f"""
            color: {style['text']};
            font-weight: bold;
            font-size: {FontSizes.H5};
            background-color: rgba(255,255,255,0.2);
            border-radius: 10px;
            padding: 2px 8px;
        """)
        layout.addWidget(icon_label)

        # Message
        message_label = QLabel(self._message)
        message_label.setStyleSheet(f"""
            color: {style['text']};
            font-size: {FontSizes.BODY};
            font-weight: bold;
        """)
        layout.addWidget(message_label, 1)

        # Dismiss button
        dismiss_btn = QLabel("x")
        dismiss_btn.setStyleSheet(f"""
            color: {style['text']};
            font-size: {FontSizes.H5};
            padding: 4px 8px;
        """)
        dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(dismiss_btn)

    def mousePressEvent(self, event):
        """Handle click on dismiss."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dismissed.emit()
            self.hide()
        super().mousePressEvent(event)
