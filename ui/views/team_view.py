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
from widgets.depth_chart_split_view import DepthChartSplitView
from widgets.staff_tab_widget import StaffTabWidget
from widgets.strategy_tab_widget import StrategyTabWidget
from widgets.team_statistics_widget import TeamStatisticsWidget
from widgets.team_needs_widget import TeamNeedsWidget
from controllers.team_controller import TeamController
from constants.team_ids import TeamIDs
from team_management.teams.team_loader import get_all_teams, get_team_by_id


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

        # Initialize controller (follows MVC pattern)
        self.controller = TeamController(db_path, dynasty_id, season)

        # Load all NFL teams for selector
        self.teams = get_all_teams()

        # Get user's team from dynasty (defaults to Detroit if not set)
        dynasty_team_id = self.controller.get_dynasty_team_id()
        self.current_team_id = dynasty_team_id if dynasty_team_id else TeamIDs.DETROIT_LIONS

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

        # Load initial roster for dynasty's team
        self._load_initial_roster()

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

        # Set default selection to dynasty's team (or Detroit as fallback)
        default_index = next(
            (i for i, team in enumerate(sorted_teams) if team.team_id == self.current_team_id),
            0
        )
        self.team_selector.setCurrentIndex(default_index)

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
        self.depth_chart_tab = DepthChartSplitView()
        self.finances_tab = FinancesTabWidget()
        self.staff_tab = StaffTabWidget()
        self.strategy_tab = StrategyTabWidget()
        self.statistics_tab = TeamStatisticsWidget(
            team_id=self.current_team_id,
            db_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season=self.season
        )
        self.team_needs_tab = TeamNeedsWidget(
            db_path=self.db_path,
            dynasty_id=self.dynasty_id,
            season=self.season
        )

        # Connect depth chart signal for persistence
        self.depth_chart_tab.swap_requested.connect(self._on_swap_requested)

        # Add tabs in order
        sub_tabs.addTab(self.roster_tab, "Roster")
        sub_tabs.addTab(self.depth_chart_tab, "Depth Chart")
        sub_tabs.addTab(self.finances_tab, "Finances")
        sub_tabs.addTab(self.staff_tab, "Staff")
        sub_tabs.addTab(self.strategy_tab, "Strategy")
        sub_tabs.addTab(self.statistics_tab, "Statistics")
        sub_tabs.addTab(self.team_needs_tab, "Team Needs")

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
        Handle team selector change - loads real data from database.

        Follows MVC pattern: View → Controller → Domain Model → Database APIs
        """
        team_id = self.team_selector.currentData()
        if team_id:
            self.current_team_id = team_id

            # Load roster data from controller
            try:
                roster_data = self.controller.get_team_roster(team_id)
                self.roster_tab.set_roster_data(roster_data)
            except Exception as e:
                print(f"[ERROR TeamView] Failed to load roster for team {team_id}: {e}")
                # Keep mock data on error

            # Load finances data from controller
            try:
                self.finances_tab.load_finances_data(self.controller, team_id)
            except Exception as e:
                print(f"[ERROR TeamView] Failed to load finances for team {team_id}: {e}")
                # Keep existing data on error

            # Load depth chart data from controller
            try:
                team = get_team_by_id(team_id)
                team_name = team.full_name if team else f"Team {team_id}"
                depth_chart_data = self.controller.get_depth_chart(team_id)
                self.depth_chart_tab.load_depth_chart(team_name, depth_chart_data)
            except Exception as e:
                print(f"[ERROR TeamView] Failed to load depth chart for team {team_id}: {e}")
                import traceback
                traceback.print_exc()
                # Keep existing data on error

            # Update statistics tab (mockup - just updates header)
            try:
                team = get_team_by_id(team_id)
                team_name = team.full_name if team else f"Team {team_id}"
                self.statistics_tab.set_team(team_id, team_name)
            except Exception as e:
                print(f"[ERROR TeamView] Failed to update statistics tab for team {team_id}: {e}")

            # Update Team Needs tab
            try:
                self.team_needs_tab.update_team(team_id)
            except Exception as e:
                print(f"[ERROR TeamView] Failed to update team needs for team {team_id}: {e}")
                import traceback
                traceback.print_exc()

            # TODO Phase 3: Load other tabs
            # self.staff_tab.load_staff(team_id)

    def _on_swap_requested(self, position: str, old_starter_id: int, new_starter_id: int):
        """
        Handle swap request from depth chart split view.

        When a bench player is dragged onto a starter slot, this method
        persists the swap to database and refreshes the display.

        Args:
            position: Position being swapped (e.g., "quarterback")
            old_starter_id: Current starter's player ID (being demoted)
            new_starter_id: Bench player's player ID (being promoted)
        """
        try:
            # Persist swap to database via controller
            success = self.controller.swap_starter_with_bench(
                self.current_team_id,
                position,
                old_starter_id,
                new_starter_id
            )

            if success:
                # Show success toast
                from ui.widgets.toast_notification import ToastNotification
                ToastNotification.show_success(
                    self.window(),
                    f"{position.replace('_', ' ').title()} depth chart updated!"
                )

                # Reload depth chart to show updated positions
                team = get_team_by_id(self.current_team_id)
                team_name = team.full_name if team else f"Team {self.current_team_id}"
                depth_chart_data = self.controller.get_depth_chart(self.current_team_id)
                self.depth_chart_tab.load_depth_chart(team_name, depth_chart_data)
            else:
                # Show error toast
                from ui.widgets.toast_notification import ToastNotification
                ToastNotification.show_error(
                    self.window(),
                    f"Failed to swap {position.replace('_', ' ')} players"
                )

        except Exception as e:
            print(f"[ERROR TeamView] Failed to swap depth chart for {position}: {e}")
            import traceback
            traceback.print_exc()

            # Show error toast
            from ui.widgets.toast_notification import ToastNotification
            ToastNotification.show_error(
                self.window(),
                f"Error swapping depth chart: {str(e)}"
            )

    def _load_initial_roster(self):
        """Load roster, finances, and depth chart for dynasty's team on initialization."""
        try:
            # Load roster
            roster_data = self.controller.get_team_roster(self.current_team_id)
            self.roster_tab.set_roster_data(roster_data)
        except Exception as e:
            print(f"[ERROR TeamView] Failed to load initial roster for team {self.current_team_id}: {e}")
            # Keep mock data on error

        try:
            # Load finances
            self.finances_tab.load_finances_data(self.controller, self.current_team_id)
        except Exception as e:
            print(f"[ERROR TeamView] Failed to load initial finances for team {self.current_team_id}: {e}")
            # Keep existing data on error

        try:
            # Load depth chart
            team = get_team_by_id(self.current_team_id)
            team_name = team.full_name if team else f"Team {self.current_team_id}"
            depth_chart_data = self.controller.get_depth_chart(self.current_team_id)
            self.depth_chart_tab.load_depth_chart(team_name, depth_chart_data)
        except Exception as e:
            print(f"[ERROR TeamView] Failed to load initial depth chart for team {self.current_team_id}: {e}")
            import traceback
            traceback.print_exc()
            # Keep existing data on error

        try:
            # Load team needs
            self.team_needs_tab.update_team(self.current_team_id)
        except Exception as e:
            print(f"[ERROR TeamView] Failed to load initial team needs for team {self.current_team_id}: {e}")
            import traceback
            traceback.print_exc()
            # Keep existing data on error
