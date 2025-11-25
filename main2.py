"""
Main Entry Point for The Owner's Sim (Game Cycle Version)

This is the new stage-based UI that uses src/game_cycle instead of
the day-by-day calendar system.

Dynasty-First Architecture:
- Uses the SAME database as main.py (shared dynasties)
- Shows dynasty selection dialog on launch
- All operations scoped to dynasty_id

Usage:
    python main2.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add src to path for backend imports
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from game_cycle_ui.main_window import GameCycleMainWindow
from ui.dialogs.dynasty_selection_dialog import DynastySelectionDialog


# Use SEPARATE database for game_cycle (different from main.py)
# Located in project's data folder for game_cycle development
DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data", "database", "game_cycle", "game_cycle.db"
)


def ensure_db_directory(db_path: str):
    """Ensure the database directory exists."""
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        print(f"[INFO] Created database directory: {db_dir}")


def main():
    """Main entry point with dynasty selection."""
    # Enable high DPI scaling for modern displays
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("The Owner's Sim (Game Cycle)")
    app.setOrganizationName("OwnersSim")
    app.setOrganizationDomain("ownerssim.com")

    # Ensure database directory exists
    ensure_db_directory(DEFAULT_DB_PATH)

    # Show dynasty selection dialog (REUSE from main.py)
    dialog = DynastySelectionDialog(db_path=DEFAULT_DB_PATH)
    if dialog.exec() != DynastySelectionDialog.DialogCode.Accepted:
        # User cancelled - exit application
        return 0

    # Get selected dynasty
    dynasty_selection = dialog.get_selection()
    if dynasty_selection is None:
        # No selection made - exit application
        return 0

    db_path, dynasty_id, season = dynasty_selection

    # Verify dynasty has player rosters in database
    try:
        from database.player_roster_api import PlayerRosterAPI

        roster_api = PlayerRosterAPI(db_path)

        if not roster_api.dynasty_has_rosters(dynasty_id):
            QMessageBox.critical(
                None,
                "Missing Dynasty Data",
                f"Dynasty '{dynasty_id}' has no player rosters in database.\n\n"
                f"This dynasty may be corrupted or incompletely initialized.\n"
                f"Please create a new dynasty."
            )
            return 1

    except Exception as e:
        QMessageBox.critical(
            None,
            "Dynasty Validation Error",
            f"Failed to validate dynasty '{dynasty_id}':\n\n{str(e)}\n\n"
            f"Please check your database and try again."
        )
        return 1

    # Create main window with dynasty context
    window = GameCycleMainWindow(
        db_path=db_path,
        dynasty_id=dynasty_id,
        season=season
    )
    window.show()

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
