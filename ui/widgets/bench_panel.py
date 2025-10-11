"""
Bench Panel Widget

Right panel showing bench players with position-based filtering.
Displays all non-starter players (depth 2-99) grouped by position.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QScrollArea, QFrame, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.widgets.bench_player_row import BenchPlayerRow


class BenchPanel(QWidget):
    """
    Right panel showing bench players with filtering.

    Features:
    - Filter dropdown (All, QB, RB, WR, TE, OL, DL, LB, DB, ST)
    - Scrollable area with position groups
    - Position group headers
    - Shows depth 2-99 players
    """

    # Position group mapping
    POSITION_GROUPS = {
        'QB': ['quarterback'],
        'RB': ['running_back', 'fullback'],
        'WR': ['wide_receiver'],
        'TE': ['tight_end'],
        'OL': ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle'],
        'DL': ['defensive_end', 'defensive_tackle', 'nose_tackle'],
        'LB': ['linebacker', 'outside_linebacker', 'middle_linebacker'],
        'DB': ['cornerback', 'safety', 'free_safety', 'strong_safety'],
        'ST': ['kicker', 'punter', 'long_snapper']
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        # Store position group widgets
        self.position_groups = {}  # {group_name: QGroupBox}

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI with filter and scrollable groups."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Filter section
        filter_widget = self._create_filter_section()
        main_layout.addWidget(filter_widget)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        # Container for position groups
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        self.container_layout.setSpacing(15)

        # Create position group widgets
        for group_name in self.POSITION_GROUPS.keys():
            group_widget = self._create_position_group(group_name)
            self.position_groups[group_name] = group_widget
            self.container_layout.addWidget(group_widget)

        self.container_layout.addStretch()

        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)

    def _create_filter_section(self) -> QWidget:
        """
        Create filter dropdown section.

        Returns:
            Filter widget with label and dropdown
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Label
        label = QLabel("Filter:")
        label_font = QFont()
        label_font.setPointSize(11)
        label_font.setBold(True)
        label.setFont(label_font)
        layout.addWidget(label)

        # Dropdown
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Positions",
            "QB", "RB", "WR", "TE", "OL",
            "DL", "LB", "DB", "ST"
        ])
        filter_font = QFont()
        filter_font.setPointSize(10)
        self.filter_combo.setFont(filter_font)
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        layout.addWidget(self.filter_combo, stretch=1)

        widget.setStyleSheet("""
            QWidget {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QLabel {
                background: transparent;
                border: none;
                color: #333333;
            }
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)

        return widget

    def _create_position_group(self, group_name: str) -> QGroupBox:
        """
        Create a position group with header.

        Args:
            group_name: Position group name (e.g., "QB", "RB")

        Returns:
            Group box widget
        """
        group = QGroupBox(f"{group_name} Bench")
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

        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(10, 10, 10, 10)
        group.setLayout(layout)

        # Initially hidden (will show when data loaded)
        group.hide()

        return group

    def _on_filter_changed(self, filter_text: str):
        """
        Handle filter dropdown change.

        Args:
            filter_text: Selected filter (e.g., "All Positions", "QB")
        """
        if filter_text == "All Positions":
            # Show all groups that have players
            for group in self.position_groups.values():
                if group.layout().count() > 0:  # Has players
                    group.show()
                else:
                    group.hide()
        else:
            # Show only selected group
            for group_name, group in self.position_groups.items():
                if group_name == filter_text:
                    group.show()
                else:
                    group.hide()

    def load_bench_players(self, depth_chart_data: dict):
        """
        Load bench players from depth chart data.

        Args:
            depth_chart_data: Dict mapping position -> sorted player list
                {
                    'quarterback': [player1, player2, ...],
                    'running_back': [...],
                    ...
                }
                Each player dict has:
                - player_id (int)
                - player_name (str)
                - overall (int)
                - depth_order (int)
                - position (str)
        """
        # Clear all groups
        self._clear_all_groups()

        # Group players by position group
        grouped_players = {group: [] for group in self.POSITION_GROUPS.keys()}

        for position, players in depth_chart_data.items():
            # Find which group this position belongs to
            for group_name, group_positions in self.POSITION_GROUPS.items():
                if position in group_positions:
                    # Filter bench players (depth 2+)
                    bench_players = [p for p in players if p['depth_order'] >= 2]
                    grouped_players[group_name].extend(bench_players)
                    break

        # Add players to their groups
        for group_name, players in grouped_players.items():
            if not players:
                # No bench players - hide group
                self.position_groups[group_name].hide()
                continue

            # Sort by depth order, then overall
            sorted_players = sorted(players, key=lambda p: (p['depth_order'], -p['overall']))

            # Deduplicate by player_id (keep first occurrence = lowest depth_order)
            # This prevents generic position players (e.g., "guard") from appearing multiple times
            # when they're included in multiple specific positions (e.g., left_guard, right_guard)
            seen_ids = set()
            unique_players = []
            for player in sorted_players:
                if player['player_id'] not in seen_ids:
                    unique_players.append(player)
                    seen_ids.add(player['player_id'])

            # Add player rows (using deduplicated list)
            group_layout = self.position_groups[group_name].layout()
            for player in unique_players:
                player_row = BenchPlayerRow(
                    player_id=player['player_id'],
                    player_name=player['player_name'],
                    position=player['position'],
                    overall=player['overall'],
                    depth_order=player['depth_order']
                )
                group_layout.addWidget(player_row)

            # Show group
            self.position_groups[group_name].show()

        # Reset filter to "All Positions"
        self.filter_combo.setCurrentText("All Positions")

    def _clear_all_groups(self):
        """Clear all player rows from all groups."""
        for group in self.position_groups.values():
            layout = group.layout()

            # Remove all widgets
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Hide group
            group.hide()

    def get_player_count(self) -> int:
        """
        Get total number of bench players displayed.

        Returns:
            Total player count across all groups
        """
        total = 0
        for group in self.position_groups.values():
            total += group.layout().count()
        return total
