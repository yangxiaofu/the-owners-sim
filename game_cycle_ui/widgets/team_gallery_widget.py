"""
Team Gallery Widget - Visual team selection grid.

Displays 32 NFL teams organized by division for visual team selection.
Each team is shown as a colored card with team abbreviation and city.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


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
        self.setFixedSize(110, 70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_stylesheet()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        # Abbreviation (large, centered)
        abbr_label = QLabel(team['abbreviation'])
        abbr_font = QFont()
        abbr_font.setPointSize(16)
        abbr_font.setBold(True)
        abbr_label.setFont(abbr_font)
        abbr_label.setStyleSheet("color: white; background: transparent;")
        abbr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(abbr_label)

        # City (small, centered)
        city_label = QLabel(team['city'])
        city_font = QFont()
        city_font.setPointSize(9)
        city_label.setFont(city_font)
        city_label.setStyleSheet("color: rgba(255, 255, 255, 0.85); background: transparent;")
        city_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(city_label)

    def _update_stylesheet(self):
        """Update the card's stylesheet based on selection state."""
        border = "3px solid #FFD700" if self._selected else "2px solid transparent"
        self.setStyleSheet(f"""
            TeamCard {{
                background-color: {self._primary_color};
                border: {border};
                border-radius: 8px;
            }}
            TeamCard:hover {{
                border: 2px solid #FFD700;
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
    Grid of 32 NFL teams organized by division.

    Layout:
    - 2 rows (AFC, NFC)
    - 4 columns (East, North, South, West)
    - Each cell contains a division group with 4 team cards

    Signals:
        team_selected(int): Emitted when a team card is clicked
    """
    team_selected = Signal(int)  # Emits team_id

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
        """Build the gallery UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("Select Your Team")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Scrollable container for team grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(10)

        # Create division groups: AFC (row 0), NFC (row 1)
        conferences = ['AFC', 'NFC']
        divisions = ['East', 'North', 'South', 'West']

        for c_idx, conf in enumerate(conferences):
            for d_idx, div in enumerate(divisions):
                group = self._create_division_group(conf, div)
                grid.addWidget(group, c_idx, d_idx)

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _create_division_group(self, conference: str, division: str) -> QGroupBox:
        """
        Create a group box containing 4 team cards for a division.

        Args:
            conference: 'AFC' or 'NFC'
            division: 'East', 'North', 'South', or 'West'

        Returns:
            QGroupBox with team cards in a 2x2 grid
        """
        group = QGroupBox(f"{conference} {division}")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        layout = QGridLayout(group)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 15, 8, 8)

        # Get teams for this division
        teams = [t for t in self.team_loader.get_all_teams()
                 if t.conference == conference and t.division == division]

        for i, team in enumerate(teams):
            team_data = {
                'team_id': team.team_id,
                'city': team.city,
                'nickname': team.nickname,
                'abbreviation': team.abbreviation,
                'colors': team.colors
            }
            card = TeamCard(team_data)
            card.clicked.connect(self._on_card_clicked)
            # 2x2 grid within each division
            layout.addWidget(card, i // 2, i % 2)
            self._cards[team.team_id] = card

        return group

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