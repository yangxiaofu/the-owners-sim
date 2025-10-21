#!/usr/bin/env python3
"""
The Owner's Sim - Offseason UI Demo Entry Point

Desktop UI demo for testing offseason functionality with placeholder events.
Starts directly in offseason phase with pre-scheduled events.

Features:
- No season simulation needed - starts in offseason
- 3 functional tabs: Offseason, Calendar, Team
- Placeholder event handlers show "Simulating: [Event]" modals
- Separate demo database (offseason_demo.db)
- Mock data: 540+ players, 32 teams, 14 scheduled events

Usage:
    python demo/offseason_demo/main_offseason_demo.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date

# Add project paths
demo_dir = Path(__file__).parent
project_root = demo_dir.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "ui"))

from PySide6.QtWidgets import QApplication, QMessageBox, QLabel
from PySide6.QtCore import Qt

from ui.main_window import MainWindow
from demo.offseason_demo.initialize_demo import DemoInitializer


def configure_demo_window(window: MainWindow) -> None:
    """
    Configure MainWindow for offseason demo mode.

    Changes:
    - Window title includes "Offseason Demo"
    - Status bar shows "DEMO MODE" indicator
    - Only 3 tabs enabled: Calendar (1), Team (2), Offseason (4)
    - All other tabs disabled
    - Simulation toolbar buttons hidden

    Args:
        window: MainWindow instance to configure
    """
    # Update window title
    window.setWindowTitle("The Owner's Sim - Offseason Demo")

    # Add demo indicator to status bar
    demo_indicator = QLabel("  🎮 DEMO MODE - Using placeholder events  ")
    demo_indicator.setStyleSheet(
        "background-color: #ff9800; "
        "color: white; "
        "font-weight: bold; "
        "padding: 2px 10px; "
        "border-radius: 3px;"
    )
    window.statusBar().insertPermanentWidget(0, demo_indicator)

    # Disable non-functional tabs (keep only Calendar, Team, Offseason)
    # Tab indices: 0=Season, 1=Calendar, 2=Team, 3=Player, 4=Offseason, 5=League, 6=Playoffs, 7=Game
    enabled_tabs = {1, 2, 4}  # Calendar, Team, Offseason

    for tab_index in range(window.tabs.count()):
        if tab_index not in enabled_tabs:
            window.tabs.setTabEnabled(tab_index, False)
            # Also hide the tab to make it clearer
            window.tabs.setTabVisible(tab_index, False)

    # Set Calendar tab as default active tab (good entry point for demo)
    window.tabs.setCurrentIndex(1)  # Calendar tab

    # Hide simulation toolbar buttons (not needed for demo)
    toolbar = window.findChild(object, "Main Toolbar")
    if toolbar:
        # Hide first 3 actions (Sim Day, Sim Week, Sim to Phase End)
        actions = toolbar.actions()
        for i in range(min(3, len(actions))):
            actions[i].setVisible(False)

        # Hide separator after simulation buttons
        if len(actions) > 3:
            actions[3].setVisible(False)


def main():
    """Initialize and run the offseason demo application."""
    print("=" * 80)
    print("THE OWNER'S SIM - OFFSEASON UI DEMO")
    print("=" * 80)
    print()

    # Step 1: Initialize database with mock data and scheduled events
    print("Initializing demo database...")
    try:
        initializer = DemoInitializer(
            database_path="data/database/offseason_demo.db",
            dynasty_id="ui_offseason_demo",
            season_year=2024
        )
        db_path = initializer.initialize()
        print(f"✓ Database ready: {db_path}")
        print()
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")
        return 1

    # Step 2: Create PySide6 application
    print("Launching UI...")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("The Owner's Sim - Offseason Demo")
    app.setOrganizationName("OwnersSimDev")
    app.setOrganizationDomain("ownerssim.com")

    # Load stylesheet if available
    stylesheet_path = project_root / "ui" / "resources" / "styles" / "main.qss"
    if stylesheet_path.exists():
        with open(stylesheet_path, "r") as f:
            app.setStyleSheet(f.read())

    # Step 3: Create main window with demo database
    try:
        window = MainWindow(
            db_path=db_path,
            dynasty_id="ui_offseason_demo",
            season=2024  # 2024 season (offseason happens in calendar year 2025)
        )
    except Exception as e:
        QMessageBox.critical(
            None,
            "Demo Initialization Failed",
            f"Failed to create main window:\n\n{str(e)}\n\n"
            f"Please check the error messages above and try again."
        )
        return 1

    # Step 4: Configure window for demo mode
    configure_demo_window(window)

    # Step 5: Show welcome message
    QMessageBox.information(
        window,
        "Welcome to Offseason Demo",
        "<h3>Welcome to The Owner's Sim - Offseason Demo</h3>"
        "<p><b>This is a demonstration mode for testing offseason functionality.</b></p>"
        "<br>"
        "<p><b>What's functional:</b></p>"
        "<ul>"
        "<li><b>Calendar Tab:</b> View scheduled offseason events (Feb 9 - Sept 5, 2025)</li>"
        "<li><b>Team Tab:</b> View mock team rosters and salary cap data</li>"
        "<li><b>Offseason Tab:</b> View offseason phases and upcoming deadlines</li>"
        "</ul>"
        "<br>"
        "<p><b>Placeholder Events:</b></p>"
        "<p>When you trigger an event (like advancing to a deadline), a modal will appear "
        "showing \"Simulating: [Event Name]\". This is a placeholder until the real "
        "event logic is implemented.</p>"
        "<br>"
        "<p><b>Mock Data:</b></p>"
        "<ul>"
        "<li>540+ players across 32 NFL teams</li>"
        "<li>Realistic contracts and salary cap data</li>"
        "<li>14 offseason events from Super Bowl to Season Start</li>"
        "</ul>"
        "<br>"
        "<p><i>This demo uses a separate database (offseason_demo.db) - your regular "
        "dynasty saves are not affected.</i></p>"
    )

    # Step 6: Show main window and run event loop
    window.show()
    print("✓ Demo UI launched successfully")
    print()
    print("Active Tabs:")
    print("  - Calendar: View scheduled offseason events")
    print("  - Team: View mock team rosters and salary cap")
    print("  - Offseason: View offseason phases and deadlines")
    print()
    print("=" * 80)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
