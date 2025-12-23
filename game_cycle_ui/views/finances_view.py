"""
Finances View - Shows player contract matrix with multi-year cap projections.

Displays:
- Player contract matrix (players x years)
- Cap hit amounts per cell
- Visual indicators for expiring contracts, guaranteed money, cap hit severity
- Sortable by player name, position, cap hit
"""

from typing import Dict, List, Optional
import sqlite3
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QComboBox, QFrame, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from game_cycle_ui.widgets import SummaryPanel
from game_cycle_ui.widgets.contract_matrix_widget import ContractMatrixWidget
from game_cycle_ui.dialogs import ContractDetailsDialog
from game_cycle_ui.theme import (
    apply_table_style,
    Colors,
    Typography,
    FontSizes,
    TextColors,
    ESPN_THEME,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE
)
from team_management.teams.team_loader import get_team_by_id


class FinancesView(QWidget):
    """
    View for team finances showing player contract matrix.

    Layout:
    - Summary panel at top (cap space, total committed, dead money)
    - Filter controls (position, contract status)
    - Contract matrix table (players x years)
    - Legend explaining visual indicators
    """

    # Signals
    refresh_requested = Signal()
    player_selected = Signal(int, str)  # player_id, player_name

    # Default salary cap (2025 season)
    DEFAULT_SALARY_CAP = 255_400_000

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Instance variables
        self._dynasty_id: Optional[str] = None
        self._db_path: str = ""
        self._season: int = 2025
        self._user_team_id: int = 1
        self._contract_data: List[Dict] = []
        self._salary_cap: int = self.DEFAULT_SALARY_CAP

        # UI setup
        self._setup_ui()

    def set_context(self, dynasty_id: str, db_path: str, season: int):
        """Set the context for data loading."""
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season
        # Update matrix year columns
        self.contract_matrix.set_current_year(season)

    def set_user_team_id(self, team_id: int):
        """Set the user's team ID for filtering."""
        self._user_team_id = team_id
        # Update team combo selection
        self._select_team_in_combo(team_id)
        self.refresh_data()

    def refresh_data(self):
        """Reload contract data from database."""
        self._load_contract_data()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel
        self._create_summary_panel(layout)

        # Filter controls
        self._create_filter_panel(layout)

        # Contract matrix (main content)
        self._create_contract_matrix(layout)

        # Legend
        self._create_legend(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create summary stats: Total Committed, Available Cap, Dead Money."""
        self.summary_panel = SummaryPanel("Financial Summary")

        # Total cap committed across all visible years
        self.total_committed_label = self.summary_panel.add_stat(
            "Total Committed", "$0", Colors.INFO
        )

        # Current year cap space
        self.cap_space_label = self.summary_panel.add_stat(
            "Cap Space", "$0", Colors.SUCCESS
        )

        # Dead money
        self.dead_money_label = self.summary_panel.add_stat(
            "Dead Money", "$0", Colors.ERROR
        )

        # Players under contract
        self.players_count_label = self.summary_panel.add_stat(
            "Players", "0"
        )

        self.summary_panel.add_stretch()
        parent_layout.addWidget(self.summary_panel)

    def _create_filter_panel(self, parent_layout: QVBoxLayout):
        """Create filter controls for team and position."""
        filter_frame = QFrame()
        filter_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_THEME['card_bg']};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 8, 10, 8)

        # Team selector
        team_label = QLabel("Team:")
        team_label.setStyleSheet(f"color: {TextColors.ON_DARK}; font-weight: bold;")
        filter_layout.addWidget(team_label)

        self.team_combo = QComboBox()
        self.team_combo.setMinimumWidth(200)
        self._populate_team_combo()
        self.team_combo.currentIndexChanged.connect(self._on_team_changed)
        filter_layout.addWidget(self.team_combo)

        filter_layout.addSpacing(20)

        # Position filter
        pos_label = QLabel("Position:")
        pos_label.setStyleSheet(f"color: {TextColors.ON_DARK}; font-weight: bold;")
        filter_layout.addWidget(pos_label)

        self.position_combo = QComboBox()
        self.position_combo.setMinimumWidth(150)
        self._populate_position_combo()
        self.position_combo.currentIndexChanged.connect(self._on_position_filter_changed)
        filter_layout.addWidget(self.position_combo)

        filter_layout.addStretch()

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        filter_layout.addWidget(self.refresh_btn)

        parent_layout.addWidget(filter_frame)

    def _populate_team_combo(self):
        """Populate team dropdown with all 32 NFL teams."""
        self.team_combo.blockSignals(True)
        self.team_combo.clear()

        # Add all teams
        for team_id in range(1, 33):
            team = get_team_by_id(team_id)
            if team:
                self.team_combo.addItem(f"{team.city} {team.nickname}", team_id)

        self.team_combo.blockSignals(False)

    def _populate_position_combo(self):
        """Populate position filter dropdown."""
        from PySide6.QtGui import QStandardItem

        self.position_combo.blockSignals(True)
        self.position_combo.clear()

        # Position groups
        self.position_combo.addItem("All Positions", None)
        self.position_combo.addItem("Offense", "OFFENSE")
        self.position_combo.addItem("Defense", "DEFENSE")
        self.position_combo.addItem("Special Teams", "SPECIAL")

        # Add non-selectable separator
        separator = QStandardItem("───────────")
        separator.setFlags(Qt.ItemFlag(0))  # Not selectable
        self.position_combo.model().appendRow(separator)

        # Individual position groups
        self.position_combo.addItem("QB", "QB")
        self.position_combo.addItem("RB", "RB")
        self.position_combo.addItem("WR", "WR")
        self.position_combo.addItem("TE", "TE")
        self.position_combo.addItem("OL (Offensive Line)", "OL")
        self.position_combo.addItem("DL (Defensive Line)", "DL")
        self.position_combo.addItem("LB (Linebackers)", "LB")
        self.position_combo.addItem("DB (Defensive Backs)", "DB")
        self.position_combo.addItem("K/P", "KP")

        self.position_combo.blockSignals(False)

    def _select_team_in_combo(self, team_id: int):
        """Select a specific team in the combo box."""
        for i in range(self.team_combo.count()):
            if self.team_combo.itemData(i) == team_id:
                self.team_combo.blockSignals(True)
                self.team_combo.setCurrentIndex(i)
                self.team_combo.blockSignals(False)
                break

    def _create_contract_matrix(self, parent_layout: QVBoxLayout):
        """Create the contract matrix widget."""
        matrix_group = QGroupBox("Contract Matrix")
        matrix_group.setStyleSheet(f"""
            QGroupBox {{
                font-family: {Typography.FAMILY};
                font-size: {FontSizes.H4};
                font-weight: bold;
                color: {TextColors.ON_DARK};
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 16px;
                background-color: {ESPN_THEME['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 8px;
                background-color: {ESPN_THEME['dark_bg']};
                border-radius: 4px;
            }}
        """)

        matrix_layout = QVBoxLayout(matrix_group)

        self.contract_matrix = ContractMatrixWidget(
            current_year=self._season,
            num_years=7,  # Current + 6 future years
            parent=self
        )

        # Connect signals
        self.contract_matrix.player_clicked.connect(self._on_player_clicked)
        self.contract_matrix.contract_clicked.connect(self._on_contract_clicked)

        matrix_layout.addWidget(self.contract_matrix)
        parent_layout.addWidget(matrix_group, stretch=1)

    def _create_legend(self, parent_layout: QVBoxLayout):
        """Create legend explaining color coding."""
        legend_frame = QFrame()
        legend_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_THEME['card_bg']};
                border-radius: 4px;
                padding: 4px;
            }}
        """)
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setContentsMargins(10, 6, 10, 6)
        legend_layout.setSpacing(20)

        # Legend title
        legend_title = QLabel("Legend:")
        legend_title.setStyleSheet(f"color: {TextColors.ON_DARK}; font-weight: bold;")
        legend_layout.addWidget(legend_title)

        # Color indicators
        legend_layout.addWidget(self._create_legend_item(
            "< $5M", TextColors.ON_DARK, None
        ))
        legend_layout.addWidget(self._create_legend_item(
            "$5-10M", Colors.WARNING, None
        ))
        legend_layout.addWidget(self._create_legend_item(
            "$10-20M", Colors.ERROR, None
        ))
        legend_layout.addWidget(self._create_legend_item(
            "> $20M", "#FF6B6B", "#3D1B1B"
        ))
        legend_layout.addWidget(self._create_legend_item(
            "Expiring", Colors.WARNING, Colors.WARNING_DARK
        ))
        legend_layout.addWidget(self._create_legend_item(
            "Guaranteed", Colors.INFO, None, underline=True
        ))

        legend_layout.addStretch()
        parent_layout.addWidget(legend_frame)

    def _create_legend_item(
        self,
        text: str,
        text_color: str,
        bg_color: Optional[str],
        underline: bool = False
    ) -> QLabel:
        """Create a single legend item."""
        label = QLabel(f"  {text}  ")

        style = f"color: {text_color}; padding: 2px 6px; border-radius: 3px;"
        if bg_color:
            style += f" background-color: {bg_color};"
        if underline:
            style += " text-decoration: underline;"

        label.setStyleSheet(style)
        return label

    def _load_contract_data(self):
        """Load contract data from database."""
        if not self._db_path or not self._dynasty_id:
            return

        # Get selected team
        team_id = self.team_combo.currentData()
        if not team_id:
            team_id = self._user_team_id

        # Get position filter ONCE at the start
        position_filter = self.position_combo.currentData()

        try:
            from salary_cap.cap_database_api import CapDatabaseAPI

            api = CapDatabaseAPI(self._db_path, dynasty_id=self._dynasty_id)

            # Get all active contracts for the team
            contracts = api.get_team_contracts(
                team_id=team_id,
                season=self._season,
                dynasty_id=self._dynasty_id,
                active_only=True
            )

            # Build matrix data with player info
            matrix_data = []
            total_current_year = 0
            dead_money = 0

            for contract in contracts:
                contract_id = contract['contract_id']
                player_id = contract['player_id']

                # Get year-by-year details
                year_details = api.get_contract_year_details(contract_id)

                # Get player info (name, position)
                player_info = self._get_player_info(player_id)
                if not player_info:
                    continue

                # Check position filter
                player_position = player_info.get('position', '')
                if position_filter is not None and not self._matches_position_filter(
                    player_position, position_filter
                ):
                    continue

                player_entry = {
                    'player_id': player_id,
                    'player_name': player_info.get('name', 'Unknown'),
                    'position': player_info.get('position', ''),
                    'contract_id': contract_id,
                    'end_year': contract['end_year'],
                    'total_value': contract['total_value'],
                    'total_guaranteed': contract.get('total_guaranteed', 0),
                    'year_cap_hits': {}
                }

                for detail in year_details:
                    year = detail['season_year']
                    player_entry['year_cap_hits'][year] = {
                        'cap_hit': detail['total_cap_hit'],
                        'base_salary': detail['base_salary'],
                        'signing_bonus_proration': detail.get('signing_bonus_proration', 0),
                        'roster_bonus': detail.get('roster_bonus', 0),
                        'workout_bonus': detail.get('workout_bonus', 0),
                        'guaranteed': detail.get('base_salary_guaranteed', False),
                        'is_final_year': (year == contract['end_year'])
                    }

                    # Track current year cap hit
                    if year == self._season:
                        total_current_year += detail['total_cap_hit']

                matrix_data.append(player_entry)

            # Apply data to widget
            self.contract_matrix.set_contract_data(matrix_data)
            self._contract_data = matrix_data

            # Update summary
            self._update_summary(matrix_data, total_current_year, dead_money)

        except Exception as e:
            import logging
            logging.error(f"Error loading contract data: {e}")

    # Position name to abbreviation mapping
    POSITION_ABBREVIATIONS = {
        # Offense - Skill positions
        'quarterback': 'QB',
        'running_back': 'RB',
        'halfback': 'HB',
        'fullback': 'FB',
        'wide_receiver': 'WR',
        'tight_end': 'TE',
        # Offense - Line
        'left_tackle': 'LT',
        'left_guard': 'LG',
        'center': 'C',
        'right_guard': 'RG',
        'right_tackle': 'RT',
        'tackle': 'OT',
        'guard': 'OG',
        'offensive_tackle': 'OT',
        'offensive_guard': 'OG',
        'offensive_line': 'OL',
        # Defense - Line
        'left_end': 'LE',
        'right_end': 'RE',
        'defensive_end': 'DE',
        'defensive_tackle': 'DT',
        'nose_tackle': 'NT',
        'defensive_line': 'DL',
        'edge': 'EDGE',
        # Defense - Linebackers
        'linebacker': 'LB',
        'left_outside_linebacker': 'LOLB',
        'middle_linebacker': 'MLB',
        'right_outside_linebacker': 'ROLB',
        'inside_linebacker': 'ILB',
        'outside_linebacker': 'OLB',
        'will_linebacker': 'WLB',
        'sam_linebacker': 'SLB',
        'mike_linebacker': 'MLB',
        # Defense - Secondary
        'cornerback': 'CB',
        'free_safety': 'FS',
        'strong_safety': 'SS',
        'safety': 'S',
        'defensive_back': 'DB',
        # Special Teams
        'kicker': 'K',
        'punter': 'P',
        'long_snapper': 'LS',
        'kick_returner': 'KR',
        'punt_returner': 'PR',
    }

    def _get_player_info(self, player_id: int) -> Optional[Dict]:
        """Get player name and position from database."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT
                        first_name || ' ' || last_name as name,
                        positions
                    FROM players
                    WHERE player_id = ?
                      AND dynasty_id = ?
                ''', (player_id, self._dynasty_id))

                row = cursor.fetchone()
                if row:
                    result = dict(row)
                    # Parse positions JSON to get primary position
                    positions = result.get('positions', '[]')
                    if isinstance(positions, str):
                        try:
                            positions_list = json.loads(positions)
                            if positions_list:
                                # Convert full position name to abbreviation
                                full_pos = positions_list[0].lower()
                                result['position'] = self.POSITION_ABBREVIATIONS.get(
                                    full_pos, full_pos.upper()
                                )
                            else:
                                result['position'] = ''
                        except json.JSONDecodeError:
                            result['position'] = positions
                    return result
                return None
        except Exception:
            return None

    def _matches_position_filter(self, position: str, filter_value) -> bool:
        """Check if position matches the filter."""
        # None = All Positions (no filter)
        if filter_value is None:
            return True

        position = position.upper()

        # Position group definitions - comprehensive coverage
        OFFENSE = {'QB', 'RB', 'FB', 'HB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT', 'OL', 'OT', 'OG', 'T', 'G'}
        DEFENSE = {'LE', 'RE', 'DT', 'NT', 'DE', 'EDGE', 'DL',
                   'LOLB', 'ROLB', 'MLB', 'ILB', 'OLB', 'LB',
                   'CB', 'FS', 'SS', 'S', 'DB', 'SAF'}
        SPECIAL = {'K', 'P', 'LS', 'KR', 'PR'}

        if filter_value == "OFFENSE":
            return position in OFFENSE
        elif filter_value == "DEFENSE":
            return position in DEFENSE
        elif filter_value == "SPECIAL":
            return position in SPECIAL
        elif filter_value == "OL":
            return position in {'LT', 'LG', 'C', 'RG', 'RT', 'OL', 'OT', 'OG', 'T', 'G'}
        elif filter_value == "DL":
            return position in {'LE', 'RE', 'DT', 'NT', 'DE', 'EDGE', 'DL'}
        elif filter_value == "LB":
            return position in {'LOLB', 'ROLB', 'MLB', 'ILB', 'OLB', 'LB', 'WLB', 'SLB'}
        elif filter_value == "DB":
            return position in {'CB', 'FS', 'SS', 'S', 'DB', 'SAF'}
        elif filter_value == "KP":
            return position in {'K', 'P'}
        else:
            # Direct position match (QB, RB, WR, TE, etc.)
            return position == filter_value

    def _update_summary(
        self,
        matrix_data: List[Dict],
        total_current_year: int,
        dead_money: int
    ):
        """Update summary panel with current data."""
        # Calculate total committed (sum of all years)
        total_committed = sum(
            entry['total_value'] for entry in matrix_data
        )

        # Cap space
        cap_space = self._salary_cap - total_current_year

        # Update labels
        self.total_committed_label.setText(self._format_cap(total_committed))
        self.cap_space_label.setText(self._format_cap(cap_space))
        self.dead_money_label.setText(self._format_cap(dead_money))
        self.players_count_label.setText(str(len(matrix_data)))

        # Update cap space color based on health
        if cap_space < 0:
            self.cap_space_label.setStyleSheet(f"color: {Colors.ERROR};")
        elif cap_space < self._salary_cap * 0.05:
            self.cap_space_label.setStyleSheet(f"color: {Colors.WARNING};")
        else:
            self.cap_space_label.setStyleSheet(f"color: {Colors.SUCCESS};")

    def _format_cap(self, amount: int) -> str:
        """Format cap amount as $XXM or $XXK."""
        if amount >= 1_000_000:
            return f"${amount / 1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount / 1_000:.0f}K"
        elif amount > 0:
            return f"${amount:,}"
        return "$0"

    def _on_team_changed(self, index: int):
        """Handle team selection change."""
        self.refresh_data()

    def _on_position_filter_changed(self, index: int):
        """Handle position filter change."""
        self.refresh_data()

    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        self.refresh_data()
        self.refresh_requested.emit()

    def _on_player_clicked(self, player_id: int):
        """Handle player click in matrix."""
        # Find player name
        for entry in self._contract_data:
            if entry.get('player_id') == player_id:
                self.player_selected.emit(player_id, entry.get('player_name', 'Unknown'))
                break

    def _on_contract_clicked(self, contract_id: int, player_name: str):
        """Handle contract click - open contract details dialog."""
        if not self._db_path or not self._dynasty_id:
            return

        try:
            dialog = ContractDetailsDialog(
                contract_id=contract_id,
                player_name=player_name,
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                parent=self
            )
            dialog.exec()
        except Exception as e:
            import logging
            logging.error(f"Error opening contract details: {e}")