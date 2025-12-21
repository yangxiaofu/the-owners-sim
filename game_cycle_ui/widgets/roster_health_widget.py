"""
RosterHealthWidget - Displays position group health bars with grades.

Shows roster strength at each position group with:
- Progress bars colored by grade (A-F)
- Warning indicators for expiring contracts
- Click-to-filter functionality

Usage:
    from game_cycle_ui.widgets import RosterHealthWidget

    widget = RosterHealthWidget()
    widget.position_clicked.connect(on_position_filter)
    widget.update_scores(players, expiring_ids)
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QGroupBox, QGridLayout, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from game_cycle_ui.theme import Colors, Typography, FontSizes
from utils.player_field_extractors import extract_primary_position, extract_overall_rating


# Position group definitions
POSITION_GROUPS = {
    "QB": ["quarterback", "qb"],
    "RB": ["running_back", "rb", "fullback", "fb"],
    "WR": ["wide_receiver", "wr"],
    "TE": ["tight_end", "te"],
    "OL": ["left_tackle", "lt", "left_guard", "lg", "center", "c",
           "right_guard", "rg", "right_tackle", "rt", "offensive_line", "ol",
           "offensive_guard", "og", "offensive_tackle", "ot", "tackle", "guard"],
    "DL": ["defensive_end", "de", "defensive_tackle", "dt", "nose_tackle", "nt",
           "edge", "defensive_line", "dl", "left_end", "le", "right_end", "re"],
    "LB": ["linebacker", "lb", "middle_linebacker", "mlb", "inside_linebacker", "ilb",
           "outside_linebacker", "olb", "mike_linebacker", "mike", "will_linebacker", "will",
           "sam_linebacker", "sam", "weak_side_linebacker", "strong_side_linebacker",
           "lolb", "rolb"],
    "DB": ["cornerback", "cb", "nickel_cornerback", "ncb", "safety", "s",
           "free_safety", "fs", "strong_safety", "ss", "defensive_back", "db"],
    "ST": ["kicker", "k", "punter", "p", "long_snapper", "ls",
           "kick_returner", "kr", "punt_returner", "pr"],
}

# Filter values for each position group (used when clicking)
POSITION_FILTER_VALUES = {
    "QB": "quarterback",
    "RB": "running_back",
    "WR": "wide_receiver",
    "TE": "tight_end",
    "OL": None,  # Multiple positions - clear filter
    "DL": None,
    "LB": None,
    "DB": None,
    "ST": None,
}

# Recommended depth for position groups
RECOMMENDED_DEPTH = {
    "QB": 3,
    "RB": 5,  # RB + FB
    "WR": 6,
    "TE": 3,
    "OL": 10,  # 5 starters + 5 backups
    "DL": 8,   # 4 starters + 4 backups
    "LB": 7,   # 3-4 starters + backups
    "DB": 9,   # 4-5 starters + backups
    "ST": 3,   # K, P, LS
}


@dataclass
class PositionGroupScore:
    """Score data for a position group."""
    score: float
    grade: str
    starter_ovr: int
    depth_count: int
    expiring_count: int


def normalize_position(pos: str) -> str:
    """Normalize position string for comparison."""
    if not pos:
        return ""
    return pos.lower().replace(" ", "_").replace("-", "_")


def get_position_group(position: str) -> Optional[str]:
    """Get the position group for a given position."""
    norm_pos = normalize_position(position)
    for group, positions in POSITION_GROUPS.items():
        if norm_pos in positions:
            return group
    return None


def score_to_grade(score: float) -> str:
    """Convert numeric score (0-100) to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 85:
        return "A-"
    elif score >= 80:
        return "B+"
    elif score >= 75:
        return "B"
    elif score >= 70:
        return "B-"
    elif score >= 65:
        return "C+"
    elif score >= 60:
        return "C"
    elif score >= 55:
        return "C-"
    elif score >= 50:
        return "D"
    else:
        return "F"


def grade_to_color(grade: str) -> str:
    """Get color hex value for a grade."""
    if grade in ("A", "A-"):
        return Colors.SUCCESS  # Green
    elif grade in ("B+", "B", "B-"):
        return Colors.INFO  # Blue
    elif grade in ("C+", "C", "C-"):
        return Colors.WARNING  # Orange
    else:  # D, F
        return Colors.ERROR  # Red


class RosterHealthWidget(QGroupBox):
    """
    Widget displaying position group health with progress bars and grades.

    Shows each position group (QB, RB, WR, etc.) with:
    - Progress bar showing relative strength (0-100)
    - Letter grade (A-F)
    - Warning indicator for expiring contracts

    Signals:
        position_clicked(str): Emitted when a position row is clicked.
                              Value is the position filter string or empty for "all".
    """

    position_clicked = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Roster Needs", parent)
        self._scores: Dict[str, PositionGroupScore] = {}
        self._bars: Dict[str, QProgressBar] = {}
        self._grade_labels: Dict[str, QLabel] = {}
        self._expiring_labels: Dict[str, QLabel] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Build the widget layout."""
        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 12, 12, 12)

        # Create rows for each position group
        groups = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "ST"]

        for row, group in enumerate(groups):
            # Position label (clickable)
            pos_label = QLabel(group)
            pos_label.setFixedWidth(30)
            pos_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: bold;")
            pos_label.setCursor(QCursor(Qt.PointingHandCursor))
            pos_label.mousePressEvent = lambda e, g=group: self._on_position_clicked(g)
            layout.addWidget(pos_label, row, 0)

            # Progress bar
            bar = QProgressBar()
            bar.setMinimum(0)
            bar.setMaximum(100)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(16)
            bar.setStyleSheet(self._get_bar_style(Colors.INFO))
            bar.setCursor(QCursor(Qt.PointingHandCursor))
            bar.mousePressEvent = lambda e, g=group: self._on_position_clicked(g)
            self._bars[group] = bar
            layout.addWidget(bar, row, 1)

            # Grade label
            grade_label = QLabel("--")
            grade_label.setFixedWidth(30)
            grade_label.setAlignment(Qt.AlignCenter)
            grade_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: bold;")
            self._grade_labels[group] = grade_label
            layout.addWidget(grade_label, row, 2)

            # Expiring indicator
            expiring_label = QLabel("")
            expiring_label.setFixedWidth(80)
            expiring_label.setStyleSheet(f"color: {Colors.WARNING}; font-size: {FontSizes.SMALL};")
            self._expiring_labels[group] = expiring_label
            layout.addWidget(expiring_label, row, 3)

        # Set column stretch
        layout.setColumnStretch(1, 1)  # Progress bar column stretches

    def _get_bar_style(self, color: str) -> str:
        """Generate progress bar stylesheet with given color."""
        return f"""
            QProgressBar {{
                background-color: #2a2a2a;
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """

    def _on_position_clicked(self, group: str):
        """Handle click on a position row."""
        filter_value = POSITION_FILTER_VALUES.get(group, "")
        self.position_clicked.emit(filter_value or "")

    def update_scores(
        self,
        players: List[Dict],
        expiring_ids: Set[int]
    ):
        """
        Update all position group scores based on roster data.

        Args:
            players: List of player dictionaries with keys:
                     - player_id (int)
                     - position (str) OR positions (JSON array)
                     - overall (int) OR attributes (JSON with overall)
            expiring_ids: Set of player IDs with expiring contracts
        """
        # Group players by position group
        grouped: Dict[str, List[Dict]] = {g: [] for g in POSITION_GROUPS}

        for player in players:
            # Handle both "position" (string) and "positions" (JSON array)
            position = player.get("position", "")
            if not position:
                position = extract_primary_position(player.get("positions", []))

            # Handle "overall" from either direct field or nested in "attributes"
            overall = extract_overall_rating(player, default=0)

            # Create normalized player dict for scoring
            normalized_player = {
                "player_id": player.get("player_id"),
                "position": position,
                "overall": overall
            }

            group = get_position_group(position)
            if group:
                grouped[group].append(normalized_player)

        # Calculate scores for each group
        for group, group_players in grouped.items():
            score_data = self._calculate_group_score(group, group_players, expiring_ids)
            self._scores[group] = score_data
            self._update_group_display(group, score_data)

    def _calculate_group_score(
        self,
        group: str,
        players: List[Dict],
        expiring_ids: Set[int]
    ) -> PositionGroupScore:
        """
        Calculate the score for a position group.

        Scoring formula:
        - Starter quality (40%): Best player's overall rating
        - Depth quality (30%): Average overall of backup players
        - Depth count (20%): Number of players vs recommended
        - Stability (10%): Penalty if top players are expiring
        """
        if not players:
            return PositionGroupScore(
                score=0.0, grade="F", starter_ovr=0,
                depth_count=0, expiring_count=0
            )

        # Sort by overall (best first)
        sorted_players = sorted(players, key=lambda p: extract_overall_rating(p, default=0), reverse=True)

        # Starter quality (40%)
        starter_ovr = extract_overall_rating(sorted_players[0], default=0)
        starter_score = starter_ovr

        # Depth quality (30%)
        backups = sorted_players[1:] if len(sorted_players) > 1 else []
        if backups:
            depth_avg = sum(extract_overall_rating(p, default=0) for p in backups) / len(backups)
        else:
            depth_avg = 0

        # Depth count (20%)
        recommended = RECOMMENDED_DEPTH.get(group, 3)
        depth_ratio = min(len(players) / recommended, 1.0)
        depth_count_score = depth_ratio * 100

        # Stability (10%) - penalty for expiring contracts in top 2
        top_players = sorted_players[:2]
        expiring_count = sum(
            1 for p in sorted_players
            if p.get("player_id") in expiring_ids
        )
        expiring_top = sum(
            1 for p in top_players
            if p.get("player_id") in expiring_ids
        )
        stability_penalty = expiring_top * 10  # 10 points per expiring top player
        stability_score = max(0, 100 - stability_penalty)

        # Calculate weighted score
        total_score = (
            (starter_score * 0.40) +
            (depth_avg * 0.30) +
            (depth_count_score * 0.20) +
            (stability_score * 0.10)
        )

        return PositionGroupScore(
            score=total_score,
            grade=score_to_grade(total_score),
            starter_ovr=starter_ovr,
            depth_count=len(players),
            expiring_count=expiring_count
        )

    def _update_group_display(self, group: str, score_data: PositionGroupScore):
        """Update the display for a single position group."""
        # Update progress bar
        bar = self._bars.get(group)
        if bar:
            bar.setValue(int(score_data.score))
            color = grade_to_color(score_data.grade)
            bar.setStyleSheet(self._get_bar_style(color))

        # Update grade label
        grade_label = self._grade_labels.get(group)
        if grade_label:
            grade_label.setText(score_data.grade)
            color = grade_to_color(score_data.grade)
            grade_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        # Update expiring indicator
        expiring_label = self._expiring_labels.get(group)
        if expiring_label:
            if score_data.expiring_count > 0:
                expiring_label.setText(f"⚠ {score_data.expiring_count} expiring")
            else:
                expiring_label.setText("")

    def get_score(self, group: str) -> Optional[PositionGroupScore]:
        """Get the score data for a specific position group."""
        return self._scores.get(group)

    def get_all_scores(self) -> Dict[str, PositionGroupScore]:
        """Get all position group scores."""
        return self._scores.copy()

    def clear(self):
        """Reset all displays to default state."""
        for group in POSITION_GROUPS:
            bar = self._bars.get(group)
            if bar:
                bar.setValue(0)
                bar.setStyleSheet(self._get_bar_style(Colors.TEXT_SECONDARY))

            grade_label = self._grade_labels.get(group)
            if grade_label:
                grade_label.setText("--")
                grade_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: bold;")

            expiring_label = self._expiring_labels.get(group)
            if expiring_label:
                expiring_label.setText("")

        self._scores.clear()
