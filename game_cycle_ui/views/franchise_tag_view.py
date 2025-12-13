"""
Franchise Tag View - Shows taggable players for user's team.

Allows the user to see which expiring contract players can be tagged
and decide whether to apply a franchise or transition tag.
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.dialogs import ContractDetailsDialog
from game_cycle_ui.theme import TABLE_HEADER_STYLE
from constants.position_abbreviations import get_position_abbreviation


class FranchiseTagView(QWidget):
    """
    View for the franchise tag stage.

    Shows a table of taggable players with tag cost estimates.
    Users can apply one franchise or transition tag per season.
    """

    # Signal emitted when user applies a tag
    tag_applied = Signal(int, str)  # player_id, tag_type ("franchise" or "transition")

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._taggable_players: List[Dict] = []
        self._tag_used = False
        self._selected_player_id: Optional[int] = None
        self._current_season: int = 2025
        self._next_season: int = 2026
        self._projected_cap_before: int = 0  # Next year's cap before tag
        self._db_path: str = ""
        self._setup_ui()

    def set_db_path(self, db_path: str):
        """Set the database path for contract lookups."""
        self._db_path = db_path

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel at top
        self._create_summary_panel(layout)

        # Main table of taggable players
        self._create_players_table(layout)

        # Tag application controls
        self._create_tag_controls(layout)

        # Instructions
        self._create_instructions(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing cap space and tag info."""
        summary_group = QGroupBox("Franchise Tag Summary")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(20)

        # Current season cap (reference only)
        current_cap_frame = QFrame()
        current_cap_layout = QVBoxLayout(current_cap_frame)
        current_cap_layout.setContentsMargins(0, 0, 0, 0)

        self.current_cap_title = QLabel("Current Cap (2025)")
        self.current_cap_title.setStyleSheet("color: #666; font-size: 11px;")
        current_cap_layout.addWidget(self.current_cap_title)

        self.cap_space_label = QLabel("$0")
        self.cap_space_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.cap_space_label.setStyleSheet("color: #666;")  # Gray - reference only
        current_cap_layout.addWidget(self.cap_space_label)

        summary_layout.addWidget(current_cap_frame)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setStyleSheet("color: #ddd;")
        summary_layout.addWidget(divider)

        # Next year projected cap (where tag actually counts)
        projected_cap_frame = QFrame()
        projected_cap_layout = QVBoxLayout(projected_cap_frame)
        projected_cap_layout.setContentsMargins(0, 0, 0, 0)

        self.projected_cap_title = QLabel("Next Year Cap (2026)")
        self.projected_cap_title.setStyleSheet("color: #666; font-size: 11px;")
        projected_cap_layout.addWidget(self.projected_cap_title)

        self.projected_cap_label = QLabel("$0")
        self.projected_cap_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.projected_cap_label.setStyleSheet("color: #2E7D32;")  # Green - main focus
        projected_cap_layout.addWidget(self.projected_cap_label)

        # Tag impact line (shows after selection)
        self.cap_impact_label = QLabel("")
        self.cap_impact_label.setStyleSheet("color: #F57C00; font-size: 11px;")  # Orange
        projected_cap_layout.addWidget(self.cap_impact_label)

        summary_layout.addWidget(projected_cap_frame)

        # Divider
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.VLine)
        divider2.setStyleSheet("color: #ddd;")
        summary_layout.addWidget(divider2)

        # Taggable players count
        taggable_frame = QFrame()
        taggable_layout = QVBoxLayout(taggable_frame)
        taggable_layout.setContentsMargins(0, 0, 0, 0)

        taggable_title = QLabel("Taggable Players")
        taggable_title.setStyleSheet("color: #666; font-size: 11px;")
        taggable_layout.addWidget(taggable_title)

        self.taggable_count_label = QLabel("0")
        self.taggable_count_label.setFont(QFont("Arial", 14, QFont.Bold))
        taggable_layout.addWidget(self.taggable_count_label)

        summary_layout.addWidget(taggable_frame)

        # Divider
        divider3 = QFrame()
        divider3.setFrameShape(QFrame.VLine)
        divider3.setStyleSheet("color: #ddd;")
        summary_layout.addWidget(divider3)

        # Tag status
        status_frame = QFrame()
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)

        status_title = QLabel("Tag Status")
        status_title.setStyleSheet("color: #666; font-size: 11px;")
        status_layout.addWidget(status_title)

        self.tag_status_label = QLabel("Available")
        self.tag_status_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.tag_status_label.setStyleSheet("color: #2E7D32;")  # Green
        status_layout.addWidget(self.tag_status_label)

        summary_layout.addWidget(status_frame)

        summary_layout.addStretch()

        parent_layout.addWidget(summary_group)

    def _create_players_table(self, parent_layout: QVBoxLayout):
        """Create the main table of taggable players."""
        table_group = QGroupBox("Expiring Contract Players")
        table_layout = QVBoxLayout(table_group)

        self.players_table = QTableWidget()
        self.players_table.setColumnCount(9)
        self.players_table.setHorizontalHeaderLabels([
            "Player", "Position", "Tag Group", "Age", "OVR",
            "Current Cap Hit", "Franchise Tag", "Transition Tag", ""
        ])

        # Configure table appearance
        header = self.players_table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.Fixed)
        header.resizeSection(8, 60)  # View button column

        self.players_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.players_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.players_table.setSelectionMode(QTableWidget.SingleSelection)
        self.players_table.setAlternatingRowColors(True)
        self.players_table.verticalHeader().setVisible(False)

        # Connect selection change
        self.players_table.itemSelectionChanged.connect(self._on_selection_changed)

        table_layout.addWidget(self.players_table)
        parent_layout.addWidget(table_group, stretch=1)

    def _create_tag_controls(self, parent_layout: QVBoxLayout):
        """Create tag application controls."""
        controls_group = QGroupBox("Apply Tag")
        controls_layout = QHBoxLayout(controls_group)
        controls_layout.setSpacing(16)

        # Selected player display
        selected_frame = QFrame()
        selected_layout = QVBoxLayout(selected_frame)
        selected_layout.setContentsMargins(0, 0, 0, 0)

        selected_title = QLabel("Selected Player")
        selected_title.setStyleSheet("color: #666; font-size: 11px;")
        selected_layout.addWidget(selected_title)

        self.selected_player_label = QLabel("None")
        self.selected_player_label.setFont(QFont("Arial", 14, QFont.Bold))
        selected_layout.addWidget(self.selected_player_label)

        controls_layout.addWidget(selected_frame)

        # Tag type dropdown
        tag_type_frame = QFrame()
        tag_type_layout = QVBoxLayout(tag_type_frame)
        tag_type_layout.setContentsMargins(0, 0, 0, 0)

        tag_type_title = QLabel("Tag Type")
        tag_type_title.setStyleSheet("color: #666; font-size: 11px;")
        tag_type_layout.addWidget(tag_type_title)

        self.tag_type_combo = QComboBox()
        self.tag_type_combo.addItems(["Franchise Tag", "Transition Tag"])
        self.tag_type_combo.setMinimumWidth(150)
        tag_type_layout.addWidget(self.tag_type_combo)

        controls_layout.addWidget(tag_type_frame)

        # Tag cost display
        cost_frame = QFrame()
        cost_layout = QVBoxLayout(cost_frame)
        cost_layout.setContentsMargins(0, 0, 0, 0)

        cost_title = QLabel("Tag Cost")
        cost_title.setStyleSheet("color: #666; font-size: 11px;")
        cost_layout.addWidget(cost_title)

        self.tag_cost_label = QLabel("$0")
        self.tag_cost_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.tag_cost_label.setStyleSheet("color: #F57C00;")  # Orange
        cost_layout.addWidget(self.tag_cost_label)

        controls_layout.addWidget(cost_frame)

        controls_layout.addStretch()

        # Apply button
        self.apply_tag_btn = QPushButton("Apply Tag")
        self.apply_tag_btn.setEnabled(False)
        self.apply_tag_btn.setMinimumWidth(120)
        self.apply_tag_btn.setMinimumHeight(40)
        self.apply_tag_btn.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; border-radius: 5px; font-weight: bold; font-size: 14px; }"
            "QPushButton:hover { background-color: #1565C0; }"
            "QPushButton:disabled { background-color: #9E9E9E; }"
        )
        self.apply_tag_btn.clicked.connect(self._on_apply_tag_clicked)
        controls_layout.addWidget(self.apply_tag_btn)

        # Connect combo box change
        self.tag_type_combo.currentIndexChanged.connect(self._on_tag_type_changed)

        parent_layout.addWidget(controls_group)

    def _create_instructions(self, parent_layout: QVBoxLayout):
        """Create instruction text at the bottom."""
        instructions = QLabel(
            "Select a player and apply a Franchise Tag (higher cost, more protection) or "
            "Transition Tag (lower cost, right to match). Each team may use ONE tag per season. "
            "Tagged players cannot enter free agency."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-style: italic; padding: 8px;")
        parent_layout.addWidget(instructions)

    def set_taggable_players(self, players: List[Dict]):
        """
        Populate the table with taggable players.

        Args:
            players: List of player dictionaries with:
                - player_id: int
                - name: str
                - position: str
                - tag_category: str (QB, RB, WR, etc.)
                - age: int
                - overall: int
                - current_cap_hit: int
                - franchise_tag_cost: int
                - transition_tag_cost: int
        """
        self._taggable_players = players
        self.taggable_count_label.setText(str(len(players)))
        self.players_table.setRowCount(len(players))

        for row, player in enumerate(players):
            self._populate_row(row, player)

    def set_tag_used(self, tag_used: bool):
        """Update the tag status display."""
        self._tag_used = tag_used
        if tag_used:
            self.tag_status_label.setText("Used")
            self.tag_status_label.setStyleSheet("color: #C62828;")  # Red
            self.apply_tag_btn.setEnabled(False)
            self.apply_tag_btn.setText("Tag Already Used")
        else:
            self.tag_status_label.setText("Available")
            self.tag_status_label.setStyleSheet("color: #2E7D32;")  # Green

    def set_cap_space(self, cap_space: int):
        """Update the current season cap space display."""
        formatted = f"${cap_space:,}"
        self.cap_space_label.setText(formatted)

        # Gray for current season - it's reference only
        self.cap_space_label.setStyleSheet("color: #666;")

    def set_projected_cap_space(self, cap_space: int):
        """Update the projected next year cap space display."""
        self._projected_cap_before = cap_space
        formatted = f"${cap_space:,}"
        self.projected_cap_label.setText(formatted)

        # Color based on cap space (red if negative, green if positive)
        if cap_space < 0:
            self.projected_cap_label.setStyleSheet("color: #C62828;")  # Red
        else:
            self.projected_cap_label.setStyleSheet("color: #2E7D32;")  # Green

    def set_season_info(self, current_season: int, next_season: int):
        """Update the season labels."""
        self._current_season = current_season
        self._next_season = next_season
        self.current_cap_title.setText(f"Current Cap ({current_season})")
        self.projected_cap_title.setText(f"Next Year Cap ({next_season})")

    def set_cap_data(self, cap_data: Dict):
        """Update the view with full cap data (current season)."""
        available = cap_data.get("available_space", 0)
        self.set_cap_space(available)

    def set_projected_cap_data(self, projected_cap_data: Dict):
        """Update the view with projected next year cap data."""
        available = projected_cap_data.get("available_space", 0)
        self.set_projected_cap_space(available)

    def _populate_row(self, row: int, player: Dict):
        """Populate a single row in the table."""
        player_id = player.get("player_id", 0)

        # Player name
        name_item = QTableWidgetItem(player.get("name", "Unknown"))
        name_item.setData(Qt.UserRole, player_id)
        name_item.setData(Qt.UserRole + 1, player.get("franchise_tag_cost", 0))
        name_item.setData(Qt.UserRole + 2, player.get("transition_tag_cost", 0))
        self.players_table.setItem(row, 0, name_item)

        # Position
        position = player.get("position", "")
        pos_item = QTableWidgetItem(get_position_abbreviation(position))
        pos_item.setTextAlignment(Qt.AlignCenter)
        self.players_table.setItem(row, 1, pos_item)

        # Tag category
        category_item = QTableWidgetItem(player.get("tag_category", ""))
        category_item.setTextAlignment(Qt.AlignCenter)
        category_item.setForeground(QColor("#1976D2"))  # Blue
        self.players_table.setItem(row, 2, category_item)

        # Age
        age = player.get("age", 0)
        age_item = QTableWidgetItem(str(age))
        age_item.setTextAlignment(Qt.AlignCenter)
        # Color code age (red if 30+)
        if age >= 30:
            age_item.setForeground(QColor("#C62828"))  # Red
        self.players_table.setItem(row, 3, age_item)

        # Overall rating
        overall = player.get("overall", 0)
        ovr_item = QTableWidgetItem(str(overall))
        ovr_item.setTextAlignment(Qt.AlignCenter)
        # Color code rating
        if overall >= 85:
            ovr_item.setForeground(QColor("#2E7D32"))  # Green - Elite
        elif overall >= 75:
            ovr_item.setForeground(QColor("#1976D2"))  # Blue - Solid
        self.players_table.setItem(row, 4, ovr_item)

        # Current cap hit
        current_cap = player.get("current_cap_hit", 0)
        current_text = f"${current_cap:,}" if current_cap else "N/A"
        current_item = QTableWidgetItem(current_text)
        current_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.players_table.setItem(row, 5, current_item)

        # Franchise tag cost
        franchise_cost = player.get("franchise_tag_cost", 0)
        franchise_text = f"${franchise_cost:,}" if franchise_cost else "N/A"
        franchise_item = QTableWidgetItem(franchise_text)
        franchise_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        franchise_item.setForeground(QColor("#F57C00"))  # Orange
        self.players_table.setItem(row, 6, franchise_item)

        # Transition tag cost
        transition_cost = player.get("transition_tag_cost", 0)
        transition_text = f"${transition_cost:,}" if transition_cost else "N/A"
        transition_item = QTableWidgetItem(transition_text)
        transition_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        transition_item.setForeground(QColor("#689F38"))  # Light green
        self.players_table.setItem(row, 7, transition_item)

        # View contract button (if contract exists)
        contract_id = player.get("contract_id")
        player_name = player.get("name", "Unknown")
        if contract_id:
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(0)

            view_btn = QPushButton("View")
            view_btn.setStyleSheet(
                "QPushButton { background-color: #1976D2; color: white; border-radius: 3px; padding: 4px 8px; }"
                "QPushButton:hover { background-color: #1565C0; }"
            )
            view_btn.clicked.connect(
                lambda checked, cid=contract_id, pname=player_name: self._on_view_contract(cid, pname)
            )
            action_layout.addWidget(view_btn)
            self.players_table.setCellWidget(row, 8, action_widget)

    def _on_view_contract(self, contract_id: int, player_name: str):
        """Handle view contract button click - opens contract details dialog."""
        if not self._db_path:
            return

        dialog = ContractDetailsDialog(
            player_name=player_name,
            contract_id=contract_id,
            db_path=self._db_path,
            parent=self
        )
        dialog.exec()

    def _on_selection_changed(self):
        """Handle player selection change."""
        selected = self.players_table.selectedItems()
        if not selected or self._tag_used:
            self._selected_player_id = None
            self.selected_player_label.setText("None")
            self.tag_cost_label.setText("$0")
            self.cap_impact_label.setText("")  # Clear cap impact
            self.apply_tag_btn.setEnabled(False)
            return

        # Get selected row
        row = selected[0].row()
        name_item = self.players_table.item(row, 0)

        if name_item:
            self._selected_player_id = name_item.data(Qt.UserRole)
            player_name = name_item.text()
            self.selected_player_label.setText(player_name)

            # Update tag cost and cap impact based on selected tag type
            self._update_tag_cost_display(name_item)
            self.apply_tag_btn.setEnabled(True)

    def _on_tag_type_changed(self, index: int):
        """Handle tag type dropdown change."""
        selected = self.players_table.selectedItems()
        if selected:
            row = selected[0].row()
            name_item = self.players_table.item(row, 0)
            if name_item:
                self._update_tag_cost_display(name_item)

    def _update_tag_cost_display(self, name_item: QTableWidgetItem):
        """Update the tag cost display and cap impact based on selection and tag type."""
        tag_type_index = self.tag_type_combo.currentIndex()

        if tag_type_index == 0:  # Franchise Tag
            cost = name_item.data(Qt.UserRole + 1)
        else:  # Transition Tag
            cost = name_item.data(Qt.UserRole + 2)

        self.tag_cost_label.setText(f"${cost:,}" if cost else "N/A")

        # Update cap impact display and button state
        if cost and self._projected_cap_before > 0:
            projected_after = self._projected_cap_before - cost
            can_afford = projected_after >= 0

            if can_afford:
                self.cap_impact_label.setText(f"After tag: ${projected_after:,}")
                self.cap_impact_label.setStyleSheet("color: #2E7D32; font-size: 11px;")  # Green
                self.apply_tag_btn.setEnabled(True)  # Enable button - can afford
            else:
                self.cap_impact_label.setText(f"After tag: ${projected_after:,} (OVER CAP)")
                self.cap_impact_label.setStyleSheet("color: #C62828; font-size: 11px; font-weight: bold;")  # Red
                self.apply_tag_btn.setEnabled(False)  # DISABLE button - over cap
        else:
            self.cap_impact_label.setText("")
            # If no projected cap data yet, allow the button (backend will validate)
            self.apply_tag_btn.setEnabled(True)

    def _on_apply_tag_clicked(self):
        """Handle apply tag button click."""
        if self._selected_player_id is None or self._tag_used:
            return

        tag_type = "franchise" if self.tag_type_combo.currentIndex() == 0 else "transition"
        self.tag_applied.emit(self._selected_player_id, tag_type)
        # Note: Controller will call set_tag_used(True) after successful application

    def show_no_taggable_message(self):
        """Show a message when there are no taggable players."""
        self.players_table.setRowCount(1)
        self.players_table.setSpan(0, 0, 1, 9)

        message_item = QTableWidgetItem("No expiring contracts for your team")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#666"))
        message_item.setFont(QFont("Arial", 12, QFont.Normal, True))  # Italic

        self.players_table.setItem(0, 0, message_item)
        self.taggable_count_label.setText("0")