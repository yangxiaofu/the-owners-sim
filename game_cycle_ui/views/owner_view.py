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
    QPushButton, QFrame, QTabWidget, QStackedWidget, QSpinBox, QComboBox,
    QLineEdit, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal

from game_cycle_ui.theme import (
    UITheme, Colors, TAB_STYLE, Typography, FontSizes, TextColors, apply_table_style,
    ESPN_THEME, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, DANGER_BUTTON_STYLE
)
from game_cycle_ui.widgets import (
    PerformanceSummaryWidget, TransactionsSectionWidget, StaffPerformanceWidget,
    CapSummaryCompactWidget
)
from game_cycle_ui.widgets.owner_flow_guidance import OwnerFlowGuidance, FlowState
from game_cycle_ui.models import StaffState


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
    ("needs_based", "Needs-Based - Focus on roster holes"),
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
    - Step 1: Season Review - Record vs. expectations + Staff Decisions (GM/HC keep/fire/hire)
    - Step 2: Strategic Direction - Directives for GM

    Sequential wizard flow with Back/Next/Continue navigation buttons.

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
        self._season_summary: Optional[Dict[str, Any]] = None

        # Staff state (consolidated from 6 scattered variables)
        self._staff_state = {
            "gm": StaffState(),
            "hc": StaffState()
        }

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

        # Stacked widget for wizard steps (create before header for flow guidance)
        self._stacked_widget = QStackedWidget()

        # Keep reference to tab widget for backward compatibility with flow guidance
        # (will be removed in future cleanup)
        self._tab_widget = QTabWidget()  # Dummy for now
        self._tab_widget.setStyleSheet(TAB_STYLE)

        # Header
        self._create_header(layout)

        # Step 1: Season Review (combines performance summary + staff decisions)
        self._review_step = self._create_comprehensive_review_tab()
        self._stacked_widget.addWidget(self._review_step)

        # Step 2: Strategic Direction
        self._strategy_step = self._create_strategy_tab()
        self._stacked_widget.addWidget(self._strategy_step)

        layout.addWidget(self._stacked_widget, stretch=1)

        # Navigation footer with Back/Next/Continue buttons
        self._create_navigation_footer(layout)

        # Initialize flow guidance
        self._update_flow_guidance()

    def _create_header(self, layout: QVBoxLayout):
        """Create the header section."""
        header = QLabel("Owner Review")
        header.setFont(Typography.H1)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"color: {Colors.INFO};")
        layout.addWidget(header)

        subtitle = QLabel("Review performance and set direction for the upcoming season")
        subtitle.setFont(Typography.BODY)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {Colors.MUTED};")
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
        self._banner_text.setFont(Typography.CAPTION)
        self._banner_text.setWordWrap(True)
        banner_layout.addWidget(self._banner_text, stretch=1)

        self._banner_action_btn = QPushButton()
        self._banner_action_btn.setFixedWidth(120)
        self._banner_action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._banner_action_btn.clicked.connect(self._on_banner_action_clicked)
        banner_layout.addWidget(self._banner_action_btn)

        layout.addWidget(self._action_banner)

        # Initialize flow guidance manager (manages banner and tab title state)
        self._flow_guidance = OwnerFlowGuidance(
            banner=self._action_banner,
            banner_icon=self._banner_icon,
            banner_text=self._banner_text,
            action_btn=self._banner_action_btn,
            tab_widget=self._tab_widget
        )

    # ==================== Tab 1: Season Review (Comprehensive) ====================

    def _create_comprehensive_review_tab(self) -> QWidget:
        """
        Create the comprehensive season review tab.

        2-column ESPN-style layout:
        - Left (60%): Performance Summary + Transactions Section
        - Right (40%): Staff Performance (GM and HC cards)

        Wrapped in scroll area for overflow content.
        """
        # Create scrollable content widget
        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {ESPN_THEME['dark_bg']};")

        main_layout = QHBoxLayout(content_widget)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ======== LEFT COLUMN (60%) ========
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setSpacing(12)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Performance Summary widget (~250px)
        self._performance_widget = PerformanceSummaryWidget()
        left_layout.addWidget(self._performance_widget)

        # Transactions Section widget (~450px scrollable)
        self._transactions_widget = TransactionsSectionWidget()
        left_layout.addWidget(self._transactions_widget)

        left_layout.addStretch()  # Push to top
        main_layout.addWidget(left_column, 60)  # 60% width

        # ======== RIGHT COLUMN (40%) ========
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setSpacing(12)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Salary Cap Summary (~90px)
        self._cap_widget = CapSummaryCompactWidget()
        right_layout.addWidget(self._cap_widget)

        # Staff Performance widget (~410px with minimum heights)
        self._staff_widget = StaffPerformanceWidget()
        self._staff_widget.gm_fired.connect(lambda: self._on_fire_staff("gm"))
        self._staff_widget.hc_fired.connect(lambda: self._on_fire_staff("hc"))
        right_layout.addWidget(self._staff_widget)

        right_layout.addStretch()  # Push to top
        main_layout.addWidget(right_column, 40)  # 40% width

        # Wrap in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content_widget)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background-color: {ESPN_THEME['dark_bg']}; border: none; }}
            QScrollBar:vertical {{ width: 8px; background: {ESPN_THEME['dark_bg']}; }}
            QScrollBar::handle:vertical {{ background: #444; border-radius: 4px; }}
        """)

        return scroll

    def _on_fire_staff(self, staff_type: str):
        """Handle firing staff member."""
        self._staff_state[staff_type].fire()

        if staff_type == "gm":
            self.gm_fired.emit()
        else:
            self.hc_fired.emit()

        self._update_flow_guidance()


    # ==================== Tab 3: Strategic Direction ====================

    def _create_strategy_tab(self) -> QWidget:
        """Create the strategic direction tab with fixed footer."""
        # Container for scroll area + fixed footer
        container = QWidget()
        container.setStyleSheet(f"background-color: {ESPN_THEME['dark_bg']};")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background-color: {ESPN_THEME['dark_bg']}; border: none; }}
            QScrollBar:vertical {{ width: 8px; background: {ESPN_THEME['dark_bg']}; }}
            QScrollBar::handle:vertical {{ background: #444; border-radius: 4px; }}
        """)

        widget = QWidget()
        widget.setStyleSheet(f"background-color: {ESPN_THEME['dark_bg']};")
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Common group box style for dark theme
        group_style = f"""
            QGroupBox {{
                font-weight: bold;
                font-size: {FontSizes.H5};
                color: {ESPN_THEME['text_primary']};
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: {ESPN_THEME['card_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: {ESPN_THEME['text_primary']};
            }}
            QLabel {{
                color: {ESPN_THEME['text_primary']};
            }}
            QComboBox {{
                color: {ESPN_THEME['text_primary']};
                background-color: #2a2a2a;
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 3px;
                padding: 6px 8px;
            }}
            QComboBox:hover {{
                border-color: #555555;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #2a2a2a;
                color: {ESPN_THEME['text_primary']};
                selection-background-color: #3a3a3a;
                border: 1px solid {ESPN_THEME['border']};
            }}
            QSpinBox {{
                color: {ESPN_THEME['text_primary']};
                background-color: #2a2a2a;
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 3px;
                padding: 6px 8px;
            }}
            QSpinBox:hover {{
                border-color: #555555;
            }}
            QLineEdit {{
                color: {ESPN_THEME['text_primary']};
                background-color: #2a2a2a;
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 3px;
                padding: 6px 8px;
            }}
            QLineEdit:hover {{
                border-color: #555555;
            }}
            QLineEdit:focus {{
                border-color: {Colors.INFO};
            }}
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
        priority_desc.setStyleSheet(f"color: {ESPN_THEME['text_secondary']};")
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

        # Note: Save button removed - navigation footer handles saving via "Save & Complete"

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

    def _create_navigation_footer(self, layout: QVBoxLayout):
        """Create navigation footer with Back/Next/Continue buttons."""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.setContentsMargins(0, 12, 0, 0)

        # Back button
        self._back_btn = QPushButton("\u2190 Back")
        self._back_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self._back_btn.setFixedWidth(120)
        self._back_btn.clicked.connect(self._on_back_clicked)
        btn_layout.addWidget(self._back_btn)

        btn_layout.addStretch()

        # Next button (changes text based on step)
        self._next_btn = QPushButton("Next: Strategic Direction \u2192")
        self._next_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.INFO};
                color: white;
                border-radius: 4px;
                padding: 12px 24px;
                font-size: {FontSizes.H5};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #1565C0;
            }}
            QPushButton:disabled {{
                background-color: #444444;
                color: {ESPN_THEME['text_muted']};
            }}
        """)
        self._next_btn.clicked.connect(self._on_next_clicked)
        btn_layout.addWidget(self._next_btn)

        btn_layout.addStretch()

        # Continue button (shown after Step 2 is complete)
        self._continue_btn = QPushButton("Continue to Franchise Tag")
        self._continue_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border-radius: 4px;
                padding: 12px 32px;
                font-size: {FontSizes.H5};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2E7D32;
            }}
        """)
        self._continue_btn.clicked.connect(self._on_continue)
        self._continue_btn.setVisible(False)  # Initially hidden
        btn_layout.addWidget(self._continue_btn)

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
        self._staff_state["gm"].reset()
        self._staff_state["hc"].reset()

        if staff:
            gm_data = staff.get("gm", {})
            hc_data = staff.get("hc", {})

            # Update new staff widget
            if hasattr(self, '_staff_widget'):
                # Convert staff data to widget format
                gm_widget_data = {
                    'name': gm_data.get('name', 'Unknown GM'),
                    'contract_year': gm_data.get('contract_year', 1),
                    'contract_total_years': gm_data.get('contract_years', 4),
                    'salary': gm_data.get('salary', 3_500_000),
                    'archetype': gm_data.get('archetype_key', 'Unknown'),
                    'draft_grade': 'N/A',  # Placeholder
                    'trade_success_rate': 0.0,  # Placeholder
                    'fa_hit_rate': 0.0  # Placeholder
                }
                hc_widget_data = {
                    'name': hc_data.get('name', 'Unknown HC'),
                    'contract_year': hc_data.get('contract_year', 1),
                    'contract_total_years': hc_data.get('contract_years', 5),
                    'salary': hc_data.get('salary', 5_200_000),
                    'archetype': hc_data.get('archetype_key', 'Unknown'),
                    'win_pct': 0.0,  # Placeholder
                    'ppg_for': 0.0,  # Placeholder
                    'ppg_against': 0.0,  # Placeholder
                    'player_dev': 0.0  # Placeholder
                }
                self._staff_widget.set_gm_data(gm_widget_data)
                self._staff_widget.set_hc_data(hc_widget_data)

        # Update flow guidance after staff changes
        if hasattr(self, '_flow_guidance'):
            self._update_flow_guidance()

    def set_gm_candidates(self, candidates: List[Dict[str, Any]]):
        """
        Set GM candidate pool after firing.

        Args:
            candidates: List of candidate dicts from StaffGeneratorService
        """
        self._staff_state["gm"].candidates = candidates

    def set_hc_candidates(self, candidates: List[Dict[str, Any]]):
        """
        Set HC candidate pool after firing.

        Args:
            candidates: List of candidate dicts from StaffGeneratorService
        """
        self._staff_state["hc"].candidates = candidates

    def set_season_summary(self, summary: Dict[str, Any]):
        """
        Set the season summary data.

        Args:
            summary: Dict with season, target_wins, wins, losses,
                    and optionally playoff_result, priority_positions, etc.
        """
        self._season_summary = summary

        season = summary.get("season", "--")
        wins = summary.get("wins", 0)
        losses = summary.get("losses", 0)
        target = summary.get("target_wins", 10)


        # Update new performance widget
        if hasattr(self, '_performance_widget'):
            performance_data = {
                'wins': wins,
                'losses': losses,
                'target_wins': target,
                'playoff_result': summary.get('playoff_result', 'Did not make playoffs'),
                'playoff_expectation': summary.get('playoff_expectation', 'Miss playoffs'),
                'cap_used': summary.get('cap_used', 0),
                'cap_total': summary.get('cap_total', 255_400_000),
                'priority_positions': summary.get('priority_positions', []),
                'strategy_adherence': summary.get('strategy_adherence', 0.0),
                'strategy_name': summary.get('strategy_name', 'Unknown Strategy')
            }
            self._performance_widget.set_data(performance_data)

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

    def set_transactions(self, transactions: List[Dict[str, Any]]):
        """
        Set the season transactions data for the transactions widget.

        Args:
            transactions: List of transaction dicts with:
                - type: 'trade' | 'fa_signing' | 'draft_pick' | 'cut'
                - timing: str (e.g., 'Week 3', 'March 15', 'Round 1, Pick 18')
                - acquired: str (optional, what was acquired)
                - sent: str (optional, what was sent)
                - impact: str (description of impact on team/goals)
        """
        if hasattr(self, '_transactions_widget'):
            self._transactions_widget.set_transactions(transactions)

    def set_cap_data(self, cap_data: Dict[str, Any]):
        """
        Set the salary cap data for the cap widget.

        Args:
            cap_data: {
                'total_cap': int,
                'cap_used': int,
                'cap_room': int
            }
        """
        if hasattr(self, '_cap_widget'):
            self._cap_widget.set_data(cap_data)

    # ==================== Flow Guidance ====================

    def _on_banner_action_clicked(self):
        """Stub for banner action button (no longer used in wizard flow)."""
        pass

    def _on_back_clicked(self):
        """Handle Back button click - return to Step 1."""
        self._stacked_widget.setCurrentIndex(0)
        self._update_navigation_buttons()
        self._update_flow_guidance()

    def _on_next_clicked(self):
        """Handle Next button click - advance to Step 2 or save directives."""
        current_step = self._stacked_widget.currentIndex() + 1

        if current_step == 1:
            # Advancing from Step 1 to Step 2
            if self._can_proceed_to_step_2():
                self._summary_reviewed = True  # Mark Step 1 as reviewed
                self._stacked_widget.setCurrentIndex(1)
                self._update_navigation_buttons()
                self._update_flow_guidance()
        elif current_step == 2:
            # Save directives on Step 2
            self._on_save_directives()
            # Note: _on_save_directives already updates flow guidance

    def _can_proceed_to_step_2(self) -> bool:
        """Check if user can proceed to Step 2."""
        # Auto-mark as reviewed when advancing (user has seen the content)
        return self._check_staff_decisions_complete()

    def _update_navigation_buttons(self):
        """Update Back/Next/Continue button states based on current step."""
        current_step = self._stacked_widget.currentIndex() + 1

        # Back button - enabled on Step 2
        self._back_btn.setEnabled(current_step == 2)

        # Next button - behavior changes by step
        if current_step == 1:
            self._next_btn.setVisible(True)
            self._next_btn.setEnabled(self._can_proceed_to_step_2())
            self._next_btn.setText("Next: Strategic Direction \u2192")
        elif current_step == 2:
            self._next_btn.setVisible(True)
            self._next_btn.setEnabled(True)
            self._next_btn.setText("Save & Complete")

        # Continue button - show after directives saved on Step 2
        self._continue_btn.setVisible(current_step == 2 and self._directives_saved)

    def _check_staff_decisions_complete(self) -> bool:
        """Check if both GM and HC decisions have been made."""
        return (self._staff_state["gm"].is_decision_complete() and
                self._staff_state["hc"].is_decision_complete())

    def _update_flow_guidance(self):
        """Update the action banner and navigation buttons based on completion state."""
        # Update staff decisions state
        self._staff_decisions_complete = self._check_staff_decisions_complete()

        # Get current wizard step
        current_step = self._stacked_widget.currentIndex() + 1

        # Delegate banner updates to flow guidance manager
        flow_state = FlowState(
            summary_reviewed=self._summary_reviewed,
            staff_decisions_complete=self._staff_decisions_complete,
            directives_saved=self._directives_saved,
            gm_fired_not_hired=self._staff_state["gm"].is_fired and not self._staff_state["gm"].selected_id,
            hc_fired_not_hired=self._staff_state["hc"].is_fired and not self._staff_state["hc"].selected_id,
            current_step=current_step
        )
        self._flow_guidance.update(flow_state)

        # Update navigation button states
        self._update_navigation_buttons()

    def refresh(self):
        """Refresh the view with current data."""
        # Reset staff state
        self._staff_state["gm"].reset()
        self._staff_state["hc"].reset()

        # Reset completion tracking
        self._summary_reviewed = False
        self._staff_decisions_complete = False
        self._directives_saved = False

        # Update UI
        # Note: Staff widgets handle their own updates now via StaffPerformanceWidget

        # Reset to Step 1
        self._stacked_widget.setCurrentIndex(0)

        # Update flow guidance and navigation buttons
        self._update_flow_guidance()
