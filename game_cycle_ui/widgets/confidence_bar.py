"""
Confidence Bar Widget - Visual indicator for GM proposal confidence.

Color-coded progress bar with percentage overlay:
- 0-50%: Red (low confidence)
- 51-75%: Yellow/Orange (medium confidence)
- 76-100%: Green (high confidence)
"""

from typing import Optional

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor

from game_cycle_ui.theme import Colors, TextColors, Typography


class ConfidenceBar(QWidget):
    """
    Progress bar widget showing GM confidence level.

    Color-coded based on confidence value:
    - Red: 0-50% (risky proposal)
    - Orange: 51-75% (moderate confidence)
    - Green: 76-100% (high confidence)
    """

    def __init__(self, confidence: float = 0.0, parent: Optional[QWidget] = None):
        """
        Initialize confidence bar.

        Args:
            confidence: Confidence level (0.0-1.0)
            parent: Parent widget
        """
        super().__init__(parent)
        self._confidence = max(0.0, min(1.0, confidence))  # Clamp to 0.0-1.0
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Label: "GM Confidence:"
        self._label = QLabel("GM Confidence:")
        self._label.setFont(Typography.BODY)
        self._label.setStyleSheet(
            f"color: {TextColors.ON_DARK_SECONDARY}; "
            f"font-weight: 500;"
        )
        layout.addWidget(self._label)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(int(self._confidence * 100))
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat(f"{int(self._confidence * 100)}%")
        self._progress_bar.setFixedHeight(24)
        self._progress_bar.setMinimumWidth(200)

        # Apply color based on confidence level
        self._apply_color_style()

        layout.addWidget(self._progress_bar, stretch=1)

    def _apply_color_style(self):
        """Apply color styling based on confidence level."""
        percentage = int(self._confidence * 100)

        if percentage <= 50:
            # Red - Low confidence
            color = Colors.ERROR
            bg_color = Colors.BG_SECONDARY
        elif percentage <= 75:
            # Orange - Medium confidence
            color = Colors.WARNING
            bg_color = Colors.BG_SECONDARY
        else:
            # Green - High confidence
            color = Colors.SUCCESS
            bg_color = Colors.BG_SECONDARY

        # Style the progress bar
        self._progress_bar.setFont(Typography.BODY_BOLD)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                background-color: {bg_color};
                text-align: center;
                font-weight: bold;
                color: {TextColors.ON_DARK};
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)

    def set_confidence(self, confidence: float):
        """
        Update confidence value and refresh display.

        Args:
            confidence: New confidence level (0.0-1.0)
        """
        self._confidence = max(0.0, min(1.0, confidence))
        percentage = int(self._confidence * 100)
        self._progress_bar.setValue(percentage)
        self._progress_bar.setFormat(f"{percentage}%")
        self._apply_color_style()

    def get_confidence(self) -> float:
        """
        Get current confidence value.

        Returns:
            Confidence level (0.0-1.0)
        """
        return self._confidence
