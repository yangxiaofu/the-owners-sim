"""
Team List Model for The Owner's Sim UI

Qt table model for displaying NFL team data in table views.
"""

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from typing import List, Optional, Any
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from team_management.teams.team_loader import Team


class TeamListModel(QAbstractTableModel):
    """
    Qt table model for displaying NFL teams.

    Displays team information in a sortable table format.
    Supports displaying team metadata (always available) and optional
    win-loss records (if season data exists).
    """

    # Column indices
    COL_TEAM_NAME = 0
    COL_DIVISION = 1
    COL_CONFERENCE = 2
    COL_RECORD = 3

    def __init__(self, parent=None):
        """Initialize team list model."""
        super().__init__(parent)
        self._teams: List[Team] = []
        self._records: dict[int, dict[str, int]] = {}  # team_id -> {wins, losses, ties}
        self._has_records = False

        # Column headers
        self._headers = ["Team", "Division", "Conference", "Record"]

    def set_teams(self, teams: List[Team], records: Optional[dict[int, dict[str, int]]] = None):
        """
        Set teams data for display.

        Args:
            teams: List of Team objects
            records: Optional dict mapping team_id to {wins, losses, ties}
        """
        self.beginResetModel()
        self._teams = sorted(teams, key=lambda t: (t.conference, t.division, t.city))
        self._records = records or {}
        self._has_records = bool(records)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows (teams)."""
        if parent.isValid():
            return 0
        return len(self._teams)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns."""
        if parent.isValid():
            return 0
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Return data for given index and role."""
        if not index.isValid():
            return None

        if role not in (Qt.DisplayRole, Qt.TextAlignmentRole):
            return None

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self._teams):
            return None

        team = self._teams[row]

        if role == Qt.TextAlignmentRole:
            # Center-align all columns
            return Qt.AlignCenter

        # Display role
        if col == self.COL_TEAM_NAME:
            return team.full_name

        elif col == self.COL_DIVISION:
            return f"{team.conference} {team.division}"

        elif col == self.COL_CONFERENCE:
            return team.conference

        elif col == self.COL_RECORD:
            if self._has_records and team.team_id in self._records:
                record = self._records[team.team_id]
                wins = record.get('wins', 0)
                losses = record.get('losses', 0)
                ties = record.get('ties', 0)
                if ties > 0:
                    return f"{wins}-{losses}-{ties}"
                else:
                    return f"{wins}-{losses}"
            else:
                return "N/A"

        return None

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
        """Sort teams by column."""
        self.beginResetModel()

        reverse = (order == Qt.DescendingOrder)

        if column == self.COL_TEAM_NAME:
            self._teams.sort(key=lambda t: t.full_name, reverse=reverse)

        elif column == self.COL_DIVISION:
            self._teams.sort(key=lambda t: (t.conference, t.division), reverse=reverse)

        elif column == self.COL_CONFERENCE:
            self._teams.sort(key=lambda t: t.conference, reverse=reverse)

        elif column == self.COL_RECORD:
            if self._has_records:
                def get_win_pct(team: Team) -> float:
                    """Calculate win percentage for sorting."""
                    if team.team_id not in self._records:
                        return 0.0
                    record = self._records[team.team_id]
                    wins = record.get('wins', 0)
                    losses = record.get('losses', 0)
                    ties = record.get('ties', 0)
                    total = wins + losses + ties
                    if total == 0:
                        return 0.0
                    return (wins + 0.5 * ties) / total

                self._teams.sort(key=get_win_pct, reverse=reverse)
            else:
                # If no records, sort by team name
                self._teams.sort(key=lambda t: t.full_name, reverse=reverse)

        self.endResetModel()

    def get_team_at_row(self, row: int) -> Optional[Team]:
        """
        Get team at given row index.

        Args:
            row: Row index

        Returns:
            Team object or None if invalid row
        """
        if 0 <= row < len(self._teams):
            return self._teams[row]
        return None

    def clear(self):
        """Clear all data from model."""
        self.beginResetModel()
        self._teams = []
        self._records = {}
        self._has_records = False
        self.endResetModel()
