"""
Playoff View - Displays NFL playoff bracket and seeding information.

This view provides a comprehensive display of:
- AFC and NFC playoff seeding (seeds 1-7)
- Tournament bracket showing all playoff rounds
- Game results and advancement

Part of the OOTP-inspired desktop UI (Phase 2 - League Views).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QGroupBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from typing import Optional, List, Dict, Any

from ui.widgets.playoff_bracket_widget import PlayoffBracketWidget


class PlayoffView(QWidget):
    """
    Playoff View - Displays playoff bracket and seeding.

    Shows:
    - AFC/NFC seeding tables (seeds 1-7)
    - Tournament bracket with matchups by round
    - Game results and winner advancement

    Follows OOTP-inspired design with clean data/UI separation.
    """

    def __init__(self, parent: Optional[QWidget] = None, controller=None):
        """
        Initialize the playoff view.

        Args:
            parent: Parent widget
            controller: PlayoffController instance for data access
        """
        super().__init__(parent)
        self.controller = controller

        # UI components
        self.afc_table: Optional[QTableWidget] = None
        self.nfc_table: Optional[QTableWidget] = None
        self.bracket_widget: Optional[PlayoffBracketWidget] = None

        self._setup_ui()

        # Load data if controller is available
        if self.controller:
            self.refresh()

    @property
    def season(self) -> int:
        """Current season year (proxied from parent/main window)."""
        if self.parent() is not None and hasattr(self.parent(), 'season'):
            return self.parent().season
        return 2025  # Fallback for testing/standalone usage

    def _setup_ui(self) -> None:
        """Build the complete UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header section
        header_layout = self._create_header_section()
        main_layout.addLayout(header_layout)

        # Seeding section (AFC/NFC tables side by side)
        seeding_section = self._create_seeding_section()
        main_layout.addWidget(seeding_section)

        # Bracket section (tournament bracket) - for future enhancement
        bracket_section = self._create_bracket_section()
        main_layout.addWidget(bracket_section, stretch=1)

    def _create_header_section(self) -> QHBoxLayout:
        """Create the header section with title."""
        header_layout = QHBoxLayout()

        # Title
        title_label = QLabel("NFL Playoffs")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        return header_layout

    def _create_seeding_section(self) -> QWidget:
        """
        Create the seeding section with AFC/NFC tables.

        Returns:
            QWidget containing seeding tables
        """
        seeding_group = QGroupBox("Playoff Seeding")
        seeding_layout = QHBoxLayout(seeding_group)
        seeding_layout.setSpacing(20)

        # AFC Seeding Table
        afc_container = self._create_conference_table("AFC")
        seeding_layout.addWidget(afc_container)

        # NFC Seeding Table
        nfc_container = self._create_conference_table("NFC")
        seeding_layout.addWidget(nfc_container)

        return seeding_group

    def _create_conference_table(self, conference: str) -> QWidget:
        """
        Create a conference seeding table.

        Args:
            conference: Conference name ('AFC' or 'NFC')

        Returns:
            QWidget containing the table
        """
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Conference label
        conf_label = QLabel(conference)
        conf_label_font = QFont()
        conf_label_font.setBold(True)
        conf_label_font.setPointSize(12)
        conf_label.setFont(conf_label_font)
        conf_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(conf_label)

        # Create table
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Seed", "Team", "Record"])
        table.setAlternatingRowColors(True)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(250)
        table.setMaximumHeight(300)

        # Set column widths
        table.setColumnWidth(0, 60)  # Seed
        table.setColumnWidth(1, 200)  # Team
        table.setColumnWidth(2, 80)  # Record

        layout.addWidget(table)

        # Store reference
        if conference == "AFC":
            self.afc_table = table
        else:
            self.nfc_table = table

        return container

    def _create_bracket_section(self) -> QWidget:
        """
        Create the bracket section showing tournament progression.

        Returns:
            QWidget containing bracket display
        """
        bracket_group = QGroupBox("Playoff Bracket")
        bracket_layout = QVBoxLayout(bracket_group)

        # Create playoff bracket widget
        self.bracket_widget = PlayoffBracketWidget()
        bracket_layout.addWidget(self.bracket_widget)

        return bracket_group

    def refresh(self) -> None:
        """Reload playoff data and update the display."""
        print(f"\n[DEBUG PlayoffView] refresh() called")

        if not self.controller:
            print(f"[DEBUG PlayoffView] Controller is None, showing no data message")
            self._show_no_data_message()
            return

        # Check if playoffs are active
        is_active = self.controller.is_active()
        print(f"[DEBUG PlayoffView] is_active() = {is_active}")

        if not is_active:
            print(f"[DEBUG PlayoffView] Not active, showing not active message")
            self._show_not_active_message()
            return

        try:
            # Get seeding data
            seeding = self.controller.get_seeding()
            print(f"[DEBUG PlayoffView] seeding = {seeding is not None}")

            if seeding:
                self._update_seeding_tables(seeding)
            else:
                print(f"[DEBUG PlayoffView] No seeding, showing no data message")
                self._show_no_data_message()

            # Get bracket data
            bracket_data = self.controller.get_bracket()
            print(f"[DEBUG PlayoffView] bracket_data = {bracket_data is not None}")
            if bracket_data:
                print(f"[DEBUG PlayoffView] bracket_data keys = {list(bracket_data.keys())}")

            if bracket_data:
                # Get game results for each round
                round_results = {
                    'wild_card': self.controller.get_round_games('wild_card'),
                    'divisional': self.controller.get_round_games('divisional'),
                    'conference': self.controller.get_round_games('conference'),
                    'super_bowl': self.controller.get_round_games('super_bowl')
                }
                print(f"[DEBUG PlayoffView] round_results counts:")
                for round_name, games in round_results.items():
                    print(f"  {round_name}: {len(games) if games else 0} games")

                print(f"[DEBUG PlayoffView] Calling _update_bracket_display()")
                self._update_bracket_display(bracket_data, round_results)
                print(f"[DEBUG PlayoffView] _update_bracket_display() completed")

        except Exception as e:
            import traceback
            print(f"[DEBUG PlayoffView] EXCEPTION: {e}")
            traceback.print_exc()
            self._show_error_message(f"Error loading playoff data: {str(e)}")

    def _update_seeding_tables(self, seeding: Dict[str, Any]) -> None:
        """
        Update AFC and NFC seeding tables with data.

        Args:
            seeding: Dictionary with 'afc' and 'nfc' seeding lists
        """
        # Update AFC table
        if 'afc' in seeding and 'seeds' in seeding['afc']:
            self._populate_table(self.afc_table, seeding['afc']['seeds'])

        # Update NFC table
        if 'nfc' in seeding and 'seeds' in seeding['nfc']:
            self._populate_table(self.nfc_table, seeding['nfc']['seeds'])

    def _populate_table(self, table: QTableWidget, seeds: List[Dict[str, Any]]) -> None:
        """
        Populate a seeding table with seed data.

        Args:
            table: QTableWidget to populate
            seeds: List of seed dictionaries
        """
        table.setRowCount(len(seeds))

        for row, seed_info in enumerate(seeds):
            # Seed number
            seed_item = QTableWidgetItem(f"#{seed_info['seed']}")
            seed_item.setTextAlignment(Qt.AlignCenter)
            if seed_info['seed'] == 1:
                font = QFont()
                font.setBold(True)
                seed_item.setFont(font)
            table.setItem(row, 0, seed_item)

            # Team name
            team_item = QTableWidgetItem(seed_info['team_name'])
            team_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if seed_info['seed'] == 1:
                font = QFont()
                font.setBold(True)
                team_item.setFont(font)
            table.setItem(row, 1, team_item)

            # Record
            record_item = QTableWidgetItem(seed_info['record'])
            record_item.setTextAlignment(Qt.AlignCenter)
            if seed_info['seed'] == 1:
                font = QFont()
                font.setBold(True)
                record_item.setFont(font)
            table.setItem(row, 2, record_item)

    def _update_bracket_display(self, bracket_data: Dict[str, Any], round_results: Dict[str, List[Dict]]) -> None:
        """
        Update bracket widget with bracket data and game results.

        Args:
            bracket_data: Complete bracket structure from controller
            round_results: Game results by round
        """
        if self.bracket_widget:
            self.bracket_widget.update_bracket(bracket_data, round_results)

    def _show_not_active_message(self) -> None:
        """Show message when playoffs are not active."""
        if self.afc_table:
            self.afc_table.setRowCount(0)
        if self.nfc_table:
            self.nfc_table.setRowCount(0)

        if self.bracket_widget:
            self.bracket_widget.update_bracket(None, None)

    def _show_no_data_message(self) -> None:
        """Show message when no playoff data is available."""
        if self.afc_table:
            self.afc_table.setRowCount(0)
        if self.nfc_table:
            self.nfc_table.setRowCount(0)

        if self.bracket_widget:
            self.bracket_widget.update_bracket(None, None)

    def _show_error_message(self, message: str) -> None:
        """
        Show error message in the view.

        Args:
            message: Error message to display
        """
        if self.afc_table:
            self.afc_table.setRowCount(0)
        if self.nfc_table:
            self.nfc_table.setRowCount(0)

        if self.bracket_widget:
            self.bracket_widget.update_bracket(None, None)
