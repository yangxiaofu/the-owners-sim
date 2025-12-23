"""
HOF Ballot Widget - Displays Hall of Fame voting results.

Shows eligible candidates and voting outcomes for a given season:
- Inducted players (celebration section)
- Non-inducted (stayed on ballot)
- Removed from ballot (<5% or 20-year limit)
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QGroupBox, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from game_cycle_ui.theme import (
    ESPN_THEME, TABLE_HEADER_STYLE, Typography, Colors
)


# HOF Tier colors (matching tier classification)
TIER_COLORS = {
    "FIRST_BALLOT": "#FFD700",  # Gold
    "STRONG": "#4CAF50",        # Green
    "BORDERLINE": "#FFC107",    # Amber
    "LONG_SHOT": "#FF9800",     # Orange
    "NOT_HOF": "#9E9E9E",       # Gray
}

# Status colors
STATUS_COLORS = {
    "INDUCTED": "#2E7D32",      # Dark green
    "ON_BALLOT": "#1976D2",     # Blue
    "REMOVED": "#C62828",       # Red
}


class HOFBallotWidget(QWidget):
    """
    Displays HOF ballot and voting results for a season.

    Shows:
    - Inducted players (highlighted)
    - Non-inducted (stayed on ballot)
    - Removed from ballot

    Signals:
        player_clicked: Emitted when player row is clicked (player_id, player_name)
        celebration_requested: Emitted to show inductee celebration dialog
    """

    player_clicked = Signal(int, str)  # player_id, player_name
    celebration_requested = Signal(list)  # list of inducted player dicts

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._voting_results = []

        self._init_ui()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel(f"Hall of Fame Ballot - {self._season}")
        title_label.setFont(Typography.H4)
        title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Celebration button (shown after inductees are loaded)
        self._celebrate_btn = QPushButton("View Inductees")
        self._celebrate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ESPN_THEME['red']};
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #C41E3A;
            }}
            QPushButton:disabled {{
                background-color: #666666;
                color: #CCCCCC;
            }}
        """)
        self._celebrate_btn.clicked.connect(self._on_celebrate_clicked)
        self._celebrate_btn.setVisible(False)  # Hidden until inductees loaded
        header_layout.addWidget(self._celebrate_btn)

        layout.addLayout(header_layout)

        # Ballot table
        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "Player", "Pos", "Retired", "Score", "Tier", "Ballot Yrs", "Vote %", "Status"
        ])

        # Table appearance
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(False)
        self._table.verticalHeader().setVisible(False)
        self._table.setFont(Typography.TABLE)
        self._table.verticalHeader().setDefaultSectionSize(32)

        # Column sizing
        header = self._table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name stretches
        for col in range(1, 8):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        # Dark theme styling
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {ESPN_THEME['card_bg']};
                gridline-color: {ESPN_THEME['border']};
                color: white;
            }}
            QTableWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {ESPN_THEME['border']};
            }}
            QTableWidget::item:selected {{
                background-color: #2a4a6a;
            }}
        """)

        # Connect row click
        self._table.cellClicked.connect(self._on_row_clicked)

        layout.addWidget(self._table)

        # Summary label
        self._summary_label = QLabel("")
        self._summary_label.setFont(Typography.BODY_SMALL)
        self._summary_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 4px;")
        layout.addWidget(self._summary_label)

    def load_voting_results(self):
        """Load voting results from database and populate table."""
        from src.game_cycle.database.connection import GameCycleDatabase
        from src.game_cycle.database.hof_api import HOFAPI

        with GameCycleDatabase(self._db_path) as db:
            hof_api = HOFAPI(db.get_connection(), self._dynasty_id)
            self._voting_results = hof_api.get_voting_history_by_season(self._season)

        self._populate_table()
        self._update_summary()

    def _populate_table(self):
        """Populate table with voting results."""
        self._table.setRowCount(len(self._voting_results))

        inducted_count = 0

        for row, result in enumerate(self._voting_results):
            self._populate_row(row, result)
            if result.get('was_inducted'):
                inducted_count += 1

        # Show celebration button if there are inductees
        if inducted_count > 0:
            self._celebrate_btn.setVisible(True)
            self._celebrate_btn.setText(f"View {inducted_count} Inductee{'s' if inducted_count > 1 else ''}")

    def _populate_row(self, row: int, result: Dict):
        """Populate a single row with voting result data."""
        # Player name
        player_name = result.get('player_name', 'Unknown')
        player_item = QTableWidgetItem(player_name)
        player_item.setFont(Typography.BODY_SMALL_BOLD)

        # Determine status and color
        if result.get('was_inducted'):
            status = "INDUCTED"
            status_color = STATUS_COLORS["INDUCTED"]
            player_item.setForeground(QColor(STATUS_COLORS["INDUCTED"]))
        elif result.get('removed_from_ballot'):
            status = "REMOVED"
            status_color = STATUS_COLORS["REMOVED"]
            player_item.setForeground(QColor(STATUS_COLORS["REMOVED"]))
        else:
            status = "ON BALLOT"
            status_color = STATUS_COLORS["ON_BALLOT"]
            player_item.setForeground(QColor("white"))

        self._table.setItem(row, 0, player_item)

        # Position
        position = result.get('primary_position', 'N/A')
        self._set_centered_item(row, 1, position)

        # Retirement season
        retired = result.get('retirement_season', 'N/A')
        self._set_centered_item(row, 2, str(retired))

        # HOF Score
        score = result.get('hof_score', 0)
        score_item = QTableWidgetItem(str(score))
        score_item.setTextAlignment(Qt.AlignCenter)
        score_item.setFont(Typography.BODY_SMALL_BOLD)
        self._table.setItem(row, 3, score_item)

        # Tier (derive from score)
        tier = self._score_to_tier(score)
        tier_item = QTableWidgetItem(tier)
        tier_item.setTextAlignment(Qt.AlignCenter)
        tier_item.setBackground(QColor(TIER_COLORS.get(tier, "#666666")))
        tier_item.setForeground(QColor("#000000" if tier in ["FIRST_BALLOT", "BORDERLINE"] else "#FFFFFF"))
        tier_item.setFont(Typography.BODY_SMALL_BOLD)
        self._table.setItem(row, 4, tier_item)

        # Ballot years
        ballot_years = result.get('years_on_ballot', 0)
        self._set_centered_item(row, 5, str(ballot_years))

        # Vote percentage
        vote_pct = result.get('vote_percentage', 0.0)
        vote_text = f"{vote_pct:.1f}%" if vote_pct > 0 else "N/A"
        self._set_centered_item(row, 6, vote_text)

        # Status
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(QColor(status_color))
        status_item.setFont(Typography.BODY_SMALL_BOLD)
        self._table.setItem(row, 7, status_item)

    def _set_centered_item(self, row: int, col: int, text: str):
        """Helper to create centered table item."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, col, item)

    def _score_to_tier(self, score: int) -> str:
        """Convert HOF score to tier string."""
        if score >= 85:
            return "FIRST_BALLOT"
        elif score >= 70:
            return "STRONG"
        elif score >= 55:
            return "BORDERLINE"
        elif score >= 40:
            return "LONG_SHOT"
        else:
            return "NOT_HOF"

    def _update_summary(self):
        """Update summary label with voting statistics."""
        if not self._voting_results:
            self._summary_label.setText("No voting results for this season.")
            return

        inducted = sum(1 for r in self._voting_results if r.get('was_inducted'))
        on_ballot = sum(1 for r in self._voting_results if not r.get('was_inducted') and not r.get('removed_from_ballot'))
        removed = sum(1 for r in self._voting_results if r.get('removed_from_ballot'))

        summary = f"Inducted: {inducted} | Still on Ballot: {on_ballot} | Removed: {removed}"
        self._summary_label.setText(summary)

    def _on_row_clicked(self, row: int, col: int):
        """Handle row click - emit player_clicked signal."""
        if 0 <= row < len(self._voting_results):
            result = self._voting_results[row]
            player_id = result.get('player_id')
            player_name = result.get('player_name', 'Unknown')
            if player_id:
                self.player_clicked.emit(player_id, player_name)

    def _on_celebrate_clicked(self):
        """Handle celebration button click."""
        inductees = [r for r in self._voting_results if r.get('was_inducted')]
        if inductees:
            self.celebration_requested.emit(inductees)

    def get_inductees(self) -> List[Dict]:
        """Get list of inducted players from current results."""
        return [r for r in self._voting_results if r.get('was_inducted')]