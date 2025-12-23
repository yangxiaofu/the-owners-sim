"""
Top Performers Widget - Shows top 5 players with weekly/season toggle.

Displays the top 5 statistical leaders with a toggle to switch between
weekly leaders and season-long leaders. Designed for the League View sidebar.

Layout:
    ┌────────────────────────────────┐
    │ [Week 3] [Season] ← Toggle     │
    ├────────────────────────────────┤
    │ QB: Patrick Mahomes (KC)       │
    │ - 350 YDS, 4 TD, 0 INT         │
    │ - Rating: 135.2                │
    ├────────────────────────────────┤
    │ (4 more players...)            │
    └────────────────────────────────┘

Usage:
    widget = TopPerformersWidget()
    widget.set_context(dynasty_id=1, db_path="...", season=2024, week=3)
    widget.set_weekly_leaders([...])
    widget.set_season_leaders([...])
"""

from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from constants.position_abbreviations import get_position_abbreviation
from game_cycle_ui.theme import (
    ESPN_THEME, Colors, Typography, FontSizes, TextColors,
    ESPN_RED, ESPN_DARK_BG, ESPN_CARD_BG, ESPN_TEXT_PRIMARY,
    ESPN_TEXT_SECONDARY, ESPN_TEXT_MUTED, ESPN_BORDER,
    SECONDARY_BUTTON_STYLE
)


class PlayerPerformanceCard(QFrame):
    """
    Single player performance card displaying:
    - Position and player name
    - Team abbreviation
    - Key statistics
    - Performance rating/score
    """

    def __init__(self, player_data: Dict, parent: Optional[QWidget] = None):
        """
        Initialize player performance card.

        Args:
            player_data: Dictionary with keys:
                - position: str (e.g., "QB")
                - name: str (player name)
                - team: str (team abbreviation)
                - stats: str (formatted stat line)
                - rating: str (formatted rating/score)
                - team_color: Optional[str] (hex color for accent)
            parent: Parent widget
        """
        super().__init__(parent)
        self._player_data = player_data
        self._setup_ui()

    def _setup_ui(self):
        """Build the player card UI."""
        # Card styling
        team_color = self._player_data.get('team_color', ESPN_RED)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_CARD_BG};
                border-radius: 6px;
                border-left: 3px solid {team_color};
                border-bottom: 1px solid {ESPN_BORDER};
            }}
        """)
        self.setFixedHeight(80)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Header row: Position, Name, Team
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        # Position badge
        position = self._player_data.get('position', 'N/A')
        position_abbr = get_position_abbreviation(position) if position != 'N/A' else 'N/A'
        pos_label = QLabel(position_abbr)
        pos_label.setFont(Typography.CAPTION_BOLD)
        pos_label.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            background-color: {team_color};
            padding: 2px 6px;
            border-radius: 3px;
        """)
        pos_label.setFixedWidth(36)
        pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(pos_label)

        # Player name
        name = self._player_data.get('name', 'Unknown')
        name_label = QLabel(name)
        name_label.setFont(Typography.BODY_BOLD)
        name_label.setStyleSheet(f"color: {ESPN_TEXT_PRIMARY};")
        header_row.addWidget(name_label, 1)  # Stretch

        # Team abbreviation
        team = self._player_data.get('team', '')
        team_label = QLabel(team)
        team_label.setFont(Typography.CAPTION)
        team_label.setStyleSheet(f"color: {ESPN_TEXT_MUTED};")
        header_row.addWidget(team_label)

        layout.addLayout(header_row)

        # Stats line
        stats = self._player_data.get('stats', '')
        if stats:
            stats_label = QLabel(f"• {stats}")
            stats_label.setFont(Typography.CAPTION)
            stats_label.setStyleSheet(f"color: {ESPN_TEXT_SECONDARY};")
            layout.addWidget(stats_label)

        # Rating line
        rating = self._player_data.get('rating', '')
        if rating:
            rating_label = QLabel(f"• {rating}")
            rating_label.setFont(Typography.CAPTION_BOLD)
            rating_label.setStyleSheet(f"color: {Colors.SUCCESS};")
            layout.addWidget(rating_label)

        layout.addStretch()


class TopPerformersWidget(QWidget):
    """
    Widget displaying top 5 player performances with weekly/season toggle.

    Shows the top performers of the week or season leaders based on the
    selected mode. Players are displayed in card format with position,
    name, team, and key statistics.

    Signals:
        mode_changed: Emitted when toggle switches between "weekly" and "season"
    """

    mode_changed = Signal(str)  # "weekly" or "season"

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the top performers widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._current_mode: str = "weekly"
        self._weekly_leaders: List[Dict] = []
        self._season_leaders: List[Dict] = []
        self._player_cards: List[PlayerPerformanceCard] = []

        # Context for data loading
        self._dynasty_id: Optional[int] = None
        self._db_path: Optional[str] = None
        self._season: Optional[int] = None
        self._week: Optional[int] = None

        self._setup_ui()

    def _setup_ui(self):
        """Build the widget UI."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header frame with toggle buttons
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            background-color: {ESPN_CARD_BG};
            border-bottom: 2px solid {ESPN_RED};
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(8)

        # Title
        title = QLabel("TOP PERFORMERS")
        title.setFont(Typography.H6)
        title.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-weight: bold;
            letter-spacing: 1px;
        """)
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Toggle buttons
        self.weekly_btn = QPushButton("Week")
        self.weekly_btn.setCheckable(True)
        self.weekly_btn.setChecked(True)
        self.weekly_btn.clicked.connect(lambda: self._on_toggle_clicked("weekly"))
        self.weekly_btn.setFixedWidth(60)

        self.season_btn = QPushButton("Season")
        self.season_btn.setCheckable(True)
        self.season_btn.setChecked(False)
        self.season_btn.clicked.connect(lambda: self._on_toggle_clicked("season"))
        self.season_btn.setFixedWidth(60)

        # Apply initial styles
        self._update_toggle_styles()

        header_layout.addWidget(self.weekly_btn)
        header_layout.addWidget(self.season_btn)

        main_layout.addWidget(header_frame)

        # Content area (scrollable if needed)
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"background-color: {ESPN_DARK_BG};")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(8)

        # Placeholder text (shown when no data)
        self.placeholder_label = QLabel("No performance data available")
        self.placeholder_label.setFont(Typography.BODY)
        self.placeholder_label.setStyleSheet(f"color: {ESPN_TEXT_MUTED};")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setVisible(True)
        self.content_layout.addWidget(self.placeholder_label)

        self.content_layout.addStretch()

        main_layout.addWidget(self.content_widget)

        # Set fixed height (header ~40px + 5 cards * 88px)
        self.setFixedHeight(450)

    def _get_toggle_button_style(self, is_selected: bool) -> str:
        """
        Get stylesheet for toggle button based on selection state.

        Args:
            is_selected: Whether this button is currently selected

        Returns:
            CSS stylesheet string
        """
        if is_selected:
            # Active button (ESPN red)
            return f"""
                QPushButton {{
                    background-color: {ESPN_RED};
                    color: {ESPN_TEXT_PRIMARY};
                    border: none;
                    border-radius: 4px;
                    padding: 6px 10px;
                    font-weight: bold;
                    font-size: {FontSizes.SMALL};
                }}
                QPushButton:hover {{
                    background-color: #dd0000;
                }}
            """
        else:
            # Inactive button (dark gray)
            return f"""
                QPushButton {{
                    background-color: #333333;
                    color: {ESPN_TEXT_MUTED};
                    border: none;
                    border-radius: 4px;
                    padding: 6px 10px;
                    font-size: {FontSizes.SMALL};
                }}
                QPushButton:hover {{
                    background-color: #3a3a3a;
                    color: {ESPN_TEXT_SECONDARY};
                }}
            """

    def _update_toggle_styles(self):
        """Update toggle button styles based on current mode."""
        self.weekly_btn.setStyleSheet(
            self._get_toggle_button_style(self._current_mode == "weekly")
        )
        self.season_btn.setStyleSheet(
            self._get_toggle_button_style(self._current_mode == "season")
        )

    def _on_toggle_clicked(self, mode: str):
        """
        Handle toggle button click.

        Args:
            mode: "weekly" or "season"
        """
        if mode == self._current_mode:
            return  # Already in this mode

        self._current_mode = mode

        # Update button checked states
        self.weekly_btn.setChecked(mode == "weekly")
        self.season_btn.setChecked(mode == "season")

        # Update button styles
        self._update_toggle_styles()

        # Update displayed data
        self._refresh_display()

        # Emit signal
        self.mode_changed.emit(mode)

    def _refresh_display(self):
        """Refresh the displayed player cards based on current mode."""
        # Clear existing cards
        self._clear_cards()

        # Get data for current mode
        if self._current_mode == "weekly":
            data = self._weekly_leaders
        else:
            data = self._season_leaders

        # Show placeholder if no data
        if not data:
            self.placeholder_label.setVisible(True)
            return

        self.placeholder_label.setVisible(False)

        # Create cards for top 5 players
        for player_data in data[:5]:
            card = PlayerPerformanceCard(player_data)
            self._player_cards.append(card)
            self.content_layout.insertWidget(
                self.content_layout.count() - 1,  # Before stretch
                card
            )

    def _clear_cards(self):
        """Remove all player cards from the display."""
        for card in self._player_cards:
            self.content_layout.removeWidget(card)
            card.deleteLater()
        self._player_cards.clear()

    # ==========================================================================
    # PUBLIC API
    # ==========================================================================

    def set_context(
        self,
        dynasty_id: int,
        db_path: str,
        season: int,
        week: int
    ):
        """
        Set the context for data loading.

        Args:
            dynasty_id: Dynasty ID for database queries
            db_path: Path to game cycle database
            season: Current season year
            week: Current week number
        """
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season
        self._week = week

        # Update weekly button text to show current week
        self.weekly_btn.setText(f"Week {week}")

    def set_weekly_leaders(self, players: List[Dict]):
        """
        Set the weekly top performers data.

        Args:
            players: List of player dicts (up to 5), each containing:
                - position: str (e.g., "QB")
                - name: str (player name)
                - team: str (team abbreviation)
                - stats: str (formatted stat line, e.g., "350 YDS, 4 TD, 0 INT")
                - rating: str (formatted rating, e.g., "Rating: 135.2")
                - team_color: Optional[str] (hex color for accent)

            Example:
                [
                    {
                        'position': 'QB',
                        'name': 'Patrick Mahomes',
                        'team': 'KC',
                        'stats': '350 YDS, 4 TD, 0 INT',
                        'rating': 'Rating: 135.2',
                        'team_color': '#E31837'
                    },
                    ...
                ]
        """
        self._weekly_leaders = players
        if self._current_mode == "weekly":
            self._refresh_display()

    def set_season_leaders(self, players: List[Dict]):
        """
        Set the season cumulative leaders data.

        Args:
            players: List of player dicts (up to 5), each containing:
                - position: str (e.g., "QB")
                - name: str (player name)
                - team: str (team abbreviation)
                - stats: str (formatted stat line, e.g., "4,200 YDS, 35 TD, 8 INT")
                - rating: str (formatted rating, e.g., "Rating: 102.4")
                - team_color: Optional[str] (hex color for accent)

            Example:
                [
                    {
                        'position': 'QB',
                        'name': 'Jared Goff',
                        'team': 'DET',
                        'stats': '4,200 YDS, 35 TD, 8 INT',
                        'rating': 'Rating: 102.4',
                        'team_color': '#0076B6'
                    },
                    ...
                ]
        """
        self._season_leaders = players
        if self._current_mode == "season":
            self._refresh_display()

    def get_current_mode(self) -> str:
        """
        Get the current display mode.

        Returns:
            "weekly" or "season"
        """
        return self._current_mode

    def clear(self):
        """Clear all data and reset to default state."""
        self._weekly_leaders = []
        self._season_leaders = []
        self._current_mode = "weekly"
        self.weekly_btn.setChecked(True)
        self.season_btn.setChecked(False)
        self._update_toggle_styles()
        self._clear_cards()
        self.placeholder_label.setVisible(True)

    # ==========================================================================
    # PLACEHOLDER DATA LOADING METHODS
    # ==========================================================================
    # These methods will be implemented later when database APIs are ready

    def _load_weekly_leaders_from_db(self):
        """
        Load weekly top performers from database.

        TODO: Implement when player_stats_api is ready.
        Query logic:
        1. Get all players with stats for current week
        2. Calculate performance scores by position
        3. Select top performer from each major position category
        4. Format stats based on position (QB: pass stats, RB: rush stats, etc.)
        """
        pass

    def _load_season_leaders_from_db(self):
        """
        Load season cumulative leaders from database.

        TODO: Implement when player_stats_api is ready.
        Query logic:
        1. Get season totals for all players
        2. Calculate performance scores by position
        3. Select top performer from each major position category
        4. Format cumulative stats
        """
        pass

    def _calculate_qb_rating(self, stats: Dict) -> float:
        """
        Calculate NFL passer rating.

        TODO: Implement standard NFL passer rating formula.

        Args:
            stats: Dict with 'pass_completions', 'pass_attempts', 'pass_yards',
                   'pass_touchdowns', 'interceptions'

        Returns:
            Passer rating (0-158.3)
        """
        return 0.0

    def _get_player_highlight_stat(self, position: str, stats: Dict) -> str:
        """
        Get the most relevant stat line for a player's position.

        TODO: Implement position-specific stat formatting.

        Args:
            position: Player position (QB, RB, WR, etc.)
            stats: Dict of player statistics

        Returns:
            Formatted stat string (e.g., "350 YDS, 4 TD, 0 INT")
        """
        return ""
