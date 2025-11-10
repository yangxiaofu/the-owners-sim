"""
Test Trade Deadline Enforcement (Comprehensive)

Tests that trades are properly blocked after the NFL trade deadline (Week 9 Tuesday).
Verifies TransactionTimingValidator correctly enforces deadline rules.

Based on NFL rules:
- Trades allowed: March 12 (new league year) through Week 9
- Trades blocked: Week 10+ through end of season
- Trade deadline occurs on Tuesday of Week 9 (early November)
"""

import pytest
from datetime import date

# Add src to path for testing
import sys
from pathlib import Path
src_path = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, src_path)

from transactions.transaction_timing_validator import TransactionTimingValidator
from calendar.season_phase_tracker import SeasonPhase


# ============================================================================
# TEST: COMPREHENSIVE TRADE WINDOW VALIDATION
# ============================================================================

class TestTradeWindowValidation:
    """Comprehensive tests for NFL trade window validation."""

    def test_trades_allowed_offseason_after_march_12(self):
        """Trades should be allowed in offseason after March 12."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 3, 13),
            current_phase=SeasonPhase.OFFSEASON,
            current_week=0
        )
        assert is_allowed, f"Trades should be allowed after March 12. Reason: {reason}"

    def test_trades_blocked_offseason_before_march_12(self):
        """Trades should be blocked in offseason before March 12."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 3, 11),
            current_phase=SeasonPhase.OFFSEASON,
            current_week=0
        )
        assert not is_allowed, "Trades should be blocked before March 12"
        assert "march 12" in reason.lower(), f"Expected March 12 message, got: {reason}"

    def test_trades_allowed_preseason(self):
        """Trades should be allowed during entire preseason."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 8, 15),
            current_phase=SeasonPhase.PRESEASON,
            current_week=0
        )
        assert is_allowed, f"Trades should be allowed in preseason. Reason: {reason}"

    def test_trades_allowed_regular_season_week_1(self):
        """Trades should be allowed during Week 1."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 9, 10),
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=1
        )
        assert is_allowed, f"Trades should be allowed in Week 1. Reason: {reason}"

    def test_trades_allowed_regular_season_week_9(self):
        """Trades should be allowed during Week 9 (deadline week)."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 11, 4),  # Tuesday of Week 9
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=9
        )
        assert is_allowed, f"Trades should be allowed in Week 9. Reason: {reason}"

    def test_trades_blocked_regular_season_week_10(self):
        """Trades should be blocked starting Week 10."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 11, 11),  # Week 10
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=10
        )
        assert not is_allowed, "Trades should be blocked after Week 9"
        assert "deadline has passed" in reason.lower(), f"Expected deadline message, got: {reason}"

    def test_trades_blocked_regular_season_week_18(self):
        """Trades should be blocked during Week 18."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2026, 1, 5),  # Week 18
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=18
        )
        assert not is_allowed, "Trades should be blocked in Week 18"

    def test_trades_blocked_playoffs(self):
        """Trades should be blocked during playoffs."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2026, 1, 15),
            current_phase=SeasonPhase.PLAYOFFS,
            current_week=0
        )
        assert not is_allowed, "Trades should be blocked in playoffs"
        assert "playoff" in reason.lower(), f"Expected playoff message, got: {reason}"

    def test_trade_deadline_boundary_week_8_vs_9(self):
        """Test the Week 8 vs Week 9 boundary (critical bug fix)."""
        validator = TransactionTimingValidator(2025)

        # Week 8 should be allowed
        week8_allowed, week8_reason = validator.is_trade_allowed(
            current_date=date(2025, 10, 28),
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=8
        )
        assert week8_allowed, f"Week 8 should allow trades. Reason: {week8_reason}"

        # Week 9 should be allowed (THIS IS THE BUG FIX)
        week9_allowed, week9_reason = validator.is_trade_allowed(
            current_date=date(2025, 11, 4),
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=9
        )
        assert week9_allowed, f"Week 9 should allow trades (deadline is AFTER Week 9). Reason: {week9_reason}"

        # Week 10 should be blocked
        week10_allowed, week10_reason = validator.is_trade_allowed(
            current_date=date(2025, 11, 11),
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=10
        )
        assert not week10_allowed, f"Week 10 should block trades. Got: {week10_allowed}"


# ============================================================================
# TEST: ADDITIONAL REGULAR SEASON WEEKS
# ============================================================================

class TestRegularSeasonTradeWindows:
    """Test trade windows for all regular season weeks."""

    def test_trades_allowed_week_2(self):
        """Trades should be allowed in Week 2."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 9, 17),
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=2
        )
        assert is_allowed, f"Week 2 should allow trades. Reason: {reason}"

    def test_trades_allowed_week_5(self):
        """Trades should be allowed in Week 5."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 10, 8),
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=5
        )
        assert is_allowed, f"Week 5 should allow trades. Reason: {reason}"

    def test_trades_allowed_week_7(self):
        """Trades should be allowed in Week 7."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 10, 22),
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=7
        )
        assert is_allowed, f"Week 7 should allow trades. Reason: {reason}"

    def test_trades_blocked_week_11(self):
        """Trades should be blocked in Week 11."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 11, 18),
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=11
        )
        assert not is_allowed, "Week 11 should block trades"

    def test_trades_blocked_week_15(self):
        """Trades should be blocked in Week 15."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 12, 16),
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=15
        )
        assert not is_allowed, "Week 15 should block trades"


# ============================================================================
# TEST: ERROR MESSAGES
# ============================================================================

class TestTradeDeadlineErrorMessages:
    """Test that deadline violations return clear error messages."""

    def test_before_march_12_message(self):
        """Test error message for trades before March 12."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 2, 15),
            current_phase=SeasonPhase.OFFSEASON,
            current_week=0
        )
        assert not is_allowed
        assert "march 12" in reason.lower()
        assert "new league year" in reason.lower()

    def test_after_deadline_message(self):
        """Test error message for trades after Week 9 deadline."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 11, 11),
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=10
        )
        assert not is_allowed
        assert "deadline has passed" in reason.lower()
        # Should reference Week 8 or Week 9 in message
        assert "week" in reason.lower()

    def test_playoffs_message(self):
        """Test error message for trades during playoffs."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2026, 1, 15),
            current_phase=SeasonPhase.PLAYOFFS,
            current_week=0
        )
        assert not is_allowed
        assert "playoff" in reason.lower()


# ============================================================================
# TEST: EDGE CASES
# ============================================================================

class TestTradeDeadlineEdgeCases:
    """Test edge cases for deadline validation."""

    def test_march_12_boundary(self):
        """Test the March 12 boundary (first day trades allowed)."""
        validator = TransactionTimingValidator(2025)

        # March 11 - should be blocked
        march_11_allowed, march_11_reason = validator.is_trade_allowed(
            current_date=date(2025, 3, 11),
            current_phase=SeasonPhase.OFFSEASON,
            current_week=0
        )
        assert not march_11_allowed, "March 11 should block trades"

        # March 12 - should be allowed
        march_12_allowed, march_12_reason = validator.is_trade_allowed(
            current_date=date(2025, 3, 12),
            current_phase=SeasonPhase.OFFSEASON,
            current_week=0
        )
        assert march_12_allowed, f"March 12 should allow trades. Reason: {march_12_reason}"

    def test_week_0_regular_season(self):
        """Test Week 0 in regular season (edge case)."""
        validator = TransactionTimingValidator(2025)
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2025, 9, 1),
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=0
        )
        # Week 0 should be allowed (not > deadline week)
        assert is_allowed, f"Week 0 should allow trades. Reason: {reason}"


# ============================================================================
# TEST: TRANSACTION STATUS SUMMARY
# ============================================================================

class TestTransactionStatusSummary:
    """Test the get_transaction_status_summary method."""

    def test_summary_during_regular_season(self):
        """Test transaction status summary during regular season."""
        validator = TransactionTimingValidator(2025)
        summary = validator.get_transaction_status_summary(
            current_date=date(2025, 9, 15),
            current_phase="regular_season",
            current_week=2
        )

        # During regular season Week 2
        assert summary["trades"][0] is True, "Trades should be allowed in Week 2"
        assert summary["franchise_tags"][0] is False, "Franchise tags closed by September"
        assert summary["free_agency"][0] is True, "Free agency open year-round after March 12"

    def test_summary_after_trade_deadline(self):
        """Test transaction status summary after trade deadline."""
        validator = TransactionTimingValidator(2025)
        summary = validator.get_transaction_status_summary(
            current_date=date(2025, 11, 15),
            current_phase="regular_season",
            current_week=11
        )

        # After trade deadline (Week 11)
        assert summary["trades"][0] is False, "Trades should be blocked in Week 11"
        assert "deadline has passed" in summary["trades"][1].lower()


# ============================================================================
# TEST: YEAR-TO-YEAR CONSISTENCY
# ============================================================================

class TestYearToYearConsistency:
    """Test that validation works correctly across different season years."""

    def test_2024_season(self):
        """Test trade window validation for 2024 season."""
        validator = TransactionTimingValidator(2024)

        # Week 9 of 2024 season
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2024, 11, 5),
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=9
        )
        assert is_allowed, f"2024 Week 9 should allow trades. Reason: {reason}"

    def test_2026_season(self):
        """Test trade window validation for 2026 season."""
        validator = TransactionTimingValidator(2026)

        # Week 9 of 2026 season
        is_allowed, reason = validator.is_trade_allowed(
            current_date=date(2026, 11, 4),
            current_phase=SeasonPhase.REGULAR_SEASON,
            current_week=9
        )
        assert is_allowed, f"2026 Week 9 should allow trades. Reason: {reason}"


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
