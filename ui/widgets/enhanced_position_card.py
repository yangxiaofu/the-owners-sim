"""
Enhanced Position Card Widget

Collapsible position card containing depth chart list with drag-and-drop support.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont, QCursor

from ui.widgets.depth_chart_list_widget import DepthChartListWidget
from ui.widgets.draggable_player_row import DraggablePlayerRow
from ui.widgets.toast_notification import ToastNotification


class EnhancedPositionCard(QWidget):
    """
    Enhanced position card with collapsible depth chart list.

    Features:
    - Collapsible header with expand/collapse button
    - DepthChartListWidget for drag-and-drop depth chart management
    - Player count display (e.g., "3 players")
    - Smooth expand/collapse animation
    - Signal emission when depth chart changes
    """

    # Signal emitted when depth chart is reordered
    # Args: (position: str, ordered_player_ids: list[int])
    depth_chart_changed = Signal(str, list)

    def __init__(self, position: str, position_display_name: str, parent=None):
        """
        Initialize enhanced position card.

        Args:
            position: Position identifier (e.g., "quarterback")
            position_display_name: Display name (e.g., "Quarterback")
            parent: Parent widget
        """
        super().__init__(parent)
        self.position = position
        self.position_display_name = position_display_name
        self.is_expanded = True  # Start expanded

        self._setup_ui()
        self._apply_styling()

    def _setup_ui(self):
        """Setup UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 8)
        main_layout.setSpacing(0)

        # Header section
        self.header_widget = self._create_header()
        main_layout.addWidget(self.header_widget)

        # Content section (collapsible)
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(0)

        # Depth chart list
        self.depth_chart_list = DepthChartListWidget(self.position)
        # Note: Height set dynamically in set_players() based on player count
        self.depth_chart_list.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        content_layout.addWidget(self.depth_chart_list)

        main_layout.addWidget(self.content_widget)

        # Connect signals
        self.depth_chart_list.depth_chart_changed.connect(
            self._on_depth_chart_changed
        )

    def _create_header(self) -> QFrame:
        """
        Create collapsible header with expand/collapse button.

        Returns:
            Header widget
        """
        header = QFrame()
        header.setFrameShape(QFrame.StyledPanel)
        header.setCursor(QCursor(Qt.PointingHandCursor))

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(8)

        # Expand/collapse button (▼ / ▶)
        self.expand_button = QLabel("▼")
        expand_font = QFont()
        expand_font.setPointSize(10)
        self.expand_button.setFont(expand_font)
        self.expand_button.setFixedWidth(20)
        header_layout.addWidget(self.expand_button)

        # Position name
        self.position_label = QLabel(self.position_display_name)
        position_font = QFont()
        position_font.setPointSize(12)
        position_font.setBold(True)
        self.position_label.setFont(position_font)
        header_layout.addWidget(self.position_label, stretch=1)

        # Player count
        self.count_label = QLabel("0 players")
        count_font = QFont()
        count_font.setPointSize(10)
        self.count_label.setFont(count_font)
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header_layout.addWidget(self.count_label)

        # Make header clickable
        header.mousePressEvent = lambda event: self.toggle_expand()

        return header

    def _apply_styling(self):
        """Apply styling to card."""
        self.setStyleSheet("""
            EnhancedPositionCard {
                background: transparent;
            }
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QFrame:hover {
                background-color: #F5F5F5;
                border: 1px solid #BDBDBD;
            }
            QLabel {
                background: transparent;
                border: none;
                color: #333333;
            }
        """)

    def toggle_expand(self):
        """Toggle expand/collapse state with animation."""
        if self.is_expanded:
            self._collapse()
        else:
            self._expand()

    def _expand(self):
        """Expand content with animation."""
        self.is_expanded = True
        self.expand_button.setText("▼")

        # Show content
        self.content_widget.show()

        # Animate height
        self.animation = QPropertyAnimation(self.content_widget, b"maximumHeight")
        self.animation.setDuration(200)
        self.animation.setStartValue(0)
        self.animation.setEndValue(self.content_widget.sizeHint().height())
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()

    def _collapse(self):
        """Collapse content with animation."""
        self.is_expanded = False
        self.expand_button.setText("▶")

        # Animate height
        self.animation = QPropertyAnimation(self.content_widget, b"maximumHeight")
        self.animation.setDuration(200)
        self.animation.setStartValue(self.content_widget.height())
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.finished.connect(lambda: self.content_widget.hide())
        self.animation.start()

    def set_players(self, players: list[dict]):
        """
        Set players for this position's depth chart.

        Args:
            players: List of player dicts with keys:
                - player_id (int)
                - player_name (str)
                - overall (int)
                - depth_order (int)
                - position (str)
        """
        # Clear existing items
        self.depth_chart_list.clear()

        # Sort by depth order
        sorted_players = sorted(players, key=lambda p: p['depth_order'])

        # Add player rows
        for player in sorted_players:
            player_row = DraggablePlayerRow(
                player_id=player['player_id'],
                player_name=player['player_name'],
                overall=player['overall'],
                depth_order=player['depth_order'],
                position=player['position']
            )
            self.depth_chart_list.add_player_row(player_row)

        # Update count label
        self._update_count_label(len(players))

        # Update list height dynamically based on player count
        self._update_list_height(len(players))

    def _update_count_label(self, count: int):
        """
        Update player count label.

        Args:
            count: Number of players
        """
        player_text = "player" if count == 1 else "players"
        self.count_label.setText(f"{count} {player_text}")

    def _update_list_height(self, player_count: int):
        """
        Dynamically set list height based on player count.

        Formula: 6 + (42 × N) where N = player_count
        - 40px per player row
        - 2px spacing between rows
        - 8px padding (4px top + 4px bottom)

        Shows all players for small rosters (2-6 players) without scrolling.
        Caps at 6 players height for large rosters to prevent huge cards.

        Args:
            player_count: Number of players in list
        """
        if player_count == 0:
            # Empty state - show minimal height
            height = 50
        else:
            # Calculate height: padding + (rows × height) + (gaps × spacing)
            height = 6 + (42 * player_count)

            # Cap at 6 players (258px) to prevent huge cards
            max_height = 6 + (42 * 6)  # 258px
            height = min(height, max_height)

        self.depth_chart_list.setMinimumHeight(height)
        self.depth_chart_list.setMaximumHeight(height)

    def _on_depth_chart_changed(self, position: str, ordered_player_ids: list[int]):
        """
        Handle depth chart reorder from list widget.

        Args:
            position: Position that changed
            ordered_player_ids: New player order
        """
        # Re-emit signal to parent (will be handled by controller)
        self.depth_chart_changed.emit(position, ordered_player_ids)

    def get_current_depth_chart(self) -> list[int]:
        """
        Get current depth chart order.

        Returns:
            List of player IDs in current visual order
        """
        return self.depth_chart_list.get_ordered_player_ids()

    def show_success(self, message: str):
        """
        Show success toast notification.

        Args:
            message: Success message to display
        """
        if self.window():
            ToastNotification.show_success(self.window(), message)

    def show_error(self, message: str):
        """
        Show error toast notification.

        Args:
            message: Error message to display
        """
        if self.window():
            ToastNotification.show_error(self.window(), message)

    def refresh_depth_numbers(self):
        """
        Refresh depth numbers (1, 2, 3...) for all players.

        Useful after external depth chart modifications.
        """
        self.depth_chart_list._update_all_depth_numbers()
