"""
Strategy Tab Widget for Team View

Displays team strategy, playbook settings, and game plan preferences.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class StrategyTabWidget(QWidget):
    """
    Strategy sub-tab for Team view.

    Displays team strategy settings, playbook configuration, and game plan preferences.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Placeholder layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Team Strategy")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)

        # Description
        description = QLabel(
            "Team strategy and playbook settings will appear here.\n\n"
            "Coming in Phase 3:\n"
            "• Offensive playbook selection\n"
            "• Defensive scheme configuration\n"
            "• Game plan preferences\n"
            "• Situational tendencies\n"
            "• Fourth down aggression\n"
            "• Two-point conversion strategy"
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #666; padding: 20px;")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()

        self.setLayout(layout)
