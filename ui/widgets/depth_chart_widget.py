"""
Depth Chart Widget for Team View

Displays team depth chart with drag-and-drop support for reordering players.
Uses EnhancedPositionCard for collapsible position groups.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QGroupBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ui.widgets.enhanced_position_card import EnhancedPositionCard


class DepthChartWidget(QWidget):
    """
    Depth Chart sub-tab widget for Team View.

    Displays complete team depth chart organized by position with offense,
    defense, and special teams sections. Supports drag-and-drop reordering.

    Signals:
        depth_chart_changed(position: str, ordered_player_ids: list[int]):
            Emitted when depth chart is reordered via drag-and-drop
    """

    # Signal emitted when depth chart changes
    depth_chart_changed = Signal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the main widget layout."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        self.title_label = QLabel("Depth Chart - Select Team")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #333333;")

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # Scroll area for depth chart sections
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        # Container for all sections
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(15)

        # Offense section
        self.offense_group = self._create_offense_section()
        container_layout.addWidget(self.offense_group)

        # Defense section
        self.defense_group = self._create_defense_section()
        container_layout.addWidget(self.defense_group)

        # Special Teams section
        self.special_teams_group = self._create_special_teams_section()
        container_layout.addWidget(self.special_teams_group)

        container_layout.addStretch()
        container.setLayout(container_layout)
        scroll_area.setWidget(container)

        main_layout.addWidget(scroll_area)

        self.setLayout(main_layout)

    def _create_offense_section(self) -> QGroupBox:
        """Create the offense depth chart section."""
        group = QGroupBox("OFFENSE")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #0066cc;
            }
        """)

        layout = QGridLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Store position cards
        self.offense_cards = {}

        # Define offensive positions by row
        position_rows = [
            # Row 0: Skill positions
            [
                ("quarterback", "QB"),
                ("running_back", "RB"),
                ("wide_receiver", "WR"),
                ("tight_end", "TE")
            ],
            # Row 1: Offensive line
            [
                ("left_tackle", "LT"),
                ("left_guard", "LG"),
                ("center", "C"),
                ("right_guard", "RG")
            ],
            # Row 2: Right tackle
            [
                ("right_tackle", "RT")
            ]
        ]

        # Create position cards
        for row_idx, positions in enumerate(position_rows):
            for col_idx, (position, display_name) in enumerate(positions):
                card = EnhancedPositionCard(position, display_name)
                card.depth_chart_changed.connect(self._on_depth_chart_changed)
                self.offense_cards[position] = card
                layout.addWidget(card, row_idx, col_idx, Qt.AlignTop)

        layout.setColumnStretch(4, 1)  # Push everything to the left

        group.setLayout(layout)
        return group

    def _create_defense_section(self) -> QGroupBox:
        """Create the defense depth chart section."""
        group = QGroupBox("DEFENSE")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #0066cc;
            }
        """)

        layout = QGridLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Store position cards
        self.defense_cards = {}

        # Define defensive positions by row
        position_rows = [
            # Row 0: Defensive line
            [
                ("defensive_end", "DE"),
                ("defensive_tackle", "DT"),
                ("nose_tackle", "NT")
            ],
            # Row 1: Linebackers
            [
                ("linebacker", "LB")
            ],
            # Row 2: Secondary
            [
                ("cornerback", "CB"),
                ("safety", "S")
            ]
        ]

        # Create position cards
        for row_idx, positions in enumerate(position_rows):
            for col_idx, (position, display_name) in enumerate(positions):
                card = EnhancedPositionCard(position, display_name)
                card.depth_chart_changed.connect(self._on_depth_chart_changed)
                self.defense_cards[position] = card
                layout.addWidget(card, row_idx, col_idx, Qt.AlignTop)

        layout.setColumnStretch(3, 1)  # Push everything to the left

        group.setLayout(layout)
        return group

    def _create_special_teams_section(self) -> QGroupBox:
        """Create the special teams depth chart section."""
        group = QGroupBox("SPECIAL TEAMS")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #0066cc;
            }
        """)

        layout = QHBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Store position cards
        self.special_teams_cards = {}

        # Define special teams positions
        positions = [
            ("kicker", "K"),
            ("punter", "P"),
            ("long_snapper", "LS")
        ]

        # Create position cards
        for position, display_name in positions:
            card = EnhancedPositionCard(position, display_name)
            card.depth_chart_changed.connect(self._on_depth_chart_changed)
            self.special_teams_cards[position] = card
            layout.addWidget(card)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def _on_depth_chart_changed(self, position: str, ordered_player_ids: list[int]):
        """
        Handle depth chart change from position card.

        Re-emits signal to controller for persistence.

        Args:
            position: Position that changed
            ordered_player_ids: New player order
        """
        # Re-emit to controller
        self.depth_chart_changed.emit(position, ordered_player_ids)

    def load_depth_chart(self, team_name: str, depth_chart_data: dict):
        """
        Load depth chart data into widget.

        Args:
            team_name: Team name for header display
            depth_chart_data: Dictionary mapping position to player list:
                {
                    'quarterback': [
                        {
                            'player_id': int,
                            'player_name': str,
                            'overall': int,
                            'depth_order': int,
                            'position': str
                        },
                        ...
                    ],
                    ...
                }
        """
        # Update header
        self.title_label.setText(f"Depth Chart - {team_name}")

        # Load offense
        for position, card in self.offense_cards.items():
            players = depth_chart_data.get(position, [])
            card.set_players(players)

        # Load defense
        for position, card in self.defense_cards.items():
            players = depth_chart_data.get(position, [])
            card.set_players(players)

        # Load special teams
        for position, card in self.special_teams_cards.items():
            players = depth_chart_data.get(position, [])
            card.set_players(players)

    def clear_depth_chart(self):
        """Clear all depth chart data (used when switching teams)."""
        # Clear offense
        for card in self.offense_cards.values():
            card.set_players([])

        # Clear defense
        for card in self.defense_cards.values():
            card.set_players([])

        # Clear special teams
        for card in self.special_teams_cards.values():
            card.set_players([])

        # Reset header
        self.title_label.setText("Depth Chart - Select Team")
