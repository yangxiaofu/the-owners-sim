"""
Owner Review View - Full-featured owner decisions UI.

Allows the owner to:
- Review season summary vs. expectations
- Fire/hire GM and Head Coach with candidate selection
- Set strategic directives for the upcoming season

Part of Milestone 13: Owner Review.
"""

from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QFrame, QTabWidget, QSpinBox, QComboBox,
    QLineEdit, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from game_cycle_ui.theme import UITheme, TABLE_HEADER_STYLE


# Position options for priority selection
POSITION_OPTIONS = [
    "None", "QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT",
    "LE", "DT", "RE", "LOLB", "MLB", "ROLB", "CB", "FS", "SS",
    "K", "P", "EDGE"
]

# Draft strategy options
DRAFT_STRATEGIES = [
    ("balanced", "Balanced - Mix of BPA and needs"),
    ("bpa", "Best Player Available"),
    ("needs", "Needs-Based - Focus on roster holes"),
    ("position_focus", "Position Focus - Target specific positions"),
]

# FA philosophy options
FA_PHILOSOPHIES = [
    ("balanced", "Balanced - Evaluate each opportunity"),
    ("aggressive", "Aggressive - Pursue top talent heavily"),
    ("conservative", "Conservative - Focus on value signings"),
]


class OwnerView(QWidget):
    """
    View for the owner review stage.

    Features:
    - Tab 1: Season Summary - Record vs. expectations
    - Tab 2: Staff Decisions - GM/HC keep/fire/hire
    - Tab 3: Strategic Direction - Directives for GM

    Signals:
        continue_clicked: User ready to proceed to next stage
        gm_fired: GM was fired, candidates generated
        hc_fired: HC was fired, candidates generated
        gm_hired(str): GM hired with candidate_id
        hc_hired(str): HC hired with candidate_id
        directives_saved(dict): Strategic directives saved
    """

    continue_clicked = Signal()
    gm_fired = Signal()
    hc_fired = Signal()
    gm_hired = Signal(str)  # candidate_id
    hc_hired = Signal(str)  # candidate_id
    directives_saved = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Current state
        self._current_staff: Optional[Dict[str, Any]] = None
        self._gm_candidates: List[Dict[str, Any]] = []
        self._hc_candidates: List[Dict[str, Any]] = []
        self._season_summary: Optional[Dict[str, Any]] = None
        self._is_gm_fired: bool = False
        self._is_hc_fired: bool = False
        self._selected_gm_id: Optional[str] = None
        self._selected_hc_id: Optional[str] = None

        # Completion tracking for flow guidance
        self._summary_reviewed: bool = False
        self._staff_decisions_complete: bool = False
        self._directives_saved: bool = False

        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        self._create_header(layout)

        # Tab widget for main content
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                background: #ffffff;
                border-radius: 4px;
            }
            QTabBar::tab {
                padding: 10px 24px;
                margin-right: 4px;
                border: 1px solid #ccc;
                border-bottom: none;
                background: #e0e0e0;
                color: #333333;
                font-size: 13px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #1976D2;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #d0d0d0;
            }
        """)

        # Tab 1: Season Summary
        self._summary_tab = self._create_summary_tab()
        self._tab_widget.addTab(self._summary_tab, "Season Summary")

        # Tab 2: Staff Decisions
        self._staff_tab = self._create_staff_tab()
        self._tab_widget.addTab(self._staff_tab, "Staff Decisions")

        # Tab 3: Strategic Direction
        self._strategy_tab = self._create_strategy_tab()
        self._tab_widget.addTab(self._strategy_tab, "Strategic Direction")

        # Connect tab change signal to track visits
        self._tab_widget.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self._tab_widget, stretch=1)

        # Continue button at bottom
        self._create_continue_button(layout)

        # Initialize flow guidance
        self._update_flow_guidance()

    def _create_header(self, layout: QVBoxLayout):
        """Create the header section."""
        header = QLabel("Owner Review")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #1976D2;")
        layout.addWidget(header)

        subtitle = QLabel("Review performance and set direction for the upcoming season")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        # Action banner for flow guidance
        self._action_banner = QFrame()
        self._action_banner.setObjectName("action_banner")
        banner_layout = QHBoxLayout(self._action_banner)
        banner_layout.setContentsMargins(16, 12, 16, 12)

        self._banner_icon = QLabel()
        self._banner_icon.setFixedWidth(24)
        banner_layout.addWidget(self._banner_icon)

        self._banner_text = QLabel()
        self._banner_text.setFont(QFont("Arial", 11))
        self._banner_text.setWordWrap(True)
        banner_layout.addWidget(self._banner_text, stretch=1)

        self._banner_action_btn = QPushButton()
        self._banner_action_btn.setFixedWidth(120)
        self._banner_action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._banner_action_btn.clicked.connect(self._on_banner_action_clicked)
        banner_layout.addWidget(self._banner_action_btn)

        layout.addWidget(self._action_banner)

    # ==================== Tab 1: Season Summary ====================

    def _create_summary_tab(self) -> QWidget:
        """Create the season summary tab."""
        widget = QWidget()
        widget.setStyleSheet("background-color: #ffffff;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Season record group
        record_group = QGroupBox("Season Record")
        record_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #f9f9f9;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #333333;
            }
        """)
        record_layout = QHBoxLayout(record_group)
        record_layout.setSpacing(40)

        # Season year
        year_frame = self._create_stat_frame("Season", "--")
        self._season_label = year_frame.findChild(QLabel, "value_label")
        record_layout.addWidget(year_frame)

        # Record
        record_frame = self._create_stat_frame("Record", "-- - --")
        self._record_label = record_frame.findChild(QLabel, "value_label")
        record_layout.addWidget(record_frame)

        # Target wins
        target_frame = self._create_stat_frame("Target", "--")
        self._target_label = target_frame.findChild(QLabel, "value_label")
        record_layout.addWidget(target_frame)

        # Met expectations
        met_frame = self._create_stat_frame("Expectations", "--")
        self._expectations_label = met_frame.findChild(QLabel, "value_label")
        record_layout.addWidget(met_frame)

        record_layout.addStretch()
        layout.addWidget(record_group)

        # Placeholder for additional stats
        placeholder = QLabel(
            "Additional season statistics and performance metrics\n"
            "will be displayed here in future updates."
        )
        placeholder.setStyleSheet("color: #888; font-style: italic;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder)

        layout.addStretch()
        return widget

    def _create_stat_frame(self, title: str, value: str) -> QFrame:
        """Create a stat display frame."""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #555555; font-size: 12px;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setObjectName("value_label")
        value_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        value_label.setStyleSheet("color: #222222;")
        layout.addWidget(value_label)

        return frame

    # ==================== Tab 2: Staff Decisions ====================

    def _create_staff_tab(self) -> QWidget:
        """Create the staff decisions tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: #ffffff;")

        widget = QWidget()
        widget.setStyleSheet("background-color: #ffffff;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(16, 16, 16, 16)

        # GM Section
        self._gm_group = self._create_staff_section("General Manager", "gm")
        layout.addWidget(self._gm_group)

        # HC Section
        self._hc_group = self._create_staff_section("Head Coach", "hc")
        layout.addWidget(self._hc_group)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def _create_staff_section(self, title: str, staff_type: str) -> QGroupBox:
        """Create a staff section (GM or HC) with keep/fire/hire functionality."""
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #f9f9f9;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #333333;
            }
            QLabel {
                color: #333333;
            }
        """)
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Current staff info frame (shown when keeping)
        info_frame = QFrame()
        info_frame.setObjectName(f"{staff_type}_info_frame")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 8, 8, 8)

        # Name and archetype
        name_label = QLabel(f"[{title} Name]")
        name_label.setObjectName(f"{staff_type}_name")
        name_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        info_layout.addWidget(name_label)

        archetype_label = QLabel("Archetype: --")
        archetype_label.setObjectName(f"{staff_type}_archetype")
        archetype_label.setStyleSheet("color: #666;")
        info_layout.addWidget(archetype_label)

        tenure_label = QLabel("Tenure: -- seasons")
        tenure_label.setObjectName(f"{staff_type}_tenure")
        tenure_label.setStyleSheet("color: #666;")
        info_layout.addWidget(tenure_label)

        history_label = QLabel("")
        history_label.setObjectName(f"{staff_type}_history")
        history_label.setStyleSheet("color: #555; font-style: italic;")
        history_label.setWordWrap(True)
        info_layout.addWidget(history_label)

        layout.addWidget(info_frame)

        # Action buttons
        btn_layout = QHBoxLayout()

        keep_btn = QPushButton(f"Keep {title.split()[0]}")
        keep_btn.setObjectName(f"{staff_type}_keep_btn")
        keep_btn.setStyleSheet(UITheme.button_style("primary"))
        keep_btn.clicked.connect(lambda: self._on_keep_staff(staff_type))
        btn_layout.addWidget(keep_btn)

        fire_btn = QPushButton(f"Fire {title.split()[0]}")
        fire_btn.setObjectName(f"{staff_type}_fire_btn")
        fire_btn.setStyleSheet(UITheme.button_style("danger"))
        fire_btn.clicked.connect(lambda: self._on_fire_staff(staff_type))
        btn_layout.addWidget(fire_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Candidates table (hidden initially)
        candidates_frame = QFrame()
        candidates_frame.setObjectName(f"{staff_type}_candidates_frame")
        candidates_frame.setVisible(False)
        candidates_layout = QVBoxLayout(candidates_frame)

        candidates_label = QLabel(f"Select New {title}:")
        candidates_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        candidates_layout.addWidget(candidates_label)

        candidates_table = QTableWidget()
        candidates_table.setObjectName(f"{staff_type}_candidates_table")
        candidates_table.setColumnCount(4)
        candidates_table.setHorizontalHeaderLabels(["Name", "Archetype", "History", "Action"])
        candidates_table.horizontalHeader().setStyleSheet(TABLE_HEADER_STYLE)
        candidates_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        candidates_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        candidates_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        candidates_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        candidates_table.horizontalHeader().resizeSection(3, 80)
        candidates_table.verticalHeader().setVisible(False)
        candidates_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        candidates_table.setMaximumHeight(200)
        candidates_layout.addWidget(candidates_table)

        layout.addWidget(candidates_frame)

        # Status label
        status_label = QLabel("")
        status_label.setObjectName(f"{staff_type}_status")
        status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(status_label)

        return group

    def _on_keep_staff(self, staff_type: str):
        """Handle keeping current staff member."""
        if staff_type == "gm":
            self._is_gm_fired = False
            self._gm_candidates = []
            self._selected_gm_id = None
        else:
            self._is_hc_fired = False
            self._hc_candidates = []
            self._selected_hc_id = None

        self._update_staff_ui(staff_type)
        self._update_flow_guidance()

    def _on_fire_staff(self, staff_type: str):
        """Handle firing staff member."""
        if staff_type == "gm":
            self._is_gm_fired = True
            self.gm_fired.emit()
        else:
            self._is_hc_fired = True
            self.hc_fired.emit()
        self._update_flow_guidance()

    def _on_hire_candidate(self, staff_type: str, candidate_id: str):
        """Handle hiring a candidate."""
        if staff_type == "gm":
            self._selected_gm_id = candidate_id
            self.gm_hired.emit(candidate_id)
        else:
            self._selected_hc_id = candidate_id
            self.hc_hired.emit(candidate_id)
        self._update_staff_ui(staff_type)
        self._update_flow_guidance()

    def _update_staff_ui(self, staff_type: str):
        """Update UI for staff section based on current state."""
        is_fired = self._is_gm_fired if staff_type == "gm" else self._is_hc_fired
        candidates = self._gm_candidates if staff_type == "gm" else self._hc_candidates
        selected_id = self._selected_gm_id if staff_type == "gm" else self._selected_hc_id

        # Get widgets
        info_frame = self._staff_tab.findChild(QFrame, f"{staff_type}_info_frame")
        candidates_frame = self._staff_tab.findChild(QFrame, f"{staff_type}_candidates_frame")
        keep_btn = self._staff_tab.findChild(QPushButton, f"{staff_type}_keep_btn")
        fire_btn = self._staff_tab.findChild(QPushButton, f"{staff_type}_fire_btn")
        status_label = self._staff_tab.findChild(QLabel, f"{staff_type}_status")

        if is_fired and not selected_id:
            # Show candidates, hide info
            info_frame.setVisible(False)
            candidates_frame.setVisible(True)
            keep_btn.setEnabled(True)
            fire_btn.setEnabled(False)
            status_label.setText("Select a replacement from the candidates below")
            status_label.setStyleSheet("color: #F57C00; font-weight: bold;")

            # Populate candidates table
            self._populate_candidates_table(staff_type, candidates)

        elif selected_id:
            # Show selected candidate info
            selected = next((c for c in candidates if c.get("staff_id") == selected_id), None)
            if selected:
                self._update_staff_info(staff_type, selected)
            info_frame.setVisible(True)
            candidates_frame.setVisible(False)
            keep_btn.setEnabled(False)
            fire_btn.setEnabled(True)
            status_label.setText("New hire selected")
            status_label.setStyleSheet("color: #2E7D32; font-weight: bold;")

        else:
            # Show current staff (keeping)
            info_frame.setVisible(True)
            candidates_frame.setVisible(False)
            keep_btn.setEnabled(False)
            fire_btn.setEnabled(True)
            status_label.setText("Keeping current staff")
            status_label.setStyleSheet("color: #2E7D32; font-weight: bold;")

    def _populate_candidates_table(self, staff_type: str, candidates: List[Dict]):
        """Populate the candidates table."""
        table = self._staff_tab.findChild(QTableWidget, f"{staff_type}_candidates_table")
        table.setRowCount(len(candidates))

        for row, candidate in enumerate(candidates):
            # Name
            name_item = QTableWidgetItem(candidate.get("name", "Unknown"))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, name_item)

            # Archetype
            archetype = candidate.get("archetype_key", "balanced")
            archetype_display = archetype.replace("_", " ").title()
            archetype_item = QTableWidgetItem(archetype_display)
            archetype_item.setFlags(archetype_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 1, archetype_item)

            # History
            history = candidate.get("history", "")
            history_item = QTableWidgetItem(history[:80] + "..." if len(history) > 80 else history)
            history_item.setToolTip(history)
            history_item.setFlags(history_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 2, history_item)

            # Hire button
            hire_btn = QPushButton("Hire")
            hire_btn.setStyleSheet(UITheme.button_style("primary"))
            candidate_id = candidate.get("staff_id", "")
            hire_btn.clicked.connect(
                lambda checked, st=staff_type, cid=candidate_id: self._on_hire_candidate(st, cid)
            )
            table.setCellWidget(row, 3, hire_btn)

    def _update_staff_info(self, staff_type: str, staff_data: Dict):
        """Update staff info display."""
        name_label = self._staff_tab.findChild(QLabel, f"{staff_type}_name")
        archetype_label = self._staff_tab.findChild(QLabel, f"{staff_type}_archetype")
        tenure_label = self._staff_tab.findChild(QLabel, f"{staff_type}_tenure")
        history_label = self._staff_tab.findChild(QLabel, f"{staff_type}_history")

        name = staff_data.get("name", "Unknown")
        archetype = staff_data.get("archetype_key", "balanced")
        hire_season = staff_data.get("hire_season", 0)
        history = staff_data.get("history", "")

        name_label.setText(name)
        archetype_label.setText(f"Archetype: {archetype.replace('_', ' ').title()}")

        # Calculate tenure
        if self._season_summary and hire_season:
            current_season = self._season_summary.get("season", 0)
            tenure = current_season - hire_season + 1
            tenure_label.setText(f"Tenure: {tenure} season{'s' if tenure != 1 else ''}")
        else:
            tenure_label.setText("Tenure: 1 season")

        history_label.setText(history)

    # ==================== Tab 3: Strategic Direction ====================

    def _create_strategy_tab(self) -> QWidget:
        """Create the strategic direction tab with fixed footer."""
        # Container for scroll area + fixed footer
        container = QWidget()
        container.setStyleSheet("background-color: #ffffff;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: #ffffff;")

        widget = QWidget()
        widget.setStyleSheet("background-color: #ffffff;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Common group box style
        group_style = """
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #f9f9f9;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #333333;
            }
            QLabel {
                color: #333333;
            }
            QComboBox, QSpinBox, QLineEdit {
                color: #333333;
                background-color: #ffffff;
                border: 1px solid #cccccc;
                padding: 4px;
            }
        """

        # Win Target
        target_group = QGroupBox("Win Target")
        target_group.setStyleSheet(group_style)
        target_layout = QHBoxLayout(target_group)

        target_label = QLabel("Target wins for next season:")
        target_layout.addWidget(target_label)

        self._win_target_spin = QSpinBox()
        self._win_target_spin.setRange(0, 17)
        self._win_target_spin.setValue(8)
        self._win_target_spin.setFixedWidth(80)
        target_layout.addWidget(self._win_target_spin)

        target_layout.addStretch()
        layout.addWidget(target_group)

        # Priority Positions
        priority_group = QGroupBox("Priority Positions")
        priority_group.setStyleSheet(group_style)
        priority_layout = QVBoxLayout(priority_group)

        priority_desc = QLabel("Select up to 5 positions to prioritize in free agency and draft:")
        priority_desc.setStyleSheet("color: #555555;")
        priority_layout.addWidget(priority_desc)

        positions_layout = QHBoxLayout()
        self._priority_combos: List[QComboBox] = []

        for i in range(5):
            combo = QComboBox()
            combo.addItems(POSITION_OPTIONS)
            combo.setFixedWidth(100)
            positions_layout.addWidget(combo)
            self._priority_combos.append(combo)

        positions_layout.addStretch()
        priority_layout.addLayout(positions_layout)
        layout.addWidget(priority_group)

        # Draft Strategy
        draft_group = QGroupBox("Draft Strategy")
        draft_group.setStyleSheet(group_style)
        draft_layout = QVBoxLayout(draft_group)

        self._draft_strategy_combo = QComboBox()
        for value, display in DRAFT_STRATEGIES:
            self._draft_strategy_combo.addItem(display, value)
        draft_layout.addWidget(self._draft_strategy_combo)

        layout.addWidget(draft_group)

        # FA Philosophy
        fa_group = QGroupBox("Free Agency Philosophy")
        fa_group.setStyleSheet(group_style)
        fa_layout = QVBoxLayout(fa_group)

        self._fa_philosophy_combo = QComboBox()
        for value, display in FA_PHILOSOPHIES:
            self._fa_philosophy_combo.addItem(display, value)
        fa_layout.addWidget(self._fa_philosophy_combo)

        layout.addWidget(fa_group)

        # Wishlists
        wishlist_group = QGroupBox("Player Wishlists")
        wishlist_group.setStyleSheet(group_style)
        wishlist_layout = QGridLayout(wishlist_group)

        # FA Wishlist
        wishlist_layout.addWidget(QLabel("Free Agency Targets:"), 0, 0)
        self._fa_wishlist_edit = QLineEdit()
        self._fa_wishlist_edit.setPlaceholderText("Enter player names separated by commas")
        wishlist_layout.addWidget(self._fa_wishlist_edit, 0, 1)

        # Draft Wishlist
        wishlist_layout.addWidget(QLabel("Draft Targets:"), 1, 0)
        self._draft_wishlist_edit = QLineEdit()
        self._draft_wishlist_edit.setPlaceholderText("Enter prospect names separated by commas")
        wishlist_layout.addWidget(self._draft_wishlist_edit, 1, 1)

        layout.addWidget(wishlist_group)

        # Contract Limits
        contract_group = QGroupBox("Contract Limits")
        contract_group.setStyleSheet(group_style)
        contract_layout = QGridLayout(contract_group)

        # Max years
        contract_layout.addWidget(QLabel("Maximum Contract Years:"), 0, 0)
        self._max_years_spin = QSpinBox()
        self._max_years_spin.setRange(1, 7)
        self._max_years_spin.setValue(5)
        self._max_years_spin.setFixedWidth(80)
        contract_layout.addWidget(self._max_years_spin, 0, 1)

        # Max guaranteed %
        contract_layout.addWidget(QLabel("Maximum Guaranteed %:"), 1, 0)
        self._max_guaranteed_spin = QSpinBox()
        self._max_guaranteed_spin.setRange(0, 100)
        self._max_guaranteed_spin.setValue(75)
        self._max_guaranteed_spin.setSuffix("%")
        self._max_guaranteed_spin.setFixedWidth(100)
        contract_layout.addWidget(self._max_guaranteed_spin, 1, 1)

        contract_layout.setColumnStretch(2, 1)
        layout.addWidget(contract_group)

        layout.addStretch()

        # Set scroll content
        scroll.setWidget(widget)
        container_layout.addWidget(scroll, stretch=1)

        # Fixed footer with Save button (always visible)
        footer = QFrame()
        footer.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-top: 1px solid #cccccc;
            }
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 12, 16, 12)
        footer_layout.addStretch()

        self._save_directives_btn = QPushButton("Save Directives")
        self._save_directives_btn.setStyleSheet(UITheme.button_style("primary"))
        self._save_directives_btn.clicked.connect(self._on_save_directives)
        footer_layout.addWidget(self._save_directives_btn)

        container_layout.addWidget(footer)

        return container

    def _on_save_directives(self):
        """Handle save directives button click."""
        # Collect priority positions (filter out "None")
        priorities = []
        for combo in self._priority_combos:
            pos = combo.currentText()
            if pos != "None" and pos not in priorities:
                priorities.append(pos)

        # Parse wishlists
        fa_wishlist = [
            name.strip()
            for name in self._fa_wishlist_edit.text().split(",")
            if name.strip()
        ]
        draft_wishlist = [
            name.strip()
            for name in self._draft_wishlist_edit.text().split(",")
            if name.strip()
        ]

        directives = {
            "target_wins": self._win_target_spin.value(),
            "priority_positions": priorities,
            "draft_strategy": self._draft_strategy_combo.currentData(),
            "fa_philosophy": self._fa_philosophy_combo.currentData(),
            "fa_wishlist": fa_wishlist,
            "draft_wishlist": draft_wishlist,
            "max_contract_years": self._max_years_spin.value(),
            "max_guaranteed_percent": self._max_guaranteed_spin.value() / 100.0,
        }

        # Mark directives as saved and update flow guidance
        self._directives_saved = True
        self._update_flow_guidance()

        self.directives_saved.emit(directives)

    # ==================== Continue Button ====================

    def _create_continue_button(self, layout: QVBoxLayout):
        """Create the continue button."""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._continue_btn = QPushButton("Continue to Franchise Tag")
        self._continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border-radius: 4px;
                padding: 12px 32px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
        """)
        self._continue_btn.clicked.connect(self._on_continue)
        btn_layout.addWidget(self._continue_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_continue(self):
        """Handle continue button click."""
        self.continue_clicked.emit()

    # ==================== Public API ====================

    def set_current_staff(self, staff: Dict[str, Any]):
        """
        Set the current GM and HC data.

        Args:
            staff: Dict with 'gm' and 'hc' keys containing staff data
        """
        self._current_staff = staff
        self._is_gm_fired = False
        self._is_hc_fired = False
        self._selected_gm_id = None
        self._selected_hc_id = None
        self._gm_candidates = []
        self._hc_candidates = []

        if staff:
            gm_data = staff.get("gm", {})
            hc_data = staff.get("hc", {})
            self._update_staff_info("gm", gm_data)
            self._update_staff_info("hc", hc_data)

        self._update_staff_ui("gm")
        self._update_staff_ui("hc")

    def set_gm_candidates(self, candidates: List[Dict[str, Any]]):
        """
        Set GM candidate pool after firing.

        Args:
            candidates: List of candidate dicts from StaffGeneratorService
        """
        self._gm_candidates = candidates
        self._update_staff_ui("gm")

    def set_hc_candidates(self, candidates: List[Dict[str, Any]]):
        """
        Set HC candidate pool after firing.

        Args:
            candidates: List of candidate dicts from StaffGeneratorService
        """
        self._hc_candidates = candidates
        self._update_staff_ui("hc")

    def set_season_summary(self, summary: Dict[str, Any]):
        """
        Set the season summary data.

        Args:
            summary: Dict with season, target_wins, wins, losses
        """
        self._season_summary = summary

        season = summary.get("season", "--")
        wins = summary.get("wins")
        losses = summary.get("losses")
        target = summary.get("target_wins")

        self._season_label.setText(str(season))

        if wins is not None and losses is not None:
            self._record_label.setText(f"{wins} - {losses}")

            if target is not None:
                self._target_label.setText(f"{target} wins")

                # Determine if expectations met
                if wins >= target:
                    self._expectations_label.setText("Met")
                    self._expectations_label.setStyleSheet(
                        "color: #2E7D32; font-weight: bold; font-size: 18px;"
                    )
                else:
                    self._expectations_label.setText("Not Met")
                    self._expectations_label.setStyleSheet(
                        "color: #C62828; font-weight: bold; font-size: 18px;"
                    )
            else:
                self._target_label.setText("Not set")
                self._expectations_label.setText("N/A")
                self._expectations_label.setStyleSheet(
                    "color: #666; font-size: 18px;"
                )
        else:
            self._record_label.setText("-- - --")
            self._target_label.setText("--")
            self._expectations_label.setText("--")

    def set_directives(self, directives: Optional[Dict[str, Any]]):
        """
        Set existing directives data to populate form.

        Args:
            directives: Dict with directive fields, or None
        """
        if not directives:
            return

        # Win target
        self._win_target_spin.setValue(directives.get("target_wins", 8) or 8)

        # Priority positions
        positions = directives.get("priority_positions", []) or []
        for i, combo in enumerate(self._priority_combos):
            if i < len(positions):
                idx = combo.findText(positions[i])
                combo.setCurrentIndex(idx if idx >= 0 else 0)
            else:
                combo.setCurrentIndex(0)

        # Draft strategy
        strategy = directives.get("draft_strategy", "balanced")
        for i in range(self._draft_strategy_combo.count()):
            if self._draft_strategy_combo.itemData(i) == strategy:
                self._draft_strategy_combo.setCurrentIndex(i)
                break

        # FA philosophy
        philosophy = directives.get("fa_philosophy", "balanced")
        for i in range(self._fa_philosophy_combo.count()):
            if self._fa_philosophy_combo.itemData(i) == philosophy:
                self._fa_philosophy_combo.setCurrentIndex(i)
                break

        # Wishlists
        fa_wishlist = directives.get("fa_wishlist", []) or []
        self._fa_wishlist_edit.setText(", ".join(fa_wishlist))

        draft_wishlist = directives.get("draft_wishlist", []) or []
        self._draft_wishlist_edit.setText(", ".join(draft_wishlist))

        # Contract limits
        self._max_years_spin.setValue(directives.get("max_contract_years", 5) or 5)
        guaranteed = directives.get("max_guaranteed_percent", 0.75) or 0.75
        self._max_guaranteed_spin.setValue(int(guaranteed * 100))

    # ==================== Flow Guidance ====================

    def _on_tab_changed(self, index: int):
        """Handle tab change to track visits and update completion state."""
        if index == 0:  # Season Summary tab
            self._summary_reviewed = True
        self._update_flow_guidance()

    def _on_banner_action_clicked(self):
        """Handle clicking the action button in the banner."""
        # Determine which tab to switch to based on current state
        if not self._summary_reviewed:
            self._tab_widget.setCurrentIndex(0)
        elif not self._staff_decisions_complete:
            self._tab_widget.setCurrentIndex(1)
        elif not self._directives_saved:
            self._tab_widget.setCurrentIndex(2)

    def _check_staff_decisions_complete(self) -> bool:
        """Check if both GM and HC decisions have been made."""
        # GM decision: either keeping (not fired) or hired a replacement
        gm_decided = not self._is_gm_fired or self._selected_gm_id is not None
        # HC decision: either keeping (not fired) or hired a replacement
        hc_decided = not self._is_hc_fired or self._selected_hc_id is not None
        return gm_decided and hc_decided

    def _update_flow_guidance(self):
        """Update the action banner, tab titles, and continue button based on completion state."""
        # Update staff decisions state
        self._staff_decisions_complete = self._check_staff_decisions_complete()

        # Determine current step and what action is needed
        all_complete = self._summary_reviewed and self._staff_decisions_complete and self._directives_saved

        # Update tab titles with completion indicators
        tab_titles = [
            ("Season Summary", self._summary_reviewed),
            ("Staff Decisions", self._staff_decisions_complete),
            ("Strategic Direction", self._directives_saved),
        ]

        for i, (title, is_complete) in enumerate(tab_titles):
            if is_complete:
                indicator = "\u2713"  # Checkmark
                self._tab_widget.setTabText(i, f"{indicator} {title}")
            elif i == 1 and self._is_gm_fired and not self._selected_gm_id:
                # Staff tab needs action (GM not yet hired)
                self._tab_widget.setTabText(i, f"! {title}")
            elif i == 1 and self._is_hc_fired and not self._selected_hc_id:
                # Staff tab needs action (HC not yet hired)
                self._tab_widget.setTabText(i, f"! {title}")
            else:
                self._tab_widget.setTabText(i, title)

        # Update action banner
        if all_complete:
            # All done - green success banner
            self._action_banner.setStyleSheet("""
                QFrame#action_banner {
                    background-color: #E8F5E9;
                    border: 1px solid #4CAF50;
                    border-radius: 6px;
                }
            """)
            self._banner_icon.setText("\u2713")
            self._banner_icon.setStyleSheet("color: #2E7D32; font-size: 16px; font-weight: bold;")
            self._banner_text.setText("All set! You've completed all owner decisions. Click Continue to proceed.")
            self._banner_text.setStyleSheet("color: #2E7D32;")
            self._banner_action_btn.setVisible(False)

        elif not self._summary_reviewed:
            # Step 1: Review season summary
            self._action_banner.setStyleSheet("""
                QFrame#action_banner {
                    background-color: #FFF3E0;
                    border: 1px solid #FF9800;
                    border-radius: 6px;
                }
            """)
            self._banner_icon.setText("1")
            self._banner_icon.setStyleSheet("""
                color: white;
                background-color: #FF9800;
                border-radius: 10px;
                font-size: 12px;
                font-weight: bold;
                padding: 2px 6px;
            """)
            self._banner_text.setText("Step 1 of 3: Review your team's season performance before making decisions.")
            self._banner_text.setStyleSheet("color: #E65100;")
            self._banner_action_btn.setText("View Summary")
            self._banner_action_btn.setStyleSheet(UITheme.button_style("warning"))
            self._banner_action_btn.setVisible(True)

        elif not self._staff_decisions_complete:
            # Step 2: Make staff decisions
            self._action_banner.setStyleSheet("""
                QFrame#action_banner {
                    background-color: #FFF3E0;
                    border: 1px solid #FF9800;
                    border-radius: 6px;
                }
            """)
            self._banner_icon.setText("2")
            self._banner_icon.setStyleSheet("""
                color: white;
                background-color: #FF9800;
                border-radius: 10px;
                font-size: 12px;
                font-weight: bold;
                padding: 2px 6px;
            """)

            # Specific message based on what's missing
            if self._is_gm_fired and not self._selected_gm_id:
                msg = "Step 2 of 3: You fired the GM - select a replacement before continuing."
            elif self._is_hc_fired and not self._selected_hc_id:
                msg = "Step 2 of 3: You fired the Head Coach - select a replacement before continuing."
            else:
                msg = "Step 2 of 3: Decide whether to keep or replace your GM and Head Coach."

            self._banner_text.setText(msg)
            self._banner_text.setStyleSheet("color: #E65100;")
            self._banner_action_btn.setText("Staff Decisions")
            self._banner_action_btn.setStyleSheet(UITheme.button_style("warning"))
            self._banner_action_btn.setVisible(True)

        elif not self._directives_saved:
            # Step 3: Set strategic direction
            self._action_banner.setStyleSheet("""
                QFrame#action_banner {
                    background-color: #FFF3E0;
                    border: 1px solid #FF9800;
                    border-radius: 6px;
                }
            """)
            self._banner_icon.setText("3")
            self._banner_icon.setStyleSheet("""
                color: white;
                background-color: #FF9800;
                border-radius: 10px;
                font-size: 12px;
                font-weight: bold;
                padding: 2px 6px;
            """)
            self._banner_text.setText("Step 3 of 3: Set your strategic direction for the upcoming season, then save.")
            self._banner_text.setStyleSheet("color: #E65100;")
            self._banner_action_btn.setText("Set Direction")
            self._banner_action_btn.setStyleSheet(UITheme.button_style("warning"))
            self._banner_action_btn.setVisible(True)

        # Update continue button state
        if all_complete:
            self._continue_btn.setEnabled(True)
            self._continue_btn.setText("Continue to Franchise Tag")
            self._continue_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1976D2;
                    color: white;
                    border-radius: 4px;
                    padding: 12px 32px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1565C0;
                }
            """)
        else:
            self._continue_btn.setEnabled(False)
            # Show what's missing
            missing = []
            if not self._summary_reviewed:
                missing.append("review summary")
            if not self._staff_decisions_complete:
                missing.append("staff decisions")
            if not self._directives_saved:
                missing.append("save directives")

            self._continue_btn.setText(f"Complete: {', '.join(missing)}")
            self._continue_btn.setStyleSheet("""
                QPushButton {
                    background-color: #BDBDBD;
                    color: #757575;
                    border-radius: 4px;
                    padding: 12px 32px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)

    def refresh(self):
        """Refresh the view with current data."""
        # Reset state
        self._is_gm_fired = False
        self._is_hc_fired = False
        self._selected_gm_id = None
        self._selected_hc_id = None
        self._gm_candidates = []
        self._hc_candidates = []

        # Reset completion tracking
        self._summary_reviewed = False
        self._staff_decisions_complete = False
        self._directives_saved = False

        # Update UI
        self._update_staff_ui("gm")
        self._update_staff_ui("hc")

        # Update flow guidance
        self._update_flow_guidance()

        # Reset to first tab
        self._tab_widget.setCurrentIndex(0)
