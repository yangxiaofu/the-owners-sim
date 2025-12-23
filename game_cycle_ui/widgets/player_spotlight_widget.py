"""
PlayerSpotlightWidget - Display player headshot and key stats.

Part of Milestone 12: Media Coverage - Split Hero Card layout.

Shows:
- Player headshot/icon
- Name, position, number
- Key game stats (position-specific)
- Reusable across Media, Awards, Draft views
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from game_cycle_ui.theme import (
    ESPN_TEXT_PRIMARY,
    ESPN_TEXT_SECONDARY,
    ESPN_TEXT_MUTED,
    FontSizes,
)


class PlayerSpotlightWidget(QWidget):
    """
    Player spotlight card showing headshot and key stats.

    Layout:
    ┌──────────────────┐
    │   ┌────────┐     │
    │   │ Head   │     │
    │   │ shot   │     │
    │   │ [80x80]│     │
    │   └────────┘     │
    │                  │
    │  Player Name     │
    │  POSITION #XX    │
    │                  │
    │  3 TDs | 285 YDS │
    │  122.5 RATING    │
    │  0 INT           │
    └──────────────────┘
    """

    def __init__(
        self,
        player_data: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize player spotlight widget.

        Args:
            player_data: Dict with keys:
                - name: Player name
                - position: Position abbreviation (QB, RB, WR, etc.)
                - number: Jersey number
                - stats: Dict of stats (passing_yards, rushing_yards, etc.)
            parent: Parent widget
        """
        super().__init__(parent)
        self._data = player_data or {}
        self._setup_ui()

    def _setup_ui(self):
        """Build the spotlight UI."""
        self.setFixedWidth(200)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: #222222;
                border-radius: 4px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # Player headshot placeholder
        headshot = QFrame()
        headshot.setFixedSize(80, 80)
        headshot.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3a3a3a, stop:0.5 #4a4a4a, stop:1 #3a3a3a
                );
                border: 2px solid #555555;
                border-radius: 40px;
            }
        """)

        # Icon in headshot
        headshot_layout = QVBoxLayout(headshot)
        headshot_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label = QLabel("👤")
        icon_label.setStyleSheet(f"font-size: {FontSizes.DISPLAY}; background: transparent; border: none;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        headshot_layout.addWidget(icon_label)

        layout.addWidget(headshot, 0, Qt.AlignmentFlag.AlignHCenter)

        # Player name
        name = self._data.get("name", "Unknown Player")
        name_label = QLabel(name)
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-size: {FontSizes.BODY_LARGE};
            font-weight: bold;
        """)
        layout.addWidget(name_label)

        # Position and number
        position = self._data.get("position", "").upper()
        number = self._data.get("number", "")
        pos_number_label = QLabel(f"{position} #{number}")
        pos_number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pos_number_label.setStyleSheet(f"""
            color: {ESPN_TEXT_SECONDARY};
            font-size: {FontSizes.SMALL};
            font-weight: bold;
            letter-spacing: 1px;
        """)
        layout.addWidget(pos_number_label)

        # Spacer
        layout.addSpacing(8)

        # Stats section
        stats = self._data.get("stats", {})
        stat_lines = self._format_stats(position, stats)

        for stat_line in stat_lines:
            stat_label = QLabel(stat_line)
            stat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_label.setStyleSheet(f"""
                color: {ESPN_TEXT_PRIMARY};
                font-size: {FontSizes.BODY};
                font-weight: bold;
            """)
            layout.addWidget(stat_label)

        layout.addStretch()

    def _format_stats(self, position: str, stats: Dict[str, Any]) -> list[str]:
        """
        Format stats based on player position.

        Args:
            position: Position abbreviation
            stats: Stats dictionary

        Returns:
            List of formatted stat lines
        """
        if not stats:
            return ["No stats available"]

        position_upper = position.upper()

        # Quarterback stats
        if position_upper == "QB":
            tds = stats.get("passing_tds", 0)
            yards = stats.get("passing_yards", 0)
            ints = stats.get("passing_interceptions", 0)
            rating = stats.get("passer_rating", 0.0)

            return [
                f"{tds} TDs | {yards} YDS",
                f"{rating:.1f} RATING" if rating > 0 else "0 RATING",
                f"{ints} INT"
            ]

        # Running back stats
        elif position_upper == "RB":
            rush_yds = stats.get("rushing_yards", 0)
            rush_tds = stats.get("rushing_tds", 0)
            rush_att = stats.get("rushing_attempts", 0)
            rec = stats.get("receptions", 0)

            ypc = rush_yds / rush_att if rush_att > 0 else 0

            return [
                f"{rush_yds} RUSH YDS",
                f"{rush_tds} TDs | {ypc:.1f} YPC",
                f"{rec} REC" if rec > 0 else ""
            ]

        # Wide receiver / Tight end stats
        elif position_upper in ["WR", "TE"]:
            rec = stats.get("receptions", 0)
            rec_yds = stats.get("receiving_yards", 0)
            rec_tds = stats.get("receiving_tds", 0)
            targets = stats.get("targets", 0)

            return [
                f"{rec} REC | {rec_yds} YDS",
                f"{rec_tds} TDs",
                f"{targets} TARGETS" if targets > 0 else ""
            ]

        # Defensive stats
        elif position_upper in ["DE", "DT", "LB", "MLB", "OLB", "ILB"]:
            tackles = stats.get("tackles_total", 0)
            sacks = stats.get("sacks", 0.0)
            ints = stats.get("interceptions", 0)

            return [
                f"{tackles} TACKLES",
                f"{sacks:.1f} SACKS" if sacks > 0 else "",
                f"{ints} INT" if ints > 0 else ""
            ]

        # Defensive back stats
        elif position_upper in ["CB", "S", "FS", "SS", "DB"]:
            tackles = stats.get("tackles_total", 0)
            ints = stats.get("interceptions", 0)
            pd = stats.get("passes_defended", 0)

            return [
                f"{tackles} TACKLES" if tackles > 0 else "",
                f"{ints} INT",
                f"{pd} PD" if pd > 0 else ""
            ]

        # Kicker stats
        elif position_upper == "K":
            fgm = stats.get("field_goals_made", 0)
            fga = stats.get("field_goals_attempted", 0)
            xpm = stats.get("extra_points_made", 0)

            return [
                f"{fgm}/{fga} FG",
                f"{xpm} XP"
            ]

        # Punter stats
        elif position_upper == "P":
            punts = stats.get("punts", 0)
            punt_yds = stats.get("punt_yards", 0)
            avg = punt_yds / punts if punts > 0 else 0

            return [
                f"{punts} PUNTS",
                f"{avg:.1f} AVG"
            ]

        # Generic fallback
        else:
            return ["See box score"]

    def update_data(self, player_data: Dict[str, Any]):
        """
        Update player data and rebuild UI.

        Args:
            player_data: New player data dictionary
        """
        self._data = player_data
        # Clear and rebuild
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._setup_ui()
