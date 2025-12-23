"""
Popularity View - League-wide player popularity rankings.

Displays top 50 most popular players with filtering by tier and position.
Shows popularity scores, trends, and component breakdowns.

Part of Milestone 16: Player Popularity.
"""

import logging
from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QComboBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from constants.position_abbreviations import get_position_abbreviation
from game_cycle_ui.theme import (
    TAB_STYLE, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE,
    Typography, FontSizes, TextColors, apply_table_style,
    GRADE_TIER_COLORS
)
from game_cycle_ui.widgets import SummaryPanel

logger = logging.getLogger(__name__)


class NumericTableWidgetItem(QTableWidgetItem):
    """Custom QTableWidgetItem that sorts numerically instead of alphabetically."""

    def __init__(self, value: Any, display_text: str = None):
        """
        Args:
            value: The numeric value for sorting
            display_text: The text to display (if different from value)
        """
        super().__init__(display_text if display_text else str(value))
        self._sort_value = value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            # Handle None/0 values
            self_val = self._sort_value if self._sort_value is not None else 0
            other_val = other._sort_value if other._sort_value is not None else 0
            return self_val < other_val
        return super().__lt__(other)


class PopularityView(QWidget):
    """
    View for displaying league-wide player popularity rankings.

    Shows top 50 most popular players with:
    - Sortable columns (rank, player, team, score, tier, trend, components)
    - Tier filtering (All / Transcendent / Star / Known / Role Player / Unknown)
    - Position filtering (All / QB / WR / RB / etc.)
    - Trend indicators (↑/↓/→ with week change)
    - Double-click to open player detail dialog
    - Refresh button to recalculate current week
    """

    # Signals
    refresh_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._season: int = 2025
        self._week: int = 1
        self._dynasty_id: str = ""
        self._db_path: str = ""
        self._popularity_api = None

        # Filter state
        self._tier_filter: Optional[str] = None  # None = All
        self._position_filter: Optional[str] = None  # None = All

        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header with filters and refresh
        self._create_header(layout)

        # Summary panel
        self._create_summary_panel(layout)

        # Main rankings table
        self._create_rankings_table(layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create header with title, filters, and refresh button."""
        header = QHBoxLayout()

        # Title
        title = QLabel("PLAYER POPULARITY RANKINGS")
        title.setFont(Typography.H4)
        header.addWidget(title)

        header.addStretch()

        # Tier filter
        tier_label = QLabel("Tier:")
        header.addWidget(tier_label)

        self.tier_combo = QComboBox()
        self.tier_combo.setMinimumWidth(150)
        self.tier_combo.addItem("All Tiers", None)
        self.tier_combo.addItem("Transcendent (90-100)", "TRANSCENDENT")
        self.tier_combo.addItem("Star (75-89)", "STAR")
        self.tier_combo.addItem("Known (50-74)", "KNOWN")
        self.tier_combo.addItem("Role Player (25-49)", "ROLE_PLAYER")
        self.tier_combo.addItem("Unknown (0-24)", "UNKNOWN")
        self.tier_combo.currentIndexChanged.connect(self._on_tier_changed)
        header.addWidget(self.tier_combo)

        header.addSpacing(20)

        # Position filter
        pos_label = QLabel("Position:")
        header.addWidget(pos_label)

        self.position_combo = QComboBox()
        self.position_combo.setMinimumWidth(120)
        self._populate_position_combo()
        self.position_combo.currentIndexChanged.connect(self._on_position_changed)
        header.addWidget(self.position_combo)

        header.addSpacing(20)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        header.addWidget(self.refresh_btn)

        parent_layout.addLayout(header)

    def _populate_position_combo(self):
        """Populate position dropdown with all positions."""
        self.position_combo.addItem("All Positions", None)

        # Offense
        self.position_combo.addItem("QB", "QB")
        self.position_combo.addItem("RB", "RB")
        self.position_combo.addItem("WR", "WR")
        self.position_combo.addItem("TE", "TE")

        # Defense
        self.position_combo.addItem("EDGE", "EDGE")
        self.position_combo.addItem("DT", "DT")
        self.position_combo.addItem("LB", "LB")
        self.position_combo.addItem("CB", "CB")
        self.position_combo.addItem("S", "S")

        # Special Teams
        self.position_combo.addItem("K", "K")
        self.position_combo.addItem("P", "P")

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create summary statistics panel."""
        summary_panel = SummaryPanel("Popularity Summary")

        # Total tracked players
        self.total_players_label = summary_panel.add_stat("Players Tracked", "0")

        # Average popularity
        self.avg_popularity_label = summary_panel.add_stat("Avg Popularity", "0.0")

        # Top player
        self.top_player_label = summary_panel.add_stat("Top Player", "-")

        # Current week
        self.week_label = summary_panel.add_stat("Week", "1")

        summary_panel.add_stretch()
        parent_layout.addWidget(summary_panel)

    def _create_rankings_table(self, parent_layout: QVBoxLayout):
        """Create the main rankings table."""
        self.rankings_table = QTableWidget()
        self.rankings_table.setColumnCount(10)
        self.rankings_table.setHorizontalHeaderLabels([
            "Rank", "Player", "Pos", "Team", "Score", "Tier", "Trend",
            "Performance", "Visibility", "Market"
        ])

        # Apply standard ESPN dark table styling
        apply_table_style(self.rankings_table)

        # Configure column resize modes
        header = self.rankings_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Rank
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Player name
        for i in range(2, 10):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # Enable sorting by clicking column headers
        self.rankings_table.setSortingEnabled(True)

        # Connect double-click to open player detail dialog
        self.rankings_table.cellDoubleClicked.connect(self._on_player_double_clicked)

        parent_layout.addWidget(self.rankings_table, stretch=1)

    # === Context and Data Methods ===

    def set_context(self, dynasty_id: str, db_path: str, season: int, week: int):
        """
        Set dynasty context for data queries.

        Args:
            dynasty_id: Dynasty identifier
            db_path: Path to game_cycle database
            season: Current season year
            week: Current week number
        """
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season
        self._week = week

        # Initialize PopularityAPI
        try:
            from game_cycle.database.connection import GameCycleDatabase
            from game_cycle.database.popularity_api import PopularityAPI

            db = GameCycleDatabase(db_path)
            self._popularity_api = PopularityAPI(db)

        except ImportError as e:
            logger.error(f"[PopularityView] Failed to import PopularityAPI: {e}")
            self._popularity_api = None

    def refresh_rankings(self):
        """Refresh popularity rankings from database."""
        if not self._popularity_api or not self._dynasty_id:
            logger.warning("[PopularityView] No API or dynasty context")
            return

        try:
            # Get top 50 players (or filtered by tier)
            if self._tier_filter:
                scores = self._popularity_api.get_players_by_tier(
                    self._dynasty_id,
                    self._season,
                    self._week,
                    self._tier_filter
                )
            else:
                scores = self._popularity_api.get_top_players(
                    self._dynasty_id,
                    self._season,
                    self._week,
                    limit=50
                )

            # Filter by position if needed
            if self._position_filter:
                scores = self._filter_by_position(scores)

            # Populate table
            self._populate_rankings_table(scores)
            self._update_summary(scores)

        except Exception as e:
            logger.error(f"[PopularityView] Error loading rankings: {e}")
            self.rankings_table.setRowCount(0)

    def _filter_by_position(self, scores: List) -> List:
        """
        Filter popularity scores by position.

        Args:
            scores: List of PopularityScore objects

        Returns:
            Filtered list
        """
        if not self._position_filter:
            return scores

        try:
            import sqlite3
            import json

            # Connect to game_cycle database for player positions
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            filtered = []
            for score in scores:
                # Get player positions
                cursor.execute(
                    "SELECT positions FROM players WHERE player_id = ? AND dynasty_id = ?",
                    (score.player_id, self._dynasty_id)
                )
                row = cursor.fetchone()
                if row and row[0]:  # positions at index 0
                    positions = json.loads(row[0])
                    if self._position_filter in positions:
                        filtered.append(score)

            conn.close()
            return filtered

        except Exception as e:
            logger.error(f"[PopularityView] Error filtering by position: {e}")
            return scores

    def _populate_rankings_table(self, scores: List):
        """Populate rankings table with popularity data."""
        self.rankings_table.setRowCount(len(scores))

        # Get player data for names/teams
        player_data = self._get_player_data([s.player_id for s in scores])

        for row, score in enumerate(scores):
            player = player_data.get(score.player_id, {})

            # Rank
            rank_item = NumericTableWidgetItem(row + 1, str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            if row == 0:
                rank_item.setFont(Typography.SMALL_BOLD)
                rank_item.setForeground(QColor("#FFD700"))  # Gold
            self.rankings_table.setItem(row, 0, rank_item)

            # Player name (store player_id for double-click)
            name = player.get("name", f"Player {score.player_id}")
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, score.player_id)
            name_item.setData(Qt.UserRole + 1, player)
            if row == 0:
                name_item.setFont(Typography.SMALL_BOLD)
            self.rankings_table.setItem(row, 1, name_item)

            # Position (abbreviated)
            position = player.get("position", "?")
            # Convert to abbreviation (e.g., "quarterback" → "QB", "running_back" → "RB")
            position_abbr = get_position_abbreviation(position) if position != "?" else "?"
            pos_item = QTableWidgetItem(position_abbr)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.rankings_table.setItem(row, 2, pos_item)

            # Team
            team_abbr = self._get_team_abbr(player.get("team_id", 0))
            team_item = QTableWidgetItem(team_abbr)
            team_item.setTextAlignment(Qt.AlignCenter)
            self.rankings_table.setItem(row, 3, team_item)

            # Popularity Score
            score_item = NumericTableWidgetItem(
                score.popularity_score,
                f"{score.popularity_score:.1f}"
            )
            score_item.setTextAlignment(Qt.AlignCenter)
            self._color_popularity_score(score_item, score.popularity_score)
            if row == 0:
                score_item.setFont(Typography.SMALL_BOLD)
            self.rankings_table.setItem(row, 4, score_item)

            # Tier (with color badge)
            tier_item = QTableWidgetItem(self._format_tier(score.tier))
            tier_item.setTextAlignment(Qt.AlignCenter)
            tier_item.setFont(Typography.SMALL_BOLD)
            self._color_tier_badge(tier_item, score.tier)
            self.rankings_table.setItem(row, 5, tier_item)

            # Trend (arrow + change)
            trend_item = QTableWidgetItem(
                self._format_trend(score.trend, score.week_change)
            )
            trend_item.setTextAlignment(Qt.AlignCenter)
            self._color_trend(trend_item, score.week_change)
            self.rankings_table.setItem(row, 6, trend_item)

            # Performance Score
            perf_item = NumericTableWidgetItem(
                score.performance_score,
                f"{score.performance_score:.0f}"
            )
            perf_item.setTextAlignment(Qt.AlignCenter)
            self.rankings_table.setItem(row, 7, perf_item)

            # Visibility Multiplier
            vis_item = NumericTableWidgetItem(
                score.visibility_multiplier,
                f"{score.visibility_multiplier:.2f}x"
            )
            vis_item.setTextAlignment(Qt.AlignCenter)
            self.rankings_table.setItem(row, 8, vis_item)

            # Market Multiplier
            mkt_item = NumericTableWidgetItem(
                score.market_multiplier,
                f"{score.market_multiplier:.2f}x"
            )
            mkt_item.setTextAlignment(Qt.AlignCenter)
            self.rankings_table.setItem(row, 9, mkt_item)

    def _get_player_data(self, player_ids: List[int]) -> Dict[int, Dict]:
        """
        Get player names, positions, and teams from game_cycle database.

        Args:
            player_ids: List of player IDs to fetch

        Returns:
            Dictionary mapping player_id to player data
        """
        if not player_ids:
            return {}

        try:
            import sqlite3
            import json

            # Connect to game_cycle database
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            placeholders = ",".join("?" * len(player_ids))
            cursor.execute(
                f"""SELECT player_id, first_name, last_name, positions, team_id
                    FROM players
                    WHERE player_id IN ({placeholders}) AND dynasty_id = ?""",
                (*player_ids, self._dynasty_id)
            )

            player_data = {}
            for row in cursor.fetchall():
                # Row indices: 0=player_id, 1=first_name, 2=last_name, 3=positions, 4=team_id
                positions = json.loads(row[3]) if row[3] else []
                player_data[row[0]] = {
                    'name': f"{row[1]} {row[2]}",  # first_name + last_name
                    'position': positions[0] if positions else "?",
                    'team_id': row[4]
                }

            conn.close()
            return player_data

        except Exception as e:
            logger.error(f"[PopularityView] Error fetching player data: {e}", exc_info=True)
            return {}

    def _update_summary(self, scores: List):
        """Update summary panel with aggregate stats."""
        if not scores:
            self.total_players_label.setText("0")
            self.avg_popularity_label.setText("0.0")
            self.top_player_label.setText("-")
            return

        self.total_players_label.setText(str(len(scores)))

        avg_pop = sum(s.popularity_score for s in scores) / len(scores)
        self.avg_popularity_label.setText(f"{avg_pop:.1f}")

        # Get top player name
        if scores:
            top_score = scores[0]
            player_data = self._get_player_data([top_score.player_id])
            top_name = player_data.get(top_score.player_id, {}).get("name", "Unknown")
            self.top_player_label.setText(top_name)

        self.week_label.setText(str(self._week))

    # === Helper Methods ===

    def _format_tier(self, tier: str) -> str:
        """Format tier for display."""
        tier_map = {
            "TRANSCENDENT": "TRANS",
            "STAR": "STAR",
            "KNOWN": "KNOWN",
            "ROLE_PLAYER": "ROLE",
            "UNKNOWN": "UNK"
        }
        return tier_map.get(tier, tier)

    def _color_tier_badge(self, item: QTableWidgetItem, tier: str):
        """Apply color to tier badge."""
        tier_colors = {
            "TRANSCENDENT": "#FFD700",  # Gold
            "STAR": "#C0C0C0",          # Silver
            "KNOWN": "#4CAF50",         # Green
            "ROLE_PLAYER": "#1976D2",   # Blue
            "UNKNOWN": "#666666"        # Gray
        }

        color = tier_colors.get(tier, "#666666")
        item.setForeground(QColor(color))

    def _format_trend(self, trend: str, week_change: Optional[float]) -> str:
        """Format trend arrow with change value."""
        if not week_change:
            return "→ 0.0"

        if week_change > 0:
            return f"↑ +{week_change:.1f}"
        elif week_change < 0:
            return f"↓ {week_change:.1f}"
        else:
            return f"→ 0.0"

    def _color_trend(self, item: QTableWidgetItem, week_change: Optional[float]):
        """Apply color to trend indicator."""
        if not week_change:
            item.setForeground(QColor("#666666"))
        elif week_change > 0:
            item.setForeground(QColor("#2E7D32"))  # Green
        elif week_change < 0:
            item.setForeground(QColor("#C62828"))  # Red
        else:
            item.setForeground(QColor("#666666"))  # Gray

    def _color_popularity_score(self, item: QTableWidgetItem, score: float):
        """Apply color coding to popularity score."""
        if score >= 90:
            item.setForeground(QColor("#FFD700"))  # Gold - Transcendent
        elif score >= 75:
            item.setForeground(QColor("#C0C0C0"))  # Silver - Star
        elif score >= 50:
            item.setForeground(QColor("#4CAF50"))  # Green - Known
        elif score >= 25:
            item.setForeground(QColor("#1976D2"))  # Blue - Role Player
        else:
            item.setForeground(QColor("#666666"))  # Gray - Unknown

    def _get_team_abbr(self, team_id: int) -> str:
        """Get team abbreviation from team ID."""
        try:
            from team_management.teams.team_loader import get_team_by_id
            team = get_team_by_id(team_id)
            return team.abbreviation if team else "FA"
        except Exception:
            return "FA" if team_id == 0 else f"T{team_id}"

    def _on_tier_changed(self, index: int):
        """Handle tier filter change."""
        if index >= 0:
            self._tier_filter = self.tier_combo.itemData(index)
            self.refresh_rankings()

    def _on_position_changed(self, index: int):
        """Handle position filter change."""
        if index >= 0:
            self._position_filter = self.position_combo.itemData(index)
            self.refresh_rankings()

    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        self.refresh_rankings()
        self.refresh_requested.emit()

    def _on_player_double_clicked(self, row: int, column: int):
        """Handle player double-click - open player detail dialog."""
        # Get player name from column 1
        name_item = self.rankings_table.item(row, 1)
        if not name_item:
            return

        player_id = name_item.data(Qt.UserRole)
        player_data = name_item.data(Qt.UserRole + 1)
        player_name = name_item.text()

        if not player_id or not player_data:
            return

        if not self._dynasty_id or not self._db_path:
            return

        # Get team name from team_id
        team_id = player_data.get("team_id", 0)
        team_name = ""
        if team_id:
            try:
                from team_management.teams.team_loader import get_team_by_id
                team = get_team_by_id(team_id)
                if team:
                    team_name = f"{team.city} {team.nickname}"
            except Exception:
                pass

        try:
            from game_cycle_ui.dialogs.player_detail_dialog import PlayerDetailDialog
            dialog = PlayerDetailDialog(
                player_id=player_id,
                player_name=player_name,
                player_data=player_data,
                dynasty_id=self._dynasty_id,
                season=self._season,
                db_path=self._db_path,
                team_name=team_name,
                parent=self
            )
            dialog.exec()
        except Exception as e:
            logger.error(f"[PopularityView] Error opening player detail: {e}")

    def clear(self):
        """Clear all data from the view."""
        self.total_players_label.setText("0")
        self.avg_popularity_label.setText("0.0")
        self.top_player_label.setText("-")
        self.week_label.setText("1")
        self.rankings_table.setRowCount(0)
