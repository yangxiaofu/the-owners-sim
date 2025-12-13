"""
Free Agency View - Shows available free agents for signing.

Allows the user to see available free agents and sign them to their team.
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QComboBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QBrush

from game_cycle_ui.theme import UITheme, TABLE_HEADER_STYLE
from constants.position_abbreviations import get_position_abbreviation


class FreeAgencyView(QWidget):
    """
    View for the free agency stage.

    Shows a table of available free agents with sign buttons.
    Users can filter by position and minimum overall rating.
    """

    # Signals emitted when user clicks Sign/Unsign button
    player_signed = Signal(int)  # player_id
    player_unsigned = Signal(int)  # player_id - for removing pending signings
    cap_validation_changed = Signal(bool, int)  # (is_valid, over_cap_amount)

    # Wave-based FA signals (Tollgate 5)
    offer_submitted = Signal(int, dict)       # player_id, offer_details
    offer_withdrawn = Signal(int)             # offer_id
    process_day_requested = Signal()          # Advance day within wave
    process_wave_requested = Signal()         # Resolve offers, advance wave

    # Default NFL salary cap (2024 value)
    DEFAULT_CAP_LIMIT = 255_400_000

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._free_agents: List[Dict] = []
        self._filtered_agents: List[Dict] = []
        self._signed_players: set = set()  # Track pending signings
        self._cap_limit: int = self.DEFAULT_CAP_LIMIT  # Current season cap limit
        self._available_cap_space: int = 0  # Track for affordability check
        self._player_interests: Dict[int, Dict] = {}  # player_id -> interest data
        self._user_team_name: str = "Your Team"  # Team name for signing dialog

        # Wave state tracking (Tollgate 5)
        self._wave_mode: bool = False         # True when wave-based FA is active
        self._current_wave: int = 0           # 0-4
        self._current_day: int = 1
        self._days_in_wave: int = 1
        self._wave_name: str = ""
        self._pending_offers_count: int = 0
        self._player_offer_status: Dict[int, Dict] = {}  # player_id -> {count, has_user_offer}

        self._setup_ui()

    @property
    def cap_limit(self) -> int:
        """Get the current salary cap limit."""
        return self._cap_limit

    @cap_limit.setter
    def cap_limit(self, value: int) -> None:
        """Set the salary cap limit (updates each season)."""
        self._cap_limit = value

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Wave header (hidden by default, shown when set_wave_info called)
        self._create_wave_header(layout)

        # Summary panel at top
        self._create_summary_panel(layout)

        # Filter panel
        self._create_filter_panel(layout)

        # Main table of free agents
        self._create_players_table(layout)

        # Wave control panel (hidden by default)
        self._create_wave_controls(layout)

        # Action instructions
        self._create_instructions(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing cap space and counts."""
        summary_group = QGroupBox("Free Agency Summary")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.setSpacing(30)

        # Cap space
        cap_frame = QFrame()
        cap_layout = QVBoxLayout(cap_frame)
        cap_layout.setContentsMargins(0, 0, 0, 0)

        cap_title = QLabel("Available Cap Space")
        cap_title.setStyleSheet("color: #666; font-size: 11px;")
        cap_layout.addWidget(cap_title)

        self.cap_space_label = QLabel("$0")
        self.cap_space_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.cap_space_label.setStyleSheet("color: #2E7D32;")  # Green
        cap_layout.addWidget(self.cap_space_label)

        summary_layout.addWidget(cap_frame)

        # Free agents count
        fa_frame = QFrame()
        fa_layout = QVBoxLayout(fa_frame)
        fa_layout.setContentsMargins(0, 0, 0, 0)

        fa_title = QLabel("Available Free Agents")
        fa_title.setStyleSheet("color: #666; font-size: 11px;")
        fa_layout.addWidget(fa_title)

        self.fa_count_label = QLabel("0")
        self.fa_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        fa_layout.addWidget(self.fa_count_label)

        summary_layout.addWidget(fa_frame)

        # Projected cap (after pending signings)
        projected_frame = QFrame()
        projected_layout = QVBoxLayout(projected_frame)
        projected_layout.setContentsMargins(0, 0, 0, 0)

        projected_title = QLabel("Projected Cap")
        projected_title.setStyleSheet("color: #666; font-size: 11px;")
        projected_layout.addWidget(projected_title)

        self.projected_cap_label = QLabel("$0")
        self.projected_cap_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.projected_cap_label.setStyleSheet("color: #1976D2;")  # Blue
        projected_layout.addWidget(self.projected_cap_label)

        summary_layout.addWidget(projected_frame)

        # Pending signings
        pending_frame = QFrame()
        pending_layout = QVBoxLayout(pending_frame)
        pending_layout.setContentsMargins(0, 0, 0, 0)

        pending_title = QLabel("Pending Signings")
        pending_title.setStyleSheet("color: #666; font-size: 11px;")
        pending_layout.addWidget(pending_title)

        self.pending_count_label = QLabel("0")
        self.pending_count_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.pending_count_label.setStyleSheet("color: #1976D2;")  # Blue
        pending_layout.addWidget(self.pending_count_label)

        summary_layout.addWidget(pending_frame)

        # Cap rollover (carryover from previous season)
        rollover_frame = QFrame()
        rollover_layout = QVBoxLayout(rollover_frame)
        rollover_layout.setContentsMargins(0, 0, 0, 0)

        rollover_title = QLabel("Cap Rollover")
        rollover_title.setStyleSheet("color: #666; font-size: 11px;")
        rollover_layout.addWidget(rollover_title)

        self.rollover_label = QLabel("$0")
        self.rollover_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.rollover_label.setStyleSheet("color: #7B1FA2;")  # Purple
        rollover_layout.addWidget(self.rollover_label)

        summary_layout.addWidget(rollover_frame)

        summary_layout.addStretch()

        parent_layout.addWidget(summary_group)

    def _create_filter_panel(self, parent_layout: QVBoxLayout):
        """Create filter controls for position and overall."""
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 5, 10, 5)

        # Position filter
        pos_label = QLabel("Position:")
        filter_layout.addWidget(pos_label)

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
        self.position_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.position_combo)

        filter_layout.addSpacing(20)

        # Min overall filter
        ovr_label = QLabel("Min Overall:")
        filter_layout.addWidget(ovr_label)

        self.min_overall_spin = QSpinBox()
        self.min_overall_spin.setRange(0, 99)
        self.min_overall_spin.setValue(60)
        self.min_overall_spin.valueChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.min_overall_spin)

        filter_layout.addStretch()

        parent_layout.addWidget(filter_frame)

    def _create_players_table(self, parent_layout: QVBoxLayout):
        """Create the main table of free agents."""
        table_group = QGroupBox("Available Free Agents")
        table_layout = QVBoxLayout(table_group)

        self.players_table = QTableWidget()
        self.players_table.setColumnCount(10)  # Added Interest column
        self.players_table.setHorizontalHeaderLabels([
            "Player", "Position", "Age", "OVR", "Potential", "Dev", "Est. AAV",
            "Interest", "Status", "Action"  # Interest added between AAV and Status
        ])

        # Configure table appearance
        header = self.players_table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Position
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Age
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # OVR
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Potential
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # Dev - narrow column
        header.resizeSection(5, 50)  # Dev column width
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Est. AAV
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # Interest - fixed width
        header.resizeSection(7, 60)  # Interest column width
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(9, QHeaderView.Fixed)  # Action
        header.resizeSection(9, 100)  # Action column width

        self.players_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.players_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.players_table.setAlternatingRowColors(True)
        self.players_table.verticalHeader().setVisible(False)

        table_layout.addWidget(self.players_table)
        parent_layout.addWidget(table_group, stretch=1)

    def _create_instructions(self, parent_layout: QVBoxLayout):
        """Create collapsible help panel with wave-based instructions."""
        # Create a collapsible group box for wave mode instructions
        self._help_group = QGroupBox("How Free Agency Works (click to expand)")
        self._help_group.setCheckable(True)
        self._help_group.setChecked(False)  # Collapsed by default
        self._help_group.toggled.connect(self._on_help_toggled)

        help_layout = QVBoxLayout(self._help_group)
        help_layout.setContentsMargins(10, 5, 10, 10)
        help_layout.setSpacing(8)

        # Wave mode instructions (shown when expanded)
        self._wave_instructions = QLabel(
            "<b>Free Agency progresses in waves:</b><br/>"
            "<br/>"
            "<b>1. Legal Tampering (Wave 0):</b> View available players, no signing yet.<br/>"
            "<b>2. Wave 1 - Elite:</b> Top-tier players (OVR 85+) available.<br/>"
            "<b>3. Wave 2 - Quality:</b> Quality starters (OVR 75-84) available.<br/>"
            "<b>4. Wave 3 - Depth:</b> Depth players (OVR 65-74) available.<br/>"
            "<b>5. Post-Draft:</b> All remaining free agents (after the draft).<br/>"
            "<br/>"
            "<b>How to sign players:</b><br/>"
            "- Click <b>'Sign'</b> on a player to submit an offer at market value<br/>"
            "- Players collect all offers during the wave, then choose at wave end<br/>"
            "<br/>"
            "<b>Wave Control Buttons:</b><br/>"
            "- <b>'Process Day'</b> - Advance one day (AI teams submit offers)<br/>"
            "- <b>'Process Wave' / 'Begin Signing Period'</b> - End current wave, resolve all offers, advance to next<br/>"
            "<br/>"
            "<i>Tip: AI teams also submit offers. Players may sign with other teams!</i>"
        )
        self._wave_instructions.setWordWrap(True)
        self._wave_instructions.setStyleSheet("color: #333; font-size: 12px; line-height: 1.4;")
        self._wave_instructions.setVisible(False)  # Hidden until expanded
        help_layout.addWidget(self._wave_instructions)

        # Legacy mode instructions (simple footer)
        self._legacy_instructions = QLabel(
            "Click 'Sign' to add a free agent to your team. "
            "Signed players will receive a market-value contract. "
            "Click 'Process Free Agency' when done to finalize signings."
        )
        self._legacy_instructions.setWordWrap(True)
        self._legacy_instructions.setStyleSheet("color: #666; font-style: italic;")
        help_layout.addWidget(self._legacy_instructions)

        parent_layout.addWidget(self._help_group)

    def _on_help_toggled(self, checked: bool):
        """Handle help group box toggle."""
        self._wave_instructions.setVisible(checked)
        if checked:
            self._help_group.setTitle("How Free Agency Works (click to collapse)")
        else:
            self._help_group.setTitle("How Free Agency Works (click to expand)")

    def set_free_agents(self, players: List[Dict]):
        """
        Populate the table with free agents.

        Preserves pending offer state (_signed_players) during refresh.
        Only clear when explicitly requested via clear_pending_state().

        Args:
            players: List of player dictionaries with:
                - player_id: int
                - name: str
                - position: str
                - age: int
                - overall: int
                - estimated_aav: int
        """
        self._free_agents = players
        # DON'T clear _signed_players - preserve pending offers during refresh
        # self._signed_players.clear()  # ← REMOVED
        self.fa_count_label.setText(str(len(players)))
        # Keep pending count as-is (will be updated by set_pending_offers_count if needed)
        # self.pending_count_label.setText("0")  # ← REMOVED
        self._apply_filters()

    def set_cap_space(self, cap_space: int):
        """Update the cap space display."""
        formatted = f"${cap_space:,}"
        self.cap_space_label.setText(formatted)

        # Color based on cap space (red if negative)
        if cap_space < 0:
            self.cap_space_label.setStyleSheet("color: #C62828;")  # Red
        else:
            self.cap_space_label.setStyleSheet("color: #2E7D32;")  # Green

    def set_cap_data(self, cap_data: Dict):
        """
        Update the view with full cap data from CapHelper.

        Args:
            cap_data: Dict with available_space, salary_cap_limit, total_spending,
                      dead_money, is_compliant, projected_available (optional), carryover
        """
        available = cap_data.get("available_space", 0)
        self._available_cap_space = available  # Store for affordability checks
        self.set_cap_space(available)

        # Update cap limit from data if provided
        if "salary_cap_limit" in cap_data:
            self.cap_limit = cap_data["salary_cap_limit"]

        # Set projected cap (defaults to available if no pending signings)
        projected = cap_data.get("projected_available", available)
        self.set_projected_cap(projected)

        # Update rollover label (carryover from previous season)
        carryover = cap_data.get("carryover", 0)
        self.rollover_label.setText(f"${carryover:,}")

        # Refresh table to update affordability indicators
        if self._free_agents:
            self._apply_filters()

    def set_projected_cap(self, projected: int):
        """
        Update the projected cap space display.

        Color coding from theme:
        - projected (blue): Healthy cap space
        - tight (orange): Less than 10% of cap remaining
        - over_cap (red): Negative cap space

        Args:
            projected: Projected cap space after pending signings
        """
        self.projected_cap_label.setText(f"${projected:,}")

        # Get threshold from theme
        tight_threshold = UITheme.get_threshold("cap_space", "tight_percentage")

        # Color coding based on cap health
        if projected < 0:
            color = UITheme.get_color("cap_space", "over_cap")
        elif projected < self._cap_limit * tight_threshold:
            color = UITheme.get_color("cap_space", "tight")
        else:
            color = UITheme.get_color("cap_space", "projected")

        self.projected_cap_label.setStyleSheet(f"color: {color};")

        # Emit cap validation signal to enable/disable Process button
        is_over_cap = projected < 0
        over_cap_amount = abs(projected) if is_over_cap else 0
        self.cap_validation_changed.emit(not is_over_cap, over_cap_amount)

    def _apply_filters(self):
        """Apply position and overall filters to the free agent list."""
        position_filter = self.position_combo.currentData()
        min_overall = self.min_overall_spin.value()

        self._filtered_agents = []
        for player in self._free_agents:
            # DON'T skip signed players - keep them visible with "Offer Pending" status
            # if player["player_id"] in self._signed_players:
            #     continue

            # Position filter
            if position_filter:
                player_pos = player.get("position", "").lower().replace(" ", "_")
                if player_pos != position_filter:
                    continue

            # Overall filter
            if player.get("overall", 0) < min_overall:
                continue

            self._filtered_agents.append(player)

        # Update table
        self.players_table.setRowCount(len(self._filtered_agents))
        for row, player in enumerate(self._filtered_agents):
            self._populate_row(row, player)

        # Update filtered count display
        self.fa_count_label.setText(str(len(self._filtered_agents)))

    def _populate_row(self, row: int, player: Dict):
        """Populate a single row in the table."""
        player_id = player.get("player_id", 0)
        aav = player.get("estimated_aav", 0)

        # Calculate affordability using projected cap (after pending signings)
        projected_cap = self._calculate_projected_cap()
        can_afford = aav <= projected_cap

        # Player name
        name_item = QTableWidgetItem(player.get("name", "Unknown"))
        name_item.setData(Qt.UserRole, player_id)
        self.players_table.setItem(row, 0, name_item)

        # Position - convert to standard NFL abbreviation
        position = player.get("position", "")
        pos_item = QTableWidgetItem(get_position_abbreviation(position))
        pos_item.setTextAlignment(Qt.AlignCenter)
        self.players_table.setItem(row, 1, pos_item)

        # Age
        age = player.get("age", 0)
        age_item = QTableWidgetItem(str(age))
        age_item.setTextAlignment(Qt.AlignCenter)
        # Color code age (red if 30+)
        if age >= 30:
            age_item.setForeground(QColor("#C62828"))  # Red
        self.players_table.setItem(row, 2, age_item)

        # Overall rating
        overall = player.get("overall", 0)
        ovr_item = QTableWidgetItem(str(overall))
        ovr_item.setTextAlignment(Qt.AlignCenter)
        # Color code rating
        if overall >= 85:
            ovr_item.setForeground(QColor("#2E7D32"))  # Green - Elite
        elif overall >= 75:
            ovr_item.setForeground(QColor("#1976D2"))  # Blue - Solid
        self.players_table.setItem(row, 3, ovr_item)

        # Potential rating with color coding
        potential = player.get("potential", 0)
        potential_item = QTableWidgetItem(str(potential))
        potential_item.setTextAlignment(Qt.AlignCenter)
        # Color code potential based on upside
        if potential > 0 and overall > 0:
            upside = potential - overall
            if upside <= 2:
                # Near ceiling - Green
                potential_item.setForeground(QColor("#2E7D32"))
            elif upside >= 10:
                # High upside - Blue
                potential_item.setForeground(QColor("#1976D2"))
        self.players_table.setItem(row, 4, potential_item)

        # Dev type - badge style display
        dev_type = player.get("dev_type", "normal")
        dev_map = {
            "early": "E",
            "normal": "N",
            "late": "L"
        }
        dev_color_map = {
            "early": "#FF6F00",  # Orange
            "normal": "#666666",  # Gray
            "late": "#1976D2"    # Blue
        }
        dev_text = dev_map.get(dev_type, "N")
        dev_color = dev_color_map.get(dev_type, "#666666")
        dev_item = QTableWidgetItem(dev_text)
        dev_item.setTextAlignment(Qt.AlignCenter)
        dev_item.setForeground(QColor(dev_color))
        self.players_table.setItem(row, 5, dev_item)

        # Estimated AAV - color red if unaffordable
        aav_text = f"${aav:,}" if aav else "N/A"
        aav_item = QTableWidgetItem(aav_text)
        aav_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if not can_afford:
            aav_item.setForeground(QColor("#C62828"))  # Red - unaffordable
        self.players_table.setItem(row, 6, aav_item)

        # Interest score - color coded (column 7)
        interest_data = self._player_interests.get(player_id, {})
        interest_score = interest_data.get("interest_score", 50)
        interest_item = QTableWidgetItem(str(interest_score))
        interest_item.setTextAlignment(Qt.AlignCenter)

        # Color coding based on interest score bands
        if interest_score >= 80:
            interest_item.setBackground(QBrush(QColor("#2E7D32")))  # Green
            interest_item.setForeground(QBrush(QColor("white")))
        elif interest_score >= 65:
            interest_item.setBackground(QBrush(QColor("#1976D2")))  # Blue
            interest_item.setForeground(QBrush(QColor("white")))
        elif interest_score >= 50:
            interest_item.setBackground(QBrush(QColor("#666666")))  # Gray
            interest_item.setForeground(QBrush(QColor("white")))
        elif interest_score >= 35:
            interest_item.setBackground(QBrush(QColor("#F57C00")))  # Orange
            interest_item.setForeground(QBrush(QColor("white")))
        else:
            interest_item.setBackground(QBrush(QColor("#C62828")))  # Red
            interest_item.setForeground(QBrush(QColor("white")))

        # Add tooltip with concerns and persona hint
        concerns = interest_data.get("concerns", [])
        persona_type = interest_data.get("persona_type", "unknown")
        tooltip_parts = []
        if persona_type != "unknown":
            hint = self._get_persona_hint(persona_type)
            tooltip_parts.append(f"Type: {persona_type.replace('_', ' ').title()}")
            if hint:
                tooltip_parts.append(f"({hint})")
        if concerns:
            tooltip_parts.append("\nConcerns:")
            for concern in concerns[:3]:  # Show max 3 concerns
                tooltip_parts.append(f"• {concern}")
        if tooltip_parts:
            interest_item.setToolTip("\n".join(tooltip_parts))

        self.players_table.setItem(row, 7, interest_item)

        # Status - show "Can't Afford" if unaffordable (column 8)
        if can_afford:
            status_item = QTableWidgetItem("Available")
            status_item.setForeground(QColor("#666"))
        else:
            status_item = QTableWidgetItem("Can't Afford")
            status_item.setForeground(QColor("#C62828"))  # Red
        status_item.setTextAlignment(Qt.AlignCenter)
        self.players_table.setItem(row, 8, status_item)

        # Action button - disable if unaffordable (column 9)
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        sign_btn = QPushButton("Sign")
        sign_btn.setEnabled(can_afford)  # Disable if can't afford
        if can_afford:
            sign_btn.setStyleSheet(
                "QPushButton { background-color: #2E7D32; color: white; border-radius: 3px; padding: 4px 12px; }"
                "QPushButton:hover { background-color: #1B5E20; }"
            )
        else:
            sign_btn.setStyleSheet(
                "QPushButton { background-color: #ccc; color: #666; border-radius: 3px; padding: 4px 12px; }"
            )
            sign_btn.setToolTip(f"Insufficient cap space. Need ${aav:,}, have ${projected_cap:,}")
        sign_btn.clicked.connect(lambda checked, pid=player_id, r=row: self._on_sign_clicked(pid, r))
        action_layout.addWidget(sign_btn)

        self.players_table.setCellWidget(row, 9, action_widget)

        # Check if player has pending offer and update row appearance
        if player_id in self._signed_players:
            self._update_row_for_pending_offer(row)

    def _on_sign_clicked(self, player_id: int, row: int):
        """Handle sign/unsign button click.

        In wave mode: Creates offer at market value (Quick Sign).
        In legacy mode: Opens signing dialog.
        """
        if player_id in self._signed_players:
            # UNSIGN - remove from pending (no dialog needed)
            self._signed_players.discard(player_id)
            self._update_row_unsigned(row)
            self._update_pending_count()
            self.player_unsigned.emit(player_id)
            # Refresh affordability for all visible players
            self._refresh_affordability()
        elif self._wave_mode:
            # WAVE MODE: Quick Sign - create offer at market value
            player_data = self._get_player_from_row(row, player_id)
            estimated_aav = player_data.get("estimated_aav", 5_000_000)

            # Build offer data at market value
            offer_data = {
                "aav": estimated_aav,
                "years": 3,  # Standard 3-year offer
                "guaranteed": int(estimated_aav * 0.5),  # 50% guaranteed
                "signing_bonus": int(estimated_aav * 0.1),  # 10% signing bonus
            }

            # Emit offer_submitted signal (controller listens to this)
            self.offer_submitted.emit(player_id, offer_data)

            # Track locally for UI state
            self._signed_players.add(player_id)
            self._update_row_for_pending_offer(row)
            self._update_pending_count()

            # Refresh affordability for all visible players
            self._refresh_affordability()
        else:
            # LEGACY MODE: Show signing dialog first
            self._show_signing_dialog(player_id, row)

    def _show_signing_dialog(self, player_id: int, row: int):
        """Show signing dialog with player preferences before signing."""
        from game_cycle_ui.dialogs.signing_dialog import SigningDialog

        # Get player info from the row
        player_info = self._get_player_from_row(row, player_id)

        # Get interest and persona data
        interest_data = self._player_interests.get(player_id, {
            "interest_score": 50,
            "interest_level": "medium",
            "acceptance_probability": 0.5,
            "concerns": [],
            "persona_type": "unknown"
        })

        # Persona data should come from the controller - use interest_data for now
        # (Controller should set this via set_player_interests with full persona data)
        persona_data = {
            "persona_type": interest_data.get("persona_type", "unknown"),
            "money_importance": 50,
            "winning_importance": 50,
            "location_importance": 50,
            "playing_time_importance": 50,
            "loyalty_importance": 50,
            "market_size_importance": 50
        }

        # Try to get full persona data from stored data or request
        if hasattr(self, '_persona_data_cache') and player_id in self._persona_data_cache:
            persona_data = self._persona_data_cache[player_id]

        dialog = SigningDialog(
            parent=self,
            player_info=player_info,
            interest_data=interest_data,
            persona_data=persona_data,
            team_name=self._user_team_name
        )

        if dialog.exec() == SigningDialog.Accepted:
            # User chose to proceed - add to pending signings
            self._signed_players.add(player_id)
            self._update_row_signed(row)
            self._update_pending_count()
            self.player_signed.emit(player_id)
            # Refresh affordability for all visible players
            self._refresh_affordability()

    def _get_player_from_row(self, row: int, player_id: int) -> Dict:
        """Get player info dictionary from table row."""
        # Find player in filtered agents
        for player in self._filtered_agents:
            if player.get("player_id") == player_id:
                return {
                    "name": player.get("name", "Unknown"),
                    "position": player.get("position", ""),
                    "overall": player.get("overall", 0),
                    "age": player.get("age", 0),
                    "potential": player.get("potential", 0),
                    "estimated_aav": player.get("estimated_aav", 0)
                }

        # Fallback to reading from table cells
        name_item = self.players_table.item(row, 0)
        pos_item = self.players_table.item(row, 1)
        ovr_item = self.players_table.item(row, 3)

        return {
            "name": name_item.text() if name_item else "Unknown",
            "position": pos_item.text() if pos_item else "",
            "overall": int(ovr_item.text()) if ovr_item and ovr_item.text().isdigit() else 0
        }

    def set_persona_data(self, persona_data: Dict[int, Dict]):
        """Set full persona data for signing dialogs.

        Args:
            persona_data: Dict mapping player_id to persona dict with:
                - persona_type: str
                - money_importance: int (0-100)
                - winning_importance: int (0-100)
                - location_importance: int (0-100)
                - playing_time_importance: int (0-100)
                - loyalty_importance: int (0-100)
                - market_size_importance: int (0-100)
        """
        if not hasattr(self, '_persona_data_cache'):
            self._persona_data_cache = {}
        self._persona_data_cache = persona_data

    def _update_row_signed(self, row: int):
        """Update row appearance when player is marked for signing."""
        # Update status cell (column 8 after adding Interest column)
        status_item = self.players_table.item(row, 8)
        if status_item:
            status_item.setText("Signing")
            color = UITheme.get_color("status", "success")
            status_item.setForeground(QColor(color))

        # Change button to "Unsign" with warning color (column 9)
        action_widget = self.players_table.cellWidget(row, 9)
        if action_widget:
            for child in action_widget.children():
                if isinstance(child, QPushButton):
                    child.setText("Unsign")
                    child.setStyleSheet(UITheme.button_style("warning"))

    def _update_row_for_pending_offer(self, row: int):
        """Update row appearance when offer is pending (wave mode).

        Shows "Offer Pending" status with blue color and "Withdraw" button.
        """
        # Update status cell (column 8)
        status_item = self.players_table.item(row, 8)
        if status_item:
            status_item.setText("Offer Pending")
            status_item.setForeground(QColor("#1976D2"))  # Blue

        # Change button to "Withdraw" with warning color (column 9)
        action_widget = self.players_table.cellWidget(row, 9)
        if action_widget:
            for child in action_widget.children():
                if isinstance(child, QPushButton):
                    child.setText("Withdraw")
                    child.setStyleSheet(
                        "QPushButton { background-color: #F57C00; color: white; "
                        "border-radius: 3px; padding: 4px 12px; }"
                        "QPushButton:hover { background-color: #E65100; }"
                    )

    def _update_row_unsigned(self, row: int):
        """Update row appearance when player is unmarked (unsigned)."""
        # Update status cell (column 8 after adding Interest column)
        status_item = self.players_table.item(row, 8)
        if status_item:
            status_item.setText("Available")
            color = UITheme.get_color("status", "neutral")
            status_item.setForeground(QColor(color))

        # Change button back to "Sign" with primary color (column 9)
        action_widget = self.players_table.cellWidget(row, 9)
        if action_widget:
            for child in action_widget.children():
                if isinstance(child, QPushButton):
                    child.setText("Sign")
                    child.setStyleSheet(UITheme.button_style("primary"))

    def _update_pending_count(self):
        """Update the count of pending signings."""
        self.pending_count_label.setText(str(len(self._signed_players)))

    def _calculate_projected_cap(self) -> int:
        """
        Calculate cap space remaining after pending signings.

        Returns:
            Projected cap space (base available - pending AAV totals)
        """
        pending_total = sum(
            p.get("estimated_aav", 0)
            for p in self._free_agents
            if p["player_id"] in self._signed_players
        )
        return self._available_cap_space - pending_total

    def _refresh_affordability(self):
        """
        Refresh affordability indicators for all visible rows after signing/unsigning.

        Updates:
        - Projected cap display in summary panel
        - AAV color (red if unaffordable)
        - Status text ("Available" vs "Can't Afford")
        - Sign button enabled state and tooltip
        """
        projected_cap = self._calculate_projected_cap()

        # Update projected cap display
        self.set_projected_cap(projected_cap)

        # Update affordability for each visible row
        for row in range(self.players_table.rowCount()):
            name_item = self.players_table.item(row, 0)
            if not name_item:
                continue

            player_id = name_item.data(Qt.UserRole)

            # Skip already-signed players (they show "Signing" status)
            if player_id in self._signed_players:
                continue

            # Find this player's data
            player = next(
                (p for p in self._filtered_agents if p["player_id"] == player_id),
                None
            )
            if not player:
                continue

            aav = player.get("estimated_aav", 0)
            can_afford = aav <= projected_cap

            # Update AAV color (column 6)
            aav_item = self.players_table.item(row, 6)
            if aav_item:
                if can_afford:
                    aav_item.setForeground(QColor("#333"))  # Default
                else:
                    aav_item.setForeground(QColor("#C62828"))  # Red

            # Update status (column 8 - after Interest at column 7)
            status_item = self.players_table.item(row, 8)
            if status_item:
                if can_afford:
                    status_item.setText("Available")
                    status_item.setForeground(QColor("#666"))
                else:
                    status_item.setText("Can't Afford")
                    status_item.setForeground(QColor("#C62828"))

            # Update button state (column 9 - Action column)
            action_widget = self.players_table.cellWidget(row, 9)
            if action_widget:
                for child in action_widget.children():
                    if isinstance(child, QPushButton) and child.text() == "Sign":
                        child.setEnabled(can_afford)
                        if can_afford:
                            child.setStyleSheet(
                                "QPushButton { background-color: #2E7D32; color: white; "
                                "border-radius: 3px; padding: 4px 12px; }"
                                "QPushButton:hover { background-color: #1B5E20; }"
                            )
                            child.setToolTip("")
                        else:
                            child.setStyleSheet(
                                "QPushButton { background-color: #ccc; color: #666; "
                                "border-radius: 3px; padding: 4px 12px; }"
                            )
                            child.setToolTip(
                                f"Insufficient cap space. Need ${aav:,}, have ${projected_cap:,}"
                            )

    def show_no_free_agents_message(self):
        """Show a message when there are no free agents available."""
        self.players_table.setRowCount(1)
        self.players_table.setSpan(0, 0, 1, 10)  # Span all 10 columns

        message_item = QTableWidgetItem("No free agents available")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#666"))
        message_item.setFont(QFont("Arial", 12, QFont.Normal, True))  # Italic

        self.players_table.setItem(0, 0, message_item)
        self.fa_count_label.setText("0")

    def clear_signed_players(self):
        """Reset signed players (call after processing)."""
        self._signed_players.clear()
        self.pending_count_label.setText("0")
        self._apply_filters()

    def clear_pending_state(self):
        """
        Clear all pending offer state.

        Called when:
        - Wave advances (new wave starts)
        - Stage changes (leaving FA stage)
        - User cancels all offers
        """
        self._signed_players.clear()
        self.pending_count_label.setText("0")
        self._apply_filters()

    def get_signed_player_ids(self) -> List[int]:
        """Get list of player IDs that were signed."""
        return list(self._signed_players)

    def set_player_interests(self, interests: Dict[int, Dict]):
        """Set interest data for all free agents.

        Args:
            interests: Dict mapping player_id to interest data dict with:
                - interest_score: int (0-100)
                - interest_level: str
                - acceptance_probability: float
                - concerns: List[str]
                - persona_type: str
        """
        self._player_interests = interests
        # Refresh display if table is populated
        if self._filtered_agents:
            self._apply_filters()

    def set_user_team_name(self, team_name: str):
        """Set the user's team name for signing dialog."""
        self._user_team_name = team_name

    def get_player_interest(self, player_id: int) -> Dict:
        """Get interest data for a specific player."""
        return self._player_interests.get(player_id, {})

    def _get_persona_hint(self, persona_type: str) -> str:
        """Get user-friendly hint for persona type."""
        hints = {
            "ring_chaser": "Values winning above all",
            "hometown_hero": "Prefers to play near home",
            "money_first": "Follows the money",
            "big_market": "Wants big city exposure",
            "small_market": "Prefers quieter markets",
            "legacy_builder": "Loyal to one team",
            "competitor": "Needs playing time",
            "system_fit": "Values scheme fit"
        }
        return hints.get(persona_type.lower(), "")

    # =========================================================================
    # Wave-based Free Agency Methods (Tollgate 5)
    # =========================================================================

    def _create_wave_header(self, parent_layout: QVBoxLayout):
        """Create wave info header with 5-segment progress indicator."""
        self._wave_header_group = QGroupBox()  # No title - clean look
        wave_layout = QVBoxLayout(self._wave_header_group)
        wave_layout.setContentsMargins(10, 8, 10, 8)

        # Top row: Wave name and day
        top_row = QHBoxLayout()

        self._wave_title_label = QLabel("FREE AGENCY")
        self._wave_title_label.setFont(QFont("Arial", 14, QFont.Bold))
        top_row.addWidget(self._wave_title_label)

        top_row.addStretch()

        self._wave_day_label = QLabel("Day 1/1")
        self._wave_day_label.setFont(QFont("Arial", 12))
        self._wave_day_label.setStyleSheet("color: #666;")
        top_row.addWidget(self._wave_day_label)

        wave_layout.addLayout(top_row)

        # Bottom row: Wave progress indicator (5 segments)
        progress_row = QHBoxLayout()
        progress_row.setSpacing(4)

        self._wave_indicators: List[QFrame] = []
        self._wave_labels: List[QLabel] = []
        wave_names = ["Legal\nTampering", "Wave 1\nElite", "Wave 2\nQuality",
                      "Wave 3\nDepth", "Post-Draft"]

        for i, name in enumerate(wave_names):
            # Container for indicator + label
            segment_widget = QWidget()
            segment_layout = QVBoxLayout(segment_widget)
            segment_layout.setContentsMargins(0, 0, 0, 0)
            segment_layout.setSpacing(2)

            # Progress bar segment
            indicator = QFrame()
            indicator.setFixedHeight(6)
            indicator.setMinimumWidth(60)
            indicator.setStyleSheet("background-color: #ddd; border-radius: 3px;")
            segment_layout.addWidget(indicator)

            # Label below segment
            label = QLabel(name)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-size: 9px; color: #666;")
            segment_layout.addWidget(label)

            self._wave_indicators.append(indicator)
            self._wave_labels.append(label)
            progress_row.addWidget(segment_widget)

            # Arrow between segments (except after last)
            if i < 4:
                arrow = QLabel("→")
                arrow.setStyleSheet("color: #999; font-size: 12px;")
                arrow.setAlignment(Qt.AlignCenter)
                progress_row.addWidget(arrow)

        wave_layout.addLayout(progress_row)

        # Initially hidden (shown when set_wave_info called)
        self._wave_header_group.hide()

        parent_layout.addWidget(self._wave_header_group)

    def _create_wave_controls(self, parent_layout: QVBoxLayout):
        """Create wave control buttons panel."""
        self._wave_controls_frame = QFrame()
        self._wave_controls_frame.setStyleSheet(
            "QFrame { background-color: #263238; border-radius: 6px; }"
        )
        frame_layout = QVBoxLayout(self._wave_controls_frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)
        frame_layout.setSpacing(8)

        # Add instruction label
        instruction_label = QLabel(
            "<i>Wave Controls:</i> "
            "<b>Process Day</b> - Advance one day (AI teams make offers) | "
            "<b>Process Wave</b> - Resolve all offers and advance to next wave"
        )
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("color: #CFD8DC; font-size: 11px; padding: 4px 0px;")
        frame_layout.addWidget(instruction_label)

        # Buttons container
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)

        # Process Day button
        self._process_day_btn = QPushButton("Process Day")
        self._process_day_btn.setToolTip(
            "Advance to next day. AI teams will submit offers and surprise signings may occur."
        )
        self._process_day_btn.setStyleSheet(
            "QPushButton { background-color: #37474F; color: white; "
            "border-radius: 4px; padding: 8px 20px; font-size: 13px; }"
            "QPushButton:hover { background-color: #263238; }"
            "QPushButton:disabled { background-color: #ccc; color: #666; }"
        )
        self._process_day_btn.clicked.connect(self._on_process_day_clicked)
        controls_layout.addWidget(self._process_day_btn)

        controls_layout.addStretch()

        # Days remaining indicator
        self._days_remaining_label = QLabel("Days Remaining: 1")
        self._days_remaining_label.setStyleSheet("color: #B0BEC5; font-size: 12px;")
        controls_layout.addWidget(self._days_remaining_label)

        controls_layout.addStretch()

        # Process Wave button
        self._process_wave_btn = QPushButton("Process Wave")
        self._process_wave_btn.setToolTip(
            "End current wave. All pending offers will be resolved and players will make decisions."
        )
        self._process_wave_btn.setStyleSheet(
            "QPushButton { background-color: #00695C; color: white; "
            "border-radius: 4px; padding: 8px 20px; font-size: 13px; }"
            "QPushButton:hover { background-color: #004D40; }"
            "QPushButton:disabled { background-color: #ccc; color: #666; }"
        )
        self._process_wave_btn.clicked.connect(self._on_process_wave_clicked)
        controls_layout.addWidget(self._process_wave_btn)

        # Add button layout to frame
        frame_layout.addLayout(controls_layout)

        # Initially hidden
        self._wave_controls_frame.hide()

        parent_layout.addWidget(self._wave_controls_frame)

    def _on_process_day_clicked(self):
        """Handle Process Day button click."""
        self.process_day_requested.emit()

    def _on_process_wave_clicked(self):
        """Handle Process Wave button click."""
        self.process_wave_requested.emit()

    def set_wave_info(
        self,
        wave: int,
        wave_name: str,
        day: int,
        days_total: int
    ) -> None:
        """
        Update wave information display.

        Enables wave mode if not already enabled.
        Updates wave header, progress indicator, and control buttons.

        Args:
            wave: Current wave number (0-4)
            wave_name: Display name (e.g., "Wave 1 - Elite Players")
            day: Current day within wave (1-based)
            days_total: Total days in this wave
        """
        # Enable wave mode on first call
        if not self._wave_mode:
            self._enable_wave_mode()

        # DEBUG: Print wave info to help diagnose button text issue
        print(f"[FA View] set_wave_info called: wave={wave}, day={day}/{days_total}, name={wave_name}")

        self._current_wave = wave
        self._current_day = day
        self._days_in_wave = days_total
        self._wave_name = wave_name

        # Update wave title
        self._wave_title_label.setText(f"FREE AGENCY - {wave_name}")

        # Update day display
        self._wave_day_label.setText(f"Day {day}/{days_total}")

        # Update progress indicator colors
        for i, indicator in enumerate(self._wave_indicators):
            if i < wave:
                # Completed wave - green
                indicator.setStyleSheet(
                    "background-color: #2E7D32; border-radius: 3px;"
                )
            elif i == wave:
                # Current wave - blue
                indicator.setStyleSheet(
                    "background-color: #1976D2; border-radius: 3px;"
                )
            else:
                # Future wave - gray
                indicator.setStyleSheet(
                    "background-color: #ddd; border-radius: 3px;"
                )

        # Update days remaining
        days_remaining = days_total - day
        self._days_remaining_label.setText(f"Days Remaining: {days_remaining}")

        # Update button states
        # Process Day disabled on last day (must use Process Wave)
        self._process_day_btn.setEnabled(day < days_total)

        # Process Wave always enabled (can end wave early)
        self._process_wave_btn.setEnabled(True)

        # Update button text based on current wave
        if wave == 0:
            # Legal Tampering - no signing allowed yet
            self._process_day_btn.setText("View Offers")
            self._process_wave_btn.setText("Begin Signing Period")
        elif wave < 3:
            # Waves 1-2 (Elite, Quality)
            self._process_day_btn.setText("Process Day")
            self._process_wave_btn.setText("Process Wave")
        elif wave == 3:
            # Wave 3 (Depth) - button text changes based on wave completion
            self._process_day_btn.setText("Process Day")

            # Dynamic button text based on wave state
            if day < days_total:
                # Days remaining - show progress
                self._process_wave_btn.setText(f"Process Day {day}/{days_total}")
            else:
                # Last day or wave complete - signal Draft requirement
                self._process_wave_btn.setText("Complete Wave 3 → Draft")
        elif wave == 4:
            # Post-Draft wave
            self._process_day_btn.setText("Process Day")
            self._process_wave_btn.setText("End Free Agency")

        # Refresh table to update action buttons
        if self._filtered_agents:
            self._apply_filters()

    def _enable_wave_mode(self) -> None:
        """Enable wave-based FA mode, showing wave-specific UI elements."""
        self._wave_mode = True

        # Show wave header
        self._wave_header_group.show()

        # Show wave controls
        self._wave_controls_frame.show()

    def set_pending_offers_count(self, count: int) -> None:
        """
        Update the pending offers count display.

        Args:
            count: Number of pending offers from user's team
        """
        self._pending_offers_count = count

        # Update the pending count label (reuse existing label for now)
        # In wave mode, this shows offers instead of signings
        if self._wave_mode:
            self.pending_count_label.setText(str(count))

            # Color coding based on count
            if count == 0:
                self.pending_count_label.setStyleSheet("color: #666;")  # Gray
            elif count <= 3:
                self.pending_count_label.setStyleSheet("color: #FF6F00;")  # Orange
            else:
                self.pending_count_label.setStyleSheet("color: #1976D2;")  # Blue

    def set_player_offer_status(self, player_statuses: Dict[int, Dict]) -> None:
        """
        Update offer status for players in the table.

        Args:
            player_statuses: Dict mapping player_id to status dict:
                - offer_count: int - Total offers on player
                - has_user_offer: bool - User has pending offer
                - user_offer_id: Optional[int] - For withdrawal
        """
        self._player_offer_status = player_statuses

        # Refresh table to update status column
        if self._filtered_agents:
            self._apply_filters()

    def show_surprise_signing_notification(
        self,
        player_name: str,
        team_name: str,
        aav: int
    ) -> None:
        """
        Show notification when a surprise signing occurs.

        Displayed as a message box notification.

        Args:
            player_name: Name of player signed
            team_name: Name of team that signed them
            aav: Average annual value of contract
        """
        from PySide6.QtWidgets import QMessageBox

        msg = QMessageBox(self)
        msg.setWindowTitle("Surprise Signing!")
        msg.setIcon(QMessageBox.Information)
        msg.setText(f"<b>{player_name}</b> has signed with the <b>{team_name}</b>!")
        msg.setInformativeText(f"Contract: ${aav:,}/year")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    @property
    def wave_mode(self) -> bool:
        """Check if wave mode is active."""
        return self._wave_mode

    @property
    def current_wave(self) -> int:
        """Get current wave number."""
        return self._current_wave