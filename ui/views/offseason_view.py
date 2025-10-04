"""
Offseason View for The Owner's Sim

Displays offseason dashboard with deadlines, free agency, draft, and roster management.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class OffseasonView(QWidget):
    """
    Offseason management view.

    Phase 1: Placeholder
    Phase 4: Full implementation with offseason dashboard and dialogs
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        # Placeholder layout
        layout = QVBoxLayout()

        title = QLabel("Offseason View")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)

        description = QLabel(
            "Offseason management dashboard will appear here.\n\n"
            "Coming in Phase 4:\n"
            "• Current date and offseason phase display\n"
            "• Deadline countdown timers\n"
            "• Salary cap status panel\n"
            "• Pending free agents list\n"
            "• Action buttons (Franchise Tag, Free Agency, Draft, Cuts)\n"
            "• Transaction feed\n"
            "• Calendar advancement controls\n\n"
            "Dialogs:\n"
            "• Franchise tag selection\n"
            "• Free agent signing\n"
            "• Draft board\n"
            "• Roster cuts"
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #666; padding: 20px;")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()

        self.setLayout(layout)
