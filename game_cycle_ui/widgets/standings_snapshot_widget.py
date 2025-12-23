"""
StandingsSnapshotWidget - Compact division standings viewer with dropdown.

Displays a single division's standings (4 teams) with a dropdown to select
any of the 8 NFL divisions. Compact layout suitable for dashboard sidebars.

Features:
- Division selector dropdown (AFC/NFC East/North/South/West)
- 4 team rows with W-L records
- Playoff position indicators (green/red)
- Clickable team rows for navigation
- Auto-defaults to user's team division
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QComboBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor

from game_cycle_ui.theme import (
    ESPN_THEME, ESPN_RED, ESPN_DARK_BG, ESPN_CARD_BG, ESPN_TEXT_PRIMARY,
    ESPN_TEXT_SECONDARY, ESPN_BORDER, Colors, FontSizes, Typography
)


# Division names for dropdown (8 NFL divisions)
DIVISION_OPTIONS = [
    "AFC East",
    "AFC North",
    "AFC South",
    "AFC West",
    "NFC East",
    "NFC North",
    "NFC South",
    "NFC West",
]


class TeamRowWidget(QWidget):
    """
    Single compact team row showing: [Indicator] Team W-L

    Layout: [🟢] Bills 8-2
    """

    clicked = Signal(int)  # team_id

    def __init__(self, team_data: Dict, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._team_data = team_data
        self._setup_ui()

    def _setup_ui(self):
        """Build the team row UI."""
        team_id = self._team_data.get("team_id", 0)
        team_abbrev = self._team_data.get("team_abbrev", "UNK")
        wins = self._team_data.get("wins", 0)
        losses = self._team_data.get("losses", 0)
        ties = self._team_data.get("ties", 0)
        in_playoff = self._team_data.get("in_playoff_position", False)
        div_rank = self._team_data.get("division_rank", 5)

        # Fixed height for compact display
        self.setFixedHeight(28)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Hover effect
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {ESPN_CARD_BG};
                border-bottom: 1px solid {ESPN_BORDER};
            }}
            QWidget:hover {{
                background-color: #252525;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Division rank number
        rank_label = QLabel(f"{div_rank}.")
        rank_label.setFixedWidth(20)
        rank_label.setStyleSheet(f"""
            color: {ESPN_TEXT_SECONDARY};
            font-size: {FontSizes.CAPTION};
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        layout.addWidget(rank_label)

        # Playoff indicator (green = in, red = out)
        indicator = "🟢" if in_playoff else "🔴"
        indicator_label = QLabel(indicator)
        indicator_label.setFixedWidth(20)
        indicator_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(indicator_label)

        # Team abbreviation
        team_label = QLabel(team_abbrev)
        team_label.setFont(Typography.BODY_SMALL_BOLD)  # 11px Arial Bold
        team_label.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            background: transparent;
            border: none;
        """)
        layout.addWidget(team_label, 1)  # Stretch

        # W-L record
        if ties > 0:
            record = f"{wins}-{losses}-{ties}"
        else:
            record = f"{wins}-{losses}"

        record_label = QLabel(record)
        record_label.setFont(Typography.CAPTION_BOLD)  # 11px Arial Bold
        record_label.setStyleSheet(f"""
            color: {ESPN_TEXT_SECONDARY};
            background: transparent;
            border: none;
        """)
        record_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(record_label)

    def mousePressEvent(self, event):
        """Handle click to emit team_clicked signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            team_id = self._team_data.get("team_id", 0)
            self.clicked.emit(team_id)
        super().mousePressEvent(event)


class StandingsSnapshotWidget(QWidget):
    """
    Compact division standings viewer with dropdown selector.

    Layout:
    ┌──────────────────────────────┐
    │ STANDINGS                    │
    │ [AFC East ▼]  ← Dropdown     │
    ├──────────────────────────────┤
    │ 1. 🟢 Bills      8-2         │
    │ 2. 🟢 Dolphins   7-3         │
    │ 3. 🔴 Jets       5-5         │
    │ 4. 🔴 Patriots   3-7         │
    └──────────────────────────────┘

    Features:
    - Dropdown with 8 NFL divisions
    - Defaults to user's team division
    - Shows 4 teams per division with W-L record
    - Playoff indicator: 🟢 (in position) or 🔴 (out)
    - Clickable teams for navigation
    - ~200px height

    Signals:
        team_clicked: Emitted when a team row is clicked (team_id)
        division_changed: Emitted when dropdown selection changes (division_name)
    """

    team_clicked = Signal(int)  # team_id
    division_changed = Signal(str)  # division_name (e.g., "AFC East")

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Internal state
        self._dynasty_id: Optional[str] = None
        self._db_path: Optional[str] = None
        self._user_team_id: Optional[int] = None
        self._standings_data: List[Dict] = []
        self._current_division: str = "AFC East"
        self._team_rows: List[TeamRowWidget] = []

        self._setup_ui()

    def _setup_ui(self):
        """Build the widget UI."""
        # Fixed height for sidebar placement
        self.setFixedHeight(200)
        self.setStyleSheet(f"background-color: {ESPN_DARK_BG};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with title and dropdown
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            background-color: {ESPN_CARD_BG};
            border-bottom: 3px solid {ESPN_RED};
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(6)

        # Title
        title = QLabel("STANDINGS")
        title.setFont(Typography.H6)  # 12px Arial Bold
        title.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-weight: bold;
            letter-spacing: 1px;
        """)
        header_layout.addWidget(title)

        # Division dropdown
        self._division_dropdown = QComboBox()
        self._division_dropdown.addItems(DIVISION_OPTIONS)
        self._division_dropdown.setCurrentText(self._current_division)
        self._division_dropdown.currentTextChanged.connect(self._on_division_changed)

        # Dropdown styling (ESPN dark theme)
        self._division_dropdown.setStyleSheet(f"""
            QComboBox {{
                background-color: #2a2a2a;
                color: {ESPN_TEXT_PRIMARY};
                border: 1px solid {ESPN_BORDER};
                border-radius: 3px;
                padding: 4px 8px;
                font-size: {FontSizes.CAPTION};
                min-width: 120px;
            }}
            QComboBox:hover {{
                background-color: #333333;
                border-color: {ESPN_RED};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {ESPN_TEXT_SECONDARY};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #2a2a2a;
                color: {ESPN_TEXT_PRIMARY};
                border: 1px solid {ESPN_BORDER};
                selection-background-color: {ESPN_RED};
                selection-color: white;
                outline: none;
            }}
        """)

        header_layout.addWidget(self._division_dropdown)
        layout.addWidget(header_frame)

        # Teams container (4 rows)
        self._teams_container = QWidget()
        self._teams_layout = QVBoxLayout(self._teams_container)
        self._teams_layout.setContentsMargins(0, 0, 0, 0)
        self._teams_layout.setSpacing(0)

        layout.addWidget(self._teams_container)
        layout.addStretch()  # Push content up

        # Load placeholder data on init
        self._load_placeholder_data()

    def set_context(
        self,
        dynasty_id: str,
        db_path: str,
        user_team_id: int
    ):
        """
        Set the widget context for data loading.

        Args:
            dynasty_id: Dynasty identifier
            db_path: Path to game_cycle database
            user_team_id: User's team ID (for default division)
        """
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._user_team_id = user_team_id

        # TODO: Load user's team division from database and set as default
        # For now, defaults to "AFC East"

    def set_division(self, division_name: str):
        """
        Change the selected division.

        Args:
            division_name: Division name (e.g., "AFC East", "NFC North")
        """
        if division_name in DIVISION_OPTIONS:
            self._current_division = division_name
            self._division_dropdown.setCurrentText(division_name)
            self._refresh_display()

    def set_standings(self, standings_data: List[Dict]):
        """
        Update the standings data and refresh display.

        Args:
            standings_data: List of team standings dicts with keys:
                - team_id: int
                - team_abbrev: str
                - division: str (e.g., "East", "North")
                - conference: str (e.g., "AFC", "NFC")
                - wins: int
                - losses: int
                - ties: int (optional)
                - playoff_seed: Optional[int] (1-7, if in playoffs)
                - division_rank: int (1-4)
        """
        self._standings_data = standings_data or []
        self._refresh_display()

    def _on_division_changed(self, division_name: str):
        """Handle division dropdown change."""
        self._current_division = division_name
        self._refresh_display()
        self.division_changed.emit(division_name)

    def _refresh_display(self):
        """Rebuild the team rows for the current division."""
        # Clear existing rows
        self._clear_team_rows()

        # Parse division name (e.g., "AFC East" -> conference="AFC", division="East")
        parts = self._current_division.split()
        if len(parts) != 2:
            return

        conference = parts[0]  # AFC or NFC
        division = parts[1]    # East, North, South, West

        # Filter standings to current division
        division_teams = [
            team for team in self._standings_data
            if team.get("conference") == conference and team.get("division") == division
        ]

        # Sort by division rank (or wins if rank not provided)
        division_teams.sort(key=lambda t: (
            t.get("division_rank", 99),
            -t.get("wins", 0)
        ))

        # Take top 4 teams (should always be 4 per division)
        division_teams = division_teams[:4]

        # Determine playoff positions (top 2 in division typically make playoffs)
        # This is simplified - actual playoff seeding is more complex
        for idx, team in enumerate(division_teams):
            # First team in division is always in playoff position
            # Second team is usually in (wildcard at minimum)
            # Rest depend on wildcard standings
            if "in_playoff_position" not in team:
                team["in_playoff_position"] = idx < 2 or team.get("playoff_seed") is not None

            if "division_rank" not in team:
                team["division_rank"] = idx + 1

        # Create team rows
        for team_data in division_teams:
            row = TeamRowWidget(team_data)
            row.clicked.connect(self._on_team_clicked)
            self._teams_layout.addWidget(row)
            self._team_rows.append(row)

    def _clear_team_rows(self):
        """Remove all team row widgets."""
        for row in self._team_rows:
            row.deleteLater()
        self._team_rows.clear()

        # Clear layout
        while self._teams_layout.count() > 0:
            item = self._teams_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_team_clicked(self, team_id: int):
        """Handle team row click."""
        self.team_clicked.emit(team_id)

    def _load_placeholder_data(self):
        """Load placeholder standings for initial display."""
        # Placeholder data for all 8 divisions
        placeholder_standings = [
            # AFC East
            {"team_id": 1, "team_abbrev": "BUF", "conference": "AFC", "division": "East", "wins": 8, "losses": 2, "ties": 0, "division_rank": 1, "playoff_seed": 2},
            {"team_id": 2, "team_abbrev": "MIA", "conference": "AFC", "division": "East", "wins": 7, "losses": 3, "ties": 0, "division_rank": 2, "playoff_seed": 5},
            {"team_id": 4, "team_abbrev": "NYJ", "conference": "AFC", "division": "East", "wins": 5, "losses": 5, "ties": 0, "division_rank": 3},
            {"team_id": 3, "team_abbrev": "NE", "conference": "AFC", "division": "East", "wins": 3, "losses": 7, "ties": 0, "division_rank": 4},

            # AFC North
            {"team_id": 5, "team_abbrev": "BAL", "conference": "AFC", "division": "North", "wins": 9, "losses": 1, "ties": 0, "division_rank": 1, "playoff_seed": 1},
            {"team_id": 8, "team_abbrev": "PIT", "conference": "AFC", "division": "North", "wins": 6, "losses": 4, "ties": 0, "division_rank": 2},
            {"team_id": 6, "team_abbrev": "CIN", "conference": "AFC", "division": "North", "wins": 4, "losses": 6, "ties": 0, "division_rank": 3},
            {"team_id": 7, "team_abbrev": "CLE", "conference": "AFC", "division": "North", "wins": 2, "losses": 8, "ties": 0, "division_rank": 4},

            # AFC South
            {"team_id": 9, "team_abbrev": "HOU", "conference": "AFC", "division": "South", "wins": 6, "losses": 4, "ties": 0, "division_rank": 1, "playoff_seed": 4},
            {"team_id": 10, "team_abbrev": "IND", "conference": "AFC", "division": "South", "wins": 5, "losses": 5, "ties": 0, "division_rank": 2},
            {"team_id": 11, "team_abbrev": "JAX", "conference": "AFC", "division": "South", "wins": 4, "losses": 6, "ties": 0, "division_rank": 3},
            {"team_id": 12, "team_abbrev": "TEN", "conference": "AFC", "division": "South", "wins": 3, "losses": 7, "ties": 0, "division_rank": 4},

            # AFC West
            {"team_id": 14, "team_abbrev": "KC", "conference": "AFC", "division": "West", "wins": 8, "losses": 2, "ties": 0, "division_rank": 1, "playoff_seed": 3},
            {"team_id": 16, "team_abbrev": "LAC", "conference": "AFC", "division": "West", "wins": 6, "losses": 4, "ties": 0, "division_rank": 2, "playoff_seed": 6},
            {"team_id": 13, "team_abbrev": "DEN", "conference": "AFC", "division": "West", "wins": 5, "losses": 5, "ties": 0, "division_rank": 3},
            {"team_id": 15, "team_abbrev": "LV", "conference": "AFC", "division": "West", "wins": 4, "losses": 6, "ties": 0, "division_rank": 4},

            # NFC East
            {"team_id": 19, "team_abbrev": "PHI", "conference": "NFC", "division": "East", "wins": 9, "losses": 1, "ties": 0, "division_rank": 1, "playoff_seed": 1},
            {"team_id": 17, "team_abbrev": "DAL", "conference": "NFC", "division": "East", "wins": 7, "losses": 3, "ties": 0, "division_rank": 2, "playoff_seed": 5},
            {"team_id": 20, "team_abbrev": "WAS", "conference": "NFC", "division": "East", "wins": 5, "losses": 5, "ties": 0, "division_rank": 3},
            {"team_id": 18, "team_abbrev": "NYG", "conference": "NFC", "division": "East", "wins": 2, "losses": 8, "ties": 0, "division_rank": 4},

            # NFC North
            {"team_id": 22, "team_abbrev": "DET", "conference": "NFC", "division": "North", "wins": 8, "losses": 2, "ties": 0, "division_rank": 1, "playoff_seed": 2},
            {"team_id": 24, "team_abbrev": "MIN", "conference": "NFC", "division": "North", "wins": 6, "losses": 4, "ties": 0, "division_rank": 2, "playoff_seed": 6},
            {"team_id": 23, "team_abbrev": "GB", "conference": "NFC", "division": "North", "wins": 5, "losses": 5, "ties": 0, "division_rank": 3},
            {"team_id": 21, "team_abbrev": "CHI", "conference": "NFC", "division": "North", "wins": 3, "losses": 7, "ties": 0, "division_rank": 4},

            # NFC South
            {"team_id": 28, "team_abbrev": "TB", "conference": "NFC", "division": "South", "wins": 6, "losses": 4, "ties": 0, "division_rank": 1, "playoff_seed": 4},
            {"team_id": 27, "team_abbrev": "NO", "conference": "NFC", "division": "South", "wins": 5, "losses": 5, "ties": 0, "division_rank": 2},
            {"team_id": 25, "team_abbrev": "ATL", "conference": "NFC", "division": "South", "wins": 4, "losses": 6, "ties": 0, "division_rank": 3},
            {"team_id": 26, "team_abbrev": "CAR", "conference": "NFC", "division": "South", "wins": 2, "losses": 8, "ties": 0, "division_rank": 4},

            # NFC West
            {"team_id": 31, "team_abbrev": "SF", "conference": "NFC", "division": "West", "wins": 8, "losses": 2, "ties": 0, "division_rank": 1, "playoff_seed": 3},
            {"team_id": 32, "team_abbrev": "SEA", "conference": "NFC", "division": "West", "wins": 6, "losses": 4, "ties": 0, "division_rank": 2, "playoff_seed": 7},
            {"team_id": 30, "team_abbrev": "LAR", "conference": "NFC", "division": "West", "wins": 5, "losses": 5, "ties": 0, "division_rank": 3},
            {"team_id": 29, "team_abbrev": "ARI", "conference": "NFC", "division": "West", "wins": 3, "losses": 7, "ties": 0, "division_rank": 4},
        ]

        self.set_standings(placeholder_standings)

    def clear(self):
        """Clear all standings data."""
        self._standings_data = []
        self._clear_team_rows()
