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

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
