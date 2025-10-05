"""
Dynasty Selection Dialog for The Owner's Sim

Professional dialog for selecting existing dynasties or creating new ones.
OOTP-inspired design with dynasty list and creation form.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QLineEdit,
    QFormLayout, QMessageBox, QComboBox, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

import sys
import os

# Add src to path for controller imports
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

from controllers.dynasty_controller import DynastyController

# Add src to path for team imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from team_management.teams.team_loader import TeamDataLoader


class DynastySelectionDialog(QDialog):
    """
    Dynasty Selection Dialog.

    Allows users to:
    1. Select an existing dynasty from a list
    2. Create a new dynasty with validation
    3. View dynasty metadata and statistics

    Returns:
    - (db_path, dynasty_id, season) if accepted
    - None if cancelled
    """

    def __init__(self, db_path: str = "data/database/nfl_simulation.db", parent=None):
        super().__init__(parent)

        self.db_path = db_path
        self.controller = DynastyController(db_path)
        self.team_loader = TeamDataLoader()

        # Selected dynasty info
        self.selected_dynasty_id = None
        self.selected_season = 2025

        # Dialog setup
        self.setWindowTitle("Dynasty Selection - The Owner's Sim")
        self.setMinimumSize(900, 600)
        self.setModal(True)

        # Create UI
        self._create_ui()
        self._load_dynasties()

    def _create_ui(self):
        """Create the dialog UI layout."""
        layout = QVBoxLayout()

        # Title
        title_label = QLabel("Select or Create a Dynasty")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Main content area - horizontal split
        content_layout = QHBoxLayout()

        # Left side: Existing dynasties list
        left_panel = self._create_dynasty_list_panel()
        content_layout.addWidget(left_panel, stretch=2)

        # Right side: Dynasty info / Create new
        right_panel = self._create_info_panel()
        content_layout.addWidget(right_panel, stretch=3)

        layout.addLayout(content_layout)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.load_button = QPushButton("Load Dynasty")
        self.load_button.setEnabled(False)
        self.load_button.clicked.connect(self._on_load_dynasty)
        button_layout.addWidget(self.load_button)

        self.create_button = QPushButton("Create New Dynasty")
        self.create_button.clicked.connect(self._on_create_dynasty)
        button_layout.addWidget(self.create_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _create_dynasty_list_panel(self):
        """Create the left panel with dynasty list."""
        group = QGroupBox("Existing Dynasties")
        layout = QVBoxLayout()

        # Dynasty list widget
        self.dynasty_list = QListWidget()
        self.dynasty_list.itemSelectionChanged.connect(self._on_dynasty_selected)
        self.dynasty_list.itemDoubleClicked.connect(self._on_load_dynasty)
        layout.addWidget(self.dynasty_list)

        # Info label
        info_label = QLabel("Double-click to load a dynasty")
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)

        group.setLayout(layout)
        return group

    def _create_info_panel(self):
        """Create the right panel with dynasty info/creation form."""
        group = QGroupBox("Dynasty Information")
        layout = QVBoxLayout()

        # Dynasty info display (shown when dynasty selected)
        self.info_widget = QTextEdit()
        self.info_widget.setReadOnly(True)
        self.info_widget.setMaximumHeight(150)
        layout.addWidget(self.info_widget)

        # Create new dynasty form
        form_group = QGroupBox("Create New Dynasty")
        form_layout = QFormLayout()

        self.dynasty_name_input = QLineEdit()
        self.dynasty_name_input.setPlaceholderText("Enter dynasty name (e.g., 'Eagles Dynasty')")
        self.dynasty_name_input.textChanged.connect(self._on_name_changed)
        form_layout.addRow("Dynasty Name:", self.dynasty_name_input)

        self.owner_name_input = QLineEdit()
        self.owner_name_input.setText("User")
        self.owner_name_input.setPlaceholderText("Enter your name")
        form_layout.addRow("Owner Name:", self.owner_name_input)

        self.team_combo = QComboBox()
        self.team_combo.addItem("(No Team - Commissioner Mode)", None)
        # Add all 32 NFL teams
        for team in self.team_loader.get_all_teams():
            self.team_combo.addItem(f"{team.city} {team.nickname}", team.team_id)
        form_layout.addRow("Your Team:", self.team_combo)

        self.season_input = QLineEdit()
        self.season_input.setText("2025")
        self.season_input.setPlaceholderText("Starting season (e.g., 2025)")
        form_layout.addRow("Starting Season:", self.season_input)

        # Validation message
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: red;")
        self.validation_label.setWordWrap(True)
        form_layout.addRow("", self.validation_label)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def _load_dynasties(self):
        """Load existing dynasties into the list."""
        self.dynasty_list.clear()

        dynasties = self.controller.list_existing_dynasties()

        if not dynasties:
            item = QListWidgetItem("No existing dynasties found")
            item.setFlags(Qt.ItemFlag.NoItemFlags)  # Make it non-selectable
            self.dynasty_list.addItem(item)
            return

        for dynasty in dynasties:
            display_text = f"{dynasty['dynasty_name']} ({dynasty['dynasty_id']})"
            if dynasty['owner_name']:
                display_text += f" - {dynasty['owner_name']}"

            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, dynasty['dynasty_id'])
            self.dynasty_list.addItem(item)

    def _on_dynasty_selected(self):
        """Handle dynasty selection from list."""
        selected_items = self.dynasty_list.selectedItems()

        if not selected_items:
            self.load_button.setEnabled(False)
            self.info_widget.clear()
            return

        item = selected_items[0]
        dynasty_id = item.data(Qt.ItemDataRole.UserRole)

        if not dynasty_id:
            # This is the "No dynasties" placeholder
            self.load_button.setEnabled(False)
            return

        # Enable load button
        self.load_button.setEnabled(True)
        self.selected_dynasty_id = dynasty_id

        # Load and display dynasty info
        dynasty_info = self.controller.get_dynasty_info(dynasty_id)
        dynasty_stats = self.controller.get_dynasty_stats(dynasty_id)

        if dynasty_info:
            info_text = f"<b>Dynasty:</b> {dynasty_info['dynasty_name']}<br>"
            info_text += f"<b>ID:</b> {dynasty_info['dynasty_id']}<br>"
            info_text += f"<b>Owner:</b> {dynasty_info['owner_name']}<br>"

            if dynasty_info['team_id']:
                team = self.team_loader.get_team_by_id(dynasty_info['team_id'])
                if team:
                    info_text += f"<b>Team:</b> {team.city} {team.nickname}<br>"

            info_text += f"<b>Created:</b> {dynasty_info['created_at']}<br>"
            info_text += f"<b>Status:</b> {'Active' if dynasty_info['is_active'] else 'Inactive'}<br>"
            info_text += "<br>"
            info_text += f"<b>Seasons Played:</b> {dynasty_stats['total_seasons']}<br>"
            info_text += f"<b>Total Games:</b> {dynasty_stats['total_games']}<br>"

            if dynasty_stats['current_season']:
                info_text += f"<b>Current Season:</b> {dynasty_stats['current_season']}"

            self.info_widget.setHtml(info_text)

    def _on_name_changed(self):
        """Validate dynasty name as user types."""
        name = self.dynasty_name_input.text()

        if not name:
            self.validation_label.setText("")
            return

        is_valid, error_msg = self.controller.validate_dynasty_name(name)

        if not is_valid:
            self.validation_label.setText(f"❌ {error_msg}")
            self.validation_label.setStyleSheet("color: red;")
        else:
            # Show what the dynasty ID will be
            dynasty_id = self.controller.generate_unique_dynasty_id(name)
            self.validation_label.setText(f"✓ Dynasty ID will be: {dynasty_id}")
            self.validation_label.setStyleSheet("color: green;")

    def _on_load_dynasty(self):
        """Load the selected dynasty."""
        if not self.selected_dynasty_id:
            QMessageBox.warning(self, "No Dynasty Selected", "Please select a dynasty to load.")
            return

        # Get current season for this dynasty
        dynasty_stats = self.controller.get_dynasty_stats(self.selected_dynasty_id)
        if dynasty_stats['current_season']:
            self.selected_season = dynasty_stats['current_season']
        else:
            self.selected_season = 2025

        self.accept()

    def _on_create_dynasty(self):
        """Create a new dynasty."""
        # Validate inputs
        dynasty_name = self.dynasty_name_input.text().strip()
        owner_name = self.owner_name_input.text().strip()
        team_id = self.team_combo.currentData()

        if not dynasty_name:
            QMessageBox.warning(self, "Validation Error", "Please enter a dynasty name.")
            return

        if not owner_name:
            owner_name = "User"

        # Validate season
        try:
            season = int(self.season_input.text())
            if season < 2000 or season > 2100:
                raise ValueError("Season must be between 2000 and 2100")
        except ValueError as e:
            QMessageBox.warning(self, "Validation Error", f"Invalid season: {str(e)}")
            return

        # Create dynasty
        success, dynasty_id, error_msg = self.controller.create_dynasty(
            dynasty_name=dynasty_name,
            owner_name=owner_name,
            team_id=team_id,
            season=season
        )

        if not success:
            QMessageBox.critical(self, "Creation Failed", f"Failed to create dynasty:\n{error_msg}")
            return

        # Success!
        self.selected_dynasty_id = dynasty_id
        self.selected_season = season

        QMessageBox.information(
            self,
            "Dynasty Created",
            f"Successfully created dynasty '{dynasty_name}'!\n\nDynasty ID: {dynasty_id}"
        )

        self.accept()

    def get_selection(self):
        """
        Get the selected dynasty information.

        Returns:
            Tuple of (db_path, dynasty_id, season) or None if cancelled
        """
        if self.result() == QDialog.DialogCode.Accepted and self.selected_dynasty_id:
            return (self.db_path, self.selected_dynasty_id, self.selected_season)
        return None
