"""
PowerRankingsWidget - Two-column split view for weekly power rankings.

Part of Milestone 12: Media Coverage, Tollgate 7.

Displays all 32 teams at once in a two-column layout:
- Left column: Ranks 1-16
- Right column: Ranks 17-32
- Compact rows with tier-colored backgrounds
- Movement indicators (▲▼—)
- Hover/click for full blurb
"""

from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QGridLayout,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor

from game_cycle_ui.theme import (
    TABLE_HEADER_STYLE,
    TIER_COLORS,
    TIER_TEXT_COLORS,
    MOVEMENT_COLORS,
    ESPN_RED,
    ESPN_DARK_BG,
    ESPN_CARD_BG,
    ESPN_TEXT_PRIMARY,
    ESPN_TEXT_SECONDARY,
    ESPN_TEXT_MUTED,
    ESPN_BORDER,
)


# Tier background colors (subtle, for row backgrounds)
TIER_ROW_COLORS = {
    "ELITE": "#2d1a1a",        # Dark red tint
    "CONTENDER": "#1a2233",    # Dark blue tint
    "PLAYOFF": "#1a2d1a",      # Dark green tint
    "BUBBLE": "#2d2a1a",       # Dark orange tint
    "REBUILDING": "#1a1a1a",   # Dark gray
}

# Tier accent colors (for left border)
TIER_ACCENT_COLORS = {
    "ELITE": ESPN_RED,
    "CONTENDER": "#1976D2",
    "PLAYOFF": "#2E7D32",
    "BUBBLE": "#F57C00",
    "REBUILDING": "#444444",
}


class RankingRowWidget(QWidget):
    """
    Single compact row for one team's ranking.

    Layout: [Rank] [Team Name] [Movement]
    With tier-colored background and hover effect.
    """

    clicked = Signal(int)  # team_id

    def __init__(
        self,
        ranking_data: Dict[str, Any],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._data = ranking_data
        self._setup_ui()

    def _setup_ui(self):
        """Build the compact row UI."""
        team_id = self._data.get("team_id", 0)
        team_name = self._data.get("team_name", f"Team {team_id}")
        rank = self._data.get("rank", 0)
        tier = self._data.get("tier", "REBUILDING")
        blurb = self._data.get("blurb", "")

        # Calculate movement
        movement = self._data.get("movement")
        if movement is None:
            previous = self._data.get("previous_rank")
            if previous is None:
                movement = "NEW"
            elif previous == rank:
                movement = "—"
            elif previous > rank:
                movement = f"▲{previous - rank}"
            else:
                movement = f"▼{rank - previous}"

        # Set fixed height for compact display
        self.setFixedHeight(28)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Tooltip shows full blurb
        if blurb:
            self.setToolTip(f"{team_name}\n\n{blurb}")
        else:
            self.setToolTip(team_name)

        # Get tier colors
        bg_color = TIER_ROW_COLORS.get(tier, TIER_ROW_COLORS["REBUILDING"])
        accent_color = TIER_ACCENT_COLORS.get(tier, TIER_ACCENT_COLORS["REBUILDING"])

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-left: 3px solid {accent_color};
                border-bottom: 1px solid {ESPN_BORDER};
            }}
            QWidget:hover {{
                background-color: #2a2a2a;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)

        # Rank number
        rank_label = QLabel(str(rank))
        rank_label.setFixedWidth(24)
        rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank_label.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-weight: bold;
            font-size: 12px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(rank_label)

        # Team name (truncated if needed)
        display_name = team_name
        if len(display_name) > 20:
            display_name = display_name[:18] + "..."

        name_label = QLabel(display_name)
        name_label.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-size: 11px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(name_label, 1)  # Stretch

        # Movement indicator
        move_label = QLabel(movement)
        move_label.setFixedWidth(32)
        move_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        if movement.startswith("▲"):
            move_color = "#2E7D32"  # Green
        elif movement.startswith("▼"):
            move_color = ESPN_RED
        elif movement == "NEW":
            move_color = "#1976D2"  # Blue
        else:
            move_color = ESPN_TEXT_MUTED

        move_label.setStyleSheet(f"""
            color: {move_color};
            font-weight: bold;
            font-size: 10px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(move_label)

    def mousePressEvent(self, event):
        """Handle click to emit signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            team_id = self._data.get("team_id", 0)
            self.clicked.emit(team_id)
        super().mousePressEvent(event)


class PowerRankingsWidget(QWidget):
    """
    Two-column split view for displaying all 32 power rankings at once.

    Layout:
    ┌─────────────────────────────────────────────────┐
    │              POWER RANKINGS                      │
    ├────────────────────┬────────────────────────────┤
    │      1-16          │         17-32              │
    ├────────────────────┼────────────────────────────┤
    │ 1  Chiefs       ▲2 │ 17 Broncos            ▼1  │
    │ 2  Eagles       —  │ 18 Raiders            ▲3  │
    │ 3  49ers        ▼1 │ 19 Panthers           —   │
    │ ...                │ ...                        │
    │ 16 Titans       ▲1 │ 32 Bears              ▼2  │
    └────────────────────┴────────────────────────────┘

    Features:
    - All 32 teams visible without scrolling
    - Tier-colored row backgrounds
    - Movement arrows
    - Hover tooltips with full blurb
    - Click to select team

    Signals:
        team_selected: Emitted when a team row is clicked, passes team_id
    """

    team_selected = Signal(int)  # team_id

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the power rankings widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._rankings: List[Dict[str, Any]] = []
        self._row_widgets: List[RankingRowWidget] = []
        self._setup_ui()

    def _setup_ui(self):
        """Build the two-column split view UI."""
        self.setStyleSheet(f"background-color: {ESPN_DARK_BG};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            background-color: {ESPN_CARD_BG};
            border-bottom: 3px solid {ESPN_RED};
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 10, 16, 10)

        title = QLabel("POWER RANKINGS")
        title.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        layout.addWidget(header_frame)

        # Two-column container
        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(1)  # Thin divider between columns

        # Left column (1-16)
        self._left_column = QWidget()
        self._left_layout = QVBoxLayout(self._left_column)
        self._left_layout.setContentsMargins(0, 0, 0, 0)
        self._left_layout.setSpacing(0)

        # Left column header
        left_header = QLabel("1 - 16")
        left_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_header.setStyleSheet(f"""
            background-color: {ESPN_CARD_BG};
            color: {ESPN_TEXT_SECONDARY};
            font-size: 10px;
            font-weight: bold;
            padding: 4px;
            border-bottom: 1px solid {ESPN_RED};
        """)
        self._left_layout.addWidget(left_header)

        # Left column content area
        self._left_content = QWidget()
        self._left_content_layout = QVBoxLayout(self._left_content)
        self._left_content_layout.setContentsMargins(0, 0, 0, 0)
        self._left_content_layout.setSpacing(0)
        self._left_layout.addWidget(self._left_content)
        self._left_layout.addStretch()

        columns_layout.addWidget(self._left_column)

        # Divider
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet(f"background-color: {ESPN_BORDER};")
        columns_layout.addWidget(divider)

        # Right column (17-32)
        self._right_column = QWidget()
        self._right_layout = QVBoxLayout(self._right_column)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.setSpacing(0)

        # Right column header
        right_header = QLabel("17 - 32")
        right_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_header.setStyleSheet(f"""
            background-color: {ESPN_CARD_BG};
            color: {ESPN_TEXT_SECONDARY};
            font-size: 10px;
            font-weight: bold;
            padding: 4px;
            border-bottom: 1px solid {ESPN_RED};
        """)
        self._right_layout.addWidget(right_header)

        # Right column content area
        self._right_content = QWidget()
        self._right_content_layout = QVBoxLayout(self._right_content)
        self._right_content_layout.setContentsMargins(0, 0, 0, 0)
        self._right_content_layout.setSpacing(0)
        self._right_layout.addWidget(self._right_content)
        self._right_layout.addStretch()

        columns_layout.addWidget(self._right_column)

        layout.addWidget(columns_container)

    def set_rankings(self, rankings: List[Dict[str, Any]]):
        """
        Populate the two columns with rankings data.

        Args:
            rankings: List of ranking dictionaries sorted by rank, each containing:
                - team_id: int
                - team_name: str (optional, fallback to team_id)
                - rank: int
                - previous_rank: Optional[int]
                - tier: str (ELITE, CONTENDER, PLAYOFF, BUBBLE, REBUILDING)
                - blurb: Optional[str]
                - movement: Optional[str] (▲3, ▼2, —, NEW)
        """
        self._rankings = rankings
        self._clear_columns()

        # Sort by rank just in case
        sorted_rankings = sorted(rankings, key=lambda r: r.get("rank", 999))

        # Split into two columns
        left_rankings = [r for r in sorted_rankings if r.get("rank", 0) <= 16]
        right_rankings = [r for r in sorted_rankings if r.get("rank", 0) > 16]

        # Populate left column (1-16)
        for ranking_data in left_rankings:
            row = RankingRowWidget(ranking_data)
            row.clicked.connect(self._on_team_clicked)
            self._left_content_layout.addWidget(row)
            self._row_widgets.append(row)

        # Populate right column (17-32)
        for ranking_data in right_rankings:
            row = RankingRowWidget(ranking_data)
            row.clicked.connect(self._on_team_clicked)
            self._right_content_layout.addWidget(row)
            self._row_widgets.append(row)

    def _clear_columns(self):
        """Clear all row widgets from both columns."""
        # Clear left column
        while self._left_content_layout.count() > 0:
            item = self._left_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear right column
        while self._right_content_layout.count() > 0:
            item = self._right_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._row_widgets = []

    def _on_team_clicked(self, team_id: int):
        """Handle team row click."""
        self.team_selected.emit(team_id)

    def get_selected_team_id(self) -> Optional[int]:
        """Get the currently selected team ID (not applicable in this view)."""
        return None

    def clear(self):
        """Clear the rankings display."""
        self._clear_columns()
        self._rankings = []

    def set_team_names(self, team_names: Dict[int, str]):
        """
        Set team name lookup for display.

        Note: This method is kept for API compatibility but the new
        implementation expects team_name in the ranking data directly.

        Args:
            team_names: Dictionary mapping team_id to team_name
        """
        # For API compatibility - refresh with updated names
        if self._rankings:
            for ranking in self._rankings:
                team_id = ranking.get("team_id")
                if team_id in team_names:
                    ranking["team_name"] = team_names[team_id]
            self.set_rankings(self._rankings)
