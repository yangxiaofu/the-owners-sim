"""
Rich hover card widget for displaying extended content on hover.
Styled floating panel similar to GitHub's hover cards.
"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QColor

from game_cycle_ui.theme import Colors


class HoverCard(QWidget):
    """Styled floating card that appears on hover."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._setup_ui()
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def _setup_ui(self):
        """Set up the card UI with styling."""
        # Container with styling
        self.container = QWidget(self)
        self.container.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
            }}
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        # Content label
        self.content_label = QLabel()
        self.content_label.setWordWrap(True)
        self.content_label.setMaximumWidth(300)
        self.content_label.setStyleSheet(f"""
            QLabel {{
                color: #e0e0e0;
                font-size: 13px;
                background: transparent;
                border: none;
                padding: 0px;
            }}
        """)

        layout = QVBoxLayout(self.container)
        layout.addWidget(self.content_label)
        layout.setContentsMargins(12, 10, 12, 10)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)

    def show_at(self, text: str, global_pos: QPoint):
        """Show card with text at global position."""
        self.content_label.setText(text)
        self.adjustSize()

        # Position below and to the right of anchor point
        self.move(global_pos.x() + 10, global_pos.y() + 10)
        self.show()
        self._hide_timer.stop()

    def schedule_hide(self, delay_ms: int = 300):
        """Schedule hiding after delay (allows moving to card)."""
        self._hide_timer.start(delay_ms)

    def cancel_hide(self):
        """Cancel scheduled hide."""
        self._hide_timer.stop()
