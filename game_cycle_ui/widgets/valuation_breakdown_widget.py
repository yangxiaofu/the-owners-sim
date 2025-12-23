"""
Valuation Breakdown Widget - Displays contract valuation transparency.

Shows GM style, pressure level, factor contributions, and detailed breakdowns
for how contract values were calculated by the ContractValuationEngine.

Usage:
    from game_cycle_ui.widgets import ValuationBreakdownWidget

    widget = ValuationBreakdownWidget()
    widget.set_valuation_result(result)

Part of Tollgate 9: Contract Valuation UI Integration.
"""

from typing import Dict, Any, Optional, List

from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QToolButton, QProgressBar, QGridLayout
)
from PySide6.QtCore import Qt, Signal

from game_cycle_ui.theme import (
    Typography, Colors, FontSizes, TextColors, ESPN_THEME
)
from game_cycle_ui.widgets.stat_frame import StatFrame


# =============================================================================
# FACTOR COLORS - Consistent color scheme for valuation factors
# =============================================================================

FACTOR_COLORS = {
    "stats_based": "#2196F3",    # Blue - data-driven
    "scouting": "#4CAF50",       # Green - eye test
    "market": "#FF9800",         # Orange - market rates
    "rating": "#9E9E9E",         # Gray - baseline rating
    "age": "#9C27B0",            # Purple - age curve
}

FACTOR_LABELS = {
    "stats_based": "Stats",
    "scouting": "Scouting",
    "market": "Market",
    "rating": "Rating",
    "age": "Age",
}


# =============================================================================
# COLLAPSIBLE SECTION
# =============================================================================

class CollapsibleSection(QFrame):
    """
    Collapsible section with header and expandable content.

    Pattern: QToolButton header toggles visibility of content frame.

    Signals:
        toggled(bool): Emits expanded state when toggled
    """

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        expanded: bool = False,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._expanded = expanded
        self._setup_ui(title)

    def _setup_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header row with toggle button
        self._toggle_btn = QToolButton()
        self._toggle_btn.setArrowType(
            Qt.ArrowType.DownArrow if self._expanded else Qt.ArrowType.RightArrow
        )
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(self._expanded)
        self._toggle_btn.clicked.connect(self._on_toggle)
        self._toggle_btn.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
            }
        """)

        self._title_label = QLabel(title)
        self._title_label.setFont(Typography.CAPTION_BOLD)
        self._title_label.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY};")

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 4, 0, 4)
        header_layout.addWidget(self._toggle_btn)
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()

        header_frame = QFrame()
        header_frame.setLayout(header_layout)
        header_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        header_frame.mousePressEvent = lambda e: self._toggle_btn.click()

        layout.addWidget(header_frame)

        # Content container (toggle visibility)
        self._content_frame = QFrame()
        self._content_layout = QVBoxLayout(self._content_frame)
        self._content_layout.setContentsMargins(20, 4, 0, 8)
        self._content_frame.setVisible(self._expanded)

        layout.addWidget(self._content_frame)

    def _on_toggle(self, checked: bool):
        self._expanded = checked
        self._toggle_btn.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )
        self._content_frame.setVisible(checked)
        self.toggled.emit(checked)

    def content_layout(self) -> QVBoxLayout:
        """Return layout for adding content widgets."""
        return self._content_layout

    def set_expanded(self, expanded: bool):
        """Programmatically expand or collapse the section."""
        if expanded != self._expanded:
            self._toggle_btn.setChecked(expanded)
            self._on_toggle(expanded)

    def is_expanded(self) -> bool:
        """Return current expanded state."""
        return self._expanded


# =============================================================================
# GM STYLE BADGE
# =============================================================================

class GMStyleBadge(QFrame):
    """
    Badge showing GM valuation style with icon and description.

    Styles: analytics_heavy, scout_focused, balanced, market_driven
    """

    STYLE_CONFIGS = {
        "analytics_heavy": {
            "icon": "📊",
            "color": Colors.INFO,
            "label": "Analytics-Heavy"
        },
        "scout_focused": {
            "icon": "👁",
            "color": Colors.SUCCESS,
            "label": "Scout-Focused"
        },
        "balanced": {
            "icon": "⚖️",
            "color": Colors.MUTED,
            "label": "Balanced"
        },
        "market_driven": {
            "icon": "📈",
            "color": Colors.WARNING,
            "label": "Market-Driven"
        },
        "custom": {
            "icon": "⚙️",
            "color": Colors.MUTED,
            "label": "Custom"
        }
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        self._icon_label = QLabel("")
        self._icon_label.setFont(Typography.BODY)
        layout.addWidget(self._icon_label)

        self._style_label = QLabel("GM Style")
        self._style_label.setFont(Typography.BODY_BOLD)
        layout.addWidget(self._style_label)

        self.setStyleSheet(f"""
            GMStyleBadge {{
                background-color: {ESPN_THEME['card_bg']};
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 4px;
            }}
        """)

    def set_style(self, style_name: str, description: str = ""):
        """
        Set the GM style to display.

        Args:
            style_name: Style identifier (e.g., "analytics_heavy")
            description: Tooltip description
        """
        config = self.STYLE_CONFIGS.get(style_name, self.STYLE_CONFIGS["balanced"])

        self._icon_label.setText(config["icon"])
        self._style_label.setText(config["label"])
        self._style_label.setStyleSheet(f"color: {config['color']};")

        if description:
            self.setToolTip(description)


# =============================================================================
# PRESSURE LEVEL INDICATOR
# =============================================================================

class PressureLevelIndicator(QWidget):
    """
    Progress bar showing GM job security pressure level.

    Colors:
    - Green (< 30%): Secure - value-focused deals
    - Blue (30-70%): Normal - standard negotiation
    - Red (> 70%): Hot seat - overpays likely
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header row
        header = QHBoxLayout()
        self._title_label = QLabel("Pressure Level")
        self._title_label.setFont(Typography.CAPTION)
        self._title_label.setStyleSheet(f"color: {Colors.MUTED};")

        self._pct_label = QLabel("0%")
        self._pct_label.setFont(Typography.CAPTION_BOLD)

        header.addWidget(self._title_label)
        header.addStretch()
        header.addWidget(self._pct_label)
        layout.addLayout(header)

        # Progress bar
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(12)
        layout.addWidget(self._bar)

        # Description label
        self._desc_label = QLabel("")
        self._desc_label.setFont(Typography.SMALL)
        self._desc_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
        self._desc_label.setWordWrap(True)
        layout.addWidget(self._desc_label)

    def set_pressure(
        self,
        level: float,
        adjustment_pct: float = 0.0,
        description: str = ""
    ):
        """
        Set pressure level and update display.

        Args:
            level: Pressure level 0.0-1.0
            adjustment_pct: AAV adjustment percentage (e.g., 0.12 = +12%)
            description: Human-readable description
        """
        pct = int(level * 100)
        self._pct_label.setText(f"{pct}%")
        self._bar.setValue(pct)

        # Color based on pressure level
        if level < 0.3:
            color = Colors.SUCCESS
            self._pct_label.setStyleSheet(f"color: {Colors.SUCCESS};")
        elif level < 0.7:
            color = Colors.INFO
            self._pct_label.setStyleSheet(f"color: {Colors.INFO};")
        else:
            color = Colors.ERROR
            self._pct_label.setStyleSheet(f"color: {Colors.ERROR};")

        self._bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #555;
                border-radius: 6px;
                background-color: #1a1a1a;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 5px;
            }}
        """)

        # Show adjustment if non-zero
        if abs(adjustment_pct) > 0.001:
            adj_sign = "+" if adjustment_pct > 0 else ""
            adj_text = f"{adj_sign}{adjustment_pct * 100:.1f}% AAV adjustment"
            self._desc_label.setText(f"{description} ({adj_text})" if description else adj_text)
        else:
            self._desc_label.setText(description)


# =============================================================================
# FACTOR CONTRIBUTION BAR
# =============================================================================

class FactorContributionBar(QWidget):
    """
    Horizontal stacked bar showing factor contributions.

    Each factor gets a colored segment proportional to its contribution.
    Labels show factor name and dollar amount.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._contributions: Dict[str, int] = {}
        self._total = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Title
        title = QLabel("Factor Contributions")
        title.setFont(Typography.CAPTION_BOLD)
        title.setStyleSheet(f"color: {TextColors.ON_DARK_SECONDARY};")
        layout.addWidget(title)

        # Stacked bar container
        self._bar_frame = QFrame()
        self._bar_frame.setFixedHeight(24)
        self._bar_layout = QHBoxLayout(self._bar_frame)
        self._bar_layout.setContentsMargins(0, 0, 0, 0)
        self._bar_layout.setSpacing(1)
        layout.addWidget(self._bar_frame)

        # Legend
        self._legend_layout = QHBoxLayout()
        self._legend_layout.setSpacing(12)
        layout.addLayout(self._legend_layout)

    def set_contributions(self, contributions: Dict[str, int]):
        """
        Set factor contributions.

        Args:
            contributions: Dict mapping factor name to dollar contribution
        """
        self._contributions = contributions
        self._total = sum(contributions.values()) if contributions else 1
        self._rebuild_bar()

    def _rebuild_bar(self):
        """Rebuild the stacked bar with current contributions."""
        # Clear existing
        while self._bar_layout.count():
            child = self._bar_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        while self._legend_layout.count():
            child = self._legend_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self._contributions:
            return

        # Sort by contribution (largest first)
        sorted_factors = sorted(
            self._contributions.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Build bar segments
        for factor_name, amount in sorted_factors:
            if amount <= 0:
                continue

            pct = amount / self._total
            color = FACTOR_COLORS.get(factor_name, "#607D8B")
            label = FACTOR_LABELS.get(factor_name, factor_name.title())

            # Bar segment
            segment = QFrame()
            segment.setStyleSheet(f"""
                QFrame {{
                    background-color: {color};
                    border-radius: 3px;
                }}
            """)
            self._bar_layout.addWidget(segment, stretch=int(pct * 100))

            # Legend item
            legend_item = QLabel(f"● {label}: ${amount/1e6:.1f}M")
            legend_item.setFont(Typography.SMALL)
            legend_item.setStyleSheet(f"color: {color};")
            self._legend_layout.addWidget(legend_item)

        self._legend_layout.addStretch()


# =============================================================================
# FACTOR DETAIL SECTION
# =============================================================================

class FactorDetailSection(CollapsibleSection):
    """
    Collapsible section showing details for a single factor.

    Shows raw value, confidence, and factor-specific breakdown.
    """

    def __init__(
        self,
        factor_name: str,
        parent: Optional[QWidget] = None
    ):
        self._factor_name = factor_name
        display_name = FACTOR_LABELS.get(factor_name, factor_name.title())
        super().__init__(f"{display_name} Factor Details", expanded=False, parent=parent)

    def set_factor_result(self, name: str, raw_value: int, confidence: float, breakdown: Dict[str, Any]):
        """
        Populate with factor result data.

        Args:
            name: Factor name
            raw_value: Unweighted AAV estimate
            confidence: 0.0-1.0 reliability score
            breakdown: Detailed calculation steps
        """
        layout = self.content_layout()

        # Clear existing content
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Raw value and confidence
        info_layout = QHBoxLayout()

        value_label = QLabel(f"Raw Value: ${raw_value:,}")
        value_label.setFont(Typography.BODY)
        value_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        info_layout.addWidget(value_label)

        conf_pct = int(confidence * 100)
        conf_label = QLabel(f"Confidence: {conf_pct}%")
        conf_label.setFont(Typography.BODY)
        conf_label.setStyleSheet(f"color: {Colors.MUTED};")
        info_layout.addWidget(conf_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Breakdown details (factor-specific)
        if breakdown:
            self._add_breakdown_details(layout, breakdown)

    def _add_breakdown_details(self, layout: QVBoxLayout, breakdown: Dict[str, Any]):
        """Add factor-specific breakdown details."""
        if self._factor_name == "stats_based":
            self._add_stats_breakdown(layout, breakdown)
        elif self._factor_name == "scouting":
            self._add_scouting_breakdown(layout, breakdown)
        elif self._factor_name == "market":
            self._add_market_breakdown(layout, breakdown)
        elif self._factor_name == "rating":
            self._add_rating_breakdown(layout, breakdown)
        elif self._factor_name == "age":
            self._add_age_breakdown(layout, breakdown)
        else:
            self._add_generic_breakdown(layout, breakdown)

    def _add_stats_breakdown(self, layout: QVBoxLayout, breakdown: Dict):
        """Stats factor: percentiles, tier, per-game stats."""
        grid = QGridLayout()
        grid.setSpacing(4)
        row = 0

        tier = breakdown.get("tier", "Unknown")
        label = QLabel("Tier:")
        label.setStyleSheet(f"color: {Colors.MUTED};")
        grid.addWidget(label, row, 0)
        tier_label = QLabel(tier.title())
        tier_label.setStyleSheet(f"color: {Colors.INFO};")
        grid.addWidget(tier_label, row, 1)
        row += 1

        composite = breakdown.get("composite_percentile", 0)
        label = QLabel("Composite Percentile:")
        label.setStyleSheet(f"color: {Colors.MUTED};")
        grid.addWidget(label, row, 0)
        val_label = QLabel(f"{composite:.0f}th")
        val_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        grid.addWidget(val_label, row, 1)
        row += 1

        games = breakdown.get("games_played", 0)
        label = QLabel("Games Played:")
        label.setStyleSheet(f"color: {Colors.MUTED};")
        grid.addWidget(label, row, 0)
        val_label = QLabel(str(games))
        val_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        grid.addWidget(val_label, row, 1)

        layout.addLayout(grid)

    def _add_scouting_breakdown(self, layout: QVBoxLayout, breakdown: Dict):
        """Scouting factor: grades by category."""
        grid = QGridLayout()
        grid.setSpacing(4)
        row = 0

        for key in ["overall", "potential", "physical_grade", "mental_grade", "composite_grade"]:
            value = breakdown.get(key)
            if value is not None:
                display_key = key.replace("_", " ").title()
                label = QLabel(f"{display_key}:")
                label.setStyleSheet(f"color: {Colors.MUTED};")
                grid.addWidget(label, row, 0)

                val_str = f"{value:.0f}" if isinstance(value, (int, float)) else str(value)
                value_label = QLabel(val_str)
                value_label.setStyleSheet(f"color: {Colors.SUCCESS};")
                grid.addWidget(value_label, row, 1)
                row += 1

        layout.addLayout(grid)

    def _add_market_breakdown(self, layout: QVBoxLayout, breakdown: Dict):
        """Market factor: heat, contract year, adjustments."""
        grid = QGridLayout()
        grid.setSpacing(4)
        row = 0

        heat = breakdown.get("market_heat", 1.0)
        label = QLabel("Market Heat:")
        label.setStyleSheet(f"color: {Colors.MUTED};")
        grid.addWidget(label, row, 0)
        heat_label = QLabel(f"{heat:.2f}x")
        heat_color = Colors.SUCCESS if heat > 1.0 else Colors.WARNING if heat < 1.0 else Colors.MUTED
        heat_label.setStyleSheet(f"color: {heat_color};")
        grid.addWidget(heat_label, row, 1)
        row += 1

        contract_year = breakdown.get("contract_year", False)
        if contract_year:
            premium = breakdown.get("contract_year_premium", 1.05)
            label = QLabel("Contract Year:")
            label.setStyleSheet(f"color: {Colors.MUTED};")
            grid.addWidget(label, row, 0)
            val_label = QLabel(f"+{(premium - 1) * 100:.0f}% premium")
            val_label.setStyleSheet(f"color: {Colors.SUCCESS};")
            grid.addWidget(val_label, row, 1)
            row += 1

        rating_adj = breakdown.get("rating_adjustment", 1.0)
        if rating_adj != 1.0:
            label = QLabel("Rating Adj:")
            label.setStyleSheet(f"color: {Colors.MUTED};")
            grid.addWidget(label, row, 0)
            val_label = QLabel(f"{rating_adj:.2f}x")
            val_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
            grid.addWidget(val_label, row, 1)

        layout.addLayout(grid)

    def _add_rating_breakdown(self, layout: QVBoxLayout, breakdown: Dict):
        """Rating factor: tier, scale factor."""
        grid = QGridLayout()
        grid.setSpacing(4)

        tier = breakdown.get("tier", "Unknown")
        label = QLabel("Tier:")
        label.setStyleSheet(f"color: {Colors.MUTED};")
        grid.addWidget(label, 0, 0)
        val_label = QLabel(tier.title())
        val_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        grid.addWidget(val_label, 0, 1)

        scale = breakdown.get("scale_factor", 1.0)
        label = QLabel("Scale Factor:")
        label.setStyleSheet(f"color: {Colors.MUTED};")
        grid.addWidget(label, 1, 0)
        val_label = QLabel(f"{scale:.2f}x")
        val_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        grid.addWidget(val_label, 1, 1)

        layout.addLayout(grid)

    def _add_age_breakdown(self, layout: QVBoxLayout, breakdown: Dict):
        """Age factor: age, modifier, peak window."""
        grid = QGridLayout()
        grid.setSpacing(4)
        row = 0

        age = breakdown.get("age", 0)
        label = QLabel("Age:")
        label.setStyleSheet(f"color: {Colors.MUTED};")
        grid.addWidget(label, row, 0)
        val_label = QLabel(str(age))
        val_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        grid.addWidget(val_label, row, 1)
        row += 1

        modifier = breakdown.get("age_modifier", 1.0)
        label = QLabel("Age Modifier:")
        label.setStyleSheet(f"color: {Colors.MUTED};")
        grid.addWidget(label, row, 0)
        mod_label = QLabel(f"{modifier:.2f}x")
        mod_color = Colors.SUCCESS if modifier >= 1.0 else Colors.WARNING
        mod_label.setStyleSheet(f"color: {mod_color};")
        grid.addWidget(mod_label, row, 1)
        row += 1

        peak_start = breakdown.get("peak_start")
        peak_end = breakdown.get("peak_end")
        if peak_start and peak_end:
            label = QLabel("Peak Window:")
            label.setStyleSheet(f"color: {Colors.MUTED};")
            grid.addWidget(label, row, 0)
            val_label = QLabel(f"{peak_start}-{peak_end}")
            val_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
            grid.addWidget(val_label, row, 1)

        layout.addLayout(grid)

    def _add_generic_breakdown(self, layout: QVBoxLayout, breakdown: Dict):
        """Generic breakdown for unknown factor types."""
        grid = QGridLayout()
        grid.setSpacing(4)
        row = 0

        for key, value in breakdown.items():
            if isinstance(value, (int, float, str, bool)) and not key.startswith("_"):
                display_key = key.replace("_", " ").title()
                label = QLabel(f"{display_key}:")
                label.setStyleSheet(f"color: {Colors.MUTED};")
                grid.addWidget(label, row, 0)

                val_label = QLabel(str(value))
                val_label.setStyleSheet(f"color: {TextColors.ON_DARK};")
                grid.addWidget(val_label, row, 1)
                row += 1

                if row >= 8:  # Limit displayed items
                    break

        layout.addLayout(grid)


# =============================================================================
# MAIN WIDGET: VALUATION BREAKDOWN WIDGET
# =============================================================================

class ValuationBreakdownWidget(QFrame):
    """
    Main widget showing complete contract valuation breakdown.

    Displays:
    1. Contract Summary (always visible)
    2. GM Style + Pressure Level (always visible)
    3. Factor Contributions (collapsible)
    4. Individual Factor Details (collapsible within #3)

    Usage:
        widget = ValuationBreakdownWidget()
        widget.set_valuation_result(result)

        # Or from dict
        widget.set_valuation_data(result.to_dict())
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._factor_detail_sections: List[FactorDetailSection] = []
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet(f"""
            ValuationBreakdownWidget {{
                background-color: {ESPN_THEME['card_bg']};
                border: 1px solid {ESPN_THEME['border']};
                border-radius: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Section 1: Contract Summary (always visible)
        self._summary_section = self._create_summary_section()
        layout.addWidget(self._summary_section)

        # Section 2: GM Style + Pressure (always visible)
        style_pressure_row = QHBoxLayout()

        self._gm_badge = GMStyleBadge()
        style_pressure_row.addWidget(self._gm_badge)

        style_pressure_row.addSpacing(16)

        self._pressure_indicator = PressureLevelIndicator()
        style_pressure_row.addWidget(self._pressure_indicator, stretch=1)

        layout.addLayout(style_pressure_row)

        # Section 3: Factor Contributions (collapsible)
        self._factors_section = CollapsibleSection(
            "Valuation Breakdown", expanded=False
        )
        factors_layout = self._factors_section.content_layout()

        self._contribution_bar = FactorContributionBar()
        factors_layout.addWidget(self._contribution_bar)

        # Section 4: Individual factor details (nested collapsibles)
        self._factor_details_container = QVBoxLayout()
        self._factor_details_container.setSpacing(4)
        factors_layout.addLayout(self._factor_details_container)

        layout.addWidget(self._factors_section)

        # Base AAV comparison
        self._base_aav_label = QLabel("")
        self._base_aav_label.setFont(Typography.SMALL)
        self._base_aav_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
        layout.addWidget(self._base_aav_label)

    def _create_summary_section(self) -> QFrame:
        """Create contract summary with AAV, Years, Guaranteed."""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        self._aav_stat = StatFrame("AAV", "$0")
        layout.addWidget(self._aav_stat)

        self._years_stat = StatFrame("Years", "0")
        layout.addWidget(self._years_stat)

        self._total_stat = StatFrame("Total Value", "$0")
        layout.addWidget(self._total_stat)

        self._guaranteed_stat = StatFrame("Guaranteed", "$0 (0%)")
        layout.addWidget(self._guaranteed_stat)

        layout.addStretch()

        return frame

    def set_valuation_result(self, result) -> None:
        """
        Populate widget from ValuationResult dataclass.

        Args:
            result: Complete ValuationResult from engine
        """
        # Extract data from result
        offer = result.offer

        # Summary section
        self._aav_stat.set_value(f"${offer.aav:,}", Colors.SUCCESS)
        self._years_stat.set_value(f"{offer.years} yr")
        self._total_stat.set_value(f"${offer.total_value:,}")

        gtd_pct = int(offer.guaranteed_pct * 100)
        self._guaranteed_stat.set_value(
            f"${offer.guaranteed:,} ({gtd_pct}%)",
            Colors.INFO
        )

        # GM Style
        self._gm_badge.set_style(result.gm_style, result.gm_style_description)

        # Pressure Level
        self._pressure_indicator.set_pressure(
            result.pressure_level,
            result.pressure_adjustment_pct,
            result.pressure_description
        )

        # Factor contributions
        self._contribution_bar.set_contributions(result.factor_contributions)

        # Individual factor details
        self._populate_factor_details(result.raw_factor_results)

        # Base AAV comparison
        if result.base_aav != offer.aav:
            diff = offer.aav - result.base_aav
            sign = "+" if diff > 0 else ""
            adj_pct = result.pressure_adjustment_pct * 100
            adj_sign = "+" if adj_pct > 0 else ""
            self._base_aav_label.setText(
                f"Base AAV: ${result.base_aav:,} | "
                f"Pressure Adjustment: {sign}${diff:,} ({adj_sign}{adj_pct:.1f}%)"
            )
        else:
            self._base_aav_label.setText(f"Base AAV: ${result.base_aav:,}")

    def set_valuation_data(self, data: Dict[str, Any]) -> None:
        """
        Populate widget from dictionary (e.g., from JSON).

        Args:
            data: Dictionary from ValuationResult.to_dict()
        """
        # Import here to avoid circular imports
        from contract_valuation.models import ValuationResult
        result = ValuationResult.from_dict(data)
        self.set_valuation_result(result)

    def _populate_factor_details(self, factor_results: list):
        """Create collapsible sections for each factor."""
        # Clear existing
        self._factor_detail_sections.clear()
        while self._factor_details_container.count():
            child = self._factor_details_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for result in factor_results:
            section = FactorDetailSection(result.name)
            section.set_factor_result(
                result.name,
                result.raw_value,
                result.confidence,
                result.breakdown
            )
            self._factor_details_container.addWidget(section)
            self._factor_detail_sections.append(section)

    def clear(self):
        """Reset widget to empty state."""
        self._aav_stat.set_value("$0")
        self._years_stat.set_value("0")
        self._total_stat.set_value("$0")
        self._guaranteed_stat.set_value("$0 (0%)")
        self._gm_badge.set_style("balanced", "")
        self._pressure_indicator.set_pressure(0.5, 0.0, "")
        self._contribution_bar.set_contributions({})
        self._base_aav_label.setText("")

        self._factor_detail_sections.clear()
        while self._factor_details_container.count():
            child = self._factor_details_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
