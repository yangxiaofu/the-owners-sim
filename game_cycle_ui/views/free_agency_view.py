"""
Free Agency View - Shows available free agents for signing.

Allows the user to see available free agents and sign them to their team.
"""

import logging
from typing import Dict, List, Optional

# Module logger for cap calculation debugging
_logger = logging.getLogger(__name__)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QComboBox, QSpinBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QBrush

from game_cycle_ui.theme import (
    UITheme, TABLE_HEADER_STYLE, Colors,
    PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, DANGER_BUTTON_STYLE,
    WARNING_BUTTON_STYLE, NEUTRAL_BUTTON_STYLE,
    Typography, FontSizes, TextColors, apply_table_style
)
from game_cycle_ui.widgets import (
    CompactFAHeader, GMProposalsPanel
)
from game_cycle_ui.dialogs.contract_modification_dialog import (
    ContractModificationDialog, ModifiedContractTerms
)
from constants.position_abbreviations import get_position_abbreviation
from utils.player_field_extractors import extract_overall_rating


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

    # GM proposal signals (Tollgate 7)
    proposal_approved = Signal(str)           # proposal_id
    proposal_rejected = Signal(str)           # proposal_id
    proposal_retracted = Signal(str)          # proposal_id (for undo tracking)

    # Cap-clearing trade search signal
    trade_search_requested = Signal(str, int)  # proposal_id, cap_shortage

    # Default NFL salary cap (2024 value)
    DEFAULT_CAP_LIMIT = 255_400_000

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._free_agents: List[Dict] = []
        self._filtered_agents: List[Dict] = []
        self._signed_players: set = set()  # Track pending signings by player_id
        self._pending_cap_commits: Dict[int, int] = {}  # player_id -> year1_cap_hit (SSOT for projected cap)
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

        # GM proposal tracking (Tollgate 7)
        self._gm_proposals: List[Dict] = []   # List of proposal dicts from handler
        self._pending_proposal_cap_hits: Dict[str, int] = {}  # proposal_id -> Year 1 cap hit (for cap projection)

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
        """Build the UI layout (Horizontal split redesign)."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Top section (vertical stack)
        # 1. Compact header (40px sticky)
        self._create_compact_header(layout)

        # 2. Owner directives display
        self._create_directives_display(layout)

        # 3. Wave header with progress indicator (hidden by default, shown in wave mode)
        self._create_wave_header(layout)

        # 4. GM Proposals panel (created here but will be added to sidebar)
        self._create_gm_proposals_panel(None)  # No parent layout

        # 5. Wave control panel (created here but will be added to left section)
        self._create_wave_controls(None)  # No parent layout

        # MAIN CONTENT - Horizontal split
        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)

        # Left: Players table section (50%)
        left_section = self._create_players_section()
        content_layout.addWidget(left_section, stretch=1)

        # Right: GM Proposals sidebar (50%)
        right_section = self._create_proposals_sidebar()
        content_layout.addWidget(right_section, stretch=1)

        layout.addLayout(content_layout, stretch=1)

        # Bottom section
        # 6. Action instructions (kept at bottom)
        self._create_instructions(layout)

    def _create_compact_header(self, parent_layout: QVBoxLayout):
        """Create compact 40px header with all essential info."""
        self.compact_header = CompactFAHeader()

        # Connect filter changed signal
        self.compact_header.filter_changed.connect(self._apply_filters)

        # Connect process day signal
        self.compact_header.process_day_clicked.connect(self._on_process_day_clicked)

        parent_layout.addWidget(self.compact_header)

    def _create_gm_proposals_panel(self, parent_layout):
        """Create GM Proposals panel with card-based layout (Concept 1)."""
        self.gm_proposals_panel = GMProposalsPanel()

        # Connect signals
        # Note: proposal_approved/retracted are for local UI state tracking only
        # Actual signing is deferred to Process Wave click
        self.gm_proposals_panel.proposal_approved.connect(self._on_proposal_approved)
        self.gm_proposals_panel.proposal_rejected.connect(self._on_proposal_rejected)
        self.gm_proposals_panel.proposal_retracted.connect(self._on_proposal_retracted)
        self.gm_proposals_panel.proposal_modify_clicked.connect(self._on_proposal_modify_clicked)
        self.gm_proposals_panel.review_later.connect(self._on_review_later)
        self.gm_proposals_panel.search_trade_partner.connect(self._on_search_trade_partner)

        # Only add to parent layout if provided (for backward compatibility)
        if parent_layout is not None:
            parent_layout.addWidget(self.gm_proposals_panel)

    def _create_directives_display(self, parent_layout: QVBoxLayout):
        """Create owner directives display."""
        # Owner directives display
        directives_frame = QFrame()
        directives_layout = QHBoxLayout(directives_frame)
        directives_layout.setContentsMargins(10, 5, 10, 5)
        directives_layout.setSpacing(15)

        # FA Philosophy badge
        self._fa_philosophy_badge = QLabel("Philosophy: Balanced")
        self._fa_philosophy_badge.setFont(Typography.SMALL)
        self._fa_philosophy_badge.setStyleSheet(
            f"color: {Colors.INFO}; background-color: #E3F2FD; "
            "padding: 4px 8px; border-radius: 3px;"
        )
        directives_layout.addWidget(self._fa_philosophy_badge)

        # Priority positions
        self._priority_positions_label = QLabel("No priority positions")
        self._priority_positions_label.setFont(Typography.SMALL)
        self._priority_positions_label.setStyleSheet(f"color: {Colors.MUTED};")
        directives_layout.addWidget(self._priority_positions_label)

        # Contract constraints
        self._contract_constraints_label = QLabel("Max: 5 years, 100% guaranteed")
        self._contract_constraints_label.setFont(Typography.SMALL)
        self._contract_constraints_label.setStyleSheet(f"color: {Colors.MUTED};")
        directives_layout.addWidget(self._contract_constraints_label)

        directives_layout.addStretch()
        parent_layout.addWidget(directives_frame)

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

    def _create_players_table_widget(self):
        """Create the main table of free agents widget (Concept 1 - simplified to 6 columns)."""
        self.players_table = QTableWidget()
        self.players_table.setColumnCount(6)  # Simplified from 10 to 6 columns
        self.players_table.setHorizontalHeaderLabels([
            "Player", "Pos", "Age", "OVR", "Pot", "Action"
            # Removed: Dev, Est. AAV, Interest, Status
            # Note: Financial Fit (AAV + Interest) will be shown in hover tooltip
        ])

        # Apply standard ESPN dark table styling
        apply_table_style(self.players_table)

        # Set row height for better button visibility
        self.players_table.verticalHeader().setDefaultSectionSize(40)

        # Configure column resize modes
        header = self.players_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name stretches
        header.setSectionResizeMode(1, QHeaderView.Fixed)     # Pos: 50px
        header.setSectionResizeMode(2, QHeaderView.Fixed)     # Age: 50px
        header.setSectionResizeMode(3, QHeaderView.Fixed)     # OVR: 60px
        header.setSectionResizeMode(4, QHeaderView.Fixed)     # Pot: 60px
        header.setSectionResizeMode(5, QHeaderView.Fixed)     # Action: 100px

        header.resizeSection(1, 50)   # Pos
        header.resizeSection(2, 50)   # Age
        header.resizeSection(3, 60)   # OVR
        header.resizeSection(4, 60)   # Pot
        header.resizeSection(5, 100)  # Action

    def _create_players_section(self) -> QWidget:
        """
        Create left panel with players table and wave controls.

        Returns main browsing area for free agents.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Group box for table
        group = QGroupBox("Browse All Free Agents")
        group.setStyleSheet("QGroupBox { font-weight: bold; color: #CFD8DC; }")
        table_layout = QVBoxLayout(group)
        table_layout.setContentsMargins(10, 10, 10, 10)

        # Players table (create widget)
        self._create_players_table_widget()
        table_layout.addWidget(self.players_table)

        layout.addWidget(group, stretch=1)

        # Wave controls at bottom (created earlier in setup)
        # Will be added later via addWidget after wave controls are created
        layout.addWidget(self._wave_controls_frame)

        return widget

    def _create_proposals_sidebar(self) -> QWidget:
        """
        Create right sidebar with GM proposals.

        Flexible width (50% of screen), scrollable if >3 proposals.
        """
        widget = QWidget()
        # No fixed width - let it flex to 50% via stretch ratio
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area for proposals
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # GM Proposals Panel (already created in setup_ui)
        scroll.setWidget(self.gm_proposals_panel)

        layout.addWidget(scroll)

        return widget

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
        self._wave_instructions.setStyleSheet(f"color: #333; font-size: {FontSizes.BODY}; line-height: 1.4;")
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
        # Update FA count in compact header
        self.compact_header.update_fa_count(len(players))
        # Keep pending count as-is (will be updated by set_pending_offers_count if needed)
        self._apply_filters()

    def set_cap_space(self, cap_space: int):
        """Update the cap space display (Concept 1 - uses compact header)."""
        # Update compact header with cap info
        self.compact_header.update_cap(cap_space, self._cap_limit)

    def set_cap_data(self, cap_data: Dict):
        """
        Update the view with full cap data from CapHelper (Concept 1).

        Args:
            cap_data: Dict with available_space, salary_cap_limit, total_spending,
                      dead_money, is_compliant, projected_available (optional), carryover
        """
        available = cap_data.get("available_space", 0)
        self._available_cap_space = available  # Store for affordability checks

        # Debug logging for cap data updates
        _logger.debug(
            f"set_cap_data: available=${available:,}, "
            f"total_spending=${cap_data.get('total_spending', 0):,}, "
            f"pending_commits={len(self._pending_cap_commits)}, "
            f"pending_total=${sum(self._pending_cap_commits.values()):,}"
        )

        # Update cap limit from data if provided
        if "salary_cap_limit" in cap_data:
            self.cap_limit = cap_data["salary_cap_limit"]

        # Update compact header with cap info
        self.compact_header.update_cap(available, self.cap_limit)

        # Set projected cap (defaults to available if no pending signings)
        projected = cap_data.get("projected_available", available)
        self.set_projected_cap(projected)

        # Note: Rollover/carryover no longer displayed in Concept 1 (compact header)
        # Can be added back if needed

        # Refresh table to update affordability indicators
        if self._free_agents:
            self._apply_filters()

    def set_projected_cap(self, projected: int):
        """
        Update the projected cap space display.

        Note: In the compact header design, projected cap is not shown separately.
        This method now only emits the cap validation signal.

        Args:
            projected: Projected cap space after pending signings
        """
        # Emit cap validation signal to enable/disable Process button
        is_over_cap = projected < 0
        over_cap_amount = abs(projected) if is_over_cap else 0
        self.cap_validation_changed.emit(not is_over_cap, over_cap_amount)

    def set_owner_directives(self, directives_dict: Optional[Dict]):
        """
        Display owner directives in the FA summary area.

        Args:
            directives_dict: Owner directives from preview (owner_directives key)
        """
        # Debug logging for UI receive
        print(f"[DEBUG] FA View received directives: "
              f"priority_positions={directives_dict.get('priority_positions', []) if directives_dict else 'None'}")
        if not directives_dict:
            self._fa_philosophy_badge.setText("Philosophy: Balanced")
            self._priority_positions_label.setText("No directives set")
            self._priority_positions_label.setStyleSheet(f"color: {Colors.MUTED};")
            self._contract_constraints_label.setText("No constraints")
            self._contract_constraints_label.setStyleSheet(f"color: {Colors.MUTED};")
            return

        # FA Philosophy badge
        philosophy = directives_dict.get("fa_philosophy", "balanced")
        philosophy_names = {
            "aggressive": "Aggressive (Overpay for talent)",
            "balanced": "Balanced (Market rate)",
            "conservative": "Conservative (Value signings)",
        }
        philosophy_text = philosophy_names.get(philosophy, "Balanced (Market rate)")
        self._fa_philosophy_badge.setText(f"Philosophy: {philosophy_text}")

        # Update badge color based on philosophy
        if philosophy == "aggressive":
            badge_color = Colors.ERROR
            bg_color = "#FFEBEE"
        elif philosophy == "conservative":
            badge_color = Colors.SUCCESS
            bg_color = "#E8F5E9"
        else:
            badge_color = Colors.INFO
            bg_color = "#E3F2FD"

        self._fa_philosophy_badge.setStyleSheet(
            f"color: {badge_color}; background-color: {bg_color}; "
            "padding: 4px 8px; border-radius: 3px;"
        )

        # Priority positions (max 3 for FA)
        priority_positions = directives_dict.get("priority_positions", [])[:3]
        if priority_positions:
            positions_text = ", ".join(priority_positions)
            self._priority_positions_label.setText(f"Priority: {positions_text}")
            self._priority_positions_label.setStyleSheet(
                f"color: {Colors.SUCCESS}; font-weight: bold;"
            )
        else:
            self._priority_positions_label.setText("No priority positions")
            self._priority_positions_label.setStyleSheet(f"color: {Colors.MUTED};")

        # Contract constraints
        max_years = directives_dict.get("max_contract_years", 5)
        max_guaranteed_pct = directives_dict.get("max_guaranteed_percent", 1.0)
        self._contract_constraints_label.setText(
            f"Max: {max_years} years, {int(max_guaranteed_pct * 100)}% guaranteed"
        )
        self._contract_constraints_label.setStyleSheet(
            f"color: {Colors.WARNING}; font-weight: bold;"
        )

    def _apply_filters(self):
        """Apply position and overall filters to the free agent list (Concept 1)."""
        # Get filter values from compact header
        position_filter = self.compact_header.get_position_filter()
        min_overall = self.compact_header.get_min_ovr_filter()
        show_filter = self.compact_header.get_show_filter()

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
            if extract_overall_rating(player, default=0) < min_overall:
                continue

            # Show filter (Concept 1 enhancement)
            if show_filter == "affordable":
                # Only show affordable players
                aav = player.get("estimated_aav", 0)
                projected_cap = self._calculate_projected_cap()
                if aav > projected_cap:
                    continue
            elif show_filter == "high_interest":
                # Only show players with 70%+ interest
                player_id = player.get("player_id", 0)
                interest_data = self._player_interests.get(player_id, {})
                interest_score = interest_data.get("interest_score", 50)
                if interest_score < 70:
                    continue

            self._filtered_agents.append(player)

        # Update table
        self.players_table.setRowCount(len(self._filtered_agents))
        for row, player in enumerate(self._filtered_agents):
            self._populate_row(row, player)

        # Update filtered count display in compact header
        self.compact_header.update_fa_count(len(self._filtered_agents))

    def _populate_row(self, row: int, player: Dict):
        """Populate a single row in the table (Concept 1 - 6 columns)."""
        player_id = player.get("player_id", 0)
        aav = player.get("estimated_aav", 0)

        # Calculate affordability using projected cap (after pending signings)
        projected_cap = self._calculate_projected_cap()
        can_afford = aav <= projected_cap

        # Get interest data for tooltip
        interest_data = self._player_interests.get(player_id, {})
        interest_score = interest_data.get("interest_score", 50)
        dev_type = player.get("dev_type", "normal")

        # Column 0: Player name with comprehensive tooltip
        name_item = QTableWidgetItem(player.get("name", "Unknown"))
        name_item.setData(Qt.UserRole, player_id)

        # Build comprehensive tooltip
        tooltip_parts = [
            f"Est. AAV: ${aav:,}",
            f"Interest: {interest_score}%",
            f"Dev Type: {dev_type.title()}",
        ]
        if not can_afford:
            tooltip_parts.append(f"\n⚠ Can't Afford (need ${(aav - projected_cap)/1e6:.1f}M more)")

        # Add persona and concerns
        persona_type = interest_data.get("persona_type", "unknown")
        if persona_type != "unknown":
            hint = self._get_persona_hint(persona_type)
            tooltip_parts.append(f"\nPersona: {persona_type.replace('_', ' ').title()}")
            if hint:
                tooltip_parts.append(f"  {hint}")

        concerns = interest_data.get("concerns", [])
        if concerns:
            tooltip_parts.append("\nConcerns:")
            for concern in concerns[:3]:
                tooltip_parts.append(f"  • {concern}")

        name_item.setToolTip("\n".join(tooltip_parts))
        self.players_table.setItem(row, 0, name_item)

        # Column 1: Position - convert to standard NFL abbreviation
        position = player.get("position", "")
        pos_item = QTableWidgetItem(get_position_abbreviation(position))
        pos_item.setTextAlignment(Qt.AlignCenter)
        self.players_table.setItem(row, 1, pos_item)

        # Column 2: Age
        age = player.get("age", 0)
        age_item = QTableWidgetItem(str(age))
        age_item.setTextAlignment(Qt.AlignCenter)
        # Color code age (red if 30+)
        if age >= 30:
            age_item.setForeground(QColor("#C62828"))  # Red
        self.players_table.setItem(row, 2, age_item)

        # Column 3: Overall rating
        overall = extract_overall_rating(player, default=0)
        ovr_item = QTableWidgetItem(str(overall))
        ovr_item.setTextAlignment(Qt.AlignCenter)
        # Color code rating
        if overall >= 85:
            ovr_item.setForeground(QColor("#2E7D32"))  # Green - Elite
        elif overall >= 75:
            ovr_item.setForeground(QColor("#1976D2"))  # Blue - Solid
        self.players_table.setItem(row, 3, ovr_item)

        # Column 4: Potential rating with color coding
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

        # Column 5: Action button
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        sign_btn = QPushButton("Sign")

        # Check if player has pending offer
        if player_id in self._signed_players:
            sign_btn.setText("Withdraw")
            sign_btn.setStyleSheet(WARNING_BUTTON_STYLE)
        else:
            sign_btn.setEnabled(can_afford)  # Disable if can't afford
            if can_afford:
                sign_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
            else:
                sign_btn.setStyleSheet(
                    "QPushButton { background-color: #ccc; color: #666; border-radius: 3px; padding: 4px 12px; }"
                )
                sign_btn.setToolTip(f"Insufficient cap space. Need ${aav:,}, have ${projected_cap:,}")

        sign_btn.clicked.connect(lambda checked, pid=player_id, r=row: self._on_sign_clicked(pid, r))
        action_layout.addWidget(sign_btn)

        self.players_table.setCellWidget(row, 5, action_widget)

    def _on_sign_clicked(self, player_id: int, row: int):
        """Handle sign/unsign button click.

        In wave mode: Creates offer at market value (Quick Sign).
        In legacy mode: Opens signing dialog.
        """
        if player_id in self._signed_players:
            # UNSIGN - remove from pending (no dialog needed)
            self._signed_players.discard(player_id)
            self._pending_cap_commits.pop(player_id, None)  # Remove cap commit
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

            # Store initial cap estimate (controller will update with actual Year-1 cap hit)
            # This ensures immediate UI feedback with a reasonable projection
            self._pending_cap_commits[player_id] = estimated_aav

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

            # Store initial cap estimate (controller will update with actual Year-1 cap hit)
            estimated_aav = player_info.get("estimated_aav", 5_000_000)
            self._pending_cap_commits[player_id] = estimated_aav

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
                    "overall": extract_overall_rating(player, default=0),
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
                    child.setStyleSheet(WARNING_BUTTON_STYLE)

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
        """
        Update the count of pending signings.

        Note: In the compact header design, pending count is not displayed.
        This method is now a no-op.
        """
        pass  # No-op - pending count not shown in compact header

    def _calculate_projected_cap(self) -> int:
        """
        Calculate cap space remaining after pending signings and approved proposals.

        Uses actual Year-1 cap hits from _pending_cap_commits (SSOT) for direct signings
        and AAV from _pending_proposal_cap_hits for GM proposal approvals.

        Returns:
            Projected cap space (base available - pending commits - pending proposals)
        """
        pending_commits_total = sum(self._pending_cap_commits.values())
        pending_proposals_total = sum(self._pending_proposal_cap_hits.values())
        projected = self._available_cap_space - pending_commits_total - pending_proposals_total

        _logger.debug(
            f"_calculate_projected_cap: base=${self._available_cap_space:,}, "
            f"pending_commits={len(self._pending_cap_commits)} (${pending_commits_total:,}), "
            f"pending_proposals={len(self._pending_proposal_cap_hits)} (${pending_proposals_total:,}), "
            f"projected=${projected:,}"
        )

        return projected

    def _refresh_affordability(self):
        """
        Refresh affordability indicators for all visible rows after signing/unsigning (Concept 1).

        Updates:
        - Projected cap display
        - Player name tooltip (shows AAV affordability)
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

            # Skip already-signed players (they show "Withdraw" button)
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

            # Update player name tooltip with affordability info
            interest_data = self._player_interests.get(player_id, {})
            interest_score = interest_data.get("interest_score", 50)
            dev_type = player.get("dev_type", "normal")

            tooltip_parts = [
                f"Est. AAV: ${aav:,}",
                f"Interest: {interest_score}%",
                f"Dev Type: {dev_type.title()}",
            ]
            if not can_afford:
                tooltip_parts.append(f"\n⚠ Can't Afford (need ${(aav - projected_cap)/1e6:.1f}M more)")

            name_item.setToolTip("\n".join(tooltip_parts))

            # Update button state (column 5 - Action column)
            action_widget = self.players_table.cellWidget(row, 5)
            if action_widget:
                for child in action_widget.children():
                    if isinstance(child, QPushButton) and child.text() == "Sign":
                        child.setEnabled(can_afford)
                        if can_afford:
                            child.setStyleSheet(PRIMARY_BUTTON_STYLE)
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
        """Show a message when there are no free agents available (Concept 1)."""
        self.players_table.setRowCount(1)
        self.players_table.setSpan(0, 0, 1, 6)  # Span all 6 columns (updated from 10)

        message_item = QTableWidgetItem("No free agents available")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor("#666"))
        font = Typography.BODY
        font.setItalic(True)
        message_item.setFont(font)

        self.players_table.setItem(0, 0, message_item)
        self.compact_header.update_fa_count(0)

    def clear_signed_players(self):
        """Reset signed players and cap commits (call after processing)."""
        self._signed_players.clear()
        self._pending_cap_commits.clear()
        self._apply_filters()

    def clear_pending_state(self):
        """
        Clear all pending offer state.

        Called when:
        - Wave advances (new wave starts)
        - Stage changes (leaving FA stage)
        - User cancels all offers
        """
        cleared_count = len(self._pending_cap_commits)
        cleared_total = sum(self._pending_cap_commits.values())

        self._signed_players.clear()
        self._pending_cap_commits.clear()

        _logger.debug(
            f"clear_pending_state: cleared {cleared_count} commits totaling ${cleared_total:,}"
        )

        self._apply_filters()

    def get_signed_player_ids(self) -> List[int]:
        """Get list of player IDs that were signed."""
        return list(self._signed_players)

    def update_pending_cap_commit(self, player_id: int, year1_cap_hit: int):
        """
        Update the Year-1 cap commitment for a pending signing.

        This is the SSOT for projected cap calculations. Called by the controller
        after backend validates the offer and calculates the actual cap hit.

        Args:
            player_id: Player ID for the pending signing
            year1_cap_hit: Actual Year-1 cap hit from CapHelper (not estimated AAV)
        """
        old_value = self._pending_cap_commits.get(player_id, 0)
        self._pending_cap_commits[player_id] = year1_cap_hit

        _logger.debug(
            f"update_pending_cap_commit: player_id={player_id}, "
            f"old=${old_value:,}, new=${year1_cap_hit:,}, "
            f"total_commits={len(self._pending_cap_commits)}"
        )

        self._refresh_affordability()

    def remove_pending_cap_commit(self, player_id: int):
        """
        Remove a pending cap commitment when offer is withdrawn.

        Args:
            player_id: Player ID to remove from pending commits
        """
        removed_value = self._pending_cap_commits.pop(player_id, None)

        removed_str = f"${removed_value:,}" if removed_value else "not found"
        _logger.debug(
            f"remove_pending_cap_commit: player_id={player_id}, "
            f"removed={removed_str}, "
            f"remaining_commits={len(self._pending_cap_commits)}"
        )

        self._refresh_affordability()

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
        self._wave_title_label.setFont(Typography.H5)
        top_row.addWidget(self._wave_title_label)

        top_row.addStretch()

        self._wave_day_label = QLabel("Day 1/1")
        self._wave_day_label.setFont(Typography.BODY)
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
            label.setStyleSheet(f"font-size: {FontSizes.TINY}; color: #666;")
            segment_layout.addWidget(label)

            self._wave_indicators.append(indicator)
            self._wave_labels.append(label)
            progress_row.addWidget(segment_widget)

            # Arrow between segments (except after last)
            if i < 4:
                arrow = QLabel("→")
                arrow.setStyleSheet(f"color: #999; font-size: {FontSizes.BODY};")
                arrow.setAlignment(Qt.AlignCenter)
                progress_row.addWidget(arrow)

        wave_layout.addLayout(progress_row)

        # Initially hidden (shown when set_wave_info called)
        self._wave_header_group.hide()

        parent_layout.addWidget(self._wave_header_group)

    def _create_wave_controls(self, parent_layout):
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
        instruction_label.setStyleSheet(f"color: #CFD8DC; font-size: {FontSizes.CAPTION}; padding: 4px 0px;")
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
            f"QPushButton {{ background-color: #37474F; color: white; "
            f"border-radius: 4px; padding: 8px 20px; font-size: {FontSizes.H5}; }}"
            f"QPushButton:hover {{ background-color: #263238; }}"
            f"QPushButton:disabled {{ background-color: #ccc; color: #666; }}"
        )
        self._process_day_btn.clicked.connect(self._on_process_day_clicked)
        controls_layout.addWidget(self._process_day_btn)

        controls_layout.addStretch()

        # Days remaining indicator
        self._days_remaining_label = QLabel("Days Remaining: 1")
        self._days_remaining_label.setStyleSheet(f"color: #B0BEC5; font-size: {FontSizes.BODY};")
        controls_layout.addWidget(self._days_remaining_label)

        controls_layout.addStretch()

        # Process Wave button
        self._process_wave_btn = QPushButton("Process Wave")
        self._process_wave_btn.setToolTip(
            "End current wave. All pending offers will be resolved and players will make decisions."
        )
        self._process_wave_btn.setStyleSheet(
            f"QPushButton {{ background-color: #00695C; color: white; "
            f"border-radius: 4px; padding: 8px 20px; font-size: {FontSizes.H5}; }}"
            f"QPushButton:hover {{ background-color: #004D40; }}"
            f"QPushButton:disabled {{ background-color: #ccc; color: #666; }}"
        )
        self._process_wave_btn.clicked.connect(self._on_process_wave_clicked)
        controls_layout.addWidget(self._process_wave_btn)

        # Add button layout to frame
        frame_layout.addLayout(controls_layout)

        # Initially hidden
        self._wave_controls_frame.hide()

        # Only add to parent layout if provided (for backward compatibility)
        if parent_layout is not None:
            parent_layout.addWidget(self._wave_controls_frame)

    def _create_gm_proposals_section(self, parent_layout: QVBoxLayout):
        """Create GM Signing Recommendations section (Tollgate 7)."""
        self._gm_proposals_group = QGroupBox("GM SIGNING RECOMMENDATIONS")
        self._gm_proposals_group.setStyleSheet(
            "QGroupBox { font-weight: bold; color: #1976D2; }"
        )
        proposals_layout = QVBoxLayout(self._gm_proposals_group)
        proposals_layout.setContentsMargins(10, 10, 10, 10)
        proposals_layout.setSpacing(8)

        # Proposals table
        self._proposals_table = QTableWidget()
        self._proposals_table.setColumnCount(7)
        self._proposals_table.setHorizontalHeaderLabels([
            "Player", "Pos", "OVR", "AAV", "Years", "Confidence", "Action"
        ])

        # Apply standard table styling
        apply_table_style(self._proposals_table)

        # Configure column widths
        header = self._proposals_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        header.resizeSection(6, 150)

        # Set taller rows for buttons
        self._proposals_table.verticalHeader().setDefaultSectionSize(44)

        proposals_layout.addWidget(self._proposals_table)

        # GM reasoning display area (shows selected proposal's reasoning)
        self._gm_reasoning_label = QLabel()
        self._gm_reasoning_label.setWordWrap(True)
        self._gm_reasoning_label.setStyleSheet(
            f"background-color: #f5f5f5; padding: 10px; border-radius: 4px; "
            f"color: #333; font-size: {FontSizes.BODY}; font-style: italic;"
        )
        self._gm_reasoning_label.setMinimumHeight(60)
        self._gm_reasoning_label.hide()  # Hidden until a proposal is selected
        proposals_layout.addWidget(self._gm_reasoning_label)

        # Initially hidden (shown when proposals are set)
        self._gm_proposals_group.hide()

        parent_layout.addWidget(self._gm_proposals_group)

    def set_gm_proposals(self, proposals: List[Dict], trust_gm: bool = False) -> None:
        """
        Set GM signing proposals for display (Concept 1 - uses new GMProposalsPanel).

        Args:
            proposals: List of proposal dicts with:
                - proposal_id: str
                - details: dict with player_name, position, age, overall_rating,
                           contract (years, aav, guaranteed)
                - gm_reasoning: str
                - confidence: float (0-1)
                - status: str
            trust_gm: If True, show auto-approval indicator
        """
        self._gm_proposals = proposals
        self._trust_gm = trust_gm  # Store for display

        # Use new GMProposalsPanel
        self.gm_proposals_panel.set_proposals(proposals, auto_approve=trust_gm)

        # Initialize cap tracking for pre-approved proposals (new default behavior)
        from game_cycle.models.proposal_enums import ProposalStatus
        for proposal in proposals:
            proposal_status = proposal.get("status", "PENDING")
            # Handle both string and enum values
            is_approved = False
            if isinstance(proposal_status, str):
                is_approved = (proposal_status == "APPROVED" or proposal_status == ProposalStatus.APPROVED.value)
            else:
                is_approved = (proposal_status == ProposalStatus.APPROVED)

            if is_approved:
                # Track cap hit for pre-approved proposal
                proposal_id = proposal.get("proposal_id")
                details = proposal.get("details", {})
                contract = details.get("contract", {})
                year1_cap_hit = self._calculate_year1_cap_hit(contract, details)
                self._pending_proposal_cap_hits[proposal_id] = year1_cap_hit
                print(f"[FreeAgencyView] Pre-approved proposal {proposal_id} - Year 1 cap hit ${year1_cap_hit:,}")

        # Refresh cap display to include pre-approved proposals
        self._refresh_cap_display()

    def _populate_proposal_row(self, row: int, proposal: Dict):
        """Populate a single row in the proposals table."""
        details = proposal.get("details", {})
        contract = details.get("contract", {})
        proposal_id = proposal.get("proposal_id", "")

        # Player name
        player_name = details.get("player_name", "Unknown")
        name_item = QTableWidgetItem(player_name)
        name_item.setData(Qt.UserRole, proposal_id)
        self._proposals_table.setItem(row, 0, name_item)

        # Position
        position = details.get("position", "")
        pos_item = QTableWidgetItem(get_position_abbreviation(position))
        pos_item.setTextAlignment(Qt.AlignCenter)
        self._proposals_table.setItem(row, 1, pos_item)

        # Overall
        overall = extract_overall_rating(details, default=0)
        ovr_item = QTableWidgetItem(str(overall))
        ovr_item.setTextAlignment(Qt.AlignCenter)
        if overall >= 85:
            ovr_item.setForeground(QColor("#2E7D32"))
        elif overall >= 75:
            ovr_item.setForeground(QColor("#1976D2"))
        self._proposals_table.setItem(row, 2, ovr_item)

        # AAV
        aav = contract.get("aav", 0)
        aav_text = f"${aav:,}" if aav else "N/A"
        aav_item = QTableWidgetItem(aav_text)
        aav_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._proposals_table.setItem(row, 3, aav_item)

        # Years
        years = contract.get("years", 0)
        years_item = QTableWidgetItem(str(years))
        years_item.setTextAlignment(Qt.AlignCenter)
        self._proposals_table.setItem(row, 4, years_item)

        # Confidence (as percentage)
        confidence = proposal.get("confidence", 0.5)
        conf_pct = int(confidence * 100)
        conf_item = QTableWidgetItem(f"{conf_pct}%")
        conf_item.setTextAlignment(Qt.AlignCenter)
        # Color code confidence
        if conf_pct >= 80:
            conf_item.setForeground(QColor("#2E7D32"))  # Green
        elif conf_pct >= 60:
            conf_item.setForeground(QColor("#1976D2"))  # Blue
        else:
            conf_item.setForeground(QColor("#F57C00"))  # Orange
        self._proposals_table.setItem(row, 5, conf_item)

        # Action buttons (Approve / Reject)
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        approve_btn = QPushButton("Approve")
        approve_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        approve_btn.setToolTip("Approve this signing recommendation")
        approve_btn.clicked.connect(
            lambda checked, pid=proposal_id: self._on_proposal_approved(pid)
        )
        action_layout.addWidget(approve_btn)

        reject_btn = QPushButton("Reject")
        reject_btn.setStyleSheet(DANGER_BUTTON_STYLE)
        reject_btn.setToolTip("Reject this signing recommendation")
        reject_btn.clicked.connect(
            lambda checked, pid=proposal_id: self._on_proposal_rejected(pid)
        )
        action_layout.addWidget(reject_btn)

        self._proposals_table.setCellWidget(row, 6, action_widget)

        # Connect row selection to show reasoning
        self._proposals_table.cellClicked.connect(self._on_proposal_row_clicked)

    def _on_proposal_row_clicked(self, row: int, column: int):
        """Handle click on proposal row to show reasoning."""
        if row < len(self._gm_proposals):
            self._show_proposal_reasoning(self._gm_proposals[row])

    def _show_proposal_reasoning(self, proposal: Dict):
        """Show GM reasoning for a proposal."""
        reasoning = proposal.get("gm_reasoning", "")
        if reasoning:
            self._gm_reasoning_label.setText(f"GM says: \"{reasoning}\"")
            self._gm_reasoning_label.show()
        else:
            self._gm_reasoning_label.hide()

    def _calculate_year1_cap_hit(self, contract: dict, details: dict) -> int:
        """
        Calculate Year 1 cap hit from contract terms.

        Uses the same formula as sign_free_agent() to match actual cap impact.

        Args:
            contract: Dict with years, total/total_value, aav
            details: Full proposal details (may contain signing_bonus)

        Returns:
            Year 1 cap hit in dollars
        """
        years = contract.get("years", 1)
        total_value = contract.get("total", contract.get("total_value", 0))
        signing_bonus = details.get("signing_bonus", 0)

        if years <= 0 or total_value <= 0:
            # Fallback to AAV if contract terms are invalid
            return contract.get("aav", 0)

        # Calculate Year 1 base salary (same weighted formula as sign_free_agent)
        remaining_after_bonus = total_value - signing_bonus
        year_weight = 1.0  # Year 1 weight = 1.0 + (0 * 0.05) = 1.0
        total_weight = sum(1.0 + (j * 0.05) for j in range(years))
        year1_base_salary = int((remaining_after_bonus * year_weight) / total_weight)

        # Calculate signing bonus proration (spread over min(years, 5))
        proration_years = min(years, 5)
        year1_bonus_proration = signing_bonus // proration_years if proration_years > 0 else 0

        return year1_base_salary + year1_bonus_proration

    def _on_proposal_approved(self, proposal_id: str):
        """
        Handle approve button click - card is now in approved state.

        Tracks the cap hit for this proposal to update projected cap display.
        Does NOT emit proposal_approved signal - actual signing is deferred
        to Process Wave click.
        """
        # Find proposal and extract Year 1 cap hit (not AAV)
        proposal = next(
            (p for p in self._gm_proposals if p.get("proposal_id") == proposal_id),
            None
        )
        if proposal:
            details = proposal.get("details", {})
            contract = details.get("contract", {})
            # Calculate actual Year 1 cap hit (matches sign_free_agent formula)
            year1_cap_hit = self._calculate_year1_cap_hit(contract, details)
            self._pending_proposal_cap_hits[proposal_id] = year1_cap_hit
            aav = contract.get("aav", 0)
            print(f"[FreeAgencyView] Proposal {proposal_id} approved - Year 1 cap hit ${year1_cap_hit:,} (AAV ${aav:,})")
            self._refresh_cap_display()
        else:
            print(f"[FreeAgencyView] Proposal {proposal_id} approved but not found in local list")

    def _on_proposal_rejected(self, proposal_id: str):
        """Handle reject button click - immediately emit rejection."""
        self.proposal_rejected.emit(proposal_id)

        # Remove from local list and pending cap tracking
        self._gm_proposals = [
            p for p in self._gm_proposals
            if p.get("proposal_id") != proposal_id
        ]
        self._pending_proposal_cap_hits.pop(proposal_id, None)
        self._refresh_cap_display()

    def _on_proposal_retracted(self, proposal_id: str):
        """
        Handle retract button click - card returns to pending state.

        Removes cap hit from tracking and refreshes display.
        Emits retracted signal for tracking.
        """
        # Remove from pending cap tracking
        cap_hit = self._pending_proposal_cap_hits.pop(proposal_id, 0)
        print(f"[FreeAgencyView] Proposal {proposal_id} retracted - ${cap_hit:,} removed from pending")
        self._refresh_cap_display()
        self.proposal_retracted.emit(proposal_id)

    def _on_proposal_modify_clicked(self, proposal_id: str, proposal_data: dict):
        """
        Handle modify button click - show contract modification dialog.

        Opens dialog allowing owner to adjust contract terms (years, AAV, guaranteed)
        before approving. If modified terms are confirmed, updates the proposal
        and marks it as approved.
        """
        details = proposal_data.get("details", {})
        contract = details.get("contract", {})

        # Get market AAV from contract or estimate from player rating
        market_aav = contract.get("aav", 0)
        if market_aav <= 0:
            # Fallback: estimate from overall rating
            overall = extract_overall_rating(details, default=70)
            market_aav = overall * 100_000  # $100K per OVR point

        # Show modification dialog
        dialog = ContractModificationDialog(
            proposal_data=proposal_data,
            market_aav=market_aav,
            cap_space=self._available_cap_space,
            parent=self,
        )

        dialog.terms_modified.connect(self._on_terms_modified)
        dialog.exec()

    def _on_terms_modified(self, proposal_id: str, modified_terms: ModifiedContractTerms):
        """
        Handle modified terms from contract modification dialog.

        Updates the proposal's contract terms and marks it as approved.
        """
        # Find and update the proposal in our local list
        for proposal in self._gm_proposals:
            if proposal.get("proposal_id") == proposal_id:
                # Update contract terms in the proposal
                if "details" not in proposal:
                    proposal["details"] = {}
                if "contract" not in proposal["details"]:
                    proposal["details"]["contract"] = {}

                proposal["details"]["contract"]["aav"] = modified_terms.aav
                proposal["details"]["contract"]["years"] = modified_terms.years
                proposal["details"]["contract"]["total"] = modified_terms.total_value
                proposal["details"]["contract"]["guaranteed"] = modified_terms.guaranteed
                proposal["details"]["signing_bonus"] = modified_terms.signing_bonus

                print(f"[FreeAgencyView] Proposal {proposal_id} modified: "
                      f"{modified_terms.years}yr, ${modified_terms.aav:,} AAV")

                # Calculate Year 1 cap hit for the modified terms
                year1_cap_hit = self._calculate_year1_cap_hit(
                    proposal["details"]["contract"],
                    proposal["details"]
                )
                self._pending_proposal_cap_hits[proposal_id] = year1_cap_hit

                # Update card to approved state
                if hasattr(self, 'gm_proposals_panel'):
                    card = self.gm_proposals_panel._cards.get(proposal_id)
                    if card:
                        card.set_approved_state(True)

                self._refresh_cap_display()
                break

    def _refresh_cap_display(self):
        """
        Update the header cap display with current and projected amounts.

        Called when proposal approvals or retractions change pending cap totals.
        """
        projected = self._calculate_projected_cap()
        pending_count = len(self._pending_proposal_cap_hits)
        self.compact_header.update_cap(
            available=self._available_cap_space,
            projected=projected,
            pending_count=pending_count
        )

    def _on_review_later(self):
        """Handle Review Later button click (Concept 1)."""
        # Simply hide the proposals panel for now
        # Proposals remain available but panel is collapsed
        self.gm_proposals_panel.hide()

    def _on_search_trade_partner(self, proposal_id: str, cap_shortage: int):
        """Handle trade search request from GM proposal card.

        Forward signal to controller for backend processing.

        Args:
            proposal_id: ID of the signing proposal we can't afford
            cap_shortage: Amount over cap we are
        """
        self.trade_search_requested.emit(proposal_id, cap_shortage)

    def clear_gm_proposals(self):
        """Clear all GM proposals (call on wave advance) - Concept 1."""
        self._gm_proposals = []
        # Use new GMProposalsPanel
        self.gm_proposals_panel.set_proposals([])

    def show_signing_result(self, proposal_id: str, success: bool, details: dict):
        """
        Show signing result - accumulates results and shows dialog when all received.

        Called by main_window after stage_controller processes the signing.
        Uses stored proposal info from _pending_results_info to get player names
        (since _gm_proposals is cleared before results arrive).

        Args:
            proposal_id: The proposal that was processed
            success: Whether the signing succeeded
            details: Contract details (success) or rejection info (failure)
        """
        # Get player info from stored pending results (not cleared _gm_proposals)
        info = getattr(self, '_pending_results_info', {}).get(proposal_id, {})
        player_name = info.get("player_name", "Unknown")
        position = info.get("position", "")

        # Try to update the card if it still exists
        card = self.gm_proposals_panel._cards.get(proposal_id)
        if card:
            if success:
                card.set_signed_state(details)
            else:
                reason = details.get("reason", "Signing failed")
                concerns = details.get("concerns", [])
                card.set_rejected_state(reason, concerns)

        # Log the result
        if success:
            aav = details.get("aav", 0)
            years = details.get("years", 0)
            if aav and years:
                msg = f"✓ SIGNED: {player_name} ({years}yr, ${aav/1e6:.1f}M/yr)"
            else:
                msg = f"✓ SIGNED: {player_name}"
            print(f"[FreeAgencyView] {msg}")
        else:
            reason = details.get("reason", "Signing failed")
            msg = f"✗ REJECTED: {player_name} - {reason}"
            print(f"[FreeAgencyView] {msg}")

        # Accumulate result for dialog
        if not hasattr(self, '_wave_results'):
            self._wave_results = []

        self._wave_results.append({
            "player_name": player_name,
            "position": position,
            "success": success,
            "details": details
        })

        # Check if all results received - show dialog
        expected = getattr(self, '_expected_results_count', 0)
        if expected > 0 and len(self._wave_results) >= expected:
            self._show_wave_results_dialog()

    def _show_wave_results_dialog(self):
        """Show the wave results dialog with all signing outcomes."""
        from game_cycle_ui.dialogs import WaveResultsDialog

        if not self._wave_results:
            return

        # Get current wave number for display
        wave_number = getattr(self, '_current_wave', 1)

        dialog = WaveResultsDialog(
            results=self._wave_results,
            wave_number=wave_number,
            parent=self
        )
        dialog.exec()

        # Clear for next wave
        self._wave_results = []
        self._pending_results_info = {}
        self._expected_results_count = 0

    def _show_signing_notification(self, message: str, success: bool):
        """
        Show a brief notification for signing results.

        Uses the wave_label in the header to show a temporary message.
        """
        from PySide6.QtCore import QTimer

        # Store original wave label text
        original_text = self.compact_header.wave_label.text()

        # Set notification style and text
        color = "#4caf50" if success else "#f44336"
        self.compact_header.wave_label.setText(message)
        self.compact_header.wave_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        # Restore original after 4 seconds
        def restore():
            self.compact_header.wave_label.setText(original_text)
            self.compact_header.wave_label.setStyleSheet("")  # Reset to default

        QTimer.singleShot(4000, restore)

    def _on_process_day_clicked(self):
        """Handle Process Day button click."""
        self.process_day_requested.emit()

    def _on_process_wave_clicked(self):
        """
        Handle Process Wave button click.

        Commits all pending proposal approvals by emitting proposal_approved
        signal for each, then clears the pending state and requests wave processing.
        """
        # Get pending approvals (includes pre-approved proposals)
        pending = self.gm_proposals_panel.get_pending_approvals()

        # Confirmation dialog for approved proposals (safety check for auto-approved proposals)
        if pending:
            from PySide6.QtWidgets import QMessageBox

            msg = f"Process {len(pending)} approved GM proposal{'s' if len(pending) != 1 else ''}?\n\n"
            msg += "This will execute all approved signings and commit them to the database.\n"
            msg += "Pre-approved proposals that you didn't review will be executed."

            reply = QMessageBox.question(
                self,
                "Confirm Process Wave",
                msg,
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return  # User cancelled

        # Continue with processing...
        if pending:
            print(f"[FreeAgencyView] Committing {len(pending)} pending approvals")

            # Store proposal info for results display BEFORE clearing
            # This fixes the "Unknown" player name bug
            self._pending_results_info = {}
            for proposal_id in pending:
                proposal = next(
                    (p for p in self._gm_proposals if p.get("proposal_id") == proposal_id),
                    None
                )
                if proposal:
                    details = proposal.get("details", {})
                    self._pending_results_info[proposal_id] = {
                        "player_name": details.get("player_name", "Unknown"),
                        "position": details.get("position", ""),
                        "contract": details.get("contract", {})
                    }

            # Initialize wave results tracking
            self._expected_results_count = len(pending)
            self._wave_results = []

            for proposal_id in pending:
                self.proposal_approved.emit(proposal_id)

            # Clear approved cards from panel
            self.gm_proposals_panel.clear_pending_approvals()

            # Update local proposals list
            self._gm_proposals = [
                p for p in self._gm_proposals
                if p.get("proposal_id") not in pending
            ]
        else:
            # No pending approvals - reset tracking
            self._pending_results_info = {}
            self._expected_results_count = 0
            self._wave_results = []

        # Clear pending proposal cap tracking and refresh display
        self._pending_proposal_cap_hits.clear()
        self._refresh_cap_display()

        # Then request wave processing
        self.process_wave_requested.emit()

    def set_wave_info(
        self,
        wave: int,
        wave_name: str,
        day: int,
        days_total: int
    ) -> None:
        """
        Update wave information display (Concept 1 - uses compact header).

        Enables wave mode if not already enabled.
        Updates compact header wave info and Process Day button.

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

        # Update compact header with wave info
        self.compact_header.update_wave_info(wave_name, day, days_total)

        # Show Process Day button in compact header
        self.compact_header.set_process_day_visible(True)

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

        # Update Process Day button state in compact header
        # Process Day disabled on last day (must use Process Wave)
        self.compact_header.set_process_day_enabled(day < days_total)

        # Update button text based on current wave
        if wave == 0:
            # Legal Tampering - no signing allowed yet
            self.compact_header.set_process_day_text("View Offers")
            # Process Wave handled by old controls (kept for now)
            if hasattr(self, '_process_wave_btn'):
                self._process_wave_btn.setText("Begin Signing Period")
        elif wave < 3:
            # Waves 1-2 (Elite, Quality)
            self.compact_header.set_process_day_text("Process Day")
            if hasattr(self, '_process_wave_btn'):
                self._process_wave_btn.setText("Process Wave")
        elif wave == 3:
            # Wave 3 (Depth)
            self.compact_header.set_process_day_text("Process Day")

            # Dynamic button text based on wave state
            if hasattr(self, '_process_wave_btn'):
                if day < days_total:
                    self._process_wave_btn.setText(f"Process Day {day}/{days_total}")
                else:
                    self._process_wave_btn.setText("Complete Wave 3 → Draft")
        elif wave == 4:
            # Post-Draft wave
            self.compact_header.set_process_day_text("Process Day")
            if hasattr(self, '_process_wave_btn'):
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

        Note: In the compact header design, pending offers count is not displayed.
        This method now only stores the count internally.

        Args:
            count: Number of pending offers from user's team
        """
        self._pending_offers_count = count
        # No-op - pending offers count not shown in compact header

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