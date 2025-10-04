"""
Player View for The Owner's Sim

Displays individual player details, statistics, and career history.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class PlayerView(QWidget):
    """
    Player details view.

    Phase 1: Placeholder
    Phase 3: Full implementation with player stats and career history
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        # Placeholder layout
        layout = QVBoxLayout()

        title = QLabel("Player View")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)

        description = QLabel(
            "Player details and statistics will appear here.\n\n"
            "Coming in Phase 3:\n"
            "• Player information card\n"
            "• Career statistics table\n"
            "• Contract details\n"
            "• Season-by-season breakdown\n"
            "• Awards and achievements\n"
            "• Player comparison tools"
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #666; padding: 20px;")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()

        self.setLayout(layout)
