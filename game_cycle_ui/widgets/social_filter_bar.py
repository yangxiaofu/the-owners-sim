"""
SocialFilterBar - Filter controls for social media feed.

Part of Milestone 14: Social Media & Fan Reactions, Tollgate 6.

Provides filtering controls for the social feed:
- Team dropdown (filter by team)
- Event type dropdown (GAME_RESULT, TRADE, AWARD, etc.)
- Sentiment filter (All, Positive, Negative, Neutral)

Emits signals when filters change to trigger feed refresh.
"""

from typing import Optional, List, Callable

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
)
from PySide6.QtCore import Signal

from game_cycle.models.social_event_types import SocialEventType, SocialSentiment


# ESPN-style colors (dark theme)
ESPN_PRIMARY = "#2E7D32"        # Green button (keep)
ESPN_TEXT_PRIMARY = "#FFFFFF"   # Primary text
ESPN_TEXT_SECONDARY = "#888888" # Secondary text
ESPN_BORDER = "#333333"         # Borders
ESPN_BG = "#1a1a1a"            # Background


class SocialFilterBar(QWidget):
    """
    Filter controls bar for social feed.

    Provides dropdowns for filtering posts by:
    - Team
    - Event type
    - Sentiment

    Signals:
        filter_changed: Emitted when any filter changes (team_id, event_type, sentiment)
    """

    filter_changed = Signal(int, str, str)  # (team_id, event_type, sentiment)

    def __init__(
        self,
        teams_data: List[dict],
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the filter bar.

        Args:
            teams_data: List of team dicts with 'id' and 'abbreviation'
            parent: Parent widget
        """
        super().__init__(parent)
        self._teams_data = teams_data
        self._setup_ui()

    def _setup_ui(self):
        """Build the filter bar UI."""
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(16)

        # Title label
        title = QLabel("Filters:")
        title.setStyleSheet(f"""
            QLabel {{
                color: {ESPN_TEXT_PRIMARY};
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(title)

        # Team filter
        self._team_combo = self._create_filter_combo(
            label="Team:",
            items=self._get_team_items(),
            default_text="All Teams"
        )
        self._team_combo.currentIndexChanged.connect(self._on_filter_change)
        layout.addWidget(self._team_combo)

        # Event type filter
        self._event_type_combo = self._create_filter_combo(
            label="Type:",
            items=self._get_event_type_items(),
            default_text="All Events"
        )
        self._event_type_combo.currentIndexChanged.connect(self._on_filter_change)
        layout.addWidget(self._event_type_combo)

        # Sentiment filter
        self._sentiment_combo = self._create_filter_combo(
            label="Sentiment:",
            items=self._get_sentiment_items(),
            default_text="All"
        )
        self._sentiment_combo.currentIndexChanged.connect(self._on_filter_change)
        layout.addWidget(self._sentiment_combo)

        # Clear filters button
        clear_btn = QPushButton("Clear Filters")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ESPN_PRIMARY};
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #1B5E20;
            }}
        """)
        clear_btn.clicked.connect(self._clear_filters)
        layout.addWidget(clear_btn)

        # Spacer to push everything left
        layout.addStretch()

    def _create_filter_combo(
        self,
        label: str,
        items: List[tuple],
        default_text: str
    ) -> QComboBox:
        """
        Create a labeled filter combo box.

        Args:
            label: Label text (e.g., "Team:")
            items: List of (display_text, value) tuples
            default_text: Default "All" option text

        Returns:
            Configured QComboBox
        """
        combo = QComboBox()

        # Add default "All" option
        combo.addItem(default_text, None)

        # Add items
        for display_text, value in items:
            combo.addItem(display_text, value)

        # Style combo box
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {ESPN_BG};
                color: {ESPN_TEXT_PRIMARY};
                border: 1px solid {ESPN_BORDER};
                border-radius: 3px;
                padding: 4px 8px;
                min-width: 120px;
                font-size: 12px;
            }}
            QComboBox:hover {{
                border-color: {ESPN_TEXT_SECONDARY};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {ESPN_BG};
                color: {ESPN_TEXT_PRIMARY};
                border: 1px solid {ESPN_BORDER};
                selection-background-color: #2a2a2a;
                selection-color: {ESPN_TEXT_PRIMARY};
            }}
        """)

        return combo

    def _get_team_items(self) -> List[tuple]:
        """
        Get team filter items.

        Returns:
            List of (display_text, team_id) tuples
        """
        # Sort teams by abbreviation
        sorted_teams = sorted(self._teams_data, key=lambda t: t.get('abbreviation', ''))

        return [
            (f"{team.get('abbreviation', 'UNK')}", team.get('id'))
            for team in sorted_teams
        ]

    def _get_event_type_items(self) -> List[tuple]:
        """
        Get event type filter items.

        Returns:
            List of (display_text, event_type_enum_value) tuples
        """
        return [
            ("Game Results", SocialEventType.GAME_RESULT.value),
            ("Trades", SocialEventType.TRADE.value),
            ("Signings", SocialEventType.SIGNING.value),
            ("Awards", SocialEventType.AWARD.value),
            ("Draft", SocialEventType.DRAFT_PICK.value),
            ("Cuts", SocialEventType.CUT.value),
            ("Injuries", SocialEventType.INJURY.value),
        ]

    def _get_sentiment_items(self) -> List[tuple]:
        """
        Get sentiment filter items.

        Returns:
            List of (display_text, sentiment_enum_value) tuples
        """
        return [
            ("Positive", SocialSentiment.POSITIVE.value),
            ("Negative", SocialSentiment.NEGATIVE.value),
            ("Neutral", SocialSentiment.NEUTRAL.value),
        ]

    def _on_filter_change(self):
        """Handle filter change event."""
        # Get current filter values
        team_id = self._team_combo.currentData()
        event_type = self._event_type_combo.currentData()
        sentiment = self._sentiment_combo.currentData()

        # Emit signal with filter values (None = no filter)
        self.filter_changed.emit(
            team_id if team_id is not None else 0,  # 0 = all teams
            event_type if event_type is not None else "ALL",
            sentiment if sentiment is not None else "ALL"
        )

    def _clear_filters(self):
        """Reset all filters to default (All)."""
        self._team_combo.setCurrentIndex(0)
        self._event_type_combo.setCurrentIndex(0)
        self._sentiment_combo.setCurrentIndex(0)

    def get_current_filters(self) -> dict:
        """
        Get current filter values.

        Returns:
            Dict with 'team_id', 'event_type', 'sentiment' keys
        """
        return {
            'team_id': self._team_combo.currentData(),
            'event_type': self._event_type_combo.currentData(),
            'sentiment': self._sentiment_combo.currentData(),
        }

    def set_filters(self, team_id: Optional[int] = None, event_type: Optional[str] = None, sentiment: Optional[str] = None):
        """
        Programmatically set filter values.

        Args:
            team_id: Team ID to filter by (None = no filter)
            event_type: Event type to filter by (None = no filter)
            sentiment: Sentiment to filter by (None = no filter)
        """
        # Set team filter
        if team_id is not None:
            for i in range(self._team_combo.count()):
                if self._team_combo.itemData(i) == team_id:
                    self._team_combo.setCurrentIndex(i)
                    break

        # Set event type filter
        if event_type is not None:
            for i in range(self._event_type_combo.count()):
                if self._event_type_combo.itemData(i) == event_type:
                    self._event_type_combo.setCurrentIndex(i)
                    break

        # Set sentiment filter
        if sentiment is not None:
            for i in range(self._sentiment_combo.count()):
                if self._sentiment_combo.itemData(i) == sentiment:
                    self._sentiment_combo.setCurrentIndex(i)
                    break
