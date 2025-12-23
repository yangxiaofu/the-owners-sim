"""
Awards Grid Widget - Compact 2x3 grid display for major awards.

Designed to show all 6 major awards on one screen without scrolling:
- MVP, OPOY, DPOY (row 1)
- OROY, DROY, CPOY (row 2)

Each tile shows winner name, position/team, and vote percentage bar.
Click tile for finalists popup.
"""

from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QProgressBar, QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QCursor

from game_cycle_ui.theme import (
    Typography, FontSizes, Colors, TextColors, apply_table_style
)


# Award metadata
AWARD_ORDER = ['mvp', 'opoy', 'dpoy', 'oroy', 'droy', 'cpoy']

AWARD_NAMES = {
    'mvp': 'MVP',
    'opoy': 'OPOY',
    'dpoy': 'DPOY',
    'oroy': 'OROY',
    'droy': 'DROY',
    'cpoy': 'CPOY',
}

AWARD_FULL_NAMES = {
    'mvp': 'Most Valuable Player',
    'opoy': 'Offensive Player of the Year',
    'dpoy': 'Defensive Player of the Year',
    'oroy': 'Offensive Rookie of the Year',
    'droy': 'Defensive Rookie of the Year',
    'cpoy': 'Comeback Player of the Year',
}

AWARD_ICONS = {
    'mvp': '\U0001F3C6',  # Trophy
    'opoy': '\U0001F3C8',  # Football
    'dpoy': '\U0001F6E1',  # Shield
    'oroy': '\U0001F31F',  # Star
    'droy': '\U0001F31F',  # Star
    'cpoy': '\U0001F4AA',  # Flexed bicep
}


class AwardTileWidget(QFrame):
    """
    Compact award tile showing winner and vote bar.

    Visual design:
    ┌────────────────────┐
    │ 🏆 MVP             │  <- Award title (gold)
    │ Josh Allen         │  <- Winner name (white, bold)
    │ QB - BUF           │  <- Position - Team (gray)
    │ ████████░░ 95.0%   │  <- Vote bar + percentage
    └────────────────────┘

    Signals:
        clicked: Emitted when tile is clicked (award_id)
        player_clicked: Emitted when winner name is clicked (player_id)
    """

    clicked = Signal(str)  # award_id
    player_clicked = Signal(int)  # player_id

    def __init__(self, award_id: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._award_id = award_id
        self._player_id: Optional[int] = None
        self._finalists: List[Dict] = []

        self._setup_ui()

    def _setup_ui(self):
        """Build the tile layout."""
        self.setStyleSheet(f"""
            AwardTileWidget {{
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 8px;
            }}
            AwardTileWidget:hover {{
                background-color: #252525;
                border-color: #444444;
            }}
        """)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(120)
        self.setMaximumHeight(140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # Award title row (icon + short name)
        title_layout = QHBoxLayout()
        title_layout.setSpacing(6)

        icon = AWARD_ICONS.get(self._award_id, '')
        name = AWARD_NAMES.get(self._award_id, self._award_id.upper())

        self._title_label = QLabel(f"{icon} {name}")
        self._title_label.setFont(Typography.H6)
        self._title_label.setStyleSheet("color: #FFD700; letter-spacing: 1px;")
        title_layout.addWidget(self._title_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # Winner name
        self._winner_label = QLabel("No winner")
        self._winner_label.setFont(Typography.H5)
        self._winner_label.setStyleSheet(f"color: {TextColors.ON_DARK}; font-weight: bold;")
        layout.addWidget(self._winner_label)

        # Position - Team
        self._details_label = QLabel("")
        self._details_label.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")
        layout.addWidget(self._details_label)

        layout.addSpacing(4)

        # Vote bar row
        vote_layout = QHBoxLayout()
        vote_layout.setSpacing(8)

        self._vote_bar = QProgressBar()
        self._vote_bar.setRange(0, 100)
        self._vote_bar.setValue(0)
        self._vote_bar.setTextVisible(False)
        self._vote_bar.setFixedHeight(12)
        self._vote_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333333;
                border-radius: 4px;
                background: #0d0d0d;
            }
            QProgressBar::chunk {
                background: #cc0000;
                border-radius: 3px;
            }
        """)
        vote_layout.addWidget(self._vote_bar, stretch=1)

        self._vote_pct_label = QLabel("0%")
        self._vote_pct_label.setStyleSheet(f"color: {TextColors.ON_DARK}; font-weight: bold; font-size: {FontSizes.CAPTION};")
        self._vote_pct_label.setMinimumWidth(50)
        self._vote_pct_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vote_layout.addWidget(self._vote_pct_label)

        layout.addLayout(vote_layout)

        layout.addStretch()

    def set_data(
        self,
        winner_name: str,
        position: str,
        team_abbr: str,
        vote_pct: float,
        player_id: Optional[int] = None,
        finalists: Optional[List[Dict]] = None
    ):
        """
        Set the award winner data.

        Args:
            winner_name: Winner's name
            position: Position abbreviation (QB, RB, etc.)
            team_abbr: Team abbreviation (BUF, KC, etc.)
            vote_pct: Vote percentage (0-100)
            player_id: Player ID for click handling
            finalists: List of finalist dicts for popup
        """
        self._player_id = player_id
        self._finalists = finalists or []

        self._winner_label.setText(winner_name)
        self._details_label.setText(f"{position} - {team_abbr}")
        self._vote_bar.setValue(int(vote_pct))
        self._vote_pct_label.setText(f"{vote_pct:.1f}%")

    def set_empty(self):
        """Set empty state when no winner."""
        self._player_id = None
        self._finalists = []
        self._winner_label.setText("No winner")
        self._details_label.setText("")
        self._vote_bar.setValue(0)
        self._vote_pct_label.setText("")

    def mousePressEvent(self, event):
        """Handle click - show finalists popup."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._award_id)
            if self._finalists:
                self._show_finalists_popup()
        super().mousePressEvent(event)

    def _show_finalists_popup(self):
        """Show popup dialog with finalists."""
        dialog = FinalistsDialog(
            self._award_id,
            self._finalists,
            parent=self.window()
        )
        dialog.player_clicked.connect(self.player_clicked.emit)
        dialog.exec()


class FinalistsDialog(QDialog):
    """
    Popup dialog showing award finalists.

    Shows top 5 candidates with vote percentages.
    """

    player_clicked = Signal(int)  # player_id

    def __init__(
        self,
        award_id: str,
        finalists: List[Dict],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._award_id = award_id
        self._finalists = finalists

        self._setup_ui()

    def _setup_ui(self):
        """Build dialog layout."""
        full_name = AWARD_FULL_NAMES.get(self._award_id, self._award_id.upper())
        icon = AWARD_ICONS.get(self._award_id, '')

        self.setWindowTitle(f"{icon} {full_name} - Finalists")
        self.setMinimumWidth(450)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #1a1a1a;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header
        header = QLabel(f"{icon} {full_name}")
        header.setFont(Typography.H4)
        header.setStyleSheet(f"color: #FFD700;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Finalists table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Rank", "Player", "Team", "Vote %"])
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setFont(Typography.TABLE)

        apply_table_style(self._table)

        header_obj = self._table.horizontalHeader()
        header_obj.setSectionResizeMode(1, QHeaderView.Stretch)

        self._populate_table()

        self._table.cellClicked.connect(self._on_row_clicked)
        layout.addWidget(self._table)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #333333;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #444444;
            }}
        """)
        close_btn.clicked.connect(self.accept)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _populate_table(self):
        """Populate finalists table."""
        self._table.setRowCount(len(self._finalists))

        for row, finalist in enumerate(self._finalists):
            # Rank
            rank = row + 1
            rank_item = QTableWidgetItem(str(rank))
            rank_item.setTextAlignment(Qt.AlignCenter)
            if rank == 1:
                rank_item.setFont(Typography.SMALL_BOLD)
                rank_item.setForeground(QColor("#FFD700"))  # Gold for winner
            self._table.setItem(row, 0, rank_item)

            # Player name
            name = finalist.get('player_name', 'Unknown')
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, finalist.get('player_id'))
            if rank == 1:
                name_item.setFont(Typography.SMALL_BOLD)
            self._table.setItem(row, 1, name_item)

            # Team
            team = finalist.get('team_abbr', '???')
            pos = finalist.get('position', '')
            team_item = QTableWidgetItem(f"{pos} - {team}")
            team_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 2, team_item)

            # Vote percentage
            vote_pct = finalist.get('vote_share', 0) * 100
            vote_item = QTableWidgetItem(f"{vote_pct:.1f}%")
            vote_item.setTextAlignment(Qt.AlignCenter)
            if rank == 1:
                vote_item.setFont(Typography.SMALL_BOLD)
                vote_item.setForeground(QColor("#4CAF50"))  # Green for winner
            self._table.setItem(row, 3, vote_item)

    def _on_row_clicked(self, row: int, col: int):
        """Handle click on finalist row."""
        item = self._table.item(row, 1)  # Player name column
        if item:
            player_id = item.data(Qt.UserRole)
            if player_id:
                self.player_clicked.emit(player_id)


class AwardsGridWidget(QWidget):
    """
    2x3 grid of award tiles showing all 6 major awards.

    Layout:
    ┌─────────┬─────────┬─────────┐
    │   MVP   │  OPOY   │  DPOY   │
    ├─────────┼─────────┼─────────┤
    │  OROY   │  DROY   │  CPOY   │
    └─────────┴─────────┴─────────┘

    Signals:
        player_selected: Emitted when player name is clicked (player_id)
        award_clicked: Emitted when award tile is clicked (award_id)
    """

    player_selected = Signal(int)  # player_id
    award_clicked = Signal(str)    # award_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._tiles: Dict[str, AwardTileWidget] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Build the grid layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("MAJOR AWARDS")
        header.setFont(Typography.H5)
        header.setStyleSheet(f"color: #FFD700; letter-spacing: 2px;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        layout.addSpacing(12)

        # Grid container
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 0, 0)

        # Create tiles in 2x3 grid
        for idx, award_id in enumerate(AWARD_ORDER):
            row = idx // 3
            col = idx % 3

            tile = AwardTileWidget(award_id)
            tile.clicked.connect(lambda aid=award_id: self.award_clicked.emit(aid))
            tile.player_clicked.connect(self.player_selected.emit)

            self._tiles[award_id] = tile
            grid.addWidget(tile, row, col)

        layout.addLayout(grid)
        layout.addStretch()

    def set_awards_data(self, awards_data: Dict[str, Any], get_team_abbrev_func):
        """
        Populate all award tiles with data.

        Args:
            awards_data: Dict mapping award_id to AwardResult objects
            get_team_abbrev_func: Function to get team abbreviation from team_id
        """
        for award_id, tile in self._tiles.items():
            result = awards_data.get(award_id)

            if not result or not result.has_winner:
                tile.set_empty()
                continue

            winner = result.winner
            team_abbr = get_team_abbrev_func(winner.team_id)
            vote_pct = winner.vote_share * 100

            # Build finalists list for popup (top_5 already includes winner)
            finalists = []
            for f in result.top_5:
                finalists.append({
                    'player_id': f.player_id,
                    'player_name': f.player_name,
                    'position': f.position,
                    'team_abbr': get_team_abbrev_func(f.team_id),
                    'vote_share': f.vote_share,
                })

            tile.set_data(
                winner_name=winner.player_name,
                position=winner.position,
                team_abbr=team_abbr,
                vote_pct=vote_pct,
                player_id=winner.player_id,
                finalists=finalists
            )

    def clear(self):
        """Clear all tiles to empty state."""
        for tile in self._tiles.values():
            tile.set_empty()
