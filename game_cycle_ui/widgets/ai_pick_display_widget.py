"""
AI Pick Display Widget - Shows detailed draft pick information for AI teams.

Part of Draft View enhancement - provides rich display when watching AI teams
make their selections, showing player details, team needs, and GM reasoning.

Layout:
┌─────────────────────────────────────────────────────────────┐
│                     TEAM HEADER                             │
│        "With the 15th pick in the 2025 NFL Draft,          │
│              the Dallas Cowboys select..."                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐                                                │
│  │  Photo  │   JOHN SMITH                                   │
│  │ Placeholder│   Quarterback • Alabama                    │
│  │         │                                                │
│  └─────────┘   Overall: 85 ████████░░ (green color)        │
├─────────────────────────────────────────────────────────────┤
│  FILLS NEEDS AT: QB (Critical), WR (High)                  │
├─────────────────────────────────────────────────────────────┤
│  GM REASONING:                                              │
│  "Addresses critical need at quarterback with the best     │
│  available talent. Strong arm and leadership qualities."   │
└─────────────────────────────────────────────────────────────┘
"""

import logging
from typing import Dict, Any, Optional, List
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QProgressBar,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from game_cycle_ui.theme import (
    Colors,
    Typography,
    FontSizes,
    TextColors,
    RatingColorizer,
    ESPN_THEME,
)
from utils.player_field_extractors import extract_overall_rating

logger = logging.getLogger(__name__)


class AIPickDisplayWidget(QWidget):
    """
    Rich display widget for AI team draft picks.

    Shows comprehensive pick information:
    - Team header with pick context
    - Player card with photo placeholder, name, position, college
    - Visual rating display with color coding
    - Position needs met
    - GM reasoning text

    Designed for viewing AI selections during draft process.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the AI pick display widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._current_data: Optional[Dict[str, Any]] = None
        self._setup_ui()

    def _setup_ui(self):
        """Build the widget UI structure."""
        # Main container with ESPN card styling
        self.setStyleSheet(f"""
            AIPickDisplayWidget {{
                background-color: {ESPN_THEME['card_bg']};
                border: 2px solid {ESPN_THEME['border']};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Team header section
        self.team_header = QLabel()
        self.team_header.setWordWrap(True)
        self.team_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.team_header.setFont(Typography.H3)
        self.team_header.setStyleSheet(f"""
            color: {TextColors.ON_DARK};
            padding: 12px;
            background-color: {Colors.INFO_DARK};
            border-radius: 6px;
        """)
        layout.addWidget(self.team_header)

        # Separator line
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setStyleSheet(f"background-color: {ESPN_THEME['border']};")
        separator1.setFixedHeight(2)
        layout.addWidget(separator1)

        # Player card section (photo + details)
        player_card = self._create_player_card()
        layout.addWidget(player_card)

        # Separator line
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet(f"background-color: {ESPN_THEME['border']};")
        separator2.setFixedHeight(2)
        layout.addWidget(separator2)

        # Needs met section
        needs_container = QWidget()
        needs_layout = QVBoxLayout(needs_container)
        needs_layout.setContentsMargins(0, 0, 0, 0)
        needs_layout.setSpacing(8)

        needs_title = QLabel("FILLS NEEDS AT:")
        needs_title.setFont(Typography.CAPTION_BOLD)
        needs_title.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY};")
        needs_layout.addWidget(needs_title)

        self.needs_label = QLabel()
        self.needs_label.setWordWrap(True)
        self.needs_label.setFont(Typography.BODY)
        self.needs_label.setStyleSheet(f"color: {TextColors.ON_DARK}; padding-left: 8px;")
        needs_layout.addWidget(self.needs_label)

        layout.addWidget(needs_container)

        # Separator line
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.HLine)
        separator3.setStyleSheet(f"background-color: {ESPN_THEME['border']};")
        separator3.setFixedHeight(2)
        layout.addWidget(separator3)

        # GM reasoning section
        reasoning_container = QWidget()
        reasoning_layout = QVBoxLayout(reasoning_container)
        reasoning_layout.setContentsMargins(0, 0, 0, 0)
        reasoning_layout.setSpacing(8)

        reasoning_title = QLabel("GM REASONING:")
        reasoning_title.setFont(Typography.CAPTION_BOLD)
        reasoning_title.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY};")
        reasoning_layout.addWidget(reasoning_title)

        self.reasoning_label = QLabel()
        self.reasoning_label.setWordWrap(True)
        self.reasoning_label.setFont(Typography.BODY)
        self.reasoning_label.setStyleSheet(f"""
            color: {TextColors.ON_DARK};
            font-style: italic;
            padding-left: 8px;
        """)
        reasoning_layout.addWidget(self.reasoning_label)

        layout.addWidget(reasoning_container)

        layout.addStretch()

        # Initially hide until data is set
        self.hide()

    def _create_player_card(self) -> QWidget:
        """
        Create the player information card section.

        Returns:
            Widget containing player photo, name, position, college, and rating
        """
        card = QWidget()
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(0, 8, 0, 8)
        card_layout.setSpacing(16)

        # Photo placeholder (left side)
        photo_container = QFrame()
        photo_container.setFixedSize(100, 100)
        photo_container.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {ESPN_THEME['card_bg']},
                    stop:0.5 #2a2a2a,
                    stop:1 {ESPN_THEME['card_bg']}
                );
                border: 3px solid {ESPN_THEME['border']};
                border-radius: 50px;
            }}
        """)

        photo_layout = QVBoxLayout(photo_container)
        photo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        photo_icon = QLabel("👤")
        photo_icon.setFont(QFont(Typography.FAMILY, 36))
        photo_icon.setStyleSheet("background: transparent; border: none;")
        photo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        photo_layout.addWidget(photo_icon)

        card_layout.addWidget(photo_container)

        # Player details (right side)
        details = QWidget()
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(6)

        # Player name
        self.player_name_label = QLabel()
        self.player_name_label.setFont(Typography.H2)
        self.player_name_label.setStyleSheet(f"color: {TextColors.ON_DARK}; font-weight: bold;")
        details_layout.addWidget(self.player_name_label)

        # Position and college
        self.position_college_label = QLabel()
        self.position_college_label.setFont(Typography.BODY)
        self.position_college_label.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY};")
        details_layout.addWidget(self.position_college_label)

        details_layout.addSpacing(8)

        # Rating display with progress bar
        rating_container = QWidget()
        rating_layout = QHBoxLayout(rating_container)
        rating_layout.setContentsMargins(0, 0, 0, 0)
        rating_layout.setSpacing(12)

        self.rating_text_label = QLabel()
        self.rating_text_label.setFont(Typography.BODY_BOLD)
        rating_layout.addWidget(self.rating_text_label)

        self.rating_bar = QProgressBar()
        self.rating_bar.setFixedWidth(150)
        self.rating_bar.setFixedHeight(20)
        self.rating_bar.setMinimum(0)
        self.rating_bar.setMaximum(99)
        self.rating_bar.setTextVisible(False)
        rating_layout.addWidget(self.rating_bar)

        rating_layout.addStretch()

        details_layout.addWidget(rating_container)
        details_layout.addStretch()

        card_layout.addWidget(details, stretch=1)

        return card

    def set_pick_data(self, pick_data: Dict[str, Any]):
        """
        Update the display with new draft pick data.

        Args:
            pick_data: Dictionary containing:
                - team_name: str (e.g., "Dallas Cowboys")
                - team_id: int (1-32)
                - pick_number: int (overall pick number, 1-224)
                - round: int (1-7)
                - pick_in_round: int (1-32)
                - prospect_name: str
                - position: str (e.g., "QB", "WR")
                - college: str
                - overall: int (rating 0-99)
                - needs_met: List[str] (positions this pick fills)
                - reasoning: str (GM's draft reasoning)
        """
        self._current_data = pick_data

        # Extract data with defaults
        team_name = pick_data.get("team_name", "Unknown Team")
        pick_number = pick_data.get("pick_number", 0)
        round_num = pick_data.get("round", 0)
        pick_in_round = pick_data.get("pick_in_round", 0)
        prospect_name = pick_data.get("prospect_name", "Unknown Player")
        position = pick_data.get("position", "").upper()
        college = pick_data.get("college", "Unknown College")
        overall = extract_overall_rating(pick_data, default=0)
        needs_met = pick_data.get("needs_met", [])
        reasoning = pick_data.get("reasoning", "No reasoning provided.")

        # Build ordinal suffix for pick number
        ordinal = self._get_ordinal_suffix(pick_number)

        # Update team header
        header_text = (
            f"With the {pick_number}{ordinal} pick in the 2025 NFL Draft,\n"
            f"the {team_name} select..."
        )
        self.team_header.setText(header_text)

        # Update player details
        self.player_name_label.setText(prospect_name.upper())
        self.position_college_label.setText(f"{position} • {college}")

        # Update rating display with color coding
        rating_color = RatingColorizer.get_color_for_rating(overall)
        self.rating_text_label.setText(f"Overall: {overall}")
        self.rating_text_label.setStyleSheet(f"color: {rating_color};")

        # Update rating bar
        self.rating_bar.setValue(overall)
        self.rating_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 4px;
                background-color: {ESPN_THEME['dark_bg']};
            }}
            QProgressBar::chunk {{
                background-color: {rating_color};
                border-radius: 3px;
            }}
        """)

        # Update needs met
        if needs_met:
            needs_text = self._format_needs_met(needs_met)
            self.needs_label.setText(needs_text)
        else:
            self.needs_label.setText("No specific needs identified")

        # Update reasoning
        self.reasoning_label.setText(f'"{reasoning}"')

        # Show the widget now that it has data
        self.show()

    def _format_needs_met(self, needs: List[str]) -> str:
        """
        Format the list of needs met into display text.

        Args:
            needs: List of position strings (e.g., ["QB", "WR"])

        Returns:
            Formatted string (e.g., "QB (Critical), WR (High)")
        """
        if not needs:
            return "None"

        # Priority labels based on position in list (first = most critical)
        priority_labels = ["Critical", "High", "Moderate", "Low"]

        formatted_needs = []
        for i, need in enumerate(needs):
            priority = priority_labels[min(i, len(priority_labels) - 1)]
            formatted_needs.append(f"{need.upper()} ({priority})")

        return ", ".join(formatted_needs)

    def _get_ordinal_suffix(self, number: int) -> str:
        """
        Get ordinal suffix for a number (st, nd, rd, th).

        Args:
            number: Integer to get suffix for

        Returns:
            Ordinal suffix string

        Examples:
            >>> _get_ordinal_suffix(1)
            'st'
            >>> _get_ordinal_suffix(2)
            'nd'
            >>> _get_ordinal_suffix(23)
            'rd'
            >>> _get_ordinal_suffix(11)
            'th'
        """
        if 10 <= number % 100 <= 20:
            return "th"
        else:
            suffix_map = {1: "st", 2: "nd", 3: "rd"}
            return suffix_map.get(number % 10, "th")

    def clear(self):
        """Clear all display data and hide the widget."""
        self._current_data = None
        self.team_header.setText("")
        self.player_name_label.setText("")
        self.position_college_label.setText("")
        self.rating_text_label.setText("")
        self.rating_bar.setValue(0)
        self.needs_label.setText("")
        self.reasoning_label.setText("")
        self.hide()

    def get_current_data(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently displayed pick data.

        Returns:
            Current pick data dictionary or None if no data
        """
        return self._current_data
