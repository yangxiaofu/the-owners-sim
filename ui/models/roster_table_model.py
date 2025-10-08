"""
Roster Table Model for The Owner's Sim UI

Qt table model for displaying team roster data in table views.
"""

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QColor
from typing import List, Optional, Any, Dict


class RosterTableModel(QAbstractTableModel):
    """
    Qt table model for displaying team roster.

    Displays player roster information in a sortable table format with
    checkboxes for selection and color coding for ratings and status.

    Features:
    - 9 columns: Sel (checkbox), #, Name, Pos, Age, OVR, Contract, Salary, Stat
    - Mock data: 20 hardcoded sample players covering all positions
    - Color-coded overall ratings (90+: Blue, 80-89: Green, etc.)
    - Status-based row coloring (ACT: green, IR: red, PUP: orange)
    - Sortable by all columns
    """

    # Column indices
    COL_SEL = 0
    COL_NUMBER = 1
    COL_NAME = 2
    COL_POSITION = 3
    COL_AGE = 4
    COL_OVERALL = 5
    COL_CONTRACT = 6
    COL_SALARY = 7
    COL_STATUS = 8

    # Status colors
    STATUS_COLORS = {
        'ACT': QColor("#E8F5E9"),    # Light green - Active
        'IR': QColor("#FFEBEE"),      # Light red - Injured Reserve
        'PUP': QColor("#FFF3E0"),     # Light orange - PUP
        'SUS': QColor("#FFCDD2"),     # Dark red - Suspended
        'NFI': QColor("#FFF9C4"),     # Light yellow - Non-Football Injury
        'RES': QColor("#F5F5F5"),     # Light gray - Reserved
    }

    # Overall rating colors (text color)
    RATING_COLORS = {
        'elite': QColor("#1976D2"),      # Blue - 90+
        'starter': QColor("#388E3C"),    # Green - 80-89
        'backup': QColor("#FBC02D"),     # Yellow - 70-79
        'depth': QColor("#F57C00"),      # Orange - 60-69
        'practice': QColor("#D32F2F"),   # Red - <60
    }

    def __init__(self, parent=None):
        """Initialize roster table model."""
        super().__init__(parent)
        self._roster_data: List[Dict] = []
        self._checked_rows: set = set()  # Track which rows are checked
        self._headers = ["Sel", "#", "Name", "Pos", "Age", "OVR", "Contract", "Salary", "Stat"]

        # Load mock data
        self._load_mock_data()

    def _load_mock_data(self):
        """Load hardcoded sample player data."""
        self._roster_data = [
            # Quarterbacks
            {"number": 9, "name": "M. Stafford", "position": "QB", "age": 35, "overall": 87,
             "contract_years": 2, "contract_value": 45_000_000, "cap_hit": 22_500_000, "status": "ACT"},

            # Running Backs
            {"number": 22, "name": "D. Henry", "position": "RB", "age": 29, "overall": 88,
             "contract_years": 3, "contract_value": 36_000_000, "cap_hit": 12_000_000, "status": "ACT"},
            {"number": 28, "name": "J. Williams", "position": "RB", "age": 23, "overall": 75,
             "contract_years": 4, "contract_value": 3_400_000, "cap_hit": 850_000, "status": "ACT"},

            # Wide Receivers
            {"number": 10, "name": "T. Hill", "position": "WR", "age": 29, "overall": 95,
             "contract_years": 4, "contract_value": 120_000_000, "cap_hit": 30_000_000, "status": "ACT"},
            {"number": 18, "name": "A. St. Brown", "position": "WR", "age": 26, "overall": 85,
             "contract_years": 4, "contract_value": 120_000_000, "cap_hit": 30_000_000, "status": "IR"},
            {"number": 19, "name": "R. Moore", "position": "WR", "age": 22, "overall": 68,
             "contract_years": 4, "contract_value": 3_560_000, "cap_hit": 890_000, "status": "ACT"},

            # Tight Ends
            {"number": 87, "name": "T. Kelce", "position": "TE", "age": 34, "overall": 91,
             "contract_years": 2, "contract_value": 28_000_000, "cap_hit": 14_000_000, "status": "ACT"},
            {"number": 84, "name": "S. LaPorta", "position": "TE", "age": 23, "overall": 79,
             "contract_years": 4, "contract_value": 3_800_000, "cap_hit": 950_000, "status": "ACT"},

            # Offensive Line
            {"number": 70, "name": "P. Sewell", "position": "OT", "age": 23, "overall": 86,
             "contract_years": 2, "contract_value": 30_000_000, "cap_hit": 7_500_000, "status": "ACT"},
            {"number": 60, "name": "F. Ragnow", "position": "C", "age": 27, "overall": 90,
             "contract_years": 4, "contract_value": 70_000_000, "cap_hit": 17_500_000, "status": "ACT"},
            {"number": 66, "name": "J. Zeitler", "position": "OG", "age": 27, "overall": 72,
             "contract_years": 3, "contract_value": 18_000_000, "cap_hit": 6_000_000, "status": "PUP"},

            # Defensive Line
            {"number": 97, "name": "A. Hutchinson", "position": "DE", "age": 23, "overall": 89,
             "contract_years": 3, "contract_value": 38_000_000, "cap_hit": 9_500_000, "status": "ACT"},
            {"number": 91, "name": "C. Jones", "position": "DT", "age": 29, "overall": 94,
             "contract_years": 5, "contract_value": 158_000_000, "cap_hit": 31_600_000, "status": "ACT"},

            # Linebackers
            {"number": 54, "name": "R. Smith", "position": "LB", "age": 24, "overall": 83,
             "contract_years": 3, "contract_value": 12_800_000, "cap_hit": 3_200_000, "status": "ACT"},
            {"number": 55, "name": "D. Campbell", "position": "LB", "age": 25, "overall": 77,
             "contract_years": 2, "contract_value": 8_000_000, "cap_hit": 4_000_000, "status": "ACT"},

            # Defensive Backs
            {"number": 23, "name": "J. Ramsey", "position": "CB", "age": 29, "overall": 91,
             "contract_years": 3, "contract_value": 72_000_000, "cap_hit": 24_000_000, "status": "ACT"},
            {"number": 31, "name": "K. Byard", "position": "S", "age": 30, "overall": 84,
             "contract_years": 2, "contract_value": 18_000_000, "cap_hit": 9_000_000, "status": "ACT"},
            {"number": 21, "name": "T. Walker", "position": "CB", "age": 22, "overall": 58,
             "contract_years": 4, "contract_value": 3_180_000, "cap_hit": 795_000, "status": "ACT"},

            # Special Teams
            {"number": 3, "name": "J. Tucker", "position": "K", "age": 34, "overall": 96,
             "contract_years": 4, "contract_value": 24_000_000, "cap_hit": 6_000_000, "status": "ACT"},
            {"number": 6, "name": "B. Mann", "position": "P", "age": 26, "overall": 71,
             "contract_years": 2, "contract_value": 4_000_000, "cap_hit": 2_000_000, "status": "ACT"},
        ]

    def set_roster(self, roster: List[Dict]):
        """
        Set roster data for display.

        Args:
            roster: List of player dictionaries with keys:
                - number: Jersey number (int)
                - name: Player name (str)
                - position: Position abbreviation (str)
                - age: Player age (int)
                - overall: Overall rating 0-99 (int)
                - contract_years: Years remaining (int)
                - contract_value: Total contract value (float)
                - cap_hit: Current year cap hit (float)
                - status: Player status (str: ACT/IR/PUP/SUS/NFI/RES)
        """
        self.beginResetModel()
        self._roster_data = roster
        self._checked_rows.clear()
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows (players)."""
        if parent.isValid():
            return 0
        return len(self._roster_data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns."""
        if parent.isValid():
            return 0
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Return data for given index and role."""
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self._roster_data):
            return None

        player = self._roster_data[row]

        # Checkbox in first column
        if col == self.COL_SEL:
            if role == Qt.CheckStateRole:
                return Qt.Checked if row in self._checked_rows else Qt.Unchecked
            return None

        # Background color based on status (for all columns)
        if role == Qt.BackgroundRole:
            status = player.get('status', 'ACT')
            return self.STATUS_COLORS.get(status, None)

        # Text color for overall rating
        if role == Qt.ForegroundRole:
            if col == self.COL_OVERALL:
                overall = player.get('overall', 0)
                if overall >= 90:
                    return self.RATING_COLORS['elite']
                elif overall >= 80:
                    return self.RATING_COLORS['starter']
                elif overall >= 70:
                    return self.RATING_COLORS['backup']
                elif overall >= 60:
                    return self.RATING_COLORS['depth']
                else:
                    return self.RATING_COLORS['practice']
            return None

        # Text alignment
        if role == Qt.TextAlignmentRole:
            if col == self.COL_SEL:
                return Qt.AlignCenter
            elif col in (self.COL_NUMBER, self.COL_AGE, self.COL_OVERALL, self.COL_STATUS):
                return Qt.AlignCenter
            elif col in (self.COL_SALARY, self.COL_CONTRACT):
                return Qt.AlignRight | Qt.AlignVCenter
            else:
                return Qt.AlignLeft | Qt.AlignVCenter

        # Display data
        if role == Qt.DisplayRole:
            if col == self.COL_NUMBER:
                return str(player.get('number', ''))

            elif col == self.COL_NAME:
                return player.get('name', '')

            elif col == self.COL_POSITION:
                return player.get('position', '')

            elif col == self.COL_AGE:
                return str(player.get('age', ''))

            elif col == self.COL_OVERALL:
                return str(player.get('overall', ''))

            elif col == self.COL_CONTRACT:
                years = player.get('contract_years', 0)
                value = player.get('contract_value', 0)
                if years > 0 and value > 0:
                    value_m = value / 1_000_000
                    return f"{years}yr/${value_m:.1f}M"
                return "N/A"

            elif col == self.COL_SALARY:
                cap_hit = player.get('cap_hit', 0)
                if cap_hit > 0:
                    cap_hit_m = cap_hit / 1_000_000
                    return f"${cap_hit_m:.1f}M"
                return "$0.0M"

            elif col == self.COL_STATUS:
                return player.get('status', 'ACT')

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """Set data for given index and role."""
        if not index.isValid():
            return False

        row = index.row()
        col = index.column()

        # Handle checkbox toggling
        if col == self.COL_SEL and role == Qt.CheckStateRole:
            if row in self._checked_rows:
                self._checked_rows.remove(row)
            else:
                self._checked_rows.add(row)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True

        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Return item flags for given index."""
        if not index.isValid():
            return Qt.NoItemFlags

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable

        # Make checkbox column user-checkable
        if index.column() == self.COL_SEL:
            flags |= Qt.ItemIsUserCheckable

        return flags

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        """Return header data."""
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]

        elif orientation == Qt.Vertical:
            return str(section + 1)

        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder):
        """Sort roster by column."""
        self.beginResetModel()

        reverse = (order == Qt.DescendingOrder)

        if column == self.COL_SEL:
            # Sort by checked state - checked items first (or last if descending)
            # Use enumerate to get row indices during sort
            indexed_data = list(enumerate(self._roster_data))
            indexed_data.sort(key=lambda x: x[0] in self._checked_rows, reverse=reverse)
            self._roster_data = [p for _, p in indexed_data]

            # Rebuild checked_rows set with new indices
            old_checked_players = [self._roster_data[i] for i in self._checked_rows if i < len(self._roster_data)]
            self._checked_rows.clear()
            for i, player in enumerate(self._roster_data):
                if player in old_checked_players:
                    self._checked_rows.add(i)

        elif column == self.COL_NUMBER:
            self._roster_data.sort(key=lambda p: p.get('number', 0), reverse=reverse)

        elif column == self.COL_NAME:
            self._roster_data.sort(key=lambda p: p.get('name', ''), reverse=reverse)

        elif column == self.COL_POSITION:
            # Sort by position with logical ordering
            pos_order = {"QB": 1, "RB": 2, "WR": 3, "TE": 4, "OT": 5, "OG": 6, "C": 7,
                        "DE": 8, "DT": 9, "LB": 10, "CB": 11, "S": 12, "K": 13, "P": 14}
            self._roster_data.sort(key=lambda p: pos_order.get(p.get('position', ''), 99), reverse=reverse)

        elif column == self.COL_AGE:
            self._roster_data.sort(key=lambda p: p.get('age', 0), reverse=reverse)

        elif column == self.COL_OVERALL:
            self._roster_data.sort(key=lambda p: p.get('overall', 0), reverse=reverse)

        elif column == self.COL_CONTRACT:
            self._roster_data.sort(
                key=lambda p: p.get('contract_value', 0),
                reverse=reverse
            )

        elif column == self.COL_SALARY:
            self._roster_data.sort(key=lambda p: p.get('cap_hit', 0), reverse=reverse)

        elif column == self.COL_STATUS:
            # Sort by status priority: ACT, PUP, IR
            status_order = {"ACT": 1, "PUP": 2, "IR": 3, "SUS": 4, "NFI": 5, "RES": 6}
            self._roster_data.sort(key=lambda p: status_order.get(p.get('status', 'ACT'), 99), reverse=reverse)

        self.endResetModel()

    def get_player_at_row(self, row: int) -> Optional[Dict]:
        """
        Get player data at given row index.

        Args:
            row: Row index

        Returns:
            Player dictionary or None if invalid row
        """
        if 0 <= row < len(self._roster_data):
            return self._roster_data[row]
        return None

    def get_checked_players(self) -> List[Dict]:
        """
        Get list of all checked players.

        Returns:
            List of player dicts that are checked
        """
        return [self._roster_data[row] for row in self._checked_rows if row < len(self._roster_data)]

    def clear_selections(self):
        """Clear all checkbox selections."""
        self.beginResetModel()
        self._checked_rows.clear()
        self.endResetModel()

    def clear(self):
        """Clear all roster data."""
        self.beginResetModel()
        self._roster_data = []
        self._checked_rows.clear()
        self.endResetModel()
