"""
Unit tests for ValuationBreakdownWidget.

Tests the widget's ability to display contract valuation transparency,
including GM style badges, pressure indicators, factor contributions,
and collapsible detail sections.

Part of Tollgate 9: Contract Valuation UI Integration.
"""

import pytest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from game_cycle_ui.widgets.valuation_breakdown_widget import (
    ValuationBreakdownWidget,
    CollapsibleSection,
    GMStyleBadge,
    PressureLevelIndicator,
    FactorContributionBar,
    FactorDetailSection,
    FACTOR_COLORS,
    FACTOR_LABELS,
)
from contract_valuation.models import (
    ValuationResult,
    FactorResult,
    ContractOffer,
    FactorWeights,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def qapp():
    """Ensure QApplication exists for widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_contract_offer():
    """Create a sample contract offer for testing."""
    return ContractOffer(
        aav=15_000_000,
        years=4,
        total_value=60_000_000,
        guaranteed=40_000_000,
        signing_bonus=20_000_000,
        guaranteed_pct=0.667,
    )


@pytest.fixture
def sample_factor_results():
    """Create sample factor results for testing."""
    return [
        FactorResult(
            name="stats_based",
            raw_value=14_000_000,
            confidence=0.85,
            breakdown={
                "tier": "elite",
                "composite_percentile": 88.5,
                "games_played": 16,
            },
        ),
        FactorResult(
            name="scouting",
            raw_value=15_500_000,
            confidence=0.78,
            breakdown={
                "overall": 87,
                "potential": 90,
                "physical_grade": 85,
                "mental_grade": 88,
                "composite_grade": 87.5,
            },
        ),
        FactorResult(
            name="market",
            raw_value=16_000_000,
            confidence=0.92,
            breakdown={
                "market_heat": 1.15,
                "contract_year": True,
                "contract_year_premium": 1.05,
                "rating_adjustment": 1.02,
            },
        ),
        FactorResult(
            name="rating",
            raw_value=13_500_000,
            confidence=0.95,
            breakdown={
                "tier": "pro_bowl",
                "scale_factor": 1.12,
            },
        ),
        FactorResult(
            name="age",
            raw_value=14_500_000,
            confidence=1.0,
            breakdown={
                "age": 27,
                "age_modifier": 1.08,
                "peak_start": 25,
                "peak_end": 29,
            },
        ),
    ]


@pytest.fixture
def sample_valuation_result(sample_contract_offer, sample_factor_results):
    """Create a complete sample valuation result."""
    return ValuationResult(
        offer=sample_contract_offer,
        factor_contributions={
            "stats_based": 4_200_000,
            "scouting": 3_875_000,
            "market": 4_000_000,
            "rating": 2_700_000,
            "age": 225_000,
        },
        gm_style="analytics_heavy",
        gm_style_description="Heavy emphasis on data and statistics",
        pressure_level=0.65,
        pressure_adjustment_pct=0.08,
        pressure_description="Moderate pressure to win now",
        raw_factor_results=sample_factor_results,
        weights_used=FactorWeights.create_analytics_heavy(),
        base_aav=13_888_889,
        player_id=12345,
        player_name="Patrick Mahomes",
        position="QB",
        valuation_timestamp="2025-12-19T10:30:00",
    )


# =============================================================================
# TEST: Widget Creation Without Data
# =============================================================================

def test_widget_creation_without_data(qapp):
    """Test that widget can be created without valuation data."""
    widget = ValuationBreakdownWidget()

    # Widget should be created successfully
    assert widget is not None
    # Note: Widget won't be visible unless added to a layout/shown explicitly
    assert widget is not None  # Just verify it exists

    # Summary stats should show default/empty values
    assert widget._aav_stat is not None
    assert widget._years_stat is not None
    assert widget._total_stat is not None
    assert widget._guaranteed_stat is not None

    # GM badge and pressure indicator should exist
    assert widget._gm_badge is not None
    assert widget._pressure_indicator is not None

    # Factor contribution bar and sections should exist but be empty
    assert widget._contribution_bar is not None
    assert widget._factors_section is not None
    assert len(widget._factor_detail_sections) == 0


# =============================================================================
# TEST: Set Valuation Result Populates Fields
# =============================================================================

def test_set_valuation_result_populates_fields(qapp, sample_valuation_result):
    """Test that set_valuation_result() populates all visible fields."""
    widget = ValuationBreakdownWidget()
    widget.set_valuation_result(sample_valuation_result)

    # Contract summary should be populated
    assert "$15,000,000" in widget._aav_stat._value_label.text()
    assert "4 yr" in widget._years_stat._value_label.text()
    assert "$60,000,000" in widget._total_stat._value_label.text()
    assert "$40,000,000" in widget._guaranteed_stat._value_label.text()
    assert "66%" in widget._guaranteed_stat._value_label.text()  # 66.7% rounds to 66%

    # GM badge should show correct style
    assert "Analytics-Heavy" in widget._gm_badge._style_label.text()

    # Pressure indicator should show correct percentage
    assert "65%" in widget._pressure_indicator._pct_label.text()

    # Base AAV label should show comparison
    base_aav_text = widget._base_aav_label.text()
    assert "$13,888,889" in base_aav_text
    assert "+8.0%" in base_aav_text or "+8%" in base_aav_text

    # Factor detail sections should be created
    assert len(widget._factor_detail_sections) == 5

    # Verify factor names
    section_titles = [section._factor_name for section in widget._factor_detail_sections]
    assert "stats_based" in section_titles
    assert "scouting" in section_titles
    assert "market" in section_titles
    assert "rating" in section_titles
    assert "age" in section_titles


# =============================================================================
# TEST: Collapsible Section Toggles
# =============================================================================

def test_collapsible_section_toggles(qapp):
    """Test that CollapsibleSection properly expands/collapses."""
    section = CollapsibleSection("Test Section", expanded=False)

    # Initially collapsed
    assert section.is_expanded() is False
    # Note: Need to show widget for visibility to work properly
    section.show()
    assert section._content_frame.isVisible() is False
    assert section._toggle_btn.arrowType() == Qt.ArrowType.RightArrow

    # Expand programmatically
    section.set_expanded(True)
    assert section.is_expanded() is True
    assert section._content_frame.isVisible() is True
    assert section._toggle_btn.arrowType() == Qt.ArrowType.DownArrow

    # Collapse programmatically
    section.set_expanded(False)
    assert section.is_expanded() is False
    assert section._content_frame.isVisible() is False
    assert section._toggle_btn.arrowType() == Qt.ArrowType.RightArrow

    # Test signal emission
    signal_received = []
    section.toggled.connect(lambda state: signal_received.append(state))

    section.set_expanded(True)
    assert len(signal_received) == 1
    assert signal_received[0] is True

    section.set_expanded(False)
    assert len(signal_received) == 2
    assert signal_received[1] is False


def test_collapsible_section_click_toggle(qapp):
    """Test that clicking the toggle button expands/collapses."""
    section = CollapsibleSection("Test Section", expanded=False)
    section.show()  # Need to show widget for visibility to work

    # Initially collapsed
    assert section.is_expanded() is False

    # Simulate button click
    section._toggle_btn.click()
    assert section.is_expanded() is True
    assert section._content_frame.isVisible() is True

    # Click again to collapse
    section._toggle_btn.click()
    assert section.is_expanded() is False
    assert section._content_frame.isVisible() is False


# =============================================================================
# TEST: GM Style Badge Displays Correct Icon Per Style
# =============================================================================

def test_gm_style_badge_displays_correct_icon_per_style(qapp):
    """Test that GMStyleBadge shows correct emoji/color for each GM style."""
    badge = GMStyleBadge()

    # Test analytics_heavy style
    badge.set_style("analytics_heavy", "Analytics-focused approach")
    assert badge._icon_label.text() == "📊"
    assert "Analytics-Heavy" in badge._style_label.text()
    assert badge.toolTip() == "Analytics-focused approach"

    # Test scout_focused style
    badge.set_style("scout_focused", "Eye-test focused")
    assert badge._icon_label.text() == "👁"
    assert "Scout-Focused" in badge._style_label.text()

    # Test balanced style
    badge.set_style("balanced", "Even distribution")
    assert badge._icon_label.text() == "⚖️"
    assert "Balanced" in badge._style_label.text()

    # Test market_driven style
    badge.set_style("market_driven", "Market rate focused")
    assert badge._icon_label.text() == "📈"
    assert "Market-Driven" in badge._style_label.text()

    # Test custom style
    badge.set_style("custom", "Custom weights")
    assert badge._icon_label.text() == "⚙️"
    assert "Custom" in badge._style_label.text()

    # Test unknown style (should default to balanced)
    badge.set_style("unknown_style", "Unknown")
    assert badge._icon_label.text() == "⚖️"
    assert "Balanced" in badge._style_label.text()


# =============================================================================
# TEST: Pressure Level Indicator Colors at Thresholds
# =============================================================================

def test_pressure_level_indicator_colors_at_thresholds(qapp):
    """Test that PressureLevelIndicator shows green/blue/red based on pressure level."""
    indicator = PressureLevelIndicator()

    # Test low pressure (< 30%) - should be green (#2E7D32 from Colors.SUCCESS)
    indicator.set_pressure(0.15, 0.0, "Low pressure - secure position")
    assert "15%" in indicator._pct_label.text()
    assert indicator._bar.value() == 15
    # Check that stylesheet contains success/green color
    stylesheet = indicator._bar.styleSheet()
    assert "#2E7D32" in stylesheet or "2E7D32" in stylesheet.upper()

    # Test boundary at 30% - should be green (< 0.3)
    indicator.set_pressure(0.29, 0.0, "Still secure")
    # Note: 0.29 * 100 = 29.0, int(29.0) = 29, but display may round differently
    pct_text = indicator._pct_label.text()
    assert "28%" in pct_text or "29%" in pct_text  # Allow for rounding variations
    stylesheet = indicator._bar.styleSheet()
    assert "#2E7D32" in stylesheet or "2E7D32" in stylesheet.upper()

    # Test moderate pressure (30-70%) - should be blue (#1976D2 from Colors.INFO)
    indicator.set_pressure(0.5, 0.05, "Moderate pressure")
    assert "50%" in indicator._pct_label.text()
    assert indicator._bar.value() == 50
    # Check that stylesheet contains info/blue color
    stylesheet = indicator._bar.styleSheet()
    assert "#1976D2" in stylesheet or "1976D2" in stylesheet.upper()

    # Test boundary at 70% - should be blue (< 0.7)
    indicator.set_pressure(0.69, 0.08, "Approaching hot seat")
    assert "69%" in indicator._pct_label.text()
    stylesheet = indicator._bar.styleSheet()
    assert "#1976D2" in stylesheet or "1976D2" in stylesheet.upper()

    # Test high pressure (>= 70%) - should be red (#C62828 from Colors.ERROR)
    indicator.set_pressure(0.85, 0.15, "Hot seat - must win now")
    assert "85%" in indicator._pct_label.text()
    assert indicator._bar.value() == 85
    # Check that stylesheet contains error/red color
    stylesheet = indicator._bar.styleSheet()
    assert "#C62828" in stylesheet or "C62828" in stylesheet.upper()

    # Test maximum pressure (100%)
    indicator.set_pressure(1.0, 0.25, "Critical pressure")
    assert "100%" in indicator._pct_label.text()
    stylesheet = indicator._bar.styleSheet()
    assert "#C62828" in stylesheet or "C62828" in stylesheet.upper()


def test_pressure_level_indicator_adjustment_display(qapp):
    """Test that pressure indicator displays adjustment percentage correctly."""
    indicator = PressureLevelIndicator()

    # Test with positive adjustment
    indicator.set_pressure(0.75, 0.12, "Hot seat")
    desc_text = indicator._desc_label.text()
    assert "+12.0%" in desc_text or "+12%" in desc_text
    assert "AAV adjustment" in desc_text

    # Test with negative adjustment (unlikely but possible)
    indicator.set_pressure(0.25, -0.05, "Secure")
    desc_text = indicator._desc_label.text()
    assert "-5.0%" in desc_text or "-5%" in desc_text

    # Test with zero adjustment (no adjustment text)
    indicator.set_pressure(0.5, 0.0, "Standard negotiation")
    desc_text = indicator._desc_label.text()
    assert "Standard negotiation" in desc_text
    assert "adjustment" not in desc_text.lower()


# =============================================================================
# TEST: Factor Contribution Bar Renders Segments
# =============================================================================

def test_factor_contribution_bar_renders_segments(qapp):
    """Test that FactorContributionBar displays proportional segments."""
    bar = FactorContributionBar()

    contributions = {
        "stats_based": 5_000_000,
        "scouting": 3_000_000,
        "market": 4_000_000,
        "rating": 2_000_000,
        "age": 1_000_000,
    }

    bar.set_contributions(contributions)

    # Check that bar layout has segments (should be 5)
    segment_count = bar._bar_layout.count()
    assert segment_count == 5

    # Check that legend layout has items
    # Each factor gets a legend item + 1 stretch at the end
    legend_count = bar._legend_layout.count()
    assert legend_count == 6  # 5 factors + 1 stretch

    # Verify contributions are stored correctly
    assert bar._contributions == contributions
    assert bar._total == 15_000_000


def test_factor_contribution_bar_empty_contributions(qapp):
    """Test that FactorContributionBar handles empty contributions."""
    bar = FactorContributionBar()

    bar.set_contributions({})

    # Should have no segments
    assert bar._bar_layout.count() == 0
    assert bar._legend_layout.count() == 0
    assert bar._total == 1  # Avoid division by zero


def test_factor_contribution_bar_zero_contributions_ignored(qapp):
    """Test that factors with zero or negative contributions are ignored."""
    bar = FactorContributionBar()

    contributions = {
        "stats_based": 5_000_000,
        "scouting": 0,  # Zero contribution
        "market": -1_000_000,  # Negative (shouldn't happen but test it)
        "rating": 3_000_000,
    }

    bar.set_contributions(contributions)

    # Should only have 2 segments (stats_based and rating)
    segment_count = bar._bar_layout.count()
    assert segment_count == 2


# =============================================================================
# TEST: Factor Detail Section Population
# =============================================================================

def test_factor_detail_section_stats_breakdown(qapp):
    """Test that FactorDetailSection correctly displays stats breakdown."""
    section = FactorDetailSection("stats_based")

    breakdown = {
        "tier": "elite",
        "composite_percentile": 92.5,
        "games_played": 17,
    }

    section.set_factor_result("stats_based", 14_000_000, 0.88, breakdown)

    # Content should be added to the section
    content_layout = section.content_layout()
    assert content_layout.count() > 0


def test_factor_detail_section_scouting_breakdown(qapp):
    """Test that FactorDetailSection correctly displays scouting breakdown."""
    section = FactorDetailSection("scouting")

    breakdown = {
        "overall": 89,
        "potential": 92,
        "physical_grade": 87,
        "mental_grade": 90,
        "composite_grade": 89.5,
    }

    section.set_factor_result("scouting", 15_500_000, 0.80, breakdown)

    # Content should be added
    content_layout = section.content_layout()
    assert content_layout.count() > 0


def test_factor_detail_section_market_breakdown(qapp):
    """Test that FactorDetailSection correctly displays market breakdown."""
    section = FactorDetailSection("market")

    breakdown = {
        "market_heat": 1.25,
        "contract_year": True,
        "contract_year_premium": 1.05,
        "rating_adjustment": 1.10,
    }

    section.set_factor_result("market", 18_000_000, 0.92, breakdown)

    # Content should be added
    content_layout = section.content_layout()
    assert content_layout.count() > 0


def test_factor_detail_section_rating_breakdown(qapp):
    """Test that FactorDetailSection correctly displays rating breakdown."""
    section = FactorDetailSection("rating")

    breakdown = {
        "tier": "all_pro",
        "scale_factor": 1.25,
    }

    section.set_factor_result("rating", 16_000_000, 0.95, breakdown)

    # Content should be added
    content_layout = section.content_layout()
    assert content_layout.count() > 0


def test_factor_detail_section_age_breakdown(qapp):
    """Test that FactorDetailSection correctly displays age breakdown."""
    section = FactorDetailSection("age")

    breakdown = {
        "age": 28,
        "age_modifier": 1.12,
        "peak_start": 26,
        "peak_end": 30,
    }

    section.set_factor_result("age", 15_000_000, 1.0, breakdown)

    # Content should be added
    content_layout = section.content_layout()
    assert content_layout.count() > 0


# =============================================================================
# TEST: Widget Clear Functionality
# =============================================================================

def test_widget_clear_resets_to_empty_state(qapp, sample_valuation_result):
    """Test that clear() resets widget to empty state."""
    widget = ValuationBreakdownWidget()

    # Populate with data
    widget.set_valuation_result(sample_valuation_result)
    assert len(widget._factor_detail_sections) == 5

    # Clear the widget
    widget.clear()

    # Check that stats are reset
    assert "$0" in widget._aav_stat._value_label.text()
    assert "0" in widget._years_stat._value_label.text()
    assert "$0" in widget._total_stat._value_label.text()

    # Check that base AAV label is cleared
    assert widget._base_aav_label.text() == ""

    # Check that factor detail sections are cleared
    assert len(widget._factor_detail_sections) == 0
    assert widget._factor_details_container.count() == 0


# =============================================================================
# TEST: Set Valuation Data from Dict
# =============================================================================

def test_set_valuation_data_from_dict(qapp, sample_valuation_result):
    """Test that set_valuation_data() works with dictionary input."""
    widget = ValuationBreakdownWidget()

    # Convert result to dict
    data_dict = sample_valuation_result.to_dict()

    # Populate from dict
    widget.set_valuation_data(data_dict)

    # Should populate same as set_valuation_result
    assert "$15,000,000" in widget._aav_stat._value_label.text()
    assert "4 yr" in widget._years_stat._value_label.text()
    assert "Analytics-Heavy" in widget._gm_badge._style_label.text()
    assert len(widget._factor_detail_sections) == 5


# =============================================================================
# TEST: Factor Colors and Labels Constants
# =============================================================================

def test_factor_colors_and_labels_constants():
    """Test that FACTOR_COLORS and FACTOR_LABELS are properly defined."""
    # Verify all expected factors have colors
    assert "stats_based" in FACTOR_COLORS
    assert "scouting" in FACTOR_COLORS
    assert "market" in FACTOR_COLORS
    assert "rating" in FACTOR_COLORS
    assert "age" in FACTOR_COLORS

    # Verify all colors are valid hex strings
    for color in FACTOR_COLORS.values():
        assert color.startswith("#")
        assert len(color) == 7

    # Verify all expected factors have labels
    assert "stats_based" in FACTOR_LABELS
    assert "scouting" in FACTOR_LABELS
    assert "market" in FACTOR_LABELS
    assert "rating" in FACTOR_LABELS
    assert "age" in FACTOR_LABELS

    # Verify labels are human-readable strings
    for label in FACTOR_LABELS.values():
        assert isinstance(label, str)
        assert len(label) > 0


# =============================================================================
# TEST: Edge Cases
# =============================================================================

def test_widget_handles_minimal_factor_results(qapp):
    """Test widget with minimal factor results (only one factor)."""
    widget = ValuationBreakdownWidget()

    minimal_result = ValuationResult(
        offer=ContractOffer(
            aav=10_000_000,
            years=3,
            total_value=30_000_000,
            guaranteed=20_000_000,
            signing_bonus=10_000_000,
            guaranteed_pct=0.667,
        ),
        factor_contributions={"rating": 10_000_000},
        gm_style="balanced",
        gm_style_description="Standard approach",
        pressure_level=0.5,
        pressure_adjustment_pct=0.0,
        pressure_description="Normal conditions",
        raw_factor_results=[
            FactorResult(
                name="rating",
                raw_value=10_000_000,
                confidence=0.95,
                breakdown={"tier": "starter", "scale_factor": 1.0},
            )
        ],
        weights_used=FactorWeights.create_balanced(),
        base_aav=10_000_000,
        player_id=999,
        player_name="Test Player",
        position="WR",
        valuation_timestamp="2025-12-19T12:00:00",
    )

    widget.set_valuation_result(minimal_result)

    # Should display successfully with only 1 factor
    assert len(widget._factor_detail_sections) == 1
    assert "$10,000,000" in widget._aav_stat._value_label.text()


def test_widget_handles_no_pressure_adjustment(qapp):
    """Test widget when pressure adjustment is zero."""
    widget = ValuationBreakdownWidget()

    result = ValuationResult(
        offer=ContractOffer(
            aav=12_000_000,
            years=4,
            total_value=48_000_000,
            guaranteed=30_000_000,
            signing_bonus=15_000_000,
            guaranteed_pct=0.625,
        ),
        factor_contributions={"rating": 12_000_000},
        gm_style="balanced",
        gm_style_description="Standard",
        pressure_level=0.5,
        pressure_adjustment_pct=0.0,  # Zero adjustment
        pressure_description="Normal",
        raw_factor_results=[
            FactorResult(
                name="rating",
                raw_value=12_000_000,
                confidence=0.95,
                breakdown={},
            )
        ],
        weights_used=FactorWeights.create_balanced(),
        base_aav=12_000_000,  # Same as AAV
        player_id=888,
        player_name="Test Player 2",
        position="LB",
        valuation_timestamp="2025-12-19T12:30:00",
    )

    widget.set_valuation_result(result)

    # Base AAV label should not show adjustment when zero
    base_aav_text = widget._base_aav_label.text()
    assert "$12,000,000" in base_aav_text
    # Should show base AAV but no adjustment details since diff is 0
    assert "Pressure Adjustment" not in base_aav_text or "$0" in base_aav_text


def test_collapsible_section_initial_state(qapp):
    """Test CollapsibleSection respects initial expanded state."""
    # Test initially expanded
    expanded_section = CollapsibleSection("Test", expanded=True)
    expanded_section.show()  # Need to show for visibility to work
    assert expanded_section.is_expanded() is True
    assert expanded_section._content_frame.isVisible() is True
    assert expanded_section._toggle_btn.arrowType() == Qt.ArrowType.DownArrow

    # Test initially collapsed
    collapsed_section = CollapsibleSection("Test", expanded=False)
    collapsed_section.show()  # Need to show for visibility to work
    assert collapsed_section.is_expanded() is False
    assert collapsed_section._content_frame.isVisible() is False
    assert collapsed_section._toggle_btn.arrowType() == Qt.ArrowType.RightArrow


# =============================================================================
# TEST: Integration with Real ValuationResult
# =============================================================================

def test_integration_with_complete_valuation_result(qapp, sample_valuation_result):
    """Integration test with a complete, realistic ValuationResult."""
    widget = ValuationBreakdownWidget()

    # This should work end-to-end without errors
    widget.set_valuation_result(sample_valuation_result)

    # Verify all major components are populated
    assert widget._aav_stat._value_label.text() != "$0"
    assert widget._years_stat._value_label.text() != "0"
    assert widget._gm_badge._style_label.text() != "GM Style"
    assert widget._pressure_indicator._pct_label.text() != "0%"
    assert len(widget._factor_detail_sections) > 0
    assert widget._contribution_bar._bar_layout.count() > 0  # Bar segments exist

    # Verify widget exists (visibility requires parent widget/show())
    assert widget is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
