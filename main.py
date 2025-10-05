#!/usr/bin/env python3
"""
The Owner's Sim - NFL Management Simulation
Desktop Application Entry Point

OOTP-inspired NFL management simulation game with deep statistical analysis.
"""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow
from ui.dialogs.dynasty_selection_dialog import DynastySelectionDialog


def main():
    """Initialize and run the application."""
    # Enable high DPI scaling for modern displays
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("The Owner's Sim")
    app.setOrganizationName("OwnersSimDev")
    app.setOrganizationDomain("ownerssim.com")

    # Load stylesheet if available
    stylesheet_path = Path(__file__).parent / "ui" / "resources" / "styles" / "main.qss"
    if stylesheet_path.exists():
        with open(stylesheet_path, "r") as f:
            app.setStyleSheet(f.read())

    # Show dynasty selection dialog
    dialog = DynastySelectionDialog()
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
        # Add src to path for imports
        src_path = Path(__file__).parent / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        from database.player_roster_api import PlayerRosterAPI
        from PySide6.QtWidgets import QMessageBox

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
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Dynasty Validation Error",
            f"Failed to validate dynasty '{dynasty_id}':\n\n{str(e)}\n\n"
            f"Please check your database and try again."
        )
        return 1

    # Create and show main window with dynasty context
    window = MainWindow(db_path=db_path, dynasty_id=dynasty_id, season=season)
    window.show()

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
