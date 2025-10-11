"""
Draggable Player Row Widget

Individual player row within depth chart that supports drag-and-drop.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QMimeData, QPoint
from PySide6.QtGui import QDrag, QPixmap, QPainter, QColor, QFont, QCursor


class DraggablePlayerRow(QWidget):
    """
    Individual player row within depth chart list.

    Supports:
    - Drag-and-drop within same position
    - Visual feedback (drag handle, hover state)
    - Ghost image during drag (50% opacity)
    """

    def __init__(self, player_id: int, player_name: str, overall: int,
                 depth_order: int, position: str, parent=None):
        """
        Initialize draggable player row.

        Args:
            player_id: Unique player ID
            player_name: Player name (e.g., "C.J. Stroud")
            overall: Overall rating (0-99)
            depth_order: Depth chart position (1=starter, 2=backup, etc.)
            position: Position (e.g., "quarterback")
            parent: Parent widget
        """
        super().__init__(parent)
        self.player_id = player_id
        self.player_name = player_name
        self.overall = overall
        self.depth_order = depth_order
        self.position = position

        self.drag_start_position = None

        self._setup_ui()
        self._apply_styling()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Drag handle (☰ icon)
        self.drag_handle = QLabel("☰")
        drag_handle_font = QFont()
        drag_handle_font.setPointSize(12)
        self.drag_handle.setFont(drag_handle_font)
        self.drag_handle.setFixedWidth(20)
        self.drag_handle.setCursor(QCursor(Qt.OpenHandCursor))
        layout.addWidget(self.drag_handle)

        # Depth number
        self.depth_label = QLabel(f"{self.depth_order}.")
        depth_font = QFont()
        depth_font.setBold(True)
        depth_font.setPointSize(10)
        self.depth_label.setFont(depth_font)
        self.depth_label.setFixedWidth(20)
        layout.addWidget(self.depth_label)

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
        self.overall_label.setFixedWidth(30)
        self.overall_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.overall_label)

        # Context menu button (⋮)
        self.context_button = QPushButton("⋮")
        context_font = QFont()
        context_font.setPointSize(14)
        self.context_button.setFont(context_font)
        self.context_button.setFixedSize(24, 24)
        self.context_button.setCursor(QCursor(Qt.PointingHandCursor))
        layout.addWidget(self.context_button)

        self.setFixedHeight(40)

    def _apply_styling(self):
        """Apply styling to widget."""
        # Starter gets blue background, backups get white
        if self.depth_order == 1:
            bg_color = "#E3F2FD"  # Light blue for starter
        else:
            bg_color = "#FFFFFF"  # White for backups

        self.setStyleSheet(f"""
            DraggablePlayerRow {{
                background-color: {bg_color};
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }}
            DraggablePlayerRow:hover {{
                background-color: #F5F5F5;
                border: 1px solid #BDBDBD;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: #333333;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: #666666;
            }}
            QPushButton:hover {{
                background-color: #E0E0E0;
                border-radius: 4px;
            }}
        """)

    def update_depth_order(self, new_depth: int):
        """
        Update depth order (e.g., after reordering).

        Args:
            new_depth: New depth chart order
        """
        self.depth_order = new_depth
        self.depth_label.setText(f"{new_depth}.")

        # Update styling (starter vs backup)
        self._apply_styling()

    def mousePressEvent(self, event):
        """Handle mouse press for drag initiation."""
        if event.button() == Qt.LeftButton:
            # Store start position for drag threshold
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
        """Initiate drag operation with ghost image."""
        # Create drag object
        drag = QDrag(self)

        # Create MIME data with player info
        mime_data = QMimeData()

        # Store player data as JSON
        import json
        player_data = {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'overall': self.overall,
            'depth_order': self.depth_order,
            'position': self.position
        }
        mime_data.setText(json.dumps(player_data))
        drag.setMimeData(mime_data)

        # Create ghost image (50% opacity)
        pixmap = self.grab()

        # Apply transparency
        transparent_pixmap = QPixmap(pixmap.size())
        transparent_pixmap.fill(Qt.transparent)

        painter = QPainter(transparent_pixmap)
        painter.setOpacity(0.5)  # 50% opacity
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        drag.setPixmap(transparent_pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        # Change cursor to grabbing hand
        self.setCursor(QCursor(Qt.ClosedHandCursor))

        # Execute drag (blocks until drop)
        result = drag.exec(Qt.MoveAction)

        # Reset cursor (safe - widget may have been deleted during reload)
        try:
            self.setCursor(QCursor(Qt.OpenHandCursor))
        except RuntimeError:
            # Widget was deleted during drag operation (e.g., from reload)
            pass

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        self.drag_start_position = None
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        """Handle mouse enter (hover)."""
        self.setCursor(QCursor(Qt.OpenHandCursor))
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave."""
        self.setCursor(QCursor(Qt.ArrowCursor))
        super().leaveEvent(event)
