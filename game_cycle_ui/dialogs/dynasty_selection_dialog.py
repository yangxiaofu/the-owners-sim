"""
Dynasty Selection Dialog for Game Cycle UI.

Provides UI for creating/selecting dynasties without legacy system dependency.
Uses GameCycleDynastyController which ensures:
- NFLScheduleGenerator creates regular_* format events
- Primetime slots (TNF/SNF/MNF) are assigned during initialization
"""

import uuid
import sys
import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QLineEdit,
    QFormLayout, QMessageBox, QTextEdit, QFrame, QSpinBox,
    QSplitter
)
from PySide6.QtCore import Qt

# Add src to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from game_cycle_ui.controllers.dynasty_controller import GameCycleDynastyController
from game_cycle_ui.widgets.team_gallery_widget import TeamGalleryWidget
from game_cycle_ui.theme import (
    Colors, Typography, FontSizes, TextColors,
    PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, NEUTRAL_BUTTON_STYLE
)
from team_management.teams.team_loader import TeamDataLoader


class GameCycleDynastySelectionDialog(QDialog):
    """
    Dynasty Selection Dialog for Game Cycle.

    Allows users to:
    1. Select an existing dynasty from a list
    2. Create a new dynasty with validation
    3. View dynasty metadata and statistics

    Key difference from legacy DynastySelectionDialog:
    - Uses GameCycleDynastyController (not legacy DynastyController)
    - Dynasty initialization uses GameCycleInitializer
    - Schedule uses NFLScheduleGenerator (regular_* format)
    - Primetime slots are assigned during initialization

    Returns:
        (db_path, dynasty_id, season) if accepted, None if cancelled
    """

    def __init__(self, db_path: str, parent=None):
        """
        Initialize the dialog.

        Args:
            db_path: Path to game_cycle.db database
            parent: Parent widget
        """
        super().__init__(parent)

        self.db_path = db_path
        self.controller = GameCycleDynastyController(db_path)
        self.team_loader = TeamDataLoader()

        # Selection state
        self.selected_dynasty_id = None
        self.selected_season = 2025
        self._selected_team_id = 1

        # Dialog setup
        self.setWindowTitle("Dynasty Selection - The Owner's Sim (Game Cycle)")
        self.setMinimumSize(1100, 700)  # Larger to fit team gallery
        self.setModal(True)

        # Create UI
        self._create_ui()
        self._load_dynasties()

    def _create_ui(self):
        """Create the dialog UI layout with tabbed team selection."""
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Main content - horizontal split with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: Existing dynasties list (narrower)
        left_panel = self._create_dynasty_list_panel()
        splitter.addWidget(left_panel)

        # Right side: Create new dynasty form
        right_panel = self._create_new_dynasty_panel()
        splitter.addWidget(right_panel)

        # Set initial sizes (1:3 ratio)
        splitter.setSizes([250, 750])
        splitter.setHandleWidth(1)

        layout.addWidget(splitter, stretch=1)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.load_button = QPushButton("Load Dynasty")
        self.load_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.load_button.setEnabled(False)
        self.load_button.clicked.connect(self._on_load_dynasty)
        button_layout.addWidget(self.load_button)

        self.create_button = QPushButton("Create New Dynasty")
        self.create_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.create_button.clicked.connect(self._on_create_dynasty)
        button_layout.addWidget(self.create_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet(NEUTRAL_BUTTON_STYLE)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _create_dynasty_list_panel(self):
        """Create the left panel with dynasty list and info."""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame { background: #1a1a1a; border-radius: 8px; }
            QGroupBox {
                border: 1px solid #333333;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                color: #CCCCCC;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header
        header = QLabel("Saved Dynasties")
        header.setFont(Typography.H5)
        header.setStyleSheet("color: #FFFFFF; background: transparent;")
        layout.addWidget(header)

        # Dynasty list widget
        self.dynasty_list = QListWidget()
        self.dynasty_list.setStyleSheet("""
            QListWidget {
                background: #2a2a2a;
                border: 1px solid #333333;
                border-radius: 4px;
                color: #FFFFFF;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:selected {
                background: #3a5a7a;
            }
            QListWidget::item:hover {
                background: #3a3a3a;
            }
        """)
        self.dynasty_list.itemSelectionChanged.connect(self._on_dynasty_selected)
        self.dynasty_list.itemDoubleClicked.connect(self._on_load_dynasty)
        layout.addWidget(self.dynasty_list, stretch=1)

        # Dynasty info display (shown when dynasty selected)
        info_group = QGroupBox("Dynasty Info")
        info_layout = QVBoxLayout(info_group)
        self.info_widget = QTextEdit()
        self.info_widget.setReadOnly(True)
        self.info_widget.setMaximumHeight(120)
        self.info_widget.setStyleSheet("""
            QTextEdit {
                background: #2a2a2a;
                border: none;
                color: #CCCCCC;
            }
        """)
        info_layout.addWidget(self.info_widget)
        layout.addWidget(info_group)

        # Info label
        info_label = QLabel("Double-click to load")
        info_label.setStyleSheet("color: #666666; font-style: italic; background: transparent;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        return panel

    def _create_new_dynasty_panel(self):
        """Create the right panel with new dynasty creation form."""
        panel = QFrame()
        panel.setStyleSheet("QFrame { background: #1a1a1a; border-radius: 8px; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QLabel("Create New Dynasty")
        header.setFont(Typography.H4)
        header.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(header)

        # Form fields in a horizontal row
        form_row = QHBoxLayout()
        form_row.setSpacing(16)

        # Dynasty Name
        name_container = QVBoxLayout()
        name_label = QLabel("Dynasty Name")
        name_label.setStyleSheet("color: #888888;")
        name_label.setFont(Typography.SMALL)
        name_container.addWidget(name_label)
        self.dynasty_name_input = QLineEdit()
        self.dynasty_name_input.setPlaceholderText("e.g., Eagles Dynasty")
        self.dynasty_name_input.setText(f"Test{uuid.uuid4().hex[:8]}")
        self.dynasty_name_input.setStyleSheet("""
            QLineEdit {
                background: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 8px;
                color: #FFFFFF;
            }
            QLineEdit:focus { border-color: #1976D2; }
        """)
        self.dynasty_name_input.textChanged.connect(self._on_name_changed)
        name_container.addWidget(self.dynasty_name_input)
        form_row.addLayout(name_container, stretch=2)

        # Owner Name
        owner_container = QVBoxLayout()
        owner_label = QLabel("Owner Name")
        owner_label.setStyleSheet("color: #888888;")
        owner_label.setFont(Typography.SMALL)
        owner_container.addWidget(owner_label)
        self.owner_name_input = QLineEdit()
        self.owner_name_input.setText("User")
        self.owner_name_input.setPlaceholderText("Your name")
        self.owner_name_input.setStyleSheet("""
            QLineEdit {
                background: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 8px;
                color: #FFFFFF;
            }
            QLineEdit:focus { border-color: #1976D2; }
        """)
        owner_container.addWidget(self.owner_name_input)
        form_row.addLayout(owner_container, stretch=1)

        # Starting Season
        season_container = QVBoxLayout()
        season_label = QLabel("Starting Season")
        season_label.setStyleSheet("color: #888888;")
        season_label.setFont(Typography.SMALL)
        season_container.addWidget(season_label)
        self.season_input = QSpinBox()
        self.season_input.setRange(2000, 2100)
        self.season_input.setValue(2025)
        self.season_input.setStyleSheet("""
            QSpinBox {
                background: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 8px;
                color: #FFFFFF;
            }
            QSpinBox:focus { border-color: #1976D2; }
        """)
        season_container.addWidget(self.season_input)
        form_row.addLayout(season_container, stretch=1)

        layout.addLayout(form_row)

        # Team selection section header
        team_header = QLabel("Select Your Team")
        team_header.setFont(Typography.H5)
        team_header.setStyleSheet("color: #FFFFFF; margin-top: 8px;")
        layout.addWidget(team_header)

        # Team selection gallery (tabbed conference view)
        self.team_gallery = TeamGalleryWidget(self.team_loader)
        self.team_gallery.team_selected.connect(self._on_team_selected)
        layout.addWidget(self.team_gallery, stretch=1)

        # Validation/status message at bottom
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        self.validation_label.setFont(Typography.BODY)
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)

        return panel

    def _load_dynasties(self):
        """Load existing dynasties into the list."""
        self.dynasty_list.clear()

        dynasties = self.controller.list_dynasties()

        if not dynasties:
            item = QListWidgetItem("No existing dynasties found")
            item.setFlags(Qt.ItemFlag.NoItemFlags)  # Make it non-selectable
            self.dynasty_list.addItem(item)
            return

        for dynasty in dynasties:
            display_text = f"{dynasty['dynasty_name']} ({dynasty['dynasty_id']})"
            if dynasty.get('owner_name'):
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
            info_text += f"<b>Owner:</b> {dynasty_info.get('owner_name', 'N/A')}<br>"

            if dynasty_info.get('team_id'):
                team = self.team_loader.get_team_by_id(dynasty_info['team_id'])
                if team:
                    info_text += f"<b>Team:</b> {team.city} {team.nickname}<br>"

            info_text += f"<b>Created:</b> {dynasty_info.get('created_at', 'N/A')}<br>"
            info_text += f"<b>Status:</b> {'Active' if dynasty_info.get('is_active') else 'Inactive'}<br>"
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
            self.validation_label.setText(f"X {error_msg}")
            self.validation_label.setStyleSheet(f"color: {Colors.ERROR};")
        else:
            # Show what the dynasty ID will be
            dynasty_id = self.controller.generate_dynasty_id(name)
            self.validation_label.setText(f"Dynasty ID will be: {dynasty_id}")
            self.validation_label.setStyleSheet(f"color: {Colors.SUCCESS};")

    def _on_team_selected(self, team_id: int):
        """Handle team selection from gallery."""
        self._selected_team_id = team_id
        team = self.team_loader.get_team_by_id(team_id)
        if team:
            self.validation_label.setText(f"Selected: {team.city} {team.nickname}")
            self.validation_label.setStyleSheet(f"color: {Colors.SUCCESS};")

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

        # Get team_id for the selected dynasty
        dynasty_info = self.controller.get_dynasty_info(self.selected_dynasty_id)
        if dynasty_info and dynasty_info.get('team_id'):
            self._selected_team_id = dynasty_info['team_id']

        self.accept()

    def _on_create_dynasty(self):
        """Create a new dynasty."""
        # Validate inputs
        dynasty_name = self.dynasty_name_input.text().strip()
        owner_name = self.owner_name_input.text().strip()
        team_id = self.team_gallery.get_selected_team_id()

        if not dynasty_name:
            QMessageBox.warning(self, "Validation Error", "Please enter a dynasty name.")
            return

        if team_id is None:
            QMessageBox.warning(self, "Validation Error", "Please select a team.")
            return

        if not owner_name:
            owner_name = "User"

        # Get season from spinbox
        season = self.season_input.value()

        # Show progress (creation can take a few seconds)
        self.create_button.setEnabled(False)
        self.create_button.setText("Creating...")
        self.repaint()

        try:
            # Create dynasty using GameCycleDynastyController
            # This uses GameCycleInitializer (NOT legacy DynastyInitializationService)
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
            self._selected_team_id = team_id or 1

            QMessageBox.information(
                self,
                "Dynasty Created",
                f"Successfully created dynasty '{dynasty_name}'!\n\nDynasty ID: {dynasty_id}"
            )

            self.accept()

        finally:
            self.create_button.setEnabled(True)
            self.create_button.setText("Create New Dynasty")

    def get_selection(self):
        """
        Get the selected dynasty information.

        Returns:
            Tuple of (db_path, dynasty_id, season) or None if cancelled
        """
        if self.result() == QDialog.DialogCode.Accepted and self.selected_dynasty_id:
            return (self.db_path, self.selected_dynasty_id, self.selected_season)
        return None