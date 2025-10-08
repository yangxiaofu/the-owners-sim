"""
Depth Chart Widget for Team View

Displays team depth chart with position-based cards showing starters and backups.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QGroupBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class PositionCardWidget(QWidget):
    """
    Position card showing depth chart for a specific position.

    Displays position label and up to 2 players (starter + backup).
    """

    def __init__(self, position: str, starter: tuple, backup: tuple, parent=None):
        """
        Initialize position card.

        Args:
            position: Position label (e.g., "QB", "RB", "WR1")
            starter: Tuple of (name, overall_rating)
            backup: Tuple of (name, overall_rating)
        """
        super().__init__(parent)
        self.position = position
        self.starter = starter
        self.backup = backup

        self._setup_ui()

    def _setup_ui(self):
        """Set up the position card UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Position label (header)
        pos_label = QLabel(self.position)
        pos_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        pos_label.setFont(font)
        pos_label.setStyleSheet("""
            QLabel {
                background-color: #e0e0e0;
                color: #333333;
                padding: 6px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                border: 1px solid #cccccc;
                border-bottom: none;
            }
        """)
        layout.addWidget(pos_label)

        # Starter (highlighted background)
        starter_frame = QFrame()
        starter_layout = QVBoxLayout()
        starter_layout.setContentsMargins(4, 4, 4, 4)
        starter_layout.setSpacing(0)

        starter_name = QLabel(f"1. {self.starter[0]}")
        starter_name.setAlignment(Qt.AlignCenter)
        starter_overall = QLabel(f"({self.starter[1]})")
        starter_overall.setAlignment(Qt.AlignCenter)

        starter_layout.addWidget(starter_name)
        starter_layout.addWidget(starter_overall)
        starter_frame.setLayout(starter_layout)
        starter_frame.setStyleSheet("""
            QFrame {
                background-color: #E3F2FD;
                border-left: 1px solid #cccccc;
                border-right: 1px solid #cccccc;
            }
            QLabel {
                color: #333333;
            }
        """)
        layout.addWidget(starter_frame)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("""
            QFrame {
                background-color: #cccccc;
                max-height: 1px;
                border: none;
            }
        """)
        layout.addWidget(separator)

        # Backup (normal background)
        backup_frame = QFrame()
        backup_layout = QVBoxLayout()
        backup_layout.setContentsMargins(4, 4, 4, 4)
        backup_layout.setSpacing(0)

        backup_name = QLabel(f"2. {self.backup[0]}")
        backup_name.setAlignment(Qt.AlignCenter)
        backup_overall = QLabel(f"({self.backup[1]})")
        backup_overall.setAlignment(Qt.AlignCenter)

        backup_layout.addWidget(backup_name)
        backup_layout.addWidget(backup_overall)
        backup_frame.setLayout(backup_layout)
        backup_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-left: 1px solid #cccccc;
                border-right: 1px solid #cccccc;
                border-bottom: 1px solid #cccccc;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QLabel {
                color: #333333;
            }
        """)
        layout.addWidget(backup_frame)

        self.setLayout(layout)
        self.setFixedWidth(100)

        # Overall card styling
        self.setStyleSheet("""
            PositionCardWidget {
                border-radius: 4px;
            }
        """)


class DepthChartWidget(QWidget):
    """
    Depth Chart sub-tab widget for Team View.

    Displays complete team depth chart organized by position with offense,
    defense (3-4 base), and special teams sections.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_mock_data()

    def _setup_ui(self):
        """Set up the main widget layout."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Depth Chart - Detroit Lions")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #333333;")

        scheme_label = QLabel("Scheme: 3-4 Defense")
        scheme_label.setStyleSheet("color: #666666; font-style: italic;")
        scheme_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(scheme_label)

        main_layout.addLayout(header_layout)

        # Scroll area for depth chart sections
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        # Container for all sections
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(15)

        # Offense section
        offense_group = self._create_offense_section()
        container_layout.addWidget(offense_group)

        # Defense section
        defense_group = self._create_defense_section()
        container_layout.addWidget(defense_group)

        # Special Teams section
        special_teams_group = self._create_special_teams_section()
        container_layout.addWidget(special_teams_group)

        container_layout.addStretch()
        container.setLayout(container_layout)
        scroll_area.setWidget(container)

        main_layout.addWidget(scroll_area)

        self.setLayout(main_layout)

    def _create_offense_section(self) -> QGroupBox:
        """Create the offense depth chart section."""
        group = QGroupBox("OFFENSE")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #0066cc;
            }
        """)

        layout = QGridLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Store position cards (will be populated with mock data)
        self.offense_cards = {}

        # Row 1: QB, RB, WR1, WR2
        positions_row1 = ["QB", "RB", "WR1", "WR2"]
        for col, pos in enumerate(positions_row1):
            card = PositionCardWidget(pos, ("TBD", 0), ("TBD", 0))
            self.offense_cards[pos] = card
            layout.addWidget(card, 0, col, Qt.AlignTop)

        # Row 2: TE, LT, LG, C
        positions_row2 = ["TE", "LT", "LG", "C"]
        for col, pos in enumerate(positions_row2):
            card = PositionCardWidget(pos, ("TBD", 0), ("TBD", 0))
            self.offense_cards[pos] = card
            layout.addWidget(card, 1, col, Qt.AlignTop)

        # Row 3: RG, RT
        positions_row3 = ["RG", "RT"]
        for col, pos in enumerate(positions_row3):
            card = PositionCardWidget(pos, ("TBD", 0), ("TBD", 0))
            self.offense_cards[pos] = card
            layout.addWidget(card, 2, col, Qt.AlignTop)

        layout.setColumnStretch(4, 1)  # Push everything to the left

        group.setLayout(layout)
        return group

    def _create_defense_section(self) -> QGroupBox:
        """Create the defense depth chart section (3-4 base)."""
        group = QGroupBox("DEFENSE (3-4 Base)")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #0066cc;
            }
        """)

        layout = QGridLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Store position cards
        self.defense_cards = {}

        # Row 1: DE, DT, DE
        positions_row1 = ["DE", "DT", "DE2"]
        display_names_row1 = ["DE", "DT", "DE"]
        for col, (pos, display) in enumerate(zip(positions_row1, display_names_row1)):
            card = PositionCardWidget(display, ("TBD", 0), ("TBD", 0))
            self.defense_cards[pos] = card
            layout.addWidget(card, 0, col, Qt.AlignTop)

        # Row 2: OLB, ILB, ILB, OLB
        positions_row2 = ["OLB", "ILB", "ILB2", "OLB2"]
        display_names_row2 = ["OLB", "ILB", "ILB", "OLB"]
        for col, (pos, display) in enumerate(zip(positions_row2, display_names_row2)):
            card = PositionCardWidget(display, ("TBD", 0), ("TBD", 0))
            self.defense_cards[pos] = card
            layout.addWidget(card, 1, col, Qt.AlignTop)

        # Row 3: CB, FS, SS, CB
        positions_row3 = ["CB", "FS", "SS", "CB2"]
        display_names_row3 = ["CB", "FS", "SS", "CB"]
        for col, (pos, display) in enumerate(zip(positions_row3, display_names_row3)):
            card = PositionCardWidget(display, ("TBD", 0), ("TBD", 0))
            self.defense_cards[pos] = card
            layout.addWidget(card, 2, col, Qt.AlignTop)

        layout.setColumnStretch(4, 1)  # Push everything to the left

        group.setLayout(layout)
        return group

    def _create_special_teams_section(self) -> QGroupBox:
        """Create the special teams depth chart section."""
        group = QGroupBox("SPECIAL TEAMS")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #0066cc;
            }
        """)

        layout = QHBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Store position cards
        self.special_teams_cards = {}

        # K, P, LS, KR, PR
        positions = ["K", "P", "LS", "KR", "PR"]
        for pos in positions:
            card = PositionCardWidget(pos, ("TBD", 0), ("TBD", 0))
            self.special_teams_cards[pos] = card
            layout.addWidget(card)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def _load_mock_data(self):
        """Load mock depth chart data."""
        # Mock offense data
        offense_data = {
            "QB": ("Stafford", 87, "Hurts", 79),
            "RB": ("Barkley", 91, "Gainwell", 75),
            "WR1": ("A.Brown", 93, "Watkins", 76),
            "WR2": ("D.Smith", 88, "Quez", 73),
            "TE": ("Goedert", 84, "Calcaterra", 72),
            "LT": ("Mailata", 85, "Becton", 74),
            "LG": ("Dickerson", 78, "Sills", 70),
            "C": ("Kelce", 96, "Jurgens", 75),
            "RG": ("Seumalo", 81, "Herbig", 72),
            "RT": ("Johnson", 87, "Driscoll", 69),
        }

        # Update offense cards
        for pos, (starter_name, starter_ovr, backup_name, backup_ovr) in offense_data.items():
            if pos in self.offense_cards:
                # Recreate the card with actual data
                card = PositionCardWidget(
                    pos,
                    (starter_name, starter_ovr),
                    (backup_name, backup_ovr)
                )
                # Replace the placeholder card
                old_card = self.offense_cards[pos]
                layout = old_card.parent().layout()
                index = layout.indexOf(old_card)
                row, col, rowspan, colspan = layout.getItemPosition(index)
                layout.removeWidget(old_card)
                old_card.deleteLater()
                layout.addWidget(card, row, col, Qt.AlignTop)
                self.offense_cards[pos] = card

        # Mock defense data (3-4)
        defense_data = {
            "DE": ("Sweat", 89, "Barnett", 79),
            "DT": ("Cox", 88, "Hargrave", 82),
            "DE2": ("Graham", 85, "Williams", 77),
            "OLB": ("Reddick", 86, "Stevens", 74),
            "ILB": ("White", 83, "Singleton", 76),
            "ILB2": ("Dean", 80, "Edwards", 72),
            "OLB2": ("Carter", 78, "Smith", 71),
            "CB": ("Bradberry", 85, "Maddox", 79),
            "FS": ("Gardner", 81, "Epps", 74),
            "SS": ("Byard", 84, "Scott", 73),
            "CB2": ("Slay", 88, "Goodrich", 76),
        }

        # Update defense cards
        for pos, (starter_name, starter_ovr, backup_name, backup_ovr) in defense_data.items():
            if pos in self.defense_cards:
                display_name = pos.replace("2", "")  # Remove '2' suffix for display
                card = PositionCardWidget(
                    display_name,
                    (starter_name, starter_ovr),
                    (backup_name, backup_ovr)
                )
                old_card = self.defense_cards[pos]
                layout = old_card.parent().layout()
                index = layout.indexOf(old_card)
                row, col, rowspan, colspan = layout.getItemPosition(index)
                layout.removeWidget(old_card)
                old_card.deleteLater()
                layout.addWidget(card, row, col, Qt.AlignTop)
                self.defense_cards[pos] = card

        # Mock special teams data
        special_teams_data = {
            "K": ("Elliott", 83, "Stout", 70),
            "P": ("Siposs", 78, "Arryn", 72),
            "LS": ("Lovato", 82, "Reiter", 74),
            "KR": ("Gainwell", 75, "Scott", 73),
            "PR": ("D.Smith", 88, "Quez", 73),
        }

        # Update special teams cards
        for pos, (starter_name, starter_ovr, backup_name, backup_ovr) in special_teams_data.items():
            if pos in self.special_teams_cards:
                card = PositionCardWidget(
                    pos,
                    (starter_name, starter_ovr),
                    (backup_name, backup_ovr)
                )
                old_card = self.special_teams_cards[pos]
                layout = old_card.parent().layout()
                index = layout.indexOf(old_card)
                layout.removeWidget(old_card)
                old_card.deleteLater()
                layout.addWidget(card)
                self.special_teams_cards[pos] = card
