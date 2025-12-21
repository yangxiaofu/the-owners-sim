"""
Franchise Tag View - Shows taggable players for user's team.

Allows the user to see which expiring contract players can be tagged
and decide whether to apply a franchise or transition tag.
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QComboBox, QProgressBar, QInputDialog, QSplitter,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.dialogs import ContractDetailsDialog
from game_cycle_ui.theme import (
    TABLE_HEADER_STYLE, Colors,
    SECONDARY_BUTTON_STYLE, PRIMARY_BUTTON_STYLE, DANGER_BUTTON_STYLE,
    Typography, FontSizes, TextColors, Spacing,
    apply_table_style, ESPN_CARD_BG
)
from game_cycle_ui.widgets import SummaryPanel, StatFrame
from constants.position_abbreviations import get_position_abbreviation
from utils.player_field_extractors import extract_overall_rating


class FranchiseTagView(QWidget):
    """
    View for the franchise tag stage.

    Shows a table of taggable players with tag cost estimates.
    Users can apply one franchise or transition tag per season.
    """

    # Signal emitted when user applies a tag (legacy direct selection)
    tag_applied = Signal(int, str)  # player_id, tag_type ("franchise" or "transition")

    # Signals for GM proposal workflow (Tollgate 5)
    proposal_approved = Signal(str)  # proposal_id
    proposal_rejected = Signal(str, str)  # proposal_id, notes

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._taggable_players: List[Dict] = []
        self._tag_used = False
        self._selected_player_id: Optional[int] = None
        self._current_season: int = 2025
        self._next_season: int = 2026
        self._projected_cap_before: int = 0  # Next year's cap before tag
        self._db_path: str = ""
        self._gm_proposal: Optional[Dict] = None  # Current GM proposal
        self._setup_ui()

    def set_db_path(self, db_path: str):
        """Set the database path for contract lookups."""
        self._db_path = db_path

    def _setup_ui(self):
        """Build the UI layout with two-panel split."""
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.MAJOR)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel at top (uses standard SummaryPanel widget)
        self._create_summary_panel(layout)

        # Main content area with splitter (60/40 split)
        self._create_content_splitter(layout)

    def _create_content_splitter(self, parent_layout: QVBoxLayout):
        """Create the main content area with left/right panel split."""
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left panel: Expiring Contracts table
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)

        # Right panel: GM Recommendation + Tag Controls (scrollable)
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)

        # Set initial sizes (60/40 ratio)
        splitter.setSizes([600, 400])

        parent_layout.addWidget(splitter, stretch=1)

    def _create_left_panel(self) -> QWidget:
        """Create the left panel containing the expiring contracts table."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(0)

        # Table wrapped in group box
        self._create_players_table(left_layout)

        return left_widget

    def _create_right_panel(self) -> QScrollArea:
        """Create the right panel with GM recommendation and tag controls."""
        # Scroll area for the right panel
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        # Container widget for scroll area
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 0, 0, 0)
        container_layout.setSpacing(Spacing.MAJOR)

        # GM Recommendation section (always visible)
        self._create_gm_proposal_section(container_layout)

        # Tag info section
        self._create_tag_info_section(container_layout)

        # Push everything up
        container_layout.addStretch()

        scroll_area.setWidget(container)
        return scroll_area

    def _create_tag_info_section(self, parent_layout: QVBoxLayout):
        """Create the tag information/instructions section."""
        info_group = QGroupBox("Tag Information")
        info_group.setStyleSheet(
            f"QGroupBox {{ background: {ESPN_CARD_BG}; border: 1px solid #333; "
            "border-radius: 6px; margin-top: 8px; padding: 12px; }}"
            f"QGroupBox::title {{ color: {Colors.MUTED}; }}"
        )
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(8)

        # Franchise tag info
        franchise_label = QLabel("• Franchise Tag: Higher cost, prevents player from negotiating with other teams")
        franchise_label.setWordWrap(True)
        franchise_label.setStyleSheet(f"color: {Colors.WARNING};")
        info_layout.addWidget(franchise_label)

        # Transition tag info
        transition_label = QLabel("• Transition Tag: Lower cost, team has right to match any offer")
        transition_label.setWordWrap(True)
        transition_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        info_layout.addWidget(transition_label)

        # Note
        note_label = QLabel("Note: Each team may use ONE tag per season. Tag salary counts against NEXT year's cap.")
        note_label.setWordWrap(True)
        note_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
        info_layout.addWidget(note_label)

        parent_layout.addWidget(info_group)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel using standard SummaryPanel widget."""
        self._summary_panel = SummaryPanel("Franchise Tag Summary")

        # Current Cap (reference only - gray)
        self._current_cap_stat = StatFrame(f"Current Cap ({self._current_season})", "$0", Colors.MUTED)
        self._summary_panel._layout.addWidget(self._current_cap_stat)

        # Next Year Cap (main focus - green/red based on value)
        self._projected_cap_stat = StatFrame(f"Next Year Cap ({self._next_season})", "$0", Colors.SUCCESS)
        self._summary_panel._layout.addWidget(self._projected_cap_stat)

        # Cap impact (shows after selection)
        self._cap_impact_stat = StatFrame("Cap Impact", "-", Colors.MUTED)
        self._cap_impact_stat.hide()  # Hidden until a player is selected
        self._summary_panel._layout.addWidget(self._cap_impact_stat)

        # Taggable Players count
        self._taggable_stat = StatFrame("Taggable Players", "0")
        self._summary_panel._layout.addWidget(self._taggable_stat)

        # Tag Status
        self._tag_status_stat = StatFrame("Tag Status", "Available", Colors.SUCCESS)
        self._summary_panel._layout.addWidget(self._tag_status_stat)

        self._summary_panel.add_stretch()

        parent_layout.addWidget(self._summary_panel)

        # Create label aliases for backward compatibility
        self.cap_space_label = self._current_cap_stat.value_label
        self.projected_cap_label = self._projected_cap_stat.value_label
        self.cap_impact_label = self._cap_impact_stat.value_label
        self.taggable_count_label = self._taggable_stat.value_label
        self.tag_status_label = self._tag_status_stat.value_label
        self.current_cap_title = self._current_cap_stat.title_label
        self.projected_cap_title = self._projected_cap_stat.title_label

    def _create_gm_proposal_section(self, parent_layout: QVBoxLayout):
        """Create the GM recommendation section (always visible, shows empty state when no proposal)."""
        self.gm_proposal_group = QGroupBox("GM RECOMMENDATION")
        self.gm_proposal_group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 2px solid #4a90d9; "
            "border-radius: 6px; margin-top: 8px; padding-top: 8px; background: #1a2a3a; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            f"padding: 0 8px; color: {Colors.INFO}; }}"
        )
        proposal_layout = QVBoxLayout(self.gm_proposal_group)
        proposal_layout.setSpacing(12)

        # Empty state container (shown when no proposal)
        self._empty_state_widget = QFrame()
        empty_layout = QVBoxLayout(self._empty_state_widget)
        empty_layout.setContentsMargins(20, 20, 20, 20)

        empty_label = QLabel("No recommendation available")
        empty_label.setFont(Typography.H5)
        empty_label.setStyleSheet(f"color: {Colors.MUTED};")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_label)

        empty_desc = QLabel("The GM has not made a franchise tag recommendation yet.")
        empty_desc.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
        empty_desc.setAlignment(Qt.AlignCenter)
        empty_desc.setWordWrap(True)
        empty_layout.addWidget(empty_desc)

        proposal_layout.addWidget(self._empty_state_widget)

        # Proposal content container (shown when proposal exists)
        self._proposal_content_widget = QFrame()
        self._proposal_content_layout = QVBoxLayout(self._proposal_content_widget)
        self._proposal_content_layout.setContentsMargins(0, 0, 0, 0)
        self._proposal_content_layout.setSpacing(12)

        # Player info row - add to content widget
        player_row = QHBoxLayout()

        # Player name and position
        player_info_frame = QFrame()
        player_info_layout = QVBoxLayout(player_info_frame)
        player_info_layout.setContentsMargins(0, 0, 0, 0)

        player_title = QLabel("Recommended Player")
        player_title.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")
        player_info_layout.addWidget(player_title)

        self.proposal_player_label = QLabel("None")
        self.proposal_player_label.setFont(Typography.H4)
        player_info_layout.addWidget(self.proposal_player_label)

        player_row.addWidget(player_info_frame)

        # Position
        pos_frame = QFrame()
        pos_layout = QVBoxLayout(pos_frame)
        pos_layout.setContentsMargins(0, 0, 0, 0)

        pos_title = QLabel("Position")
        pos_title.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")
        pos_layout.addWidget(pos_title)

        self.proposal_position_label = QLabel("-")
        self.proposal_position_label.setFont(Typography.H5)
        pos_layout.addWidget(self.proposal_position_label)

        player_row.addWidget(pos_frame)

        # Tag type
        tag_type_frame = QFrame()
        tag_type_layout = QVBoxLayout(tag_type_frame)
        tag_type_layout.setContentsMargins(0, 0, 0, 0)

        tag_type_title = QLabel("Tag Type")
        tag_type_title.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")
        tag_type_layout.addWidget(tag_type_title)

        self.proposal_tag_type_label = QLabel("-")
        self.proposal_tag_type_label.setFont(Typography.H5)
        self.proposal_tag_type_label.setStyleSheet(f"color: {Colors.INFO};")
        tag_type_layout.addWidget(self.proposal_tag_type_label)

        player_row.addWidget(tag_type_frame)

        # Tag amount
        amount_frame = QFrame()
        amount_layout = QVBoxLayout(amount_frame)
        amount_layout.setContentsMargins(0, 0, 0, 0)

        amount_title = QLabel("Tag Amount")
        amount_title.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")
        amount_layout.addWidget(amount_title)

        self.proposal_amount_label = QLabel("$0")
        self.proposal_amount_label.setFont(Typography.H5)
        self.proposal_amount_label.setStyleSheet(f"color: {Colors.WARNING};")
        amount_layout.addWidget(self.proposal_amount_label)

        player_row.addWidget(amount_frame)
        player_row.addStretch()

        self._proposal_content_layout.addLayout(player_row)

        # GM Reasoning
        reasoning_frame = QFrame()
        reasoning_frame.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border-radius: 4px; padding: 8px; }"
        )
        reasoning_layout = QVBoxLayout(reasoning_frame)

        reasoning_title = QLabel("GM Reasoning")
        reasoning_title.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")
        reasoning_layout.addWidget(reasoning_title)

        self.proposal_reasoning_label = QLabel("")
        self.proposal_reasoning_label.setWordWrap(True)
        self.proposal_reasoning_label.setFont(Typography.BODY)
        self.proposal_reasoning_label.setStyleSheet("font-style: italic;")
        reasoning_layout.addWidget(self.proposal_reasoning_label)

        self._proposal_content_layout.addWidget(reasoning_frame)

        # Confidence meter
        confidence_row = QHBoxLayout()

        confidence_title = QLabel("GM Confidence:")
        confidence_title.setFont(Typography.BODY_BOLD)
        confidence_row.addWidget(confidence_title)

        self.proposal_confidence_bar = QProgressBar()
        self.proposal_confidence_bar.setRange(0, 100)
        self.proposal_confidence_bar.setFixedHeight(18)
        self.proposal_confidence_bar.setTextVisible(True)
        self.proposal_confidence_bar.setFormat("%v%")
        confidence_row.addWidget(self.proposal_confidence_bar, 1)

        self._proposal_content_layout.addLayout(confidence_row)

        # Status and action buttons
        action_row = QHBoxLayout()

        self.proposal_status_label = QLabel("Awaiting Decision")
        self.proposal_status_label.setFont(Typography.BODY_BOLD)
        self.proposal_status_label.setStyleSheet(f"color: {Colors.WARNING};")
        action_row.addWidget(self.proposal_status_label)

        action_row.addStretch()

        self.proposal_approve_btn = QPushButton("Approve Tag")
        self.proposal_approve_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.proposal_approve_btn.setMinimumWidth(120)
        self.proposal_approve_btn.clicked.connect(self._on_proposal_approve)
        action_row.addWidget(self.proposal_approve_btn)

        self.proposal_reject_btn = QPushButton("Reject")
        self.proposal_reject_btn.setStyleSheet(DANGER_BUTTON_STYLE)
        self.proposal_reject_btn.setMinimumWidth(100)
        self.proposal_reject_btn.clicked.connect(self._on_proposal_reject)
        action_row.addWidget(self.proposal_reject_btn)

        self._proposal_content_layout.addLayout(action_row)

        # Add content widget to proposal layout (hidden by default)
        proposal_layout.addWidget(self._proposal_content_widget)
        self._proposal_content_widget.hide()  # Show empty state by default

        parent_layout.addWidget(self.gm_proposal_group)
        # Group box is always visible - empty state shows when no proposal

    def _create_players_table(self, parent_layout: QVBoxLayout):
        """Create the main table of taggable players."""
        table_group = QGroupBox("Expiring Contract Players")
        table_layout = QVBoxLayout(table_group)

        self.players_table = QTableWidget()
        self.players_table.setColumnCount(9)
        self.players_table.setHorizontalHeaderLabels([
            "Player", "Position", "Tag Group", "Age", "OVR",
            "Current Cap Hit", "Franchise Tag", "Transition Tag", ""
        ])

        # Apply centralized table styling
        apply_table_style(self.players_table)

        # Set taller row height to accommodate buttons
        self.players_table.verticalHeader().setDefaultSectionSize(40)

        # Configure column resize modes
        header = self.players_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.Fixed)
        header.resizeSection(8, 80)  # View button column - wider for button

        # Connect selection change
        self.players_table.itemSelectionChanged.connect(self._on_selection_changed)

        table_layout.addWidget(self.players_table)
        parent_layout.addWidget(table_group, stretch=1)

    def _create_tag_controls(self, parent_layout: QVBoxLayout):
        """Create tag application controls."""
        controls_group = QGroupBox("Apply Tag")
        controls_layout = QHBoxLayout(controls_group)
        controls_layout.setSpacing(16)

        # Selected player display
        selected_frame = QFrame()
        selected_layout = QVBoxLayout(selected_frame)
        selected_layout.setContentsMargins(0, 0, 0, 0)

        selected_title = QLabel("Selected Player")
        selected_title.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")
        selected_layout.addWidget(selected_title)

        self.selected_player_label = QLabel("None")
        self.selected_player_label.setFont(Typography.H5)
        selected_layout.addWidget(self.selected_player_label)

        controls_layout.addWidget(selected_frame)

        # Tag type dropdown
        tag_type_frame = QFrame()
        tag_type_layout = QVBoxLayout(tag_type_frame)
        tag_type_layout.setContentsMargins(0, 0, 0, 0)

        tag_type_title = QLabel("Tag Type")
        tag_type_title.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")
        tag_type_layout.addWidget(tag_type_title)

        self.tag_type_combo = QComboBox()
        self.tag_type_combo.addItems(["Franchise Tag", "Transition Tag"])
        self.tag_type_combo.setMinimumWidth(150)
        tag_type_layout.addWidget(self.tag_type_combo)

        controls_layout.addWidget(tag_type_frame)

        # Tag cost display
        cost_frame = QFrame()
        cost_layout = QVBoxLayout(cost_frame)
        cost_layout.setContentsMargins(0, 0, 0, 0)

        cost_title = QLabel("Tag Cost")
        cost_title.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")
        cost_layout.addWidget(cost_title)

        self.tag_cost_label = QLabel("$0")
        self.tag_cost_label.setFont(Typography.H5)
        self.tag_cost_label.setStyleSheet(f"color: {Colors.WARNING};")  # Orange
        cost_layout.addWidget(self.tag_cost_label)

        controls_layout.addWidget(cost_frame)

        controls_layout.addStretch()

        # Apply button
        self.apply_tag_btn = QPushButton("Apply Tag")
        self.apply_tag_btn.setEnabled(False)
        self.apply_tag_btn.setMinimumWidth(120)
        self.apply_tag_btn.setMinimumHeight(40)
        self.apply_tag_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.apply_tag_btn.clicked.connect(self._on_apply_tag_clicked)
        controls_layout.addWidget(self.apply_tag_btn)

        # Connect combo box change
        self.tag_type_combo.currentIndexChanged.connect(self._on_tag_type_changed)

        parent_layout.addWidget(controls_group)

    def set_taggable_players(self, players: List[Dict]):
        """
        Populate the table with taggable players.

        Args:
            players: List of player dictionaries with:
                - player_id: int
                - name: str
                - position: str
                - tag_category: str (QB, RB, WR, etc.)
                - age: int
                - overall: int
                - current_cap_hit: int
                - franchise_tag_cost: int
                - transition_tag_cost: int
        """
        self._taggable_players = players
        self.taggable_count_label.setText(str(len(players)))
        self.players_table.setRowCount(len(players))

        for row, player in enumerate(players):
            self._populate_row(row, player)

    def set_tag_used(self, tag_used: bool):
        """Update the tag status display."""
        self._tag_used = tag_used
        if tag_used:
            self.tag_status_label.setText("Used")
            self.tag_status_label.setStyleSheet(f"color: {Colors.ERROR};")  # Red
            self.apply_tag_btn.setEnabled(False)
            self.apply_tag_btn.setText("Tag Already Used")
        else:
            self.tag_status_label.setText("Available")
            self.tag_status_label.setStyleSheet(f"color: {Colors.SUCCESS};")  # Green

    def set_cap_space(self, cap_space: int):
        """Update the current season cap space display."""
        formatted = f"${cap_space:,}"
        self.cap_space_label.setText(formatted)

        # Gray for current season - it's reference only
        self.cap_space_label.setStyleSheet(f"color: {Colors.MUTED};")

    def set_projected_cap_space(self, cap_space: int):
        """Update the projected next year cap space display."""
        self._projected_cap_before = cap_space
        formatted = f"${cap_space:,}"
        self.projected_cap_label.setText(formatted)

        # Color based on cap space (red if negative, green if positive)
        if cap_space < 0:
            self.projected_cap_label.setStyleSheet(f"color: {Colors.ERROR};")  # Red
        else:
            self.projected_cap_label.setStyleSheet(f"color: {Colors.SUCCESS};")  # Green

    def set_season_info(self, current_season: int, next_season: int):
        """Update the season labels."""
        self._current_season = current_season
        self._next_season = next_season
        self.current_cap_title.setText(f"Current Cap ({current_season})")
        self.projected_cap_title.setText(f"Next Year Cap ({next_season})")

    def set_cap_data(self, cap_data: Dict):
        """Update the view with full cap data (current season)."""
        available = cap_data.get("available_space", 0)
        self.set_cap_space(available)

    def set_projected_cap_data(self, projected_cap_data: Dict):
        """Update the view with projected next year cap data."""
        available = projected_cap_data.get("available_space", 0)
        self.set_projected_cap_space(available)

    def _populate_row(self, row: int, player: Dict):
        """Populate a single row in the table."""
        player_id = player.get("player_id", 0)

        # Player name
        name_item = QTableWidgetItem(player.get("name", "Unknown"))
        name_item.setData(Qt.UserRole, player_id)
        name_item.setData(Qt.UserRole + 1, player.get("franchise_tag_cost", 0))
        name_item.setData(Qt.UserRole + 2, player.get("transition_tag_cost", 0))
        self.players_table.setItem(row, 0, name_item)

        # Position
        position = player.get("position", "")
        pos_item = QTableWidgetItem(get_position_abbreviation(position))
        pos_item.setTextAlignment(Qt.AlignCenter)
        self.players_table.setItem(row, 1, pos_item)

        # Tag category
        category_item = QTableWidgetItem(player.get("tag_category", ""))
        category_item.setTextAlignment(Qt.AlignCenter)
        category_item.setForeground(QColor(Colors.INFO))  # Blue
        self.players_table.setItem(row, 2, category_item)

        # Age
        age = player.get("age", 0)
        age_item = QTableWidgetItem(str(age))
        age_item.setTextAlignment(Qt.AlignCenter)
        # Color code age (red if 30+)
        if age >= 30:
            age_item.setForeground(QColor(Colors.ERROR))  # Red
        self.players_table.setItem(row, 3, age_item)

        # Overall rating
        overall = extract_overall_rating(player, default=0)
        ovr_item = QTableWidgetItem(str(overall))
        ovr_item.setTextAlignment(Qt.AlignCenter)
        # Color code rating
        if overall >= 85:
            ovr_item.setForeground(QColor(Colors.SUCCESS))  # Green - Elite
        elif overall >= 75:
            ovr_item.setForeground(QColor(Colors.INFO))  # Blue - Solid
        self.players_table.setItem(row, 4, ovr_item)

        # Current cap hit
        current_cap = player.get("current_cap_hit", 0)
        current_text = f"${current_cap:,}" if current_cap else "N/A"
        current_item = QTableWidgetItem(current_text)
        current_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.players_table.setItem(row, 5, current_item)

        # Franchise tag cost
        franchise_cost = player.get("franchise_tag_cost", 0)
        franchise_text = f"${franchise_cost:,}" if franchise_cost else "N/A"
        franchise_item = QTableWidgetItem(franchise_text)
        franchise_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        franchise_item.setForeground(QColor(Colors.WARNING))  # Orange
        self.players_table.setItem(row, 6, franchise_item)

        # Transition tag cost
        transition_cost = player.get("transition_tag_cost", 0)
        transition_text = f"${transition_cost:,}" if transition_cost else "N/A"
        transition_item = QTableWidgetItem(transition_text)
        transition_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        transition_item.setForeground(QColor(Colors.SUCCESS))  # Light green
        self.players_table.setItem(row, 7, transition_item)

        # View contract button (if contract exists)
        contract_id = player.get("contract_id")
        player_name = player.get("name", "Unknown")
        if contract_id:
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(0)

            view_btn = QPushButton("View")
            view_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
            view_btn.clicked.connect(
                lambda checked, cid=contract_id, pname=player_name: self._on_view_contract(cid, pname)
            )
            action_layout.addWidget(view_btn)
            self.players_table.setCellWidget(row, 8, action_widget)

    def _on_view_contract(self, contract_id: int, player_name: str):
        """Handle view contract button click - opens contract details dialog."""
        if not self._db_path:
            return

        dialog = ContractDetailsDialog(
            player_name=player_name,
            contract_id=contract_id,
            db_path=self._db_path,
            parent=self
        )
        dialog.exec()

    def _on_selection_changed(self):
        """Handle player selection change."""
        selected = self.players_table.selectedItems()
        if not selected or self._tag_used:
            self._selected_player_id = None
            return

        # Get selected row
        row = selected[0].row()
        name_item = self.players_table.item(row, 0)

        if name_item:
            self._selected_player_id = name_item.data(Qt.UserRole)

    def _on_tag_type_changed(self, index: int):
        """Handle tag type dropdown change."""
        selected = self.players_table.selectedItems()
        if selected:
            row = selected[0].row()
            name_item = self.players_table.item(row, 0)
            if name_item:
                self._update_tag_cost_display(name_item)

    def _update_tag_cost_display(self, name_item: QTableWidgetItem):
        """Update the tag cost display and cap impact based on selection and tag type."""
        tag_type_index = self.tag_type_combo.currentIndex()

        if tag_type_index == 0:  # Franchise Tag
            cost = name_item.data(Qt.UserRole + 1)
        else:  # Transition Tag
            cost = name_item.data(Qt.UserRole + 2)

        self.tag_cost_label.setText(f"${cost:,}" if cost else "N/A")

        # Update cap impact display and button state
        if cost and self._projected_cap_before > 0:
            projected_after = self._projected_cap_before - cost
            can_afford = projected_after >= 0

            # Show the cap impact stat
            self._cap_impact_stat.show()

            if can_afford:
                self._cap_impact_stat.set_value(f"${projected_after:,}", Colors.SUCCESS)
                self.apply_tag_btn.setEnabled(True)  # Enable button - can afford
            else:
                self._cap_impact_stat.set_value(f"${projected_after:,} (OVER)", Colors.ERROR)
                self.apply_tag_btn.setEnabled(False)  # DISABLE button - over cap
        else:
            self._cap_impact_stat.hide()
            # If no projected cap data yet, allow the button (backend will validate)
            self.apply_tag_btn.setEnabled(True)

    def _on_apply_tag_clicked(self):
        """Handle apply tag button click."""
        if self._selected_player_id is None or self._tag_used:
            return

        tag_type = "franchise" if self.tag_type_combo.currentIndex() == 0 else "transition"
        self.tag_applied.emit(self._selected_player_id, tag_type)
        # Note: Controller will call set_tag_used(True) after successful application

    def show_no_taggable_message(self):
        """Show a message when there are no taggable players."""
        self.players_table.setRowCount(1)
        self.players_table.setSpan(0, 0, 1, 9)

        message_item = QTableWidgetItem("No expiring contracts for your team")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor(Colors.MUTED))
        font = Typography.BODY
        font.setItalic(True)
        message_item.setFont(font)

        self.players_table.setItem(0, 0, message_item)
        self.taggable_count_label.setText("0")

    # =========================================================================
    # GM Proposal Methods (Tollgate 5)
    # =========================================================================

    def set_gm_proposal(self, proposal: Optional[Dict]):
        """
        Display GM's tag recommendation.

        Args:
            proposal: GM proposal dict with keys:
                - proposal_id: str
                - details: {player_name, position, tag_type, tag_amount, cap_impact}
                - gm_reasoning: str
                - confidence: float (0.0-1.0)
                - auto_approved: bool (True if Trust GM mode)
        """
        self._gm_proposal = proposal

        if not proposal:
            # Show empty state, hide content
            self._empty_state_widget.show()
            self._proposal_content_widget.hide()
            return

        # Show content, hide empty state
        self._empty_state_widget.hide()
        self._proposal_content_widget.show()

        # Extract details
        details = proposal.get("details", {})
        player_name = details.get("player_name", "Unknown")
        position = details.get("position", "-")
        tag_type = details.get("tag_type", "non_exclusive")
        tag_amount = details.get("tag_amount", 0)

        # Update labels
        self.proposal_player_label.setText(player_name)
        self.proposal_position_label.setText(get_position_abbreviation(position))
        self.proposal_tag_type_label.setText(tag_type.replace("_", " ").title())
        self.proposal_amount_label.setText(f"${tag_amount:,}")

        # GM reasoning
        reasoning = proposal.get("gm_reasoning", "")
        self.proposal_reasoning_label.setText(f'"{reasoning}"')

        # Confidence meter
        confidence = proposal.get("confidence", 0.5)
        confidence_pct = int(confidence * 100)
        self.proposal_confidence_bar.setValue(confidence_pct)
        self._update_proposal_confidence_color(confidence_pct)

        # Handle auto-approved (Trust GM mode)
        auto_approved = proposal.get("auto_approved", False)
        if auto_approved:
            self.proposal_status_label.setText("AUTO-APPROVED (Trust GM)")
            self.proposal_status_label.setStyleSheet(f"color: {Colors.SUCCESS};")
            self.proposal_approve_btn.setEnabled(False)
            self.proposal_approve_btn.setText("Approved")
            self.proposal_reject_btn.setEnabled(False)
        else:
            self.proposal_status_label.setText("Awaiting Your Decision")
            self.proposal_status_label.setStyleSheet(f"color: {Colors.WARNING};")
            self.proposal_approve_btn.setEnabled(True)
            self.proposal_approve_btn.setText("Approve Tag")
            self.proposal_reject_btn.setEnabled(True)

    def _update_proposal_confidence_color(self, confidence: int):
        """Set confidence bar color based on level."""
        if confidence >= 70:
            color = Colors.SUCCESS
        elif confidence >= 40:
            color = Colors.INFO
        else:
            color = Colors.MUTED

        self.proposal_confidence_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background-color: {color}; }}"
            f"QProgressBar {{ border: 1px solid #444; border-radius: 3px; }}"
        )

    def _on_proposal_approve(self):
        """Handle approve button click."""
        if not self._gm_proposal:
            return

        proposal_id = self._gm_proposal.get("proposal_id")
        if proposal_id:
            self.proposal_approved.emit(proposal_id)

            # Update UI to show approved state
            self.proposal_status_label.setText("APPROVED")
            self.proposal_status_label.setStyleSheet(f"color: {Colors.SUCCESS};")
            self.proposal_approve_btn.setEnabled(False)
            self.proposal_approve_btn.setText("Approved")
            self.proposal_reject_btn.setEnabled(False)

    def _on_proposal_reject(self):
        """Handle reject button click - prompts for notes."""
        if not self._gm_proposal:
            return

        proposal_id = self._gm_proposal.get("proposal_id")
        if not proposal_id:
            return

        # Prompt for rejection notes
        notes, ok = QInputDialog.getMultiLineText(
            self,
            "Rejection Notes",
            "Why are you rejecting this tag proposal? (optional)\n\n"
            "This helps the GM understand your preferences.",
            "",
        )

        if ok:  # User didn't cancel
            self.proposal_rejected.emit(proposal_id, notes if notes.strip() else "")

            # Update UI to show rejected state
            self.proposal_status_label.setText("REJECTED")
            self.proposal_status_label.setStyleSheet(f"color: {Colors.ERROR};")
            self.proposal_approve_btn.setEnabled(False)
            self.proposal_reject_btn.setEnabled(False)
            self.proposal_reject_btn.setText("Rejected")