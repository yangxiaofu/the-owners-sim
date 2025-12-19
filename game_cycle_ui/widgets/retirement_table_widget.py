"""
Retirement Table Widget - Displays non-notable retirements in a table format.

Shows player retirements with columns for name, position, age, team, seasons played,
and retirement reason. Supports double-click to view player details.
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from game_cycle_ui.theme import apply_table_style, Colors
from game_cycle_ui.utils.table_utils import NumericTableWidgetItem
from constants.position_abbreviations import get_position_abbreviation
from src.utils.team_utils import get_team_name


class RetirementTableWidget(QTableWidget):
    """
    Widget displaying player retirements in a table format.

    Columns:
        0: Player - Player name (full name)
        1: Position - Position abbreviation (QB, RB, etc.)
        2: Age - Age at retirement (numeric sort)
        3: Team - Final team name
        4: Seasons - Years played in the league (numeric sort)
        5: Reason - Retirement reason text

    Signals:
        player_double_clicked(int, dict): Emitted when player row double-clicked
            Args:
                player_id: Player's unique identifier
                retirement: Full retirement data dict
    """

    # Signal emitted when player double-clicked
    player_double_clicked = Signal(int, dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._retirements: List[Dict] = []
        self._dynasty_id: Optional[str] = None
        self._db_path: str = ""
        self._setup_table()

    def _setup_table(self):
        """Initialize the table with columns and styling."""
        # Set up columns
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "Player", "Position", "Age", "Team", "Seasons", "Reason"
        ])

        # Apply standard ESPN dark table styling
        apply_table_style(self)

        # Enable sorting
        self.setSortingEnabled(True)

        # Configure column resize modes
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Position
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Age
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # Team
        header.resizeSection(3, 150)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Seasons
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # Reason

        # Connect double-click
        self.cellDoubleClicked.connect(self._on_cell_double_clicked)

    def set_context(self, dynasty_id: str, db_path: str):
        """
        Set context for team name lookups.

        Args:
            dynasty_id: Dynasty identifier
            db_path: Path to game_cycle database
        """
        self._dynasty_id = dynasty_id
        self._db_path = db_path

    def set_retirements(self, retirements: List[Dict]):
        """
        Set the retirement data and populate the table.

        Args:
            retirements: List of retirement dictionaries with keys:
                - player_id (int): Player's unique identifier
                - player_name (str): Full player name
                - position (str): Position name
                - age_at_retirement (int): Age when retired
                - final_team_id (int): Team ID of final team
                - years_played (int): Number of seasons in the league
                - retirement_reason (str): Reason for retirement

        Example:
            >>> retirements = [
            ...     {
            ...         "player_id": 12345,
            ...         "player_name": "Tom Brady",
            ...         "position": "QB",
            ...         "age_at_retirement": 45,
            ...         "final_team_id": 29,
            ...         "years_played": 23,
            ...         "retirement_reason": "Age"
            ...     }
            ... ]
            >>> widget.set_retirements(retirements)
        """
        self._retirements = retirements or []
        self._refresh_table()

    def _refresh_table(self):
        """Refresh the table with current retirement data."""
        # Temporarily disable sorting to avoid performance issues during population
        self.setSortingEnabled(False)

        self.setRowCount(len(self._retirements))

        for row, retirement in enumerate(self._retirements):
            self._populate_row(row, retirement)

        # Re-enable sorting
        self.setSortingEnabled(True)

    def _populate_row(self, row: int, retirement: Dict):
        """
        Populate a single table row with retirement data.

        Args:
            row: Row index
            retirement: Retirement data dictionary
        """
        player_id = retirement.get("player_id", 0)
        player_name = retirement.get("player_name", "Unknown Player")
        position = retirement.get("position", "")
        age = retirement.get("age_at_retirement", 0)
        final_team_id = retirement.get("final_team_id", 0)
        years_played = retirement.get("years_played", 0)
        retirement_reason = retirement.get("retirement_reason", "Unknown")

        # Column 0: Player name (store full data for double-click)
        name_item = QTableWidgetItem(player_name)
        name_item.setData(Qt.UserRole, player_id)
        name_item.setData(Qt.UserRole + 1, retirement)
        name_item.setForeground(QColor(Colors.TEXT_INVERSE))
        self.setItem(row, 0, name_item)

        # Column 1: Position
        pos_abbrev = get_position_abbreviation(position)
        pos_item = QTableWidgetItem(pos_abbrev)
        pos_item.setTextAlignment(Qt.AlignCenter)
        pos_item.setForeground(QColor(Colors.INFO))
        self.setItem(row, 1, pos_item)

        # Column 2: Age (NumericTableWidgetItem for proper sorting)
        age_item = NumericTableWidgetItem(age)
        age_item.setTextAlignment(Qt.AlignCenter)
        # Color code by age (older = more red)
        if age >= 40:
            age_item.setForeground(QColor(Colors.ERROR))
        elif age >= 35:
            age_item.setForeground(QColor(Colors.WARNING))
        else:
            age_item.setForeground(QColor(Colors.TEXT_INVERSE))
        self.setItem(row, 2, age_item)

        # Column 3: Team
        team_name = get_team_name(
            final_team_id,
            dynasty_id=self._dynasty_id,
            db_path=self._db_path
        )
        team_item = QTableWidgetItem(team_name)
        team_item.setForeground(QColor("#CCCCCC"))
        self.setItem(row, 3, team_item)

        # Column 4: Seasons (NumericTableWidgetItem for proper sorting)
        seasons_item = NumericTableWidgetItem(years_played)
        seasons_item.setTextAlignment(Qt.AlignCenter)
        # Color code by career length (longer = more green)
        if years_played >= 15:
            seasons_item.setForeground(QColor(Colors.SUCCESS))
        elif years_played >= 10:
            seasons_item.setForeground(QColor(Colors.INFO))
        else:
            seasons_item.setForeground(QColor(Colors.TEXT_INVERSE))
        self.setItem(row, 4, seasons_item)

        # Column 5: Reason
        reason_item = QTableWidgetItem(retirement_reason)
        reason_item.setForeground(QColor("#999999"))
        self.setItem(row, 5, reason_item)

    def _on_cell_double_clicked(self, row: int, column: int):
        """
        Handle double-click to emit player data signal.

        Args:
            row: Row index that was double-clicked
            column: Column index that was double-clicked
        """
        name_item = self.item(row, 0)
        if not name_item:
            return

        player_id = name_item.data(Qt.UserRole)
        retirement_data = name_item.data(Qt.UserRole + 1)

        if player_id and retirement_data:
            self.player_double_clicked.emit(player_id, retirement_data)

    def clear(self):
        """Clear all retirement data from the table."""
        self._retirements = []
        self.setRowCount(0)
