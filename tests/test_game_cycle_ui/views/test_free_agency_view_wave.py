"""
Unit tests for FreeAgencyView wave-based UI components.

Part of Milestone 8: Free Agency Depth - Tollgate 5.

Tests the wave header, progress indicator, control buttons, and new signals.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

# Check if Qt is available
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Signal
    HAS_QT = True
except ImportError:
    HAS_QT = False


# Skip all tests if Qt is not available
pytestmark = pytest.mark.skipif(not HAS_QT, reason="Qt not available")


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    if not HAS_QT:
        return None
    # Check if QApplication already exists
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def view(qapp):
    """Create FreeAgencyView instance for testing."""
    from game_cycle_ui.views.free_agency_view import FreeAgencyView
    return FreeAgencyView()


class TestWaveSignals:
    """Tests for wave-related signals."""

    def test_offer_submitted_signal_exists(self, view):
        """offer_submitted signal should exist."""
        assert hasattr(view, 'offer_submitted')

    def test_offer_withdrawn_signal_exists(self, view):
        """offer_withdrawn signal should exist."""
        assert hasattr(view, 'offer_withdrawn')

    def test_process_day_requested_signal_exists(self, view):
        """process_day_requested signal should exist."""
        assert hasattr(view, 'process_day_requested')

    def test_process_wave_requested_signal_exists(self, view):
        """process_wave_requested signal should exist."""
        assert hasattr(view, 'process_wave_requested')


class TestWaveInitialState:
    """Tests for initial wave state."""

    def test_wave_mode_initially_false(self, view):
        """Wave mode should be disabled by default."""
        assert view._wave_mode is False

    def test_wave_header_initially_hidden(self, view):
        """Wave header should be hidden by default."""
        assert view._wave_header_group.isHidden()

    def test_wave_controls_initially_hidden(self, view):
        """Wave controls should be hidden by default."""
        assert view._wave_controls_frame.isHidden()

    def test_current_wave_initial_value(self, view):
        """Current wave should be 0 initially."""
        assert view._current_wave == 0

    def test_current_day_initial_value(self, view):
        """Current day should be 1 initially."""
        assert view._current_day == 1


class TestSetWaveInfo:
    """Tests for set_wave_info method."""

    def test_enables_wave_mode_on_first_call(self, view):
        """set_wave_info should enable wave mode on first call."""
        assert view._wave_mode is False

        view.set_wave_info(wave=0, wave_name="Legal Tampering", day=1, days_total=1)

        assert view._wave_mode is True

    def test_shows_wave_header(self, view):
        """set_wave_info should show wave header."""
        view.set_wave_info(wave=1, wave_name="Wave 1 - Elite", day=1, days_total=3)

        assert not view._wave_header_group.isHidden()

    def test_shows_wave_controls(self, view):
        """set_wave_info should show wave controls."""
        view.set_wave_info(wave=1, wave_name="Wave 1 - Elite", day=1, days_total=3)

        assert not view._wave_controls_frame.isHidden()

    def test_updates_wave_title(self, view):
        """set_wave_info should update wave title label."""
        view.set_wave_info(wave=1, wave_name="Wave 1 - Elite", day=2, days_total=3)

        assert "Wave 1 - Elite" in view._wave_title_label.text()

    def test_updates_day_display(self, view):
        """set_wave_info should update day display."""
        view.set_wave_info(wave=2, wave_name="Wave 2 - Quality", day=2, days_total=3)

        assert "Day 2/3" in view._wave_day_label.text()

    def test_updates_days_remaining(self, view):
        """set_wave_info should update days remaining label."""
        view.set_wave_info(wave=1, wave_name="Wave 1", day=2, days_total=3)

        assert "Days Remaining: 1" in view._days_remaining_label.text()

    def test_progress_indicators_count(self, view):
        """Should have 5 wave progress indicators."""
        view.set_wave_info(wave=0, wave_name="Legal Tampering", day=1, days_total=1)

        assert len(view._wave_indicators) == 5

    def test_current_wave_indicator_blue(self, view):
        """Current wave indicator should be blue."""
        view.set_wave_info(wave=2, wave_name="Wave 2", day=1, days_total=2)

        # Wave 2 is index 2, should be blue
        style = view._wave_indicators[2].styleSheet()
        assert "#1976D2" in style  # Blue

    def test_completed_wave_indicator_green(self, view):
        """Completed wave indicators should be green."""
        view.set_wave_info(wave=2, wave_name="Wave 2", day=1, days_total=2)

        # Waves 0 and 1 should be green (completed)
        style_0 = view._wave_indicators[0].styleSheet()
        style_1 = view._wave_indicators[1].styleSheet()
        assert "#2E7D32" in style_0  # Green
        assert "#2E7D32" in style_1  # Green

    def test_future_wave_indicator_gray(self, view):
        """Future wave indicators should be gray."""
        view.set_wave_info(wave=1, wave_name="Wave 1", day=1, days_total=3)

        # Waves 2, 3, 4 should be gray (future)
        for i in [2, 3, 4]:
            style = view._wave_indicators[i].styleSheet()
            assert "#ddd" in style  # Gray

    def test_process_day_disabled_on_last_day(self, view):
        """Process Day button should be disabled on last day of wave."""
        view.set_wave_info(wave=1, wave_name="Wave 1", day=3, days_total=3)

        assert not view._process_day_btn.isEnabled()

    def test_process_day_enabled_before_last_day(self, view):
        """Process Day button should be enabled before last day."""
        view.set_wave_info(wave=1, wave_name="Wave 1", day=2, days_total=3)

        assert view._process_day_btn.isEnabled()

    def test_process_wave_always_enabled(self, view):
        """Process Wave button should always be enabled."""
        view.set_wave_info(wave=1, wave_name="Wave 1", day=1, days_total=3)

        assert view._process_wave_btn.isEnabled()

    def test_legal_tampering_button_text(self, view):
        """Legal Tampering wave should have special button text."""
        view.set_wave_info(wave=0, wave_name="Legal Tampering", day=1, days_total=1)

        assert view._process_day_btn.text() == "View Offers"
        assert view._process_wave_btn.text() == "Start Wave 1"

    def test_normal_wave_button_text(self, view):
        """Normal waves should have standard button text."""
        view.set_wave_info(wave=1, wave_name="Wave 1", day=1, days_total=3)

        assert view._process_day_btn.text() == "Process Day"
        assert view._process_wave_btn.text() == "Process Wave"


class TestSetPendingOffersCount:
    """Tests for set_pending_offers_count method."""

    def test_updates_count_in_wave_mode(self, view):
        """set_pending_offers_count should update label in wave mode."""
        view.set_wave_info(wave=1, wave_name="Wave 1", day=1, days_total=3)

        view.set_pending_offers_count(5)

        assert view.pending_count_label.text() == "5"

    def test_zero_count_gray(self, view):
        """Zero offers should show gray color."""
        view.set_wave_info(wave=1, wave_name="Wave 1", day=1, days_total=3)

        view.set_pending_offers_count(0)

        style = view.pending_count_label.styleSheet()
        assert "#666" in style

    def test_low_count_orange(self, view):
        """1-3 offers should show orange color."""
        view.set_wave_info(wave=1, wave_name="Wave 1", day=1, days_total=3)

        view.set_pending_offers_count(2)

        style = view.pending_count_label.styleSheet()
        assert "#FF6F00" in style

    def test_high_count_blue(self, view):
        """4+ offers should show blue color."""
        view.set_wave_info(wave=1, wave_name="Wave 1", day=1, days_total=3)

        view.set_pending_offers_count(5)

        style = view.pending_count_label.styleSheet()
        assert "#1976D2" in style


class TestSetPlayerOfferStatus:
    """Tests for set_player_offer_status method."""

    def test_stores_player_statuses(self, view):
        """set_player_offer_status should store status data."""
        statuses = {
            100: {"offer_count": 2, "has_user_offer": True, "user_offer_id": 1},
            101: {"offer_count": 1, "has_user_offer": False},
        }

        view.set_player_offer_status(statuses)

        assert view._player_offer_status == statuses


class TestWaveProperties:
    """Tests for wave-related properties."""

    def test_wave_mode_property(self, view):
        """wave_mode property should reflect internal state."""
        assert view.wave_mode is False

        view.set_wave_info(wave=1, wave_name="Wave 1", day=1, days_total=3)

        assert view.wave_mode is True

    def test_current_wave_property(self, view):
        """current_wave property should return current wave number."""
        view.set_wave_info(wave=2, wave_name="Wave 2", day=1, days_total=2)

        assert view.current_wave == 2


class TestBackwardCompatibility:
    """Tests for backward compatibility with non-wave mode."""

    def test_legacy_signals_still_exist(self, view):
        """Legacy signals should still exist."""
        assert hasattr(view, 'player_signed')
        assert hasattr(view, 'player_unsigned')
        assert hasattr(view, 'cap_validation_changed')

    def test_legacy_methods_still_work(self, view):
        """Legacy methods should still work when wave mode is off."""
        # These should not raise
        view.set_free_agents([])
        view.set_cap_space(50_000_000)
        view.set_cap_data({"available_space": 50_000_000})