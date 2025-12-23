"""
Awards View - Displays season awards, All-Pro teams, Pro Bowl rosters, and statistical leaders.

Shows:
- Major Awards: MVP, OPOY, DPOY, OROY, DROY, CPOY with voting results
- All-Pro Teams: First Team (22) + Second Team (22) by position
- Pro Bowl: AFC and NFC rosters with starters/reserves
- Statistical Leaders: Top 10 in 15 categories

Part of Milestone 10: Awards System, Tollgate 6.
"""

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QComboBox, QTabWidget, QFrame, QScrollArea, QProgressBar,
    QSplitter, QButtonGroup, QRadioButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.theme import (
    TABLE_HEADER_STYLE, TAB_STYLE, PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE, DANGER_BUTTON_STYLE, WARNING_BUTTON_STYLE,
    NEUTRAL_BUTTON_STYLE, Typography, FontSizes, TextColors,
    apply_table_style
)
from game_cycle_ui.widgets import HOFBallotWidget, AwardsGridWidget
from game_cycle_ui.dialogs import HOFInducteeDialog

logger = logging.getLogger(__name__)


# ============================================
# Constants
# ============================================

AWARD_NAMES = {
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

# Position groupings for All-Pro display
OFFENSE_POSITIONS = ['QB', 'RB', 'FB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT']
DEFENSE_POSITIONS = ['EDGE', 'DT', 'LOLB', 'MLB', 'ROLB', 'CB', 'FS', 'SS']
SPECIAL_TEAMS_POSITIONS = ['K', 'P']

# Statistical categories
STAT_CATEGORIES = [
    ('passing_yards', 'Passing Yards'),
    ('passing_tds', 'Passing TDs'),
    ('passer_rating', 'Passer Rating'),
    ('rushing_yards', 'Rushing Yards'),
    ('rushing_tds', 'Rushing TDs'),
    ('receiving_yards', 'Receiving Yards'),
    ('receiving_tds', 'Receiving TDs'),
    ('receptions', 'Receptions'),
    ('sacks', 'Sacks'),
    ('interceptions', 'Interceptions'),
    ('tackles_total', 'Total Tackles'),
    ('forced_fumbles', 'Forced Fumbles'),
]


class AllProTableColumns:
    """Column indices for All-Pro tables."""
    POSITION = 0
    PLAYER = 1
    TEAM = 2
    GRADE = 3


class ProBowlTableColumns:
    """Column indices for Pro Bowl tables."""
    POSITION = 0
    PLAYER = 1
    TEAM = 2
    SELECTION_TYPE = 3
    SCORE = 4


class AwardsView(QWidget):
    """
    View for displaying season awards and voting results.

    Follows StatsView/AnalyticsView patterns - talks directly to AwardsService
    via set_context(). No separate controller needed.
    """

    # Signals
    refresh_requested = Signal()
    player_selected = Signal(int)  # player_id for navigation
    continue_to_next_stage = Signal()  # Emitted when user clicks Continue during offseason flow

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Dynasty context (set via set_context())
        self._season: int = 2025
        self._dynasty_id: str = ""
        self._db_path: str = ""

        # Offseason flow mode flag
        self._offseason_mode: bool = False

        # Cached data
        self._awards_data: Dict[str, Any] = {}
        self._all_pro_data: Optional[Any] = None
        self._pro_bowl_data: Optional[Any] = None
        self._stat_leaders_data: Optional[Any] = None

        # Build UI
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header with season selector and refresh
        self._create_header(layout)

        # Summary panel
        self._create_summary_panel(layout)

        # Main tabbed content
        self._create_tabs(layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create header with title, season selector, and refresh button."""
        header = QHBoxLayout()

        # Title
        title = QLabel("AWARDS & HONORS")
        title.setFont(Typography.H4)
        header.addWidget(title)

        header.addStretch()

        # Season selector
        season_label = QLabel("Season:")
        header.addWidget(season_label)

        self.season_combo = QComboBox()
        self.season_combo.setMinimumWidth(100)
        self.season_combo.currentIndexChanged.connect(self._on_season_changed)
        header.addWidget(self.season_combo)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.refresh_btn.clicked.connect(self.refresh_data)
        header.addWidget(self.refresh_btn)

        parent_layout.addLayout(header)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create summary panel showing award counts."""
        summary_group = QGroupBox("Summary")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(40)

        # Major Awards count
        self._create_stat_widget(summary_layout, "awards_count_label", "Major Awards", "0")

        # All-Pro selections
        self._create_stat_widget(summary_layout, "all_pro_count_label", "All-Pro", "0")

        # Pro Bowl selections
        self._create_stat_widget(summary_layout, "pro_bowl_count_label", "Pro Bowlers", "0")

        # Stat Leaders
        self._create_stat_widget(summary_layout, "stat_leaders_count_label", "Stat Leaders", "0")

        summary_layout.addStretch()
        parent_layout.addWidget(summary_group)

    def _create_stat_widget(self, parent_layout: QHBoxLayout, attr_name: str,
                            title: str, initial_value: str):
        """Create a single stat widget for the summary panel."""
        frame = QFrame()
        vlayout = QVBoxLayout(frame)
        vlayout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: #666; font-size: {FontSizes.CAPTION};")
        vlayout.addWidget(title_label)

        value_label = QLabel(initial_value)
        value_label.setFont(Typography.H4)
        vlayout.addWidget(value_label)

        setattr(self, attr_name, value_label)
        parent_layout.addWidget(frame)

    def _create_tabs(self, parent_layout: QVBoxLayout):
        """Create the main tabbed content area."""
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_STYLE)

        # Tab 1: Major Awards
        self._create_major_awards_tab()
        self.tabs.addTab(self.major_awards_tab, "Major Awards")

        # Tab 2: All-Pro Teams
        self._create_all_pro_tab()
        self.tabs.addTab(self.all_pro_tab, "All-Pro Teams")

        # Tab 3: Pro Bowl
        self._create_pro_bowl_tab()
        self.tabs.addTab(self.pro_bowl_tab, "Pro Bowl")

        # Tab 4: Statistical Leaders
        self._create_stat_leaders_tab()
        self.tabs.addTab(self.stat_leaders_tab, "Stat Leaders")

        # Tab 5: Award History (past seasons)
        self._create_award_history_tab()
        self.tabs.addTab(self.award_history_tab, "Award History")

        # Tab 6: Hall of Fame
        self._create_hall_of_fame_tab()
        self.tabs.addTab(self.hof_tab, "Hall of Fame")

        parent_layout.addWidget(self.tabs, stretch=1)

    # ============================================
    # Tab 1: Major Awards
    # ============================================

    def _create_major_awards_tab(self):
        """Create the Major Awards tab with compact 2x3 grid."""
        self.major_awards_tab = QWidget()

        tab_layout = QVBoxLayout(self.major_awards_tab)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(12)

        # Compact 2x3 grid widget
        self.awards_grid = AwardsGridWidget()
        self.awards_grid.player_selected.connect(self.player_selected.emit)
        self.awards_grid.award_clicked.connect(self._on_award_tile_clicked)
        tab_layout.addWidget(self.awards_grid)

        # Keep legacy dict for compatibility (but won't be used)
        self.award_widgets = {}

    def _on_award_tile_clicked(self, award_id: str):
        """Handle click on award tile - finalists popup is shown by the tile."""
        pass  # Popup is handled internally by AwardTileWidget

    # ============================================
    # Tab 2: All-Pro Teams
    # ============================================

    def _create_all_pro_tab(self):
        """Create the All-Pro Teams tab."""
        self.all_pro_tab = QWidget()
        layout = QHBoxLayout(self.all_pro_tab)

        # Two-column splitter
        splitter = QSplitter(Qt.Horizontal)

        # First Team
        first_team_widget = self._create_all_pro_team_widget("First Team All-Pro")
        self.first_team_table = first_team_widget.findChild(QTableWidget)
        splitter.addWidget(first_team_widget)

        # Second Team
        second_team_widget = self._create_all_pro_team_widget("Second Team All-Pro")
        self.second_team_table = second_team_widget.findChild(QTableWidget)
        splitter.addWidget(second_team_widget)

        splitter.setSizes([500, 500])
        layout.addWidget(splitter)

    def _create_all_pro_team_widget(self, title: str) -> QGroupBox:
        """Create a widget for one All-Pro team (First or Second)."""
        group = QGroupBox(title)
        layout = QVBoxLayout(group)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Position", "Player", "Team", "Grade"])

        # Apply centralized table styling
        apply_table_style(table)

        # Keep column resize mode settings
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        table.cellClicked.connect(
            lambda row, col, t=table: self._on_table_player_clicked(t, row)
        )

        layout.addWidget(table)
        return group

    # ============================================
    # Tab 3: Pro Bowl
    # ============================================

    def _create_pro_bowl_tab(self):
        """Create the Pro Bowl tab with AFC/NFC toggle."""
        self.pro_bowl_tab = QWidget()
        layout = QVBoxLayout(self.pro_bowl_tab)

        # Conference toggle
        toggle_layout = QHBoxLayout()
        toggle_layout.addStretch()

        self.conference_group = QButtonGroup(self)

        self.afc_radio = QRadioButton("AFC")
        self.afc_radio.setChecked(True)
        self.conference_group.addButton(self.afc_radio, 0)
        toggle_layout.addWidget(self.afc_radio)

        self.nfc_radio = QRadioButton("NFC")
        self.conference_group.addButton(self.nfc_radio, 1)
        toggle_layout.addWidget(self.nfc_radio)

        toggle_layout.addStretch()
        layout.addLayout(toggle_layout)

        self.conference_group.buttonClicked.connect(self._on_conference_changed)

        # Pro Bowl table
        self.pro_bowl_table = QTableWidget()
        self.pro_bowl_table.setColumnCount(5)
        self.pro_bowl_table.setHorizontalHeaderLabels(
            ["Position", "Player", "Team", "Type", "Score"]
        )

        # Apply centralized table styling
        apply_table_style(self.pro_bowl_table)

        # Keep column resize mode settings
        self.pro_bowl_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        self.pro_bowl_table.cellClicked.connect(
            lambda row, col: self._on_table_player_clicked(self.pro_bowl_table, row)
        )

        layout.addWidget(self.pro_bowl_table)

    # ============================================
    # Tab 4: Statistical Leaders
    # ============================================

    def _create_stat_leaders_tab(self):
        """Create the Statistical Leaders tab."""
        self.stat_leaders_tab = QWidget()
        layout = QVBoxLayout(self.stat_leaders_tab)

        # Category selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Category:"))

        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(200)
        for cat_id, cat_name in STAT_CATEGORIES:
            self.category_combo.addItem(cat_name, cat_id)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        selector_layout.addWidget(self.category_combo)

        selector_layout.addStretch()
        layout.addLayout(selector_layout)

        # Leaders table
        self.stat_leaders_table = QTableWidget()
        self.stat_leaders_table.setColumnCount(5)
        self.stat_leaders_table.setHorizontalHeaderLabels(
            ["Rank", "Player", "Team", "Position", "Value"]
        )

        # Apply centralized table styling
        apply_table_style(self.stat_leaders_table)

        # Keep column resize mode settings
        self.stat_leaders_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        self.stat_leaders_table.cellClicked.connect(
            lambda row, col: self._on_table_player_clicked(self.stat_leaders_table, row)
        )

        layout.addWidget(self.stat_leaders_table)

    # ============================================
    # Tab 5: Award History (Past Seasons)
    # ============================================

    def _create_award_history_tab(self):
        """Create the Award History tab showing past seasons' award winners."""
        self.award_history_tab = QWidget()
        layout = QVBoxLayout(self.award_history_tab)

        # Season selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Season:"))

        self.history_season_combo = QComboBox()
        self.history_season_combo.setMinimumWidth(100)
        self.history_season_combo.currentIndexChanged.connect(self._on_history_season_changed)
        selector_layout.addWidget(self.history_season_combo)

        selector_layout.addStretch()
        layout.addLayout(selector_layout)

        # Award History table
        self.award_history_table = QTableWidget()
        self.award_history_table.setColumnCount(5)
        self.award_history_table.setHorizontalHeaderLabels(
            ["Award", "Winner", "Position", "Team", "Vote %"]
        )

        # Apply centralized table styling
        apply_table_style(self.award_history_table)

        # Column sizing
        self.award_history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.award_history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.award_history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.award_history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.award_history_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.award_history_table.cellClicked.connect(
            lambda row, col: self._on_table_player_clicked(self.award_history_table, row)
        )

        layout.addWidget(self.award_history_table)

        # Status label
        self.award_history_status = QLabel("")
        self.award_history_status.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED}; margin-top: 8px;")
        layout.addWidget(self.award_history_status)

    def _on_history_season_changed(self):
        """Handle season change in Award History tab."""
        self._populate_award_history()

    def _populate_award_history(self):
        """Populate Award History table with past award winners."""
        if not self._dynasty_id or not self._db_path:
            self.award_history_status.setText("No dynasty context")
            return

        selected_season = self.history_season_combo.currentData()
        if not selected_season:
            return

        try:
            import sqlite3

            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Query award winners for selected season
            cursor.execute("""
                SELECT aw.award_id, aw.player_id, aw.team_id, aw.vote_share,
                       p.first_name, p.last_name, p.positions
                FROM award_winners aw
                LEFT JOIN players p ON aw.player_id = p.player_id AND aw.dynasty_id = p.dynasty_id
                WHERE aw.dynasty_id = ? AND aw.season = ? AND aw.is_winner = 1
                ORDER BY CASE aw.award_id
                    WHEN 'mvp' THEN 1 WHEN 'opoy' THEN 2 WHEN 'dpoy' THEN 3
                    WHEN 'oroy' THEN 4 WHEN 'droy' THEN 5 WHEN 'cpoy' THEN 6
                    ELSE 7
                END
            """, (self._dynasty_id, selected_season))

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                self.award_history_table.setRowCount(0)
                self.award_history_status.setText(f"No awards recorded for {selected_season} season")
                return

            self.award_history_table.setRowCount(len(rows))

            import json

            for row_idx, (award_id, player_id, team_id, vote_share, first_name, last_name, positions_json) in enumerate(rows):
                # Award name with icon
                icon = AWARD_ICONS.get(award_id, '')
                name = AWARD_NAMES.get(award_id, award_id.upper())
                award_item = QTableWidgetItem(f"{icon} {name}")
                award_item.setFont(Typography.SMALL_BOLD)
                self.award_history_table.setItem(row_idx, 0, award_item)

                # Winner name
                player_name = f"{first_name or ''} {last_name or ''}".strip() or f"Player {player_id}"
                name_item = QTableWidgetItem(player_name)
                name_item.setData(Qt.UserRole, player_id)
                self.award_history_table.setItem(row_idx, 1, name_item)

                # Position (parse JSON positions list, get first)
                position = ""
                if positions_json:
                    try:
                        positions_list = json.loads(positions_json)
                        position = positions_list[0] if positions_list else ""
                    except (json.JSONDecodeError, IndexError):
                        position = ""
                pos_item = QTableWidgetItem(position)
                pos_item.setTextAlignment(Qt.AlignCenter)
                self.award_history_table.setItem(row_idx, 2, pos_item)

                # Team
                team_item = QTableWidgetItem(self._get_team_abbrev(team_id))
                team_item.setTextAlignment(Qt.AlignCenter)
                self.award_history_table.setItem(row_idx, 3, team_item)

                # Vote percentage
                vote_pct = (vote_share or 0) * 100
                vote_item = QTableWidgetItem(f"{vote_pct:.1f}%")
                vote_item.setTextAlignment(Qt.AlignCenter)
                self._color_grade(vote_item, vote_pct)
                self.award_history_table.setItem(row_idx, 4, vote_item)

            self.award_history_status.setText(f"{len(rows)} awards for {selected_season} season")

        except Exception as e:
            logger.error(f"Error loading award history: {e}")
            self.award_history_table.setRowCount(0)
            self.award_history_status.setText(f"Error loading data: {e}")

    def _populate_history_season_combo(self):
        """Populate the season dropdown for Award History tab."""
        if not self._dynasty_id or not self._db_path:
            return

        try:
            import sqlite3

            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Get all seasons with award winners
            cursor.execute("""
                SELECT DISTINCT season FROM award_winners
                WHERE dynasty_id = ? AND is_winner = 1
                ORDER BY season DESC
            """, (self._dynasty_id,))

            seasons = [row[0] for row in cursor.fetchall()]
            conn.close()

            # Update combo if seasons changed
            current_seasons = [self.history_season_combo.itemData(i)
                               for i in range(self.history_season_combo.count())]

            if seasons != current_seasons:
                self.history_season_combo.blockSignals(True)
                self.history_season_combo.clear()

                for season in seasons:
                    self.history_season_combo.addItem(str(season), season)

                # If no seasons with awards, add current season as placeholder
                if not seasons and self._season:
                    self.history_season_combo.addItem(str(self._season), self._season)

                self.history_season_combo.blockSignals(False)

        except Exception as e:
            logger.error(f"Error populating history season combo: {e}")

    # ============================================
    # Tab 6: Hall of Fame
    # ============================================

    def _create_hall_of_fame_tab(self):
        """Create the Hall of Fame tab showing voting results."""
        self.hof_tab = QWidget()
        layout = QVBoxLayout(self.hof_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        # HOF Ballot Widget (will be created when context is set)
        self.hof_ballot_widget = None

        # Placeholder message (shown until widget is created with context)
        self.hof_placeholder = QLabel("Loading Hall of Fame ballot...")
        self.hof_placeholder.setAlignment(Qt.AlignCenter)
        self.hof_placeholder.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED}; padding: 40px;")
        layout.addWidget(self.hof_placeholder)

    def _populate_hof_ballot(self):
        """Populate Hall of Fame ballot with voting results."""
        if not self._dynasty_id or not self._db_path:
            if self.hof_placeholder:
                self.hof_placeholder.setText("No dynasty context")
            return

        try:
            # Create HOF widget if it doesn't exist yet
            if not self.hof_ballot_widget:
                self.hof_ballot_widget = HOFBallotWidget(
                    self._db_path,
                    self._dynasty_id,
                    self._season,
                    parent=self.hof_tab
                )

                # Connect signals
                self.hof_ballot_widget.player_clicked.connect(
                    lambda player_id, name: self.player_selected.emit(player_id)
                )
                self.hof_ballot_widget.celebration_requested.connect(
                    self._show_hof_celebration
                )

                # Replace placeholder with widget
                layout = self.hof_tab.layout()
                if self.hof_placeholder:
                    layout.removeWidget(self.hof_placeholder)
                    self.hof_placeholder.deleteLater()
                    self.hof_placeholder = None

                layout.addWidget(self.hof_ballot_widget)

            # Load voting results for current season
            self.hof_ballot_widget.load_voting_results()

        except Exception as e:
            logger.error(f"Error loading HOF ballot: {e}")
            if self.hof_placeholder:
                self.hof_placeholder.setText(f"Error loading HOF ballot: {e}")

    def _show_hof_celebration(self, inductees: List[Dict]):
        """Show celebration dialog for HOF inductees."""
        if not inductees:
            return

        try:
            dialog = HOFInducteeDialog(inductees, self._season, parent=self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error showing HOF celebration dialog: {e}")

    # ============================================
    # Context and Data Loading
    # ============================================

    def set_context(self, dynasty_id: str, db_path: str, season: int):
        """
        Set dynasty context for data operations.

        Called by main window during initialization.

        Args:
            dynasty_id: Dynasty identifier
            db_path: Path to game_cycle.db
            season: Current season year
        """
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season

        # Populate season combo
        self._populate_season_combo()

        # Load initial data
        self.refresh_data()

    def _populate_season_combo(self):
        """Populate the season dropdown with available seasons."""
        self.season_combo.blockSignals(True)
        self.season_combo.clear()

        # Add current and past seasons (last 10 years)
        for year in range(self._season, max(2020, self._season - 10), -1):
            self.season_combo.addItem(str(year), year)

        self.season_combo.blockSignals(False)

    def _on_season_changed(self, index: int):
        """Handle season selection change."""
        if index >= 0:
            self._season = self.season_combo.itemData(index)
            self.refresh_data()

    def refresh_data(self):
        """Refresh all awards data from database."""
        if not self._dynasty_id or not self._db_path:
            return

        try:
            from game_cycle.services.awards_service import AwardsService

            service = AwardsService(self._db_path, self._dynasty_id, self._season)

            # Check if awards exist for this season
            if not service.awards_already_calculated():
                self._show_no_awards_state()
                # Still populate Award History - shows past seasons
                self._populate_history_season_combo()
                self._populate_award_history()
                return

            # Load award data from DATABASE (fast, no recalculation)
            # Use get_* methods to avoid expensive re-computation
            self._awards_data = service.get_calculated_awards()
            self._all_pro_data = service.get_all_pro_teams()
            self._pro_bowl_data = service.get_pro_bowl_rosters()
            self._stat_leaders_data = service.get_statistical_leaders()

            # Populate UI
            self._populate_major_awards()
            self._populate_all_pro()
            self._populate_pro_bowl()
            self._populate_stat_leaders()
            self._populate_history_season_combo()
            self._populate_award_history()  # Past seasons' awards
            self._populate_hof_ballot()  # Hall of Fame voting results
            self._update_summary()

            # Note: Do NOT emit refresh_requested here - it causes infinite recursion
            # when main_window's handler calls refresh_data() again.
            # Signal should only be emitted from user-initiated actions (button clicks).

        except ImportError as e:
            logger.warning(f"[AwardsView] AwardsService not available: {e}")
            self._show_no_awards_state()
        except Exception as e:
            logger.error(f"[AwardsView] Error loading awards: {e}")
            self._show_no_awards_state()

    def _show_no_awards_state(self):
        """Show empty state when no awards calculated."""
        # Clear summary
        self.awards_count_label.setText("0")
        self.all_pro_count_label.setText("0")
        self.pro_bowl_count_label.setText("0")
        self.stat_leaders_count_label.setText("0")

        # Clear the compact awards grid
        if hasattr(self, 'awards_grid'):
            self.awards_grid.clear()

        # Clear other tables
        self.first_team_table.setRowCount(0)
        self.second_team_table.setRowCount(0)
        self.pro_bowl_table.setRowCount(0)
        self.stat_leaders_table.setRowCount(0)

        # Note: Award History table is NOT cleared here - it can still show past seasons

    def _update_summary(self):
        """Update summary panel counts."""
        # Count awards with winners
        awards_count = sum(1 for r in self._awards_data.values() if r.has_winner)
        self.awards_count_label.setText(str(awards_count))

        # All-Pro count
        if self._all_pro_data:
            self.all_pro_count_label.setText(str(self._all_pro_data.total_selections))

        # Pro Bowl count
        if self._pro_bowl_data:
            self.pro_bowl_count_label.setText(str(self._pro_bowl_data.total_selections))

        # Stat leaders count
        if self._stat_leaders_data:
            self.stat_leaders_count_label.setText(str(self._stat_leaders_data.total_recorded))

    # ============================================
    # Population Methods
    # ============================================

    def _populate_major_awards(self):
        """Populate the compact awards grid with data."""
        if hasattr(self, 'awards_grid') and self._awards_data:
            self.awards_grid.set_awards_data(self._awards_data, self._get_team_abbrev)

    def _populate_all_pro(self):
        """Populate All-Pro team tables."""
        if not self._all_pro_data:
            return

        # Populate First Team
        self._populate_all_pro_table(
            self.first_team_table,
            self._all_pro_data.first_team
        )

        # Populate Second Team
        self._populate_all_pro_table(
            self.second_team_table,
            self._all_pro_data.second_team
        )

    def _populate_all_pro_table(self, table: QTableWidget, team_data: Dict):
        """Populate a single All-Pro team table."""
        rows = []

        # Add in position order
        for position in OFFENSE_POSITIONS + DEFENSE_POSITIONS + SPECIAL_TEAMS_POSITIONS:
            players = team_data.get(position, [])
            for player in players:
                rows.append((position, player))

        table.setRowCount(len(rows))

        for row, (position, player) in enumerate(rows):
            # Position
            pos_item = QTableWidgetItem(position)
            pos_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0, pos_item)

            # Player name
            name_item = QTableWidgetItem(player.player_name)
            name_item.setData(Qt.UserRole, player.player_id)
            table.setItem(row, 1, name_item)

            # Team
            team_item = QTableWidgetItem(self._get_team_abbrev(player.team_id))
            team_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 2, team_item)

            # Grade
            grade_item = QTableWidgetItem(f"{player.overall_grade:.1f}")
            grade_item.setTextAlignment(Qt.AlignCenter)
            self._color_grade(grade_item, player.overall_grade)
            table.setItem(row, 3, grade_item)

    def _populate_pro_bowl(self):
        """Populate Pro Bowl table for selected conference."""
        if not self._pro_bowl_data:
            return

        is_afc = self.afc_radio.isChecked()
        roster = (self._pro_bowl_data.afc_roster if is_afc
                  else self._pro_bowl_data.nfc_roster)

        rows = []
        for position in OFFENSE_POSITIONS + DEFENSE_POSITIONS + SPECIAL_TEAMS_POSITIONS:
            players = roster.get(position, [])
            # Sort: STARTER first, then by combined_score descending
            players_sorted = sorted(
                players,
                key=lambda p: (0 if p.selection_type == 'STARTER' else 1, -p.combined_score)
            )
            for player in players_sorted:
                rows.append((position, player))

        self.pro_bowl_table.setRowCount(len(rows))

        for row, (position, player) in enumerate(rows):
            # Position
            pos_item = QTableWidgetItem(position)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.pro_bowl_table.setItem(row, 0, pos_item)

            # Player name
            name_item = QTableWidgetItem(player.player_name)
            name_item.setData(Qt.UserRole, player.player_id)
            self.pro_bowl_table.setItem(row, 1, name_item)

            # Team
            team_item = QTableWidgetItem(self._get_team_abbrev(player.team_id))
            team_item.setTextAlignment(Qt.AlignCenter)
            self.pro_bowl_table.setItem(row, 2, team_item)

            # Selection type (STARTER, RESERVE, ALTERNATE)
            type_item = QTableWidgetItem(player.selection_type)
            type_item.setTextAlignment(Qt.AlignCenter)
            if player.selection_type == 'STARTER':
                type_item.setFont(Typography.SMALL_BOLD)
                type_item.setForeground(QColor("#2E7D32"))
            self.pro_bowl_table.setItem(row, 3, type_item)

            # Score (Pro Bowl combined score, not PFF grade)
            score_item = QTableWidgetItem(f"{player.combined_score:.1f}")
            score_item.setTextAlignment(Qt.AlignCenter)
            self._color_grade(score_item, player.combined_score)
            self.pro_bowl_table.setItem(row, 4, score_item)

    def _on_conference_changed(self):
        """Handle conference toggle."""
        self._populate_pro_bowl()

    def _populate_stat_leaders(self):
        """Populate statistical leaders for selected category."""
        if not self._stat_leaders_data:
            return

        category = self.category_combo.currentData()
        leaders = self._stat_leaders_data.get_category_top_10(category)

        self.stat_leaders_table.setRowCount(len(leaders))

        for row, leader in enumerate(leaders):
            # Rank
            rank_item = QTableWidgetItem(str(leader.league_rank))
            rank_item.setTextAlignment(Qt.AlignCenter)
            if leader.league_rank == 1:
                rank_item.setFont(Typography.SMALL_BOLD)
            self.stat_leaders_table.setItem(row, 0, rank_item)

            # Player name
            name_item = QTableWidgetItem(leader.player_name)
            name_item.setData(Qt.UserRole, leader.player_id)
            if leader.league_rank == 1:
                name_item.setFont(Typography.SMALL_BOLD)
            self.stat_leaders_table.setItem(row, 1, name_item)

            # Team
            team_item = QTableWidgetItem(self._get_team_abbrev(leader.team_id))
            team_item.setTextAlignment(Qt.AlignCenter)
            self.stat_leaders_table.setItem(row, 2, team_item)

            # Position
            pos_item = QTableWidgetItem(leader.position)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.stat_leaders_table.setItem(row, 3, pos_item)

            # Value (formatted based on category)
            value_str = self._format_stat_value(category, leader.stat_value)
            value_item = QTableWidgetItem(value_str)
            value_item.setTextAlignment(Qt.AlignCenter)
            if leader.league_rank == 1:
                value_item.setFont(Typography.SMALL_BOLD)
                value_item.setForeground(QColor("#2E7D32"))
            self.stat_leaders_table.setItem(row, 4, value_item)

    def _on_category_changed(self):
        """Handle category dropdown change."""
        self._populate_stat_leaders()

    # ============================================
    # Helper Methods
    # ============================================

    def _add_table_item(self, table: QTableWidget, row: int, col: int,
                       text: str, align_center: bool = False) -> QTableWidgetItem:
        """Helper to create and add a table item with optional centering."""
        item = QTableWidgetItem(str(text))
        if align_center:
            item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, col, item)
        return item

    def _color_grade_item(self, item: QTableWidgetItem, grade: float) -> None:
        """Apply grade-based color to a table item."""
        from game_cycle_ui.theme import GRADE_TIER_COLORS

        if grade >= 90:
            color = GRADE_TIER_COLORS["elite"]
        elif grade >= 80:
            color = GRADE_TIER_COLORS["excellent"]
        elif grade >= 70:
            color = GRADE_TIER_COLORS["good"]
        elif grade >= 60:
            color = GRADE_TIER_COLORS["average"]
        else:
            color = GRADE_TIER_COLORS["below_average"]

        item.setForeground(QColor(color))

    def _on_table_player_clicked(self, table: QTableWidget, row: int):
        """Handle click on a player in any table."""
        # Get player_id from the name column (usually column 1)
        name_col = 1
        item = table.item(row, name_col)
        if item:
            player_id = item.data(Qt.UserRole)
            if player_id:
                self.player_selected.emit(player_id)

    def _get_team_name(self, team_id: int) -> str:
        """Get full team name from ID."""
        try:
            from team_management.teams.team_loader import get_team_by_id
            team = get_team_by_id(team_id)
            return team.name if team else f'Team {team_id}'
        except Exception:
            return f'Team {team_id}'

    def _get_team_abbrev(self, team_id: int) -> str:
        """Get team abbreviation from ID."""
        try:
            from team_management.teams.team_loader import get_team_by_id
            team = get_team_by_id(team_id)
            return team.abbreviation if team else '???'
        except Exception:
            return '???'

    def _color_grade(self, item: QTableWidgetItem, grade: float):
        """Apply color coding to grade value."""
        if grade >= 90:
            item.setForeground(QColor("#2E7D32"))  # Dark green - Elite
        elif grade >= 80:
            item.setForeground(QColor("#4CAF50"))  # Green - Excellent
        elif grade >= 70:
            item.setForeground(QColor("#1976D2"))  # Blue - Good
        elif grade >= 60:
            item.setForeground(QColor("#FF9800"))  # Orange - Average
        else:
            item.setForeground(QColor("#f44336"))  # Red - Below average

    def _format_stat_value(self, category: str, value: float) -> str:
        """Format stat value based on category."""
        if category == 'passer_rating':
            return f"{value:.1f}"
        elif category in ('sacks', 'interceptions', 'forced_fumbles'):
            return f"{value:.1f}" if value != int(value) else str(int(value))
        else:
            return f"{int(value):,}"

    # ============================================
    # Offseason Flow Support
    # ============================================

    def set_offseason_mode(self, enabled: bool):
        """
        Enable/disable offseason mode which shows the Continue button.

        When viewing awards during the OFFSEASON_HONORS stage flow, this button
        allows the user to continue to the next offseason stage (Franchise Tag)
        after reviewing the awards.

        Args:
            enabled: True to show Continue button, False to hide it
        """
        self._offseason_mode = enabled

        # Create continue button if it doesn't exist yet
        if not hasattr(self, 'continue_btn'):
            self._create_continue_button()

        self.continue_btn.setVisible(enabled)

    def _create_continue_button(self):
        """Create the Continue to Franchise Tag button for offseason flow."""
        # Create a container for the button at the bottom of the view
        self.continue_btn = QPushButton("Continue to Franchise Tag")
        self.continue_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.continue_btn.setMinimumHeight(50)
        self.continue_btn.setVisible(False)  # Hidden by default
        self.continue_btn.clicked.connect(self._on_continue_clicked)

        # Add to main layout (at the bottom)
        self.layout().addWidget(self.continue_btn)

    def _on_continue_clicked(self):
        """Handle Continue button click - advance to next offseason stage."""
        self._offseason_mode = False
        self.continue_btn.setVisible(False)
        self.continue_to_next_stage.emit()
