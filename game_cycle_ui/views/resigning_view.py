"""
Re-signing View - Shows GM extension recommendations and cap relief options.

Redesigned layout with 50/50 split:
- Left: GM Extension Recommendations (inline table with Approve/Reject per row)
- Right: Do Not Extend recommendations + Cap Relief options

Allows the owner to review and approve GM's extension recommendations,
see players the GM recommends not extending, and manage cap space.
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QScrollArea, QApplication, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.dialogs import ContractDetailsDialog
from game_cycle_ui.theme import (
    apply_table_style,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
    DANGER_BUTTON_STYLE,
    WARNING_BUTTON_STYLE,
    Colors,
    Typography,
    FontSizes,
    TextColors
)
from game_cycle_ui.widgets import SummaryPanel
from game_cycle_ui.widgets.splitter_layout_mixin import SplitterLayoutMixin
from game_cycle_ui.widgets.hover_card import HoverCard
from game_cycle_ui.widgets.roster_health_widget import RosterHealthWidget
from game_cycle_ui.utils.table_utils import NumericTableWidgetItem, TableCellHelper
from constants.position_abbreviations import get_position_abbreviation
from utils.player_field_extractors import extract_overall_rating


class ResigningView(QWidget, SplitterLayoutMixin):
    """
    View for the re-signing stage.

    Redesigned layout with 50/50 split:
    - Summary panel at top (full width)
    - QSplitter with 50/50 ratio
      - Left: GM Extension Recommendations (inline table with Approve/Reject)
      - Right: Do Not Extend list + Cap Relief options (scrollable)
    - Instructions at bottom (full width)
    """

    # Signals emitted when user takes action
    player_resigned = Signal(int)  # player_id
    player_released = Signal(int)  # player_id
    cap_validation_changed = Signal(bool, int)  # (is_valid, over_cap_amount)
    proposals_reviewed = Signal(list)  # List of (proposal_id, approved: bool) tuples
    restructure_completed = Signal(int, int)  # contract_id, cap_savings
    early_cut_completed = Signal(int, int, int)  # player_id, dead_money, cap_savings
    restructure_proposal_approved = Signal(dict)  # proposal dict
    restructure_proposal_rejected = Signal(dict)  # proposal dict
    gm_reevaluation_requested = Signal()  # Request GM to re-evaluate extensions with current cap

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._db_path: str = ""
        self._dynasty_id: Optional[str] = None
        self._team_id: int = 0
        self._season: int = 2025
        self._team_name: str = ""
        self._available_cap_space: int = 0  # Track cap space for affordability checks
        self._base_available_cap: int = 0  # Base cap space before extensions (for projection)
        self._is_over_cap: bool = False  # Track if team is over the cap
        self._over_cap_amount: int = 0  # Track how much over the cap
        self._gm_proposals: List[Dict] = []  # GM extension proposals (legacy format)
        self._all_recommendations: List[Dict] = []  # Unified player recommendations (new format)
        self._restructure_proposals: List[Dict] = []  # GM restructure proposals
        self._proposal_cards: Dict[int, QWidget] = {}  # contract_id -> card widget for restructure proposals
        self._approved_proposals: set = set()  # Track approved proposal_ids
        self._rejected_proposals: set = set()  # Track rejected proposal_ids
        self._toggle_states: Dict[str, bool] = {}  # proposal_id -> is_approved (True=ON)
        self._setup_ui()

    def set_db_path(self, db_path: str):
        """Set the database path for contract lookups."""
        self._db_path = db_path

    def set_context(
        self,
        dynasty_id: str,
        db_path: str,
        season: int,
        team_name: str = "",
        team_id: int = 0
    ):
        """Set context for player detail dialogs and cap operations.

        Args:
            dynasty_id: Current dynasty ID
            db_path: Path to the database
            season: Current season year
            team_name: Name of the user's team (optional)
            team_id: Team ID for cap operations
        """
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season
        self._team_name = team_name
        self._team_id = team_id

    def _setup_ui(self):
        """Build the UI layout with two-panel split (50/50)."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel at top (full width)
        self._create_summary_panel(layout)

        # Main content - horizontal splitter (50/50 ratio)
        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()
        self.content_splitter = self._create_content_splitter(
            left_panel, right_panel, ratio=(500, 500)
        )
        layout.addWidget(self.content_splitter, stretch=1)

        # Action instructions (full width, bottom)
        self._create_instructions(layout)

    def _create_left_panel(self) -> QWidget:
        """Create left panel with GM extension recommendations table."""
        panel, panel_layout = self._create_left_panel_container()

        # "No recommendations" placeholder (shown when no extension proposals)
        self._create_no_recommendations_placeholder(panel_layout)

        # GM Extension Recommendations inline table
        self._create_gm_extensions_table(panel_layout)

        return panel

    def _create_no_recommendations_placeholder(self, parent_layout: QVBoxLayout):
        """Create placeholder shown when there are no GM extension recommendations."""
        self.no_recommendations_widget = QWidget()
        no_rec_layout = QVBoxLayout(self.no_recommendations_widget)
        no_rec_layout.setContentsMargins(20, 40, 20, 40)
        no_rec_layout.setSpacing(16)

        # Icon/header
        header = QLabel("No Extension Recommendations")
        header.setFont(QFont(Typography.FAMILY, 16, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {TextColors.ON_LIGHT_SECONDARY};")
        header.setAlignment(Qt.AlignCenter)
        no_rec_layout.addWidget(header)

        # Explanation text
        explanation = QLabel(
            "Your GM has not made any extension recommendations.\n\n"
            "This could mean:\n"
            "• No players have expiring contracts\n"
            "• Owner directives have not been set\n"
            "• All expiring players are recommended for release"
        )
        explanation.setWordWrap(True)
        explanation.setFont(QFont(Typography.FAMILY, 12))
        explanation.setStyleSheet(f"color: {TextColors.ON_LIGHT_MUTED};")
        explanation.setAlignment(Qt.AlignCenter)
        no_rec_layout.addWidget(explanation)

        no_rec_layout.addStretch()
        parent_layout.addWidget(self.no_recommendations_widget, stretch=1)
        # Show by default (hidden when proposals exist)
        self.no_recommendations_widget.show()

    def _create_right_panel(self) -> QScrollArea:
        """Create right panel with Team Needs + Cap Relief (scrollable)."""
        # Create content layout for sidebar
        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)

        # Team Needs section (position priorities)
        self._create_team_needs_section(content_layout)

        # Cap Relief section (visible when over cap)
        self._create_cap_relief_section(content_layout)

        # Push content to top
        content_layout.addStretch()

        return self._create_scrollable_sidebar(content_layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing cap space and counts."""
        summary_panel = SummaryPanel("Re-signing Summary")

        # Cap space (green)
        self.cap_space_label = summary_panel.add_stat("Available Cap Space", "$0", Colors.SUCCESS)

        # Expiring contracts count (no color)
        self.expiring_count_label = summary_panel.add_stat("Expiring Contracts", "0")

        # Pending re-signs (blue)
        self.resign_count_label = summary_panel.add_stat("Pending Re-signs", "0", Colors.INFO)

        # Total spending (no color)
        self.spending_label = summary_panel.add_stat("Total Spending", "$0")

        # Cap rollover (purple - #7B1FA2)
        self.rollover_label = summary_panel.add_stat("Cap Rollover", "$0", "#7B1FA2")

        summary_panel.add_stretch()
        parent_layout.addWidget(summary_panel)

    def _create_gm_extensions_table(self, parent_layout: QVBoxLayout):
        """Create inline table for all expiring contract players."""
        self.gm_extensions_group = QGroupBox("EXPIRING CONTRACTS")
        self.gm_extensions_group.setStyleSheet(f"""
            QGroupBox {{
                font-family: {Typography.FAMILY};
                font-size: {FontSizes.H4};
                font-weight: bold;
                color: {Colors.INFO};
                border: 2px solid {Colors.INFO};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 16px;
                background-color: rgba(74, 144, 217, 0.05);
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 8px;
                background-color: #1a2a3a;
                border-radius: 4px;
            }}
        """)

        group_layout = QVBoxLayout(self.gm_extensions_group)
        group_layout.setSpacing(8)

        # Summary row with count and total AAV
        summary_row = QHBoxLayout()

        self.extension_summary_label = QLabel("0 extension(s) recommended")
        self.extension_summary_label.setFont(QFont(Typography.FAMILY, 12))
        self.extension_summary_label.setStyleSheet(f"color: {TextColors.ON_LIGHT_SECONDARY};")
        summary_row.addWidget(self.extension_summary_label)

        summary_row.addStretch()

        # Re-evaluate GM button
        self.reevaluate_gm_btn = QPushButton("⟳ Re-evaluate GM")
        self.reevaluate_gm_btn.setStyleSheet(WARNING_BUTTON_STYLE)
        self.reevaluate_gm_btn.setToolTip(
            "Ask your GM to re-evaluate extensions based on current cap space.\n"
            "This will reset all toggles to new GM recommendations."
        )
        self.reevaluate_gm_btn.clicked.connect(self._on_reevaluate_gm_clicked)
        summary_row.addWidget(self.reevaluate_gm_btn)

        # Approve All button
        self.approve_all_btn = QPushButton("Approve All")
        self.approve_all_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.approve_all_btn.clicked.connect(self._on_approve_all_extensions)
        summary_row.addWidget(self.approve_all_btn)

        # Reject All button
        self.reject_all_btn = QPushButton("Reject All")
        self.reject_all_btn.setStyleSheet(DANGER_BUTTON_STYLE)
        self.reject_all_btn.clicked.connect(self._on_reject_all_extensions)
        summary_row.addWidget(self.reject_all_btn)

        group_layout.addLayout(summary_row)

        # Extensions table
        self.extensions_table = QTableWidget()
        self.extensions_table.setColumnCount(8)
        self.extensions_table.setHorizontalHeaderLabels([
            "Player", "Pos", "Age", "OVR", "Proposed AAV", "Years", "GM Reasoning", "Approve"
        ])

        # Apply standard table styling
        apply_table_style(self.extensions_table)

        # Enable sorting
        self.extensions_table.setSortingEnabled(True)

        # Set row height for action buttons
        self.extensions_table.verticalHeader().setDefaultSectionSize(44)

        # Column widths
        header = self.extensions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Player name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # Pos
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Age
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # OVR
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)    # AAV
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)    # Years
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # Reasoning
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)    # Action

        self.extensions_table.setColumnWidth(1, 50)   # Pos
        self.extensions_table.setColumnWidth(2, 50)   # Age
        self.extensions_table.setColumnWidth(3, 50)   # OVR
        self.extensions_table.setColumnWidth(4, 100)  # AAV
        self.extensions_table.setColumnWidth(5, 60)   # Years
        self.extensions_table.setColumnWidth(7, 80)   # Approve toggle

        group_layout.addWidget(self.extensions_table, stretch=1)

        # Hover card for GM Reasoning column
        self._hover_card = HoverCard(self)
        self.extensions_table.setMouseTracking(True)
        self.extensions_table.cellEntered.connect(self._on_cell_entered)
        self._original_leave_event = self.extensions_table.leaveEvent
        self.extensions_table.leaveEvent = self._on_table_leave

        parent_layout.addWidget(self.gm_extensions_group, stretch=1)

        # Hidden by default until proposals are set
        self.gm_extensions_group.hide()

    def _create_team_needs_section(self, parent_layout: QVBoxLayout):
        """Create Team Needs section using RosterHealthWidget."""
        # Create RosterHealthWidget for visual position group health display
        self.roster_health = RosterHealthWidget()
        parent_layout.addWidget(self.roster_health)

    def _create_cap_relief_section(self, parent_layout: QVBoxLayout):
        """Create cap relief options section (visible when over cap)."""
        self.cap_relief_group = QGroupBox("CAP RELIEF OPTIONS")
        self.cap_relief_group.setStyleSheet(f"""
            QGroupBox {{
                font-family: {Typography.FAMILY};
                font-size: {FontSizes.H4};
                font-weight: bold;
                color: {Colors.WARNING};
                border: 2px solid {Colors.WARNING};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 16px;
                background-color: rgba(255, 152, 0, 0.1);
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 8px;
                background-color: #FFFFFF;
                border-radius: 4px;
            }}
        """)

        group_layout = QVBoxLayout(self.cap_relief_group)
        group_layout.setSpacing(8)

        # Warning message
        self.over_cap_warning = QLabel()
        self.over_cap_warning.setWordWrap(True)
        self.over_cap_warning.setStyleSheet(f"color: {Colors.ERROR}; font-size: 12px;")
        group_layout.addWidget(self.over_cap_warning)

        # Help text
        help_label = QLabel(
            "Create cap space by restructuring contracts or cutting players:"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet(f"color: {TextColors.ON_LIGHT_SECONDARY}; font-size: 11px;")
        group_layout.addWidget(help_label)

        # GM Restructure Recommendations subsection
        self._create_gm_restructure_subsection(group_layout)

        # Buttons layout
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(6)

        # Restructure button (hidden when proposals exist)
        self.restructure_btn = QPushButton("Restructure Contracts...")
        self.restructure_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.restructure_btn.setToolTip(
            "Convert base salary to signing bonus to reduce current year cap hit"
        )
        self.restructure_btn.clicked.connect(self._on_restructure_clicked)
        btn_layout.addWidget(self.restructure_btn)

        # Early cuts button
        self.early_cuts_btn = QPushButton("Early Roster Cuts...")
        self.early_cuts_btn.setStyleSheet(DANGER_BUTTON_STYLE)
        self.early_cuts_btn.setToolTip(
            "Release players to free up cap space (warning: dead money may apply)"
        )
        self.early_cuts_btn.clicked.connect(self._on_early_cuts_clicked)
        btn_layout.addWidget(self.early_cuts_btn)

        group_layout.addLayout(btn_layout)

        parent_layout.addWidget(self.cap_relief_group)

        # Hidden by default - shown when over cap
        self.cap_relief_group.hide()

    def _create_gm_restructure_subsection(self, parent_layout: QVBoxLayout):
        """Create GM restructure recommendations subsection."""
        # Container widget for all restructure proposal cards
        self.restructure_proposals_widget = QWidget()
        self.restructure_proposals_layout = QVBoxLayout(self.restructure_proposals_widget)
        self.restructure_proposals_layout.setSpacing(8)
        self.restructure_proposals_layout.setContentsMargins(0, 0, 0, 0)

        # Header for the subsection
        header_label = QLabel("GM RESTRUCTURE RECOMMENDATIONS")
        header_label.setFont(QFont(Typography.FAMILY, 12, QFont.Weight.Bold))
        header_label.setStyleSheet(f"color: {Colors.INFO}; padding: 4px 0px;")
        self.restructure_proposals_layout.addWidget(header_label)

        # Placeholder for proposal cards
        # Individual cards will be added dynamically via set_restructure_proposals()

        parent_layout.addWidget(self.restructure_proposals_widget)
        self.restructure_proposals_widget.hide()  # Hidden until proposals are set

    def _create_instructions(self, parent_layout: QVBoxLayout):
        """Create instruction text at the bottom."""
        instructions = QLabel(
            "Review GM's extension recommendations on the left. "
            "Approve to re-sign the player at the proposed terms, or Reject to let them enter free agency. "
            "Use Cap Relief options if you need to create cap space."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic; padding: 8px;")
        parent_layout.addWidget(instructions)

    def set_cap_space(self, cap_space: int):
        """Update the cap space display."""
        formatted = f"${cap_space:,}"
        self.cap_space_label.setText(formatted)

        # Color based on cap space (red if negative)
        if cap_space < 0:
            self.cap_space_label.setStyleSheet(f"color: {Colors.ERROR};")  # Red
        else:
            self.cap_space_label.setStyleSheet(f"color: {Colors.SUCCESS};")  # Green

    def _calculate_projected_cap(self) -> int:
        """
        Calculate cap space remaining after approved extensions.

        Uses toggle states to determine which extensions are approved.
        Supports both new unified format (_all_recommendations) and
        legacy format (_gm_proposals).

        Returns:
            Projected cap space after approved extension commitments
        """
        # Try new unified format first
        if hasattr(self, '_all_recommendations') and self._all_recommendations:
            approved_aav = sum(
                r.get("proposed_contract", {}).get("aav", 0)
                for r in self._all_recommendations
                if self._toggle_states.get(str(r.get("player_id")), False)
            )
            return self._base_available_cap - approved_aav

        # Fall back to legacy format
        approved_aav = sum(
            p.get("details", {}).get("proposed_contract", {}).get("aav", 0)
            for p in self._gm_proposals
            if self._toggle_states.get(p.get("proposal_id"), True)
        )
        return self._base_available_cap - approved_aav

    def _refresh_cap_display(self):
        """
        Update cap space display with base → projected format (FA-style).

        Shows both the base available cap and the projected cap after
        approved extensions, matching the Free Agency view pattern.
        """
        projected = self._calculate_projected_cap()
        approved_count = sum(1 for v in self._toggle_states.values() if v)

        # Format: "$45.2M → $28.5M (3 approved)"
        base_str = f"${self._base_available_cap / 1_000_000:.1f}M"
        if projected >= 0:
            proj_str = f"${projected / 1_000_000:.1f}M"
        else:
            proj_str = f"-${abs(projected) / 1_000_000:.1f}M"

        if approved_count > 0:
            display_text = f"{base_str} → {proj_str} ({approved_count} approved)"
        else:
            display_text = base_str

        self.cap_space_label.setText(display_text)

        # Color based on projected cap
        if projected < 0:
            self.cap_space_label.setStyleSheet(f"color: {Colors.ERROR};")
        else:
            self.cap_space_label.setStyleSheet(f"color: {Colors.SUCCESS};")

        # Update over-cap state
        self._is_over_cap = projected < 0
        self._over_cap_amount = abs(projected) if projected < 0 else 0

        # Emit cap validation signal to enable/disable Process button
        self.cap_validation_changed.emit(not self._is_over_cap, self._over_cap_amount)

    def set_cap_data(self, cap_data: Dict):
        """
        Update the view with full cap data from CapHelper.

        Args:
            cap_data: Dict with available_space, salary_cap_limit, total_spending,
                      dead_money, is_compliant, carryover
                      (is_over_cap and over_cap_amount calculated from available_space)
        """
        available = cap_data.get("available_space", 0)
        spending = cap_data.get("total_spending", 0)
        carryover = cap_data.get("carryover", 0)

        # Calculate over-cap status from available space
        is_over_cap = available < 0
        over_cap_amount = abs(available) if is_over_cap else 0

        # Store cap state
        self._available_cap_space = available
        self._base_available_cap = available  # Store base for projection calculations
        self._is_over_cap = is_over_cap
        self._over_cap_amount = over_cap_amount

        # Update spending label
        self.spending_label.setText(f"${spending:,}")

        # Update rollover label (carryover from previous season)
        self.rollover_label.setText(f"${carryover:,}")

        # Update cap space display with projection if we have proposals
        if self._gm_proposals and self._toggle_states:
            self._refresh_cap_display()
        else:
            self.set_cap_space(available)
            # Emit cap validation signal to enable/disable Process button
            self.cap_validation_changed.emit(not is_over_cap, over_cap_amount)

        # Show/hide cap relief section based on cap status
        self._update_cap_relief_visibility(over_cap_amount)

    def _update_cap_relief_visibility(self, over_cap_amount: int = 0):
        """Show/hide cap relief section based on cap status AND active proposals.

        The section remains visible if:
        1. Team is over the cap, OR
        2. There are still pending restructure proposals to review
        """
        has_active_proposals = bool(self._proposal_cards)

        # Show/hide over-cap warning based on cap status
        if self._is_over_cap and over_cap_amount > 0:
            self.over_cap_warning.setText(
                f"Your team is ${over_cap_amount:,} over the salary cap. "
                f"You must create cap space before the league year begins."
            )
            self.over_cap_warning.show()
        else:
            self.over_cap_warning.hide()

        # Always keep both buttons visible - they're independent cap management tools
        self.early_cuts_btn.show()
        self.restructure_btn.show()
        self.cap_relief_group.show()

    def set_restructure_proposals(self, proposals: List[Dict]):
        """
        Set and display GM restructure proposals.

        Args:
            proposals: List of proposal dicts with:
                - player_name: str
                - position: str
                - overall: int
                - current_cap_hit: int
                - new_cap_hit: int
                - cap_savings: int
                - dead_money_added: int
                - gm_reasoning: str
                - proposal_id: str (optional, for tracking)
        """
        self._restructure_proposals = proposals
        self._proposal_cards.clear()  # Clear the card tracking dictionary

        # Clear existing proposal cards (except the header)
        # Remove all widgets except the first one (header label)
        while self.restructure_proposals_layout.count() > 1:
            item = self.restructure_proposals_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        if not proposals:
            self.restructure_proposals_widget.hide()
            self.restructure_btn.show()  # Show manual restructure button
            return

        # Show proposals widget
        self.restructure_proposals_widget.show()
        self.restructure_btn.hide()  # Hide manual restructure button when proposals exist

        # Create a card for each proposal and track by contract_id
        for proposal in proposals:
            card = self._create_restructure_proposal_card(proposal)
            contract_id = proposal.get("contract_id")
            if contract_id:
                self._proposal_cards[contract_id] = card  # Track card by contract_id
            self.restructure_proposals_layout.addWidget(card)

    def clear_restructure_proposals(self):
        """
        Clear all restructure proposals and their cards.

        Used when re-evaluating to allow fresh proposal generation.
        """
        self._restructure_proposals.clear()
        self._proposal_cards.clear()

        # Remove all card widgets (except header)
        while self.restructure_proposals_layout.count() > 1:
            item = self.restructure_proposals_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        # Hide proposals widget, show manual restructure button
        self.restructure_proposals_widget.hide()
        self.restructure_btn.show()

    def _create_restructure_proposal_card(self, proposal: Dict) -> QWidget:
        """Create a single restructure proposal card widget."""
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(12, 10, 12, 10)

        # Row 1: Player info
        player_info_layout = QHBoxLayout()
        player_name = proposal.get("player_name", "Unknown")
        position = get_position_abbreviation(proposal.get("position", ""))
        overall = extract_overall_rating(proposal, default=0)

        player_label = QLabel(f"{player_name} ({position}, {overall} OVR)")
        player_label.setFont(QFont(Typography.FAMILY, 12, QFont.Weight.Bold))
        player_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        player_info_layout.addWidget(player_label)
        player_info_layout.addStretch()

        card_layout.addLayout(player_info_layout)

        # Row 2: Cap hit change
        current_cap_hit = proposal.get("current_cap_hit", 0)
        new_cap_hit = proposal.get("new_cap_hit", 0)
        cap_hit_label = QLabel(
            f"Cap Hit: ${current_cap_hit / 1_000_000:.1f}M → ${new_cap_hit / 1_000_000:.1f}M"
        )
        cap_hit_label.setFont(QFont(Typography.FAMILY, 11))
        cap_hit_label.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY};")
        card_layout.addWidget(cap_hit_label)

        # Row 3: Savings and dead money
        cap_savings = proposal.get("cap_savings", 0)
        dead_money = proposal.get("dead_money_added", 0)

        savings_layout = QHBoxLayout()

        savings_label = QLabel(f"Savings: +${cap_savings / 1_000_000:.1f}M")
        savings_label.setFont(QFont(Typography.FAMILY, 11, QFont.Weight.Bold))
        savings_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        savings_layout.addWidget(savings_label)

        dead_money_label = QLabel(f"Dead Money: +${dead_money / 1_000_000:.1f}M")
        dead_money_label.setFont(QFont(Typography.FAMILY, 11))
        dead_money_label.setStyleSheet(f"color: {Colors.WARNING};")
        savings_layout.addWidget(dead_money_label)

        savings_layout.addStretch()

        card_layout.addLayout(savings_layout)

        # Row 4: GM reasoning
        reasoning = proposal.get("gm_reasoning", "No reasoning provided")
        reasoning_label = QLabel(f'"{reasoning}"')
        reasoning_label.setWordWrap(True)
        reasoning_label.setFont(QFont(Typography.FAMILY, 10))
        reasoning_label.setStyleSheet(f"color: {TextColors.ON_DARK_MUTED}; font-style: italic;")
        card_layout.addWidget(reasoning_label)

        # Row 5: Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        approve_btn = QPushButton("Approve")
        approve_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        approve_btn.clicked.connect(lambda: self._on_restructure_proposal_approved(proposal, card))
        button_layout.addWidget(approve_btn)

        reject_btn = QPushButton("Reject")
        reject_btn.setStyleSheet(DANGER_BUTTON_STYLE)
        reject_btn.clicked.connect(lambda: self._on_restructure_proposal_rejected(proposal, card))
        button_layout.addWidget(reject_btn)

        card_layout.addLayout(button_layout)

        return card

    def _on_restructure_proposal_approved(self, proposal: Dict, card: QWidget):
        """
        Handle approval of a restructure proposal.

        Emits signal to controller for execution. Card is removed by controller
        calling remove_proposal_card(contract_id) after successful execution.
        If execution fails, card stays visible for retry.
        """
        # Emit signal with the proposal - controller will execute and call remove_proposal_card on success
        self.restructure_proposal_approved.emit(proposal)

    def remove_proposal_card(self, contract_id: int):
        """
        Remove a restructure proposal card by contract ID.

        Called by controller after successful restructure execution,
        or immediately after rejection.

        Args:
            contract_id: The contract ID to remove
        """
        if contract_id in self._proposal_cards:
            card = self._proposal_cards.pop(contract_id)
            card.hide()
            card.deleteLater()

            # Also remove from proposals list
            self._restructure_proposals = [
                p for p in self._restructure_proposals
                if p.get("contract_id") != contract_id
            ]

            self._update_proposals_visibility()

    def _update_proposals_visibility(self):
        """Update visibility of proposals widget based on remaining proposals."""
        if not self._restructure_proposals:
            self.restructure_proposals_widget.hide()
            self.restructure_btn.show()

    def set_card_processing(self, contract_id: int):
        """
        Show processing state on card when approval is in progress.

        Tints the entire card blue and shows "Processing..." to indicate action is executing.

        Args:
            contract_id: The contract ID of the card to update
        """
        if contract_id in self._proposal_cards:
            card = self._proposal_cards[contract_id]

            # Tint the entire card to indicate processing (light blue)
            card.setStyleSheet("""
                background-color: #E3F2FD;
                border: 2px solid #2196F3;
                border-radius: 6px;
            """)

            # Find and disable buttons, show "Processing..."
            for btn in card.findChildren(QPushButton):
                btn.setEnabled(False)
                if btn.text() == "Approve":
                    btn.setText("Processing...")
                    btn.setStyleSheet("""
                        background: #2196F3;
                        color: white;
                        font-weight: bold;
                        border-radius: 4px;
                        padding: 6px 12px;
                    """)

            # Force UI repaint so user sees processing state
            card.repaint()
            self.repaint()
            QApplication.processEvents()

    def set_card_success(self, contract_id: int, cap_savings: int, on_complete=None):
        """
        Show success state on card, then remove after 1.5 second delay.

        Changes entire card to green with success styling to make feedback unmissable.

        Args:
            contract_id: The contract ID of the card to update
            cap_savings: The amount of cap space saved (in dollars)
            on_complete: Optional callback to invoke after timer fires (for cap refresh)
        """
        if contract_id in self._proposal_cards:
            card = self._proposal_cards[contract_id]

            # Change ENTIRE CARD to success styling (green background with border)
            card.setStyleSheet("""
                background-color: #E8F5E9;
                border: 2px solid #4CAF50;
                border-radius: 6px;
            """)

            # Show success message on the approve button
            for btn in card.findChildren(QPushButton):
                if btn.text() == "Processing...":
                    savings_str = f"${cap_savings / 1_000_000:.1f}M"
                    btn.setText(f"✓ Saved {savings_str}")
                    btn.setStyleSheet("""
                        background: #2E7D32;
                        color: white;
                        font-weight: bold;
                        border-radius: 4px;
                        padding: 8px 16px;
                        font-size: 14px;
                    """)
                elif btn.text() == "Reject":
                    btn.hide()  # Hide reject button on success

            # Force UI repaint so user sees the success message
            card.update()
            card.repaint()
            QApplication.processEvents()

            # Create a timer that we keep a reference to (prevents garbage collection)
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(1500)  # 1.5 seconds to ensure visibility

            # Store contract_id and callback in timer's properties
            timer.setProperty("contract_id", contract_id)
            timer.setProperty("on_complete", on_complete)
            timer.timeout.connect(self._on_success_timer_fired)
            timer.start()

    def _on_success_timer_fired(self):
        """Handle timer timeout - remove the card after success display."""
        timer = self.sender()
        if timer:
            contract_id = timer.property("contract_id")
            on_complete = timer.property("on_complete")
            if contract_id is not None:
                self.remove_proposal_card(contract_id)
            # Call the completion callback (e.g., to refresh cap display)
            if on_complete and callable(on_complete):
                on_complete()
            timer.deleteLater()

    def set_card_failure(self, contract_id: int, error: str):
        """
        Show failure state on card, re-enable buttons for retry.

        Restores the approve button and shows an error indication so the user
        can try again or reject the proposal.

        Args:
            contract_id: The contract ID of the card to update
            error: The error message (currently not displayed, but logged)
        """
        if contract_id in self._proposal_cards:
            card = self._proposal_cards[contract_id]
            for btn in card.findChildren(QPushButton):
                btn.setEnabled(True)
                if "Processing" in btn.text() or "✓" in btn.text():
                    btn.setText("Approve")
                    btn.setStyleSheet(PRIMARY_BUTTON_STYLE)  # Reset to default style

    def _on_restructure_proposal_rejected(self, proposal: Dict, card: QWidget):
        """Handle rejection of a restructure proposal."""
        # Emit signal with the proposal
        self.restructure_proposal_rejected.emit(proposal)

        # Immediately remove the card (rejection doesn't need controller confirmation)
        contract_id = proposal.get("contract_id")
        self.remove_proposal_card(contract_id)

    # =========================================================================
    # GM Extension Recommendations (Inline Table)
    # =========================================================================

    def set_gm_proposals(self, proposals: List[Dict]):
        """
        Display GM's extension recommendations in the inline table.

        Args:
            proposals: List of proposal dicts with:
                - proposal_id: str
                - details: {player_name, position, age, overall, proposed_contract: {aav, years}}
                - gm_reasoning: str
                - confidence: float (0.0-1.0)
                - auto_approved: bool (True if Trust GM mode)
        """
        self._gm_proposals = proposals
        self._approved_proposals.clear()
        self._rejected_proposals.clear()
        self._toggle_states.clear()  # Clear toggle states

        if not proposals:
            self.gm_extensions_group.hide()
            self.no_recommendations_widget.show()  # Show placeholder when no proposals
            self.expiring_count_label.setText("0")
            return

        self.no_recommendations_widget.hide()  # Hide placeholder when we have proposals
        self.gm_extensions_group.show()

        # Calculate summary stats
        count = len(proposals)
        total_aav = sum(
            p.get("details", {}).get("proposed_contract", {}).get("aav", 0)
            for p in proposals
        )

        self.extension_summary_label.setText(
            f"{count} extension(s) recommended • Total AAV: ${total_aav / 1_000_000:.1f}M"
        )
        self.expiring_count_label.setText(str(count))

        # Populate the table
        self.extensions_table.setRowCount(len(proposals))
        for row, proposal in enumerate(proposals):
            self._populate_extension_row(row, proposal)

        # Update Approve All button state
        self.approve_all_btn.setEnabled(count > 0)

        # Update extension summary with toggle states
        self._update_extension_summary()

        # Show initial projected cap (all extensions default to approved)
        # Always refresh regardless of base cap sign - projection shows impact
        self._refresh_cap_display()

    def set_team_needs(self, needs: Dict):
        """
        DEPRECATED: This method is kept for backward compatibility but no longer used.
        Team needs are now displayed via set_roster_health() using RosterHealthWidget.

        Args:
            needs: Dict with "high_priority" and "medium_priority" lists (no longer used)
        """
        pass  # Deprecated - roster health widget is now used instead

    def set_roster_health(self, roster_players: List[Dict], expiring_ids: set):
        """
        Update roster health widget with current roster composition.

        Args:
            roster_players: List of dicts with player_id, position, overall
            expiring_ids: Set of player IDs with expiring contracts
        """
        if hasattr(self, 'roster_health'):
            self.roster_health.update_scores(roster_players, expiring_ids)

    def set_all_players(self, recommendations: List[Dict], is_reevaluation: bool = False):
        """
        Display ALL expiring contract players with GM recommendations.

        This is the new unified view - shows all players with toggles pre-set
        to GM recommendations. Owner can override by toggling.

        Args:
            recommendations: List of dicts with:
                - player_id, name, position, age, overall
                - gm_recommends: bool (True = GM recommends extension)
                - proposed_contract: {aav, years, total, guaranteed}
                - gm_reasoning: str
                - priority_tier: int (1-5)
            is_reevaluation: If True, indicates this is a re-evaluation (restore UI, animate changes)
        """
        # Track old recommendations if this is a re-evaluation (for animation)
        old_recommendations = {}
        if is_reevaluation and hasattr(self, '_all_recommendations'):
            old_recommendations = {
                str(rec.get("player_id")): rec.get("gm_recommends", False)
                for rec in self._all_recommendations
            }

        self._all_recommendations = recommendations
        self._gm_proposals = []  # Clear old format
        self._approved_proposals.clear()
        self._rejected_proposals.clear()
        self._toggle_states.clear()

        if not recommendations:
            self.gm_extensions_group.hide()
            self.no_recommendations_widget.show()
            self.expiring_count_label.setText("0")
            return

        self.no_recommendations_widget.hide()
        self.gm_extensions_group.show()

        # Populate table with ALL players
        self.extensions_table.setRowCount(len(recommendations))

        changed_rows = []
        for row, rec in enumerate(recommendations):
            self._populate_unified_row(row, rec)

            # Initialize toggle to GM recommendation
            player_id = str(rec.get("player_id"))
            new_recommends = rec.get("gm_recommends", False)
            self._toggle_states[player_id] = new_recommends

            # Track if recommendation changed (for animation)
            if is_reevaluation and player_id in old_recommendations:
                if old_recommendations[player_id] != new_recommends:
                    changed_rows.append(row)

        # Update summary
        self._update_unified_summary()
        self.expiring_count_label.setText(str(len(recommendations)))

        # Refresh cap display
        self._refresh_cap_display()

        # If this is a re-evaluation, restore UI and animate changes
        if is_reevaluation:
            self._restore_reevaluation_ui(len(recommendations), len(changed_rows))

            # Animate changed rows
            for row in changed_rows:
                self._animate_row_change(row)

    def _restore_reevaluation_ui(self, total_count: int, changed_count: int):
        """Restore UI state after re-evaluation completes."""
        # Restore summary label style
        self.extension_summary_label.setStyleSheet(f"color: {TextColors.ON_LIGHT_SECONDARY};")

        # Show success message briefly, then restore normal summary
        success_text = f"✓ Re-evaluated! {changed_count} recommendation(s) changed."
        self.extension_summary_label.setText(success_text)
        self.extension_summary_label.setStyleSheet(
            f"background-color: rgba(76, 175, 80, 0.2); "
            f"color: {Colors.SUCCESS}; "
            f"padding: 8px; "
            f"border-radius: 4px; "
            f"font-weight: bold;"
        )

        # Restore normal summary after 2 seconds
        QTimer.singleShot(2000, self._update_unified_summary)
        QTimer.singleShot(2000, lambda: self.extension_summary_label.setStyleSheet(
            f"color: {TextColors.ON_LIGHT_SECONDARY};"
        ))

        # Show action buttons again
        self.reevaluate_gm_btn.show()
        self.reevaluate_gm_btn.setEnabled(True)  # Re-enable
        self.approve_all_btn.show()
        self.reject_all_btn.show()

    def _animate_row_change(self, row: int):
        """Animate a row to show it changed with a green pulse effect."""
        # Store original background
        for col in range(self.extensions_table.columnCount()):
            item = self.extensions_table.item(row, col)
            if item:
                # Set green background
                item.setBackground(QColor(76, 175, 80, 100))  # Light green

        # Restore original background after 1 second
        QTimer.singleShot(1000, lambda: self._clear_row_animation(row))

    def _clear_row_animation(self, row: int):
        """Clear animation and restore normal row styling."""
        # Get the current toggle state for this row
        name_item = self.extensions_table.item(row, 0)
        if not name_item:
            return

        player_id = name_item.data(Qt.UserRole)
        is_approved = self._toggle_states.get(str(player_id), False)

        # Clear background color and restore normal styling
        for col in range(self.extensions_table.columnCount()):
            item = self.extensions_table.item(row, col)
            if item:
                item.setBackground(QColor(0, 0, 0, 0))  # Transparent

        # Re-apply row styling based on toggle state
        self._apply_row_styling(row, is_approved)

    def _populate_unified_row(self, row: int, rec: Dict):
        """Populate a single row for any player (recommended or not)."""
        player_id = rec.get("player_id")
        gm_recommends = rec.get("gm_recommends", False)
        contract = rec.get("proposed_contract") or {}

        # Player name
        name = rec.get("name", "Unknown")
        name_item = QTableWidgetItem(name)
        name_item.setData(Qt.UserRole, str(player_id))
        name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.extensions_table.setItem(row, 0, name_item)

        # Position
        pos = get_position_abbreviation(rec.get("position", ""))
        pos_item = QTableWidgetItem(pos)
        pos_item.setTextAlignment(Qt.AlignCenter)
        pos_item.setFlags(pos_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.extensions_table.setItem(row, 1, pos_item)

        # Age (color coded: 32+ red, 30-31 orange)
        age = rec.get("age", 0)
        age_item = NumericTableWidgetItem(age)
        age_item.setTextAlignment(Qt.AlignCenter)
        age_item.setFlags(age_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if age >= 32:
            age_item.setForeground(QColor(Colors.ERROR))
        elif age >= 30:
            age_item.setForeground(QColor(Colors.WARNING))
        self.extensions_table.setItem(row, 2, age_item)

        # OVR (color coded: 85+ green, 75+ blue)
        ovr = extract_overall_rating(rec, default=0)
        ovr_item = NumericTableWidgetItem(ovr)
        ovr_item.setTextAlignment(Qt.AlignCenter)
        ovr_item.setFlags(ovr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if ovr >= 85:
            ovr_item.setForeground(QColor(Colors.SUCCESS))
        elif ovr >= 75:
            ovr_item.setForeground(QColor(Colors.INFO))
        self.extensions_table.setItem(row, 3, ovr_item)

        # Proposed AAV (show even for non-recommended, or "—" if no contract)
        aav = contract.get("aav", 0)
        aav_str = f"${aav / 1_000_000:.1f}M" if aav else "—"
        aav_item = QTableWidgetItem(aav_str)
        aav_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        aav_item.setFlags(aav_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.extensions_table.setItem(row, 4, aav_item)

        # Years
        years = contract.get("years", 0)
        years_item = NumericTableWidgetItem(years) if years else QTableWidgetItem("—")
        years_item.setTextAlignment(Qt.AlignCenter)
        years_item.setFlags(years_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.extensions_table.setItem(row, 5, years_item)

        # GM Reasoning (truncated with tooltip for full text)
        reasoning = rec.get("gm_reasoning", "")
        display_text = reasoning[:40] + "..." if len(reasoning) > 40 else reasoning
        reasoning_item = QTableWidgetItem(display_text)
        reasoning_item.setToolTip(reasoning)
        reasoning_item.setFlags(reasoning_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.extensions_table.setItem(row, 6, reasoning_item)

        # Toggle switch - pre-set to GM recommendation
        toggle_widget = QWidget()
        toggle_layout = QHBoxLayout(toggle_widget)
        toggle_layout.setContentsMargins(4, 2, 4, 2)
        toggle_layout.setAlignment(Qt.AlignCenter)

        toggle = QCheckBox()
        toggle.setChecked(gm_recommends)  # Pre-set to GM's recommendation
        toggle.setProperty("player_id", str(player_id))
        toggle.setProperty("row", row)
        toggle.setStyleSheet(self._get_toggle_stylesheet())
        toggle.stateChanged.connect(
            lambda state, pid=str(player_id), r=row: self._on_unified_toggle_changed(pid, r, state)
        )
        toggle_layout.addWidget(toggle)

        self.extensions_table.setCellWidget(row, 7, toggle_widget)

        # Apply styling based on GM recommendation
        self._apply_row_styling(row, gm_recommends)

    def _on_unified_toggle_changed(self, player_id: str, row: int, state: int):
        """Handle toggle switch state change for unified view."""
        is_approved = (state == Qt.CheckState.Checked.value)
        self._toggle_states[player_id] = is_approved

        # Apply visual styling
        self._apply_row_styling(row, is_approved)

        # Update summary counts
        self._update_unified_summary()

        # Update cap space display with projection
        self._refresh_cap_display()

    def _update_unified_summary(self):
        """Update summary label for unified player view."""
        if not hasattr(self, '_all_recommendations'):
            return

        total = len(self._all_recommendations)
        selected = sum(1 for v in self._toggle_states.values() if v)
        gm_recommended = sum(
            1 for r in self._all_recommendations if r.get("gm_recommends")
        )

        # Calculate selected AAV
        selected_aav = sum(
            r.get("proposed_contract", {}).get("aav", 0)
            for r in self._all_recommendations
            if self._toggle_states.get(str(r.get("player_id")), False)
        )

        self.extension_summary_label.setText(
            f"{total} expiring • {selected} selected • "
            f"GM recommended {gm_recommended} • "
            f"Selected AAV: ${selected_aav / 1_000_000:.1f}M"
        )

        # Update pending re-signs count (selected ones)
        self.resign_count_label.setText(str(selected))

    def _populate_extension_row(self, row: int, proposal: Dict):
        """Populate a single row in the extensions table."""
        details = proposal.get("details", {})
        contract = details.get("proposed_contract", {})
        proposal_id = proposal.get("proposal_id", "")

        # Player name (store proposal_id for action handlers)
        name = details.get("player_name", "Unknown")
        name_item = QTableWidgetItem(name)
        name_item.setData(Qt.UserRole, proposal_id)
        name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.extensions_table.setItem(row, 0, name_item)

        # Position
        pos = get_position_abbreviation(details.get("position", ""))
        pos_item = QTableWidgetItem(pos)
        pos_item.setTextAlignment(Qt.AlignCenter)
        pos_item.setFlags(pos_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.extensions_table.setItem(row, 1, pos_item)

        # Age (color coded: 32+ red, 30-31 orange)
        age = details.get("age", 0)
        age_item = NumericTableWidgetItem(age)
        age_item.setTextAlignment(Qt.AlignCenter)
        age_item.setFlags(age_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if age >= 32:
            age_item.setForeground(QColor(Colors.ERROR))
        elif age >= 30:
            age_item.setForeground(QColor(Colors.WARNING))
        self.extensions_table.setItem(row, 2, age_item)

        # OVR (color coded: 85+ green, 75+ blue)
        ovr = extract_overall_rating(details, default=0)
        ovr_item = NumericTableWidgetItem(ovr)
        ovr_item.setTextAlignment(Qt.AlignCenter)
        ovr_item.setFlags(ovr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if ovr >= 85:
            ovr_item.setForeground(QColor(Colors.SUCCESS))
        elif ovr >= 75:
            ovr_item.setForeground(QColor(Colors.INFO))
        self.extensions_table.setItem(row, 3, ovr_item)

        # Proposed AAV
        aav = contract.get("aav", 0)
        aav_item = QTableWidgetItem(f"${aav / 1_000_000:.1f}M")
        aav_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        aav_item.setFlags(aav_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.extensions_table.setItem(row, 4, aav_item)

        # Years
        years = contract.get("years", 0)
        years_item = NumericTableWidgetItem(years)
        years_item.setTextAlignment(Qt.AlignCenter)
        years_item.setFlags(years_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.extensions_table.setItem(row, 5, years_item)

        # GM Reasoning (truncated with tooltip for full text)
        reasoning = proposal.get("gm_reasoning", "")
        display_text = reasoning[:40] + "..." if len(reasoning) > 40 else reasoning
        reasoning_item = QTableWidgetItem(display_text)
        reasoning_item.setToolTip(reasoning)
        reasoning_item.setFlags(reasoning_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.extensions_table.setItem(row, 6, reasoning_item)

        # Toggle switch (defaults to ON = approved)
        toggle_widget = QWidget()
        toggle_layout = QHBoxLayout(toggle_widget)
        toggle_layout.setContentsMargins(4, 2, 4, 2)
        toggle_layout.setAlignment(Qt.AlignCenter)

        toggle = QCheckBox()
        toggle.setChecked(True)  # Default ON (approved)
        toggle.setProperty("proposal_id", proposal_id)
        toggle.setProperty("row", row)
        toggle.setStyleSheet(self._get_toggle_stylesheet())
        toggle.stateChanged.connect(
            lambda state, pid=proposal_id, r=row: self._on_extension_toggle_changed(pid, r, state)
        )
        toggle_layout.addWidget(toggle)

        self.extensions_table.setCellWidget(row, 7, toggle_widget)

        # Initialize toggle state tracking (default: approved)
        self._toggle_states[proposal_id] = True

    def _get_toggle_stylesheet(self) -> str:
        """Return CSS for styled toggle checkbox (iOS-style switch)."""
        return f"""
            QCheckBox {{
                spacing: 0px;
            }}
            QCheckBox::indicator {{
                width: 40px;
                height: 22px;
                border-radius: 11px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.SUCCESS};
                border: 2px solid {Colors.SUCCESS};
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {Colors.MUTED};
                border: 2px solid {Colors.MUTED};
            }}
        """

    def _on_extension_toggle_changed(self, proposal_id: str, row: int, state: int):
        """
        Handle toggle switch state change.

        Updates local state only - no immediate signal emission.
        The signal is emitted in batch when Process Re-signing is clicked.

        Args:
            proposal_id: The proposal ID
            row: Table row index
            state: Qt.CheckState value (0=unchecked, 2=checked)
        """
        is_approved = (state == Qt.CheckState.Checked.value)
        self._toggle_states[proposal_id] = is_approved

        # Apply dimmed styling to row if rejected (toggle OFF)
        self._apply_row_styling(row, is_approved)

        # Update summary counts
        self._update_extension_summary()

        # Update cap space display with projection (FA-style)
        self._refresh_cap_display()

    def _apply_row_styling(self, row: int, is_approved: bool):
        """
        Apply visual styling to row based on approval state.

        Approved rows: Normal appearance
        Rejected rows: Dimmed/grayed out with reduced opacity

        Args:
            row: Table row index
            is_approved: True if approved (toggle ON), False if rejected (toggle OFF)
        """
        # Set row opacity/color based on state (skip toggle column)
        for col in range(self.extensions_table.columnCount() - 1):
            item = self.extensions_table.item(row, col)
            if item:
                if is_approved:
                    # Restore normal text color
                    item.setForeground(QColor(TextColors.ON_DARK))
                else:
                    # Dim the text for rejected rows
                    item.setForeground(QColor(Colors.MUTED))

    def get_extension_decisions(self) -> List[tuple]:
        """
        Collect all extension decisions for batch processing.

        Called when "Process Re-signing" is clicked to get current toggle states.

        Returns:
            List of (proposal_id, approved: bool) tuples
        """
        return [(pid, approved) for pid, approved in self._toggle_states.items()]

    def _on_approve_all_extensions(self):
        """Toggle all extension switches to ON (approved)."""
        for row in range(self.extensions_table.rowCount()):
            name_item = self.extensions_table.item(row, 0)
            if not name_item:
                continue

            proposal_id = name_item.data(Qt.UserRole)

            # Update toggle widget
            toggle_widget = self.extensions_table.cellWidget(row, 7)
            if toggle_widget:
                toggle = toggle_widget.findChild(QCheckBox)
                if toggle:
                    toggle.setChecked(True)  # This triggers _on_extension_toggle_changed

            # Ensure state tracking is updated
            self._toggle_states[proposal_id] = True
            self._apply_row_styling(row, True)

        self._update_extension_summary()
        self._refresh_cap_display()

    def _on_reject_all_extensions(self):
        """Toggle all extension switches to OFF (rejected)."""
        for row in range(self.extensions_table.rowCount()):
            name_item = self.extensions_table.item(row, 0)
            if not name_item:
                continue

            proposal_id = name_item.data(Qt.UserRole)

            # Update toggle widget
            toggle_widget = self.extensions_table.cellWidget(row, 7)
            if toggle_widget:
                toggle = toggle_widget.findChild(QCheckBox)
                if toggle:
                    toggle.setChecked(False)  # This triggers _on_extension_toggle_changed

            # Ensure state tracking is updated
            self._toggle_states[proposal_id] = False
            self._apply_row_styling(row, False)

        self._update_extension_summary()
        self._refresh_cap_display()

    def _on_reevaluate_gm_clicked(self):
        """Handle re-evaluate GM button click - show inline confirmation."""
        # Store original summary text
        self._original_summary_text = self.extension_summary_label.text()

        # Get current cap space for display
        cap_space_text = self.cap_space_label.text() if hasattr(self, 'cap_space_label') else "current cap"

        # Create inline confirmation UI
        confirm_text = f"Re-evaluate with {cap_space_text}? All toggles will reset."
        self.extension_summary_label.setText(confirm_text)
        self.extension_summary_label.setStyleSheet(
            f"background-color: rgba(245, 124, 0, 0.2); "
            f"color: {Colors.WARNING}; "
            f"padding: 8px; "
            f"border-radius: 4px; "
            f"font-weight: bold;"
        )

        # Hide action buttons temporarily
        self.reevaluate_gm_btn.hide()
        self.approve_all_btn.hide()
        self.reject_all_btn.hide()

        # Create confirmation buttons
        self._confirm_reevaluate_btn = QPushButton("Confirm")
        self._confirm_reevaluate_btn.setStyleSheet(WARNING_BUTTON_STYLE)
        self._confirm_reevaluate_btn.clicked.connect(self._confirm_reevaluation)

        self._cancel_reevaluate_btn = QPushButton("Cancel")
        self._cancel_reevaluate_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self._cancel_reevaluate_btn.clicked.connect(self._cancel_reevaluation)

        # Add buttons to summary row
        summary_row = self.extension_summary_label.parent().layout()
        if summary_row:
            summary_row.addWidget(self._confirm_reevaluate_btn)
            summary_row.addWidget(self._cancel_reevaluate_btn)

    def _confirm_reevaluation(self):
        """User confirmed re-evaluation - show loading and emit signal."""
        # Remove confirmation buttons
        if hasattr(self, '_confirm_reevaluate_btn'):
            self._confirm_reevaluate_btn.deleteLater()
            del self._confirm_reevaluate_btn
        if hasattr(self, '_cancel_reevaluate_btn'):
            self._cancel_reevaluate_btn.deleteLater()
            del self._cancel_reevaluate_btn

        # Show loading state
        self.extension_summary_label.setText("⟳ Re-evaluating...")
        self.extension_summary_label.setStyleSheet(
            f"background-color: rgba(255, 193, 7, 0.2); "
            f"color: {Colors.WARNING}; "
            f"padding: 8px; "
            f"border-radius: 4px;"
        )

        # Disable re-evaluate button during processing
        self.reevaluate_gm_btn.setEnabled(False)

        # Emit signal to controller
        self.gm_reevaluation_requested.emit()

    def _cancel_reevaluation(self):
        """User cancelled re-evaluation - restore original UI."""
        # Remove confirmation buttons
        if hasattr(self, '_confirm_reevaluate_btn'):
            self._confirm_reevaluate_btn.deleteLater()
            del self._confirm_reevaluate_btn
        if hasattr(self, '_cancel_reevaluate_btn'):
            self._cancel_reevaluate_btn.deleteLater()
            del self._cancel_reevaluate_btn

        # Restore original summary text and style
        if hasattr(self, '_original_summary_text'):
            self.extension_summary_label.setText(self._original_summary_text)
        self.extension_summary_label.setStyleSheet(f"color: {TextColors.ON_LIGHT_SECONDARY};")

        # Show action buttons again AND re-enable them
        self.reevaluate_gm_btn.show()
        self.reevaluate_gm_btn.setEnabled(True)  # Re-enable button after cancel/error
        self.approve_all_btn.show()
        self.reject_all_btn.show()

    def _update_extension_row_status(self, row: int, status: str, color: str):
        """Update row to show decision status and disable buttons."""
        # Replace action buttons with status label
        status_label = QLabel(status)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.extensions_table.setCellWidget(row, 7, status_label)

    def _update_extension_summary(self):
        """Update the summary label based on current toggle states."""
        approved_count = sum(1 for v in self._toggle_states.values() if v)
        rejected_count = sum(1 for v in self._toggle_states.values() if not v)
        total = len(self._toggle_states)

        # Calculate approved AAV
        approved_aav = sum(
            p.get("details", {}).get("proposed_contract", {}).get("aav", 0)
            for p in self._gm_proposals
            if self._toggle_states.get(p.get("proposal_id"), True)  # Default ON
        )

        self.extension_summary_label.setText(
            f"{total} extension(s) • {approved_count} approved • {rejected_count} rejected • "
            f"Approved AAV: ${approved_aav / 1_000_000:.1f}M"
        )

        # Update pending re-signs count (only approved ones)
        self.resign_count_label.setText(str(approved_count))

    # =========================================================================
    # Cap Relief Action Handlers
    # =========================================================================

    def _on_restructure_clicked(self):
        """Open restructure dialog showing restructurable contracts."""
        try:
            from game_cycle_ui.dialogs.restructure_dialog import RestructureDialog

            # Validate required context
            if not self._db_path or not self._dynasty_id:
                print("[ResigningView] Cannot open restructure dialog: context not set")
                return

            dialog = RestructureDialog(
                team_id=self._team_id,
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._season,
                parent=self
            )
            dialog.restructure_applied.connect(self._on_restructure_applied)
            dialog.exec()
        except ImportError as ie:
            print(f"[ResigningView] Restructure dialog not implemented: {ie}")
        except Exception as e:
            print(f"[ResigningView] Error opening restructure dialog: {e}")
            import traceback
            traceback.print_exc()

    def _on_early_cuts_clicked(self):
        """Open early cuts dialog for non-recommended players."""
        try:
            from game_cycle_ui.dialogs.early_cuts_dialog import EarlyCutsDialog

            # Validate required context
            if not self._db_path or not self._dynasty_id:
                print("[ResigningView] Cannot open early cuts dialog: context not set")
                return

            # Get player IDs from extension recommendations to exclude
            excluded_ids = {
                p.get("details", {}).get("player_id")
                for p in self._gm_proposals
                if p.get("details", {}).get("player_id")
            }

            dialog = EarlyCutsDialog(
                team_id=self._team_id,
                excluded_player_ids=excluded_ids,
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._season,
                cap_shortfall=self._over_cap_amount,
                parent=self
            )
            dialog.player_cut.connect(self._on_early_cut_applied)
            dialog.exec()
        except ImportError as ie:
            print(f"[ResigningView] Early cuts dialog not implemented: {ie}")
        except Exception as e:
            print(f"[ResigningView] Error opening early cuts dialog: {e}")
            import traceback
            traceback.print_exc()

    def _on_restructure_applied(self, contract_id: int, cap_savings: int):
        """Handle restructure completion."""
        print(f"[ResigningView] Restructure applied: contract_id={contract_id}, cap_savings=${cap_savings:,}")
        # Emit signal for controller
        self.restructure_completed.emit(contract_id, cap_savings)

    def _on_early_cut_applied(self, player_id: int, dead_money: int, cap_savings: int):
        """Handle early cut completion."""
        # Emit signal for controller
        self.early_cut_completed.emit(player_id, dead_money, cap_savings)
        self.player_released.emit(player_id)

    # =========================================================================
    # Hover Card for GM Reasoning
    # =========================================================================

    def _on_cell_entered(self, row: int, col: int):
        """Show hover card when entering GM Reasoning column (col 6)."""
        if col != 6:  # GM Reasoning column
            self._hover_card.schedule_hide(100)
            return

        item = self.extensions_table.item(row, col)
        if item and item.toolTip():
            # Get cell position
            cell_rect = self.extensions_table.visualItemRect(item)
            global_pos = self.extensions_table.viewport().mapToGlobal(
                cell_rect.bottomLeft()
            )
            self._hover_card.show_at(item.toolTip(), global_pos)

    def _on_table_leave(self, event):
        """Hide hover card when leaving table."""
        self._hover_card.schedule_hide(200)
        self._original_leave_event(event)
