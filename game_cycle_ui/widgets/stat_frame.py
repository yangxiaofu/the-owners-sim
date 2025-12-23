"""
StatFrame - Reusable stat display widget with title and value.

Provides two APIs:
1. StatFrame class - Widget-based approach for direct layout addition
2. create_stat_display() - Function-based approach that returns the value label

Usage (Class):
    from game_cycle_ui.widgets import StatFrame

    frame = StatFrame("Cap Space", "$45.2M", color="#2E7D32")
    layout.addWidget(frame)

    # Update value later
    frame.set_value("$32.1M", color="#F57C00")

Usage (Function):
    from game_cycle_ui.widgets.stat_frame import create_stat_display

    value_label = create_stat_display(layout, "Age", "26")

    # Update value later
    value_label.setText("27")
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtGui import QFont

from game_cycle_ui.theme import Typography, FontSizes, TextColors, Colors


class StatFrame(QFrame):
    """
    A compact stat display with title label and value label.

    Replaces the common pattern:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        title = QLabel("Title")
        value = QLabel("Value")
    """

    # Default colors - using hardcoded values to avoid circular import
    _MUTED_COLOR = "#666666"

    def __init__(
        self,
        title: str,
        value: str = "",
        color: str = None,
        parent=None
    ):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Title label
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(f"color: {self._MUTED_COLOR}; font-size: {FontSizes.CAPTION};")
        layout.addWidget(self._title_label)

        # Value label (H4 = 16pt bold)
        self._value_label = QLabel(value)
        Typography.apply(self._value_label, Typography.H4)
        if color:
            self._value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self._value_label)

    @property
    def value_label(self) -> QLabel:
        """Access to value label for direct manipulation."""
        return self._value_label

    @property
    def title_label(self) -> QLabel:
        """Access to title label for direct manipulation."""
        return self._title_label

    def set_value(self, value: str, color: str = None) -> None:
        """Update the displayed value and optionally the color."""
        self._value_label.setText(value)
        if color:
            self._value_label.setStyleSheet(f"color: {color};")

    def set_title(self, title: str) -> None:
        """Update the title text."""
        self._title_label.setText(title)


# =============================================================================
# FUNCTION-BASED API (for dialogs that need to return value label)
# =============================================================================

def create_stat_display(
    parent_layout: QHBoxLayout,
    title: str,
    value: str,
    *,
    value_color: str = None,
    title_font_size: str = None,
    value_font: QFont = None,
) -> QLabel:
    """
    Create a stat display frame with title and value.

    This function-based API is used by dialogs that need direct access to the
    value label for updates. For widget-based usage, see StatFrame class.

    The frame contains a title label (muted gray, small) above a value label
    (larger, bold). The value label is returned so callers can update it later.

    Args:
        parent_layout: QHBoxLayout to add the frame to
        title: Stat title (e.g., "Age", "Overall", "Cap Hit")
        value: Initial stat value (e.g., "26", "85", "$12.5M")
        value_color: Optional hex color for value text (default: white)
        title_font_size: Optional font size for title (default: CAPTION)
        value_font: Optional QFont for value (default: Typography.H5)

    Returns:
        The value QLabel for later updates via setText()

    Example:
        >>> age_label = create_stat_display(layout, "Age", "26")
        >>> # Later...
        >>> age_label.setText("27")
    """
    # Create frame container
    frame = QFrame()
    frame_layout = QVBoxLayout(frame)
    frame_layout.setContentsMargins(0, 0, 0, 0)
    frame_layout.setSpacing(2)

    # Title label (small, muted)
    title_label = QLabel(title)
    title_size = title_font_size or FontSizes.CAPTION
    title_label.setStyleSheet(f"color: {Colors.MUTED}; font-size: {title_size};")
    frame_layout.addWidget(title_label)

    # Value label (larger, bold)
    value_label = QLabel(str(value))
    value_label.setFont(value_font or Typography.H5)
    if value_color:
        value_label.setStyleSheet(f"color: {value_color};")
    frame_layout.addWidget(value_label)

    # Add to parent layout
    parent_layout.addWidget(frame)
    return value_label
