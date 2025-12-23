"""
Demo script for PopularityView widget.

Tests the league-wide popularity rankings view with sample data.

Usage:
    python demos/popularity_view_demo.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from game_cycle_ui.views.popularity_view import PopularityView


class PopularityViewDemoWindow(QMainWindow):
    """Demo window for PopularityView."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Popularity View Demo")
        self.resize(1400, 800)

        # Create central widget
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create PopularityView
        self.popularity_view = PopularityView()

        # Set context (using demo database if it exists)
        db_path = "data/database/game_cycle/game_cycle.db"
        if os.path.exists(db_path):
            dynasty_id = "demo_dynasty"
            season = 2025
            week = 10

            self.popularity_view.set_context(dynasty_id, db_path, season, week)
            self.popularity_view.refresh_rankings()
        else:
            print(f"Database not found: {db_path}")
            print("View created but no data loaded.")

        layout.addWidget(self.popularity_view)
        self.setCentralWidget(central)


def main():
    """Run the demo."""
    app = QApplication(sys.argv)
    window = PopularityViewDemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
