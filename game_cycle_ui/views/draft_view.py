"""
Draft View - Interactive NFL Draft UI for game cycle offseason.

Allows the user to select prospects for their team while AI teams
auto-pick. Supports simulate-to-pick and auto-complete modes.
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QComboBox, QProgressBar, QSplitter,
    QStackedWidget, QScrollArea, QCheckBox  # Added for sidebar + delegation
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from game_cycle_ui.widgets import SummaryPanel
from game_cycle_ui.widgets.ai_pick_display_widget import AIPickDisplayWidget
from game_cycle_ui.widgets.draft_trade_offers_panel import DraftTradeOffersPanel
from game_cycle_ui.theme import (
    TABLE_HEADER_STYLE, Colors,
    PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE,
    WARNING_BUTTON_STYLE, Typography, FontSizes, TextColors,
    apply_table_style, RatingColorizer
)
from game_cycle_ui.utils import TableCellHelper
from game_cycle_ui.dialogs import DraftDirectionDialog
from game_cycle.models import DraftDirection, DraftStrategy
from utils.player_field_extractors import extract_overall_rating


# ========================================================================
# Constants
# ========================================================================

class DraftConstants:
    """Draft-related constants."""
    TOTAL_PICKS = 224  # 7 rounds × 32 teams
    ROUNDS = 7
    TEAMS = 32


class UIMetrics:
    """UI sizing constants for consistent layout."""
    # Button heights
    BUTTON_HEIGHT_SMALL = 36
    BUTTON_HEIGHT_STANDARD = 40
    BUTTON_HEIGHT_LARGE = 50

    # Button widths
    BUTTON_WIDTH_NARROW = 120
    BUTTON_WIDTH_MEDIUM = 150
    BUTTON_WIDTH_MEDIUM_WIDE = 180
    BUTTON_WIDTH_WIDE = 200
    BUTTON_WIDTH_EXTRA_WIDE = 250

    # Column widths
    SELECT_COLUMN_WIDTH = 80
    PICK_COLUMN_WIDTH = 70

    # Dropdown widths
    DROPDOWN_WIDTH_STANDARD = 100
    DROPDOWN_WIDTH_MEDIUM = 120

    # GM confidence bar
    CONFIDENCE_BAR_WIDTH = 120

    # Sidebar dimensions
    SIDEBAR_EXPANDED_WIDTH = 300
    SIDEBAR_COLLAPSED_WIDTH = 40
    HEADER_HEIGHT = 40
    TAB_BAR_HEIGHT = 44
    COLLAPSE_BUTTON_SIZE = 32


# ========================================================================
# DraftSidebarPanel - Collapsible Right Sidebar
# ========================================================================

class DraftSidebarPanel(QWidget):
    """
    Collapsible right sidebar for draft information.

    Contains 4 tabs:
    - GM Recommendation (proposal card + alternatives)
    - Team Needs Analysis
    - Draft History
    - Player Scouting Details

    Signals:
        collapsed_changed: Emitted when sidebar collapse state changes (is_collapsed: bool)
        proposal_approved: GM proposal approved (proposal_id)
        proposal_rejected: GM proposal rejected (proposal_id)
        alternative_requested: Alternative prospect selected (proposal_id, prospect_id)
    """

    # Signals
    collapsed_changed = Signal(bool)
    proposal_approved = Signal(str)
    proposal_rejected = Signal(str)
    alternative_requested = Signal(str, int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._is_collapsed = False
        self._current_tab = 0
        self._current_proposal: Optional[Dict] = None
        self._team_needs: List[Dict] = []
        self._draft_history: List[Dict] = []
        self._scouting_data: Optional[Dict] = None

        self._setup_ui()

    def _setup_ui(self):
        """Build sidebar layout with header + tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with collapse button
        header = self._create_header()
        layout.addWidget(header)

        # Main content (stacked widget with 4 tabs)
        self._content_stack = QStackedWidget()

        # Tab 0: GM Recommendation
        self._gm_tab = self._create_gm_recommendation_tab()
        self._content_stack.addWidget(self._gm_tab)

        # Tab 1: Team Needs
        self._needs_tab = self._create_team_needs_tab()
        self._content_stack.addWidget(self._needs_tab)

        # Tab 2: Draft History
        self._history_tab = self._create_draft_history_tab()
        self._content_stack.addWidget(self._history_tab)

        # Tab 3: Scouting
        self._scouting_tab = self._create_scouting_tab()
        self._content_stack.addWidget(self._scouting_tab)

        layout.addWidget(self._content_stack, stretch=1)

        # Tab selector buttons at bottom
        tab_bar = self._create_tab_bar()
        layout.addWidget(tab_bar)

        # Connect history filter to refresh history table
        self.history_round_filter.currentIndexChanged.connect(
            lambda: self.set_draft_history(self._draft_history)
        )

        # Styling
        self.setStyleSheet("""
            DraftSidebarPanel {
                background-color: #1e1e1e;
                border-left: 2px solid #444;
            }
        """)

        # Set initial width
        self.setMinimumWidth(UIMetrics.SIDEBAR_EXPANDED_WIDTH)

    def _create_header(self) -> QWidget:
        """Create collapsible header with title and toggle button."""
        header = QFrame()
        header.setStyleSheet("background-color: #263238; border-bottom: 1px solid #444;")
        header.setFixedHeight(UIMetrics.HEADER_HEIGHT)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        # Title (changes based on active tab)
        self._title_label = QLabel("GM RECOMMENDATION")
        self._title_label.setFont(Typography.H5)
        self._title_label.setStyleSheet("color: #1e88e5; font-weight: bold;")
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        # Collapse/Expand button
        self._toggle_btn = QPushButton("◀")  # Left arrow when expanded
        self._toggle_btn.setFixedSize(UIMetrics.COLLAPSE_BUTTON_SIZE, UIMetrics.COLLAPSE_BUTTON_SIZE)
        self._toggle_btn.setToolTip("Collapse sidebar")
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #37474F;
                color: white;
                border-radius: 16px;
                font-size: 14pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
        """)
        self._toggle_btn.clicked.connect(self._toggle_collapse)
        header_layout.addWidget(self._toggle_btn)

        return header

    def _create_tab_bar(self) -> QWidget:
        """Create tab selector bar at bottom."""
        bar = QFrame()
        bar.setStyleSheet("background-color: #263238; border-top: 1px solid #444;")
        bar.setFixedHeight(UIMetrics.TAB_BAR_HEIGHT)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(0)

        tab_names = ["GM", "Needs", "History", "Scout"]
        self._tab_buttons = []

        for i, name in enumerate(tab_names):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setChecked(i == 0)  # First tab active
            btn.clicked.connect(lambda checked, idx=i: self._switch_tab(idx))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #90A4AE;
                    border: none;
                    padding: 10px;
                    font-size: 11pt;
                }
                QPushButton:checked {
                    color: #1e88e5;
                    background-color: #1e1e1e;
                    border-top: 3px solid #1e88e5;
                }
                QPushButton:hover {
                    background-color: #37474F;
                }
            """)
            bar_layout.addWidget(btn)
            self._tab_buttons.append(btn)

        return bar

    def _create_gm_recommendation_tab(self) -> QWidget:
        """Tab 0: GM proposal card + alternatives table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Prospect card (always visible at top, outside scroll)
        self._gm_prospect_frame = self._create_prospect_card()
        layout.addWidget(self._gm_prospect_frame)

        # Action buttons (immediately below prospect card, no scrolling needed)
        btn_layout = QHBoxLayout()
        self._approve_btn = QPushButton("Approve GM Pick")
        self._approve_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self._approve_btn.setMinimumHeight(UIMetrics.BUTTON_HEIGHT_SMALL)
        self._approve_btn.clicked.connect(self._on_approve_clicked)
        btn_layout.addWidget(self._approve_btn)

        self._reject_btn = QPushButton("Draft Manually")
        self._reject_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self._reject_btn.setMinimumHeight(UIMetrics.BUTTON_HEIGHT_SMALL)
        self._reject_btn.clicked.connect(self._on_reject_clicked)
        btn_layout.addWidget(self._reject_btn)

        layout.addLayout(btn_layout)

        # Scroll area for details (reasoning + alternatives)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)

        # Reasoning (in scroll area)
        self._gm_reasoning_label = QLabel("")
        self._gm_reasoning_label.setWordWrap(True)
        self._gm_reasoning_label.setStyleSheet(
            "color: #ccc; padding: 8px; background-color: #2a2a2a; "
            "border: 1px solid #444; border-radius: 4px; font-style: italic;"
        )
        scroll_layout.addWidget(self._gm_reasoning_label)

        # Alternatives table (in scroll area)
        alt_label = QLabel("Alternatives:")
        alt_label.setFont(Typography.SMALL)
        scroll_layout.addWidget(alt_label)

        self._alternatives_table = QTableWidget()
        self._alternatives_table.setColumnCount(5)
        self._alternatives_table.setHorizontalHeaderLabels(
            ["Name", "Pos", "College", "OVR", "Select"]
        )
        self._alternatives_table.setMaximumHeight(150)
        self._alternatives_table.verticalHeader().setVisible(False)
        apply_table_style(self._alternatives_table)

        header = self._alternatives_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.resizeSection(4, UIMetrics.PICK_COLUMN_WIDTH)

        scroll_layout.addWidget(self._alternatives_table)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Hide by default (no proposal)
        widget.setVisible(False)
        return widget

    def _create_prospect_card(self) -> QFrame:
        """Create prospect info card for GM recommendation."""
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border: 1px solid #444; "
            "border-radius: 4px; padding: 10px; }"
        )
        card_layout = QVBoxLayout(frame)
        card_layout.setContentsMargins(10, 10, 10, 10)

        # Name
        self._gm_prospect_name = QLabel("--")
        self._gm_prospect_name.setFont(Typography.H4)
        card_layout.addWidget(self._gm_prospect_name)

        # Details (Position | College | OVR)
        self._gm_prospect_details = QLabel("Position | College | OVR")
        self._gm_prospect_details.setStyleSheet(f"color: {Colors.MUTED};")
        card_layout.addWidget(self._gm_prospect_details)

        # Grade + Confidence
        detail_row = QHBoxLayout()

        self._gm_draft_grade = QLabel("Grade: --")
        self._gm_draft_grade.setFont(Typography.BODY_BOLD)
        detail_row.addWidget(self._gm_draft_grade)

        detail_row.addStretch()

        # Confidence bar (horizontal, compact)
        self._gm_confidence_bar = QProgressBar()
        self._gm_confidence_bar.setMinimum(0)
        self._gm_confidence_bar.setMaximum(100)
        self._gm_confidence_bar.setTextVisible(True)
        self._gm_confidence_bar.setFormat("Conf: %v%")
        self._gm_confidence_bar.setFixedWidth(100)
        self._gm_confidence_bar.setFixedHeight(20)
        detail_row.addWidget(self._gm_confidence_bar)

        card_layout.addLayout(detail_row)

        return frame

    def _create_team_needs_tab(self) -> QWidget:
        """Tab 1: Team needs analysis."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Instructions text
        instructions = QLabel("Positions sorted by urgency. Draft to fill your biggest needs.")
        instructions.setFont(Typography.CAPTION)
        instructions.setStyleSheet("color: #90A4AE; padding: 4px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Team needs table
        self.team_needs_table = QTableWidget()
        self.team_needs_table.setColumnCount(3)
        self.team_needs_table.setHorizontalHeaderLabels(["Position", "Priority", "Best Available"])
        self.team_needs_table.verticalHeader().setVisible(False)
        self.team_needs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.team_needs_table.setSelectionMode(QTableWidget.NoSelection)

        # Styling
        self.team_needs_table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                border: 1px solid #444;
                gridline-color: #444;
            }
            QHeaderView::section {
                background-color: #263238;
                color: #90A4AE;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)

        # Column widths
        header = self.team_needs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Position
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Priority
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Best Available

        layout.addWidget(self.team_needs_table)

        return widget

    def _create_draft_history_tab(self) -> QWidget:
        """Tab 2: Draft history."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header with round filter
        header_layout = QHBoxLayout()

        filter_label = QLabel("Round:")
        filter_label.setStyleSheet("color: #90A4AE;")
        header_layout.addWidget(filter_label)

        self.history_round_filter = QComboBox()
        self.history_round_filter.addItem("All", None)
        for r in range(1, DraftConstants.ROUNDS + 1):
            self.history_round_filter.addItem(f"R{r}", r)
        self.history_round_filter.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #444;
                padding: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: white;
                selection-background-color: #1e88e5;
            }
        """)
        header_layout.addWidget(self.history_round_filter)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Pick", "Team", "Player", "Pos", "OVR"])
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionMode(QTableWidget.NoSelection)

        # Styling
        self.history_table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                border: 1px solid #444;
                gridline-color: #444;
            }
            QHeaderView::section {
                background-color: #263238;
                color: #90A4AE;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)

        # Column widths
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Pick
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Team
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Player
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Pos
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # OVR

        layout.addWidget(self.history_table)

        return widget

    def _create_scouting_tab(self) -> QWidget:
        """Tab 3: Player scouting."""
        widget = QWidget()

        # Scroll area for long content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #1e1e1e; }")

        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Prospect name (title)
        self.scouting_name = QLabel("Select a prospect to view details")
        self.scouting_name.setFont(Typography.H4)
        self.scouting_name.setStyleSheet("color: white; padding: 4px;")
        self.scouting_name.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.scouting_name)

        # Development info section
        dev_frame = QFrame()
        dev_frame.setStyleSheet("background-color: #2a2a2a; border: 1px solid #444; border-radius: 4px;")
        dev_layout = QVBoxLayout(dev_frame)
        dev_layout.setContentsMargins(8, 8, 8, 8)

        self.scouting_dev_label = QLabel("Development: --")
        self.scouting_dev_label.setStyleSheet("color: #90A4AE; font-size: 10pt;")
        dev_layout.addWidget(self.scouting_dev_label)

        self.scouting_potential_label = QLabel("Potential: --")
        self.scouting_potential_label.setStyleSheet("color: #90A4AE; font-size: 10pt;")
        dev_layout.addWidget(self.scouting_potential_label)

        layout.addWidget(dev_frame)

        # Attributes section
        attr_label = QLabel("Key Attributes:")
        attr_label.setFont(Typography.SMALL)
        attr_label.setStyleSheet("color: #90A4AE; font-weight: bold;")
        layout.addWidget(attr_label)

        self.scouting_attributes = QLabel("--")
        self.scouting_attributes.setWordWrap(True)
        self.scouting_attributes.setStyleSheet("color: white; padding: 4px;")
        layout.addWidget(self.scouting_attributes)

        # Strengths section
        strengths_label = QLabel("Strengths:")
        strengths_label.setFont(Typography.SMALL)
        strengths_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
        layout.addWidget(strengths_label)

        self.scouting_strengths = QLabel("--")
        self.scouting_strengths.setWordWrap(True)
        self.scouting_strengths.setStyleSheet("color: #81C784; padding: 4px;")
        layout.addWidget(self.scouting_strengths)

        # Weaknesses section
        weaknesses_label = QLabel("Weaknesses:")
        weaknesses_label.setFont(Typography.SMALL)
        weaknesses_label.setStyleSheet("color: #C62828; font-weight: bold;")
        layout.addWidget(weaknesses_label)

        self.scouting_weaknesses = QLabel("--")
        self.scouting_weaknesses.setWordWrap(True)
        self.scouting_weaknesses.setStyleSheet("color: #E57373; padding: 4px;")
        layout.addWidget(self.scouting_weaknesses)

        layout.addStretch()

        scroll.setWidget(scroll_widget)

        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        return widget

    # ======== Public Methods ========

    def set_gm_proposal(self, proposal: Optional[Dict], trust_gm: bool = False):
        """Update GM recommendation display."""
        self._current_proposal = proposal

        if not proposal:
            self._gm_tab.setVisible(False)
            return

        self._gm_tab.setVisible(True)

        # Extract and populate
        details = proposal.get("details", {})
        player_name = details.get("player_name", "Unknown")
        position = details.get("position", "??")
        college = details.get("college", "Unknown")
        projected_rating = details.get("projected_rating", 0)
        draft_grade = details.get("draft_grade", "?")

        self._gm_prospect_name.setText(player_name)
        self._gm_prospect_details.setText(
            f"{position} | {college} | {projected_rating} OVR"
        )

        # Grade color coding
        grade_colors = {
            "A+": Colors.SUCCESS, "A": Colors.SUCCESS, "A-": Colors.SUCCESS,
            "B+": Colors.INFO, "B": Colors.INFO, "B-": Colors.INFO,
            "C+": Colors.WARNING, "C": Colors.WARNING,
            "D": Colors.ERROR, "F": Colors.ERROR,
        }
        self._gm_draft_grade.setText(f"Grade: {draft_grade}")
        self._gm_draft_grade.setStyleSheet(
            f"color: {grade_colors.get(draft_grade, Colors.MUTED)}; font-weight: bold;"
        )

        # Confidence
        confidence = proposal.get("confidence", 0.5)
        self._gm_confidence_bar.setValue(int(confidence * 100))

        # Reasoning
        reasoning = proposal.get("gm_reasoning", "No reasoning provided.")
        self._gm_reasoning_label.setText(reasoning)

        # Alternatives table
        alternatives = details.get("alternatives", [])
        self._populate_alternatives_table(alternatives)

        # Switch to GM tab
        self._switch_tab(0)

    def set_team_needs(self, needs: List[Dict]):
        """
        Update team needs analysis.

        Args:
            needs: List of dicts with keys: position, priority, best_available
        """
        self._team_needs = needs

        # Populate table
        self.team_needs_table.setRowCount(len(needs))
        for row, need in enumerate(needs):
            position = need.get("position", "")
            priority = need.get("priority", "Medium")
            best_available = need.get("best_available", "None")

            # Position
            TableCellHelper.set_cell(
                self.team_needs_table, row, 0,
                position,
                align=Qt.AlignCenter
            )

            # Priority (color-coded)
            priority_colors = {
                "High": "#C62828",    # Red
                "Medium": "#F57C00",  # Orange
                "Low": "#2E7D32"      # Green
            }
            TableCellHelper.set_cell(
                self.team_needs_table, row, 1,
                priority,
                align=Qt.AlignCenter,
                color=priority_colors.get(priority, "#90A4AE")
            )

            # Best Available
            TableCellHelper.set_cell(
                self.team_needs_table, row, 2,
                best_available
            )

    def set_draft_history(self, history: List[Dict]):
        """
        Update draft history.

        Args:
            history: List of dicts with keys: pick_number, team_name, player_name, position, overall
        """
        self._draft_history = history

        # Filter by selected round if needed
        selected_round = self.history_round_filter.currentData()
        if selected_round is not None:
            filtered = [
                h for h in history
                if ((h.get("pick_number", 0) - 1) // 32 + 1) == selected_round
            ]
        else:
            filtered = history

        # Populate table
        self.history_table.setRowCount(len(filtered))
        for row, pick in enumerate(filtered):
            pick_num = pick.get("pick_number", 0)
            team_name = pick.get("team_name", "")
            player_name = pick.get("player_name", "Unknown")
            position = pick.get("position", "")
            overall = pick.get("overall", 0)

            # Pick number (format: 1.1, 1.2, etc.)
            round_num = (pick_num - 1) // 32 + 1
            pick_in_round = (pick_num - 1) % 32 + 1
            TableCellHelper.set_cell(
                self.history_table, row, 0,
                f"{round_num}.{pick_in_round}",
                align=Qt.AlignCenter
            )

            # Team
            TableCellHelper.set_cell(self.history_table, row, 1, team_name)

            # Player
            TableCellHelper.set_cell(self.history_table, row, 2, player_name)

            # Position
            TableCellHelper.set_cell(
                self.history_table, row, 3,
                position,
                align=Qt.AlignCenter
            )

            # Overall
            overall_rating = extract_overall_rating(pick, default=0)
            TableCellHelper.set_cell(
                self.history_table, row, 4,
                str(overall_rating),
                align=Qt.AlignCenter
            )

    def set_scouting_data(self, prospect_data: Optional[Dict]):
        """
        Update scouting tab.

        Args:
            prospect_data: Dict with keys: name, dev_type, potential, attributes, strengths, weaknesses
        """
        self._scouting_data = prospect_data

        if not prospect_data:
            self.scouting_name.setText("Select a prospect to view details")
            self.scouting_dev_label.setText("Development: --")
            self.scouting_potential_label.setText("Potential: --")
            self.scouting_attributes.setText("--")
            self.scouting_strengths.setText("--")
            self.scouting_weaknesses.setText("--")
            return

        # Populate fields
        name = prospect_data.get("name", "Unknown")
        dev_type = prospect_data.get("dev_type", "normal").capitalize()
        potential = prospect_data.get("potential", 0)

        self.scouting_name.setText(name)
        self.scouting_dev_label.setText(f"Development: {dev_type}")
        self.scouting_potential_label.setText(f"Potential: {potential} OVR")

        # Attributes (format as bullet list)
        attributes = prospect_data.get("attributes", {})
        if attributes:
            attr_text = "\n".join([f"• {k}: {v}" for k, v in list(attributes.items())[:8]])
            self.scouting_attributes.setText(attr_text)
        else:
            self.scouting_attributes.setText("No attribute data available")

        # Strengths (green text)
        strengths = prospect_data.get("strengths", [])
        if strengths:
            strengths_text = "\n".join([f"✓ {s}" for s in strengths])
            self.scouting_strengths.setText(strengths_text)
        else:
            self.scouting_strengths.setText("--")

        # Weaknesses (red text)
        weaknesses = prospect_data.get("weaknesses", [])
        if weaknesses:
            weaknesses_text = "\n".join([f"✗ {w}" for w in weaknesses])
            self.scouting_weaknesses.setText(weaknesses_text)
        else:
            self.scouting_weaknesses.setText("--")

        # Switch to scouting tab
        self._switch_tab(3)

    def toggle_collapse(self):
        """Public method to toggle collapse state."""
        self._toggle_collapse()

    def is_collapsed(self) -> bool:
        """Return current collapse state."""
        return self._is_collapsed

    # ======== Private Methods ========

    def _toggle_collapse(self):
        """Toggle between expanded and collapsed states."""
        self._is_collapsed = not self._is_collapsed

        if self._is_collapsed:
            # Collapse: Hide content, show icon bar
            self._content_stack.setVisible(False)
            self._title_label.setVisible(False)
            self._toggle_btn.setText("▶")  # Right arrow when collapsed
            self._toggle_btn.setToolTip("Expand sidebar")

            # Shrink width
            self.setMinimumWidth(UIMetrics.SIDEBAR_COLLAPSED_WIDTH)
            self.setMaximumWidth(UIMetrics.SIDEBAR_COLLAPSED_WIDTH)

            # Rotate tab buttons to show first letter only
            for btn in self._tab_buttons:
                btn.setText(btn.text()[0])
        else:
            # Expand: Show content
            self._content_stack.setVisible(True)
            self._title_label.setVisible(True)
            self._toggle_btn.setText("◀")  # Left arrow when expanded
            self._toggle_btn.setToolTip("Collapse sidebar")

            # Restore width
            self.setMinimumWidth(UIMetrics.SIDEBAR_EXPANDED_WIDTH)
            self.setMaximumWidth(16777215)  # Qt max

            # Restore full tab names
            tab_names = ["GM", "Needs", "History", "Scout"]
            for i, btn in enumerate(self._tab_buttons):
                btn.setText(tab_names[i])

        self.collapsed_changed.emit(self._is_collapsed)

    def _switch_tab(self, index: int):
        """Switch to specified tab."""
        self._current_tab = index
        self._content_stack.setCurrentIndex(index)

        # Update title
        titles = [
            "GM RECOMMENDATION",
            "TEAM NEEDS ANALYSIS",
            "DRAFT HISTORY",
            "PLAYER SCOUTING"
        ]
        self._title_label.setText(titles[index])

        # Update button states
        for i, btn in enumerate(self._tab_buttons):
            btn.setChecked(i == index)

    def _populate_alternatives_table(self, alternatives: List[Dict]):
        """Populate alternatives table with prospect data."""
        self._alternatives_table.setRowCount(len(alternatives))

        for row, alt in enumerate(alternatives):
            # Name
            TableCellHelper.set_cell(
                self._alternatives_table, row, 0,
                alt.get("name", "Unknown")
            )

            # Position
            TableCellHelper.set_cell(
                self._alternatives_table, row, 1,
                alt.get("position", ""),
                align=Qt.AlignCenter
            )

            # College
            TableCellHelper.set_cell(
                self._alternatives_table, row, 2,
                alt.get("college", "")
            )

            # Rating
            TableCellHelper.set_cell(
                self._alternatives_table, row, 3,
                alt.get("rating", 0),
                align=Qt.AlignCenter
            )

            # Select button
            select_btn = QPushButton("Pick")
            select_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
            prospect_id = alt.get("prospect_id", 0)
            select_btn.clicked.connect(
                lambda checked, pid=prospect_id: self._on_alternative_selected(pid)
            )
            self._alternatives_table.setCellWidget(row, 4, select_btn)

    def _on_approve_clicked(self):
        """Handle approve button click."""
        if self._current_proposal:
            proposal_id = self._current_proposal.get("proposal_id", "")
            if proposal_id:
                self.proposal_approved.emit(proposal_id)

    def _on_reject_clicked(self):
        """Handle reject button click."""
        if self._current_proposal:
            proposal_id = self._current_proposal.get("proposal_id", "")
            if proposal_id:
                self.proposal_rejected.emit(proposal_id)

    def _on_alternative_selected(self, prospect_id: int):
        """Handle alternative prospect selection."""
        if self._current_proposal:
            proposal_id = self._current_proposal.get("proposal_id", "")
            if proposal_id and prospect_id:
                self.alternative_requested.emit(proposal_id, prospect_id)


class DraftView(QWidget):
    """
    Interactive draft view for the OFFSEASON_DRAFT stage.

    Features:
    - Summary panel (round, pick, on the clock)
    - Prospects table with position filter
    - Draft history table
    - Progress bar (0-224)
    - Action buttons: Draft Selected, Simulate to My Pick, Auto-Draft All

    Signals:
        prospect_drafted: Emitted when user selects a prospect (prospect_id)
        simulate_to_pick_requested: Emitted when user wants to sim to their pick
        auto_draft_all_requested: Emitted when user wants to auto-complete draft
    """

    # Signals
    prospect_drafted = Signal(int)  # prospect_id
    simulate_to_pick_requested = Signal()
    auto_draft_all_requested = Signal()
    round_filter_changed = Signal(object)  # None or int (round number)
    draft_direction_changed = Signal(object)  # DraftDirection
    advance_requested = Signal()  # Request to advance to next stage

    # Tollgate 9: GM Proposal signals
    proposal_approved = Signal(str)  # proposal_id
    proposal_rejected = Signal(str)  # proposal_id
    alternative_requested = Signal(str, int)  # proposal_id, prospect_id

    # Scouting signal
    prospect_selected_for_scouting = Signal(int)  # prospect_id

    # Enhanced Draft View signals (Phase 1-5)
    next_pick_requested = Signal()  # Manual mode: advance to next pick
    speed_changed = Signal(int)  # Speed in ms (0=manual, 1000=1s, 3000=3s, -1=instant)
    delegation_changed = Signal(bool)  # GM delegation mode changed
    trade_offer_accepted = Signal(str)  # Trade proposal_id accepted
    trade_offer_rejected = Signal(str)  # Trade proposal_id rejected

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._prospects: List[Dict] = []
        self._draft_history: List[Dict] = []
        self._current_pick: Optional[Dict] = None
        self._user_team_id: int = 1
        self._selected_prospect_id: Optional[int] = None
        self._is_user_turn: bool = False
        self._current_direction: Optional[DraftDirection] = None  # Draft strategy

        # Team context for draft direction dialog (Phase 2)
        self._season: int = 0
        self._dynasty_id: str = ""
        self._db_path: str = ""

        # Tollgate 9: GM proposal state
        self._current_proposal: Optional[Dict] = None
        self._trust_gm: bool = False

        # Enhanced Draft View state (Phase 1-5)
        self._simulation_speed: int = 0  # 0=manual, 1000=1s, 3000=3s, -1=instant
        self._delegate_to_gm: bool = False
        self._pending_trade_offers: List[Dict] = []
        self._is_simulating: bool = False
        self._last_ai_pick: Optional[Dict] = None  # For AI pick display

        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Summary panel at top
        self._create_summary_panel(layout)

        # Progress bar
        self._create_progress_bar(layout)

        # Main content: stacked widget (AI pick view / prospects table) + collapsible sidebar
        splitter = QSplitter(Qt.Horizontal)

        # Left: Stacked widget with AI Pick Display and Prospects Table
        self._left_stack = QStackedWidget()

        # Page 0: AI Pick Display (when watching AI teams pick)
        self._ai_pick_display = AIPickDisplayWidget()
        self._left_stack.addWidget(self._ai_pick_display)

        # Page 1: Prospects Table (when it's user's turn)
        prospects_widget = self._create_prospects_panel()
        self._left_stack.addWidget(prospects_widget)

        # Start on prospects table (page 1)
        self._left_stack.setCurrentIndex(1)

        splitter.addWidget(self._left_stack)

        # Right: Collapsible sidebar panel (replaces GM panel + history)
        self._sidebar_panel = DraftSidebarPanel()

        # Connect sidebar signals
        self._sidebar_panel.proposal_approved.connect(self.proposal_approved.emit)
        self._sidebar_panel.proposal_rejected.connect(self.proposal_rejected.emit)
        self._sidebar_panel.alternative_requested.connect(self.alternative_requested.emit)
        self._sidebar_panel.collapsed_changed.connect(self._on_sidebar_collapsed_changed)

        # TODO: Connect history filter when History tab is implemented
        # self._sidebar_panel.history_round_filter.currentIndexChanged.connect(
        #     self._on_history_round_filter_changed
        # )

        splitter.addWidget(self._sidebar_panel)

        # Store splitter reference for collapse handling
        self._main_splitter = splitter

        # Set initial sizes (70/30 split when expanded)
        splitter.setSizes([700, 300])

        layout.addWidget(splitter, stretch=1)

        # Action buttons at bottom
        self._create_action_buttons(layout)

    def _create_summary_panel(self, parent_layout: QVBoxLayout):
        """Create the summary panel showing draft progress."""
        # Main layout container
        summary_group = QGroupBox("Draft Status")
        summary_main_layout = QHBoxLayout(summary_group)
        summary_main_layout.setSpacing(20)

        # Stats panel (left side)
        stats_panel = SummaryPanel("")  # No title, nested inside group
        stats_panel.setFlat(True)
        stats_panel.setStyleSheet("QGroupBox { border: none; }")

        # Round info
        self.round_label = stats_panel.add_stat("Round", "1")
        # Make round label larger (override font)
        self.round_label.setFont(Typography.H2)

        # Pick info
        self.pick_label = stats_panel.add_stat("Overall Pick", "1")
        self.pick_label.setFont(Typography.H2)

        # On the clock (blue)
        self.on_clock_label = stats_panel.add_stat("On The Clock", "--", Colors.INFO)

        # Picks made
        self.picks_made_label = stats_panel.add_stat("Picks Made", f"0 / {DraftConstants.TOTAL_PICKS}")
        self.picks_made_label.setFont(Typography.H5)

        # User status
        self.user_status_label = stats_panel.add_stat("Your Status", "Waiting...")
        self.user_status_label.setFont(Typography.BODY_BOLD)

        stats_panel.add_stretch()
        summary_main_layout.addWidget(stats_panel, stretch=1)

        # Strategy section (right side) - preserve original implementation
        strategy_frame = QFrame()
        strategy_layout = QVBoxLayout(strategy_frame)
        strategy_layout.setContentsMargins(0, 0, 0, 0)

        self._strategy_badge = QLabel("Strategy: Balanced")
        self._strategy_badge.setFont(Typography.SMALL)
        self._strategy_badge.setStyleSheet(
            f"color: {Colors.INFO}; background-color: #E3F2FD; "
            "padding: 4px 8px; border-radius: 3px;"
        )
        strategy_layout.addWidget(self._strategy_badge)

        # Priority positions display
        self._priority_positions_label = QLabel("No priority positions set")
        self._priority_positions_label.setFont(Typography.SMALL)
        self._priority_positions_label.setStyleSheet(f"color: {Colors.MUTED};")
        strategy_layout.addWidget(self._priority_positions_label)

        self._set_strategy_btn = QPushButton("Set Strategy")
        self._set_strategy_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self._set_strategy_btn.clicked.connect(self._show_draft_direction_dialog)
        strategy_layout.addWidget(self._set_strategy_btn)

        summary_main_layout.addWidget(strategy_frame)

        parent_layout.addWidget(summary_group)


    def _create_progress_bar(self, parent_layout: QVBoxLayout):
        """Create the draft progress bar."""
        progress_layout = QHBoxLayout()

        progress_label = QLabel("Draft Progress:")
        progress_label.setStyleSheet("font-weight: bold;")
        progress_layout.addWidget(progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(DraftConstants.TOTAL_PICKS)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m picks")
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #ccc; border-radius: 4px; text-align: center; }"
            f"QProgressBar::chunk {{ background-color: {Colors.INFO}; }}"
        )
        progress_layout.addWidget(self.progress_bar, stretch=1)

        parent_layout.addLayout(progress_layout)

    def _create_prospects_panel(self) -> QWidget:
        """Create the prospects panel with table and filter."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header with filter
        header_layout = QHBoxLayout()

        header_label = QLabel("Available Prospects")
        header_label.setFont(Typography.BODY_BOLD)
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        filter_label = QLabel("Position:")
        header_layout.addWidget(filter_label)

        self.position_filter = QComboBox()
        self.position_filter.addItem("All Positions", "")
        positions = ["QB", "RB", "WR", "TE", "OT", "OG", "C", "EDGE", "DT", "LB", "CB", "S", "K", "P"]
        for pos in positions:
            self.position_filter.addItem(pos, pos)
        self.position_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.position_filter.setMinimumWidth(UIMetrics.DROPDOWN_WIDTH_MEDIUM)
        header_layout.addWidget(self.position_filter)

        layout.addLayout(header_layout)

        # Prospects table
        self.prospects_table = QTableWidget()
        self.prospects_table.setColumnCount(7)
        self.prospects_table.setHorizontalHeaderLabels([
            "Rank", "Name", "Position", "College", "OVR", "Age", "Select"
        ])

        # Apply standard table styling
        apply_table_style(self.prospects_table)

        # Configure column resize modes
        header = self.prospects_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Rank
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Position
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # College
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # OVR
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Age
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        header.resizeSection(6, UIMetrics.SELECT_COLUMN_WIDTH)  # Select button column

        # Connect row click to load scouting data
        self.prospects_table.cellClicked.connect(self._on_prospect_row_clicked)

        layout.addWidget(self.prospects_table)

        return widget


    def _create_action_buttons(self, parent_layout: QVBoxLayout):
        """Create the control bar and action buttons at the bottom."""
        # Control bar container
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #263238;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(12, 8, 12, 8)
        control_layout.setSpacing(8)

        # Top row: Speed controls and simulation buttons
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # Speed dropdown
        speed_label = QLabel("Speed:")
        speed_label.setStyleSheet("color: #90A4AE; font-weight: bold;")
        top_row.addWidget(speed_label)

        self._speed_combo = QComboBox()
        self._speed_combo.addItem("Manual", 0)
        self._speed_combo.addItem("1 Second", 1000)
        self._speed_combo.addItem("3 Seconds", 3000)
        self._speed_combo.addItem("Instant", -1)
        self._speed_combo.setMinimumWidth(UIMetrics.DROPDOWN_WIDTH_MEDIUM)
        self._speed_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #444;
                padding: 6px 10px;
                border-radius: 4px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: white;
                selection-background-color: #1e88e5;
            }
        """)
        self._speed_combo.currentIndexChanged.connect(self._on_speed_combo_changed)
        top_row.addWidget(self._speed_combo)

        # Next Pick button (only visible in manual mode)
        self._next_pick_btn = QPushButton("Next Pick →")
        self._next_pick_btn.setMinimumHeight(UIMetrics.BUTTON_HEIGHT_SMALL)
        self._next_pick_btn.setMinimumWidth(UIMetrics.BUTTON_WIDTH_NARROW)
        self._next_pick_btn.setStyleSheet(WARNING_BUTTON_STYLE)
        self._next_pick_btn.clicked.connect(self._on_next_pick)
        top_row.addWidget(self._next_pick_btn)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("color: #444;")
        top_row.addWidget(sep1)

        # Simulate to my pick button
        self.sim_to_pick_btn = QPushButton("Sim to My Pick")
        self.sim_to_pick_btn.setMinimumHeight(UIMetrics.BUTTON_HEIGHT_SMALL)
        self.sim_to_pick_btn.setMinimumWidth(UIMetrics.BUTTON_WIDTH_MEDIUM)
        self.sim_to_pick_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.sim_to_pick_btn.clicked.connect(self._on_sim_to_pick)
        top_row.addWidget(self.sim_to_pick_btn)

        # Draft selected button
        self.draft_btn = QPushButton("Draft Selected")
        self.draft_btn.setMinimumHeight(UIMetrics.BUTTON_HEIGHT_SMALL)
        self.draft_btn.setMinimumWidth(UIMetrics.BUTTON_WIDTH_MEDIUM)
        self.draft_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.draft_btn.setEnabled(False)
        self.draft_btn.clicked.connect(self._on_draft_selected)
        top_row.addWidget(self.draft_btn)

        top_row.addStretch()

        # Complete Draft button
        self.auto_draft_btn = QPushButton("Complete Draft")
        self.auto_draft_btn.setMinimumHeight(UIMetrics.BUTTON_HEIGHT_SMALL)
        self.auto_draft_btn.setMinimumWidth(UIMetrics.BUTTON_WIDTH_MEDIUM)
        self.auto_draft_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.auto_draft_btn.clicked.connect(self._on_auto_draft)
        top_row.addWidget(self.auto_draft_btn)

        control_layout.addLayout(top_row)

        # Bottom row: Delegation checkbox
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        self._delegate_checkbox = QCheckBox("Delegate to GM")
        self._delegate_checkbox.setStyleSheet("""
            QCheckBox {
                color: #90A4AE;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #2a2a2a;
                border: 2px solid #444;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #1e88e5;
                border: 2px solid #1e88e5;
                border-radius: 3px;
            }
        """)
        self._delegate_checkbox.setToolTip(
            "When enabled, GM will automatically handle all draft picks and trade decisions"
        )
        self._delegate_checkbox.toggled.connect(self._on_delegation_toggled)
        bottom_row.addWidget(self._delegate_checkbox)

        self._delegation_status = QLabel("GM will await your decisions")
        self._delegation_status.setStyleSheet("color: #666; font-style: italic;")
        bottom_row.addWidget(self._delegation_status)

        bottom_row.addStretch()

        # Advance to next stage button (shown only when draft complete)
        self.advance_btn = QPushButton("Advance to Next Stage →")
        self.advance_btn.setMinimumHeight(UIMetrics.BUTTON_HEIGHT_LARGE)
        self.advance_btn.setMinimumWidth(UIMetrics.BUTTON_WIDTH_EXTRA_WIDE)
        self.advance_btn.setStyleSheet(PRIMARY_BUTTON_STYLE + "; font-size: 14pt;")
        self.advance_btn.setVisible(False)  # Hidden until draft complete
        self.advance_btn.clicked.connect(self._on_advance_requested)
        bottom_row.addWidget(self.advance_btn)

        control_layout.addLayout(bottom_row)

        parent_layout.addWidget(control_frame)

    # ========================================================================
    # Public Methods
    # ========================================================================

    def set_user_team_id(self, team_id: int):
        """Set the user's team ID for determining when it's their pick."""
        self._user_team_id = team_id

    def set_team_context(self, season: int, dynasty_id: str, db_path: str):
        """
        Set team context for draft direction dialog (Phase 2).

        Args:
            season: Current season
            dynasty_id: Dynasty ID
            db_path: Database path
        """
        self._season = season
        self._dynasty_id = dynasty_id
        self._db_path = db_path

    def set_prospects(self, prospects: List[Dict]):
        """
        Set the available prospects.

        Args:
            prospects: List of prospect dictionaries with:
                - prospect_id: int
                - name: str
                - position: str
                - college: str (optional)
                - overall: int
                - age: int
                - rank: int (draft rank)
        """
        self._prospects = prospects
        self._refresh_prospects_table()

    def set_current_pick(self, pick_info: Optional[Dict]):
        """
        Set the current pick information.

        Args:
            pick_info: Dictionary with:
                - round: int
                - pick_in_round: int
                - overall_pick: int
                - team_id: int
                - team_name: str (optional)
        """
        self._current_pick = pick_info

        if pick_info is None:
            # Draft complete
            self.round_label.setText("-")
            self.pick_label.setText("-")
            self.on_clock_label.setText("Draft Complete")
            self.on_clock_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: bold;")
            self._is_user_turn = False
            self._update_button_states()
            return

        # Update display
        round_num = pick_info.get("round", 1)
        overall = pick_info.get("overall_pick", 1)
        team_id = pick_info.get("team_id", 0)
        team_name = pick_info.get("team_name", f"Team {team_id}")

        self.round_label.setText(str(round_num))
        self.pick_label.setText(str(overall))
        self.on_clock_label.setText(team_name)

        # Check if it's user's turn
        self._is_user_turn = (team_id == self._user_team_id)

        if self._is_user_turn:
            self.on_clock_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: bold;")
            self.user_status_label.setText("YOUR PICK!")
            self.user_status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: bold;")
        else:
            self.on_clock_label.setStyleSheet(f"color: {Colors.INFO};")
            self.user_status_label.setText("Waiting...")
            self.user_status_label.setStyleSheet(f"color: {Colors.MUTED};")

        self._update_button_states()

    def set_draft_progress(self, picks_made: int, total_picks: int = DraftConstants.TOTAL_PICKS):
        """Update the draft progress bar and counter."""
        self.progress_bar.setMaximum(total_picks)
        self.progress_bar.setValue(picks_made)
        self.picks_made_label.setText(f"{picks_made} / {total_picks}")

    def set_draft_history(self, history: List[Dict]):
        """
        Set the draft history.

        Args:
            history: List of pick dictionaries with:
                - pick_number: int (or overall_pick)
                - team_name: str
                - player_name: str
                - position: str
                - overall: int
        """
        self._draft_history = history

        # Delegate to sidebar (convert old format if needed)
        formatted_history = []
        for pick in history:
            formatted_history.append({
                "pick_number": pick.get("pick_number") or pick.get("overall_pick", 0),
                "team_name": pick.get("team_name", ""),
                "player_name": pick.get("player_name", "Unknown"),
                "position": pick.get("position", ""),
                "overall": pick.get("overall", 0)
            })

        self._sidebar_panel.set_draft_history(formatted_history)

    def set_draft_complete(self):
        """Mark draft as complete and show advance button."""
        self.set_current_pick(None)

        # Hide all action buttons
        self.draft_btn.setVisible(False)
        self.sim_to_pick_btn.setVisible(False)
        self.auto_draft_btn.setVisible(False)

        # Show advance button
        self.advance_btn.setVisible(True)
        self.advance_btn.setEnabled(True)

        self.user_status_label.setText("Draft Complete!")
        self.user_status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: bold;")

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _refresh_prospects_table(self):
        """Refresh the prospects table with current filter."""
        filter_pos = self.position_filter.currentData()

        # Filter prospects
        if filter_pos:
            filtered = [p for p in self._prospects if p.get("position") == filter_pos]
        else:
            filtered = self._prospects

        self.prospects_table.setRowCount(len(filtered))

        for row, prospect in enumerate(filtered):
            self._populate_prospect_row(row, prospect)

    def _populate_prospect_row(self, row: int, prospect: Dict):
        """Populate a single row in the prospects table."""
        prospect_id = prospect.get("prospect_id", 0)

        # Rank
        TableCellHelper.set_cell(
            self.prospects_table, row, 0,
            prospect.get("rank", row + 1),
            align=Qt.AlignCenter,
            data=prospect_id
        )

        # Name
        TableCellHelper.set_cell(self.prospects_table, row, 1, prospect.get("name", "Unknown"))

        # Position
        TableCellHelper.set_cell(
            self.prospects_table, row, 2,
            prospect.get("position", ""),
            align=Qt.AlignCenter
        )

        # College
        TableCellHelper.set_cell(self.prospects_table, row, 3, prospect.get("college", ""))

        # Overall (with rating color)
        overall = extract_overall_rating(prospect, default=0)
        TableCellHelper.set_cell(
            self.prospects_table, row, 4,
            overall,
            align=Qt.AlignCenter,
            color=RatingColorizer.get_color_for_rating(overall)
        )

        # Age
        TableCellHelper.set_cell(
            self.prospects_table, row, 5,
            prospect.get("age", 21),
            align=Qt.AlignCenter
        )

        # Select button
        select_btn = QPushButton("Select")
        select_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        select_btn.clicked.connect(lambda checked, pid=prospect_id: self._on_prospect_selected(pid))
        # Only enable if it's user's turn
        select_btn.setEnabled(self._is_user_turn)
        self.prospects_table.setCellWidget(row, 6, select_btn)

    def _refresh_history_table(self):
        """Refresh the draft history table."""
        # Show most recent picks first
        history = list(reversed(self._draft_history))
        self.history_table.setRowCount(len(history))

        for row, pick in enumerate(history):
            self._populate_history_row(row, pick)

    def _populate_history_row(self, row: int, pick: Dict):
        """Populate a single row in the history table."""
        # Pick number
        TableCellHelper.set_cell(
            self.history_table, row, 0,
            pick.get("overall_pick", 0),
            align=Qt.AlignCenter
        )

        # Team
        TableCellHelper.set_cell(self.history_table, row, 1, pick.get("team_name", ""))

        # Player
        TableCellHelper.set_cell(self.history_table, row, 2, pick.get("player_name", ""))

        # Position
        TableCellHelper.set_cell(
            self.history_table, row, 3,
            pick.get("position", ""),
            align=Qt.AlignCenter
        )

        # Overall rating
        TableCellHelper.set_cell(
            self.history_table, row, 4,
            pick.get("overall", 0),
            align=Qt.AlignCenter
        )

    def _on_filter_changed(self):
        """Handle position filter change."""
        self._refresh_prospects_table()

    # TODO: Uncomment when History tab is implemented
    # def _on_history_round_filter_changed(self):
    #     """Handle history round filter change from sidebar."""
    #     # Access filter from sidebar
    #     round_val = self._sidebar_panel.history_round_filter.currentData()
    #     self.round_filter_changed.emit(round_val)

    def _on_sidebar_collapsed_changed(self, is_collapsed: bool):
        """Handle sidebar collapse/expand."""
        if is_collapsed:
            # Give more space to prospects table when sidebar collapsed
            self._main_splitter.setSizes([1000, 40])
        else:
            # Restore 70/30 split when sidebar expanded
            self._main_splitter.setSizes([700, 300])

    def _on_prospect_row_clicked(self, row: int, col: int):
        """Handle prospect row click to load scouting data."""
        # Get prospect_id from the row's first cell
        rank_item = self.prospects_table.item(row, 0)
        if not rank_item:
            return

        prospect_id = rank_item.data(Qt.UserRole)
        if prospect_id:
            # Emit signal for controller to load scouting data
            self.prospect_selected_for_scouting.emit(prospect_id)

    def _on_prospect_selected(self, prospect_id: int):
        """Handle prospect selection."""
        self._selected_prospect_id = prospect_id
        self._update_button_states()

        # Highlight selected row
        for row in range(self.prospects_table.rowCount()):
            rank_item = self.prospects_table.item(row, 0)
            if rank_item and rank_item.data(Qt.UserRole) == prospect_id:
                self.prospects_table.selectRow(row)
                break

        # If it's user's turn, draft immediately
        if self._is_user_turn and prospect_id:
            self._on_draft_selected()

    def _on_draft_selected(self):
        """Handle draft selected button click."""
        if self._selected_prospect_id and self._is_user_turn:
            self.draft_btn.setEnabled(False)
            self.prospect_drafted.emit(self._selected_prospect_id)
            self._selected_prospect_id = None

    def _on_sim_to_pick(self):
        """Handle simulate to my pick button click."""
        self.sim_to_pick_btn.setEnabled(False)
        self.sim_to_pick_btn.setText("Simulating...")
        self.simulate_to_pick_requested.emit()

    def _on_auto_draft(self):
        """Handle auto-draft all button click."""
        self.auto_draft_btn.setEnabled(False)
        self.auto_draft_btn.setText("Auto-Drafting...")
        self.auto_draft_all_requested.emit()

    def _on_advance_requested(self):
        """Handle advance to next stage button click."""
        self.advance_requested.emit()

    def _update_button_states(self):
        """Update button enabled states based on current state."""
        draft_not_complete = self._current_pick is not None

        # Draft button: only when user's turn and prospect selected
        can_draft = self._is_user_turn and self._selected_prospect_id is not None
        self.draft_btn.setEnabled(can_draft)

        # Sim to pick: enabled if not user's turn and draft not complete
        can_sim = not self._is_user_turn and draft_not_complete and not self._is_simulating
        self.sim_to_pick_btn.setEnabled(can_sim)
        self.sim_to_pick_btn.setText("Sim to My Pick")

        # Auto draft: enabled if draft not complete
        can_auto = draft_not_complete and not self._is_simulating
        self.auto_draft_btn.setEnabled(can_auto)
        self.auto_draft_btn.setText("Complete Draft")

        # Next Pick button: only in manual mode when not user's turn
        is_manual = (self._simulation_speed == 0)
        can_next = is_manual and not self._is_user_turn and draft_not_complete and not self._is_simulating
        self._next_pick_btn.setEnabled(can_next)
        self._next_pick_btn.setVisible(is_manual)

        # Update select buttons in table
        for row in range(self.prospects_table.rowCount()):
            btn = self.prospects_table.cellWidget(row, 6)
            if btn:
                btn.setEnabled(self._is_user_turn)

    def show_no_prospects_message(self):
        """Show a message when there are no available prospects."""
        self.prospects_table.setRowCount(1)
        self.prospects_table.setSpan(0, 0, 1, 7)

        message_item = QTableWidgetItem("No prospects available - Draft class not generated")
        message_item.setTextAlignment(Qt.AlignCenter)
        message_item.setForeground(QColor(Colors.MUTED))
        message_font = Typography.BODY
        message_font.setItalic(True)
        message_item.setFont(message_font)

        self.prospects_table.setItem(0, 0, message_item)

    def set_cap_data(self, cap_data: Dict):
        """
        Update the view with full cap data from CapHelper.

        Args:
            cap_data: Dict with available_space, salary_cap_limit, total_spending,
                      dead_money, is_compliant
        """
        # Draft view uses rookie contracts (slot-based)
        # Cap impact is minimal and fixed by pick position
        pass

    def set_owner_directives(self, directives_dict: Optional[Dict]):
        """
        Display owner directives in strategy section.

        Args:
            directives_dict: Owner directives from preview (owner_directives key)
        """
        if not directives_dict:
            self._priority_positions_label.setText("No directives set")
            self._priority_positions_label.setStyleSheet(f"color: {Colors.MUTED};")
            return

        # Update strategy badge
        draft_strategy = directives_dict.get("draft_strategy", "balanced")
        strategy_names = {
            "bpa": "Best Player Available",
            "balanced": "Balanced",
            "needs_based": "Needs-Based",
            "position_focus": "Position Focus",
        }
        strategy_text = strategy_names.get(draft_strategy, "Balanced")
        self._strategy_badge.setText(f"Strategy: {strategy_text}")

        # Update priority positions
        priority_positions = directives_dict.get("priority_positions", [])
        if priority_positions:
            # Display up to 5 positions
            positions_text = ", ".join(priority_positions[:5])
            self._priority_positions_label.setText(f"Priority: {positions_text}")
            self._priority_positions_label.setStyleSheet(
                f"color: {Colors.SUCCESS}; font-weight: bold;"
            )
        else:
            self._priority_positions_label.setText("No priority positions")
            self._priority_positions_label.setStyleSheet(f"color: {Colors.MUTED};")

    def _show_draft_direction_dialog(self):
        """Show the draft direction configuration dialog."""
        dialog = DraftDirectionDialog(
            current_direction=self._current_direction,
            team_id=self._user_team_id,
            season=self._season,
            dynasty_id=self._dynasty_id,
            db_path=self._db_path,
            parent=self
        )

        dialog.direction_saved.connect(self._on_direction_saved)
        dialog.exec()

    def _on_direction_saved(self, direction: DraftDirection):
        """
        Handle saved draft direction.

        Args:
            direction: New draft direction from dialog
        """
        self._current_direction = direction
        self.draft_direction_changed.emit(direction)

        # Update badge
        strategy_names = {
            DraftStrategy.BEST_PLAYER_AVAILABLE: "BPA",
            DraftStrategy.BALANCED: "Balanced",
            DraftStrategy.NEEDS_BASED: "Needs-Based",
            DraftStrategy.POSITION_FOCUS: "Position Focus",
        }
        strategy_text = strategy_names.get(direction.strategy, "Balanced")
        self._strategy_badge.setText(f"Strategy: {strategy_text}")

    def get_draft_direction(self) -> Optional[DraftDirection]:
        """
        Get the current draft direction.

        Returns:
            Current DraftDirection or None
        """
        return self._current_direction

    # ==========================================================================
    # Tollgate 9: GM Proposal Methods
    # ==========================================================================

    def set_gm_proposal(self, proposal: Optional[Dict], trust_gm: bool = False):
        """
        Set the GM's draft proposal for display.

        Args:
            proposal: GM proposal dict with details, or None to hide panel
            trust_gm: Whether the owner has enabled trust_gm mode
        """
        # Delegate to sidebar
        self._sidebar_panel.set_gm_proposal(proposal, trust_gm)

        # Switch to GM tab when proposal is set
        if proposal:
            self._sidebar_panel._switch_tab(0)

    def set_team_needs(self, needs: List[Dict]):
        """
        Update team needs analysis in sidebar.

        Args:
            needs: List of dicts with keys: position, priority, best_available
        """
        self._sidebar_panel.set_team_needs(needs)

    def set_prospect_scouting_data(self, prospect_data: Optional[Dict]):
        """
        Update scouting tab with prospect details.

        Args:
            prospect_data: Dict with keys: name, dev_type, potential, attributes, strengths, weaknesses
        """
        self._sidebar_panel.set_scouting_data(prospect_data)

    def toggle_sidebar(self):
        """Toggle sidebar for keyboard shortcut."""
        self._sidebar_panel.toggle_collapse()

    # ==========================================================================
    # Enhanced Draft View Methods (Phase 1-5)
    # ==========================================================================

    def _on_speed_combo_changed(self):
        """Handle speed dropdown change."""
        speed_ms = self._speed_combo.currentData()
        self._simulation_speed = speed_ms
        self.speed_changed.emit(speed_ms)

        # Show/hide Next Pick button based on manual mode
        is_manual = (speed_ms == 0)
        self._next_pick_btn.setVisible(is_manual)

        # Update button states
        self._update_button_states()

    def _on_next_pick(self):
        """Handle Next Pick button click (manual mode)."""
        self._next_pick_btn.setEnabled(False)
        self.next_pick_requested.emit()

    def _on_delegation_toggled(self, checked: bool):
        """Handle delegation checkbox toggle."""
        self._delegate_to_gm = checked
        self.delegation_changed.emit(checked)

        # Update status label
        if checked:
            self._delegation_status.setText("GM will handle all draft decisions automatically")
            self._delegation_status.setStyleSheet("color: #1e88e5; font-style: italic;")
        else:
            self._delegation_status.setText("GM will await your decisions")
            self._delegation_status.setStyleSheet("color: #666; font-style: italic;")

    def set_ai_pick_display(self, pick_data: Dict):
        """
        Display AI team's draft pick in the AI Pick Display widget.

        Switches the left panel to show the AI pick view.

        Args:
            pick_data: Dict with keys:
                - team_name: str
                - team_id: int
                - pick_number: int (overall)
                - round: int
                - pick_in_round: int
                - prospect_name: str
                - position: str
                - college: str
                - overall: int
                - needs_met: List[str]
                - reasoning: str
        """
        self._last_ai_pick = pick_data
        self._ai_pick_display.set_pick_data(pick_data)
        self._left_stack.setCurrentIndex(0)  # Switch to AI pick view

    def show_ai_pick_view(self):
        """Switch to AI pick display view."""
        self._left_stack.setCurrentIndex(0)

    def show_prospects_view(self):
        """Switch to prospects table view (user's turn)."""
        self._left_stack.setCurrentIndex(1)
        self._ai_pick_display.clear()

    def set_trade_offers(self, offers: List[Dict]):
        """
        Set incoming trade offers for the current pick.

        When user is on the clock, this updates the sidebar to show
        trade offers from AI teams.

        Args:
            offers: List of trade offer dicts with:
                - proposal_id: str
                - offering_team: str
                - offering_team_id: int
                - offering_assets: List[Dict]
                - requesting_pick: str
                - gm_recommendation: str
                - gm_reasoning: str
                - gm_confidence: float
        """
        self._pending_trade_offers = offers

        # If sidebar has trade offers panel, update it
        # For now, we'll integrate with the existing GM tab
        # TODO: Create dedicated trade offers panel in sidebar

    def set_simulating(self, is_simulating: bool):
        """
        Set simulation state to update UI accordingly.

        Args:
            is_simulating: True if draft is being simulated
        """
        self._is_simulating = is_simulating

        if is_simulating:
            self._next_pick_btn.setEnabled(False)
            self.sim_to_pick_btn.setEnabled(False)
            self.sim_to_pick_btn.setText("Simulating...")
            self.auto_draft_btn.setEnabled(False)
        else:
            self._update_button_states()

    def on_pick_completed(self, pick_result: Dict):
        """
        Handle notification that a pick was completed.

        Called by controller after each pick during simulation.

        Args:
            pick_result: Dict with pick details from DraftService
        """
        # Update AI pick display if it was an AI pick
        if pick_result.get("team_id") != self._user_team_id:
            self.set_ai_pick_display(pick_result)

        # Re-enable Next Pick button in manual mode
        if self._simulation_speed == 0:
            self._next_pick_btn.setEnabled(True)

    def on_user_turn_reached(self):
        """
        Handle notification that it's the user's turn.

        Called by controller when simulation reaches user's pick.
        """
        self._is_simulating = False
        self.show_prospects_view()
        self._update_button_states()

        # Enable Next Pick button if in manual mode
        if self._simulation_speed == 0:
            self._next_pick_btn.setEnabled(False)  # Can't advance when it's your turn

    def get_simulation_speed(self) -> int:
        """Get current simulation speed in milliseconds."""
        return self._simulation_speed

    def is_delegation_enabled(self) -> bool:
        """Check if GM delegation is enabled."""
        return self._delegate_to_gm
