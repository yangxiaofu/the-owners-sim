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

from game_cycle_ui.theme import TABLE_HEADER_STYLE

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
        title.setFont(QFont("Arial", 16, QFont.Bold))
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
        self.refresh_btn.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; "
            "border-radius: 4px; padding: 6px 16px; }"
            "QPushButton:hover { background-color: #1565C0; }"
        )
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
        title_label.setStyleSheet("color: #666; font-size: 11px;")
        vlayout.addWidget(title_label)

        value_label = QLabel(initial_value)
        value_label.setFont(QFont("Arial", 16, QFont.Bold))
        vlayout.addWidget(value_label)

        setattr(self, attr_name, value_label)
        parent_layout.addWidget(frame)

    def _create_tabs(self, parent_layout: QVBoxLayout):
        """Create the main tabbed content area."""
        self.tabs = QTabWidget()

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

        # Tab 5: Award Race (mid-season tracking)
        self._create_award_race_tab()
        self.tabs.addTab(self.award_race_tab, "Award Race")

        parent_layout.addWidget(self.tabs, stretch=1)

    # ============================================
    # Tab 1: Major Awards
    # ============================================

    def _create_major_awards_tab(self):
        """Create the Major Awards tab with all 6 awards."""
        self.major_awards_tab = QWidget()

        # Use scroll area for many awards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)

        # Create a group box for each award
        self.award_widgets = {}
        for award_id in ['mvp', 'opoy', 'dpoy', 'oroy', 'droy', 'cpoy']:
            award_widget = self._create_award_widget(award_id)
            self.award_widgets[award_id] = award_widget
            layout.addWidget(award_widget)

        layout.addStretch()
        scroll.setWidget(content)

        tab_layout = QVBoxLayout(self.major_awards_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

    def _create_award_widget(self, award_id: str) -> QGroupBox:
        """Create a widget for displaying a single award."""
        icon = AWARD_ICONS.get(award_id, '')
        name = AWARD_NAMES.get(award_id, award_id.upper())

        group = QGroupBox(f"{icon} {name}")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #ffffff;
                background-color: #263238;
                border: 1px solid #37474f;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Winner section - use dark background for better readability
        winner_frame = QFrame()
        winner_frame.setStyleSheet("background-color: #1e3a5f; border-radius: 4px; padding: 8px;")
        winner_layout = QVBoxLayout(winner_frame)
        winner_layout.setContentsMargins(12, 12, 12, 12)

        # Winner name - white text on dark background
        winner_name = QLabel("No winner yet")
        winner_name.setObjectName(f"{award_id}_winner_name")
        winner_name.setFont(QFont("Arial", 14, QFont.Bold))
        winner_name.setStyleSheet("color: #ffffff;")
        winner_name.setCursor(Qt.PointingHandCursor)
        winner_layout.addWidget(winner_name)

        # Winner details (team, position) - light gray text
        winner_details = QLabel("")
        winner_details.setObjectName(f"{award_id}_winner_details")
        winner_details.setStyleSheet("color: #b0bec5;")
        winner_layout.addWidget(winner_details)

        # Vote share progress bar - styled for dark background
        vote_share_layout = QHBoxLayout()
        vote_share_label = QLabel("Vote Share:")
        vote_share_label.setStyleSheet("color: #b0bec5;")
        vote_share_layout.addWidget(vote_share_label)

        vote_progress = QProgressBar()
        vote_progress.setObjectName(f"{award_id}_vote_progress")
        vote_progress.setRange(0, 100)
        vote_progress.setValue(0)
        vote_progress.setTextVisible(False)
        vote_progress.setFixedHeight(16)
        vote_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2c5282;
                border-radius: 3px;
                background: #0d2137;
            }
            QProgressBar::chunk {
                background: #4CAF50;
                border-radius: 2px;
            }
        """)
        vote_share_layout.addWidget(vote_progress, stretch=1)

        vote_percent = QLabel("0%")
        vote_percent.setObjectName(f"{award_id}_vote_percent")
        vote_percent.setStyleSheet("color: #ffffff; font-weight: bold;")
        vote_percent.setMinimumWidth(80)
        vote_share_layout.addWidget(vote_percent)

        winner_layout.addLayout(vote_share_layout)
        layout.addWidget(winner_frame)

        # Finalists section - 2x2 card grid
        finalists_label = QLabel("Finalists:")
        finalists_label.setStyleSheet("font-weight: bold; margin-top: 8px; color: #ffffff;")
        layout.addWidget(finalists_label)

        finalists_grid = QWidget()
        finalists_grid.setObjectName(f"{award_id}_finalists_grid")
        grid_layout = QGridLayout(finalists_grid)
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # Create 4 finalist card placeholders (2x2 grid)
        for i in range(4):
            card = self._create_finalist_card(award_id, i)
            row, col = divmod(i, 2)
            grid_layout.addWidget(card, row, col)

        layout.addWidget(finalists_grid)

        return group

    def _create_finalist_card(self, award_id: str, index: int) -> QFrame:
        """Create a compact finalist card for the 2x2 grid."""
        card = QFrame()
        card.setObjectName(f"{award_id}_finalist_card_{index}")
        card.setStyleSheet("""
            QFrame {
                background-color: #2a3441;
                border: 1px solid #3a4451;
                border-radius: 6px;
            }
            QFrame:hover {
                background-color: #3a4451;
                border-color: #4a5461;
            }
        """)
        card.setFixedHeight(50)
        card.setCursor(Qt.PointingHandCursor)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 4, 8, 4)
        card_layout.setSpacing(2)

        # Line 1: Rank + Name (e.g., "#2 Nick Chubb")
        name_label = QLabel()
        name_label.setObjectName(f"{award_id}_finalist_name_{index}")
        name_label.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 11px;")
        card_layout.addWidget(name_label)

        # Line 2: Position - Team · Vote% (e.g., "RB - CLE · 26.0%")
        details_label = QLabel()
        details_label.setObjectName(f"{award_id}_finalist_details_{index}")
        details_label.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        card_layout.addWidget(details_label)

        # Connect click handler
        card.mousePressEvent = lambda e, c=card: self._on_finalist_card_clicked(c)

        return card

    def _on_finalist_card_clicked(self, card: QFrame):
        """Handle click on finalist card - show player details."""
        player_id = card.property("player_id")
        if player_id:
            self._show_player_dialog(player_id)

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
        table.horizontalHeader().setStyleSheet(TABLE_HEADER_STYLE)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
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
        self.pro_bowl_table.horizontalHeader().setStyleSheet(TABLE_HEADER_STYLE)
        self.pro_bowl_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.pro_bowl_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.pro_bowl_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pro_bowl_table.setAlternatingRowColors(True)
        self.pro_bowl_table.verticalHeader().setVisible(False)
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
        self.stat_leaders_table.horizontalHeader().setStyleSheet(TABLE_HEADER_STYLE)
        self.stat_leaders_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.stat_leaders_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stat_leaders_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stat_leaders_table.setAlternatingRowColors(True)
        self.stat_leaders_table.verticalHeader().setVisible(False)
        self.stat_leaders_table.cellClicked.connect(
            lambda row, col: self._on_table_player_clicked(self.stat_leaders_table, row)
        )

        layout.addWidget(self.stat_leaders_table)

    # ============================================
    # Tab 5: Award Race (Mid-Season Tracking)
    # ============================================

    def _create_award_race_tab(self):
        """Create the Award Race tab showing mid-season tracking."""
        self.award_race_tab = QWidget()
        layout = QVBoxLayout(self.award_race_tab)

        # Header with explanation
        header_label = QLabel(
            "Award Race shows current leaders based on weekly tracking (Weeks 10-18). "
            "These are not final awards - see Major Awards for end-of-season results."
        )
        header_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 8px;")
        header_label.setWordWrap(True)
        layout.addWidget(header_label)

        # Award type selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Award:"))

        self.award_race_combo = QComboBox()
        self.award_race_combo.setMinimumWidth(250)
        for award_id in ['mvp', 'opoy', 'dpoy', 'oroy', 'droy']:
            name = AWARD_NAMES.get(award_id, award_id.upper())
            icon = AWARD_ICONS.get(award_id, '')
            self.award_race_combo.addItem(f"{icon} {name}", award_id)
        self.award_race_combo.currentIndexChanged.connect(self._on_award_race_type_changed)
        selector_layout.addWidget(self.award_race_combo)

        selector_layout.addStretch()
        layout.addLayout(selector_layout)

        # Award Race table
        self.award_race_table = QTableWidget()
        self.award_race_table.setColumnCount(6)
        self.award_race_table.setHorizontalHeaderLabels(
            ["Rank", "Player", "Team", "Position", "Score", "Trend"]
        )
        self.award_race_table.horizontalHeader().setStyleSheet(TABLE_HEADER_STYLE)
        self.award_race_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.award_race_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.award_race_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.award_race_table.setAlternatingRowColors(True)
        self.award_race_table.verticalHeader().setVisible(False)
        self.award_race_table.cellClicked.connect(
            lambda row, col: self._on_table_player_clicked(self.award_race_table, row)
        )

        layout.addWidget(self.award_race_table)

        # Status label
        self.award_race_status = QLabel("")
        self.award_race_status.setStyleSheet("color: #888; margin-top: 8px;")
        layout.addWidget(self.award_race_status)

    def _on_award_race_type_changed(self):
        """Handle award type change in Award Race tab."""
        self._populate_award_race()

    def _populate_award_race(self):
        """Populate Award Race table with tracking data."""
        if not self._dynasty_id or not self._db_path:
            self.award_race_status.setText("No dynasty context")
            return

        award_type = self.award_race_combo.currentData()
        if not award_type:
            return

        try:
            from game_cycle.services.awards.award_race_tracker import AwardRaceTracker
            from game_cycle.services.awards.models import AwardType

            # Map string to AwardType enum
            award_type_enum = {
                'mvp': AwardType.MVP,
                'opoy': AwardType.OPOY,
                'dpoy': AwardType.DPOY,
                'oroy': AwardType.OROY,
                'droy': AwardType.DROY,
            }.get(award_type)

            if not award_type_enum:
                return

            tracker = AwardRaceTracker(self._db_path, self._dynasty_id, self._season)
            standings = tracker.get_current_standings(award_type_enum)

            if not standings:
                self.award_race_table.setRowCount(0)
                self.award_race_status.setText(
                    "No tracking data yet. Award race tracking begins at Week 10."
                )
                return

            self.award_race_table.setRowCount(len(standings))

            for row, entry in enumerate(standings):
                # Rank
                rank_item = QTableWidgetItem(str(entry.get('rank', row + 1)))
                rank_item.setTextAlignment(Qt.AlignCenter)
                if row < 3:
                    rank_item.setFont(QFont("Arial", 10, QFont.Bold))
                self.award_race_table.setItem(row, 0, rank_item)

                # Player name
                name = f"{entry.get('first_name', '')} {entry.get('last_name', '')}".strip()
                name_item = QTableWidgetItem(name or f"Player {entry.get('player_id', '?')}")
                name_item.setData(Qt.UserRole, entry.get('player_id'))
                if row < 3:
                    name_item.setFont(QFont("Arial", 10, QFont.Bold))
                self.award_race_table.setItem(row, 1, name_item)

                # Team
                team_item = QTableWidgetItem(self._get_team_abbrev(entry.get('team_id', 0)))
                team_item.setTextAlignment(Qt.AlignCenter)
                self.award_race_table.setItem(row, 2, team_item)

                # Position
                pos_item = QTableWidgetItem(entry.get('position', ''))
                pos_item.setTextAlignment(Qt.AlignCenter)
                self.award_race_table.setItem(row, 3, pos_item)

                # Score
                score = entry.get('cumulative_score', 0)
                score_item = QTableWidgetItem(f"{score:.1f}")
                score_item.setTextAlignment(Qt.AlignCenter)
                self._color_grade(score_item, score)
                self.award_race_table.setItem(row, 4, score_item)

                # Trend indicator (compare week_score to cumulative)
                week_score = entry.get('week_score', 0)
                if week_score and score:
                    if week_score > score * 1.1:
                        trend = "\u2191"  # Up arrow (hot)
                        trend_color = "#4CAF50"
                    elif week_score < score * 0.9:
                        trend = "\u2193"  # Down arrow (cooling)
                        trend_color = "#f44336"
                    else:
                        trend = "\u2194"  # Steady
                        trend_color = "#888"
                else:
                    trend = "-"
                    trend_color = "#888"

                trend_item = QTableWidgetItem(trend)
                trend_item.setTextAlignment(Qt.AlignCenter)
                trend_item.setForeground(QColor(trend_color))
                self.award_race_table.setItem(row, 5, trend_item)

            # Update status
            week = standings[0].get('week', 0) if standings else 0
            self.award_race_status.setText(f"Week {week} standings - {len(standings)} players tracked")

        except ImportError:
            self.award_race_table.setRowCount(0)
            self.award_race_status.setText("Award Race tracking not available")
        except Exception as e:
            logger.error(f"Error loading award race data: {e}")
            self.award_race_table.setRowCount(0)
            self.award_race_status.setText(f"Error loading data: {e}")

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
                # Still populate Award Race - it tracks mid-season data (weeks 10-18)
                self._populate_award_race()
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
            self._populate_award_race()  # Mid-season tracking data
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

        # Clear all award widgets
        for award_id, widget in self.award_widgets.items():
            winner_name = widget.findChild(QLabel, f"{award_id}_winner_name")
            if winner_name:
                winner_name.setText("No awards calculated for this season")

            winner_details = widget.findChild(QLabel, f"{award_id}_winner_details")
            if winner_details:
                winner_details.setText("")

            vote_progress = widget.findChild(QProgressBar, f"{award_id}_vote_progress")
            if vote_progress:
                vote_progress.setValue(0)

            vote_percent = widget.findChild(QLabel, f"{award_id}_vote_percent")
            if vote_percent:
                vote_percent.setText("")

            # Clear finalist cards
            finalists_grid = widget.findChild(QWidget, f"{award_id}_finalists_grid")
            if finalists_grid:
                for i in range(4):
                    name_label = finalists_grid.findChild(QLabel, f"{award_id}_finalist_name_{i}")
                    details_label = finalists_grid.findChild(QLabel, f"{award_id}_finalist_details_{i}")
                    if name_label:
                        name_label.setText("")
                    if details_label:
                        details_label.setText("")

        # Clear other tables
        self.first_team_table.setRowCount(0)
        self.second_team_table.setRowCount(0)
        self.pro_bowl_table.setRowCount(0)
        self.stat_leaders_table.setRowCount(0)

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
        """Populate all major award widgets."""
        for award_id, result in self._awards_data.items():
            if award_id not in self.award_widgets:
                continue

            widget = self.award_widgets[award_id]

            # Get components
            winner_name = widget.findChild(QLabel, f"{award_id}_winner_name")
            winner_details = widget.findChild(QLabel, f"{award_id}_winner_details")
            vote_progress = widget.findChild(QProgressBar, f"{award_id}_vote_progress")
            vote_percent = widget.findChild(QLabel, f"{award_id}_vote_percent")

            if not result.has_winner:
                if winner_name:
                    winner_name.setText("No winner")
                continue

            winner = result.winner

            # Set winner info
            if winner_name:
                winner_name.setText(winner.player_name)
                winner_name.setProperty("player_id", winner.player_id)

            if winner_details:
                team_abbrev = self._get_team_abbrev(winner.team_id)
                winner_details.setText(f"{winner.position} - {team_abbrev}")

            # Set vote share
            vote_share_pct = int(winner.vote_share * 100)
            if vote_progress:
                vote_progress.setValue(vote_share_pct)

            if vote_percent:
                vote_percent.setText(f"{winner.vote_share:.1%} ({winner.total_points} pts)")

            # Populate finalists cards (top 4 for 2x2 grid)
            finalists_grid = widget.findChild(QWidget, f"{award_id}_finalists_grid")
            if finalists_grid:
                top_4 = result.top_5[:4]  # Show top 4 for 2x2 grid

                for i, finalist in enumerate(top_4):
                    name_label = finalists_grid.findChild(QLabel, f"{award_id}_finalist_name_{i}")
                    details_label = finalists_grid.findChild(QLabel, f"{award_id}_finalist_details_{i}")
                    card = finalists_grid.findChild(QFrame, f"{award_id}_finalist_card_{i}")

                    if name_label:
                        name_label.setText(f"#{i+2} {finalist.player_name}")
                    if details_label:
                        team = self._get_team_abbrev(finalist.team_id)
                        details_label.setText(f"{finalist.position} - {team} · {finalist.vote_share:.1%}")
                    if card:
                        # Store player_id for click handling
                        card.setProperty("player_id", finalist.player_id)
                        card.setVisible(True)

                # Hide unused cards if fewer than 4 finalists
                for i in range(len(top_4), 4):
                    card = finalists_grid.findChild(QFrame, f"{award_id}_finalist_card_{i}")
                    if card:
                        card.setVisible(False)

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
                type_item.setFont(QFont("Arial", 10, QFont.Bold))
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
                rank_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.stat_leaders_table.setItem(row, 0, rank_item)

            # Player name
            name_item = QTableWidgetItem(leader.player_name)
            name_item.setData(Qt.UserRole, leader.player_id)
            if leader.league_rank == 1:
                name_item.setFont(QFont("Arial", 10, QFont.Bold))
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
                value_item.setFont(QFont("Arial", 10, QFont.Bold))
                value_item.setForeground(QColor("#2E7D32"))
            self.stat_leaders_table.setItem(row, 4, value_item)

    def _on_category_changed(self):
        """Handle category dropdown change."""
        self._populate_stat_leaders()

    # ============================================
    # Helper Methods
    # ============================================

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
        self.continue_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "border-radius: 6px; padding: 12px 24px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #43A047; }"
        )
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
