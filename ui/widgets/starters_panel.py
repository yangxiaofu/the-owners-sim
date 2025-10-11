"""
Starters Panel Widget

Left panel showing all starter positions in depth chart.
Organizes starter slots by Offense, Defense, and Special Teams.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QGroupBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal

from ui.widgets.starter_slot_widget import StarterSlotWidget


class StartersPanel(QWidget):
    """
    Left panel showing all starter positions.

    Layout: 3 sections (Offense, Defense, Special Teams)
    Contains: Grid of StarterSlotWidgets
    Emits: swap_requested(position, old_starter_id, new_starter_id)
    """

    # Signal emitted when a swap is requested
    swap_requested = Signal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Store all starter slot widgets
        self.starter_slots = {}

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI with scrollable sections."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        # Container
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(15)

        # Create sections
        offense_group = self._create_offense_section()
        defense_group = self._create_defense_section()
        st_group = self._create_special_teams_section()

        container_layout.addWidget(offense_group)
        container_layout.addWidget(defense_group)
        container_layout.addWidget(st_group)
        container_layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_offense_section(self) -> QGroupBox:
        """Create offense starter slots."""
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
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Row 0: QB, RB1, RB2
        self._add_slot(layout, 0, 0, "quarterback", "QB", 1)
        self._add_slot(layout, 0, 1, "running_back", "RB1", 1)
        self._add_slot(layout, 0, 2, "running_back", "RB2", 2)

        # Row 1: WR1, WR2, WR3
        self._add_slot(layout, 1, 0, "wide_receiver", "WR1", 1)
        self._add_slot(layout, 1, 1, "wide_receiver", "WR2", 2)
        self._add_slot(layout, 1, 2, "wide_receiver", "WR3", 3)

        # Row 2: TE1, TE2
        self._add_slot(layout, 2, 0, "tight_end", "TE1", 1)
        self._add_slot(layout, 2, 1, "tight_end", "TE2", 2)

        # Row 3: LT, LG, C
        self._add_slot(layout, 3, 0, "left_tackle", "LT", 1)
        self._add_slot(layout, 3, 1, "left_guard", "LG", 1)
        self._add_slot(layout, 3, 2, "center", "C", 1)

        # Row 4: RG, RT
        self._add_slot(layout, 4, 0, "right_guard", "RG", 1)
        self._add_slot(layout, 4, 1, "right_tackle", "RT", 1)

        group.setLayout(layout)
        return group

    def _create_defense_section(self) -> QGroupBox:
        """Create defense starter slots."""
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
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Row 0: DE1, DT, DE2
        self._add_slot(layout, 0, 0, "defensive_end", "DE1", 1)
        self._add_slot(layout, 0, 1, "defensive_tackle", "DT", 1)
        self._add_slot(layout, 0, 2, "defensive_end", "DE2", 2)

        # Row 1: LB1, LB2, LB3
        self._add_slot(layout, 1, 0, "linebacker", "LB1", 1)
        self._add_slot(layout, 1, 1, "linebacker", "LB2", 2)
        self._add_slot(layout, 1, 2, "linebacker", "LB3", 3)

        # Row 2: CB1, CB2, FS, SS
        self._add_slot(layout, 2, 0, "cornerback", "CB1", 1)
        self._add_slot(layout, 2, 1, "cornerback", "CB2", 2)
        self._add_slot(layout, 2, 2, "safety", "FS", 1)

        # Row 3: SS (safety position, depth 2)
        self._add_slot(layout, 3, 0, "safety", "SS", 2)

        group.setLayout(layout)
        return group

    def _create_special_teams_section(self) -> QGroupBox:
        """Create special teams starter slots."""
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

        layout = QGridLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Row 0: K, P, LS
        self._add_slot(layout, 0, 0, "kicker", "K", 1)
        self._add_slot(layout, 0, 1, "punter", "P", 1)
        self._add_slot(layout, 0, 2, "long_snapper", "LS", 1)

        group.setLayout(layout)
        return group

    def _add_slot(self, layout: QGridLayout, row: int, col: int,
                  position: str, label: str, depth: int):
        """
        Add a starter slot to the grid.

        Args:
            layout: Grid layout to add to
            row: Grid row
            col: Grid column
            position: Position name (e.g., "quarterback")
            label: Display label (e.g., "QB", "RB1")
            depth: Starter depth (1, 2, 3...)
        """
        # Create unique key for this slot
        slot_key = f"{position}_{depth}"

        # Create slot widget
        slot = StarterSlotWidget(position, label, depth)

        # Connect signal
        slot.swap_requested.connect(self._on_swap_requested)

        # Store reference
        self.starter_slots[slot_key] = slot

        # Add to layout
        layout.addWidget(slot, row, col, Qt.AlignTop)

    def _on_swap_requested(self, position: str, old_starter_id: int, new_starter_id: int):
        """
        Handle swap request from a starter slot.

        Re-emits to parent controller.
        """
        self.swap_requested.emit(position, old_starter_id, new_starter_id)

    def load_starters(self, depth_chart_data: dict):
        """
        Load starters from depth chart data.

        Args:
            depth_chart_data: Dict mapping position -> sorted player list
                {
                    'quarterback': [player1, player2, ...],
                    'running_back': [...],
                    ...
                }
        """
        # Clear all slots first
        for slot in self.starter_slots.values():
            slot.clear_starter()

        # Load starters
        for position, players in depth_chart_data.items():
            # Sort by depth order
            sorted_players = sorted(players, key=lambda p: p['depth_order'])

            # Assign to appropriate slots
            for player in sorted_players:
                depth = player['depth_order']

                # Skip if not a starter (depth > 3 for most positions)
                if depth > 3:
                    continue

                # Create slot key
                slot_key = f"{position}_{depth}"

                # Set starter if slot exists
                if slot_key in self.starter_slots:
                    self.starter_slots[slot_key].set_starter(
                        player['player_id'],
                        player['player_name'],
                        player['overall']
                    )
