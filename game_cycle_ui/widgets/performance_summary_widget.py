"""
Performance Summary Widget - Visual goal tracking for Owner Review.

Shows season performance vs. owner directives:
- Win target progress bar
- Playoff results comparison
- Cap utilization
- Priority positions checklist
- Strategy adherence percentage
"""

from typing import Dict, Any, List
import logging
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from game_cycle_ui.theme import Typography, ESPN_THEME, TextColors
from game_cycle_ui.widgets.base_widgets import ReadOnlyDataWidget

logger = logging.getLogger(__name__)


class PerformanceSummaryWidget(ReadOnlyDataWidget):
    """
    Visual summary of season performance vs. goals.

    Shows: Win target progress, playoff results, cap utilization,
    priority positions checklist, strategy adherence.
    """

    def _setup_ui(self):
        """Build the widget layout (called by base class)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Section header (using base class helper)
        header = self._create_section_header("SEASON PERFORMANCE")
        layout.addWidget(header)

        # Win target progress bar
        self.win_target_widget = self._create_win_target_widget()
        layout.addWidget(self.win_target_widget)

        layout.addSpacing(6)

        # Playoff result
        self.playoff_label = QLabel()
        self.playoff_label.setFont(Typography.BODY)
        self.playoff_label.setWordWrap(True)
        layout.addWidget(self.playoff_label)

        layout.addSpacing(6)

        # Financial snapshot
        self.cap_widget = self._create_cap_widget()
        layout.addWidget(self.cap_widget)

        layout.addSpacing(6)

        # Priority positions checklist
        self.positions_widget = self._create_positions_checklist()
        layout.addWidget(self.positions_widget)

        layout.addSpacing(6)

        # Strategy adherence
        self.strategy_label = QLabel()
        self.strategy_label.setFont(Typography.BODY)
        self.strategy_label.setWordWrap(True)
        layout.addWidget(self.strategy_label)

        # Note: Card styling is handled by ReadOnlyDataWidget base class

    def _create_win_target_widget(self):
        """Progress bar for win target."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Label: "Record: 12-5 (Target: 10)"
        self.win_label = QLabel()
        self.win_label.setFont(Typography.BODY)
        layout.addWidget(self.win_label)

        # Progress bar
        self.win_progress = QProgressBar()
        self.win_progress.setTextVisible(True)
        self.win_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #555;
                border-radius: 4px;
                height: 20px;
                text-align: center;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background: {TextColors.SUCCESS};
            }}
        """)
        layout.addWidget(self.win_progress)

        return widget

    def _create_cap_widget(self):
        """Cap utilization display."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.cap_used_label = QLabel()
        self.cap_used_label.setFont(Typography.BODY)
        layout.addWidget(self.cap_used_label)

        self.cap_remaining_label = QLabel()
        self.cap_remaining_label.setFont(Typography.BODY)
        layout.addWidget(self.cap_remaining_label)

        return widget

    def _create_positions_checklist(self):
        """Priority positions addressed/not addressed."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QLabel("Priority Positions Addressed:")
        header.setFont(Typography.BODY)
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        # Dynamic checklist (populated later)
        self.positions_list_layout = QVBoxLayout()
        self.positions_list_layout.setContentsMargins(0, 0, 0, 0)
        self.positions_list_layout.setSpacing(2)
        layout.addLayout(self.positions_list_layout)

        return widget

    def set_data(self, performance_data: Dict[str, Any]):
        """
        Populate widget with season performance data.

        Args:
            performance_data: {
                'wins': int,
                'losses': int,
                'target_wins': int,
                'playoff_result': str,
                'playoff_expectation': str,
                'cap_used': int,
                'cap_total': int,
                'priority_positions': [
                    {'position': 'WR', 'addressed': True, 'player': 'Marcus Johnson', 'ovr': 81},
                    {'position': 'S', 'addressed': True, 'player': 'Isaiah Oliver', 'ovr': 74},
                    {'position': 'EDGE', 'addressed': False}
                ],
                'strategy_adherence': float,  # 0.0 to 1.0
                'strategy_name': str  # e.g., 'Balanced Approach'
            }

        Raises:
            ValueError: If required keys are missing or data types are incorrect
            TypeError: If performance_data is not a dictionary
        """
        try:
            # Type validation
            if not isinstance(performance_data, dict):
                raise TypeError(f"performance_data must be a dict, got {type(performance_data).__name__}")

            # Apply defaults for missing/None values (handles skipping to offseason for testing)
            defaults = {
                'wins': 0,
                'losses': 0,
                'target_wins': 9,
                'playoff_result': None,
                'playoff_expectation': None,
                'cap_used': 0,
                'cap_total': 255_400_000,
                'strategy_adherence': None,
                'strategy_name': None,
            }
            # Merge: defaults first, then provided non-None values override
            data = {**defaults, **{k: v for k, v in performance_data.items() if v is not None}}

            # Win target (with type validation)
            wins = int(data['wins'])
            losses = int(data['losses'])
            target = int(data['target_wins'])

            # Safe division
            if target > 0:
                pct = int((wins / target * 100))
            else:
                pct = 0

            if wins > target:
                status = "✓ EXCEEDED"
                color = TextColors.SUCCESS
            elif wins == target:
                status = "✓ MET"
                color = TextColors.SUCCESS
            else:
                status = "✗ MISSED"
                color = TextColors.ERROR

            self.win_label.setText(f"Record: {wins}-{losses} (Target: {target})  {status}")
            self.win_label.setStyleSheet(f"color: {color}; font-weight: bold;")
            self.win_progress.setValue(min(pct, 100))  # Cap at 100%
            self.win_progress.setFormat(f"{pct}% of target")

            # Playoff result
            playoff_result = data.get('playoff_result') or 'Did not make playoffs'
            playoff_expect = data.get('playoff_expectation') or 'Miss playoffs'

            # Simple comparison (could be enhanced with ordinal ranking)
            if playoff_result == playoff_expect:
                playoff_icon = "✓"
                playoff_color = TextColors.SUCCESS
            elif "Super Bowl" in playoff_result or "Conference" in playoff_result:
                playoff_icon = "✓"
                playoff_color = TextColors.SUCCESS
            elif "Did not make" in playoff_result:
                playoff_icon = "✗"
                playoff_color = TextColors.ERROR
            else:
                playoff_icon = "⚠"
                playoff_color = TextColors.WARNING

            self.playoff_label.setText(
                f"Playoffs: {playoff_result} (Expected: {playoff_expect})  {playoff_icon}"
            )
            self.playoff_label.setStyleSheet(f"color: {playoff_color};")

            # Cap (with type conversion)
            cap_used = int(data.get('cap_used', 0))
            cap_total = int(data.get('cap_total', 255_400_000))

            if cap_total > 0:
                cap_pct = int((cap_used / cap_total * 100))
                cap_remaining = cap_total - cap_used
            else:
                cap_pct = 0
                cap_remaining = 0

            self.cap_used_label.setText(
                f"Cap Utilization: ${cap_used/1e6:.1f}M / ${cap_total/1e6:.1f}M ({cap_pct}%)"
            )
            self.cap_remaining_label.setText(
                f"Cap Space Remaining: ${cap_remaining/1e6:.1f}M"
            )

            # Positions checklist
            # Clear existing
            while self.positions_list_layout.count():
                child = self.positions_list_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Add position rows
            priority_positions = data.get('priority_positions', [])
            if not isinstance(priority_positions, list):
                logger.warning(f"priority_positions should be a list, got {type(priority_positions).__name__}")
                priority_positions = []

            for pos_data in priority_positions:
                if not isinstance(pos_data, dict):
                    continue  # Skip invalid entries

                position = pos_data.get('position', '?')
                addressed = pos_data.get('addressed', False)

                if addressed:
                    player_name = pos_data.get('player', 'Unknown')
                    ovr = pos_data.get('ovr', 0)
                    icon = "✓"
                    color = TextColors.SUCCESS
                    text = f"{icon} {position}: {player_name} ({ovr} OVR)"
                else:
                    icon = "✗"
                    color = TextColors.ERROR
                    text = f"{icon} {position}: NOT ADDRESSED"

                label = QLabel(text)
                label.setFont(Typography.BODY)
                label.setStyleSheet(f"color: {color}; padding: 2px 0;")
                self.positions_list_layout.addWidget(label)

            # Strategy adherence
            adherence = data.get('strategy_adherence')
            strategy_name = data.get('strategy_name')

            # Handle None values for strategy (no season data)
            if adherence is None or strategy_name is None:
                self.strategy_label.setText("Strategy: No season data yet")
                self.strategy_label.setStyleSheet(f"color: {TextColors.ON_LIGHT_SECONDARY};")
            else:
                adherence_pct = int(float(adherence) * 100)
                self.strategy_label.setText(
                    f"Strategy Adherence: {strategy_name}  ✓\n"
                    f"• {adherence_pct}% of moves aligned with directives"
                )
                self.strategy_label.setStyleSheet(f"color: {TextColors.SUCCESS};")

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Failed to set performance data: {e}")
            # Show error state in UI
            self.win_label.setText("Error loading performance data")
            self.win_label.setStyleSheet(f"color: {TextColors.ERROR};")
            self.win_progress.setValue(0)
            self.win_progress.setFormat("Error")
            self.playoff_label.setText("Error loading playoff data")
            self.playoff_label.setStyleSheet(f"color: {TextColors.ERROR};")
            self.cap_used_label.setText("Error loading cap data")
            self.cap_remaining_label.setText("")
            self.strategy_label.setText("Error loading strategy data")
            self.strategy_label.setStyleSheet(f"color: {TextColors.ERROR};")
