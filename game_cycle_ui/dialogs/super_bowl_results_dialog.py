"""
Super Bowl Results Dialog - Shows championship results and season awards.

Displays after Super Bowl completion:
- Super Bowl winner with final score
- Super Bowl MVP with key stats
- Season award winners (MVP, OPOY, DPOY, etc.)
- Continue button to proceed to Franchise Tag
"""

from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QWidget, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class SuperBowlResultsDialog(QDialog):
    """
    Dialog showing Super Bowl results and season awards.

    Layout:
    - Header: "Super Bowl Champions"
    - Winner panel: Team name with score
    - MVP panel: Player name, position, stats
    - Awards summary: Table of season award winners
    - Continue button
    """

    continue_clicked = Signal()

    def __init__(
        self,
        super_bowl_result: Dict[str, Any],
        season_awards: Dict[str, Any],
        team_loader: Any,
        season: int,
        parent=None
    ):
        """
        Initialize Super Bowl results dialog.

        Args:
            super_bowl_result: Dict with winner_team_id, scores, mvp data
            season_awards: Dict mapping award_id to award result
            team_loader: TeamLoader for getting team names
            season: Season year
            parent: Parent widget
        """
        super().__init__(parent)
        self._super_bowl_result = super_bowl_result or {}
        self._season_awards = season_awards or {}
        self._team_loader = team_loader
        self._season = season

        self.setWindowTitle(f"Super Bowl {self._get_super_bowl_number()} Champions")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        self._setup_ui()

    def _get_super_bowl_number(self) -> str:
        """Get Super Bowl number in Roman numerals (approximate)."""
        # Super Bowl I was 1966 season, so season 2025 = Super Bowl LIX (59)
        number = self._season - 1966 + 1
        # Simple Roman numeral conversion for 40-70 range
        if 50 <= number < 60:
            return f"L{self._to_roman(number - 50)}"
        elif 60 <= number < 70:
            return f"LX{self._to_roman(number - 60)}"
        elif 40 <= number < 50:
            return f"XL{self._to_roman(number - 40)}"
        else:
            return str(number)

    def _to_roman(self, n: int) -> str:
        """Convert small number (0-9) to Roman numerals."""
        if n == 0:
            return ""
        numerals = {9: "IX", 5: "V", 4: "IV", 1: "I"}
        result = ""
        for value, numeral in numerals.items():
            while n >= value:
                result += numeral
                n -= value
        return result

    def _setup_ui(self):
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        self._create_header(layout)

        # Winner section
        self._create_winner_section(layout)

        # MVP section
        self._create_mvp_section(layout)

        # Awards summary
        self._create_awards_section(layout)

        layout.addStretch()

        # Continue button
        self._create_continue_button(layout)

    def _create_header(self, layout: QVBoxLayout):
        """Create the header section."""
        header = QLabel(f"Super Bowl {self._get_super_bowl_number()}")
        header.setFont(QFont("Arial", 24, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #1976D2;")
        layout.addWidget(header)

        subtitle = QLabel(f"{self._season} Season Champions")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

    def _create_winner_section(self, layout: QVBoxLayout):
        """Create the winner display section."""
        winner_frame = QFrame()
        winner_frame.setStyleSheet("""
            QFrame {
                background-color: #E3F2FD;
                border: 2px solid #1976D2;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        winner_layout = QVBoxLayout(winner_frame)

        # Get team info
        winner_team_id = self._super_bowl_result.get("winner_team_id")
        home_team_id = self._super_bowl_result.get("home_team_id")
        away_team_id = self._super_bowl_result.get("away_team_id")
        home_score = self._super_bowl_result.get("home_score", 0)
        away_score = self._super_bowl_result.get("away_score", 0)

        winner_name = "Unknown"
        loser_name = "Unknown"
        winner_score = 0
        loser_score = 0

        if self._team_loader and winner_team_id:
            winner_team = self._team_loader.get_team_by_id(winner_team_id)
            winner_name = winner_team.full_name if winner_team else f"Team {winner_team_id}"

            loser_team_id = away_team_id if winner_team_id == home_team_id else home_team_id
            loser_team = self._team_loader.get_team_by_id(loser_team_id)
            loser_name = loser_team.full_name if loser_team else f"Team {loser_team_id}"

            if winner_team_id == home_team_id:
                winner_score = home_score
                loser_score = away_score
            else:
                winner_score = away_score
                loser_score = home_score

        # Champion label
        champion_label = QLabel(winner_name)
        champion_label.setFont(QFont("Arial", 20, QFont.Bold))
        champion_label.setAlignment(Qt.AlignCenter)
        champion_label.setStyleSheet("color: #1a1a1a;")
        winner_layout.addWidget(champion_label)

        # Score
        score_label = QLabel(f"defeated {loser_name}")
        score_label.setFont(QFont("Arial", 12))
        score_label.setAlignment(Qt.AlignCenter)
        score_label.setStyleSheet("color: #333;")
        winner_layout.addWidget(score_label)

        score_value = QLabel(f"{winner_score} - {loser_score}")
        score_value.setFont(QFont("Arial", 16, QFont.Bold))
        score_value.setAlignment(Qt.AlignCenter)
        score_value.setStyleSheet("color: #1a1a1a;")
        winner_layout.addWidget(score_value)

        layout.addWidget(winner_frame)

    def _create_mvp_section(self, layout: QVBoxLayout):
        """Create the Super Bowl MVP section."""
        mvp_data = self._super_bowl_result.get("mvp")
        if not mvp_data:
            return

        mvp_group = QGroupBox("Super Bowl MVP")
        mvp_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        mvp_layout = QVBoxLayout(mvp_group)

        # MVP name and position
        player_name = mvp_data.get("player_name", "Unknown")
        position = mvp_data.get("position", "")
        team_id = mvp_data.get("team_id")

        team_name = ""
        if self._team_loader and team_id:
            team = self._team_loader.get_team_by_id(team_id)
            team_name = f" - {team.abbreviation}" if team else ""

        name_label = QLabel(f"{player_name} ({position}){team_name}")
        name_label.setFont(QFont("Arial", 14, QFont.Bold))
        name_label.setAlignment(Qt.AlignCenter)
        mvp_layout.addWidget(name_label)

        # Stats summary
        stat_summary = mvp_data.get("stat_summary", "")
        if stat_summary:
            stats_label = QLabel(stat_summary)
            stats_label.setFont(QFont("Arial", 11))
            stats_label.setAlignment(Qt.AlignCenter)
            stats_label.setStyleSheet("color: #444;")
            stats_label.setWordWrap(True)
            mvp_layout.addWidget(stats_label)

        layout.addWidget(mvp_group)

    def _create_awards_section(self, layout: QVBoxLayout):
        """Create the season awards summary section."""
        if not self._season_awards:
            return

        awards_group = QGroupBox(f"{self._season} Season Awards")
        awards_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        awards_layout = QVBoxLayout(awards_group)

        # Create table for awards
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Award", "Winner", "Team"])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)

        # Award display names
        award_names = {
            "mvp": "Most Valuable Player",
            "opoy": "Offensive Player of the Year",
            "dpoy": "Defensive Player of the Year",
            "oroy": "Offensive Rookie of the Year",
            "droy": "Defensive Rookie of the Year",
            "cpoy": "Comeback Player of the Year",
        }

        # Populate table
        awards_to_show = ["mvp", "opoy", "dpoy", "oroy", "droy", "cpoy"]
        table.setRowCount(len(awards_to_show))

        for row, award_id in enumerate(awards_to_show):
            award_data = self._season_awards.get(award_id, {})

            # Award name
            award_name = award_names.get(award_id, award_id.upper())
            table.setItem(row, 0, QTableWidgetItem(award_name))

            # Winner name - show "To be announced" if no winner
            winner = award_data.get("winner") or {}
            winner_name = winner.get("player_name") if winner else "To be announced"
            table.setItem(row, 1, QTableWidgetItem(winner_name))

            # Team - only show if winner exists
            team_id = winner.get("team_id") if winner else None
            team_abbr = "-"
            if self._team_loader and team_id:
                team = self._team_loader.get_team_by_id(team_id)
                team_abbr = team.abbreviation if team else str(team_id)
            table.setItem(row, 2, QTableWidgetItem(team_abbr))

        table.setMaximumHeight(200)
        awards_layout.addWidget(table)

        layout.addWidget(awards_group)

    def _create_continue_button(self, layout: QVBoxLayout):
        """Create the continue button."""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        continue_btn = QPushButton("Continue to Offseason")
        continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border-radius: 4px;
                padding: 12px 32px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
        """)
        continue_btn.clicked.connect(self._on_continue)
        btn_layout.addWidget(continue_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_continue(self):
        """Handle continue button click."""
        self.continue_clicked.emit()
        self.accept()
