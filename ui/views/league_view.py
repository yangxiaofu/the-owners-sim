"""
League View for The Owner's Sim

Displays league-wide statistics, leaderboards, and team comparisons.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class LeagueView(QWidget):
    """
    League-wide statistics view.

    Phase 1: Placeholder
    Phase 3: Full implementation with league stats and leaderboards
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        # Placeholder layout
        layout = QVBoxLayout()

        title = QLabel("League View")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)

        description = QLabel(
            "League-wide statistics and leaderboards will appear here.\n\n"
            "Coming in Phase 3:\n"
            "• Statistical leaders by category\n"
            "• Team offensive/defensive rankings\n"
            "• League-wide standings\n"
            "• Conference comparisons\n"
            "• Historical records\n"
            "• Advanced analytics\n"
            "• Customizable stat views"
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #666; padding: 20px;")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()

        self.setLayout(layout)
