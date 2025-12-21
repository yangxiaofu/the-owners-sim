"""
PlayerTableWidget - Base class for player tables with common columns.

Provides consistent implementation of player table columns:
- Player name (with data storage for double-click)
- Position
- Age (NumericTableWidgetItem, color coded: 32+ red, 30-31 orange)
- OVR (NumericTableWidgetItem, color coded: 85+ green, 75+ blue)
- Potential (NumericTableWidgetItem, color coded by upside)
- Dev type (badge style: E/N/L)

Subclasses can add custom columns by overriding:
- _get_custom_column_headers() -> List[str]
- _populate_custom_cells(row, player) -> None
- _create_action_buttons(player) -> QWidget
"""

from abc import abstractmethod
from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from game_cycle_ui.theme import Colors, apply_table_style
from game_cycle_ui.utils.table_utils import NumericTableWidgetItem
from constants.position_abbreviations import get_position_abbreviation
from utils.player_field_extractors import extract_overall_rating


class PlayerTableWidget(QTableWidget):
    """
    Base class for player tables with consistent column handling.

    Common columns (indices 0-5):
        0: Player name
        1: Position
        2: Age
        3: OVR
        4: Potential
        5: Dev

    Subclasses add custom columns after index 5.
    """

    # Signal emitted when player double-clicked
    player_double_clicked = Signal(int, dict)  # player_id, player_data

    # Common column count (before custom columns)
    COMMON_COLUMN_COUNT = 6

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._players: List[Dict] = []
        self._dynasty_id: Optional[str] = None
        self._db_path: str = ""
        self._season: int = 2025
        self._team_name: str = ""
        self._setup_table()

    def _setup_table(self):
        """Initialize the table with common + custom columns."""
        # Get all column headers
        common_headers = ["Player", "Position", "Age", "OVR", "Potential", "Dev"]
        custom_headers = self._get_custom_column_headers()
        all_headers = common_headers + custom_headers

        self.setColumnCount(len(all_headers))
        self.setHorizontalHeaderLabels(all_headers)

        # Apply standard ESPN dark table styling
        apply_table_style(self)

        # Enable numeric sorting
        self.setSortingEnabled(True)

        # Set row height for buttons
        self.verticalHeader().setDefaultSectionSize(44)

        # Configure common column resize modes
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Position
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Age
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # OVR
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Potential
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # Dev
        header.resizeSection(5, 50)

        # Let subclass configure custom column widths
        self._configure_custom_columns(header)

        # Connect double-click
        self.cellDoubleClicked.connect(self._on_cell_double_clicked)

    def set_context(self, dynasty_id: str, db_path: str, season: int, team_name: str = ""):
        """Set context for player detail dialogs."""
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season
        self._team_name = team_name

    def set_players(self, players: List[Dict]):
        """Set the player data and populate the table."""
        self._players = players
        self._refresh_table()

    def _refresh_table(self):
        """Refresh the table with current player data."""
        self.setRowCount(len(self._players))
        for row, player in enumerate(self._players):
            self._populate_row(row, player)

    def _populate_row(self, row: int, player: Dict):
        """Populate a single row with common + custom cells."""
        player_id = player.get("player_id", 0)

        # Column 0: Player name (store full data for double-click)
        name_item = QTableWidgetItem(player.get("name", "Unknown"))
        name_item.setData(Qt.UserRole, player_id)
        name_item.setData(Qt.UserRole + 1, player)
        self.setItem(row, 0, name_item)

        # Column 1: Position
        position = player.get("position", "")
        pos_item = QTableWidgetItem(get_position_abbreviation(position))
        pos_item.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 1, pos_item)

        # Column 2: Age (NumericTableWidgetItem for proper sorting)
        age = player.get("age", 0)
        age_item = NumericTableWidgetItem(age)
        age_item.setTextAlignment(Qt.AlignCenter)
        if age >= 32:
            age_item.setForeground(QColor(Colors.ERROR))
        elif age >= 30:
            age_item.setForeground(QColor(Colors.WARNING))
        self.setItem(row, 2, age_item)

        # Column 3: Overall rating
        overall = extract_overall_rating(player, default=0)
        ovr_item = NumericTableWidgetItem(overall)
        ovr_item.setTextAlignment(Qt.AlignCenter)
        if overall >= 85:
            ovr_item.setForeground(QColor(Colors.SUCCESS))
        elif overall >= 75:
            ovr_item.setForeground(QColor(Colors.INFO))
        self.setItem(row, 3, ovr_item)

        # Column 4: Potential
        potential = player.get("potential", 0)
        potential_item = NumericTableWidgetItem(potential)
        potential_item.setTextAlignment(Qt.AlignCenter)
        if potential > 0:
            upside = potential - overall
            if upside >= 10:
                potential_item.setForeground(QColor(Colors.INFO))
            elif upside <= 2:
                potential_item.setForeground(QColor(Colors.SUCCESS))
        self.setItem(row, 4, potential_item)

        # Column 5: Dev type (badge style)
        dev_type = player.get("dev_type", "Normal")
        dev_map = {"Early": "E", "Normal": "N", "Late": "L"}
        dev_letter = dev_map.get(dev_type, "N")
        dev_item = QTableWidgetItem(dev_letter)
        dev_item.setTextAlignment(Qt.AlignCenter)
        if dev_type == "Early":
            dev_item.setForeground(QColor(Colors.WARNING))
        elif dev_type == "Late":
            dev_item.setForeground(QColor(Colors.INFO))
        else:
            dev_item.setForeground(QColor(Colors.MUTED))
        self.setItem(row, 5, dev_item)

        # Populate custom columns (starting at index 6)
        self._populate_custom_cells(row, player)

    def _on_cell_double_clicked(self, row: int, column: int):
        """Handle double-click to emit player data signal."""
        name_item = self.item(row, 0)
        if not name_item:
            return

        player_id = name_item.data(Qt.UserRole)
        player_data = name_item.data(Qt.UserRole + 1)
        if player_id and player_data:
            self.player_double_clicked.emit(player_id, player_data)

    # =========================================================================
    # Abstract methods for subclasses to override
    # =========================================================================

    @abstractmethod
    def _get_custom_column_headers(self) -> List[str]:
        """
        Return list of custom column headers.

        Example: ["Est. Cap Hit", "Status", "Action"]
        """
        pass

    @abstractmethod
    def _configure_custom_columns(self, header: QHeaderView):
        """
        Configure resize modes for custom columns.

        Args:
            header: The horizontal header to configure
        """
        pass

    @abstractmethod
    def _populate_custom_cells(self, row: int, player: Dict):
        """
        Populate custom column cells for a row.

        Args:
            row: Row index
            player: Player data dictionary
        """
        pass
