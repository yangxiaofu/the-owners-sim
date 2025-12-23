"""
League Leaders Widget - Displays top statistical leaders across multiple categories.

Shows top 5 players in 8 key statistical categories organized in a 2x4 grid.
"""

from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea
)
from PySide6.QtCore import Qt

from game_cycle_ui.theme import ESPN_THEME, Colors, Typography, FontSizes, TextColors


class LeagueLeadersWidget(QWidget):
    """Widget displaying league statistical leaders in multiple categories."""

    # Category configuration: (display_title, data_key, stat_suffix)
    CATEGORIES = [
        # Row 1
        ("Passing Yards", "passing_yards", "YDS"),
        ("Passing TDs", "passing_tds", "TD"),
        ("Rushing Yards", "rushing_yards", "YDS"),
        ("Rushing TDs", "rushing_tds", "TD"),
        # Row 2
        ("Receiving Yards", "receiving_yards", "YDS"),
        ("Receptions", "receptions", "REC"),
        ("Sacks", "sacks", "SCK"),
        ("Interceptions", "interceptions", "INT"),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the league leaders widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._category_cards: Dict[str, QFrame] = {}
        self._category_containers: Dict[str, QVBoxLayout] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area for the content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"background-color: {ESPN_THEME['dark_bg']};")

        # Content widget
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # Title
        title = QLabel("League Leaders")
        title.setFont(Typography.H2)
        title.setStyleSheet(f"color: white; padding-bottom: 10px;")
        content_layout.addWidget(title)

        # Grid layout for categories (2 rows x 4 columns)
        grid = QGridLayout()
        grid.setSpacing(16)

        # Create category cards
        for idx, (title, key, suffix) in enumerate(self.CATEGORIES):
            row = idx // 4
            col = idx % 4
            card = self._create_category_card(title, key, suffix)
            self._category_cards[key] = card
            grid.addWidget(card, row, col)

        content_layout.addLayout(grid)
        content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _create_category_card(self, title: str, key: str, suffix: str) -> QFrame:
        """Create a category card for displaying leaders.

        Args:
            title: Display title for the category
            key: Data key for this category
            suffix: Stat suffix (e.g., 'YDS', 'TD')

        Returns:
            QFrame containing the category card
        """
        # Card frame
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_THEME['card_bg']};
                border-radius: 8px;
                border: 1px solid {ESPN_THEME['border']};
            }}
        """)

        # Card layout
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        # Header
        header = QLabel(title)
        header.setFont(Typography.H5)
        header.setStyleSheet(f"color: {ESPN_THEME['text_muted']}; border: none;")
        card_layout.addWidget(header)

        # Container for player entries
        entries_container = QVBoxLayout()
        entries_container.setSpacing(8)
        self._category_containers[key] = entries_container

        card_layout.addLayout(entries_container)
        card_layout.addStretch()

        # Store suffix for formatting
        card.setProperty("stat_suffix", suffix)

        return card

    def _create_player_entry(self, rank: int, player_data: Dict, suffix: str) -> QWidget:
        """Create a single player entry widget.

        Args:
            rank: Player's rank (1-5)
            player_data: Player data dict with 'name', 'team', 'value'
            suffix: Stat suffix for display

        Returns:
            QWidget containing the player entry
        """
        entry = QWidget()
        entry_layout = QHBoxLayout(entry)
        entry_layout.setContentsMargins(0, 4, 0, 4)
        entry_layout.setSpacing(8)

        # Rank
        rank_label = QLabel(f"{rank}.")
        rank_label.setFont(Typography.CAPTION_BOLD)
        rank_label.setStyleSheet(f"color: {ESPN_THEME['text_muted']}; min-width: 20px;")
        rank_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        entry_layout.addWidget(rank_label)

        # Player name
        name_label = QLabel(player_data.get('name', 'Unknown'))
        name_label.setFont(Typography.CAPTION)
        name_label.setStyleSheet("color: white;")
        entry_layout.addWidget(name_label, 1)

        # Team abbreviation
        team_label = QLabel(player_data.get('team', ''))
        team_label.setFont(Typography.SMALL)
        team_label.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
        entry_layout.addWidget(team_label)

        # Stat value
        value = player_data.get('value', 0)
        value_text = f"{value:,}" if isinstance(value, int) else f"{value:.1f}"
        value_label = QLabel(value_text)
        value_label.setFont(Typography.CAPTION_BOLD)
        value_label.setStyleSheet(f"color: {Colors.SUCCESS}; min-width: 60px;")
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        entry_layout.addWidget(value_label)

        return entry

    def _update_category(self, key: str, players: List[Dict]) -> None:
        """Update a specific category with player data.

        Args:
            key: Category key
            players: List of player dicts (up to 5)
        """
        if key not in self._category_containers:
            return

        container = self._category_containers[key]
        card = self._category_cards[key]
        suffix = card.property("stat_suffix")

        # Clear existing entries
        while container.count():
            item = container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add new entries (top 5)
        for idx, player_data in enumerate(players[:5], start=1):
            entry = self._create_player_entry(idx, player_data, suffix)
            container.addWidget(entry)

        # Add placeholder if fewer than 5
        for idx in range(len(players), 5):
            placeholder = QWidget()
            placeholder.setFixedHeight(28)
            container.addWidget(placeholder)

    def set_leaders(self, leaders: Dict[str, List[Dict]]) -> None:
        """Set the league leaders data.

        Args:
            leaders: Dict mapping category keys to lists of player dicts.
                    Each player dict should have 'name', 'team', 'value' keys.
                    Example:
                    {
                        'passing_yards': [
                            {'name': 'J. Goff', 'team': 'DET', 'value': 4200},
                            ...
                        ],
                        ...
                    }
        """
        for key in self._category_containers.keys():
            player_list = leaders.get(key, [])
            self._update_category(key, player_list)

    def clear(self) -> None:
        """Clear all league leaders data."""
        for key in self._category_containers.keys():
            self._update_category(key, [])
