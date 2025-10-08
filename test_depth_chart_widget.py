#!/usr/bin/env python3
"""
Test script for DepthChartWidget

Run this to visually verify the depth chart widget displays correctly.
"""
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from ui.widgets import DepthChartWidget


def main():
    """Launch the depth chart widget test."""
    app = QApplication(sys.argv)

    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Depth Chart Widget Test")
    window.setGeometry(100, 100, 1200, 800)

    # Create and set the depth chart widget
    depth_chart = DepthChartWidget()
    window.setCentralWidget(depth_chart)

    # Apply stylesheet (OOTP-inspired theme)
    try:
        with open("ui/resources/styles/main.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Warning: Could not load stylesheet")

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
