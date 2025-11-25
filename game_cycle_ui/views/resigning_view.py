"""
Re-signing View - Shows expiring contracts for user's team.

Allows the user to see which players have expiring contracts and
decide whether to re-sign them or let them walk to free agency.
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor


class ResigningView(QWidget):
    """
    View for the re-signing stage.

    Shows a table of expiring contracts with action buttons.
    Users can mark players to re-sign or let walk to free agency.
    """

    # Signals emitted when user takes action
    player_resigned = Signal(int)  # player_id
    player_released = Signal(int)  # player_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._expiring_players: List[Dict] = []
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel at top
        self._create_summary_panel(layout)

        # Main table of expiring players
        self._create_players_table(layout)

        # Action instructions
        self._create_instructions(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing cap space and counts."""
        summary_group = QGroupBox("Re-signing Summary")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(30)

        # Cap space
        cap_frame = QFrame()
        cap_layout = QVBoxLayout(cap_frame)
        cap_layout.setContentsMargins(0, 0, 0, 0)

        cap_title = QLabel("Available Cap Space")
        cap_title.setStyleSheet("color: #666; font-size: 11px;")
        cap_layout.addWidget(cap_title)

        self.cap_space_label = QLabel("$0")
        self.cap_space_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.cap_space_label.setStyleSheet("color: #2E7D32;")  # Green
        cap_layout.addWidget(self.cap_space_label)

        summary_layout.addWidget(cap_frame)

        # Expiring contracts count
        expiring_frame = QFrame()
        expiring_layout = QVBoxLayout(expiring_frame)
        expiring_layout.setContentsMargins(0, 0, 0, 0)

        expiring_title = QLabel("Expiring Contracts")
        expiring_title.setStyleSheet("color: #666; font-size: 11px;")
        expiring_layout.addWidget(expiring_title)

        self.expiring_count_label = QLabel("0")
        self.expiring_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        expiring_layout.addWidget(self.expiring_count_label)

        summary_layout.addWidget(expiring_frame)

        # Pending re-signs
        resign_frame = QFrame()
        resign_layout = QVBoxLayout(resign_frame)
        resign_layout.setContentsMargins(0, 0, 0, 0)

        resign_title = QLabel("Pending Re-signs")
        resign_title.setStyleSheet("color: #666; font-size: 11px;")
        resign_layout.addWidget(resign_title)

        self.resign_count_label = QLabel("0")
        self.resign_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.resign_count_label.setStyleSheet("color: #1976D2;")  # Blue
        resign_layout.addWidget(self.resign_count_label)

        summary_layout.addWidget(resign_frame)

        summary_layout.addStretch()

        parent_layout.addWidget(summary_group)

    def _create_players_table(self, parent_layout: QVBoxLayout):
        """Create the main table of expiring players."""
        table_group = QGroupBox("Expiring Contracts")
        table_layout = QVBoxLayout(table_group)

        self.players_table = QTableWidget()
        self.players_table.setColumnCount(7)
        self.players_table.setHorizontalHeaderLabels([
            "Player", "Position", "Age", "OVR", "Salary", "Status", "Action"
        ])

        # Configure table appearance
        header = self.players_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        header.resizeSection(6, 150)  # Action column width

        self.players_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.players_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.players_table.setAlternatingRowColors(True)
        self.players_table.verticalHeader().setVisible(False)

        table_layout.addWidget(self.players_table)
        parent_layout.addWidget(table_group, stretch=1)

    def _create_instructions(self, parent_layout: QVBoxLayout):
        """Create instruction text at the bottom."""
        instructions = QLabel(
            "Click 'Re-sign' to keep a player, or 'Let Go' to allow them to enter free agency. "
            "Re-signed players will receive a new contract. Players you let go will be available "
            "to all teams in the Free Agency stage."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-style: italic; padding: 8px;")
        parent_layout.addWidget(instructions)

    def set_expiring_players(self, players: List[Dict]):
        """
        Populate the table with expiring contract players.

        Args:
            players: List of player dictionaries with:
                - player_id: int
                - name: str
                - position: str
                - age: int
                - overall: int
                - salary: int
                - years_remaining: int
        """
        self._expiring_players = players
        self.expiring_count_label.setText(str(len(players)))
        self.players_table.setRowCount(len(players))

        for row, player in enumerate(players):
            self._populate_row(row, player)

    def set_cap_space(self, cap_space: int):
        """Update the cap space display."""
        formatted = f"${cap_space:,}"
        self.cap_space_label.setText(formatted)

        # Color based on cap space (red if negative)
        if cap_space < 0:
            self.cap_space_label.setStyleSheet("color: #C62828;")  # Red
        else:
            self.cap_space_label.setStyleSheet("color: #2E7D32;")  # Green

    def _populate_row(self, row: int, player: Dict):
        """Populate a single row in the table."""
        player_id = player.get("player_id", 0)

        # Player name
        name_item = QTableWidgetItem(player.get("name", "Unknown"))
        name_item.setData(Qt.UserRole, player_id)
        self.players_table.setItem(row, 0, name_item)

        # Position
        pos_item = QTableWidgetItem(player.get("position", ""))
        pos_item.setTextAlignment(Qt.AlignCenter)
        self.players_table.setItem(row, 1, pos_item)

        # Age
        age = player.get("age", 0)
        age_item = QTableWidgetItem(str(age))
        age_item.setTextAlignment(Qt.AlignCenter)
        # Color code age (red if 30+)
        if age >= 30:
            age_item.setForeground(QColor("#C62828"))  # Red
        self.players_table.setItem(row, 2, age_item)

        # Overall rating
        overall = player.get("overall", 0)
        ovr_item = QTableWidgetItem(str(overall))
        ovr_item.setTextAlignment(Qt.AlignCenter)
        # Color code rating
        if overall >= 85:
            ovr_item.setForeground(QColor("#2E7D32"))  # Green - Elite
        elif overall >= 75:
            ovr_item.setForeground(QColor("#1976D2"))  # Blue - Solid
        self.players_table.setItem(row, 3, ovr_item)

        # Salary
        salary = player.get("salary", 0)
        salary_text = f"${salary:,}" if salary else "N/A"
        salary_item = QTableWidgetItem(salary_text)
        salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.players_table.setItem(row, 4, salary_item)

        # Status (default: Pending)
        status_item = QTableWidgetItem("Pending")
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(QColor("#666"))
        self.players_table.setItem(row, 5, status_item)

        # Action buttons
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        resign_btn = QPushButton("Re-sign")
        resign_btn.setStyleSheet(
            "QPushButton { background-color: #2E7D32; color: white; border-radius: 3px; padding: 4px 8px; }"
            "QPushButton:hover { background-color: #1B5E20; }"
        )
        resign_btn.clicked.connect(lambda checked, pid=player_id, r=row: self._on_resign_clicked(pid, r))
        action_layout.addWidget(resign_btn)

        let_go_btn = QPushButton("Let Go")
        let_go_btn.setStyleSheet(
            "QPushButton { background-color: #C62828; color: white; border-radius: 3px; padding: 4px 8px; }"
            "QPushButton:hover { background-color: #B71C1C; }"
        )
        let_go_btn.clicked.connect(lambda checked, pid=player_id, r=row: self._on_let_go_clicked(pid, r))
        action_layout.addWidget(let_go_btn)

        self.players_table.setCellWidget(row, 6, action_widget)

    def _on_resign_clicked(self, player_id: int, row: int):
        """Handle re-sign button click."""
        # Update status cell
        status_item = self.players_table.item(row, 5)
        if status_item:
            status_item.setText("Re-signing")
            status_item.setForeground(QColor("#2E7D32"))  # Green

        # Update pending count
        self._update_resign_count()

        # Emit signal (for future implementation)
        self.player_resigned.emit(player_id)

    def _on_let_go_clicked(self, player_id: int, row: int):
        """Handle let go button click."""
        # Update status cell
        status_item = self.players_table.item(row, 5)
        if status_item:
            status_item.setText("Free Agent")
            status_item.setForeground(QColor("#C62828"))  # Red

        # Update pending count
        self._update_resign_count()

        # Emit signal (for future implementation)
        self.player_released.emit(player_id)

    def _update_resign_count(self):
        """Update the count of pending re-signs."""
        count = 0
        for row in range(self.players_table.rowCount()):
            status_item = self.players_table.item(row, 5)
            if status_item and status_item.text() == "Re-signing":
                count += 1
        self.resign_count_label.setText(str(count))

    def show_no_expiring_message(self):
        """Show a message when there are no expiring contracts."""
        self.players_table.setRowCount(1)
        self.players_table.setSpan(0, 0, 1, 7)

        message_item = QTableWidgetItem("No expiring contracts for your team")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#666"))
        message_item.setFont(QFont("Arial", 12, QFont.Normal, True))  # Italic

        self.players_table.setItem(0, 0, message_item)
        self.expiring_count_label.setText("0")
