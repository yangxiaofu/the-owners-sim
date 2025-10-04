"""
Team View for The Owner's Sim

Displays team roster, depth chart, finances, and coaching staff.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class TeamView(QWidget):
    """
    Team management view.

    Phase 1: Placeholder
    Phase 2: Full implementation with roster, depth chart, finances
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        # Placeholder layout
        layout = QVBoxLayout()

        title = QLabel("Team View")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)

        description = QLabel(
            "Team management interface will appear here.\n\n"
            "Coming in Phase 2:\n"
            "• Complete roster display with stats\n"
            "• Salary cap and contract information\n"
            "• Team selector dropdown\n"
            "• Position filtering\n"
            "• Player search\n\n"
            "Coming in Phase 5:\n"
            "• Drag-and-drop depth chart\n"
            "• Coaching staff management"
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #666; padding: 20px;")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()

        self.setLayout(layout)
