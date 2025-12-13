"""
Rivalry Info Dialog - Displays rivalry details and head-to-head history.

Part of Milestone 11: Schedule & Rivalries, Tollgate 7.
Shows rivalry name, type, intensity meter, all-time record, current streak,
and playoff history between two teams.
"""

from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QProgressBar, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.theme import (
    UITheme, TABLE_HEADER_STYLE,
    get_intensity_label, get_rivalry_intensity_color, RIVALRY_TYPE_COLORS
)


class RivalryInfoDialog(QDialog):
    """
    Dialog showing rivalry details and head-to-head history.

    Shows:
    - Rivalry name and type badge
    - Intensity meter (visual bar 0-100)
    - All-time record (W-L-T)
    - Current streak
    - Playoff history
    - Team names
    """

    def __init__(
        self,
        rivalry: Optional[Any] = None,
        h2h_record: Optional[Any] = None,
        team_names: Optional[Dict[int, str]] = None,
        parent=None
    ):
        """
        Initialize rivalry info dialog.

        Args:
            rivalry: Rivalry model object
            h2h_record: HeadToHeadRecord model object
            team_names: Dict mapping team_id -> team_name
            parent: Parent widget
        """
        super().__init__(parent)
        self._rivalry = rivalry
        self._h2h_record = h2h_record
        self._team_names = team_names or {}

        self.setWindowTitle("Rivalry Information")
        self.setMinimumSize(450, 500)
        self.setModal(True)

        self._setup_ui()
        if rivalry:
            self._populate_data()

    def _setup_ui(self):
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header: Rivalry name
        self._create_header(layout)

        # Intensity section
        self._create_intensity_section(layout)

        # Teams section
        self._create_teams_section(layout)

        # Head-to-Head section
        self._create_h2h_section(layout)

        # Playoff history section
        self._create_playoff_section(layout)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(
            "QPushButton { background-color: #666; color: white; "
            "border-radius: 4px; padding: 10px 30px; font-size: 13px; }"
            "QPushButton:hover { background-color: #555; }"
        )
        close_btn.clicked.connect(self.accept)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create the header with rivalry name and type badge."""
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(8)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Rivalry name
        self.name_label = QLabel("Rivalry")
        self.name_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.name_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.name_label)

        # Type badge
        type_frame = QFrame()
        type_layout = QHBoxLayout(type_frame)
        type_layout.setContentsMargins(0, 0, 0, 0)

        type_layout.addStretch()

        self.type_badge = QLabel("TYPE")
        self.type_badge.setStyleSheet(
            "padding: 4px 12px; border-radius: 4px; "
            "font-weight: bold; font-size: 11px;"
        )
        type_layout.addWidget(self.type_badge)

        self.protected_badge = QLabel("PROTECTED")
        self.protected_badge.setStyleSheet(
            "background-color: #FFD700; color: #333; "
            "padding: 4px 12px; border-radius: 4px; "
            "font-weight: bold; font-size: 11px;"
        )
        self.protected_badge.hide()  # Hidden by default
        type_layout.addWidget(self.protected_badge)

        type_layout.addStretch()
        header_layout.addWidget(type_frame)

        parent_layout.addWidget(header_frame)

    def _create_intensity_section(self, parent_layout: QVBoxLayout):
        """Create the intensity meter section."""
        intensity_group = QGroupBox("Rivalry Intensity")
        intensity_layout = QVBoxLayout(intensity_group)
        intensity_layout.setSpacing(8)

        # Intensity bar
        bar_layout = QHBoxLayout()

        self.intensity_bar = QProgressBar()
        self.intensity_bar.setRange(0, 100)
        self.intensity_bar.setTextVisible(False)
        self.intensity_bar.setMinimumHeight(24)
        bar_layout.addWidget(self.intensity_bar, stretch=1)

        self.intensity_value_label = QLabel("0")
        self.intensity_value_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.intensity_value_label.setMinimumWidth(40)
        self.intensity_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bar_layout.addWidget(self.intensity_value_label)

        intensity_layout.addLayout(bar_layout)

        # Intensity level label
        self.intensity_level_label = QLabel("Mild")
        self.intensity_level_label.setAlignment(Qt.AlignCenter)
        self.intensity_level_label.setFont(QFont("Arial", 12))
        intensity_layout.addWidget(self.intensity_level_label)

        parent_layout.addWidget(intensity_group)

    def _create_teams_section(self, parent_layout: QVBoxLayout):
        """Create the teams section showing both team names."""
        teams_group = QGroupBox("Teams")
        teams_layout = QHBoxLayout(teams_group)
        teams_layout.setSpacing(20)

        # Team A
        team_a_frame = QFrame()
        team_a_layout = QVBoxLayout(team_a_frame)
        team_a_layout.setContentsMargins(0, 0, 0, 0)
        team_a_layout.setAlignment(Qt.AlignCenter)

        self.team_a_label = QLabel("Team A")
        self.team_a_label.setFont(QFont("Arial", 13, QFont.Bold))
        self.team_a_label.setAlignment(Qt.AlignCenter)
        team_a_layout.addWidget(self.team_a_label)

        teams_layout.addWidget(team_a_frame, stretch=1)

        # VS separator
        vs_label = QLabel("vs")
        vs_label.setFont(QFont("Arial", 16, QFont.Bold))
        vs_label.setStyleSheet("color: #999;")
        vs_label.setAlignment(Qt.AlignCenter)
        teams_layout.addWidget(vs_label)

        # Team B
        team_b_frame = QFrame()
        team_b_layout = QVBoxLayout(team_b_frame)
        team_b_layout.setContentsMargins(0, 0, 0, 0)
        team_b_layout.setAlignment(Qt.AlignCenter)

        self.team_b_label = QLabel("Team B")
        self.team_b_label.setFont(QFont("Arial", 13, QFont.Bold))
        self.team_b_label.setAlignment(Qt.AlignCenter)
        team_b_layout.addWidget(self.team_b_label)

        teams_layout.addWidget(team_b_frame, stretch=1)

        parent_layout.addWidget(teams_group)

    def _create_h2h_section(self, parent_layout: QVBoxLayout):
        """Create the head-to-head record section."""
        h2h_group = QGroupBox("All-Time Record")
        h2h_layout = QVBoxLayout(h2h_group)
        h2h_layout.setSpacing(12)

        # Record display
        record_layout = QHBoxLayout()

        self.team_a_record = QLabel("0")
        self.team_a_record.setFont(QFont("Arial", 28, QFont.Bold))
        self.team_a_record.setStyleSheet("color: #2E7D32;")  # Green
        self.team_a_record.setAlignment(Qt.AlignCenter)
        record_layout.addWidget(self.team_a_record, stretch=1)

        separator = QLabel("-")
        separator.setFont(QFont("Arial", 28, QFont.Bold))
        separator.setStyleSheet("color: #999;")
        separator.setAlignment(Qt.AlignCenter)
        record_layout.addWidget(separator)

        self.team_b_record = QLabel("0")
        self.team_b_record.setFont(QFont("Arial", 28, QFont.Bold))
        self.team_b_record.setStyleSheet("color: #1976D2;")  # Blue
        self.team_b_record.setAlignment(Qt.AlignCenter)
        record_layout.addWidget(self.team_b_record, stretch=1)

        h2h_layout.addLayout(record_layout)

        # Ties (if any)
        self.ties_label = QLabel("")
        self.ties_label.setAlignment(Qt.AlignCenter)
        self.ties_label.setStyleSheet("color: #666;")
        h2h_layout.addWidget(self.ties_label)

        # Current streak
        streak_layout = QHBoxLayout()
        streak_layout.addStretch()

        streak_title = QLabel("Current Streak:")
        streak_title.setStyleSheet("color: #666;")
        streak_layout.addWidget(streak_title)

        self.streak_label = QLabel("No current streak")
        self.streak_label.setFont(QFont("Arial", 11, QFont.Bold))
        streak_layout.addWidget(self.streak_label)

        streak_layout.addStretch()
        h2h_layout.addLayout(streak_layout)

        # Last meeting
        last_layout = QHBoxLayout()
        last_layout.addStretch()

        last_title = QLabel("Last Meeting:")
        last_title.setStyleSheet("color: #666;")
        last_layout.addWidget(last_title)

        self.last_meeting_label = QLabel("N/A")
        self.last_meeting_label.setFont(QFont("Arial", 11))
        last_layout.addWidget(self.last_meeting_label)

        last_layout.addStretch()
        h2h_layout.addLayout(last_layout)

        parent_layout.addWidget(h2h_group)

    def _create_playoff_section(self, parent_layout: QVBoxLayout):
        """Create the playoff history section."""
        playoff_group = QGroupBox("Playoff History")
        playoff_layout = QVBoxLayout(playoff_group)
        playoff_layout.setSpacing(8)

        # Playoff meetings count
        self.playoff_meetings_label = QLabel("Playoff Meetings: 0")
        self.playoff_meetings_label.setAlignment(Qt.AlignCenter)
        self.playoff_meetings_label.setFont(QFont("Arial", 12, QFont.Bold))
        playoff_layout.addWidget(self.playoff_meetings_label)

        # Playoff record
        playoff_record_layout = QHBoxLayout()
        playoff_record_layout.addStretch()

        self.playoff_team_a_wins = QLabel("0")
        self.playoff_team_a_wins.setFont(QFont("Arial", 16, QFont.Bold))
        self.playoff_team_a_wins.setStyleSheet("color: #2E7D32;")
        playoff_record_layout.addWidget(self.playoff_team_a_wins)

        playoff_sep = QLabel("-")
        playoff_sep.setFont(QFont("Arial", 16, QFont.Bold))
        playoff_sep.setStyleSheet("color: #999;")
        playoff_record_layout.addWidget(playoff_sep)

        self.playoff_team_b_wins = QLabel("0")
        self.playoff_team_b_wins.setFont(QFont("Arial", 16, QFont.Bold))
        self.playoff_team_b_wins.setStyleSheet("color: #1976D2;")
        playoff_record_layout.addWidget(self.playoff_team_b_wins)

        playoff_record_layout.addStretch()
        playoff_layout.addLayout(playoff_record_layout)

        parent_layout.addWidget(playoff_group)

    def _populate_data(self):
        """Populate dialog with rivalry and H2H data."""
        if not self._rivalry:
            return

        # Rivalry name
        self.name_label.setText(self._rivalry.rivalry_name)

        # Type badge
        rivalry_type = self._rivalry.rivalry_type.value
        type_color = RIVALRY_TYPE_COLORS.get(rivalry_type, "#666")
        self.type_badge.setText(rivalry_type.upper())
        self.type_badge.setStyleSheet(
            f"background-color: {type_color}; color: white; "
            "padding: 4px 12px; border-radius: 4px; "
            "font-weight: bold; font-size: 11px;"
        )

        # Protected badge
        if self._rivalry.is_protected:
            self.protected_badge.show()

        # Intensity
        intensity = self._rivalry.intensity
        self.intensity_bar.setValue(intensity)
        self.intensity_value_label.setText(str(intensity))
        self.intensity_level_label.setText(get_intensity_label(intensity))

        # Set intensity bar color based on level
        intensity_color = get_rivalry_intensity_color(intensity)
        self.intensity_bar.setStyleSheet(
            f"QProgressBar {{"
            f"  border: 1px solid #ccc; border-radius: 4px; text-align: center;"
            f"}}"
            f"QProgressBar::chunk {{"
            f"  background-color: {self._get_intensity_bar_color(intensity)};"
            f"  border-radius: 3px;"
            f"}}"
        )

        # Level label color
        level_color = self._get_intensity_bar_color(intensity)
        self.intensity_level_label.setStyleSheet(f"color: {level_color}; font-weight: bold;")

        # Team names
        team_a_name = self._team_names.get(self._rivalry.team_a_id, f"Team {self._rivalry.team_a_id}")
        team_b_name = self._team_names.get(self._rivalry.team_b_id, f"Team {self._rivalry.team_b_id}")
        self.team_a_label.setText(team_a_name)
        self.team_b_label.setText(team_b_name)

        # Head-to-head record
        if self._h2h_record:
            self.team_a_record.setText(str(self._h2h_record.team_a_wins))
            self.team_b_record.setText(str(self._h2h_record.team_b_wins))

            if self._h2h_record.ties > 0:
                self.ties_label.setText(f"Ties: {self._h2h_record.ties}")

            # Current streak
            if self._h2h_record.current_streak_team and self._h2h_record.current_streak_count > 0:
                streak_team_name = self._team_names.get(
                    self._h2h_record.current_streak_team,
                    f"Team {self._h2h_record.current_streak_team}"
                )
                self.streak_label.setText(f"{streak_team_name} W{self._h2h_record.current_streak_count}")

                # Color based on which team
                if self._h2h_record.current_streak_team == self._rivalry.team_a_id:
                    self.streak_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
                else:
                    self.streak_label.setStyleSheet("color: #1976D2; font-weight: bold;")
            else:
                self.streak_label.setText("No current streak")
                self.streak_label.setStyleSheet("color: #666;")

            # Last meeting
            if self._h2h_record.last_meeting_season:
                winner_name = "Tie"
                if self._h2h_record.last_meeting_winner:
                    winner_name = self._team_names.get(
                        self._h2h_record.last_meeting_winner,
                        f"Team {self._h2h_record.last_meeting_winner}"
                    )
                self.last_meeting_label.setText(
                    f"Season {self._h2h_record.last_meeting_season} ({winner_name})"
                )

            # Playoff history
            self.playoff_meetings_label.setText(
                f"Playoff Meetings: {self._h2h_record.playoff_meetings}"
            )
            self.playoff_team_a_wins.setText(str(self._h2h_record.playoff_team_a_wins))
            self.playoff_team_b_wins.setText(str(self._h2h_record.playoff_team_b_wins))

    def _get_intensity_bar_color(self, intensity: int) -> str:
        """Get progress bar chunk color based on intensity."""
        if intensity >= 90:
            return "#C62828"  # Red - Legendary
        elif intensity >= 75:
            return "#F57C00"  # Orange - Intense
        elif intensity >= 50:
            return "#FBC02D"  # Yellow - Competitive
        elif intensity >= 25:
            return "#4CAF50"  # Green - Developing
        else:
            return "#78909C"  # Gray - Mild

    def set_data(
        self,
        rivalry,
        h2h_record,
        team_names: Dict[int, str]
    ):
        """
        Set rivalry and H2H data after initialization.

        Args:
            rivalry: Rivalry model object
            h2h_record: HeadToHeadRecord model object
            team_names: Dict mapping team_id -> team_name
        """
        self._rivalry = rivalry
        self._h2h_record = h2h_record
        self._team_names = team_names
        self._populate_data()
