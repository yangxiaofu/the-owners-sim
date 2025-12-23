"""
Roster Cuts View - Shows roster for cutting down to 53-man limit.

Allows the user to cut players from their roster, with AI suggestions
highlighting low-value players while respecting position minimums.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QComboBox, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QBrush

from game_cycle_ui.dialogs import ContractDetailsDialog
from game_cycle_ui.theme import (
    TABLE_HEADER_STYLE, Colors,
    PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, DANGER_BUTTON_STYLE,
    WARNING_BUTTON_STYLE, NEUTRAL_BUTTON_STYLE,
    Typography, FontSizes, TextColors,
    apply_table_style
)
from game_cycle_ui.widgets import SummaryPanel
from game_cycle_ui.utils.table_utils import NumericTableWidgetItem, TableCellHelper
from constants.position_abbreviations import get_position_abbreviation


def _load_position_filter_mapping() -> Dict[str, List[str]]:
    """Load position filter mapping from config file."""
    config_path = Path(__file__).parents[2] / "src" / "config" / "positions" / "position_filter_mapping.json"
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("mappings", {})


# Load position mapping from external config for easy manual updates
POSITION_FILTER_MAP = _load_position_filter_mapping()

# Table-specific button styles - larger, more legible for table cells
TABLE_VIEW_BTN_STYLE = """
    QPushButton {
        background-color: #1976D2;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 13px;
        font-weight: bold;
        min-width: 50px;
    }
    QPushButton:hover { background-color: #1565C0; }
    QPushButton:pressed { background-color: #0D47A1; }
"""

TABLE_CUT_BTN_STYLE = """
    QPushButton {
        background-color: #D32F2F;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 13px;
        font-weight: bold;
        min-width: 50px;
    }
    QPushButton:hover { background-color: #C62828; }
    QPushButton:pressed { background-color: #B71C1C; }
"""

TABLE_JUNE1_BTN_STYLE = """
    QPushButton {
        background-color: #F57C00;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 13px;
        font-weight: bold;
        min-width: 60px;
    }
    QPushButton:hover { background-color: #E65100; }
    QPushButton:pressed { background-color: #BF360C; }
"""

TABLE_DISABLED_BTN_STYLE = """
    QPushButton {
        background-color: #616161;
        color: #BDBDBD;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 13px;
        min-width: 70px;
    }
"""


class RosterCutsView(QWidget):
    """
    View for the roster cuts stage.

    Shows a table of all roster players with cut buttons.
    AI suggestions are highlighted for easy identification.
    Users can filter by position and minimum overall rating.
    """

    # Signals
    player_cut = Signal(int, bool)  # player_id, use_june_1
    get_suggestions_requested = Signal()
    process_cuts_requested = Signal()
    view_contract_requested = Signal(int, str)  # contract_id, player_name
    cap_validation_changed = Signal(bool, int)  # (is_compliant, over_cap_amount)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._roster_players: List[Dict] = []
        self._filtered_players: List[Dict] = []
        self._cut_players: Dict[int, bool] = {}  # Manual cuts: player_id -> use_june_1
        self._approved_gm_cuts: Set[int] = set()  # GM proposal player IDs
        self._approved_coach_cuts: Set[int] = set()  # Coach proposal player IDs
        self._suggested_cuts: Set[int] = set()
        self._protected_players: Set[int] = set()
        self._db_path: str = ""
        self._dynasty_id: Optional[str] = None
        self._season: int = 2025
        self._team_name: str = ""
        self._cap_space: int = 0  # Current cap space (negative = over cap)
        self._target_roster_size: int = 53  # Dynamic target size (53 for final cuts)
        self._cut_phase: str = "FINAL"  # Cut phase identifier (e.g., "FINAL", "PRESEASON")
        self._cuts_needed: int = 0  # Number of cuts still needed to reach target
        self._coach_proposals: List[Dict] = []  # Coach cut recommendations
        self._setup_ui()

    def set_db_path(self, db_path: str):
        """Set the database path for contract lookups."""
        self._db_path = db_path

    def set_context(self, dynasty_id: str, db_path: str, season: int, team_name: str = ""):
        """Set context for player detail dialogs.

        Args:
            dynasty_id: Current dynasty ID
            db_path: Path to the database
            season: Current season year
            team_name: Name of the user's team (optional)
        """
        self._dynasty_id = dynasty_id
        self._db_path = db_path
        self._season = season
        self._team_name = team_name

    def _setup_ui(self):
        """Build the UI layout with two-section Coach-first design."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Section 1: Summary panel at top
        self._create_summary_panel(layout)

        # Section 2: Head Coach Recommendations (primary focus)
        self._create_coach_recommendations_section(layout)

        # Section 3: Collapsible Full Roster (secondary)
        self._create_collapsible_roster_section(layout)

        # Section 4: Action instructions
        self._create_instructions(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing roster and cut info using SummaryPanel."""
        summary_panel = SummaryPanel("Roster Cuts Summary")

        # Current roster size (no initial color - will be set dynamically)
        self.roster_size_label = summary_panel.add_stat("Current Roster", "0 / 53")

        # Cuts needed (red)
        self.cuts_needed_label = summary_panel.add_stat("Cuts Needed", "0", Colors.ERROR)

        # Players marked for cut (orange/warning)
        self.marked_cut_label = summary_panel.add_stat("Marked for Cut", "0", Colors.WARNING)

        # Total dead money (red)
        self.dead_money_label = summary_panel.add_stat("Total Dead Money", "$0", Colors.ERROR)

        # Cap savings (green)
        self.cap_savings_label = summary_panel.add_stat("Cap Savings", "$0", Colors.SUCCESS)

        summary_panel.add_stretch()
        parent_layout.addWidget(summary_panel)

    def _create_coach_recommendations_section(self, parent_layout: QVBoxLayout):
        """Create the Head Coach recommendations section (primary focus)."""
        # Group box with prominent styling
        self.coach_group = QGroupBox("HEAD COACH RECOMMENDATIONS")
        self.coach_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 14px;
                color: {Colors.WARNING};
                border: 2px solid {Colors.WARNING};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }}
        """)

        coach_layout = QVBoxLayout(self.coach_group)
        coach_layout.setSpacing(8)

        # Header row with Select All checkbox
        header_layout = QHBoxLayout()

        self.select_all_coach = QCheckBox("Select All Coach Recommendations")
        self.select_all_coach.setStyleSheet(f"color: {Colors.TEXT_INVERSE}; font-weight: bold;")
        self.select_all_coach.stateChanged.connect(self._on_select_all_coach)
        header_layout.addWidget(self.select_all_coach)

        header_layout.addStretch()

        # Count label
        self.coach_count_label = QLabel("0 recommendations")
        self.coach_count_label.setStyleSheet(f"color: {Colors.MUTED};")
        header_layout.addWidget(self.coach_count_label)

        coach_layout.addLayout(header_layout)

        # Container for coach recommendation items (will be populated dynamically)
        self.coach_items_container = QWidget()
        self.coach_items_layout = QVBoxLayout(self.coach_items_container)
        self.coach_items_layout.setSpacing(4)
        self.coach_items_layout.setContentsMargins(0, 0, 0, 0)
        coach_layout.addWidget(self.coach_items_container)

        # "No recommendations" placeholder
        self.no_recommendations_label = QLabel(
            "No cut recommendations from Head Coach.\n"
            "Your roster composition looks good!"
        )
        self.no_recommendations_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic; padding: 20px;")
        self.no_recommendations_label.setAlignment(Qt.AlignCenter)
        coach_layout.addWidget(self.no_recommendations_label)

        parent_layout.addWidget(self.coach_group)

        # Initialize checkbox tracking
        self._coach_checkboxes: List[QCheckBox] = []

    def _create_coach_recommendation_item(self, proposal: Dict) -> QWidget:
        """Create a single coach recommendation row widget."""
        widget = QFrame()
        widget.setMinimumHeight(45)  # Minimum height, can grow if needed
        widget.setStyleSheet(f"""
            QFrame {{
                background: {Colors.BG_SECONDARY};
                border-radius: 6px;
                padding: 8px 12px;
                margin: 2px 0;
            }}
            QFrame:hover {{
                background: {Colors.BG_HOVER};
            }}
        """)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # Get details dict (player data is nested inside details)
        details = proposal.get("details", {})

        # Checkbox for approval
        checkbox = QCheckBox()
        checkbox.setChecked(True)  # Default: approved
        checkbox.setProperty("player_id", details.get("player_id", proposal.get("subject_player_id")))
        checkbox.stateChanged.connect(self._on_coach_item_toggled)
        layout.addWidget(checkbox)

        # Player info: "DE Shelby Harris (79 OVR)"
        pos = get_position_abbreviation(details.get("position", ""))
        name = details.get("player_name", "Unknown")
        ovr = details.get("overall_rating", 0)
        info_text = f"{pos}  {name}  ({ovr} OVR)" if pos else f"{name}  ({ovr} OVR)"
        info_label = QLabel(info_text)
        info_label.setMinimumWidth(200)  # Ensure enough space for text
        info_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: bold; font-size: 14px;")
        layout.addWidget(info_label)

        # Reason badge extracted from gm_reasoning
        reason = self._extract_reason_badge(proposal.get("gm_reasoning", ""))
        if reason:
            badge = QLabel(reason)
            badge_color = self._get_reason_badge_color(reason)
            badge.setStyleSheet(f"""
                background: {badge_color};
                color: {Colors.BG_PRIMARY};
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            """)
            layout.addWidget(badge)

        layout.addStretch()

        # Cap savings (from details dict)
        savings = details.get("cap_savings", 0)
        if savings > 0:
            savings_label = QLabel(f"Save ${savings/1_000_000:.1f}M")
            savings_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: bold;")
            layout.addWidget(savings_label)

        # Dead money (if any, from details dict)
        dead_money = details.get("dead_money", 0)
        if dead_money > 0:
            dead_label = QLabel(f"Dead: ${dead_money/1_000_000:.1f}M")
            dead_label.setStyleSheet(f"color: {Colors.ERROR};")
            layout.addWidget(dead_label)

        # View button
        view_btn = QPushButton("View")
        view_btn.setStyleSheet(TABLE_VIEW_BTN_STYLE)
        view_btn.setFixedWidth(60)
        player_id = details.get("player_id", proposal.get("subject_player_id"))
        view_btn.clicked.connect(lambda checked, pid=player_id: self._on_view_player_detail(pid))
        layout.addWidget(view_btn)

        return widget

    def _extract_reason_badge(self, gm_reasoning: str) -> str:
        """Extract the reason badge from GM reasoning text."""
        if not gm_reasoning:
            return ""
        first_line = gm_reasoning.split("\n")[0]
        if ":" in first_line:
            reason = first_line.split(":")[0].strip()
            # Clean up common prefixes
            for prefix in ["PRESEASON WEEK 1 CUT", "PRESEASON WEEK 2 CUT", "PRESEASON WEEK 3 CUT"]:
                if reason.startswith(prefix):
                    reason = reason.replace(prefix, "").strip()
                    if reason.startswith(":"):
                        reason = reason[1:].strip()
            return reason.upper() if reason else ""
        return ""

    def _get_reason_badge_color(self, reason: str) -> str:
        """Get color for reason badge based on type."""
        reason_upper = reason.upper()
        if "PERFORMANCE" in reason_upper:
            return Colors.ERROR  # Red for performance issues
        elif "AGE" in reason_upper:
            return Colors.WARNING  # Orange for age concerns
        elif "DEPTH" in reason_upper:
            return "#1976D2"  # Blue for depth
        elif "ROTATION" in reason_upper:
            return Colors.MUTED  # Gray for rotation players
        else:
            return Colors.WARNING  # Default orange

    def _populate_coach_recommendations(self):
        """Populate the coach recommendations list."""
        # Clear existing items
        while self.coach_items_layout.count():
            item = self.coach_items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._coach_checkboxes.clear()

        if not self._coach_proposals:
            # Show different message depending on whether cuts are needed
            if self._cuts_needed > 0:
                self.no_recommendations_label.setText(
                    "No coach recommendations generated.\n"
                    "Use 'Browse Full Roster' below to manually select players to cut."
                )
            else:
                self.no_recommendations_label.setText(
                    "No cut recommendations from Head Coach.\n"
                    "Your roster composition looks good!"
                )
            self.no_recommendations_label.setVisible(True)
            self.select_all_coach.setVisible(False)
            self.coach_count_label.setText("0 recommendations")
            return

        self.no_recommendations_label.setVisible(False)
        self.select_all_coach.setVisible(True)
        self.select_all_coach.setChecked(True)
        self.coach_count_label.setText(f"{len(self._coach_proposals)} recommendations")

        # Add each coach recommendation
        for proposal in self._coach_proposals:
            item = self._create_coach_recommendation_item(proposal)
            self.coach_items_layout.addWidget(item)

            # Store checkbox reference
            checkbox = item.findChild(QCheckBox)
            if checkbox:
                self._coach_checkboxes.append(checkbox)

    def _on_select_all_coach(self, state: int):
        """Handle Select All checkbox change."""
        is_checked = state == Qt.Checked
        for checkbox in self._coach_checkboxes:
            checkbox.setChecked(is_checked)
        self._update_approved_coach_cuts()
        self._update_totals()

    def _on_coach_item_toggled(self, state: int):
        """Handle individual coach recommendation toggle."""
        # Update select all checkbox state
        all_checked = all(cb.isChecked() for cb in self._coach_checkboxes)
        none_checked = not any(cb.isChecked() for cb in self._coach_checkboxes)

        self.select_all_coach.blockSignals(True)
        if all_checked:
            self.select_all_coach.setCheckState(Qt.Checked)
        elif none_checked:
            self.select_all_coach.setCheckState(Qt.Unchecked)
        else:
            self.select_all_coach.setCheckState(Qt.PartiallyChecked)
        self.select_all_coach.blockSignals(False)

        self._update_approved_coach_cuts()
        self._update_totals()

    def _update_approved_coach_cuts(self):
        """Update the set of approved coach cuts based on checkboxes."""
        self._approved_coach_cuts.clear()
        for checkbox in self._coach_checkboxes:
            if checkbox.isChecked():
                player_id = checkbox.property("player_id")
                if player_id:
                    self._approved_coach_cuts.add(int(player_id))

    def _on_view_player_detail(self, player_id: int):
        """Open player detail view."""
        # Find the player in roster
        for player in self._roster_players:
            if player.get("player_id") == player_id:
                self._show_player_details_dialog(player)
                return

    def _create_collapsible_roster_section(self, parent_layout: QVBoxLayout):
        """Create the collapsible full roster section."""
        # Toggle button to expand/collapse
        self.roster_toggle = QPushButton("▶ Browse Full Roster (0 players)")
        self.roster_toggle.setCheckable(True)
        self.roster_toggle.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 12px 16px;
                background: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                color: {Colors.MUTED};
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {Colors.BG_HOVER};
            }}
            QPushButton:checked {{
                color: {Colors.TEXT_INVERSE};
                background: {Colors.BG_HOVER};
            }}
        """)
        self.roster_toggle.toggled.connect(self._on_roster_toggle)
        parent_layout.addWidget(self.roster_toggle)

        # Container for roster content (hidden by default)
        self.roster_container = QWidget()
        self.roster_container.setVisible(False)
        roster_layout = QVBoxLayout(self.roster_container)
        roster_layout.setContentsMargins(0, 8, 0, 0)

        # Filter panel inside roster section
        self._create_filter_panel(roster_layout)

        # Players table
        self._create_players_table(roster_layout)

        parent_layout.addWidget(self.roster_container, stretch=1)

    def _on_roster_toggle(self, checked: bool):
        """Handle roster section expand/collapse."""
        self.roster_container.setVisible(checked)
        count = len(self._roster_players)
        if checked:
            self.roster_toggle.setText(f"▼ Browse Full Roster ({count} players)")
        else:
            self.roster_toggle.setText(f"▶ Browse Full Roster ({count} players)")

    def _create_filter_panel(self, parent_layout: QVBoxLayout):
        """Create filter controls and AI suggestion button."""
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

        # Show suggestions only checkbox (kept for legacy suggestions compatibility)
        self.show_suggestions_check = QCheckBox("Show Suggested Cuts Only")
        self.show_suggestions_check.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.show_suggestions_check)

        filter_layout.addStretch()

        parent_layout.addWidget(filter_frame)

    def _create_players_table(self, parent_layout: QVBoxLayout):
        """Create the main table of roster players."""
        table_group = QGroupBox("Current Roster")
        table_layout = QVBoxLayout(table_group)

        self.players_table = QTableWidget()
        self.players_table.setColumnCount(12)
        self.players_table.setHorizontalHeaderLabels([
            "Player", "Position", "Age", "OVR", "Potential", "Dev", "Salary", "Value",
            "Dead $", "Savings", "Status", "Action"
        ])

        # Apply standard ESPN dark table styling
        apply_table_style(self.players_table)

        # Enable numeric sorting
        self.players_table.setSortingEnabled(True)

        # Set taller row height to accommodate buttons
        self.players_table.verticalHeader().setDefaultSectionSize(44)

        # Configure column resize modes
        header = self.players_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Position
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Age
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # OVR
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Potential
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # Dev
        header.resizeSection(5, 50)  # Dev column width (narrow for badge)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Salary
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Value
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Dead $
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Savings
        header.setSectionResizeMode(10, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(11, QHeaderView.Fixed)  # Action
        header.resizeSection(11, 200)  # Action column width (wider for View + Cut + June 1)

        # Connect double-click to open player details
        self.players_table.cellDoubleClicked.connect(self._on_player_double_clicked)

        table_layout.addWidget(self.players_table)
        parent_layout.addWidget(table_group, stretch=1)

    def _create_instructions(self, parent_layout: QVBoxLayout):
        """Create instruction text at the bottom."""
        instructions = QLabel(
            "Review Head Coach recommendations above and select players to cut. "
            "Expand 'Browse Full Roster' to manually select additional cuts. "
            "Protected players (last at their position) cannot be cut. "
            "Click 'Process Cuts' when done to release marked players to the waiver wire."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic; padding: 8px;")
        parent_layout.addWidget(instructions)

    def set_roster_data(self, data: Dict, target_size: int = 53, cut_phase: str = "FINAL"):
        """
        Populate the view with roster cut data.

        Args:
            data: Dictionary containing:
                - roster: List of player dicts with value_score, dead_money, cap_savings
                - current_size: int
                - target_size: int (optional, can override with parameter)
                - cut_phase: str (optional, can override with parameter)
                - cuts_needed: int
                - ai_suggestions: List of player_ids suggested for cuts
                - protected_players: List of player_ids that cannot be cut
                - approved_gm_cuts: List of player_ids from approved GM proposals (NEW)
                - approved_coach_cuts: List of player_ids from approved Coach proposals (NEW)
        """
        self._roster_players = data.get("roster", [])
        self._suggested_cuts = set(data.get("ai_suggestions", []))
        self._protected_players = set(data.get("protected_players", []))
        self._approved_gm_cuts = set(data.get("approved_gm_cuts", []))  # NEW
        self._approved_coach_cuts = set(data.get("approved_coach_cuts", []))  # NEW
        self._cut_players = {}  # Reset manual cut tracking dict

        # Store target size and phase (priority: parameter > data dict > default)
        self._target_roster_size = data.get("target_size", target_size)
        self._cut_phase = data.get("cut_phase", cut_phase)

        current_size = data.get("current_size", len(self._roster_players))
        self._cuts_needed = data.get("cuts_needed", max(0, current_size - self._target_roster_size))

        # Store coach proposals for the new recommendations section
        self._coach_proposals = data.get("coach_proposals", [])

        # Update summary labels with dynamic target
        self.roster_size_label.setText(f"{current_size} / {self._target_roster_size}")
        if current_size > self._target_roster_size:
            self.roster_size_label.setStyleSheet(f"color: {Colors.ERROR};")
        else:
            self.roster_size_label.setStyleSheet(f"color: {Colors.SUCCESS};")

        self.cuts_needed_label.setText(str(self._cuts_needed))
        if self._cuts_needed > 0:
            self.cuts_needed_label.setStyleSheet(f"color: {Colors.ERROR};")
        else:
            self.cuts_needed_label.setStyleSheet(f"color: {Colors.SUCCESS};")


        self.marked_cut_label.setText("0")
        self.dead_money_label.setText("$0")
        self.cap_savings_label.setText("$0")

        # Populate coach recommendations section
        self._populate_coach_recommendations()

        # Update roster toggle text
        self.roster_toggle.setText(f"▶ Browse Full Roster ({len(self._roster_players)} players)")

        self._apply_filters()

    def _apply_filters(self):
        """Apply position filter and suggestions filter to roster."""
        position_filter = self.position_combo.currentData()
        show_suggestions_only = self.show_suggestions_check.isChecked()

        self._filtered_players = []
        for player in self._roster_players:
            player_id = player.get("player_id", 0)

            # Skip already cut players (check dict keys)
            if player_id in self._cut_players.keys():
                continue

            # Position filter - use POSITION_FILTER_MAP for abbreviated positions
            if position_filter:
                player_pos = player.get("position", "").lower().replace(" ", "_")

                # Check if player position maps to the selected filter
                if player_pos in POSITION_FILTER_MAP:
                    mapped_positions = POSITION_FILTER_MAP[player_pos]
                    if position_filter not in mapped_positions:
                        continue
                elif player_pos != position_filter:
                    # Unknown position - direct match only
                    continue

            # Suggestions filter
            if show_suggestions_only and player_id not in self._suggested_cuts:
                continue

            self._filtered_players.append(player)

        # Sort by value score (lowest first for easier cutting)
        self._filtered_players.sort(key=lambda p: p.get("value_score", 0))

        # Update table
        self.players_table.setRowCount(len(self._filtered_players))
        for row, player in enumerate(self._filtered_players):
            self._populate_row(row, player)

    def _populate_row(self, row: int, player: Dict):
        """Populate a single row in the table."""
        player_id = player.get("player_id", 0)
        is_suggested = player_id in self._suggested_cuts
        is_protected = player_id in self._protected_players
        is_gm_cut = player_id in self._approved_gm_cuts
        is_coach_cut = player_id in self._approved_coach_cuts
        is_manual_cut = player_id in self._cut_players

        # Highlight color based on cut source (priority: Coach > Manual > Suggested > Protected)
        if is_gm_cut or is_coach_cut:
            # Both GM and Coach cuts shown as Coach cuts (GM kept for backward compat)
            row_color = QColor("#FFEBEE")  # Light red for Coach cuts
        elif is_manual_cut:
            row_color = QColor("#FFF9C4")  # Light yellow for Manual cuts
        elif is_protected:
            row_color = QColor("#E8F5E9")  # Light green for Protected
        elif is_suggested:
            row_color = QColor("#FFF3E0")  # Light orange for Suggested
        else:
            row_color = None

        # Player name (store player_id and full player data for double-click handler)
        name_item = QTableWidgetItem(player.get("name", "Unknown"))
        name_item.setData(Qt.UserRole, player_id)
        name_item.setData(Qt.UserRole + 1, player)  # Full data for PlayerDetailDialog
        if row_color:
            name_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 0, name_item)

        # Position
        position = player.get("position", "")
        pos_item = QTableWidgetItem(get_position_abbreviation(position))
        pos_item.setTextAlignment(Qt.AlignCenter)
        if row_color:
            pos_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 1, pos_item)

        # Age (using NumericTableWidgetItem for proper sorting)
        age = player.get("age", 0)
        age_item = NumericTableWidgetItem(age)
        age_item.setTextAlignment(Qt.AlignCenter)
        # Color code age: 32+ red, 30-31 orange
        if age >= 32:
            age_item.setForeground(QColor(Colors.ERROR))
        elif age >= 30:
            age_item.setForeground(QColor(Colors.WARNING))
        if row_color:
            age_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 2, age_item)

        # Overall rating (using NumericTableWidgetItem for proper sorting)
        overall = player.get("overall", 0)
        ovr_item = NumericTableWidgetItem(overall)
        ovr_item.setTextAlignment(Qt.AlignCenter)
        if overall >= 85:
            ovr_item.setForeground(QColor(Colors.SUCCESS))
        elif overall >= 75:
            ovr_item.setForeground(QColor(Colors.INFO))
        if row_color:
            ovr_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 3, ovr_item)

        # Potential (using NumericTableWidgetItem for proper sorting)
        potential = player.get("potential", 0)
        potential_item = NumericTableWidgetItem(potential)
        potential_item.setTextAlignment(Qt.AlignCenter)
        # Color coding: Green for near ceiling, Blue for high upside
        if potential > 0:
            upside = potential - overall
            if upside <= 2:
                potential_item.setForeground(QColor(Colors.SUCCESS))
            elif upside >= 10:
                potential_item.setForeground(QColor(Colors.INFO))
        if row_color:
            potential_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 4, potential_item)

        # Dev Type (badge-style)
        dev_type = player.get("dev_type", "Normal")
        # Map dev type to single letter badge
        dev_map = {
            "Early": "E",
            "Normal": "N",
            "Late": "L"
        }
        dev_letter = dev_map.get(dev_type, "N")
        dev_item = QTableWidgetItem(dev_letter)
        dev_item.setTextAlignment(Qt.AlignCenter)
        # Badge colors
        if dev_type == "Early":
            dev_item.setForeground(QColor(Colors.WARNING))
        elif dev_type == "Late":
            dev_item.setForeground(QColor(Colors.INFO))
        else:
            dev_item.setForeground(QColor(Colors.MUTED))
        if row_color:
            dev_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 5, dev_item)

        # Salary
        salary = player.get("salary", 0)
        salary_text = f"${salary:,}" if salary else "N/A"
        salary_item = QTableWidgetItem(salary_text)
        salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if row_color:
            salary_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 6, salary_item)

        # Value score (using NumericTableWidgetItem for proper sorting)
        value = player.get("value_score", 0)
        value_item = NumericTableWidgetItem(value, display_text=f"{value:.1f}")
        value_item.setTextAlignment(Qt.AlignCenter)
        if value < 50:
            value_item.setForeground(QColor(Colors.ERROR))
        if row_color:
            value_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 7, value_item)

        # Dead money
        dead_money = player.get("dead_money", 0)
        dead_text = f"${dead_money:,}" if dead_money else "$0"
        dead_item = QTableWidgetItem(dead_text)
        dead_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if dead_money > 0:
            dead_item.setForeground(QColor(Colors.ERROR))
        if row_color:
            dead_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 8, dead_item)

        # Cap savings
        cap_savings = player.get("cap_savings", 0)
        savings_text = f"${cap_savings:,}" if cap_savings else "$0"
        savings_item = QTableWidgetItem(savings_text)
        savings_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if cap_savings > 0:
            savings_item.setForeground(QColor(Colors.SUCCESS))
        if row_color:
            savings_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 9, savings_item)

        # Status (priority: Protected > Coach Cut > Manual > Suggested > Roster)
        if is_protected:
            status_text = "Protected"
            status_color = QColor(Colors.SUCCESS)
        elif is_gm_cut or is_coach_cut:
            # Both GM and Coach cuts shown as "Coach Cut" (GM kept for backward compat)
            status_text = "Coach Cut"
            status_color = QColor(Colors.ERROR)
        elif is_manual_cut:
            june_1 = self._cut_players[player_id]
            status_text = "Manual (June 1)" if june_1 else "Manual Cut"
            status_color = QColor(Colors.WARNING)
        elif is_suggested:
            status_text = "Suggested"
            status_color = QColor(Colors.WARNING)
        else:
            status_text = "Roster"
            status_color = QColor(Colors.MUTED)

        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(status_color)
        if row_color:
            status_item.setBackground(QBrush(row_color))
        self.players_table.setItem(row, 10, status_item)

        # Action buttons
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        # View contract button (always enabled if contract exists)
        contract_id = player.get("contract_id")
        player_name = player.get("name", "Unknown")
        if contract_id:
            view_btn = QPushButton("View")
            view_btn.setStyleSheet(TABLE_VIEW_BTN_STYLE)
            view_btn.clicked.connect(
                lambda checked, cid=contract_id, pname=player_name: self._on_view_contract(cid, pname)
            )
            action_layout.addWidget(view_btn)

        if is_protected:
            # Show disabled button for protected players
            btn = QPushButton("Protected")
            btn.setEnabled(False)
            btn.setStyleSheet(TABLE_DISABLED_BTN_STYLE)
            action_layout.addWidget(btn)
        elif is_gm_cut or is_coach_cut:
            # Show disabled button for Coach approved cuts (GM cuts treated as Coach)
            btn = QPushButton("Coach Cut")
            btn.setEnabled(False)
            btn.setStyleSheet(TABLE_DISABLED_BTN_STYLE)
            action_layout.addWidget(btn)
        else:
            # Immediate Cut button
            cut_btn = QPushButton("Cut")
            cut_btn.setStyleSheet(TABLE_CUT_BTN_STYLE)
            cut_btn.clicked.connect(lambda checked, pid=player_id, r=row: self._on_cut_clicked(pid, r, False))
            action_layout.addWidget(cut_btn)

            # June 1 Cut button (spread dead money over 2 years)
            june1_btn = QPushButton("June 1")
            june1_btn.setToolTip(
                "Post-June 1 designation:\n"
                "Dead money spread over 2 years\n"
                "(more immediate cap relief)"
            )
            june1_btn.setStyleSheet(TABLE_JUNE1_BTN_STYLE)
            june1_btn.clicked.connect(lambda checked, pid=player_id, r=row: self._on_cut_clicked(pid, r, True))
            action_layout.addWidget(june1_btn)

        self.players_table.setCellWidget(row, 11, action_widget)

    def _on_cut_clicked(self, player_id: int, row: int, use_june_1: bool = False):
        """Handle cut button click.

        Args:
            player_id: ID of the player to cut
            row: Row index in the table
            use_june_1: If True, use Post-June 1 designation (spread dead money)
        """
        # Find player data for cap calculations
        player = next((p for p in self._roster_players if p.get("player_id") == player_id), None)
        if not player:
            return

        # Update status cell with cut type
        status_item = self.players_table.item(row, 10)
        if status_item:
            status_text = "June 1 Cut" if use_june_1 else "Cutting"
            status_item.setText(status_text)
            status_item.setForeground(QColor(Colors.WARNING if use_june_1 else Colors.ERROR))

        # Disable all cut buttons
        action_widget = self.players_table.cellWidget(row, 11)
        if action_widget:
            for child in action_widget.children():
                if isinstance(child, QPushButton) and child.text() in ("Cut", "June 1"):
                    child.setEnabled(False)

        # Track cut player with cut type
        self._cut_players[player_id] = use_june_1

        # Update counts and totals
        self._update_totals()

        # Emit signal with cut type
        self.player_cut.emit(player_id, use_june_1)

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

    def _on_player_double_clicked(self, row: int, column: int):
        """Handle double-click on player row to open detail dialog."""
        name_item = self.players_table.item(row, 0)
        if not name_item:
            return

        player_id = name_item.data(Qt.UserRole)
        player_data = name_item.data(Qt.UserRole + 1)
        if not player_id or not player_data:
            return

        # Only open if we have context set
        if not self._db_path or not self._dynasty_id:
            return

        try:
            from game_cycle_ui.dialogs.player_detail_dialog import PlayerDetailDialog
            dialog = PlayerDetailDialog(
                player_id=player_id,
                player_name=player_data.get("name", "Unknown"),
                player_data=player_data,
                dynasty_id=self._dynasty_id,
                season=self._season,
                db_path=self._db_path,
                team_name=self._team_name,
                parent=self
            )
            dialog.exec()
        except ImportError:
            # PlayerDetailDialog not available
            pass

    def _update_totals(self):
        """Update the summary totals based on all cut sources (GM + Coach + Manual)."""
        total_dead = 0
        total_savings = 0

        # Track counts for each source
        total_gm = len(self._approved_gm_cuts)
        total_coach = len(self._approved_coach_cuts)
        total_manual = len(self._cut_players)
        total_cuts = total_gm + total_coach + total_manual

        for player in self._roster_players:
            player_id = player.get("player_id")
            # Include all three cut sources in totals
            if (player_id in self._cut_players or
                player_id in self._approved_gm_cuts or
                player_id in self._approved_coach_cuts):
                # Note: dead_money shown is the base dead money
                # For June 1 cuts, actual dead money would be split but we show total
                total_dead += player.get("dead_money", 0)
                total_savings += player.get("cap_savings", 0)

        # Show breakdown by source (Note: approved_gm_cuts kept for backward compat, treated as Coach cuts)
        total_approved = total_gm + total_coach
        self.marked_cut_label.setText(
            f"{total_cuts} (Coach: {total_approved}, Manual: {total_manual})"
        )
        self.dead_money_label.setText(f"${total_dead:,}")
        self.cap_savings_label.setText(f"${total_savings:,}")

        # Update roster size to reflect all pending cuts (use dynamic target)
        current = len(self._roster_players) - total_cuts
        target = self._target_roster_size
        self.roster_size_label.setText(f"{current} / {target}")
        if current > target:
            self.roster_size_label.setStyleSheet(f"color: {Colors.ERROR};")
        elif current == target:
            self.roster_size_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        else:
            self.roster_size_label.setStyleSheet(f"color: {Colors.WARNING};")

        # Update cuts needed (use dynamic target)
        self._cuts_needed = max(0, current - target)
        self.cuts_needed_label.setText(str(self._cuts_needed))
        if self._cuts_needed > 0:
            self.cuts_needed_label.setStyleSheet(f"color: {Colors.ERROR};")
        else:
            self.cuts_needed_label.setStyleSheet(f"color: {Colors.SUCCESS};")

        # Re-check cap compliance after cuts change
        self._check_cap_compliance()

    def _on_get_suggestions(self):
        """Handle get suggestions button click."""
        self.get_suggestions_requested.emit()

    def set_ai_suggestions(self, suggestions: List[int], protected: List[int]):
        """Update AI suggestions after request."""
        self._suggested_cuts = set(suggestions)
        self._protected_players = set(protected)
        self._apply_filters()

    def get_cut_player_ids(self) -> List[int]:
        """Get list of ALL player IDs marked for cutting (manual + GM + Coach)."""
        all_cuts = set(self._cut_players.keys())
        all_cuts.update(self._approved_gm_cuts)
        all_cuts.update(self._approved_coach_cuts)
        return list(all_cuts)

    def get_cut_decisions(self) -> List[Dict]:
        """Get list of cut decisions with cut type.

        Returns:
            List of dicts with player_id and use_june_1 keys
        """
        return [
            {"player_id": pid, "use_june_1": use_june_1}
            for pid, use_june_1 in self._cut_players.items()
        ]

    def get_cuts_needed(self) -> int:
        """Return number of cuts still needed to reach target roster size.

        Returns:
            Number of additional cuts needed (0 if already at or below target)
        """
        return self._cuts_needed

    def show_no_cuts_needed_message(self):
        """Show message when roster is already at or under limit."""
        self.players_table.setRowCount(1)
        self.players_table.setSpan(0, 0, 1, 12)

        message_item = QTableWidgetItem(
            f"Your roster is already at or below the {self._target_roster_size}-man limit. No cuts needed!"
        )
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor(Colors.SUCCESS))
        message_font = QFont(Typography.BODY)
        message_font.setItalic(True)
        message_item.setFont(message_font)

        self.players_table.setItem(0, 0, message_item)

    def clear_cuts(self):
        """Reset cut players (call after processing)."""
        self._cut_players = {}
        self._update_totals()
        self._apply_filters()

    def set_cap_data(self, cap_data: Dict):
        """
        Update the view with full cap data from CapHelper.

        Args:
            cap_data: Dict with available_space, salary_cap_limit, total_spending,
                      dead_money, is_compliant
        """
        # Store current cap space for compliance calculations
        self._cap_space = cap_data.get("available_space", 0)
        # Check and emit cap compliance status
        self._check_cap_compliance()

    def _check_cap_compliance(self):
        """
        Check if team is cap-compliant after pending cuts and emit validation signal.

        Calculates projected cap space by adding savings from marked cuts
        to current cap space. Emits cap_validation_changed signal to
        enable/disable the Process button.
        """
        # Calculate total savings from pending cuts
        total_savings = sum(
            player.get("cap_savings", 0)
            for player in self._roster_players
            if player.get("player_id") in self._cut_players
        )

        # Projected space = current space + savings from cuts
        projected_space = self._cap_space + total_savings

        # Compliant if projected space >= 0
        is_compliant = projected_space >= 0
        over_cap_amount = abs(projected_space) if not is_compliant else 0

        self.cap_validation_changed.emit(is_compliant, over_cap_amount)