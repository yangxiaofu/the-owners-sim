"""
Bench Player Row Widget

Draggable bench player row for depth chart management.
Used in right panel to drag players onto starter positions.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QMimeData, QPoint
from PySide6.QtGui import QDrag, QPixmap, QPainter, QFont, QCursor
import json


class BenchPlayerRow(QWidget):
    """
    Individual bench player row (drag source).

    Shows: Position + Name + Overall + Depth
    Drag: Player can be dragged to starter slots
    """

    def __init__(self, player_id: int, player_name: str, position: str,
                 overall: int, depth_order: int, parent=None):
        """
        Initialize bench player row.

        Args:
            player_id: Unique player ID
            player_name: Player full name
            position: Position (e.g., "quarterback")
            overall: Overall rating (0-99)
            depth_order: Current depth (2, 3, 4..., 99)
            parent: Parent widget
        """
        super().__init__(parent)
        self.player_id = player_id
        self.player_name = player_name
        self.position = position
        self.overall = overall
        self.depth_order = depth_order

        self.drag_start_position = None

        self._setup_ui()
        self._apply_styling()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Drag handle (☰ icon)
        drag_handle = QLabel("☰")
        drag_handle_font = QFont()
        drag_handle_font.setPointSize(10)
        drag_handle.setFont(drag_handle_font)
        drag_handle.setFixedWidth(16)
        layout.addWidget(drag_handle)

        # Position abbreviation (e.g., "QB", "RB")
        from constants.position_abbreviations import get_position_abbreviation
        pos_abbrev = get_position_abbreviation(self.position)
        self.pos_label = QLabel(pos_abbrev)
        pos_font = QFont()
        pos_font.setPointSize(9)
        pos_font.setBold(True)
        self.pos_label.setFont(pos_font)
        self.pos_label.setFixedWidth(30)
        self.pos_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.pos_label)

        # Player name
        self.name_label = QLabel(self.player_name)
        name_font = QFont()
        name_font.setPointSize(10)
        self.name_label.setFont(name_font)
        layout.addWidget(self.name_label, stretch=1)

        # Overall rating
        self.overall_label = QLabel(f"{self.overall}")
        overall_font = QFont()
        overall_font.setPointSize(10)
        overall_font.setBold(True)
        self.overall_label.setFont(overall_font)
        self.overall_label.setFixedWidth(25)
        self.overall_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.overall_label)

        # Depth order (if not 99)
        if self.depth_order != 99:
            depth_label = QLabel(f"#{self.depth_order}")
            depth_font = QFont()
            depth_font.setPointSize(9)
            depth_label.setFont(depth_font)
            depth_label.setFixedWidth(30)
            depth_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            layout.addWidget(depth_label)

        self.setFixedHeight(32)

    def _apply_styling(self):
        """Apply styling to widget."""
        self.setStyleSheet("""
            BenchPlayerRow {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            BenchPlayerRow:hover {
                background-color: #F0F0F0;
                border: 1px solid #BDBDBD;
            }
            QLabel {
                background: transparent;
                border: none;
                color: #E0E0E0;
            }
        """)
        self.setCursor(QCursor(Qt.OpenHandCursor))

    def mousePressEvent(self, event):
        """Handle mouse press for drag initiation."""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        """Handle mouse move for drag operation."""
        if not (event.buttons() & Qt.LeftButton):
            return

        if not self.drag_start_position:
            return

        # Check if moved beyond drag threshold
        if (event.pos() - self.drag_start_position).manhattanLength() < 10:
            return

        # Start drag operation
        self._start_drag()

    def _start_drag(self):
        """Initiate drag operation with player data."""
        # Create drag object
        drag = QDrag(self)

        # Create MIME data with player info
        mime_data = QMimeData()

        # Store player data as JSON
        player_data = {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'position': self.position,
            'overall': self.overall,
            'depth_order': self.depth_order
        }
        mime_data.setText(json.dumps(player_data))
        drag.setMimeData(mime_data)

        # Create ghost image (50% opacity)
        pixmap = self.grab()

        transparent_pixmap = QPixmap(pixmap.size())
        transparent_pixmap.fill(Qt.transparent)

        painter = QPainter(transparent_pixmap)
        painter.setOpacity(0.5)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        drag.setPixmap(transparent_pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        # Change cursor
        self.setCursor(QCursor(Qt.ClosedHandCursor))

        # Execute drag (blocks until drop)
        drag.exec(Qt.MoveAction)

        # Reset cursor (with safety check for widget deletion)
        try:
            self.setCursor(QCursor(Qt.OpenHandCursor))
        except RuntimeError:
            pass

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        self.drag_start_position = None
        super().mouseReleaseEvent(event)
