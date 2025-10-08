"""
Team View for The Owner's Sim

Displays team roster, depth chart, finances, and coaching staff.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTabWidget, QStatusBar
)
from PySide6.QtCore import Qt

import sys
import os

# Add parent directories to path
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

# Add src to path for team data
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from widgets.roster_tab_widget import RosterTabWidget
from widgets.finances_tab_widget import FinancesTabWidget
from widgets.depth_chart_widget import DepthChartWidget
from widgets.staff_tab_widget import StaffTabWidget
from widgets.strategy_tab_widget import StrategyTabWidget
from constants.team_ids import TeamIDs
from team_management.teams.team_loader import load_all_teams


class TeamView(QWidget):
    """
    Team management view with complete roster, finances, depth chart, and staff.

    Phase 1 Mock UI: Visual-only implementation with hardcoded data
    Phase 2: Will add controllers and database connectivity
    """

    def __init__(self, parent=None, db_path="data/database/nfl_simulation.db",
                 dynasty_id="default", season=2025):
        super().__init__(parent)
        self.main_window = parent
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        # Load all NFL teams for selector
        self.teams = load_all_teams()
        self.current_team_id = TeamIDs.DETROIT_LIONS  # Default to Detroit

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Top bar: Team selector + Dynasty info
        top_bar = self._create_top_bar()
        layout.addLayout(top_bar)

        # Sub-tab widget
        self.sub_tabs = self._create_sub_tabs()
        layout.addWidget(self.sub_tabs)

        # Status bar
        status_bar = self._create_status_bar()
        layout.addLayout(status_bar)

        self.setLayout(layout)

    def _create_top_bar(self) -> QHBoxLayout:
        """Create top bar with team selector and dynasty info."""
        top_bar = QHBoxLayout()

        # Team selector label
        team_label = QLabel("Team:")
        team_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        top_bar.addWidget(team_label)

        # Team selector dropdown
        self.team_selector = QComboBox()
        self.team_selector.setMinimumWidth(250)

        # Populate with all 32 NFL teams (sorted alphabetically)
        sorted_teams = sorted(self.teams, key=lambda t: t.full_name)
        for team in sorted_teams:
            self.team_selector.addItem(team.full_name, team.team_id)

        # Set default selection to Detroit Lions
        detroit_index = next(
            (i for i, team in enumerate(sorted_teams) if team.team_id == TeamIDs.DETROIT_LIONS),
            0
        )
        self.team_selector.setCurrentIndex(detroit_index)

        # Connect signal (no functionality yet, just UI)
        self.team_selector.currentIndexChanged.connect(self._on_team_changed)

        top_bar.addWidget(self.team_selector)

        # Spacer
        top_bar.addStretch()

        # Dynasty info label
        dynasty_info = QLabel(f"Dynasty: {self.dynasty_id} | Season: {self.season}")
        dynasty_info.setStyleSheet("font-size: 12px; color: #888;")
        dynasty_info.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_bar.addWidget(dynasty_info)

        return top_bar

    def _create_sub_tabs(self) -> QTabWidget:
        """Create sub-tab widget with all team management tabs."""
        sub_tabs = QTabWidget()
        sub_tabs.setTabPosition(QTabWidget.North)
        sub_tabs.setDocumentMode(True)

        # Create all sub-tab widgets
        self.roster_tab = RosterTabWidget()
        self.depth_chart_tab = DepthChartWidget()
        self.finances_tab = FinancesTabWidget()
        self.staff_tab = StaffTabWidget()
        self.strategy_tab = StrategyTabWidget()

        # Add tabs in order
        sub_tabs.addTab(self.roster_tab, "Roster")
        sub_tabs.addTab(self.depth_chart_tab, "Depth Chart")
        sub_tabs.addTab(self.finances_tab, "Finances")
        sub_tabs.addTab(self.staff_tab, "Staff")
        sub_tabs.addTab(self.strategy_tab, "Strategy")

        return sub_tabs

    def _create_status_bar(self) -> QHBoxLayout:
        """Create status bar showing roster count, cap space, and dead money."""
        status_bar = QHBoxLayout()

        # Roster count (mock data)
        roster_label = QLabel("Roster: 53/53")
        roster_label.setStyleSheet("font-size: 12px; padding: 5px 10px;")
        status_bar.addWidget(roster_label)

        # Separator
        sep1 = QLabel("|")
        sep1.setStyleSheet("color: #ccc; padding: 0 5px;")
        status_bar.addWidget(sep1)

        # Cap space (mock data - green since positive)
        cap_space_label = QLabel("Cap Space: $12,547,332")
        cap_space_label.setStyleSheet(
            "font-size: 12px; padding: 5px 10px; color: #388E3C; font-weight: bold;"
        )
        status_bar.addWidget(cap_space_label)

        # Separator
        sep2 = QLabel("|")
        sep2.setStyleSheet("color: #ccc; padding: 0 5px;")
        status_bar.addWidget(sep2)

        # Dead money (mock data)
        dead_money_label = QLabel("Dead Money: $0")
        dead_money_label.setStyleSheet("font-size: 12px; padding: 5px 10px;")
        status_bar.addWidget(dead_money_label)

        # Spacer
        status_bar.addStretch()

        return status_bar

    def _on_team_changed(self, index: int):
        """
        Handle team selector change.

        Phase 1 (Mock): No functionality - just updates current_team_id
        Phase 2: Will reload roster/depth chart/finances/staff for new team
        """
        team_id = self.team_selector.currentData()
        if team_id:
            self.current_team_id = team_id
            # In Phase 2, we would call:
            # self.load_team_data(team_id)
            # self.roster_tab.load_roster(team_id)
            # self.finances_tab.load_contracts(team_id)
            # self.depth_chart_tab.load_depth_chart(team_id)
            # self.staff_tab.load_staff(team_id)
