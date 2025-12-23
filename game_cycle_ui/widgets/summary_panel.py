"""
SummaryPanel - Reusable summary panel with stat frames.

Usage:
    from game_cycle_ui.widgets import SummaryPanel

    panel = SummaryPanel("Cap Summary")
    cap_label = panel.add_stat("Available Cap", "$45.2M", "#2E7D32")
    used_label = panel.add_stat("Cap Used", "$180.3M", "#1976D2")

    layout.addWidget(panel)

    # Update values later
    cap_label.setText("$32.1M")
"""

from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel
from game_cycle_ui.widgets.stat_frame import StatFrame


class SummaryPanel(QGroupBox):
    """
    A horizontal panel containing multiple stat frames.

    Replaces the common pattern:
        group = QGroupBox("Title")
        layout = QHBoxLayout(group)
        # ... create multiple stat frames
    """

    def __init__(self, title: str = "", parent=None):
        super().__init__(title, parent)

        self._layout = QHBoxLayout(self)
        self._layout.setSpacing(30)  # Standard spacing between stats
        self._frames: list[StatFrame] = []

    def add_stat(
        self,
        title: str,
        value: str = "",
        color: str = None
    ) -> QLabel:
        """
        Add a stat frame to the panel.

        Args:
            title: The stat label (e.g., "Cap Space")
            value: Initial value (e.g., "$45.2M")
            color: Optional hex color for the value

        Returns:
            QLabel: The value label for later updates
        """
        frame = StatFrame(title, value, color)
        self._layout.addWidget(frame)
        self._frames.append(frame)
        return frame.value_label

    def add_stretch(self) -> None:
        """Add stretch to push remaining stats to the right."""
        self._layout.addStretch()

    def get_frame(self, index: int) -> StatFrame:
        """Get a specific stat frame by index."""
        return self._frames[index] if 0 <= index < len(self._frames) else None

    def clear(self) -> None:
        """Remove all stat frames."""
        for frame in self._frames:
            self._layout.removeWidget(frame)
            frame.deleteLater()
        self._frames.clear()
