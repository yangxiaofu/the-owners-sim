"""
Main Entry Point for The Owner's Sim (Game Cycle Version)

This is the new stage-based UI that uses src/game_cycle instead of
the day-by-day calendar system.

Architecture:
- Uses SEPARATE database from main.py (game_cycle.db vs nfl_simulation.db)
- Uses GameCycleDynastySelectionDialog (not legacy DynastySelectionDialog)
- Dynasty initialization uses GameCycleInitializer (not legacy DynastyInitializationService)
- Schedule uses NFLScheduleGenerator (regular_* format, not game_YYYYMMDD_*)
- Primetime slots (TNF/SNF/MNF) assigned during initialization

Usage:
    python main2.py
"""

import sys
import os
import logging
from pathlib import Path

# Configure logging to show INFO and above
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

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

# === RUNTIME VERIFICATION (TEMPORARY DEBUG) ===
import game_cycle.handlers.regular_season as rs_module
print("=" * 80)
print("[DEBUG] RUNTIME VERIFICATION")
print("=" * 80)
print(f"[DEBUG] Loaded regular_season from: {rs_module.__file__}")
print(f"[DEBUG] Method signature: {rs_module.RegularSeasonHandler._generate_game_social_posts.__code__.co_varnames[:12]}")
print(f"[DEBUG] Parameter count: {rs_module.RegularSeasonHandler._generate_game_social_posts.__code__.co_argcount}")
print("=" * 80)
print("[DEBUG] Expected: 11 params (self + 10 args including sim_result)")
print("=" * 80)
# === END DEBUG ===

from game_cycle_ui.main_window import GameCycleMainWindow
from game_cycle_ui.dialogs.dynasty_selection_dialog import GameCycleDynastySelectionDialog


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

    # Show dynasty selection dialog (uses GameCycleDynastyController)
    # This dialog uses GameCycleInitializer for dynasty creation, which ensures:
    # - NFLScheduleGenerator creates regular_* format events
    # - PrimetimeScheduler assigns TNF/SNF/MNF slots
    dialog = GameCycleDynastySelectionDialog(db_path=DEFAULT_DB_PATH)
    if dialog.exec() != GameCycleDynastySelectionDialog.DialogCode.Accepted:
        # User cancelled - exit application
        return 0

    # Get selected dynasty
    dynasty_selection = dialog.get_selection()
    if dynasty_selection is None:
        # No selection made - exit application
        return 0

    db_path, dynasty_id, season = dynasty_selection

    # Get user team_id from dynasty selection dialog
    user_team_id = getattr(dialog, '_selected_team_id', 1)

    # Note: Dynasty initialization now happens inside the dialog's controller
    # when creating a new dynasty. No need to call GameCycleInitializer here.

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