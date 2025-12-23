"""
Preseason View - Displays preseason games.

Modern NFL (2024+) style:
- Weeks 1-3: Game results only (roster cuts happen in separate stage after Week 3)
- Navigation: Review all preseason weeks with Prev/Next buttons

Shows preseason game schedule, simulated game results, and your team's games.
"""

from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QSplitter, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from game_cycle_ui.theme import (
    Typography, TextColors, apply_table_style, UITheme,
    Colors, FontSizes
)
from game_cycle_ui.widgets import SummaryPanel


class PreseasonView(QWidget):
    """
    View for preseason weeks (OFFSEASON_PRESEASON_W1/W2/W3).

    Features:
    - Game results table showing all preseason games
    - User's game highlighted prominently
    - Navigation: Prev/Next buttons to review past preseason weeks
    - Read-only review mode for completed weeks

    Signals:
        advance_requested: Emitted when ready to advance stage
        game_selected: Emitted when user double-clicks a game to view box score
    """

    # Signals
    advance_requested = Signal()
    game_selected = Signal(str)  # game_id - for viewing box scores

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._preseason_week: int = 1          # Actual current stage week
        self._display_week: int = 1            # Week currently being viewed
        self._max_completed_week: int = 0      # Highest week simulated so far
        self._games: List[Dict[str, Any]] = []
        self._user_team_id: int = 1
        self._dynasty_id: Optional[str] = None
        self._db_path: Optional[str] = None
        self._season: int = 2025
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header with week info
        self._create_header(layout)

        # Navigation controls
        self._create_navigation_header(layout)

        # Main content area
        self._create_content_area(layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create the header section with SummaryPanel."""
        # SummaryPanel with key stats
        self.summary_panel = SummaryPanel("Preseason")
        self.week_stat = self.summary_panel.add_stat("Week", "1", Colors.INFO)
        self.games_stat = self.summary_panel.add_stat("Games", "0", Colors.INFO)
        self.status_stat = self.summary_panel.add_stat("Roster", "90 players", Colors.SUCCESS)
        self.summary_panel.add_stretch()

        parent_layout.addWidget(self.summary_panel)

        # Description label below summary panel
        self.description_label = QLabel("Exhibition games - Results do not affect regular season standings")
        self.description_label.setFont(Typography.BODY)
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY}; padding: 8px 0px;")
        parent_layout.addWidget(self.description_label)

    def _create_navigation_header(self, parent_layout: QVBoxLayout):
        """Create week navigation controls (Prev/Next buttons)."""
        nav_frame = QFrame()
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(8, 4, 8, 4)
        nav_layout.setSpacing(12)

        # Previous week button
        self.prev_week_btn = QPushButton("< Prev Week")
        self.prev_week_btn.setStyleSheet(UITheme.button_style("secondary"))
        self.prev_week_btn.setMinimumWidth(120)
        self.prev_week_btn.clicked.connect(self._on_prev_week)
        nav_layout.addWidget(self.prev_week_btn)

        # Current week display
        self.nav_week_label = QLabel("Week 1")
        self.nav_week_label.setFont(Typography.H3)
        self.nav_week_label.setStyleSheet(f"color: {Colors.INFO}; font-weight: bold;")
        self.nav_week_label.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(self.nav_week_label, stretch=1)

        # Review mode indicator (hidden by default)
        self.review_indicator = QLabel("(Review Mode - Read Only)")
        self.review_indicator.setFont(Typography.BODY_SMALL)
        self.review_indicator.setStyleSheet(f"color: {Colors.WARNING}; font-style: italic;")
        self.review_indicator.setAlignment(Qt.AlignCenter)
        self.review_indicator.setVisible(False)
        nav_layout.addWidget(self.review_indicator)

        # Next week button
        self.next_week_btn = QPushButton("Next Week >")
        self.next_week_btn.setStyleSheet(UITheme.button_style("secondary"))
        self.next_week_btn.setMinimumWidth(120)
        self.next_week_btn.clicked.connect(self._on_next_week)
        nav_layout.addWidget(self.next_week_btn)

        parent_layout.addWidget(nav_frame)

    def _create_content_area(self, parent_layout: QVBoxLayout):
        """Create the main content area with games."""
        # User's game highlight box
        self._create_user_game_section(parent_layout)

        # Games table
        self._create_games_table(parent_layout)

    def _create_user_game_section(self, parent_layout: QVBoxLayout):
        """Create the user's game highlight section."""
        self.user_game_group = QGroupBox("Your Game")
        self.user_game_group.setStyleSheet(f"""
            QGroupBox {{
                font-family: {Typography.FAMILY};
                font-size: {FontSizes.H4};
                font-weight: bold;
                color: {Colors.INFO};
                border: 2px solid {Colors.INFO};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 16px;
                background-color: rgba(25, 118, 210, 0.05);
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 8px;
                background-color: #1a2a3a;
                border-radius: 4px;
            }}
        """)

        user_game_layout = QHBoxLayout(self.user_game_group)

        self.user_game_label = QLabel("No game scheduled")
        self.user_game_label.setFont(Typography.H3)
        self.user_game_label.setStyleSheet("color: white;")
        self.user_game_label.setAlignment(Qt.AlignCenter)
        user_game_layout.addWidget(self.user_game_label)

        parent_layout.addWidget(self.user_game_group)

    def _create_games_table(self, parent_layout: QVBoxLayout):
        """Create the games results table."""
        games_group = QGroupBox("All Preseason Games")
        games_layout = QVBoxLayout(games_group)

        self.games_table = QTableWidget()
        self.games_table.setColumnCount(5)
        self.games_table.setHorizontalHeaderLabels([
            "Away", "Score", "@", "Home", "Score"
        ])

        # Apply standard table styling
        apply_table_style(self.games_table)

        # Configure header
        header = self.games_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Away
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Away Score
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # @
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Home
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Home Score

        self.games_table.verticalHeader().setVisible(False)
        self.games_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.games_table.setSelectionMode(QTableWidget.SingleSelection)
        self.games_table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Connect double-click to view box score
        self.games_table.cellDoubleClicked.connect(self._on_game_double_clicked)

        games_layout.addWidget(self.games_table)
        parent_layout.addWidget(games_group)

    def set_context(self, dynasty_id: str, db_path: str, season: int, user_team_id: int):
        """Set the context for this view."""
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season
        self._user_team_id = user_team_id

    def set_week(self, week: int):
        """Set the preseason week (1-3) - the actual current stage."""
        self._preseason_week = week

        # Set display week to current week by default
        self._display_week = week

        # Track max completed week (weeks before current are completed)
        self._max_completed_week = max(self._max_completed_week, week - 1)

        # Update summary panel week stat
        self.week_stat.setText(str(week))

        # Update navigation label
        self.nav_week_label.setText(f"Week {week}")
        self._update_nav_buttons()

        # Review indicator off when viewing current week
        self.review_indicator.setVisible(False)

        # Update description (same for all weeks)
        self.description_label.setText(
            "Exhibition games - Results do not affect regular season standings"
        )

        # Fetch and display games for this week (ensures fresh data on stage transitions)
        self._fetch_and_display_games(week)

    def set_games(self, games: List[Dict[str, Any]]):
        """
        Set the preseason games to display.

        Args:
            games: List of game dicts with keys:
                - home_team_id, away_team_id
                - home_score, away_score (may be None if not played)
                - home_team_name, away_team_name (optional)
                - is_user_game (bool)
        """
        self._games = games

        # Update summary panel game count
        self.games_stat.setText(str(len(games)))

        self._refresh_games_table()
        self._refresh_user_game()

    def set_roster_status(self, current_size: int, target_size: int = 90):
        """Update the roster status display."""
        # Update summary panel roster stat (just show current size)
        self.status_stat.setText(f"{current_size} players")
        self.status_stat.setStyleSheet(f"color: {Colors.INFO};")

    def _refresh_games_table(self):
        """Refresh the games table with current data."""
        self.games_table.setRowCount(len(self._games))

        for row, game in enumerate(self._games):
            home_team_id = game.get("home_team_id", 0)
            away_team_id = game.get("away_team_id", 0)
            home_score = game.get("home_score")
            away_score = game.get("away_score")
            is_user_game = game.get("is_user_game", False)

            # Get team names
            home_name = game.get("home_team_name") or self._get_team_name(home_team_id)
            away_name = game.get("away_team_name") or self._get_team_name(away_team_id)

            # Away team
            away_item = QTableWidgetItem(away_name)
            away_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # Away score
            away_score_text = str(away_score) if away_score is not None else "-"
            away_score_item = QTableWidgetItem(away_score_text)
            away_score_item.setTextAlignment(Qt.AlignCenter)

            # @ symbol
            at_item = QTableWidgetItem("@")
            at_item.setTextAlignment(Qt.AlignCenter)

            # Home team
            home_item = QTableWidgetItem(home_name)
            home_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # Home score
            home_score_text = str(home_score) if home_score is not None else "-"
            home_score_item = QTableWidgetItem(home_score_text)
            home_score_item.setTextAlignment(Qt.AlignCenter)

            # Highlight user's game
            if is_user_game:
                highlight_color = QColor(Colors.INFO)
                for item in [away_item, away_score_item, at_item, home_item, home_score_item]:
                    item.setBackground(highlight_color)
                    item.setForeground(QColor(TextColors.ON_DARK))

            # Set items
            self.games_table.setItem(row, 0, away_item)
            self.games_table.setItem(row, 1, away_score_item)
            self.games_table.setItem(row, 2, at_item)
            self.games_table.setItem(row, 3, home_item)
            self.games_table.setItem(row, 4, home_score_item)

    def _refresh_user_game(self):
        """Refresh the user's game highlight section."""
        user_game = None
        for game in self._games:
            if game.get("is_user_game"):
                user_game = game
                break

        if user_game:
            home_team_id = user_game.get("home_team_id", 0)
            away_team_id = user_game.get("away_team_id", 0)
            home_score = user_game.get("home_score")
            away_score = user_game.get("away_score")

            home_name = user_game.get("home_team_name") or self._get_team_name(home_team_id)
            away_name = user_game.get("away_team_name") or self._get_team_name(away_team_id)

            if home_score is not None and away_score is not None:
                self.user_game_label.setText(
                    f"{away_name}  {away_score}  @  {home_name}  {home_score}"
                )
            else:
                self.user_game_label.setText(f"{away_name} @ {home_name} (Not yet played)")
        else:
            self.user_game_label.setText("No game this week")

    def _get_team_name(self, team_id: int) -> str:
        """Get team name from ID."""
        try:
            from constants.team_names import get_team_by_id
            team = get_team_by_id(team_id)
            return team.get("abbreviation", f"Team {team_id}")
        except Exception:
            return f"Team {team_id}"

    def _on_game_double_clicked(self, row: int, column: int):
        """Handle double-click on game row to view box score."""
        if row < 0 or row >= len(self._games):
            return

        game = self._games[row]
        game_id = game.get("game_id")

        if not game_id:
            return

        # Only show box score if game has been played
        is_played = game.get("is_played", False)
        if not is_played:
            # Game not yet played - do nothing
            return

        # Emit signal for parent to handle
        self.game_selected.emit(game_id)

    def _on_prev_week(self):
        """Navigate to previous preseason week."""
        if self._display_week > 1:
            self._display_week -= 1
            self._refresh_display_for_week(self._display_week)

    def _on_next_week(self):
        """Navigate to next preseason week."""
        if self._display_week < 3:
            self._display_week += 1
            self._refresh_display_for_week(self._display_week)

    def _refresh_display_for_week(self, week: int):
        """Refresh the view to display a specific week's games."""
        # Update navigation UI
        self.nav_week_label.setText(f"Week {week}")
        self._update_nav_buttons()

        # Update week stat in summary panel
        self.week_stat.setText(str(week))

        # Check if in review mode (viewing a past week)
        is_review_mode = (week < self._preseason_week)
        self.review_indicator.setVisible(is_review_mode)

        # Fetch and display games for this week
        self._fetch_and_display_games(week)

    def _update_nav_buttons(self):
        """Enable/disable navigation buttons based on boundaries."""
        # Prev enabled if not at Week 1
        self.prev_week_btn.setEnabled(self._display_week > 1)

        # Next enabled if not at max completed week OR current stage week
        max_viewable = max(self._max_completed_week, self._preseason_week)
        self.next_week_btn.setEnabled(self._display_week < min(max_viewable, 3))

    def _fetch_and_display_games(self, week: int):
        """Fetch games from database for specified week and display them."""
        print(f"[PreseasonView] _fetch_and_display_games called for week {week}")
        print(f"[PreseasonView] Context: dynasty_id={self._dynasty_id}, db_path={self._db_path}")

        if not self._dynasty_id or not self._db_path:
            print(f"[PreseasonView] ERROR: Cannot fetch games - missing context!")
            return

        try:
            import sys
            import os
            # Add src to path if not already there
            src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
            if src_path not in sys.path:
                sys.path.insert(0, src_path)

            from game_cycle.services.preseason_schedule_service import PreseasonScheduleService
            from team_management.teams.team_loader import get_team_by_id

            service = PreseasonScheduleService(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._season
            )

            # Fetch games for this week
            games = service.get_preseason_games(week=week)
            print(f"[PreseasonView] Fetched {len(games)} games from database for week {week}")
            if games:
                # Show first game as example
                first_game = games[0].get("parameters", {})
                print(f"[PreseasonView] First game: {first_game.get('home_team_id')} vs {first_game.get('away_team_id')}")

            # Build matchup format for display
            display_games = []
            for game_data in games:
                params = game_data.get("parameters", {})
                results = game_data.get("results") or {}  # Handle None case for unplayed games

                home_team_id = params.get("home_team_id")
                away_team_id = params.get("away_team_id")

                home_team = get_team_by_id(home_team_id)
                away_team = get_team_by_id(away_team_id)

                display_games.append({
                    "game_id": game_data.get("event_id"),
                    "home_team_id": home_team_id,
                    "away_team_id": away_team_id,
                    "home_team_name": home_team.full_name if home_team else f"Team {home_team_id}",
                    "away_team_name": away_team.full_name if away_team else f"Team {away_team_id}",
                    "home_abbreviation": home_team.abbreviation if home_team else "???",
                    "away_abbreviation": away_team.abbreviation if away_team else "???",
                    "home_score": results.get("home_score"),
                    "away_score": results.get("away_score"),
                    "is_played": results.get("home_score") is not None,
                    "is_user_game": (home_team_id == self._user_team_id or
                                    away_team_id == self._user_team_id),
                    "week": week
                })

            # Update games display
            self._games = display_games
            self.games_stat.setText(str(len(display_games)))
            print(f"[PreseasonView] Set {len(display_games)} games for display")
            self._refresh_games_table()
            self._refresh_user_game()

        except Exception as e:
            print(f"[PreseasonView] ERROR fetching games for week {week}: {e}")
            import traceback
            traceback.print_exc()
