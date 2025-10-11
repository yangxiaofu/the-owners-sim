"""
Toast Notification Widget

Provides non-intrusive popup notifications for user feedback.
"""

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont


class ToastNotification(QWidget):
    """
    Toast notification widget that slides in from top and auto-dismisses.

    Usage:
        toast = ToastNotification.show_success(parent, "Depth chart updated!")
        toast = ToastNotification.show_error(parent, "Failed to save changes")
    """

    # Toast types
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"

    def __init__(self, message: str, toast_type: str = INFO, parent: QWidget = None):
        """
        Initialize toast notification.

        Args:
            message: Message to display
            toast_type: Type of toast (SUCCESS, ERROR, INFO, WARNING)
            parent: Parent widget to position toast relative to
        """
        super().__init__(parent)
        self.message = message
        self.toast_type = toast_type

        self._setup_ui()
        self._apply_styling()

        # Position at top-center of parent
        if parent:
            self.setParent(parent)
            self._position_toast()

        # Set window flags for overlay
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

    def _setup_ui(self):
        """Setup UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Icon label (emoji)
        self.icon_label = QLabel(self._get_icon())
        icon_font = QFont()
        icon_font.setPointSize(14)
        self.icon_label.setFont(icon_font)
        layout.addWidget(self.icon_label)

        # Message label
        self.message_label = QLabel(self.message)
        message_font = QFont()
        message_font.setPointSize(11)
        self.message_label.setFont(message_font)
        self.message_label.setWordWrap(False)
        layout.addWidget(self.message_label)

        # Set fixed height
        self.setFixedHeight(48)
        self.adjustSize()

    def _get_icon(self) -> str:
        """Get icon emoji based on toast type."""
        icons = {
            self.SUCCESS: "✅",
            self.ERROR: "❌",
            self.INFO: "ℹ️",
            self.WARNING: "⚠️"
        }
        return icons.get(self.toast_type, "ℹ️")

    def _apply_styling(self):
        """Apply styling based on toast type."""
        styles = {
            self.SUCCESS: {
                'bg': '#4CAF50',
                'text': '#FFFFFF'
            },
            self.ERROR: {
                'bg': '#F44336',
                'text': '#FFFFFF'
            },
            self.INFO: {
                'bg': '#2196F3',
                'text': '#FFFFFF'
            },
            self.WARNING: {
                'bg': '#FF9800',
                'text': '#FFFFFF'
            }
        }

        style = styles.get(self.toast_type, styles[self.INFO])

        self.setStyleSheet(f"""
            ToastNotification {{
                background-color: {style['bg']};
                border-radius: 8px;
                border: none;
            }}
            QLabel {{
                color: {style['text']};
                background: transparent;
                border: none;
            }}
        """)

    def _position_toast(self):
        """Position toast at top-center of parent (global screen coordinates)."""
        if not self.parent():
            return

        # Calculate global screen position
        parent_global_pos = self.parent().mapToGlobal(self.parent().rect().topLeft())
        parent_width = self.parent().width()

        # Position at top-center, 20px from parent's top edge
        x = parent_global_pos.x() + (parent_width - self.width()) // 2
        y = parent_global_pos.y() + 20

        self.move(x, y)

    def show_animated(self, duration: int = 3000):
        """
        Show toast with slide-in animation and auto-dismiss.

        Args:
            duration: Duration in milliseconds before auto-dismiss (default 3000ms)
        """
        # Initial position (above visible area)
        if self.parent():
            # Calculate global screen position (not parent-relative)
            parent_width = self.parent().width()
            parent_global_pos = self.parent().mapToGlobal(self.parent().rect().topLeft())

            # Center horizontally, position above visible area
            x = parent_global_pos.x() + (parent_width - self.width()) // 2
            y = parent_global_pos.y() - self.height()
            self.move(x, y)

        self.show()

        # Slide-in animation
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(300)
        self.slide_animation.setStartValue(self.pos())

        if self.parent():
            # Target: 20px from parent's top edge (in global coordinates)
            parent_global_pos = self.parent().mapToGlobal(self.parent().rect().topLeft())
            target_x = parent_global_pos.x() + (self.parent().width() - self.width()) // 2
            target_y = parent_global_pos.y() + 20

            from PySide6.QtCore import QPoint
            self.slide_animation.setEndValue(QPoint(target_x, target_y))

        self.slide_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.slide_animation.start()

        # Auto-dismiss after duration
        QTimer.singleShot(duration, self._fade_out)

    def _fade_out(self):
        """Fade out and close toast."""
        # Fade out animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.fade_animation.finished.connect(self.close)
        self.fade_animation.start()

    @classmethod
    def show_success(cls, parent: QWidget, message: str, duration: int = 3000):
        """
        Show success toast.

        Args:
            parent: Parent widget
            message: Success message
            duration: Duration in ms before auto-dismiss
        """
        toast = cls(message, cls.SUCCESS, parent)
        toast.show_animated(duration)
        return toast

    @classmethod
    def show_error(cls, parent: QWidget, message: str, duration: int = 5000):
        """
        Show error toast.

        Args:
            parent: Parent widget
            message: Error message
            duration: Duration in ms before auto-dismiss (default 5s for errors)
        """
        toast = cls(message, cls.ERROR, parent)
        toast.show_animated(duration)
        return toast

    @classmethod
    def show_info(cls, parent: QWidget, message: str, duration: int = 3000):
        """
        Show info toast.

        Args:
            parent: Parent widget
            message: Info message
            duration: Duration in ms before auto-dismiss
        """
        toast = cls(message, cls.INFO, parent)
        toast.show_animated(duration)
        return toast

    @classmethod
    def show_warning(cls, parent: QWidget, message: str, duration: int = 4000):
        """
        Show warning toast.

        Args:
            parent: Parent widget
            message: Warning message
            duration: Duration in ms before auto-dismiss
        """
        toast = cls(message, cls.WARNING, parent)
        toast.show_animated(duration)
        return toast
