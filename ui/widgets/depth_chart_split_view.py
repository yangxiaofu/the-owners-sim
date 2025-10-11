"""
Depth Chart Split View Widget

Main depth chart widget with starter/bench split layout.
Left panel: Starters (top 2-3 per position)
Right panel: Bench players with filtering (depth 2-99)
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ui.widgets.starters_panel import StartersPanel
from ui.widgets.bench_panel import BenchPanel
from ui.widgets.toast_notification import ToastNotification


class DepthChartSplitView(QWidget):
    """
    Main depth chart widget with starter/bench split view.

    Layout: QSplitter 40/60 (starters left, bench right)
    Features:
    - Drag-and-drop from bench to starter slots
    - Position validation
    - Pure swap (players trade exact depth positions)
    - Toast notifications for success/error
    - Automatic refresh after swap
    """

    # Signal emitted when depth chart changes
    # Args: (position: str, old_starter_id: int, new_starter_id: int)
    swap_requested = Signal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_team_name = None
        self.current_depth_chart_data = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI with split view layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Header
        header = self._create_header()
        main_layout.addWidget(header)

        # Split view (40/60 ratio)
        splitter = QSplitter(Qt.Horizontal)

        # Left panel: Starters
        self.starters_panel = StartersPanel()
        splitter.addWidget(self.starters_panel)

        # Right panel: Bench
        self.bench_panel = BenchPanel()
        splitter.addWidget(self.bench_panel)

        # Set initial sizes (40% left, 60% right)
        splitter.setSizes([400, 600])

        main_layout.addWidget(splitter, stretch=1)

        # Connect signals
        self.starters_panel.swap_requested.connect(self._on_swap_requested)

    def _create_header(self) -> QWidget:
        """
        Create header with title and instructions.

        Returns:
            Header widget
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Title
        self.title_label = QLabel("Depth Chart")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        # Instructions
        instructions = QLabel("Drag bench players onto starter slots to swap positions")
        instructions_font = QFont()
        instructions_font.setPointSize(10)
        instructions.setFont(instructions_font)
        instructions.setStyleSheet("color: #666666;")
        layout.addWidget(instructions, stretch=1)

        return widget

    def load_depth_chart(self, team_name: str, depth_chart_data: dict):
        """
        Load depth chart data for display.

        Args:
            team_name: Team name for display
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
        self.current_team_name = team_name
        self.current_depth_chart_data = depth_chart_data

        # Update title
        self.title_label.setText(f"{team_name} - Depth Chart")

        # Load starters (left panel)
        self.starters_panel.load_starters(depth_chart_data)

        # Load bench (right panel)
        self.bench_panel.load_bench_players(depth_chart_data)

    def _on_swap_requested(self, position: str, old_starter_id: int, new_starter_id: int):
        """
        Handle swap request from starter slot.

        This method is called when a bench player is dropped onto a starter slot.
        It re-emits the signal to the parent (TeamView) which will handle the
        actual database update via TeamController.

        Args:
            position: Position being swapped (e.g., "quarterback")
            old_starter_id: Current starter's player ID
            new_starter_id: Bench player's player ID (being promoted)
        """
        # Re-emit signal to parent (TeamView will handle persistence)
        self.swap_requested.emit(position, old_starter_id, new_starter_id)

    def refresh_display(self):
        """
        Refresh display with current data.

        Called after a successful swap to update both panels.
        """
        if self.current_team_name and self.current_depth_chart_data:
            self.load_depth_chart(self.current_team_name, self.current_depth_chart_data)

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

    def get_starters_count(self) -> int:
        """
        Get number of starter slots displayed.

        Returns:
            Number of starter slots
        """
        return len(self.starters_panel.starter_slots)

    def get_bench_count(self) -> int:
        """
        Get number of bench players displayed.

        Returns:
            Number of bench players
        """
        return self.bench_panel.get_player_count()
