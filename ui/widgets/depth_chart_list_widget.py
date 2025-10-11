"""
Depth Chart List Widget

List widget that accepts player row drops and manages depth chart ordering.
"""

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QPen
import json


class DepthChartListWidget(QListWidget):
    """
    List widget for depth chart management with drag-and-drop support.

    Features:
    - Accepts drops from DraggablePlayerRow
    - Validates position matches
    - Shows visual feedback (green line for valid drop, red border for invalid)
    - Emits signal when order changes
    """

    # Signal emitted when depth chart order changes
    # Args: (position: str, ordered_player_ids: list[int])
    depth_chart_changed = Signal(str, list)

    def __init__(self, position: str, parent=None):
        """
        Initialize depth chart list.

        Args:
            position: Position this list represents (e.g., "quarterback")
            parent: Parent widget
        """
        super().__init__(parent)
        self.position = position
        self.drop_indicator_rect = None  # For drawing green line
        self.is_valid_drop = True

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI properties."""
        # Enable drops
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.InternalMove)

        # Visual properties
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.setSpacing(2)

        # Styling
        self.setStyleSheet("""
            QListWidget {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item {
                background: transparent;
                border: none;
            }
            QListWidget::item:selected {
                background: transparent;
                border: none;
            }
        """)

    def dragEnterEvent(self, event):
        """Handle drag enter - validate if drop is allowed."""
        mime_data = event.mimeData()

        if not mime_data.hasText():
            event.ignore()
            return

        try:
            player_data = json.loads(mime_data.text())

            # Validate position matches
            if player_data['position'] == self.position:
                self.is_valid_drop = True
                event.acceptProposedAction()
                self._update_border_style(valid=True)
            else:
                self.is_valid_drop = False
                event.ignore()
                self._update_border_style(valid=False)

        except (json.JSONDecodeError, KeyError):
            event.ignore()
            self.is_valid_drop = False
            self._update_border_style(valid=False)

    def dragMoveEvent(self, event):
        """Handle drag move - show drop indicator."""
        if not self.is_valid_drop:
            event.ignore()
            return

        # Calculate drop position
        drop_index = self._get_drop_index(event.pos())

        # Update drop indicator (green line)
        self._update_drop_indicator(drop_index)

        event.acceptProposedAction()
        self.viewport().update()

    def dragLeaveEvent(self, event):
        """Handle drag leave - remove visual feedback."""
        self.drop_indicator_rect = None
        self._update_border_style(valid=None)  # Reset to normal
        self.viewport().update()

    def dropEvent(self, event):
        """Handle drop - reorder depth chart."""
        if not self.is_valid_drop:
            event.ignore()
            return

        mime_data = event.mimeData()

        if not mime_data.hasText():
            event.ignore()
            return

        try:
            player_data = json.loads(mime_data.text())
            player_id = player_data['player_id']

            # Get drop index
            drop_index = self._get_drop_index(event.pos())

            # Find source item (if exists in this list)
            source_index = self._find_player_index(player_id)

            if source_index is not None:
                # Reorder within same list
                self._reorder_item(source_index, drop_index)
            else:
                # Add new player (from external source)
                # This case is for future cross-widget drag support
                pass

            # Clear visual feedback
            self.drop_indicator_rect = None
            self._update_border_style(valid=None)

            # Emit signal with new order
            ordered_player_ids = self.get_ordered_player_ids()
            self.depth_chart_changed.emit(self.position, ordered_player_ids)

            event.acceptProposedAction()
            self.viewport().update()

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[ERROR] Failed to process drop: {e}")
            event.ignore()

    def _get_drop_index(self, pos) -> int:
        """
        Get drop index based on mouse position.

        Args:
            pos: Mouse position (QPoint)

        Returns:
            Index where item should be dropped
        """
        item = self.itemAt(pos)

        if item is None:
            # Drop at end
            return self.count()

        index = self.row(item)

        # Check if mouse is in top half or bottom half of item
        item_rect = self.visualItemRect(item)
        if pos.y() < item_rect.center().y():
            return index  # Drop before item
        else:
            return index + 1  # Drop after item

    def _update_drop_indicator(self, drop_index: int):
        """
        Update drop indicator visual (green line).

        Args:
            drop_index: Index where drop would occur
        """
        if drop_index >= self.count():
            # Drop at end
            if self.count() == 0:
                # Empty list - highlight entire area
                self.drop_indicator_rect = self.viewport().rect()
            else:
                # After last item
                last_item = self.item(self.count() - 1)
                item_rect = self.visualItemRect(last_item)
                self.drop_indicator_rect = QRect(
                    0,
                    item_rect.bottom(),
                    self.viewport().width(),
                    2
                )
        else:
            # Between items
            item = self.item(drop_index)
            item_rect = self.visualItemRect(item)
            self.drop_indicator_rect = QRect(
                0,
                item_rect.top() - 1,
                self.viewport().width(),
                2
            )

    def paintEvent(self, event):
        """Override paint to draw drop indicator."""
        super().paintEvent(event)

        # Draw drop indicator (green line)
        if self.drop_indicator_rect and self.is_valid_drop:
            painter = QPainter(self.viewport())
            pen = QPen(QColor("#4CAF50"), 2)  # Green, 2px
            painter.setPen(pen)
            painter.drawLine(
                self.drop_indicator_rect.left(),
                self.drop_indicator_rect.top(),
                self.drop_indicator_rect.right(),
                self.drop_indicator_rect.top()
            )

    def _update_border_style(self, valid: bool | None):
        """
        Update border styling based on drop validity.

        Args:
            valid: True (green), False (red), None (normal)
        """
        if valid is True:
            # Valid drop - normal border (green indicator shown separately)
            border_color = "#E0E0E0"
        elif valid is False:
            # Invalid drop - red border
            border_color = "#F44336"
            self.setCursor(Qt.ForbiddenCursor)
        else:
            # Normal
            border_color = "#E0E0E0"
            self.setCursor(Qt.ArrowCursor)

        self.setStyleSheet(f"""
            QListWidget {{
                background-color: #FAFAFA;
                border: 2px solid {border_color};
                border-radius: 4px;
                padding: 4px;
            }}
            QListWidget::item {{
                background: transparent;
                border: none;
            }}
            QListWidget::item:selected {{
                background: transparent;
                border: none;
            }}
        """)

    def _find_player_index(self, player_id: int) -> int | None:
        """
        Find index of player in list.

        Args:
            player_id: Player ID to find

        Returns:
            Index or None if not found
        """
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)

            if hasattr(widget, 'player_id') and widget.player_id == player_id:
                return i

        return None

    def _reorder_item(self, source_index: int, target_index: int):
        """
        Reorder item from source_index to target_index.

        Uses the rebuild pattern: collect all widgets, clear list, re-add in new order.
        This is the correct Qt approach for reordering custom widgets.

        Args:
            source_index: Current index
            target_index: Target index
        """
        if source_index == target_index:
            return

        # Step 1: Collect all player widgets and detach from list ownership
        widgets = []
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            if widget:
                # CRITICAL: Detach widget from QListWidget before clear()
                # Without this, clear() will DELETE all widgets from memory
                widget.setParent(None)
                widgets.append(widget)

        # Step 2: Extract the moving widget
        moving_widget = widgets.pop(source_index)

        # Step 3: Adjust target index if moving down (before removal)
        if source_index < target_index:
            target_index -= 1

        # Step 4: Insert widget at new position
        widgets.insert(target_index, moving_widget)

        # Step 5: Clear entire list (removes all items)
        self.clear()

        # Step 6: Re-add all widgets in new order with fresh items
        for widget in widgets:
            item = QListWidgetItem(self)
            item.setSizeHint(widget.sizeHint())
            self.addItem(item)
            self.setItemWidget(item, widget)

        # Step 7: Update depth numbers (1, 2, 3...)
        self._update_all_depth_numbers()

    def _update_all_depth_numbers(self):
        """Update depth numbers (1, 2, 3...) for all players."""
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)

            if hasattr(widget, 'update_depth_order'):
                widget.update_depth_order(i + 1)  # 1-indexed

    def get_ordered_player_ids(self) -> list[int]:
        """
        Get player IDs in current visual order.

        Returns:
            List of player_ids in depth chart order
        """
        ordered_ids = []

        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)

            if hasattr(widget, 'player_id'):
                ordered_ids.append(widget.player_id)

        return ordered_ids

    def add_player_row(self, player_row_widget: QWidget):
        """
        Add player row widget to list.

        Args:
            player_row_widget: DraggablePlayerRow widget
        """
        item = QListWidgetItem(self)
        item.setSizeHint(player_row_widget.sizeHint())

        self.addItem(item)
        self.setItemWidget(item, player_row_widget)
