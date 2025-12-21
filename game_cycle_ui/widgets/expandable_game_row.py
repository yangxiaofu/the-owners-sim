"""
Expandable Game Row Widget for Regular Season Week View.

Provides an ESPN SportsCenter-style collapsible game row that displays:
- Pre-simulation: Team matchup with records and featured players
- Post-simulation: Final scores with top performers

Components:
- ExpandableGameRow: Main container with animation
- GameRowHeader: Always-visible header with team names, scores, expand arrow
- GameRowBody: Collapsible section with featured players or top performers
"""

from PySide6.QtWidgets import (
    QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget
)
from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QCursor

from constants.position_abbreviations import get_position_abbreviation
from utils.player_field_extractors import extract_overall_rating


class GameRowHeader(QFrame):
    """
    Header section of expandable game row.

    Layout:
    [▶] Team1 (W-L) @ Team2 (W-L)     [Game Time/Status]  [i]

    Post-simulation:
    [▼] Team1 Score - Team2 Score     [✓ FINAL]           [i]
    """

    arrow_clicked = Signal()
    info_clicked = Signal()

    def __init__(self, game_data: dict, parent=None):
        super().__init__(parent)
        self.game_data = game_data
        self.is_played = game_data.get('is_played', False)

        # Widgets (created in _init_ui)
        self.arrow_label = None
        self.matchup_label = None
        self.time_label = None
        self.info_button = None

        self._init_ui()
        self._setup_styling()

    def _init_ui(self):
        """Build header layout."""
        # Set minimum height for better readability and clickability
        self.setMinimumHeight(55)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(8)

        # Expand/collapse arrow (clickable)
        self.arrow_label = QLabel("▶")
        self.arrow_label.setObjectName("arrow_label")
        self.arrow_label.setFixedWidth(20)
        self.arrow_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.arrow_label.mousePressEvent = lambda e: self.arrow_clicked.emit()
        layout.addWidget(self.arrow_label)

        # Matchup text (e.g., "LV Raiders (4-4) @ DEN Broncos (3-6)")
        matchup_text = self._build_matchup_text()
        self.matchup_label = QLabel(matchup_text)
        self.matchup_label.setObjectName("matchup_label")
        layout.addWidget(self.matchup_label, stretch=1)

        # Spacer
        layout.addStretch()

        # Time/status label
        time_text = self._build_time_text()
        self.time_label = QLabel(time_text)
        self.time_label.setObjectName("time_label")
        layout.addWidget(self.time_label)

        # Info button [i]
        self.info_button = QPushButton("ⓘ")
        self.info_button.setObjectName("info_button")
        self.info_button.setFixedSize(24, 24)
        self.info_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.info_button.clicked.connect(self.info_clicked.emit)
        layout.addWidget(self.info_button)

    def _build_matchup_text(self) -> str:
        """Build matchup text based on current state."""
        away = self.game_data['away_team']
        home = self.game_data['home_team']

        if self.is_played:
            # Post-simulation: "LV 20 - DEN 17"
            away_score = self.game_data.get('away_score', 0)
            home_score = self.game_data.get('home_score', 0)
            return f"{away['abbreviation']} {away_score} - {home['abbreviation']} {home_score}"
        else:
            # Pre-simulation: "LV Raiders (4-4) @ DEN Broncos (3-6)"
            return (
                f"{away['abbreviation']} {away['name']} ({away['record']}) @ "
                f"{home['abbreviation']} {home['name']} ({home['record']})"
            )

    def _build_time_text(self) -> str:
        """Build time/status text."""
        if self.is_played:
            return "✓ FINAL"
        else:
            # TODO: Pull from game_data if time slot exists
            return "📅 Scheduled"

    def set_expanded(self, expanded: bool):
        """Update arrow icon based on expansion state."""
        self.arrow_label.setText("▼" if expanded else "▶")

    def update_with_result(self, result_data: dict):
        """Update header after simulation."""
        self.is_played = True
        self.game_data.update(result_data)
        self.matchup_label.setText(self._build_matchup_text())
        self.time_label.setText(self._build_time_text())

    def _setup_styling(self):
        """Apply CSS styling to header."""
        self.setObjectName("game_row_header")
        self.setStyleSheet("""
            QFrame#game_row_header {
                background-color: transparent;
            }
            QFrame#game_row_header:hover {
                background-color: #2d2d2d;
            }
            QLabel#arrow_label {
                font-size: 14px;
                color: #888;
            }
            QLabel#arrow_label:hover {
                color: #fff;
            }
            QLabel#matchup_label {
                font-size: 14px;
                font-weight: bold;
            }
            QLabel#time_label {
                font-size: 12px;
                color: #888;
            }
            QPushButton#info_button {
                background-color: transparent;
                border: 1px solid #888;
                border-radius: 12px;
                color: #888;
                font-size: 11px;
            }
            QPushButton#info_button:hover {
                background-color: #3d3d3d;
                border-color: #fff;
                color: #fff;
            }
        """)


class GameRowBody(QFrame):
    """
    Collapsible body section showing featured players or top performers.

    Pre-simulation layout:
    ┌─────────────────────────────────────────────────┐
    │  Away Team Featured Players:                     │
    │  • QB Player Name (OVR)                          │
    │  • RB Player Name (OVR)                          │
    │  • WR Player Name (OVR)                          │
    │                                                   │
    │  Home Team Featured Players:                     │
    │  • QB Player Name (OVR)                          │
    │  • RB Player Name (OVR)                          │
    │  • WR Player Name (OVR)                          │
    └─────────────────────────────────────────────────┘

    Post-simulation layout:
    ┌─────────────────────────────────────────────────┐
    │  Away Team Top Performers:                       │
    │  • QB Player: 287 yds, 2 TD, 0 INT               │
    │  • RB Player: 112 yds, 1 TD                      │
    │  • WR Player: 8 rec, 95 yds                      │
    │                                                   │
    │  Home Team Top Performers:                       │
    │  • QB Player: 245 yds, 1 TD, 1 INT               │
    │  • RB Player: 87 yds                             │
    │  • WR Player: 6 rec, 78 yds                      │
    └─────────────────────────────────────────────────┘
    """

    def __init__(self, game_data: dict, parent=None):
        super().__init__(parent)
        self.game_data = game_data
        self.is_played = game_data.get('is_played', False)
        self._content_loaded = False  # For lazy loading

        # Widgets (created in _build_content)
        self.away_header = None
        self.away_players_layout = None
        self.home_header = None
        self.home_players_layout = None
        self.stats_label = None

        self._setup_styling()

    def _build_content(self):
        """Build body layout with featured players (lazy-loaded on first expansion)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 12, 12, 12)  # Indent from arrow
        layout.setSpacing(12)

        # Create horizontal layout for two columns
        columns_layout = QHBoxLayout()

        # Away team column
        away_column = self._build_team_section(
            team_data=self.game_data['away_team'],
            is_home=False
        )
        columns_layout.addLayout(away_column)

        # Spacer between columns
        columns_layout.addSpacing(40)

        # Home team column
        home_column = self._build_team_section(
            team_data=self.game_data['home_team'],
            is_home=True
        )
        columns_layout.addLayout(home_column)

        layout.addLayout(columns_layout)

        # Game stats (only shown post-simulation)
        self.stats_label = QLabel("")
        self.stats_label.setObjectName("stats_label")
        self.stats_label.setVisible(False)
        layout.addWidget(self.stats_label)

        self._content_loaded = True

    def _build_team_section(self, team_data: dict, is_home: bool) -> QVBoxLayout:
        """Build featured/top players section for one team."""
        section_layout = QVBoxLayout()
        section_layout.setSpacing(4)

        # Header
        team_name = team_data['name']
        header_text = f"{team_name} {'Top Performers' if self.is_played else 'Featured Players'}:"
        header = QLabel(header_text)
        header.setObjectName("team_section_header")
        section_layout.addWidget(header)

        # Store reference to header for updates
        if is_home:
            self.home_header = header
        else:
            self.away_header = header

        # Player list container
        players_layout = QVBoxLayout()
        players_layout.setSpacing(2)

        # Get players and populate list
        players = self._get_featured_or_top_players(team_data['team_id'], is_home)
        for player in players:
            player_label = QLabel(self._format_player_text(player))
            player_label.setObjectName("player_label")
            players_layout.addWidget(player_label)

        # Store reference to players layout for updates
        if is_home:
            self.home_players_layout = players_layout
        else:
            self.away_players_layout = players_layout

        section_layout.addLayout(players_layout)
        section_layout.addStretch()
        return section_layout

    def _get_featured_or_top_players(self, team_id: int, is_home: bool) -> list:
        """
        Get featured players (pre-game) or top performers (post-game).

        This will be replaced with actual database queries in implementation.
        """
        if self.is_played:
            # Post-game: Get from result_data
            performers_key = 'home' if is_home else 'away'
            return self.game_data.get('top_performers', {}).get(performers_key, [])
        else:
            # Pre-game: Get from featured_players in game_data
            players_key = 'home_featured' if is_home else 'away_featured'
            return self.game_data.get(players_key, [])

    def _format_player_text(self, player: dict) -> str:
        """Format player text based on pre/post simulation."""
        name = player.get('name', 'Unknown Player')
        position_raw = player.get('position', 'N/A')

        # Convert position from underscore format to abbreviation (e.g., "quarterback" → "QB")
        position = get_position_abbreviation(position_raw) if position_raw != 'N/A' else 'N/A'

        if self.is_played:
            # Post-game: "QB G. Minshew: 287 yds, 2 TD, 0 INT"
            stats = player.get('stats', '')
            return f"• {position} {name}: {stats}"
        else:
            # Pre-game: "QB Gardner Minshew (85 OVR)"
            overall = extract_overall_rating(player, default=0)
            return f"• {position} {name} ({overall} OVR)"

    def update_with_result(self, result_data: dict):
        """Update body after simulation with top performers."""
        self.is_played = True
        self.game_data.update(result_data)

        # Update headers
        if self.away_header:
            away_name = self.game_data['away_team']['name']
            self.away_header.setText(f"{away_name} Top Performers:")

        if self.home_header:
            home_name = self.game_data['home_team']['name']
            self.home_header.setText(f"{home_name} Top Performers:")

        # Rebuild player lists with top performers
        # (In production, we'd update existing widgets, but for simplicity we'll rebuild)
        self._rebuild_player_lists()

        # Update stats label if game stats exist
        if 'game_stats' in result_data:
            stats = result_data['game_stats']
            stats_text = (
                f"Game Stats: "
                f"Pass: {stats.get('away_pass', 0)}-{stats.get('home_pass', 0)} | "
                f"Rush: {stats.get('away_rush', 0)}-{stats.get('home_rush', 0)}"
            )
            self.stats_label.setText(stats_text)
            self.stats_label.setVisible(True)

    def _rebuild_player_lists(self):
        """Rebuild player lists after result update."""
        # Clear and rebuild away players
        if self.away_players_layout:
            # Clear existing items
            while self.away_players_layout.count():
                item = self.away_players_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Add updated players
            away_players = self._get_featured_or_top_players(
                self.game_data['away_team']['team_id'], is_home=False
            )
            for player in away_players:
                player_label = QLabel(self._format_player_text(player))
                player_label.setObjectName("player_label")
                self.away_players_layout.addWidget(player_label)

        # Clear and rebuild home players
        if self.home_players_layout:
            # Clear existing items
            while self.home_players_layout.count():
                item = self.home_players_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Add updated players
            home_players = self._get_featured_or_top_players(
                self.game_data['home_team']['team_id'], is_home=True
            )
            for player in home_players:
                player_label = QLabel(self._format_player_text(player))
                player_label.setObjectName("player_label")
                self.home_players_layout.addWidget(player_label)

    def setVisible(self, visible: bool):
        """Override to lazy-load content on first expansion."""
        if visible and not self._content_loaded:
            # First time expanding - create widgets now
            self._build_content()

        super().setVisible(visible)

    def _setup_styling(self):
        """Apply CSS styling to body."""
        self.setObjectName("game_row_body")
        self.setStyleSheet("""
            QFrame#game_row_body {
                background-color: #252525;
                border-top: 1px solid #3d3d3d;
            }
            QLabel#team_section_header {
                font-size: 12px;
                font-weight: bold;
                margin-bottom: 4px;
            }
            QLabel#player_label {
                font-size: 11px;
                margin-left: 8px;
                color: #ccc;
            }
            QLabel#stats_label {
                font-size: 11px;
                color: #666;
                margin-top: 8px;
            }
        """)


class ExpandableGameRow(QFrame):
    """
    Expandable game row with three distinct states:
    - PREVIEW_COLLAPSED: Before simulation, collapsed (default)
    - PREVIEW_EXPANDED: Before simulation, expanded (user clicked arrow)
    - RESULT_EXPANDED: After simulation, auto-expanded with results
    """

    # Signals
    info_clicked = Signal(str)  # Emits game_id when [i] icon clicked
    expanded_changed = Signal(bool)  # Emits when expansion state changes

    def __init__(self, game_data: dict, parent=None):
        super().__init__(parent)

        # State variables
        self.game_data = game_data
        self.game_id = game_data['game_id']
        self.is_played = game_data.get('is_played', False)
        self.expanded = False
        self.animation_duration = 200  # ms

        # Sub-widgets (created in _init_ui)
        self.header_widget = None      # GameRowHeader
        self.body_widget = None        # GameRowBody
        self.expand_animation = None   # QPropertyAnimation

        self._init_ui()
        self._setup_styling()
        self._connect_signals()

    def _init_ui(self):
        """Initialize UI with header and collapsible body."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header (always visible)
        self.header_widget = GameRowHeader(
            game_data=self.game_data,
            parent=self
        )
        layout.addWidget(self.header_widget)

        # Body (collapsible)
        self.body_widget = GameRowBody(
            game_data=self.game_data,
            parent=self
        )
        self.body_widget.setVisible(False)  # Hidden by default
        self.body_widget.setMaximumHeight(0)  # For smooth animation
        layout.addWidget(self.body_widget)

        # Setup expand/collapse animation
        self.expand_animation = QPropertyAnimation(
            self.body_widget,
            b"maximumHeight"
        )
        self.expand_animation.setDuration(self.animation_duration)
        self.expand_animation.setEasingCurve(QEasingCurve.InOutQuad)

    def toggle_expansion(self):
        """Toggle between expanded/collapsed state with smooth animation."""
        self.expanded = not self.expanded

        # Update header arrow icon
        self.header_widget.set_expanded(self.expanded)

        if self.expanded:
            # Expand animation
            self.body_widget.setVisible(True)
            target_height = self.body_widget.sizeHint().height()
            self.expand_animation.setStartValue(0)
            self.expand_animation.setEndValue(target_height)
            self.expand_animation.start()
        else:
            # Collapse animation
            current_height = self.body_widget.height()
            self.expand_animation.setStartValue(current_height)
            self.expand_animation.setEndValue(0)

            # Hide body after animation completes
            def on_collapse_finished():
                if not self.expanded:  # Only hide if still collapsed
                    self.body_widget.setVisible(False)

            self.expand_animation.finished.connect(on_collapse_finished)
            self.expand_animation.start()

        # Emit signal
        self.expanded_changed.emit(self.expanded)

    def update_with_result(self, result_data: dict):
        """
        Update row after simulation completes.

        Args:
            result_data: {
                'game_id': str,
                'home_score': int,
                'away_score': int,
                'top_performers': {
                    'home': [player_dict, ...],
                    'away': [player_dict, ...]
                },
                'game_stats': {...}  # Optional
            }
        """
        # Update internal state
        self.is_played = True
        self.game_data.update(result_data)

        # Update header with scores
        self.header_widget.update_with_result(result_data)

        # Update body with top performers
        self.body_widget.update_with_result(result_data)

        # Auto-expand if currently collapsed
        if not self.expanded:
            self.toggle_expansion()

    def _setup_styling(self):
        """Apply CSS styling to row."""
        self.setObjectName("expandable_game_row")
        self.setStyleSheet("""
            QFrame#expandable_game_row {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                margin: 2px 0;
            }
            QFrame#expandable_game_row:hover {
                background-color: #353535;
                border-color: #4d4d4d;
            }
        """)

    def _connect_signals(self):
        """Connect internal signals."""
        # Header arrow clicked → toggle expansion
        self.header_widget.arrow_clicked.connect(self.toggle_expansion)

        # Header info icon clicked → emit game_id
        self.header_widget.info_clicked.connect(
            lambda: self.info_clicked.emit(self.game_id)
        )
