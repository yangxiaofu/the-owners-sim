"""
Season View for The Owner's Sim

Displays season schedule, standings, stats leaders, and playoff picture.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class SeasonView(QWidget):
    """
    Season overview view.

    Phase 1: Placeholder
    Phase 2: Full implementation with schedule, standings, simulation controls
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        # Placeholder layout
        layout = QVBoxLayout()

        title = QLabel("Season View")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)

        description = QLabel(
            "Season schedule, standings, and playoff picture will appear here.\n\n"
            "Coming in Phase 2:\n"
            "• Interactive schedule grid\n"
            "• Division and conference standings\n"
            "• Statistical leaders\n"
            "• Playoff picture tracker\n"
            "• Day/Week simulation controls"
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #666; padding: 20px;")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()

        self.setLayout(layout)
