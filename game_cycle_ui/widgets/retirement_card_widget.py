"""
Retirement Card Widget - Displays notable player retirement.

Card-based display showing career highlights for notable retiring players.
"""

from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QProgressBar
)
from PySide6.QtCore import Qt, Signal

from game_cycle_ui.theme import (
    Typography, FontSizes, Colors,
    SECONDARY_BUTTON_STYLE
)


class RetirementCardWidget(QFrame):
    """
    Card widget for displaying notable retirement.

    Shows:
    - Player name, position, age, team
    - Career highlights (seasons, awards)
    - Key stats and HOF score
    - View Career button

    Designed for ESPN dark theme.
    """

    details_clicked = Signal(int)  # player_id for career detail dialog

    def __init__(self, retirement: Dict[str, Any], parent: Optional[QWidget] = None):
        """
        Initialize retirement card.

        Args:
            retirement: Retirement data dict with keys:
                - player_id: int
                - player_name: str
                - position: str
                - age: int (age_at_retirement)
                - years_played: int
                - final_team_id: int
                - retirement_reason: str
                - career_summary: Dict with pro_bowls, mvp_awards, etc.
                - is_notable: bool
                - headline: str
            parent: Parent widget
        """
        super().__init__(parent)
        self._retirement = retirement
        self._player_id = retirement.get("player_id", 0)

        self._setup_ui()
        self._populate_data()

    def _setup_ui(self):
        """Build the card layout."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1e3a5f;
                border: 1px solid #37474F;
                border-radius: 8px;
                padding: 16px;
            }}
            QFrame:hover {{
                border-color: {Colors.INFO};
                background-color: #234569;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)

        # Header row: Name and View Career button
        header_layout = QHBoxLayout()

        # Left side: Name and position
        name_layout = QVBoxLayout()
        name_layout.setSpacing(2)

        self._name_label = QLabel()
        self._name_label.setFont(Typography.H4)
        self._name_label.setStyleSheet("color: white;")
        name_layout.addWidget(self._name_label)

        self._position_label = QLabel()
        self._position_label.setFont(Typography.BODY_SMALL)
        self._position_label.setStyleSheet(f"color: {Colors.MUTED};")
        name_layout.addWidget(self._position_label)

        header_layout.addLayout(name_layout)
        header_layout.addStretch()

        # View Career button
        self._view_btn = QPushButton("View Career")
        self._view_btn.setStyleSheet(SECONDARY_BUTTON_STYLE + """
            QPushButton {
                padding: 6px 12px;
                font-size: 12px;
            }
        """)
        self._view_btn.clicked.connect(self._on_view_career_clicked)
        header_layout.addWidget(self._view_btn)

        layout.addLayout(header_layout)

        # Career highlights line
        self._highlights_label = QLabel()
        self._highlights_label.setFont(Typography.BODY)
        self._highlights_label.setStyleSheet("color: #B0BEC5;")
        self._highlights_label.setWordWrap(True)
        layout.addWidget(self._highlights_label)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        # Career stats frame
        self._stats_frame = self._create_stats_section()
        stats_layout.addWidget(self._stats_frame)

        stats_layout.addStretch()

        # HOF Score section
        self._hof_frame = self._create_hof_section()
        stats_layout.addWidget(self._hof_frame)

        layout.addLayout(stats_layout)

    def _create_stats_section(self) -> QFrame:
        """Create the career stats mini-section."""
        frame = QFrame()
        frame.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._stats_label = QLabel()
        self._stats_label.setFont(Typography.BODY_SMALL)
        self._stats_label.setStyleSheet(f"color: {Colors.MUTED};")
        layout.addWidget(self._stats_label)

        return frame

    def _create_hof_section(self) -> QFrame:
        """Create the Hall of Fame score section."""
        frame = QFrame()
        frame.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        hof_title = QLabel("HOF Score")
        hof_title.setFont(Typography.SMALL)
        hof_title.setStyleSheet(f"color: {Colors.MUTED};")
        hof_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(hof_title)

        # HOF score progress bar
        self._hof_bar = QProgressBar()
        self._hof_bar.setRange(0, 100)
        self._hof_bar.setFixedWidth(80)
        self._hof_bar.setFixedHeight(16)
        self._hof_bar.setTextVisible(True)
        self._hof_bar.setStyleSheet("""
            QProgressBar {
                background-color: #37474F;
                border: none;
                border-radius: 4px;
                text-align: center;
                color: white;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self._hof_bar)

        return frame

    def _populate_data(self):
        """Populate all labels with retirement data."""
        # Name with notable indicator
        player_name = self._retirement.get("player_name", "Unknown")
        is_notable = self._retirement.get("is_notable", False)
        if is_notable:
            self._name_label.setText(f"{player_name}")
        else:
            self._name_label.setText(player_name)

        # Position, age, team
        position = self._retirement.get("position", "")
        age = self._retirement.get("age_at_retirement") or self._retirement.get("age", 0)
        team_name = self._get_team_display()
        self._position_label.setText(f"{position} ({age}) - {team_name}")

        # Career highlights
        highlights = self._build_highlights()
        self._highlights_label.setText(highlights)

        # Career stats
        stats = self._build_stats_line()
        self._stats_label.setText(stats)

        # HOF score
        career_summary = self._retirement.get("career_summary", {})
        if isinstance(career_summary, dict):
            hof_score = career_summary.get("hall_of_fame_score", 0)
        else:
            # CareerSummary object
            hof_score = getattr(career_summary, "hall_of_fame_score", 0) or 0

        self._hof_bar.setValue(int(hof_score))
        self._update_hof_bar_color(hof_score)

    def _get_team_display(self) -> str:
        """Get team display name."""
        # Try to get team name from retirement data
        final_team_id = self._retirement.get("final_team_id", 0)
        if final_team_id == 0:
            return "Free Agent"

        # Use team_id as fallback
        return f"Team {final_team_id}"

    def _build_highlights(self) -> str:
        """Build career highlights string."""
        parts = []

        years = self._retirement.get("years_played", 0)
        if years > 0:
            parts.append(f"{years} seasons")

        career_summary = self._retirement.get("career_summary", {})
        if isinstance(career_summary, dict):
            mvp = career_summary.get("mvp_awards", 0)
            sb = career_summary.get("super_bowl_wins", 0)
            pro_bowls = career_summary.get("pro_bowls", 0)
            all_pro_first = career_summary.get("all_pro_first_team", 0)
            all_pro_second = career_summary.get("all_pro_second_team", 0)
        else:
            # CareerSummary object
            mvp = getattr(career_summary, "mvp_awards", 0) or 0
            sb = getattr(career_summary, "super_bowl_wins", 0) or 0
            pro_bowls = getattr(career_summary, "pro_bowls", 0) or 0
            all_pro_first = getattr(career_summary, "all_pro_first_team", 0) or 0
            all_pro_second = getattr(career_summary, "all_pro_second_team", 0) or 0

        if mvp > 0:
            parts.append(f"{mvp}x MVP")
        if sb > 0:
            parts.append(f"{sb}x Super Bowl Champion")
        if pro_bowls > 0:
            parts.append(f"{pro_bowls}x Pro Bowl")

        all_pro = all_pro_first + all_pro_second
        if all_pro > 0:
            parts.append(f"{all_pro}x All-Pro")

        return " | ".join(parts) if parts else "Career highlights unavailable"

    def _build_stats_line(self) -> str:
        """Build position-specific career stats line."""
        career_summary = self._retirement.get("career_summary", {})
        position = self._retirement.get("position", "")

        if isinstance(career_summary, dict):
            games = career_summary.get("games_played", 0)
            pass_yds = career_summary.get("pass_yards", 0)
            pass_tds = career_summary.get("pass_tds", 0)
            rush_yds = career_summary.get("rush_yards", 0)
            rush_tds = career_summary.get("rush_tds", 0)
            rec_yds = career_summary.get("rec_yards", 0)
            rec_tds = career_summary.get("rec_tds", 0)
            tackles = career_summary.get("tackles", 0)
            sacks = career_summary.get("sacks", 0)
            ints = career_summary.get("interceptions", 0)
        else:
            # CareerSummary object
            games = getattr(career_summary, "games_played", 0) or 0
            pass_yds = getattr(career_summary, "pass_yards", 0) or 0
            pass_tds = getattr(career_summary, "pass_tds", 0) or 0
            rush_yds = getattr(career_summary, "rush_yards", 0) or 0
            rush_tds = getattr(career_summary, "rush_tds", 0) or 0
            rec_yds = getattr(career_summary, "rec_yards", 0) or 0
            rec_tds = getattr(career_summary, "rec_tds", 0) or 0
            tackles = getattr(career_summary, "tackles", 0) or 0
            sacks = getattr(career_summary, "sacks", 0) or 0
            ints = getattr(career_summary, "interceptions", 0) or 0

        parts = [f"{games} games"]

        if position == "QB":
            if pass_yds > 0:
                parts.append(f"{pass_yds:,} pass yds")
            if pass_tds > 0:
                parts.append(f"{pass_tds} TDs")
        elif position in ("RB", "FB"):
            if rush_yds > 0:
                parts.append(f"{rush_yds:,} rush yds")
            if rush_tds > 0:
                parts.append(f"{rush_tds} TDs")
        elif position in ("WR", "TE"):
            if rec_yds > 0:
                parts.append(f"{rec_yds:,} rec yds")
            if rec_tds > 0:
                parts.append(f"{rec_tds} TDs")
        elif position in ("EDGE", "DT", "DE", "LOLB", "MLB", "ROLB", "LB"):
            if tackles > 0:
                parts.append(f"{tackles} tackles")
            if sacks > 0:
                parts.append(f"{sacks:.1f} sacks")
        elif position in ("CB", "FS", "SS", "S"):
            if tackles > 0:
                parts.append(f"{tackles} tackles")
            if ints > 0:
                parts.append(f"{ints} INTs")

        return " | ".join(parts)

    def _update_hof_bar_color(self, score: int):
        """Update HOF bar color based on score."""
        if score >= 85:
            color = "#FFD700"  # Gold - First ballot lock
        elif score >= 60:
            color = "#4CAF50"  # Green - Strong candidate
        elif score >= 40:
            color = "#2196F3"  # Blue - Possible
        else:
            color = "#78909C"  # Gray - Unlikely

        self._hof_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #37474F;
                border: none;
                border-radius: 4px;
                text-align: center;
                color: white;
                font-size: 10px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)

    def _on_view_career_clicked(self):
        """Handle View Career button click."""
        if self._player_id:
            self.details_clicked.emit(self._player_id)

    def get_player_id(self) -> int:
        """Get the player ID for this retirement card."""
        return self._player_id
