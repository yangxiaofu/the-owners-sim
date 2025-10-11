"""
Starter Slot Widget

Drop target for starter positions in depth chart.
Displays current starter and accepts bench player drops for swapping.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QDragEnterEvent, QDragMoveEvent, QDropEvent
import json


class StarterSlotWidget(QFrame):
    """
    Individual starter position slot (drop target).

    Shows: Position label + Current starter name + Overall
    Accepts: Bench player drops (validates position match)
    Emits: swap_requested(position, old_starter_id, new_starter_id)
    """

    # Signal emitted when a swap is requested
    # Args: (position: str, old_starter_id: int, new_starter_id: int)
    swap_requested = Signal(str, int, int)

    def __init__(self, position: str, position_label: str, depth_order: int = 1, parent=None):
        """
        Initialize starter slot.

        Args:
            position: Position name (e.g., "quarterback", "running_back")
            position_label: Display label (e.g., "QB", "RB1", "WR2")
            depth_order: Starter depth (1 = RB1, 2 = RB2, 3 = WR3, etc.)
            parent: Parent widget
        """
        super().__init__(parent)
        self.position = position
        self.position_label = position_label
        self.depth_order = depth_order

        # Current starter data
        self.current_starter_id = None
        self.current_starter_name = None
        self.current_starter_overall = None

        self._setup_ui()
        self._apply_styling()

        # Enable drops
        self.setAcceptDrops(True)

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Position label
        self.pos_label = QLabel(self.position_label)
        pos_font = QFont()
        pos_font.setPointSize(10)
        pos_font.setBold(True)
        self.pos_label.setFont(pos_font)
        self.pos_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.pos_label)

        # Starter name
        self.name_label = QLabel("Empty")
        name_font = QFont()
        name_font.setPointSize(10)
        self.name_label.setFont(name_font)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label, stretch=1)

        # Overall rating
        self.overall_label = QLabel("")
        overall_font = QFont()
        overall_font.setPointSize(9)
        overall_font.setBold(True)
        self.overall_label.setFont(overall_font)
        self.overall_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.overall_label)

        self.setMinimumSize(100, 80)

    def _apply_styling(self, state="normal"):
        """
        Apply styling based on state.

        Args:
            state: "normal", "valid_hover", "invalid_hover"
        """
        if state == "valid_hover":
            border_color = "#4CAF50"  # Green
            bg_color = "#E8F5E9"
        elif state == "invalid_hover":
            border_color = "#F44336"  # Red
            bg_color = "#FFEBEE"
        else:
            border_color = "#BDBDBD"
            bg_color = "#FAFAFA"

        self.setStyleSheet(f"""
            StarterSlotWidget {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 6px;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: #333333;
            }}
        """)

    def set_starter(self, player_id: int, player_name: str, overall: int):
        """
        Set current starter for this slot.

        Args:
            player_id: Player ID
            player_name: Player full name
            overall: Overall rating
        """
        self.current_starter_id = player_id
        self.current_starter_name = player_name
        self.current_starter_overall = overall

        self.name_label.setText(player_name)
        self.overall_label.setText(f"OVR {overall}")

    def clear_starter(self):
        """Clear starter (slot is empty)."""
        self.current_starter_id = None
        self.current_starter_name = None
        self.current_starter_overall = None

        self.name_label.setText("Empty")
        self.overall_label.setText("")

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter - validate if drop is allowed."""
        mime_data = event.mimeData()

        if not mime_data.hasText():
            event.ignore()
            return

        try:
            player_data = json.loads(mime_data.text())

            # Validate position matches
            if player_data['position'] == self.position:
                # Valid drop
                event.acceptProposedAction()
                self._apply_styling("valid_hover")
            else:
                # Invalid drop (wrong position)
                event.ignore()
                self._apply_styling("invalid_hover")

        except (json.JSONDecodeError, KeyError):
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        """Handle drag move."""
        mime_data = event.mimeData()

        if not mime_data.hasText():
            event.ignore()
            return

        try:
            player_data = json.loads(mime_data.text())

            if player_data['position'] == self.position:
                event.acceptProposedAction()
            else:
                event.ignore()

        except (json.JSONDecodeError, KeyError):
            event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave - reset styling."""
        self._apply_styling("normal")

    def dropEvent(self, event: QDropEvent):
        """Handle drop - emit swap request."""
        mime_data = event.mimeData()

        if not mime_data.hasText():
            event.ignore()
            return

        try:
            player_data = json.loads(mime_data.text())

            # Validate position
            if player_data['position'] != self.position:
                event.ignore()
                self._apply_styling("normal")
                return

            # Get bench player ID
            new_starter_id = player_data['player_id']

            # Check if slot has a current starter
            if self.current_starter_id is None:
                # Slot is empty - just set starter (no swap needed)
                # TODO: Handle this case (might need different signal)
                print(f"[INFO] Dropping {player_data['player_name']} into empty {self.position_label} slot")
                event.acceptProposedAction()
                self._apply_styling("normal")
                return

            # Emit swap request
            self.swap_requested.emit(
                self.position,
                self.current_starter_id,
                new_starter_id
            )

            event.acceptProposedAction()
            self._apply_styling("normal")

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[ERROR] Failed to process drop: {e}")
            event.ignore()
            self._apply_styling("normal")
