"""
Compact FA Header - Single-line sticky header for Free Agency view.

Part of Concept 1 UI redesign - consolidates 230px of headers into 40px.
Layout: [Cap] [FAs] [Wave] [Filters▼] [Process Day]
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QMenu, QComboBox,
    QSpinBox, QWidgetAction
)
from PySide6.QtCore import Signal, Qt
from game_cycle_ui.theme import Typography, FontSizes, Colors


class CompactFAHeader(QWidget):
    """
    Single-line sticky header with essential FA context.

    Displays:
    - Available cap (color-coded: green >10%, amber 5-10%, red <5%)
    - Free agents count
    - Wave progress (name and day)
    - Filters dropdown (collapsed by default)
    - Process Day button (when in wave mode)

    Signals:
        process_day_clicked: User clicked Process Day button
        filter_changed: Filters were modified (position, min_ovr, or show option)
    """

    process_day_clicked = Signal()
    filter_changed = Signal()  # Emitted when any filter changes

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._cap_limit: int = 255_400_000  # Default NFL cap
        self._setup_ui()

    def _setup_ui(self):
        """Build the horizontal layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(12)

        # Left section: Financial and wave info
        self.cap_label = QLabel("Cap: $0")
        self.cap_label.setFont(Typography.SMALL)
        self.cap_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.cap_label)

        # Over-cap warning label (hidden by default)
        self._over_cap_warning = QLabel("OVER CAP")
        self._over_cap_warning.setFont(Typography.SMALL)
        self._over_cap_warning.setStyleSheet(
            f"color: {Colors.ERROR}; font-weight: bold; "
            "background-color: rgba(244, 67, 54, 0.2); "
            "padding: 2px 6px; border-radius: 3px;"
        )
        self._over_cap_warning.hide()
        layout.addWidget(self._over_cap_warning)

        # Separator
        separator1 = QLabel("|")
        separator1.setStyleSheet("color: #666;")
        layout.addWidget(separator1)

        self.fa_count_label = QLabel("0 FAs")
        self.fa_count_label.setFont(Typography.SMALL)
        layout.addWidget(self.fa_count_label)

        # Separator
        separator2 = QLabel("|")
        separator2.setStyleSheet("color: #666;")
        layout.addWidget(separator2)

        self.wave_label = QLabel("Free Agency")
        self.wave_label.setFont(Typography.SMALL)
        layout.addWidget(self.wave_label)

        # Spacer to push right section to edge
        layout.addStretch()

        # Right section: Filters dropdown and Process Day
        self.filters_button = QPushButton("Filters ▼")
        self.filters_button.setFont(Typography.SMALL)
        self.filters_button.setStyleSheet(
            "QPushButton { background-color: #37474F; color: white; "
            "border-radius: 3px; padding: 4px 12px; }"
            "QPushButton:hover { background-color: #263238; }"
        )
        self._create_filters_menu()
        layout.addWidget(self.filters_button)

        self.process_day_btn = QPushButton("Process Day")
        self.process_day_btn.setFont(Typography.SMALL)
        self.process_day_btn.setStyleSheet(
            "QPushButton { background-color: #00695C; color: white; "
            "border-radius: 3px; padding: 4px 12px; }"
            "QPushButton:hover { background-color: #004D40; }"
            "QPushButton:disabled { background-color: #ccc; color: #666; }"
        )
        self.process_day_btn.clicked.connect(self.process_day_clicked.emit)
        self.process_day_btn.hide()  # Hidden by default, shown in wave mode
        layout.addWidget(self.process_day_btn)

        # Set fixed height for compact header
        self.setFixedHeight(40)

        # Background styling
        self.setStyleSheet(
            "CompactFAHeader { background-color: #263238; border-radius: 4px; }"
        )

    def _create_filters_menu(self):
        """Create dropdown menu with position, min OVR, and show options."""
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #263238; color: white; }"
            "QMenu::item:selected { background-color: #37474F; }"
        )

        # Position filter
        position_widget = QWidget()
        position_layout = QHBoxLayout(position_widget)
        position_layout.setContentsMargins(8, 4, 8, 4)

        position_label = QLabel("Position:")
        position_label.setStyleSheet("color: white;")
        position_layout.addWidget(position_label)

        self.position_combo = QComboBox()
        self.position_combo.addItem("All Positions", "")
        positions = [
            "Quarterback", "Running Back", "Wide Receiver", "Tight End",
            "Left Tackle", "Left Guard", "Center", "Right Guard", "Right Tackle",
            "Defensive End", "Defensive Tackle", "Linebacker",
            "Cornerback", "Safety", "Kicker", "Punter"
        ]
        for pos in positions:
            self.position_combo.addItem(pos, pos.lower().replace(" ", "_"))
        self.position_combo.currentIndexChanged.connect(self._on_filter_changed)
        position_layout.addWidget(self.position_combo)

        position_action = QWidgetAction(menu)
        position_action.setDefaultWidget(position_widget)
        menu.addAction(position_action)

        # Min OVR filter
        ovr_widget = QWidget()
        ovr_layout = QHBoxLayout(ovr_widget)
        ovr_layout.setContentsMargins(8, 4, 8, 4)

        ovr_label = QLabel("Min OVR:")
        ovr_label.setStyleSheet("color: white;")
        ovr_layout.addWidget(ovr_label)

        self.min_ovr_spin = QSpinBox()
        self.min_ovr_spin.setRange(0, 99)
        self.min_ovr_spin.setValue(60)
        self.min_ovr_spin.valueChanged.connect(self._on_filter_changed)
        ovr_layout.addWidget(self.min_ovr_spin)

        ovr_action = QWidgetAction(menu)
        ovr_action.setDefaultWidget(ovr_widget)
        menu.addAction(ovr_action)

        # Show options filter
        show_widget = QWidget()
        show_layout = QHBoxLayout(show_widget)
        show_layout.setContentsMargins(8, 4, 8, 4)

        show_label = QLabel("Show:")
        show_label.setStyleSheet("color: white;")
        show_layout.addWidget(show_label)

        self.show_combo = QComboBox()
        self.show_combo.addItems(["All", "Affordable Only", "High Interest (70%+)"])
        self.show_combo.currentIndexChanged.connect(self._on_filter_changed)
        show_layout.addWidget(self.show_combo)

        show_action = QWidgetAction(menu)
        show_action.setDefaultWidget(show_widget)
        menu.addAction(show_action)

        # Connect menu to button
        self.filters_button.setMenu(menu)

    def _on_filter_changed(self):
        """Emit filter_changed signal when any filter is modified."""
        self.filter_changed.emit()

    def update_cap(
        self,
        available: int,
        total: Optional[int] = None,
        projected: Optional[int] = None,
        pending_count: int = 0
    ):
        """
        Update cap label with color coding and optional projected cap.

        Args:
            available: Current available cap space in dollars
            total: Total cap limit (optional, uses default if not provided)
            projected: Projected cap after pending approvals (optional)
            pending_count: Number of pending proposal approvals
        """
        if total is not None:
            self._cap_limit = total

        # Determine if we're showing projected cap
        show_projection = projected is not None and pending_count > 0

        if show_projection:
            # Calculate color for PROJECTED amount
            pct = projected / self._cap_limit if self._cap_limit > 0 else 0

            if projected < 0:
                projected_color = Colors.ERROR  # Red - over cap
            elif pct > 0.10:
                projected_color = Colors.SUCCESS  # Green
            elif pct > 0.05:
                projected_color = Colors.WARNING  # Amber/Orange
            else:
                projected_color = Colors.ERROR  # Red - low

            # Format: "Cap: $45.2M → $28.5M (3 pending)"
            projected_text = f"${projected/1e6:.1f}M" if projected >= 0 else f"-${abs(projected)/1e6:.1f}M"
            label_text = f"Cap: ${available/1e6:.1f}M → {projected_text} ({pending_count} pending)"

            # Style with projected color
            self.cap_label.setText(label_text)
            self.cap_label.setStyleSheet(f"color: {projected_color}; font-weight: bold;")

            # Show/hide over-cap warning
            if projected < 0:
                self._over_cap_warning.show()
            else:
                self._over_cap_warning.hide()
        else:
            # Normal display: "Cap: $45.2M"
            pct = available / self._cap_limit if self._cap_limit > 0 else 0

            if pct > 0.10:
                color = Colors.SUCCESS  # Green
            elif pct > 0.05:
                color = Colors.WARNING  # Amber/Orange
            else:
                color = Colors.ERROR  # Red

            self.cap_label.setText(f"Cap: ${available/1e6:.1f}M")
            self.cap_label.setStyleSheet(f"color: {color}; font-weight: bold;")
            self._over_cap_warning.hide()

    def update_fa_count(self, count: int):
        """Update free agents count display."""
        self.fa_count_label.setText(f"{count} FAs")

    def update_wave_info(self, wave_name: str, day: int = 0, days_total: int = 0):
        """
        Update wave progress display.

        Args:
            wave_name: Display name (e.g., "Wave 3: Depth")
            day: Current day within wave (0 if not in wave mode)
            days_total: Total days in wave (0 if not in wave mode)
        """
        if day > 0 and days_total > 0:
            # Wave mode with day tracking
            self.wave_label.setText(f"{wave_name} - Day {day}/{days_total}")
        else:
            # Simple wave name
            self.wave_label.setText(wave_name)

        # Color coding by wave tier (optional enhancement)
        # For now, use default white text

    def set_process_day_visible(self, visible: bool):
        """Show or hide Process Day button (for wave mode)."""
        self.process_day_btn.setVisible(visible)

    def set_process_day_enabled(self, enabled: bool):
        """Enable or disable Process Day button."""
        self.process_day_btn.setEnabled(enabled)

    def set_process_day_text(self, text: str):
        """Update Process Day button text."""
        self.process_day_btn.setText(text)

    def get_position_filter(self) -> str:
        """Get current position filter value."""
        return self.position_combo.currentData() or ""

    def get_min_ovr_filter(self) -> int:
        """Get current min OVR filter value."""
        return self.min_ovr_spin.value()

    def get_show_filter(self) -> str:
        """Get current show filter value (all/affordable/high_interest)."""
        index = self.show_combo.currentIndex()
        if index == 1:
            return "affordable"
        elif index == 2:
            return "high_interest"
        return "all"
