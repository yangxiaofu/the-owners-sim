"""
Team Gallery Widget - Visual team selection with conference tabs.

Displays 32 NFL teams organized by division with AFC/NFC tab navigation.
Each team is shown as a colored card with team abbreviation and city.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QGroupBox, QTabWidget
)
from PySide6.QtCore import Qt, Signal

from game_cycle_ui.theme import Colors, Typography, FontSizes, TextColors


class TeamCard(QFrame):
    """
    Clickable card for a single team.

    Displays team abbreviation and city on a background
    colored with the team's primary color.
    """
    clicked = Signal(int)  # Emits team_id when clicked

    def __init__(self, team_data: dict, parent=None):
        """
        Initialize team card.

        Args:
            team_data: Dict with team_id, abbreviation, city, colors
            parent: Parent widget
        """
        super().__init__(parent)
        self.team_id = team_data['team_id']
        self._primary_color = team_data['colors'].get('primary', '#333333')
        self._selected = False
        self._setup_ui(team_data)

    def _setup_ui(self, team: dict):
        """Build the card UI."""
        self.setFixedSize(130, 80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_stylesheet()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Abbreviation (large, centered)
        abbr_label = QLabel(team['abbreviation'])
        abbr_label.setFont(Typography.H3)
        abbr_label.setStyleSheet("color: white; background: transparent;")
        abbr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(abbr_label)

        # City (small, centered)
        city_label = QLabel(team['city'])
        city_label.setFont(Typography.SMALL)
        city_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); background: transparent;")
        city_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(city_label)

    def _update_stylesheet(self):
        """Update the card's stylesheet based on selection state."""
        border = "3px solid #FFD700" if self._selected else "2px solid rgba(255,255,255,0.2)"
        self.setStyleSheet(f"""
            TeamCard {{
                background-color: {self._primary_color};
                border: {border};
                border-radius: 8px;
            }}
            TeamCard:hover {{
                border: 3px solid #FFD700;
            }}
        """)

    def set_selected(self, selected: bool):
        """
        Set the selection state of this card.

        Args:
            selected: True to show as selected (gold border)
        """
        self._selected = selected
        self._update_stylesheet()

    def mousePressEvent(self, event):
        """Handle mouse click - emit clicked signal."""
        self.clicked.emit(self.team_id)
        super().mousePressEvent(event)


class TeamGalleryWidget(QWidget):
    """
    Tabbed team selection with AFC/NFC conference tabs.

    Layout:
    - Tab bar with AFC / NFC tabs
    - Each tab shows 4 divisions (East, North, South, West) in columns
    - Each division column contains 4 team cards vertically

    Signals:
        team_selected(int): Emitted when a team card is clicked
    """
    team_selected = Signal(int)  # Emits team_id

    # Tab styling for conference tabs
    TAB_STYLE = """
        QTabWidget::pane {
            border: none;
            background: #2a2a2a;
            border-radius: 8px;
        }
        QTabBar::tab {
            background: #333333;
            color: #888888;
            padding: 10px 40px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 4px;
            font-weight: bold;
            font-size: 14px;
        }
        QTabBar::tab:selected {
            background: #2a2a2a;
            color: #FFFFFF;
        }
        QTabBar::tab:hover:!selected {
            background: #3a3a3a;
            color: #CCCCCC;
        }
    """

    def __init__(self, team_loader, parent=None):
        """
        Initialize team gallery.

        Args:
            team_loader: TeamDataLoader instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.team_loader = team_loader
        self._cards = {}  # team_id -> TeamCard
        self._selected_team_id = None
        self._setup_ui()

    def _setup_ui(self):
        """Build the gallery UI with conference tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget for AFC/NFC
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(self.TAB_STYLE)

        # Create AFC and NFC tabs
        afc_widget = self._create_conference_widget('AFC')
        nfc_widget = self._create_conference_widget('NFC')

        self.tab_widget.addTab(afc_widget, "AFC")
        self.tab_widget.addTab(nfc_widget, "NFC")

        layout.addWidget(self.tab_widget)

    def _create_conference_widget(self, conference: str) -> QWidget:
        """
        Create a widget showing all 4 divisions for a conference.

        Args:
            conference: 'AFC' or 'NFC'

        Returns:
            QWidget with 4 division columns
        """
        widget = QWidget()
        widget.setStyleSheet("background: #2a2a2a;")

        # Horizontal layout for 4 divisions
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(24)

        divisions = ['East', 'North', 'South', 'West']

        for division in divisions:
            div_widget = self._create_division_column(conference, division)
            layout.addWidget(div_widget)

        return widget

    def _create_division_column(self, conference: str, division: str) -> QWidget:
        """
        Create a vertical column for a division with header and team cards.

        Args:
            conference: 'AFC' or 'NFC'
            division: 'East', 'North', 'South', or 'West'

        Returns:
            QWidget with division header and 4 team cards stacked vertically
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Division header
        header = QLabel(division.upper())
        header.setFont(Typography.H5)
        header.setStyleSheet("color: #888888; background: transparent;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Get teams for this division
        teams = [t for t in self.team_loader.get_all_teams()
                 if t.conference == conference and t.division == division]

        # Create team cards vertically
        for team in teams:
            team_data = {
                'team_id': team.team_id,
                'city': team.city,
                'nickname': team.nickname,
                'abbreviation': team.abbreviation,
                'colors': team.colors
            }
            card = TeamCard(team_data)
            card.clicked.connect(self._on_card_clicked)
            layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._cards[team.team_id] = card

        layout.addStretch()
        return widget

    def _on_card_clicked(self, team_id: int):
        """
        Handle team card click.

        Args:
            team_id: ID of the clicked team
        """
        # Deselect previous selection
        if self._selected_team_id is not None and self._selected_team_id in self._cards:
            self._cards[self._selected_team_id].set_selected(False)

        # Select new team
        self._selected_team_id = team_id
        if team_id in self._cards:
            self._cards[team_id].set_selected(True)

        self.team_selected.emit(team_id)

    def get_selected_team_id(self) -> Optional[int]:
        """
        Get the currently selected team ID.

        Returns:
            Team ID (1-32) or None if no team selected
        """
        return self._selected_team_id

    def set_selected_team(self, team_id: int):
        """
        Programmatically select a team.

        Args:
            team_id: Team ID to select
        """
        if team_id in self._cards:
            self._on_card_clicked(team_id)

            # Switch to the correct tab
            team = self.team_loader.get_team_by_id(team_id)
            if team:
                tab_index = 0 if team.conference == 'AFC' else 1
                self.tab_widget.setCurrentIndex(tab_index)