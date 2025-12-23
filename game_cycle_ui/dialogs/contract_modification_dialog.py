"""
Contract Modification Dialog - Allows owner to modify GM proposal terms.

Part of Tollgate 6: Free Agency Depth milestone.

Design Philosophy:
- Owner is NOT making direct offers to players
- Owner is modifying the GM's proposed terms before approval
- GM will then submit the modified offer on owner's behalf

UI Components:
- Player info header (read-only)
- Market value reference from valuation engine
- Contract modification sliders (years, AAV, guaranteed %)
- Live acceptance probability and cap impact
- Approve with Changes / Cancel buttons
"""

from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QPushButton,
    QGroupBox,
    QProgressBar,
    QFrame,
    QWidget,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from game_cycle_ui.theme import (
    Typography,
    FontSizes,
    Colors,
    PRIMARY_BUTTON_STYLE,
    NEUTRAL_BUTTON_STYLE,
)
from constants.position_abbreviations import get_position_abbreviation


@dataclass
class ModifiedContractTerms:
    """Contract terms after owner modification."""

    aav: int
    years: int
    guaranteed: int
    signing_bonus: int

    @property
    def total_value(self) -> int:
        """Total contract value (AAV × years)."""
        return self.aav * self.years

    @property
    def guaranteed_pct(self) -> float:
        """Guaranteed percentage of total value."""
        if self.total_value <= 0:
            return 0.0
        return self.guaranteed / self.total_value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for signal emission."""
        return {
            "aav": self.aav,
            "years": self.years,
            "guaranteed": self.guaranteed,
            "signing_bonus": self.signing_bonus,
            "total_value": self.total_value,
            "guaranteed_pct": self.guaranteed_pct,
        }


class ContractModificationDialog(QDialog):
    """
    Dialog for owner to modify GM's proposed contract terms.

    Displays player info and market reference, allows adjustment of:
    - Years (1-5)
    - AAV (70%-150% of market value)
    - Guaranteed % (30%-100% of total)

    Shows live updates of:
    - Total contract value
    - Year 1 cap hit
    - Cap space after signing
    - Acceptance probability

    Signals:
        terms_modified: Emits (proposal_id, ModifiedContractTerms) when approved
    """

    terms_modified = Signal(str, object)  # proposal_id, ModifiedContractTerms

    # Constants for slider ranges
    MIN_AAV_PCT = 70   # 70% of market
    MAX_AAV_PCT = 150  # 150% of market
    MIN_YEARS = 1
    MAX_YEARS = 5
    MIN_GTD_PCT = 30   # 30% guaranteed
    MAX_GTD_PCT = 100  # 100% guaranteed

    def __init__(
        self,
        proposal_data: Dict[str, Any],
        market_aav: int,
        cap_space: int,
        acceptance_prob_callback: Optional[Callable[[int, int, int], float]] = None,
        parent: Optional[QWidget] = None,
    ):
        """
        Initialize contract modification dialog.

        Args:
            proposal_data: Original GM proposal dict with:
                - proposal_id: str
                - details: dict with player_name, position, age, overall_rating,
                           contract (years, aav, guaranteed)
                - gm_reasoning: str
            market_aav: Market value AAV from valuation engine
            cap_space: Current available cap space
            acceptance_prob_callback: Optional function(aav, years, gtd) -> probability
            parent: Parent widget
        """
        super().__init__(parent)

        self._proposal_id = proposal_data.get("proposal_id", "")
        self._details = proposal_data.get("details", {})
        self._contract = self._details.get("contract", {})
        self._market_aav = max(1_000_000, market_aav)  # Minimum $1M
        self._cap_space = cap_space
        self._acceptance_callback = acceptance_prob_callback

        # Original values from GM proposal
        self._original_aav = self._contract.get("aav", self._market_aav)
        self._original_years = self._contract.get("years", 3)
        self._original_gtd = self._contract.get("guaranteed", 0)
        self._original_bonus = self._contract.get("signing_bonus", 0)

        # Calculate original guaranteed %
        original_total = self._original_aav * self._original_years
        if original_total > 0:
            self._original_gtd_pct = int(self._original_gtd / original_total * 100)
        else:
            self._original_gtd_pct = 50

        # Calculate original AAV as % of market
        self._original_aav_pct = int(self._original_aav / self._market_aav * 100)
        self._original_aav_pct = max(self.MIN_AAV_PCT, min(self.MAX_AAV_PCT, self._original_aav_pct))

        self._setup_ui()
        self._connect_signals()
        self._update_all_displays()

    def _setup_ui(self):
        """Build the dialog UI."""
        self.setWindowTitle("Modify Contract Terms")
        self.setMinimumSize(550, 600)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Header with player info
        layout.addWidget(self._create_player_header())

        # 2. GM's original proposal (read-only reference)
        layout.addWidget(self._create_original_proposal_section())

        # 3. Contract modification controls
        layout.addWidget(self._create_modification_section())

        # 4. Live impact display
        layout.addWidget(self._create_impact_section())

        layout.addStretch()

        # 5. Action buttons
        layout.addLayout(self._create_buttons())

    def _create_player_header(self) -> QWidget:
        """Create player info header section."""
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #263238; border-radius: 6px; padding: 12px; }"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)

        # Player name and position
        player_name = self._details.get("player_name", "Unknown")
        position = self._details.get("position", "")
        pos_abbrev = get_position_abbreviation(position)

        name_label = QLabel(f"{player_name}")
        name_label.setFont(Typography.H4)
        name_label.setStyleSheet("color: white;")
        layout.addWidget(name_label)

        # Position, Age, OVR row
        info_layout = QHBoxLayout()
        info_layout.setSpacing(20)

        pos_label = QLabel(f"Position: {pos_abbrev}")
        pos_label.setFont(Typography.BODY)
        pos_label.setStyleSheet("color: #B0BEC5;")
        info_layout.addWidget(pos_label)

        age = self._details.get("age", 0)
        age_label = QLabel(f"Age: {age}")
        age_label.setFont(Typography.BODY)
        age_color = "#FF8A65" if age >= 30 else "#B0BEC5"
        age_label.setStyleSheet(f"color: {age_color};")
        info_layout.addWidget(age_label)

        overall = self._details.get("overall_rating", 0)
        ovr_label = QLabel(f"Overall: {overall}")
        ovr_label.setFont(Typography.BODY)
        ovr_color = "#4CAF50" if overall >= 85 else "#2196F3" if overall >= 75 else "#B0BEC5"
        ovr_label.setStyleSheet(f"color: {ovr_color};")
        info_layout.addWidget(ovr_label)

        info_layout.addStretch()

        # Market value
        market_label = QLabel(f"Market AAV: ${self._market_aav:,}")
        market_label.setFont(Typography.BODY_BOLD)
        market_label.setStyleSheet("color: #FFD54F;")
        info_layout.addWidget(market_label)

        layout.addLayout(info_layout)

        return frame

    def _create_original_proposal_section(self) -> QGroupBox:
        """Create section showing GM's original proposal."""
        group = QGroupBox("GM's Original Proposal")
        group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 1px solid #444; "
            "border-radius: 4px; margin-top: 8px; padding-top: 8px; color: #B0BEC5; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }"
        )
        layout = QHBoxLayout(group)
        layout.setSpacing(30)

        # AAV
        aav_frame = self._create_info_item("AAV", f"${self._original_aav:,}")
        layout.addWidget(aav_frame)

        # Years
        years_frame = self._create_info_item("Years", str(self._original_years))
        layout.addWidget(years_frame)

        # Total Value
        total = self._original_aav * self._original_years
        total_frame = self._create_info_item("Total", f"${total:,}")
        layout.addWidget(total_frame)

        # Guaranteed
        gtd_frame = self._create_info_item(
            "Guaranteed",
            f"${self._original_gtd:,} ({self._original_gtd_pct}%)"
        )
        layout.addWidget(gtd_frame)

        layout.addStretch()

        return group

    def _create_info_item(self, title: str, value: str) -> QWidget:
        """Create a title/value pair display."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setFont(Typography.SMALL)
        title_label.setStyleSheet("color: #78909C;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setFont(Typography.BODY_BOLD)
        value_label.setStyleSheet("color: white;")
        layout.addWidget(value_label)

        return widget

    def _create_modification_section(self) -> QGroupBox:
        """Create contract modification controls."""
        group = QGroupBox("Your Modifications")
        group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 1px solid #1976D2; "
            "border-radius: 4px; margin-top: 8px; padding-top: 12px; color: #1976D2; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }"
        )
        layout = QVBoxLayout(group)
        layout.setSpacing(16)

        # Years slider
        years_row = self._create_slider_row(
            "Contract Length",
            f"{self._original_years} years",
            self.MIN_YEARS,
            self.MAX_YEARS,
            self._original_years,
        )
        self._years_slider = years_row["slider"]
        self._years_value_label = years_row["value_label"]
        layout.addWidget(years_row["widget"])

        # AAV slider (as % of market)
        aav_row = self._create_slider_row(
            "AAV (% of Market)",
            f"{self._original_aav_pct}% (${self._original_aav:,})",
            self.MIN_AAV_PCT,
            self.MAX_AAV_PCT,
            self._original_aav_pct,
        )
        self._aav_slider = aav_row["slider"]
        self._aav_value_label = aav_row["value_label"]
        layout.addWidget(aav_row["widget"])

        # Guaranteed % slider
        gtd_row = self._create_slider_row(
            "Guaranteed %",
            f"{self._original_gtd_pct}%",
            self.MIN_GTD_PCT,
            self.MAX_GTD_PCT,
            self._original_gtd_pct,
        )
        self._gtd_slider = gtd_row["slider"]
        self._gtd_value_label = gtd_row["value_label"]
        layout.addWidget(gtd_row["widget"])

        return group

    def _create_slider_row(
        self,
        title: str,
        initial_value: str,
        min_val: int,
        max_val: int,
        current_val: int,
    ) -> Dict[str, Any]:
        """Create a labeled slider row."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Title label (fixed width)
        title_label = QLabel(title)
        title_label.setFont(Typography.BODY)
        title_label.setStyleSheet("color: #CFD8DC;")
        title_label.setFixedWidth(130)
        layout.addWidget(title_label)

        # Slider
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(current_val)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval((max_val - min_val) // 5)
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #37474F;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1976D2;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #2196F3;
            }
            QSlider::sub-page:horizontal {
                background: #1976D2;
                border-radius: 4px;
            }
        """)
        layout.addWidget(slider, stretch=1)

        # Value label (fixed width, right-aligned)
        value_label = QLabel(initial_value)
        value_label.setFont(Typography.BODY_BOLD)
        value_label.setStyleSheet("color: #4CAF50;")
        value_label.setFixedWidth(150)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(value_label)

        return {
            "widget": widget,
            "slider": slider,
            "value_label": value_label,
        }

    def _create_impact_section(self) -> QGroupBox:
        """Create live impact display section."""
        group = QGroupBox("Contract Impact")
        group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 1px solid #444; "
            "border-radius: 4px; margin-top: 8px; padding-top: 12px; color: #B0BEC5; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }"
        )
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Row 1: Total Value, Year 1 Cap Hit
        row1 = QHBoxLayout()

        self._total_value_label = QLabel("Total Value: $0")
        self._total_value_label.setFont(Typography.BODY_BOLD)
        self._total_value_label.setStyleSheet("color: white;")
        row1.addWidget(self._total_value_label)

        row1.addStretch()

        self._cap_hit_label = QLabel("Year 1 Cap Hit: $0")
        self._cap_hit_label.setFont(Typography.BODY_BOLD)
        self._cap_hit_label.setStyleSheet("color: white;")
        row1.addWidget(self._cap_hit_label)

        layout.addLayout(row1)

        # Row 2: Guaranteed Amount, Cap Space After
        row2 = QHBoxLayout()

        self._gtd_amount_label = QLabel("Guaranteed: $0")
        self._gtd_amount_label.setFont(Typography.BODY)
        self._gtd_amount_label.setStyleSheet("color: #B0BEC5;")
        row2.addWidget(self._gtd_amount_label)

        row2.addStretch()

        self._cap_after_label = QLabel("Cap After: $0")
        self._cap_after_label.setFont(Typography.BODY)
        self._cap_after_label.setStyleSheet("color: #B0BEC5;")
        row2.addWidget(self._cap_after_label)

        layout.addLayout(row2)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #444;")
        layout.addWidget(sep)

        # Acceptance Probability
        prob_layout = QHBoxLayout()

        prob_title = QLabel("Acceptance Probability:")
        prob_title.setFont(Typography.BODY_BOLD)
        prob_title.setStyleSheet("color: #B0BEC5;")
        prob_layout.addWidget(prob_title)

        self._prob_bar = QProgressBar()
        self._prob_bar.setRange(0, 100)
        self._prob_bar.setValue(50)
        self._prob_bar.setTextVisible(True)
        self._prob_bar.setFormat("%v%")
        self._prob_bar.setFixedHeight(24)
        self._prob_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                background-color: #1a1a1a;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #2196F3);
                border-radius: 3px;
            }
        """)
        prob_layout.addWidget(self._prob_bar, stretch=1)

        layout.addLayout(prob_layout)

        # Warning label (hidden by default)
        self._warning_label = QLabel("")
        self._warning_label.setWordWrap(True)
        self._warning_label.setFont(Typography.SMALL)
        self._warning_label.setStyleSheet("color: #FF8A65; padding: 4px;")
        self._warning_label.hide()
        layout.addWidget(self._warning_label)

        return group

    def _create_buttons(self) -> QHBoxLayout:
        """Create action buttons."""
        layout = QHBoxLayout()
        layout.addStretch()

        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFont(Typography.BODY)
        cancel_btn.setStyleSheet(NEUTRAL_BUTTON_STYLE)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        layout.addSpacing(12)

        # Approve with Changes button
        self._approve_btn = QPushButton("Approve with Changes")
        self._approve_btn.setFont(Typography.BODY_BOLD)
        self._approve_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "border-radius: 4px; padding: 12px 24px; font-weight: bold; }"
            "QPushButton:hover { background-color: #66BB6A; }"
            "QPushButton:disabled { background-color: #666; color: #999; }"
        )
        self._approve_btn.clicked.connect(self._on_approve)
        layout.addWidget(self._approve_btn)

        return layout

    def _connect_signals(self):
        """Connect slider signals to update displays."""
        self._years_slider.valueChanged.connect(self._on_slider_changed)
        self._aav_slider.valueChanged.connect(self._on_slider_changed)
        self._gtd_slider.valueChanged.connect(self._on_slider_changed)

    def _on_slider_changed(self, value: int):
        """Handle any slider value change."""
        self._update_all_displays()

    def _update_all_displays(self):
        """Update all display labels based on current slider values."""
        years = self._years_slider.value()
        aav_pct = self._aav_slider.value()
        gtd_pct = self._gtd_slider.value()

        # Calculate actual values
        aav = int(self._market_aav * aav_pct / 100)
        total_value = aav * years
        guaranteed = int(total_value * gtd_pct / 100)

        # Signing bonus = 30% of guaranteed (same as GM proposal logic)
        signing_bonus = int(guaranteed * 0.30)

        # Year 1 cap hit = AAV + prorated bonus
        # Simplified: year1_hit = AAV (bonus spread over contract years)
        year1_cap_hit = aav + (signing_bonus // years) if years > 0 else aav

        # Cap after signing
        cap_after = self._cap_space - year1_cap_hit

        # Update value labels
        self._years_value_label.setText(f"{years} year{'s' if years != 1 else ''}")
        self._aav_value_label.setText(f"{aav_pct}% (${aav:,})")
        self._gtd_value_label.setText(f"{gtd_pct}%")

        # Update impact labels
        self._total_value_label.setText(f"Total Value: ${total_value:,}")
        self._cap_hit_label.setText(f"Year 1 Cap Hit: ${year1_cap_hit:,}")
        self._gtd_amount_label.setText(f"Guaranteed: ${guaranteed:,}")

        # Cap after styling
        if cap_after < 0:
            self._cap_after_label.setText(f"Cap After: -${abs(cap_after):,}")
            self._cap_after_label.setStyleSheet("color: #F44336; font-weight: bold;")
            self._warning_label.setText("⚠ This signing would put you over the cap!")
            self._warning_label.show()
            self._approve_btn.setEnabled(False)
        elif cap_after < 5_000_000:
            self._cap_after_label.setText(f"Cap After: ${cap_after:,}")
            self._cap_after_label.setStyleSheet("color: #FF9800; font-weight: bold;")
            self._warning_label.setText("⚠ Low remaining cap space - proceed with caution.")
            self._warning_label.show()
            self._approve_btn.setEnabled(True)
        else:
            self._cap_after_label.setText(f"Cap After: ${cap_after:,}")
            self._cap_after_label.setStyleSheet("color: #4CAF50;")
            self._warning_label.hide()
            self._approve_btn.setEnabled(True)

        # Calculate acceptance probability
        if self._acceptance_callback:
            try:
                prob = self._acceptance_callback(aav, years, guaranteed)
                prob_pct = int(prob * 100)
            except Exception:
                prob_pct = 50
        else:
            # Default calculation based on offer vs market
            offer_vs_market = aav / self._market_aav
            if offer_vs_market >= 1.20:
                prob_pct = 95
            elif offer_vs_market >= 1.10:
                prob_pct = 80
            elif offer_vs_market >= 1.0:
                prob_pct = 65
            elif offer_vs_market >= 0.90:
                prob_pct = 45
            else:
                prob_pct = 25

        self._prob_bar.setValue(prob_pct)

        # Color code probability bar
        if prob_pct >= 70:
            chunk_color = "#4CAF50"  # Green
        elif prob_pct >= 50:
            chunk_color = "#2196F3"  # Blue
        elif prob_pct >= 30:
            chunk_color = "#FF9800"  # Orange
        else:
            chunk_color = "#F44336"  # Red

        self._prob_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #444;
                border-radius: 4px;
                background-color: #1a1a1a;
                text-align: center;
                color: white;
            }}
            QProgressBar::chunk {{
                background-color: {chunk_color};
                border-radius: 3px;
            }}
        """)

    def _on_approve(self):
        """Handle Approve with Changes button click."""
        years = self._years_slider.value()
        aav_pct = self._aav_slider.value()
        gtd_pct = self._gtd_slider.value()

        # Calculate actual values
        aav = int(self._market_aav * aav_pct / 100)
        total_value = aav * years
        guaranteed = int(total_value * gtd_pct / 100)
        signing_bonus = int(guaranteed * 0.30)

        # Create modified terms
        modified = ModifiedContractTerms(
            aav=aav,
            years=years,
            guaranteed=guaranteed,
            signing_bonus=signing_bonus,
        )

        # Emit signal and close
        self.terms_modified.emit(self._proposal_id, modified)
        self.accept()

    def get_modified_terms(self) -> ModifiedContractTerms:
        """Get the current modified contract terms."""
        years = self._years_slider.value()
        aav_pct = self._aav_slider.value()
        gtd_pct = self._gtd_slider.value()

        aav = int(self._market_aav * aav_pct / 100)
        total_value = aav * years
        guaranteed = int(total_value * gtd_pct / 100)
        signing_bonus = int(guaranteed * 0.30)

        return ModifiedContractTerms(
            aav=aav,
            years=years,
            guaranteed=guaranteed,
            signing_bonus=signing_bonus,
        )