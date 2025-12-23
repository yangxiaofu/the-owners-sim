"""
League Sidebar Widget - Left panel for League Dashboard.

Displays current week, clinched/eliminated teams, and top performers.
"""

from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PySide6.QtCore import Qt

from game_cycle_ui.theme import ESPN_THEME, Colors, Typography, FontSizes, TextColors


class LeagueSidebarWidget(QWidget):
    """
    Sidebar widget displaying league overview information.

    Sections:
    1. Week Indicator - Current week number
    2. Clinched Teams - Teams that clinched playoff/division
    3. Eliminated Teams - Teams eliminated from playoffs
    4. Top Performers - League leaders snapshot
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._week: int = 1
        self._clinched_teams: List[Dict] = []
        self._eliminated_teams: List[Dict] = []
        self._top_performers: Dict[str, Dict] = {}

        self.setFixedWidth(280)
        self._setup_ui()

    def _setup_ui(self):
        """Build the sidebar layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(8, 8, 8, 8)

        # 1. Week Indicator
        self._create_week_section(layout)

        # 2. Clinched Teams
        self._create_clinched_section(layout)

        # 3. Eliminated Teams
        self._create_eliminated_section(layout)

        # 4. Top Performers
        self._create_performers_section(layout)

        # Push everything up
        layout.addStretch()

    def _create_week_section(self, parent_layout: QVBoxLayout):
        """Create week indicator section."""
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: {ESPN_THEME['card_bg']}; "
            "border-radius: 6px; }}"
        )

        layout = QVBoxLayout(frame)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 10, 12, 10)

        # Week label
        self.week_label = QLabel("WEEK 1")
        self.week_label.setFont(Typography.H1)
        self.week_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        self.week_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.week_label)

        # Season type
        self.season_type_label = QLabel("Regular Season")
        self.season_type_label.setFont(Typography.SMALL)
        self.season_type_label.setStyleSheet(f"color: {ESPN_THEME['text_secondary']};")
        self.season_type_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.season_type_label)

        parent_layout.addWidget(frame)

    def _create_clinched_section(self, parent_layout: QVBoxLayout):
        """Create clinched teams section."""
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: {ESPN_THEME['card_bg']}; "
            "border-radius: 6px; }}"
        )

        layout = QVBoxLayout(frame)
        layout.setSpacing(4)
        layout.setContentsMargins(10, 8, 10, 8)

        # Section header
        header = QLabel("CLINCHED")
        header.setFont(Typography.TINY_BOLD)
        header.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
        layout.addWidget(header)

        # Teams container
        self.clinched_container = QVBoxLayout()
        self.clinched_container.setSpacing(2)
        layout.addLayout(self.clinched_container)

        # Empty state
        self.clinched_empty = QLabel("No teams clinched yet")
        self.clinched_empty.setFont(Typography.SMALL)
        self.clinched_empty.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
        self.clinched_container.addWidget(self.clinched_empty)

        self.clinched_frame = frame
        parent_layout.addWidget(frame)

    def _create_eliminated_section(self, parent_layout: QVBoxLayout):
        """Create eliminated teams section."""
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: {ESPN_THEME['card_bg']}; "
            "border-radius: 6px; }}"
        )

        layout = QVBoxLayout(frame)
        layout.setSpacing(4)
        layout.setContentsMargins(10, 8, 10, 8)

        # Section header
        header = QLabel("ELIMINATED")
        header.setFont(Typography.TINY_BOLD)
        header.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
        layout.addWidget(header)

        # Teams container
        self.eliminated_container = QVBoxLayout()
        self.eliminated_container.setSpacing(2)
        layout.addLayout(self.eliminated_container)

        # Empty state
        self.eliminated_empty = QLabel("No teams eliminated yet")
        self.eliminated_empty.setFont(Typography.SMALL)
        self.eliminated_empty.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
        self.eliminated_container.addWidget(self.eliminated_empty)

        self.eliminated_frame = frame
        parent_layout.addWidget(frame)

    def _create_performers_section(self, parent_layout: QVBoxLayout):
        """Create top performers section."""
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: {ESPN_THEME['card_bg']}; "
            "border-radius: 6px; }}"
        )

        layout = QVBoxLayout(frame)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 8, 10, 8)

        # Section header
        header = QLabel("TOP PERFORMERS")
        header.setFont(Typography.TINY_BOLD)
        header.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
        layout.addWidget(header)

        # Performer rows (5 categories)
        self.performer_labels: Dict[str, tuple] = {}
        categories = [
            ("pass", "Pass"),
            ("rush", "Rush"),
            ("rec", "Rec"),
            ("sacks", "Sacks"),
            ("int", "INT")
        ]

        for key, display in categories:
            row = QHBoxLayout()
            row.setSpacing(4)

            # Category label
            cat_label = QLabel(f"{display}:")
            cat_label.setFont(Typography.SMALL)
            cat_label.setStyleSheet(f"color: {ESPN_THEME['text_secondary']};")
            cat_label.setFixedWidth(45)
            row.addWidget(cat_label)

            # Player name
            name_label = QLabel("--")
            name_label.setFont(Typography.SMALL_BOLD)
            name_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
            row.addWidget(name_label, 1)

            # Stat value
            stat_label = QLabel("--")
            stat_label.setFont(Typography.SMALL)
            stat_label.setStyleSheet(f"color: {Colors.SUCCESS};")
            stat_label.setAlignment(Qt.AlignRight)
            row.addWidget(stat_label)

            layout.addLayout(row)
            self.performer_labels[key] = (name_label, stat_label)

        parent_layout.addWidget(frame)

    # =========================================================================
    # Public API
    # =========================================================================

    def set_week(self, week: int, season_type: str = "regular_season"):
        """Set current week display."""
        self._week = week
        self.week_label.setText(f"WEEK {week}")

        if season_type == "regular_season":
            self.season_type_label.setText("Regular Season")
        elif season_type == "playoffs":
            self.season_type_label.setText("Playoffs")
        else:
            self.season_type_label.setText(season_type.replace("_", " ").title())

    def set_clinched_teams(self, teams: List[Dict]):
        """
        Set clinched teams list.

        Args:
            teams: List of dicts with 'name', 'abbrev', 'type' (division/playoff)
        """
        self._clinched_teams = teams

        # Clear existing
        self._clear_layout(self.clinched_container)

        if not teams:
            empty = QLabel("No teams clinched yet")
            empty.setFont(Typography.SMALL)
            empty.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
            self.clinched_container.addWidget(empty)
            return

        for team in teams[:8]:  # Limit to 8
            row = QHBoxLayout()
            row.setSpacing(4)

            # Bullet
            bullet = QLabel("•")
            bullet.setStyleSheet(f"color: {Colors.SUCCESS};")
            row.addWidget(bullet)

            # Team name
            name = QLabel(team.get('name', team.get('abbrev', 'Team')))
            name.setFont(Typography.SMALL)
            name.setStyleSheet(f"color: {TextColors.ON_DARK};")
            row.addWidget(name, 1)

            # Clinch type badge
            clinch_type = team.get('type', '')
            if clinch_type:
                badge = QLabel(clinch_type[0].upper())  # D for division, P for playoff
                badge.setStyleSheet(
                    f"color: {Colors.SUCCESS}; "
                    f"font-size: {FontSizes.TINY}; font-weight: bold; "
                    "background-color: rgba(46, 125, 50, 0.3); "
                    "padding: 1px 4px; border-radius: 2px;"
                )
                row.addWidget(badge)

            self.clinched_container.addLayout(row)

    def set_eliminated_teams(self, teams: List[Dict]):
        """
        Set eliminated teams list.

        Args:
            teams: List of dicts with 'name', 'abbrev'
        """
        self._eliminated_teams = teams

        # Clear existing
        self._clear_layout(self.eliminated_container)

        if not teams:
            empty = QLabel("No teams eliminated yet")
            empty.setFont(Typography.SMALL)
            empty.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
            self.eliminated_container.addWidget(empty)
            return

        for team in teams[:8]:  # Limit to 8
            row = QHBoxLayout()
            row.setSpacing(4)

            # Bullet
            bullet = QLabel("•")
            bullet.setStyleSheet(f"color: {Colors.ERROR};")
            row.addWidget(bullet)

            # Team name
            name = QLabel(team.get('name', team.get('abbrev', 'Team')))
            name.setFont(Typography.SMALL)
            name.setStyleSheet(f"color: {ESPN_THEME['text_secondary']};")
            row.addWidget(name, 1)

            self.eliminated_container.addLayout(row)

    def set_top_performers(self, performers: Dict[str, Dict]):
        """
        Set top performers display.

        Args:
            performers: Dict with keys 'pass', 'rush', 'rec', 'sacks', 'int'
                       Each value is dict with 'name', 'value', 'team'
        """
        self._top_performers = performers

        for key, (name_label, stat_label) in self.performer_labels.items():
            if key in performers and performers[key]:
                perf = performers[key]
                # Shorten name: "Jared Goff" -> "J. Goff"
                full_name = perf.get('name', '--')
                parts = full_name.split()
                if len(parts) >= 2:
                    short_name = f"{parts[0][0]}. {parts[-1]}"
                else:
                    short_name = full_name
                name_label.setText(short_name)

                # Format stat value
                value = perf.get('value', 0)
                if key == 'sacks':
                    stat_label.setText(f"{value:.1f}")
                else:
                    stat_label.setText(f"{value:,}")
            else:
                name_label.setText("--")
                stat_label.setText("--")

    def clear(self):
        """Clear all data."""
        self._week = 1
        self._clinched_teams = []
        self._eliminated_teams = []
        self._top_performers = {}

        self.week_label.setText("WEEK 1")
        self.season_type_label.setText("Regular Season")
        self.set_clinched_teams([])
        self.set_eliminated_teams([])
        self.set_top_performers({})

    def _clear_layout(self, layout):
        """Clear all items from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
