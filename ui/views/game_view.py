"""
Game View for The Owner's Sim

Displays live game simulation with play-by-play commentary and statistics.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class GameView(QWidget):
    """
    Live game simulation view.

    Phase 1: Placeholder
    Phase 2: Full implementation with play-by-play and live stats
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        # Placeholder layout
        layout = QVBoxLayout()

        title = QLabel("Game View")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)

        description = QLabel(
            "Live game simulation will appear here.\n\n"
            "Coming in Phase 2:\n"
            "• Real-time play-by-play commentary\n"
            "• Live scoreboard\n"
            "• Drive summary\n"
            "• Player statistics update\n"
            "• Game flow visualization\n"
            "• Coaching decisions display\n\n"
            "Coming in Phase 5:\n"
            "• Game ticker for multiple games\n"
            "• Score notifications"
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #666; padding: 20px;")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()

        self.setLayout(layout)
