"""
Season View for The Owner's Sim

Displays season schedule, upcoming games, simulation controls, and playoff picture.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

import sys
import os

# Add parent directories to path
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

from controllers.season_controller import SeasonController


class SeasonView(QWidget):
    """
    Season overview view.

    Displays season schedule, simulation controls, and upcoming games.
    For standings, see League tab.
    """

    def __init__(self, parent=None, controller: SeasonController = None):
        super().__init__(parent)
        self.main_window = parent
        self.controller = controller
        self._setup_ui()

    @property
    def season(self) -> int:
        """Current season year (proxied from parent/main window)."""
        if self.parent() is not None and hasattr(self.parent(), 'season'):
            return self.parent().season
        return 2025  # Fallback for testing/standalone usage

    def _setup_ui(self):
        """Setup UI components."""
        # Placeholder layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Season Schedule & Simulation")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)

        # Description
        description = QLabel(
            "Season schedule, upcoming games, and simulation controls will appear here.\n\n"
            "Coming in Phase 2:\n"
            "• Interactive schedule grid (18-week season)\n"
            "• Upcoming games display\n"
            "• Day/Week simulation controls\n"
            "• Game results and highlights\n"
            "• Playoff picture tracker (Week 10+)\n"
            "• Your team's next game preview\n\n"
            "For league standings, see the League tab →"
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #666; padding: 20px;")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()

        self.setLayout(layout)
