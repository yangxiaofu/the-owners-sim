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

    # Apply database migrations BEFORE showing dynasty dialog
    # This ensures the schema is up-to-date before any dynasty creation
    db_path = "data/database/nfl_simulation.db"  # Default database path

    # Apply salary cap schema migration (idempotent - safe to run multiple times)
    # This creates all 8 salary cap tables including cap_transactions
    try:
        import sqlite3

        migration_path = Path(__file__).parent / "src" / "database" / "migrations" / "002_salary_cap_schema.sql"
        if migration_path.exists():
            conn = sqlite3.connect(db_path)
            try:
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                conn.executescript(migration_sql)
                conn.commit()
                print(f"[INFO] Applied salary cap schema migration: {migration_path.name}")
            finally:
                conn.close()
    except Exception as e:
        print(f"[WARNING] Failed to apply salary cap schema migration: {e}")
        import traceback
        traceback.print_exc()

    # Apply transaction schema migration (idempotent - safe to run multiple times)
    try:
        import sqlite3

        migration_path = Path(__file__).parent / "src" / "database" / "migrations" / "003_player_transactions_table.sql"
        if migration_path.exists():
            conn = sqlite3.connect(db_path)
            try:
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                conn.executescript(migration_sql)
                conn.commit()
                print(f"[INFO] Applied transaction schema migration: {migration_path.name}")
            finally:
                conn.close()
    except Exception as e:
        print(f"[WARNING] Failed to apply transaction schema migration: {e}")
        import traceback
        traceback.print_exc()

    # Apply standings season_type migration (idempotent - safe to run multiple times)
    try:
        import sqlite3

        migration_path = Path(__file__).parent / "src" / "database" / "migrations" / "003_add_season_type_to_standings.sql"
        if migration_path.exists():
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()

                # First, check if standings table exists at all
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='standings'
                """)
                table_exists = cursor.fetchone() is not None

                if not table_exists:
                    print(f"[INFO] Migration 003 skipped: standings table doesn't exist yet (will be created with season_type)")
                else:
                    # Table exists - check if season_type column already exists
                    cursor.execute("PRAGMA table_info(standings)")
                    columns = [row[1] for row in cursor.fetchall()]  # row[1] is column name

                    if 'season_type' in columns:
                        print(f"[INFO] Migration 003 already applied: season_type column exists")
                    else:
                        # Column doesn't exist, apply migration
                        print(f"[INFO] Applying migration 003: adding season_type column to standings...")
                        with open(migration_path, 'r') as f:
                            migration_sql = f.read()
                        conn.executescript(migration_sql)
                        conn.commit()
                        print(f"[INFO] ✅ Applied standings season_type migration: {migration_path.name}")
            finally:
                conn.close()
    except Exception as e:
        print(f"[WARNING] Failed to apply standings season_type migration: {e}")
        import traceback
        traceback.print_exc()

    # Apply standings UNIQUE constraint fix (removes old inline constraint)
    try:
        import sqlite3

        migration_path = Path(__file__).parent / "src" / "database" / "migrations" / "004_fix_standings_unique_constraint.sql"
        if migration_path.exists():
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()

                # First, check if standings table exists at all
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='standings'
                """)
                table_exists = cursor.fetchone() is not None

                if not table_exists:
                    print(f"[INFO] Migration 004 skipped: standings table doesn't exist yet (will be created with correct schema)")
                else:
                    # Check if migration is needed by looking at existing UNIQUE constraints
                    cursor.execute("""
                        SELECT sql FROM sqlite_master
                        WHERE type='index' AND tbl_name='standings' AND name='idx_standings_unique'
                    """)
                    index_sql = cursor.fetchone()

                    # Check if index includes season_type (modern schema)
                    if index_sql and 'season_type' in index_sql[0]:
                        print(f"[INFO] Migration 004 already applied: UNIQUE index includes season_type")
                    else:
                        # Migration needed - apply it
                        print(f"[INFO] Applying migration 004: fixing standings UNIQUE constraint...")
                        with open(migration_path, 'r') as f:
                            migration_sql = f.read()
                        conn.executescript(migration_sql)
                        conn.commit()
                        print(f"[INFO] ✅ Applied standings UNIQUE constraint fix: {migration_path.name}")
            finally:
                conn.close()
    except Exception as e:
        print(f"[WARNING] Failed to apply standings UNIQUE constraint fix: {e}")
        import traceback
        traceback.print_exc()

    # Show dynasty selection dialog (migrations are now complete)
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
