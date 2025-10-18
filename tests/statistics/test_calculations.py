"""
Unit tests for statistical calculation functions.

Tests cover:
- NFL passer rating formula with known values
- Perfect and minimum passer ratings
- Edge cases (0 attempts, negative values, etc.)
- All efficiency metrics
- Division by zero handling
- Percentage calculations
"""

import pytest
from stats_calculations.calculations import (
    calculate_passer_rating,
    calculate_yards_per_carry,
    calculate_catch_rate,
    calculate_yards_per_reception,
    calculate_yards_per_attempt,
    calculate_fg_percentage,
    calculate_xp_percentage,
    safe_divide,
)


class TestPasserRating:
    """Test NFL passer rating calculations."""

    def test_perfect_passer_rating(self):
        """Test perfect passer rating (158.3)."""
        # 77.5% completion, 12.5 Y/A, 11.875% TD%, 0% INT%
        rating = calculate_passer_rating(
            completions=31, attempts=40, yards=500, touchdowns=5, interceptions=0
        )
        assert rating == 158.3

    def test_zero_attempts(self):
        """Test passer rating with zero attempts."""
        rating = calculate_passer_rating(
            completions=0, attempts=0, yards=0, touchdowns=0, interceptions=0
        )
        assert rating == 0.0

    def test_all_completions_no_tds_or_ints(self):
        """Test 100% completion rate with average yards."""
        rating = calculate_passer_rating(
            completions=20, attempts=20, yards=200, touchdowns=0, interceptions=0
        )
        assert 100.0 < rating < 120.0

    def test_mahomes_2023_season(self):
        """Test Patrick Mahomes 2023 season stats (approximate)."""
        # 2023: 67.2% comp, 4,183 yards, 27 TDs, 14 INTs, 525 attempts
        rating = calculate_passer_rating(
            completions=353, attempts=525, yards=4183, touchdowns=27, interceptions=14
        )
        # Expected rating around 97 (actual calculation)
        assert 96.0 < rating < 99.0

    def test_very_poor_performance(self):
        """Test very poor passer performance."""
        rating = calculate_passer_rating(
            completions=5, attempts=30, yards=30, touchdowns=0, interceptions=5
        )
        # Should be very low rating
        assert 0.0 <= rating < 20.0

    def test_high_completion_low_yards(self):
        """Test high completion percentage but low yards."""
        rating = calculate_passer_rating(
            completions=18, attempts=20, yards=50, touchdowns=0, interceptions=0
        )
        # High completion but low Y/A should result in moderate rating
        assert 60.0 < rating < 90.0

    def test_low_completion_high_yards(self):
        """Test low completion percentage but high yards."""
        rating = calculate_passer_rating(
            completions=10, attempts=30, yards=400, touchdowns=2, interceptions=1
        )
        # Low completion but very high Y/A boosts rating
        assert 88.0 < rating < 92.0

    def test_many_touchdowns(self):
        """Test high touchdown rate impact."""
        rating = calculate_passer_rating(
            completions=20, attempts=30, yards=300, touchdowns=5, interceptions=0
        )
        # High TD rate should boost rating significantly
        assert 120.0 < rating < 158.3

    def test_many_interceptions(self):
        """Test high interception rate impact."""
        rating = calculate_passer_rating(
            completions=20, attempts=30, yards=300, touchdowns=2, interceptions=6
        )
        # High INT rate (20%) lowers rating but good completion/yards offset it
        assert 80.0 < rating < 85.0

    def test_average_qb_performance(self):
        """Test average NFL QB performance."""
        # ~65% completion, ~7.5 Y/A, 4% TD%, 2% INT%
        rating = calculate_passer_rating(
            completions=325, attempts=500, yards=3750, touchdowns=20, interceptions=10
        )
        # Should be around 90-95 rating
        assert 85.0 < rating < 100.0

    def test_component_clamping_max(self):
        """Test that components are clamped to maximum (2.375)."""
        # Unrealistically good stats to test clamping
        rating = calculate_passer_rating(
            completions=100, attempts=100, yards=2000, touchdowns=50, interceptions=0
        )
        assert rating == 158.3

    def test_component_clamping_min(self):
        """Test that components are clamped to minimum (0.0)."""
        # Unrealistically bad stats to test clamping
        rating = calculate_passer_rating(
            completions=0, attempts=50, yards=-100, touchdowns=0, interceptions=20
        )
        assert rating >= 0.0

    def test_single_attempt_completion(self):
        """Test single attempt completion."""
        rating = calculate_passer_rating(
            completions=1, attempts=1, yards=50, touchdowns=1, interceptions=0
        )
        assert rating == 158.3

    def test_single_attempt_incompletion(self):
        """Test single attempt incompletion with interception."""
        rating = calculate_passer_rating(
            completions=0, attempts=1, yards=0, touchdowns=0, interceptions=1
        )
        assert 0.0 <= rating < 40.0

    def test_negative_yards(self):
        """Test passer rating with negative yards (sacks)."""
        rating = calculate_passer_rating(
            completions=10, attempts=20, yards=-50, touchdowns=0, interceptions=2
        )
        assert 0.0 <= rating < 50.0

    def test_rodgers_2011_mvp_season(self):
        """Test Aaron Rodgers 2011 MVP season (122.5 rating)."""
        # 68.3% comp, 4,643 yards, 45 TDs, 6 INTs, 502 attempts
        rating = calculate_passer_rating(
            completions=343, attempts=502, yards=4643, touchdowns=45, interceptions=6
        )
        # Expected rating around 122-123
        assert 120.0 < rating < 125.0

    def test_rounding_behavior(self):
        """Test that passer rating is properly rounded."""
        rating = calculate_passer_rating(
            completions=20, attempts=30, yards=250, touchdowns=2, interceptions=1
        )
        # Should have exactly 1 decimal place
        assert rating == round(rating, 1)


class TestYardsPerCarry:
    """Test yards per carry calculations."""

    def test_normal_ypc(self):
        """Test normal yards per carry."""
        ypc = calculate_yards_per_carry(yards=100, attempts=20)
        assert ypc == 5.0

    def test_zero_attempts(self):
        """Test YPC with zero attempts."""
        ypc = calculate_yards_per_carry(yards=0, attempts=0)
        assert ypc == 0.0

    def test_negative_yards(self):
        """Test YPC with negative yards (sacks/losses)."""
        ypc = calculate_yards_per_carry(yards=-10, attempts=5)
        assert ypc == -2.0

    def test_single_carry(self):
        """Test YPC with single carry."""
        ypc = calculate_yards_per_carry(yards=15, attempts=1)
        assert ypc == 15.0

    def test_high_ypc(self):
        """Test high yards per carry."""
        ypc = calculate_yards_per_carry(yards=200, attempts=10)
        assert ypc == 20.0

    def test_low_ypc(self):
        """Test low yards per carry."""
        ypc = calculate_yards_per_carry(yards=10, attempts=20)
        assert ypc == 0.5


class TestCatchRate:
    """Test catch rate calculations."""

    def test_perfect_catch_rate(self):
        """Test 100% catch rate."""
        catch_rate = calculate_catch_rate(receptions=10, targets=10)
        assert catch_rate == 100.0

    def test_zero_targets(self):
        """Test catch rate with zero targets."""
        catch_rate = calculate_catch_rate(receptions=0, targets=0)
        assert catch_rate == 0.0

    def test_fifty_percent_catch_rate(self):
        """Test 50% catch rate."""
        catch_rate = calculate_catch_rate(receptions=5, targets=10)
        assert catch_rate == 50.0

    def test_single_target_caught(self):
        """Test single target caught."""
        catch_rate = calculate_catch_rate(receptions=1, targets=1)
        assert catch_rate == 100.0

    def test_single_target_missed(self):
        """Test single target missed."""
        catch_rate = calculate_catch_rate(receptions=0, targets=1)
        assert catch_rate == 0.0

    def test_high_volume_receiver(self):
        """Test high volume receiver stats."""
        catch_rate = calculate_catch_rate(receptions=100, targets=150)
        assert 66.0 < catch_rate < 67.0

    def test_rounding_behavior(self):
        """Test that catch rate is properly rounded."""
        catch_rate = calculate_catch_rate(receptions=7, targets=10)
        assert catch_rate == 70.0


class TestYardsPerReception:
    """Test yards per reception calculations."""

    def test_normal_ypr(self):
        """Test normal yards per reception."""
        ypr = calculate_yards_per_reception(yards=150, receptions=10)
        assert ypr == 15.0

    def test_zero_receptions(self):
        """Test YPR with zero receptions."""
        ypr = calculate_yards_per_reception(yards=0, receptions=0)
        assert ypr == 0.0

    def test_single_reception(self):
        """Test YPR with single reception."""
        ypr = calculate_yards_per_reception(yards=50, receptions=1)
        assert ypr == 50.0

    def test_deep_threat_receiver(self):
        """Test deep threat receiver (high YPR)."""
        ypr = calculate_yards_per_reception(yards=400, receptions=20)
        assert ypr == 20.0

    def test_possession_receiver(self):
        """Test possession receiver (low YPR)."""
        ypr = calculate_yards_per_reception(yards=60, receptions=10)
        assert ypr == 6.0


class TestYardsPerAttempt:
    """Test yards per attempt calculations."""

    def test_normal_ypa(self):
        """Test normal yards per attempt."""
        ypa = calculate_yards_per_attempt(yards=250, attempts=30)
        assert 8.0 < ypa < 8.5

    def test_zero_attempts(self):
        """Test YPA with zero attempts."""
        ypa = calculate_yards_per_attempt(yards=0, attempts=0)
        assert ypa == 0.0

    def test_negative_yards(self):
        """Test YPA with negative yards."""
        ypa = calculate_yards_per_attempt(yards=-30, attempts=10)
        assert ypa == -3.0

    def test_high_ypa(self):
        """Test high yards per attempt."""
        ypa = calculate_yards_per_attempt(yards=400, attempts=30)
        assert 13.0 < ypa < 13.5


class TestFieldGoalPercentage:
    """Test field goal percentage calculations."""

    def test_perfect_fg_percentage(self):
        """Test 100% field goal percentage."""
        fg_pct = calculate_fg_percentage(made=20, attempted=20)
        assert fg_pct == 100.0

    def test_zero_attempts(self):
        """Test FG% with zero attempts."""
        fg_pct = calculate_fg_percentage(made=0, attempted=0)
        assert fg_pct == 0.0

    def test_fifty_percent(self):
        """Test 50% field goal percentage."""
        fg_pct = calculate_fg_percentage(made=10, attempted=20)
        assert fg_pct == 50.0

    def test_single_make(self):
        """Test single field goal made."""
        fg_pct = calculate_fg_percentage(made=1, attempted=1)
        assert fg_pct == 100.0

    def test_single_miss(self):
        """Test single field goal missed."""
        fg_pct = calculate_fg_percentage(made=0, attempted=1)
        assert fg_pct == 0.0

    def test_typical_kicker(self):
        """Test typical NFL kicker (85% accuracy)."""
        fg_pct = calculate_fg_percentage(made=17, attempted=20)
        assert fg_pct == 85.0


class TestExtraPointPercentage:
    """Test extra point percentage calculations."""

    def test_perfect_xp_percentage(self):
        """Test 100% extra point percentage."""
        xp_pct = calculate_xp_percentage(made=30, attempted=30)
        assert xp_pct == 100.0

    def test_zero_attempts(self):
        """Test XP% with zero attempts."""
        xp_pct = calculate_xp_percentage(made=0, attempted=0)
        assert xp_pct == 0.0

    def test_one_miss(self):
        """Test one missed extra point."""
        xp_pct = calculate_xp_percentage(made=29, attempted=30)
        assert 96.0 < xp_pct < 97.0

    def test_typical_kicker(self):
        """Test typical NFL kicker (99% XP accuracy)."""
        xp_pct = calculate_xp_percentage(made=49, attempted=50)
        assert xp_pct == 98.0


class TestSafeDivide:
    """Test safe division utility function."""

    def test_normal_division(self):
        """Test normal division."""
        result = safe_divide(10.0, 2.0)
        assert result == 5.0

    def test_divide_by_zero_default(self):
        """Test division by zero with default return value."""
        result = safe_divide(10.0, 0.0, default=0.0)
        assert result == 0.0

    def test_divide_by_zero_custom_default(self):
        """Test division by zero with custom default."""
        result = safe_divide(10.0, 0.0, default=99.9)
        assert result == 99.9

    def test_negative_numerator(self):
        """Test safe divide with negative numerator."""
        result = safe_divide(-10.0, 2.0)
        assert result == -5.0

    def test_negative_denominator(self):
        """Test safe divide with negative denominator."""
        result = safe_divide(10.0, -2.0)
        assert result == -5.0

    def test_both_negative(self):
        """Test safe divide with both negative."""
        result = safe_divide(-10.0, -2.0)
        assert result == 5.0

    def test_float_precision(self):
        """Test safe divide with float precision."""
        result = safe_divide(10.0, 3.0)
        assert 3.3 == result

    def test_rounding_behavior(self):
        """Test that safe divide rounds to 1 decimal place."""
        result = safe_divide(7.0, 3.0)
        assert result == 2.3
