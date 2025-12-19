"""
Season Recap View - Main tabbed view for OFFSEASON_HONORS stage.

Displays:
- Super Bowl: Champion and MVP
- Awards: All major awards, All-Pro teams, Pro Bowl rosters
- Retirements: Notable retirements and full list

Part of Milestone 13: Owner-GM Offseason Flow, Tollgate 12.
"""

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QComboBox, QTabWidget, QFrame, QScrollArea, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.views.awards_view import AwardsView
from game_cycle_ui.widgets.super_bowl_result_widget import SuperBowlResultWidget
from game_cycle_ui.widgets.retirement_card_widget import RetirementCardWidget
from game_cycle_ui.dialogs.retirement_detail_dialog import RetirementDetailDialog
from game_cycle_ui.theme import (
    TAB_STYLE, PRIMARY_BUTTON_STYLE, Typography, FontSizes, Colors, TextColors,
    apply_table_style
)

logger = logging.getLogger(__name__)


class SeasonRecapView(QWidget):
    """
    Season Recap View for OFFSEASON_HONORS stage.

    Three-tab interface:
    1. Super Bowl: Champion, MVP, box score
    2. Awards: Full AwardsView with all awards and honors
    3. Retirements: Notable retirements + full list

    Signals:
        continue_to_next_stage: User clicked Continue to Franchise Tag
        player_selected: User clicked on a player (for detail dialog)
        retirement_selected: User clicked on retirement (for career detail)
    """

    # Signals
    continue_to_next_stage = Signal()  # Forwarded from AwardsView
    player_selected = Signal(int)  # player_id for player detail
    retirement_selected = Signal(int)  # player_id for career detail

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Context
        self._dynasty_id: str = ""
        self._db_path: str = ""
        self._season: int = 2025
        self._user_team_id: int = 0
        self._offseason_mode: bool = False

        # Data cache
        self._retirements: List[Dict[str, Any]] = []
        self._super_bowl_result: Dict[str, Any] = {}
        self._super_bowl_mvp: Dict[str, Any] = {}

        # Build UI
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create main tabbed interface
        self._create_tabs(layout)

        # Continue button (shown in offseason mode)
        self._create_continue_button(layout)

    def _create_tabs(self, parent_layout: QVBoxLayout):
        """Create the main three-tab interface."""
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_STYLE)

        # Tab 1: Super Bowl
        self._create_super_bowl_tab()
        self.tabs.addTab(self.super_bowl_tab, "Super Bowl")

        # Tab 2: Awards (embedded AwardsView)
        self._create_awards_tab()
        self.tabs.addTab(self.awards_tab, "Awards")

        # Tab 3: Retirements
        self._create_retirements_tab()
        self.tabs.addTab(self.retirements_tab, "Retirements")

        parent_layout.addWidget(self.tabs, stretch=1)

    # ============================================
    # Tab 1: Super Bowl
    # ============================================

    def _create_super_bowl_tab(self):
        """Create the Super Bowl results tab."""
        self.super_bowl_tab = QWidget()
        layout = QVBoxLayout(self.super_bowl_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        # Super Bowl result widget
        self.super_bowl_widget = SuperBowlResultWidget()
        self.super_bowl_widget.view_box_score.connect(self._on_view_box_score)
        layout.addWidget(self.super_bowl_widget)

    def _on_view_box_score(self, game_id: str):
        """Handle View Box Score button click."""
        # TODO: Navigate to box score view
        logger.info(f"View box score for game {game_id}")

    # ============================================
    # Tab 2: Awards
    # ============================================

    def _create_awards_tab(self):
        """Create the Awards tab with embedded AwardsView."""
        self.awards_tab = QWidget()
        layout = QVBoxLayout(self.awards_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        # Embed full AwardsView
        self.awards_view = AwardsView()

        # Forward signals
        self.awards_view.player_selected.connect(self.player_selected.emit)
        self.awards_view.continue_to_next_stage.connect(self._on_awards_continue)

        layout.addWidget(self.awards_view)

    def _on_awards_continue(self):
        """Handle Continue button from AwardsView - forward to main handler."""
        # Switch to next tab or emit continue signal
        self.continue_to_next_stage.emit()

    # ============================================
    # Tab 3: Retirements
    # ============================================

    def _create_retirements_tab(self):
        """Create the Retirements tab."""
        self.retirements_tab = QWidget()
        layout = QVBoxLayout(self.retirements_tab)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header with filter and count
        self._create_retirements_header(layout)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        self.retirements_content_layout = QVBoxLayout(content)
        self.retirements_content_layout.setSpacing(16)

        # Notable retirements section
        self._create_notable_section()
        self.retirements_content_layout.addWidget(self.notable_group)

        # Other retirements table
        self._create_other_retirements_table()
        self.retirements_content_layout.addWidget(self.other_retirements_group)

        self.retirements_content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

    def _create_retirements_header(self, parent_layout: QVBoxLayout):
        """Create header with filter dropdown and count."""
        header = QHBoxLayout()

        # Title
        title = QLabel("RETIREMENTS")
        title.setFont(Typography.H4)
        title.setStyleSheet(f"color: {TextColors.ON_DARK};")
        header.addWidget(title)

        header.addStretch()

        # Filter dropdown
        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        header.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Retirements", "all")
        self.filter_combo.addItem("Your Team", "user_team")
        self.filter_combo.addItem("Notable Only", "notable")
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        header.addWidget(self.filter_combo)

        # Count label
        self.retirements_count_label = QLabel("0 retirements")
        self.retirements_count_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED}; margin-left: 16px;")
        header.addWidget(self.retirements_count_label)

        parent_layout.addLayout(header)

    def _create_notable_section(self):
        """Create the notable retirements section with cards."""
        self.notable_group = QGroupBox("Notable Retirements")
        self.notable_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: {FontSizes.H5};
                color: {TextColors.ON_DARK};
                background-color: #263238;
                border: 1px solid #37474f;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {TextColors.ON_DARK};
            }}
        """)

        self.notable_layout = QVBoxLayout(self.notable_group)
        self.notable_layout.setSpacing(12)

        # Placeholder
        self.notable_empty_label = QLabel("No notable retirements this season")
        self.notable_empty_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
        self.notable_empty_label.setAlignment(Qt.AlignCenter)
        self.notable_layout.addWidget(self.notable_empty_label)

    def _create_other_retirements_table(self):
        """Create the other retirements table."""
        self.other_retirements_group = QGroupBox("Other Retirements")
        self.other_retirements_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: {FontSizes.H5};
                color: {TextColors.ON_DARK};
                background-color: #263238;
                border: 1px solid #37474f;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {TextColors.ON_DARK};
            }}
        """)

        layout = QVBoxLayout(self.other_retirements_group)

        # Table
        self.other_retirements_table = QTableWidget()
        self.other_retirements_table.setColumnCount(6)
        self.other_retirements_table.setHorizontalHeaderLabels([
            "Player", "Position", "Age", "Years", "Team", "Reason"
        ])

        # Apply centralized table styling
        apply_table_style(self.other_retirements_table)

        # Column resize modes
        self.other_retirements_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.other_retirements_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)

        # Click handler
        self.other_retirements_table.cellClicked.connect(self._on_retirement_row_clicked)

        layout.addWidget(self.other_retirements_table)

    def _on_filter_changed(self):
        """Handle filter dropdown change."""
        self._populate_retirements()

    def _on_retirement_row_clicked(self, row: int, col: int):
        """Handle click on retirement row."""
        item = self.other_retirements_table.item(row, 0)  # Name column
        if item:
            player_id = item.data(Qt.UserRole)
            if player_id:
                self._show_retirement_detail(player_id)
                self.retirement_selected.emit(player_id)

    def _show_retirement_detail(self, player_id: int):
        """Show retirement detail dialog for a player."""
        # Find the retirement data for this player
        retirement_data = None
        for r in self._retirements:
            if r.get('player_id') == player_id:
                retirement_data = r
                break

        if not retirement_data:
            logger.warning(f"No retirement data found for player {player_id}")
            return

        # Get career summary (it's stored in retirement data)
        career_summary = retirement_data.get('career_summary', {})

        # Add retirement season for HOF eligibility
        retirement_data['retirement_season'] = self._season

        # Show dialog
        dialog = RetirementDetailDialog(
            retirement_data=retirement_data,
            career_summary=career_summary,
            user_team_id=self._user_team_id,
            parent=self
        )

        # Connect one-day contract signal
        dialog.one_day_contract_requested.connect(self._on_one_day_contract_requested)

        dialog.exec()

    def _on_one_day_contract_requested(self, player_id: int, team_id: int):
        """Handle one-day contract request."""
        logger.info(f"One-day contract requested for player {player_id} from team {team_id}")
        # TODO: Integrate with RetirementService to process the one-day contract
        try:
            from game_cycle.services.retirement_service import RetirementService
            service = RetirementService(self._db_path, self._dynasty_id, self._season)
            success = service.process_one_day_contract(player_id, team_id)
            if success:
                logger.info(f"One-day contract processed successfully")
            else:
                logger.warning(f"Failed to process one-day contract")
        except Exception as e:
            logger.error(f"Error processing one-day contract: {e}")

    # ============================================
    # Continue Button
    # ============================================

    def _create_continue_button(self, parent_layout: QVBoxLayout):
        """Create the Continue to Franchise Tag button."""
        self.continue_btn = QPushButton("Continue to Franchise Tag")
        self.continue_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.continue_btn.setMinimumHeight(50)
        self.continue_btn.setVisible(False)  # Hidden by default
        self.continue_btn.clicked.connect(self._on_continue_clicked)

        parent_layout.addWidget(self.continue_btn)

    def _on_continue_clicked(self):
        """Handle Continue button click."""
        self._offseason_mode = False
        self.continue_btn.setVisible(False)
        self.continue_to_next_stage.emit()

    # ============================================
    # Context Management
    # ============================================

    def set_context(self, dynasty_id: str, db_path: str, season: int):
        """
        Set dynasty context for data operations.

        Args:
            dynasty_id: Dynasty identifier
            db_path: Path to game_cycle.db
            season: Current season year
        """
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season

        # Propagate to embedded AwardsView
        self.awards_view.set_context(dynasty_id, db_path, season)

        # Load initial data
        self.refresh_data()

    def set_user_team_id(self, team_id: int):
        """
        Set user's team ID for filtering.

        Args:
            team_id: User's team ID (1-32)
        """
        self._user_team_id = team_id

    def set_offseason_mode(self, enabled: bool):
        """
        Enable/disable offseason mode (shows Continue button).

        Args:
            enabled: True to show Continue button, False to hide
        """
        self._offseason_mode = enabled
        self.continue_btn.setVisible(enabled)

        # Also propagate to AwardsView (it has its own Continue button)
        self.awards_view.set_offseason_mode(enabled)

    # ============================================
    # Data Loading
    # ============================================

    def refresh_data(self):
        """Refresh all tab data."""
        if not self._dynasty_id or not self._db_path:
            return

        # Load data for each tab
        self._load_super_bowl_data()
        self._load_retirements_data()

        # AwardsView handles its own refresh via set_context

    def _load_super_bowl_data(self):
        """Load Super Bowl champion and MVP data."""
        try:
            from game_cycle.database.connection import GameCycleDatabase
            from game_cycle.database.schedule_api import ScheduleAPI
            from game_cycle.database.awards_api import AwardsAPI
            from team_management.teams.team_loader import TeamLoader

            with GameCycleDatabase(self._db_path) as conn:
                schedule_api = ScheduleAPI(conn, self._dynasty_id)
                awards_api = AwardsAPI(conn, self._dynasty_id)

                # Get Super Bowl game
                playoff_games = schedule_api.get_playoff_games(self._season, "super_bowl")
                if playoff_games:
                    sb_game = playoff_games[0]
                    self._super_bowl_result = {
                        'winner_team_id': sb_game.get('winner_team_id'),
                        'home_team_id': sb_game.get('home_team_id'),
                        'away_team_id': sb_game.get('away_team_id'),
                        'home_score': sb_game.get('home_score', 0),
                        'away_score': sb_game.get('away_score', 0),
                        'game_id': sb_game.get('game_id'),
                    }
                else:
                    self._super_bowl_result = {}

                # Get Super Bowl MVP
                mvp_record = awards_api.get_super_bowl_mvp(self._season)
                if mvp_record:
                    self._super_bowl_mvp = {
                        'player_name': mvp_record.get('player_name', ''),
                        'position': mvp_record.get('position', ''),
                        'team_id': mvp_record.get('team_id'),
                        'stat_summary': mvp_record.get('stat_summary', ''),
                    }
                else:
                    self._super_bowl_mvp = {}

            # Populate Super Bowl widget
            team_loader = TeamLoader()
            self.super_bowl_widget.set_data(
                self._super_bowl_result,
                self._super_bowl_mvp,
                team_loader,
                self._season
            )

        except Exception as e:
            logger.error(f"Error loading Super Bowl data: {e}")
            self._super_bowl_result = {}
            self._super_bowl_mvp = {}

    def _load_retirements_data(self):
        """Load retirements data from RetirementService."""
        try:
            from game_cycle.services.retirement_service import RetirementService

            service = RetirementService(self._db_path, self._dynasty_id, self._season)

            # Check if retirements already processed
            if not service.retirements_already_processed():
                logger.info("No retirements processed for this season yet")
                self._retirements = []
                self._populate_retirements()
                return

            # Get season retirements from database
            retirement_records = service.get_season_retirements()

            # Enrich with player data and career summaries
            self._retirements = []
            for record in retirement_records:
                player_id = record.get('player_id')

                # Get career summary
                career_summary = service.get_player_career_summary(player_id)

                # Get player data for name, position
                player_dict = self._get_player_data(player_id)

                if player_dict and career_summary:
                    retirement_dict = {
                        'player_id': player_id,
                        'player_name': f"{player_dict.get('first_name', '')} {player_dict.get('last_name', '')}".strip(),
                        'position': career_summary.get('position', ''),
                        'age_at_retirement': record.get('age_at_retirement', 0),
                        'years_played': record.get('years_played', 0),
                        'final_team_id': record.get('final_team_id', 0),
                        'retirement_reason': record.get('retirement_reason', 'age_decline'),
                        'career_summary': career_summary,
                        'is_notable': self._is_notable(career_summary),
                        'headline': self._generate_headline(player_dict, career_summary),
                    }
                    self._retirements.append(retirement_dict)

            # Populate UI
            self._populate_retirements()

        except Exception as e:
            logger.error(f"Error loading retirements: {e}")
            self._retirements = []
            self._populate_retirements()

    def _get_player_data(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get player data from database."""
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT player_id, first_name, last_name, position, team_id
                FROM players
                WHERE dynasty_id = ? AND player_id = ?
            """, (self._dynasty_id, player_id))

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.warning(f"Error getting player data: {e}")
            return None

    def _is_notable(self, career_summary: Dict[str, Any]) -> bool:
        """Determine if retirement is notable."""
        return (
            career_summary.get('mvp_awards', 0) > 0 or
            career_summary.get('super_bowl_wins', 0) > 0 or
            career_summary.get('pro_bowls', 0) >= 3 or
            career_summary.get('all_pro_first_team', 0) > 0 or
            career_summary.get('all_pro_second_team', 0) > 0 or
            career_summary.get('hall_of_fame_score', 0) >= 40
        )

    def _generate_headline(self, player_dict: Dict[str, Any], career_summary: Dict[str, Any]) -> str:
        """Generate retirement headline."""
        name = f"{player_dict.get('first_name', '')} {player_dict.get('last_name', '')}".strip()
        position = career_summary.get('position', '')

        # Check notable achievements
        if career_summary.get('hall_of_fame_score', 0) >= 85:
            return f"Future Hall of Famer {name} announces retirement"
        elif career_summary.get('mvp_awards', 0) > 1:
            return f"{career_summary.get('mvp_awards')}x MVP {name} calls it a career"
        elif career_summary.get('mvp_awards', 0) > 0:
            return f"MVP {name} calls it a career"
        elif career_summary.get('super_bowl_wins', 0) > 1:
            return f"{career_summary.get('super_bowl_wins')}x Super Bowl champion {name} retires"
        elif career_summary.get('super_bowl_wins', 0) > 0:
            return f"Super Bowl champion {name} retires"
        elif career_summary.get('pro_bowls', 0) >= 3:
            return f"{career_summary.get('pro_bowls')}x Pro Bowler {name} announces retirement"
        else:
            return f"{position} {name} announces retirement"

    def _populate_retirements(self):
        """Populate retirements UI based on current filter."""
        filter_type = self.filter_combo.currentData()

        # Filter retirements
        if filter_type == "user_team":
            filtered = [r for r in self._retirements if r['final_team_id'] == self._user_team_id]
        elif filter_type == "notable":
            filtered = [r for r in self._retirements if r['is_notable']]
        else:  # "all"
            filtered = self._retirements

        # Update count
        self.retirements_count_label.setText(f"{len(filtered)} retirements")

        # Split into notable and other
        notable = [r for r in filtered if r['is_notable']]
        other = [r for r in filtered if not r['is_notable']]

        # Populate notable section
        self._populate_notable_section(notable)

        # Populate other retirements table
        self._populate_other_retirements_table(other)

    def _populate_notable_section(self, notable: List[Dict[str, Any]]):
        """Populate notable retirements section with cards."""
        # Clear existing cards
        while self.notable_layout.count() > 0:
            item = self.notable_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not notable:
            self.notable_empty_label = QLabel("No notable retirements this season")
            self.notable_empty_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED};")
            self.notable_empty_label.setAlignment(Qt.AlignCenter)
            self.notable_layout.addWidget(self.notable_empty_label)
            return

        # Add retirement cards
        for retirement in notable:
            card = RetirementCardWidget(retirement)
            card.details_clicked.connect(self._show_retirement_detail)
            card.details_clicked.connect(self.retirement_selected.emit)
            self.notable_layout.addWidget(card)

    def _populate_other_retirements_table(self, other: List[Dict[str, Any]]):
        """Populate other retirements table."""
        self.other_retirements_table.setRowCount(len(other))

        for row, retirement in enumerate(other):
            # Player name
            name = retirement.get('player_name', 'Unknown')
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, retirement.get('player_id'))
            self.other_retirements_table.setItem(row, 0, name_item)

            # Position
            pos = retirement.get('position', '')
            pos_item = QTableWidgetItem(pos)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.other_retirements_table.setItem(row, 1, pos_item)

            # Age
            age = retirement.get('age_at_retirement', 0)
            age_item = QTableWidgetItem(str(age))
            age_item.setTextAlignment(Qt.AlignCenter)
            self.other_retirements_table.setItem(row, 2, age_item)

            # Years
            years = retirement.get('years_played', 0)
            years_item = QTableWidgetItem(str(years))
            years_item.setTextAlignment(Qt.AlignCenter)
            self.other_retirements_table.setItem(row, 3, years_item)

            # Team
            team_id = retirement.get('final_team_id', 0)
            team_abbr = self._get_team_abbrev(team_id)
            team_item = QTableWidgetItem(team_abbr)
            team_item.setTextAlignment(Qt.AlignCenter)
            self.other_retirements_table.setItem(row, 4, team_item)

            # Reason
            reason = retirement.get('retirement_reason', 'age_decline')
            reason_display = self._format_reason(reason)
            reason_item = QTableWidgetItem(reason_display)
            self.other_retirements_table.setItem(row, 5, reason_item)

        # Show/hide group based on content
        self.other_retirements_group.setVisible(len(other) > 0)

    def _get_team_abbrev(self, team_id: int) -> str:
        """Get team abbreviation from team ID."""
        if team_id == 0:
            return "FA"

        try:
            from team_management.teams.team_loader import get_team_by_id
            team = get_team_by_id(team_id)
            return team.abbreviation if team else f"T{team_id}"
        except Exception:
            return f"T{team_id}"

    def _format_reason(self, reason: str) -> str:
        """Format retirement reason for display."""
        reason_map = {
            'age_decline': 'Age/Decline',
            'injury': 'Injury',
            'championship': 'Won Championship',
            'released': 'Released',
            'personal': 'Personal',
        }
        return reason_map.get(reason, reason.replace('_', ' ').title())

    # ============================================
    # Test Helpers / Public Data Setters
    # ============================================

    @property
    def tab_widget(self) -> QTabWidget:
        """Alias for tabs (for test compatibility)."""
        return self.tabs

    @property
    def continue_button(self) -> QPushButton:
        """Alias for continue_btn (for test compatibility)."""
        return self.continue_btn

    def set_super_bowl_data(self, data: Optional[Dict[str, Any]]):
        """
        Set Super Bowl data for display.

        Args:
            data: Dict with champion_team_id, runner_up_team_id, scores, mvp, etc.
                  Or None to show empty state.
        """
        if data is None:
            self._super_bowl_result = {}
            self._super_bowl_mvp = {}
            self.super_bowl_widget.set_data({}, {}, None, self._season)
            return

        # Map the test data format to the internal format
        self._super_bowl_result = {
            'winner_team_id': data.get('champion_team_id'),
            'home_team_id': data.get('champion_team_id'),  # Simplified mapping
            'away_team_id': data.get('runner_up_team_id'),
            'home_score': data.get('champion_score', 0),
            'away_score': data.get('runner_up_score', 0),
            'game_id': data.get('game_id'),
        }

        mvp = data.get('mvp', {})
        if mvp:
            stats = mvp.get('stats', {})
            stat_summary = ""
            if stats:
                stat_summary = f"{stats.get('completions', 0)}/{stats.get('attempts', 0)}, {stats.get('passing_yards', 0)} YDS, {stats.get('passing_tds', 0)} TD"
            self._super_bowl_mvp = {
                'player_name': mvp.get('name', ''),
                'position': mvp.get('position', ''),
                'team_id': mvp.get('team_id'),
                'stat_summary': stat_summary,
            }
        else:
            self._super_bowl_mvp = {}

        # Update widget
        try:
            from team_management.teams.team_loader import TeamLoader
            team_loader = TeamLoader()
        except Exception:
            team_loader = None

        self.super_bowl_widget.set_data(
            self._super_bowl_result,
            self._super_bowl_mvp,
            team_loader,
            data.get('season', self._season)
        )

    def set_retirements(self, retirements: List[Dict[str, Any]]):
        """
        Set retirements data for display.

        Args:
            retirements: List of retirement dicts with player_id, name, position,
                        age, team_id, years_played, reason, is_notable, career_summary
        """
        # Map the test data format to internal format
        self._retirements = []
        for r in retirements:
            retirement_dict = {
                'player_id': r.get('player_id'),
                'player_name': r.get('name', ''),
                'position': r.get('position', ''),
                'age_at_retirement': r.get('age', 0),
                'years_played': r.get('years_played', 0),
                'final_team_id': r.get('team_id', 0),
                'retirement_reason': r.get('reason', 'age_decline'),
                'career_summary': r.get('career_summary', {}),
                'is_notable': r.get('is_notable', False),
                'headline': r.get('headline', ''),
            }
            self._retirements.append(retirement_dict)

        # Populate UI
        self._populate_retirements()

    def _get_visible_retirements_count(self) -> int:
        """Get count of currently visible retirements (for tests)."""
        filter_type = self.filter_combo.currentData()

        if filter_type == "user_team":
            return len([r for r in self._retirements if r['final_team_id'] == self._user_team_id])
        elif filter_type == "notable":
            return len([r for r in self._retirements if r['is_notable']])
        else:
            return len(self._retirements)

    @property
    def _super_bowl_data(self) -> Dict[str, Any]:
        """Return combined Super Bowl data (for test compatibility)."""
        return {
            **self._super_bowl_result,
            'mvp': self._super_bowl_mvp,
        }
