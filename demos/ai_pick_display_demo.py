"""
Demo script for AIPickDisplayWidget - test the draft pick display.

Shows various pick scenarios to validate styling and layout.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from game_cycle_ui.widgets import AIPickDisplayWidget


class DemoWindow(QMainWindow):
    """Demo window for testing the AI pick display widget."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Pick Display Widget Demo")
        self.setGeometry(100, 100, 800, 700)

        # Set dark background
        self.setStyleSheet("QMainWindow { background-color: #0d0d0d; }")

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Create the AI pick display widget
        self.pick_display = AIPickDisplayWidget()
        layout.addWidget(self.pick_display)

        # Test buttons
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setSpacing(8)

        # Sample pick scenarios
        btn1 = QPushButton("QB Pick (Elite)")
        btn1.clicked.connect(self.show_qb_pick)
        btn_layout.addWidget(btn1)

        btn2 = QPushButton("WR Pick (Solid)")
        btn2.clicked.connect(self.show_wr_pick)
        btn_layout.addWidget(btn2)

        btn3 = QPushButton("OL Pick (Project)")
        btn3.clicked.connect(self.show_ol_pick)
        btn_layout.addWidget(btn3)

        btn4 = QPushButton("Late Round Pick")
        btn4.clicked.connect(self.show_late_pick)
        btn_layout.addWidget(btn4)

        btn5 = QPushButton("Clear")
        btn5.clicked.connect(self.pick_display.clear)
        btn_layout.addWidget(btn5)

        layout.addWidget(btn_container)
        layout.addStretch()

        # Style buttons
        for btn in [btn1, btn2, btn3, btn4, btn5]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)

        # Show first pick by default
        self.show_qb_pick()

    def show_qb_pick(self):
        """Show elite QB pick example."""
        pick_data = {
            "team_name": "Dallas Cowboys",
            "team_id": 17,
            "pick_number": 15,
            "round": 1,
            "pick_in_round": 15,
            "prospect_name": "Caleb Williams",
            "position": "QB",
            "college": "USC",
            "overall": 88,
            "needs_met": ["QB", "Leadership"],
            "reasoning": "Franchise quarterback with elite arm talent and mobility. "
                        "Addresses critical need and provides immediate upgrade at the position. "
                        "Best player available aligns perfectly with team needs.",
        }
        self.pick_display.set_pick_data(pick_data)

    def show_wr_pick(self):
        """Show solid WR pick example."""
        pick_data = {
            "team_name": "New England Patriots",
            "team_id": 3,
            "pick_number": 32,
            "round": 1,
            "pick_in_round": 32,
            "prospect_name": "Marvin Harrison Jr.",
            "position": "WR",
            "college": "Ohio State",
            "overall": 76,
            "needs_met": ["WR", "Red Zone Threat"],
            "reasoning": "Elite route runner with exceptional hands and body control. "
                        "Fills high-priority need at wide receiver and gives the offense "
                        "a true number one target.",
        }
        self.pick_display.set_pick_data(pick_data)

    def show_ol_pick(self):
        """Show developmental OL pick example."""
        pick_data = {
            "team_name": "Cleveland Browns",
            "team_id": 7,
            "pick_number": 68,
            "round": 3,
            "pick_in_round": 4,
            "prospect_name": "Joe Alt",
            "position": "OT",
            "college": "Notre Dame",
            "overall": 64,
            "needs_met": ["OT", "Depth"],
            "reasoning": "High-upside developmental tackle with excellent size and athleticism. "
                        "Needs technical refinement but has the tools to become a starter. "
                        "Value pick in round 3.",
        }
        self.pick_display.set_pick_data(pick_data)

    def show_late_pick(self):
        """Show late round depth pick example."""
        pick_data = {
            "team_name": "San Francisco 49ers",
            "team_id": 31,
            "pick_number": 198,
            "round": 6,
            "pick_in_round": 22,
            "prospect_name": "Brock Bowers",
            "position": "TE",
            "college": "Georgia",
            "overall": 52,
            "needs_met": ["TE"],
            "reasoning": "Special teams contributor with untapped potential as a receiving threat. "
                        "Adding depth at tight end for competition in training camp.",
        }
        self.pick_display.set_pick_data(pick_data)


def main():
    """Run the demo application."""
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
