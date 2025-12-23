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
from PySide6.QtGui import QCursor, QPixmap

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
    Colors,
    FontSizes,
    TextColors,
)
from game_cycle_ui.widgets.empty_state_widget import EmptyStateWidget


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
    "CONTENDER": Colors.INFO,
    "PLAYOFF": Colors.SUCCESS,
    "BUBBLE": Colors.WARNING,
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

        # Set fixed height for expanded display (was 28px, now 70px)
        self.setFixedHeight(70)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

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

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(12)

        # Rank number
        rank_label = QLabel(str(rank))
        rank_label.setFixedWidth(30)
        rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank_label.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-weight: bold;
            font-size: {FontSizes.H5};
            background: transparent;
            border: none;
        """)
        main_layout.addWidget(rank_label)

        # Team logo placeholder (30x30)
        # TODO: Load actual team logo from resources
        logo_label = QLabel("🏈")  # Placeholder emoji
        logo_label.setFixedSize(30, 30)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet(f"""
            font-size: {FontSizes.H5};
            background: transparent;
            border: none;
        """)
        main_layout.addWidget(logo_label)

        # Team info column (name + blurb)
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        # Team name row with movement indicator
        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        name_label = QLabel(team_name)
        name_label.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-size: {FontSizes.BODY};
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        name_row.addWidget(name_label)

        # Movement indicator
        move_label = QLabel(movement)
        move_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        if movement.startswith("▲"):
            move_color = Colors.SUCCESS
        elif movement.startswith("▼"):
            move_color = ESPN_RED
        elif movement == "NEW":
            move_color = Colors.INFO
        else:
            move_color = ESPN_TEXT_MUTED

        move_label.setStyleSheet(f"""
            color: {move_color};
            font-weight: bold;
            font-size: {FontSizes.SMALL};
            background: transparent;
            border: none;
        """)
        name_row.addWidget(move_label)
        name_row.addStretch()

        info_layout.addLayout(name_row)

        # Blurb text (truncate if too long)
        if blurb:
            display_blurb = blurb
            if len(display_blurb) > 80:
                display_blurb = display_blurb[:77] + "..."

            blurb_label = QLabel(display_blurb)
            blurb_label.setWordWrap(True)
            blurb_label.setStyleSheet(f"""
                color: {ESPN_TEXT_SECONDARY};
                font-size: {FontSizes.SMALL};
                background: transparent;
                border: none;
            """)
            info_layout.addWidget(blurb_label)

        main_layout.addWidget(info_widget, 1)  # Stretch

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

        # Header bar with week selector and history button
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            background-color: {ESPN_CARD_BG};
            border-bottom: 3px solid {ESPN_RED};
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(12)

        title = QLabel("POWER RANKINGS")
        title.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-size: {FontSizes.H5};
            font-weight: bold;
            letter-spacing: 2px;
        """)
        header_layout.addWidget(title)

        header_layout.addStretch()

        layout.addWidget(header_frame)

        # Empty state widget (shown when no rankings available)
        self._empty_state = EmptyStateWidget(
            "Power rankings will be available after Week 1 is simulated",
            icon="📊"
        )
        self._empty_state.setVisible(True)  # Show by default until rankings are loaded
        layout.addWidget(self._empty_state)

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
            font-size: {FontSizes.SMALL};
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
            font-size: {FontSizes.SMALL};
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

        self._columns_container = columns_container
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

        if not rankings:
            # Show empty state, hide columns
            self._empty_state.setVisible(True)
            self._columns_container.setVisible(False)
            return

        # Hide empty state, show columns when displaying rankings
        self._empty_state.setVisible(False)
        self._columns_container.setVisible(True)

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

    def clear(self, message: Optional[str] = None):
        """
        Clear the rankings display and show empty state message.

        Args:
            message: Optional custom message to display when empty.
                     If None, shows default message.
        """
        self._clear_columns()
        self._rankings = []

        # Show empty state with custom or default message
        if message:
            self._empty_state.set_message(message)
        else:
            self._empty_state.set_message("Power rankings will be available after Week 1 is simulated")

        self._empty_state.setVisible(True)
        self._columns_container.setVisible(False)

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
