"""
Wave Results Dialog - Shows FA wave completion results.

Displays successful signings and rejected offers after wave resolution.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QFrame,
    QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from game_cycle_ui.theme import (
    Colors, SECONDARY_BUTTON_STYLE, PRIMARY_BUTTON_STYLE,
    Typography, FontSizes, TextColors, apply_table_style
)
from constants.position_abbreviations import get_position_abbreviation


class WaveResultsDialog(QDialog):
    """
    Dialog showing Free Agency wave resolution results.

    Displays:
    - Players successfully signed by user
    - Players who rejected offers
    - Summary statistics
    """

    def __init__(
        self,
        results: Optional[List[Dict[str, Any]]] = None,
        wave_number: int = 1,
        result_data: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        """
        Initialize dialog with signing results.

        Args:
            results: List of individual signing results (new pattern):
                [{"player_name": str, "position": str, "success": bool, "details": dict}, ...]
            wave_number: Wave number for display
            result_data: Legacy pattern with user_signings, user_lost_bids keys
            parent: Parent widget
        """
        super().__init__(parent)
        self._results = results or []
        self._wave_number = wave_number
        self._result_data = result_data
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(f"Wave {self._wave_number} Results")
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)
        self.setMaximumHeight(600)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Use new pattern if results provided, otherwise fall back to legacy
        if self._results:
            self._create_results_ui(layout)
        elif self._result_data:
            self._create_legacy_ui(layout)
        else:
            self._create_empty_ui(layout)

        # Close Button
        self._create_buttons(layout)

    def _create_results_ui(self, parent_layout):
        """Create UI for new results pattern."""
        # Header
        header = QLabel(f"Wave {self._wave_number} Results")
        header.setFont(Typography.H3)
        header.setAlignment(Qt.AlignCenter)
        parent_layout.addWidget(header)

        # Scrollable results area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setSpacing(10)
        results_layout.setContentsMargins(0, 0, 0, 0)

        # Sort: signed first, then rejected
        signed = [r for r in self._results if r.get("success")]
        rejected = [r for r in self._results if not r.get("success")]

        for result in signed + rejected:
            card = self._create_result_card(result)
            results_layout.addWidget(card)

        results_layout.addStretch()
        scroll.setWidget(results_widget)
        parent_layout.addWidget(scroll, 1)

        # Summary
        self._create_results_summary(parent_layout)

    def _create_result_card(self, result: Dict[str, Any]) -> QFrame:
        """Create a card showing one signing result - Badge-Focused minimal design."""
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)

        success = result.get("success", False)
        player_name = result.get("player_name", "Unknown")
        position_raw = result.get("position", "")
        details = result.get("details", {})

        # Convert position to abbreviation (e.g., "outside_linebacker" -> "OLB")
        position = get_position_abbreviation(position_raw) if position_raw else ""

        # Neutral card background for both states
        frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(6)
        layout.setContentsMargins(14, 10, 14, 10)

        # Top row: name, position, status badge
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Player name
        name_label = QLabel(f"<b>{player_name}</b>")
        name_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        top_row.addWidget(name_label)

        # Position abbreviation
        if position:
            pos_label = QLabel(position)
            pos_label.setStyleSheet("color: #999999; font-size: 12px;")
            top_row.addWidget(pos_label)

        top_row.addStretch()

        # Status badge (colored pill) - only colored element
        status_text = "SIGNED" if success else "REJECTED"
        badge_bg = "#2E7D32" if success else "#C62828"
        status_badge = QLabel(status_text)
        status_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 10px;
                border-radius: 10px;
            }}
        """)
        top_row.addWidget(status_badge)

        layout.addLayout(top_row)

        # Details row - all in neutral gray tones
        if success:
            # Show contract details
            contract = details if isinstance(details, dict) else {}
            years = contract.get("years", 0)
            aav = contract.get("aav", 0)

            if years and aav:
                contract_text = f"{years}yr, ${aav:,.0f}/yr"
                detail_label = QLabel(contract_text)
                detail_label.setStyleSheet("color: #cccccc; font-size: 12px;")
                layout.addWidget(detail_label)

            total = contract.get("total_value", contract.get("total", 0))
            guaranteed = contract.get("guaranteed", contract.get("guaranteed_money", 0))
            if total and guaranteed:
                guarantee_text = f"${total:,.0f} total, ${guaranteed:,.0f} guaranteed"
                guarantee_label = QLabel(guarantee_text)
                guarantee_label.setStyleSheet("color: #888888; font-size: 11px;")
                layout.addWidget(guarantee_label)
        else:
            # Show rejection reason
            reason = details.get("reason", "Player declined offer")
            reason_label = QLabel(reason)
            reason_label.setStyleSheet("color: #cccccc; font-size: 12px;")
            reason_label.setWordWrap(True)
            layout.addWidget(reason_label)

            # Show concerns if available
            concerns = details.get("concerns", [])
            if concerns:
                concerns_text = " • ".join(concerns[:2])  # Show max 2 concerns
                concerns_label = QLabel(concerns_text)
                concerns_label.setStyleSheet("color: #888888; font-size: 11px;")
                concerns_label.setWordWrap(True)
                layout.addWidget(concerns_label)

        return frame

    def _create_results_summary(self, parent_layout):
        """Summary for new results pattern."""
        signed_count = sum(1 for r in self._results if r.get("success"))
        rejected_count = len(self._results) - signed_count

        summary_frame = QFrame()
        summary_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_SECONDARY};
                border-radius: 4px;
                padding: 8px;
            }}
        """)

        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(10, 8, 10, 8)

        summary_parts = []
        if signed_count > 0:
            summary_parts.append(f"<span style='color: #4caf50;'>{signed_count} signed</span>")
        if rejected_count > 0:
            summary_parts.append(f"<span style='color: #f44336;'>{rejected_count} rejected</span>")

        summary_text = " • ".join(summary_parts) if summary_parts else "No results"

        label = QLabel(summary_text)
        label.setAlignment(Qt.AlignCenter)
        summary_layout.addWidget(label)

        parent_layout.addWidget(summary_frame)

    def _create_legacy_ui(self, parent_layout):
        """Create UI for legacy result_data pattern (backward compatibility)."""
        # Header
        header = QLabel("Wave Complete!")
        header.setFont(Typography.H3)
        header.setAlignment(Qt.AlignCenter)
        parent_layout.addWidget(header)

        wave_name = self._result_data.get("wave_name", "Unknown Wave")
        subtitle = QLabel(f"{wave_name} - All offers have been resolved")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.BODY};")
        parent_layout.addWidget(subtitle)

        # Successful Signings Section
        self._create_signings_section(parent_layout)

        # Lost Bids Section
        self._create_lost_bids_section(parent_layout)

        # Summary Footer
        self._create_summary(parent_layout)

    def _create_signings_section(self, parent_layout):
        """Show players user successfully signed."""
        user_signings = self._result_data.get("user_signings", [])

        section_label = QLabel(f"✅ Your Signings ({len(user_signings)})")
        section_label.setFont(Typography.H5)
        section_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        parent_layout.addWidget(section_label)

        if user_signings:
            table = self._create_player_table(user_signings)
            parent_layout.addWidget(table)
        else:
            no_signings = QLabel("No players signed this wave.")
            no_signings.setStyleSheet("color: #999; font-style: italic; padding: 10px;")
            parent_layout.addWidget(no_signings)

    def _create_lost_bids_section(self, parent_layout):
        """Show bids user lost (players signed elsewhere)."""
        lost_bids = self._result_data.get("user_lost_bids", [])

        if not lost_bids:
            return  # Don't show section if no lost bids

        section_label = QLabel(f"❌ Lost Bids ({len(lost_bids)})")
        section_label.setFont(Typography.H5)
        section_label.setStyleSheet(f"color: {Colors.ERROR};")
        parent_layout.addWidget(section_label)

        table = self._create_player_table(lost_bids, show_team=True)
        parent_layout.addWidget(table)

    def _create_player_table(self, players: List[Dict], show_team: bool = False):
        """Create table showing player details."""
        columns = ["Player", "Contract"]
        if show_team:
            columns.append("Signed With")

        table = QTableWidget(len(players), len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.verticalHeader().setVisible(False)

        # Apply standardized table styling
        apply_table_style(table)

        for row, player in enumerate(players):
            # Player name
            name_item = QTableWidgetItem(player.get("player_name", "Unknown"))
            table.setItem(row, 0, name_item)

            # Contract
            aav = player.get("aav", 0)
            years = player.get("years", 0)
            contract_text = f"{years}yr / ${aav:,}"
            contract_item = QTableWidgetItem(contract_text)
            contract_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 1, contract_item)

            # Signed With (for lost bids)
            if show_team:
                team_item = QTableWidgetItem(player.get("team_name", "Unknown"))
                team_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 2, team_item)

        # Auto-resize columns
        table.resizeColumnsToContents()
        table.setMaximumHeight(200)

        return table

    def _create_summary(self, parent_layout):
        """Summary statistics for legacy pattern."""
        user_signings = self._result_data.get("user_signings", [])
        lost_bids = self._result_data.get("user_lost_bids", [])
        pending = self._result_data.get("pending_offers", 0)

        summary_frame = QFrame()
        summary_frame.setFrameStyle(QFrame.StyledPanel)
        summary_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 4px;")

        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(10, 8, 10, 8)

        # Summary text
        summary_text = (
            f"<b>Summary:</b> "
            f"{len(user_signings)} signed • "
            f"{len(lost_bids)} lost • "
            f"{pending} pending offers"
        )
        summary_label = QLabel(summary_text)
        summary_layout.addWidget(summary_label)

        parent_layout.addWidget(summary_frame)

    def _create_empty_ui(self, parent_layout):
        """Show when no results available."""
        label = QLabel("No results to display")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
        parent_layout.addWidget(label)

    def _create_buttons(self, parent_layout):
        """Close button."""
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Continue")
        close_btn.setDefault(True)
        close_btn.setMinimumWidth(120)
        close_btn.setMinimumHeight(36)
        close_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        button_layout.addStretch()
        parent_layout.addLayout(button_layout)
