"""
Staff Performance Widget - Tabbed GM and HC cards with actions.

Shows one staff member at a time with tabs:
- GM tab: Contract information, archetype, performance metrics, Keep/Fire buttons
- HC tab: Contract information, archetype, performance metrics, Keep/Fire buttons
- Scalable for future staff (OC, DC, etc.)
"""

from typing import Dict, Any
import logging
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget
)
from PySide6.QtCore import Signal
from game_cycle_ui.theme import Typography, ESPN_THEME, TextColors, Colors

logger = logging.getLogger(__name__)


class StaffPerformanceWidget(QFrame):
    """
    Tabbed staff performance cards with placeholder metrics.

    Shows: Contract info, archetype, performance stats, Keep/Fire buttons.
    Only one staff card visible at a time (saves vertical space).

    Uses QStackedWidget for proper tab switching without widget deletion/recreation.
    """

    gm_fired = Signal()
    hc_fired = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gm_data = None
        self._hc_data = None

        # Widget references for updates (GM)
        self.gm_name_label = None
        self.gm_contract_label = None
        self.gm_archetype_label = None
        self.gm_draft_label = None
        self.gm_trade_label = None
        self.gm_fa_label = None

        # Widget references for updates (HC)
        self.hc_name_label = None
        self.hc_contract_label = None
        self.hc_archetype_label = None
        self.hc_record_label = None
        self.hc_ppg_for_label = None
        self.hc_ppg_against_label = None
        self.hc_dev_label = None

        self._setup_ui()

    def _setup_ui(self):
        """Build the tabbed widget layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        # Section header
        header = QLabel("STAFF DECISIONS")
        header.setFont(Typography.TINY_BOLD)
        header.setStyleSheet(f"color: {TextColors.ON_DARK_DISABLED};")
        layout.addWidget(header)

        # Tab buttons row
        tab_row = QHBoxLayout()
        tab_row.setSpacing(4)

        self.gm_tab_btn = QPushButton("GM")
        self.hc_tab_btn = QPushButton("HC")

        # Style tabs (ESPN theme - matches transaction filter buttons)
        for btn in [self.gm_tab_btn, self.hc_tab_btn]:
            btn.setCheckable(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.STAFF_TAB_BACKGROUND};
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 3px;
                    font-weight: normal;
                }}
                QPushButton:checked {{
                    background-color: {Colors.STAFF_TAB_SELECTED};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {Colors.STAFF_CARD_BACKGROUND};
                }}
            """)
            btn.clicked.connect(self._on_tab_changed)
            tab_row.addWidget(btn)

        tab_row.addStretch()  # Push tabs left
        layout.addLayout(tab_row)

        # Stacked widget for GM/HC cards
        self.card_stack = QStackedWidget()
        self.card_stack.setMinimumHeight(180)
        self.card_stack.setStyleSheet(f"""
            QStackedWidget {{
                background-color: {ESPN_THEME['card_hover']};
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 4px;
                padding: 8px;
            }}
        """)

        # Create GM card (page 0)
        self.gm_card = self._create_gm_card()
        self.card_stack.addWidget(self.gm_card)

        # Create HC card (page 1)
        self.hc_card = self._create_hc_card()
        self.card_stack.addWidget(self.hc_card)

        layout.addWidget(self.card_stack)

        # Default to GM tab
        self.gm_tab_btn.setChecked(True)
        self.card_stack.setCurrentIndex(0)

        # Section styling
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet(f"""
            StaffPerformanceWidget {{
                background-color: {ESPN_THEME['card_bg']};
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 6px;
            }}
        """)

    def _create_gm_card(self) -> QWidget:
        """Create GM card widget with all UI elements."""
        card = QWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        self.gm_name_label = QLabel("GENERAL MANAGER: Unknown")
        self.gm_name_label.setFont(Typography.BODY)
        self.gm_name_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {Colors.STAFF_HEADER};")
        layout.addWidget(self.gm_name_label)

        # Contract
        self.gm_contract_label = QLabel("Contract: Year 1 of 4 ($0.0M/yr)")
        self.gm_contract_label.setFont(Typography.SMALL)
        self.gm_contract_label.setStyleSheet(f"color: {Colors.STAFF_CONTRACT_INFO};")
        layout.addWidget(self.gm_contract_label)

        # Archetype
        self.gm_archetype_label = QLabel("Archetype: Unknown")
        self.gm_archetype_label.setFont(Typography.SMALL)
        self.gm_archetype_label.setStyleSheet(f"color: {Colors.STAFF_CONTRACT_INFO};")
        layout.addWidget(self.gm_archetype_label)

        layout.addSpacing(8)

        # Performance metrics (placeholder)
        perf_header = QLabel("GM Performance (Placeholder):")
        perf_header.setFont(Typography.SMALL)
        perf_header.setStyleSheet("font-weight: bold; color: #ccc;")
        layout.addWidget(perf_header)

        self.gm_draft_label = QLabel("• Draft Grade: N/A")
        self.gm_trade_label = QLabel("• Trade Success: 0%")
        self.gm_fa_label = QLabel("• FA Hit Rate: 0%")

        for lbl in [self.gm_draft_label, self.gm_trade_label, self.gm_fa_label]:
            lbl.setFont(Typography.SMALL)
            lbl.setStyleSheet(f"color: {Colors.STAFF_PERFORMANCE_METRIC};")
            layout.addWidget(lbl)

        layout.addSpacing(8)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        keep_btn = QPushButton("Keep GM")
        keep_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.STAFF_KEEP_BUTTON};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.STAFF_KEEP_BUTTON_HOVER};
            }}
        """)

        fire_btn = QPushButton("Fire GM")
        fire_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.STAFF_FIRE_BUTTON};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {Colors.STAFF_FIRE_BUTTON_HOVER};
            }}
        """)
        fire_btn.clicked.connect(self.gm_fired.emit)

        btn_row.addWidget(keep_btn)
        btn_row.addWidget(fire_btn)
        btn_row.addStretch()

        layout.addLayout(btn_row)
        layout.addStretch()  # Push content to top

        return card

    def _create_hc_card(self) -> QWidget:
        """Create HC card widget with all UI elements."""
        card = QWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        self.hc_name_label = QLabel("HEAD COACH: Unknown")
        self.hc_name_label.setFont(Typography.BODY)
        self.hc_name_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {Colors.STAFF_HEADER};")
        layout.addWidget(self.hc_name_label)

        # Contract
        self.hc_contract_label = QLabel("Contract: Year 1 of 5 ($0.0M/yr)")
        self.hc_contract_label.setFont(Typography.SMALL)
        self.hc_contract_label.setStyleSheet(f"color: {Colors.STAFF_CONTRACT_INFO};")
        layout.addWidget(self.hc_contract_label)

        # Archetype
        self.hc_archetype_label = QLabel("Archetype: Unknown")
        self.hc_archetype_label.setFont(Typography.SMALL)
        self.hc_archetype_label.setStyleSheet(f"color: {Colors.STAFF_CONTRACT_INFO};")
        layout.addWidget(self.hc_archetype_label)

        layout.addSpacing(8)

        # Performance metrics (placeholder)
        perf_header = QLabel("HC Measurables (Placeholder):")
        perf_header.setFont(Typography.SMALL)
        perf_header.setStyleSheet("font-weight: bold; color: #ccc;")
        layout.addWidget(perf_header)

        self.hc_record_label = QLabel("• Win %: 0.000")
        self.hc_ppg_for_label = QLabel("• Points For: 0.0 ppg")
        self.hc_ppg_against_label = QLabel("• Points Against: 0.0 ppg")
        self.hc_dev_label = QLabel("• Player Development: +0.0 avg OVR improvement")

        for lbl in [self.hc_record_label, self.hc_ppg_for_label, self.hc_ppg_against_label, self.hc_dev_label]:
            lbl.setFont(Typography.SMALL)
            lbl.setStyleSheet(f"color: {Colors.STAFF_PERFORMANCE_METRIC};")
            layout.addWidget(lbl)

        layout.addSpacing(8)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        keep_btn = QPushButton("Keep HC")
        keep_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.STAFF_KEEP_BUTTON};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.STAFF_KEEP_BUTTON_HOVER};
            }}
        """)

        fire_btn = QPushButton("Fire HC")
        fire_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.STAFF_FIRE_BUTTON};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {Colors.STAFF_FIRE_BUTTON_HOVER};
            }}
        """)
        fire_btn.clicked.connect(self.hc_fired.emit)

        btn_row.addWidget(keep_btn)
        btn_row.addWidget(fire_btn)
        btn_row.addStretch()

        layout.addLayout(btn_row)
        layout.addStretch()  # Push content to top

        return card

    def _on_tab_changed(self):
        """Handle tab button clicks - switch displayed staff."""
        # Uncheck all tabs except sender
        sender = self.sender()
        for btn in [self.gm_tab_btn, self.hc_tab_btn]:
            if btn != sender:
                btn.setChecked(False)

        # Ensure sender is checked
        sender.setChecked(True)

        # Switch visible card using QStackedWidget
        if sender == self.gm_tab_btn:
            self.card_stack.setCurrentIndex(0)  # Show GM card
        elif sender == self.hc_tab_btn:
            self.card_stack.setCurrentIndex(1)  # Show HC card

    def set_gm_data(self, gm_data: Dict[str, Any]):
        """
        Store GM data and update GM card widgets.

        Args:
            gm_data: {
                'name': str,
                'contract_year': int,
                'contract_total_years': int,
                'salary': int,
                'archetype': str,
                'draft_grade': str,  # Placeholder
                'trade_success_rate': float,  # Placeholder
                'fa_hit_rate': float  # Placeholder
            }

        Raises:
            TypeError: If gm_data is not a dictionary
            ValueError: If data types are incorrect
        """
        try:
            # Type validation
            if not isinstance(gm_data, dict):
                raise TypeError(f"gm_data must be a dict, got {type(gm_data).__name__}")

            self._gm_data = gm_data

            # Update GM card widgets (with safe type conversions)
            name = str(gm_data.get('name', 'Unknown GM'))
            self.gm_name_label.setText(f"GENERAL MANAGER: {name}")

            contract_year = int(gm_data.get('contract_year', 1))
            contract_total = int(gm_data.get('contract_total_years', 4))
            salary = int(gm_data.get('salary', 0))
            self.gm_contract_label.setText(
                f"Contract: Year {contract_year} of {contract_total} "
                f"(${salary/1e6:.1f}M/yr)"
            )

            archetype_key = str(gm_data.get('archetype', 'Unknown'))
            archetype_display = archetype_key.replace('_', ' ').title() if archetype_key != 'Unknown' else 'Unknown'
            self.gm_archetype_label.setText(f"Archetype: {archetype_display}")

            draft_grade = gm_data.get('draft_grade', 'N/A')
            trade_success = float(gm_data.get('trade_success_rate', 0.0))
            fa_hit = float(gm_data.get('fa_hit_rate', 0.0))

            self.gm_draft_label.setText(f"• Draft Grade: {draft_grade}")
            self.gm_trade_label.setText(f"• Trade Success: {int(trade_success*100)}%")
            self.gm_fa_label.setText(f"• FA Hit Rate: {int(fa_hit*100)}%")

        except (ValueError, TypeError) as e:
            logger.error(f"Failed to set GM data: {e}")
            # Show error state in UI
            self.gm_name_label.setText("GENERAL MANAGER: Error loading data")
            self.gm_name_label.setStyleSheet(f"color: {TextColors.ERROR};")
            self.gm_contract_label.setText("Contract: Error")
            self.gm_archetype_label.setText("Archetype: Error")

    def set_hc_data(self, hc_data: Dict[str, Any]):
        """
        Store HC data and update HC card widgets.

        Args:
            hc_data: {
                'name': str,
                'contract_year': int,
                'contract_total_years': int,
                'salary': int,
                'archetype': str,
                'win_pct': float,  # Placeholder
                'ppg_for': float,  # Placeholder
                'ppg_against': float,  # Placeholder
                'player_dev': float  # Placeholder
            }

        Raises:
            TypeError: If hc_data is not a dictionary
            ValueError: If data types are incorrect
        """
        try:
            # Type validation
            if not isinstance(hc_data, dict):
                raise TypeError(f"hc_data must be a dict, got {type(hc_data).__name__}")

            self._hc_data = hc_data

            # Update HC card widgets (with safe type conversions)
            name = str(hc_data.get('name', 'Unknown HC'))
            self.hc_name_label.setText(f"HEAD COACH: {name}")

            contract_year = int(hc_data.get('contract_year', 1))
            contract_total = int(hc_data.get('contract_total_years', 5))
            salary = int(hc_data.get('salary', 0))
            self.hc_contract_label.setText(
                f"Contract: Year {contract_year} of {contract_total} "
                f"(${salary/1e6:.1f}M/yr)"
            )

            archetype_key = str(hc_data.get('archetype', 'Unknown'))
            archetype_display = archetype_key.replace('_', ' ').title() if archetype_key != 'Unknown' else 'Unknown'
            self.hc_archetype_label.setText(f"Archetype: {archetype_display}")

            win_pct = float(hc_data.get('win_pct', 0.0))
            ppg_for = float(hc_data.get('ppg_for', 0.0))
            ppg_against = float(hc_data.get('ppg_against', 0.0))
            player_dev = float(hc_data.get('player_dev', 0.0))

            self.hc_record_label.setText(f"• Win %: {win_pct:.3f}")
            self.hc_ppg_for_label.setText(f"• Points For: {ppg_for:.1f} ppg")
            self.hc_ppg_against_label.setText(f"• Points Against: {ppg_against:.1f} ppg")
            self.hc_dev_label.setText(f"• Player Development: +{player_dev:.1f} avg OVR improvement")

        except (ValueError, TypeError) as e:
            logger.error(f"Failed to set HC data: {e}")
            # Show error state in UI
            self.hc_name_label.setText("HEAD COACH: Error loading data")
            self.hc_name_label.setStyleSheet(f"color: {TextColors.ERROR};")
            self.hc_contract_label.setText("Contract: Error")
            self.hc_archetype_label.setText("Archetype: Error")
