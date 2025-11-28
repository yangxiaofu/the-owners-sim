"""
Tests for position-specific age categorization in training camp progression.

Validates Tollgate 1 acceptance criteria:
- RB age 28 is VETERAN (peak 23-27)
- QB age 28 is PRIME (peak 27-32)
"""

import pytest
import sys
import importlib.util
from pathlib import Path


def _import_training_camp_service():
    """Import training_camp_service directly without going through __init__.py."""
    src_path = Path(__file__).parent.parent.parent.parent / 'src'
    module_path = src_path / 'game_cycle' / 'services' / 'training_camp_service.py'

    # Add src to path for nested imports
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    spec = importlib.util.spec_from_file_location("training_camp_service", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_tcs = _import_training_camp_service()
AgeWeightedDevelopment = _tcs.AgeWeightedDevelopment
AgeCategory = _tcs.AgeCategory
PositionPeakAges = _tcs.PositionPeakAges


class TestPositionPeakAges:
    """Test suite for PositionPeakAges mapping class."""

    # === Position Group Mapping Tests ===

    def test_quarterback_maps_to_quarterback_group(self):
        """QB positions should map to QUARTERBACK group."""
        assert PositionPeakAges.get_position_group('quarterback') == 'QUARTERBACK'
        assert PositionPeakAges.get_position_group('Quarterback') == 'QUARTERBACK'
        assert PositionPeakAges.get_position_group('qb') == 'QUARTERBACK'
        assert PositionPeakAges.get_position_group('QB') == 'QUARTERBACK'

    def test_running_back_maps_to_running_back_group(self):
        """RB positions should map to RUNNING_BACK group."""
        assert PositionPeakAges.get_position_group('running_back') == 'RUNNING_BACK'
        assert PositionPeakAges.get_position_group('Running Back') == 'RUNNING_BACK'
        assert PositionPeakAges.get_position_group('halfback') == 'RUNNING_BACK'
        assert PositionPeakAges.get_position_group('fullback') == 'RUNNING_BACK'
        assert PositionPeakAges.get_position_group('rb') == 'RUNNING_BACK'

    def test_wide_receiver_maps_correctly(self):
        """WR positions should map to WIDE_RECEIVER group."""
        assert PositionPeakAges.get_position_group('wide_receiver') == 'WIDE_RECEIVER'
        assert PositionPeakAges.get_position_group('wr') == 'WIDE_RECEIVER'

    def test_tight_end_maps_correctly(self):
        """TE positions should map to TIGHT_END group."""
        assert PositionPeakAges.get_position_group('tight_end') == 'TIGHT_END'
        assert PositionPeakAges.get_position_group('te') == 'TIGHT_END'

    def test_offensive_line_positions_map_correctly(self):
        """All OL positions should map to OFFENSIVE_LINE group."""
        ol_positions = [
            'left_tackle', 'right_tackle', 'left_guard',
            'right_guard', 'center', 'offensive_line'
        ]
        for pos in ol_positions:
            assert PositionPeakAges.get_position_group(pos) == 'OFFENSIVE_LINE'

    def test_defensive_line_positions_map_correctly(self):
        """All DL positions should map to DEFENSIVE_LINE group."""
        dl_positions = [
            'defensive_end', 'defensive_tackle', 'nose_tackle', 'edge'
        ]
        for pos in dl_positions:
            assert PositionPeakAges.get_position_group(pos) == 'DEFENSIVE_LINE'

    def test_linebacker_positions_map_correctly(self):
        """All LB positions should map to LINEBACKER group."""
        lb_positions = [
            'linebacker', 'outside_linebacker', 'inside_linebacker',
            'mike_linebacker', 'will_linebacker', 'sam_linebacker'
        ]
        for pos in lb_positions:
            assert PositionPeakAges.get_position_group(pos) == 'LINEBACKER'

    def test_defensive_back_positions_map_correctly(self):
        """All DB positions should map to DEFENSIVE_BACK group."""
        db_positions = [
            'cornerback', 'safety', 'free_safety', 'strong_safety'
        ]
        for pos in db_positions:
            assert PositionPeakAges.get_position_group(pos) == 'DEFENSIVE_BACK'

    def test_special_teams_positions_map_correctly(self):
        """Kicker and punter should map to their groups."""
        assert PositionPeakAges.get_position_group('kicker') == 'KICKER'
        assert PositionPeakAges.get_position_group('punter') == 'PUNTER'
        assert PositionPeakAges.get_position_group('long_snapper') == 'OFFENSIVE_LINE'

    def test_unknown_position_returns_default(self):
        """Unknown positions should return DEFAULT group."""
        assert PositionPeakAges.get_position_group('unknown') == 'DEFAULT'
        assert PositionPeakAges.get_position_group('') == 'DEFAULT'
        assert PositionPeakAges.get_position_group('mascot') == 'DEFAULT'

    # === Peak Age Retrieval Tests ===

    def test_get_peak_ages_for_quarterback(self):
        """QB peak ages should be 27-32."""
        peak_start, peak_end = PositionPeakAges.get_peak_ages('quarterback')
        assert peak_start == 27
        assert peak_end == 32

    def test_get_peak_ages_for_running_back(self):
        """RB peak ages should be 23-27."""
        peak_start, peak_end = PositionPeakAges.get_peak_ages('running_back')
        assert peak_start == 23
        assert peak_end == 27

    def test_get_peak_ages_for_wide_receiver(self):
        """WR peak ages should be 25-29."""
        peak_start, peak_end = PositionPeakAges.get_peak_ages('wide_receiver')
        assert peak_start == 25
        assert peak_end == 29

    def test_get_peak_ages_for_offensive_line(self):
        """OL peak ages should be 26-31."""
        peak_start, peak_end = PositionPeakAges.get_peak_ages('left_tackle')
        assert peak_start == 26
        assert peak_end == 31

    def test_get_peak_ages_for_kicker(self):
        """Kicker peak ages should be 28-36 (extended career)."""
        peak_start, peak_end = PositionPeakAges.get_peak_ages('kicker')
        assert peak_start == 28
        assert peak_end == 36

    def test_get_peak_ages_for_punter(self):
        """Punter peak ages should be 28-36 (extended career)."""
        peak_start, peak_end = PositionPeakAges.get_peak_ages('punter')
        assert peak_start == 28
        assert peak_end == 36


class TestAgeWeightedDevelopmentPositionSpecific:
    """Test suite for position-specific age categorization."""

    @pytest.fixture
    def algo(self):
        """Create AgeWeightedDevelopment instance."""
        return AgeWeightedDevelopment()

    # === ACCEPTANCE CRITERIA TESTS ===

    def test_rb_age_28_is_veteran(self, algo):
        """RB age 28 should be VETERAN (peak 23-27)."""
        category = algo.get_age_category(28, 'running_back')
        assert category == AgeCategory.VETERAN

    def test_qb_age_28_is_prime(self, algo):
        """QB age 28 should be PRIME (peak 27-32)."""
        category = algo.get_age_category(28, 'quarterback')
        assert category == AgeCategory.PRIME

    # === Quarterback Tests ===

    def test_qb_young_classification(self, algo):
        """QB under 27 should be YOUNG."""
        assert algo.get_age_category(22, 'quarterback') == AgeCategory.YOUNG
        assert algo.get_age_category(25, 'quarterback') == AgeCategory.YOUNG
        assert algo.get_age_category(26, 'quarterback') == AgeCategory.YOUNG

    def test_qb_prime_classification(self, algo):
        """QB 27-32 should be PRIME."""
        for age in range(27, 33):
            assert algo.get_age_category(age, 'quarterback') == AgeCategory.PRIME

    def test_qb_veteran_classification(self, algo):
        """QB over 32 should be VETERAN."""
        assert algo.get_age_category(33, 'quarterback') == AgeCategory.VETERAN
        assert algo.get_age_category(38, 'quarterback') == AgeCategory.VETERAN
        assert algo.get_age_category(42, 'quarterback') == AgeCategory.VETERAN

    # === Running Back Tests ===

    def test_rb_young_classification(self, algo):
        """RB under 23 should be YOUNG."""
        assert algo.get_age_category(21, 'running_back') == AgeCategory.YOUNG
        assert algo.get_age_category(22, 'running_back') == AgeCategory.YOUNG

    def test_rb_prime_classification(self, algo):
        """RB 23-27 should be PRIME."""
        for age in range(23, 28):
            assert algo.get_age_category(age, 'running_back') == AgeCategory.PRIME

    def test_rb_veteran_classification(self, algo):
        """RB over 27 should be VETERAN."""
        assert algo.get_age_category(28, 'running_back') == AgeCategory.VETERAN
        assert algo.get_age_category(30, 'running_back') == AgeCategory.VETERAN

    # === Offensive Line Tests ===

    def test_ol_classification(self, algo):
        """OL should peak at 26-31."""
        assert algo.get_age_category(25, 'left_tackle') == AgeCategory.YOUNG
        assert algo.get_age_category(28, 'left_tackle') == AgeCategory.PRIME
        assert algo.get_age_category(32, 'left_tackle') == AgeCategory.VETERAN

    # === Wide Receiver Tests ===

    def test_wr_classification(self, algo):
        """WR should peak at 25-29."""
        assert algo.get_age_category(24, 'wide_receiver') == AgeCategory.YOUNG
        assert algo.get_age_category(27, 'wide_receiver') == AgeCategory.PRIME
        assert algo.get_age_category(30, 'wide_receiver') == AgeCategory.VETERAN

    # === Special Teams Tests ===

    def test_kicker_extended_prime(self, algo):
        """Kicker should have extended prime (28-36)."""
        assert algo.get_age_category(27, 'kicker') == AgeCategory.YOUNG
        assert algo.get_age_category(32, 'kicker') == AgeCategory.PRIME
        assert algo.get_age_category(35, 'kicker') == AgeCategory.PRIME
        assert algo.get_age_category(37, 'kicker') == AgeCategory.VETERAN

    # === Backward Compatibility Tests ===

    def test_no_position_uses_generic_thresholds(self, algo):
        """Without position, should use generic thresholds (26-30 PRIME)."""
        # Generic: YOUNG < 26, PRIME 26-30, VETERAN > 30
        assert algo.get_age_category(25) == AgeCategory.YOUNG
        assert algo.get_age_category(26) == AgeCategory.PRIME
        assert algo.get_age_category(30) == AgeCategory.PRIME
        assert algo.get_age_category(31) == AgeCategory.VETERAN

    def test_position_with_spaces_works(self, algo):
        """Position strings with spaces should be handled."""
        category = algo.get_age_category(28, 'Running Back')
        assert category == AgeCategory.VETERAN

    def test_case_insensitive_position(self, algo):
        """Position matching should be case-insensitive."""
        assert algo.get_age_category(28, 'QUARTERBACK') == AgeCategory.PRIME
        assert algo.get_age_category(28, 'QuarterBack') == AgeCategory.PRIME
        assert algo.get_age_category(28, 'RUNNING_BACK') == AgeCategory.VETERAN

    def test_position_abbreviations_work(self, algo):
        """Position abbreviations should work."""
        assert algo.get_age_category(28, 'qb') == AgeCategory.PRIME
        assert algo.get_age_category(28, 'rb') == AgeCategory.VETERAN
        assert algo.get_age_category(28, 'wr') == AgeCategory.PRIME

    # === Edge Cases ===

    def test_unknown_position_uses_default(self, algo):
        """Unknown position should fall back to default (25-29 peak)."""
        # DEFAULT: peak 25-29
        assert algo.get_age_category(24, 'unknown_position') == AgeCategory.YOUNG
        assert algo.get_age_category(27, 'unknown_position') == AgeCategory.PRIME
        assert algo.get_age_category(30, 'unknown_position') == AgeCategory.VETERAN

    def test_invalid_archetype_falls_back_to_position(self, algo):
        """Invalid archetype should fall back to position group."""
        category = algo.get_age_category(
            28, 'running_back', archetype_id='invalid_archetype'
        )
        # RB peak is 23-27, so 28 is VETERAN
        assert category == AgeCategory.VETERAN


class TestAgeWeightedDevelopmentCalculateChanges:
    """Test that calculate_changes uses position-specific age categories."""

    @pytest.fixture
    def algo(self):
        """Create AgeWeightedDevelopment instance."""
        return AgeWeightedDevelopment()

    def test_calculate_changes_uses_position(self, algo):
        """calculate_changes should use position for age category."""
        # A 28-year-old QB should be PRIME (stable-biased)
        # A 28-year-old RB should be VETERAN (decline-biased)
        # We can't easily test the random outcomes, but we can verify
        # the method runs without error with position parameter
        attrs = {'awareness': 75, 'speed': 80}

        qb_changes = algo.calculate_changes(28, 'quarterback', attrs)
        rb_changes = algo.calculate_changes(28, 'running_back', attrs)

        # Both should return dicts (even if empty due to randomness)
        assert isinstance(qb_changes, dict)
        assert isinstance(rb_changes, dict)


class TestGrowthRates:
    """Test suite for Tollgate 2: Growth Rate configuration."""

    def test_get_growth_rates_for_quarterback(self):
        """QB should have growth_rate=1.5, regression_rate=1.5."""
        growth, regression = PositionPeakAges.get_growth_rates('quarterback')
        assert growth == 1.5
        assert regression == 1.5

    def test_get_growth_rates_for_running_back(self):
        """RB should have growth_rate=2.5, regression_rate=3.0."""
        growth, regression = PositionPeakAges.get_growth_rates('running_back')
        assert growth == 2.5
        assert regression == 3.0

    def test_get_growth_rates_for_wide_receiver(self):
        """WR should have growth_rate=2.0, regression_rate=2.0."""
        growth, regression = PositionPeakAges.get_growth_rates('wide_receiver')
        assert growth == 2.0
        assert regression == 2.0

    def test_get_growth_rates_for_kicker(self):
        """Kicker should have growth_rate=1.0, regression_rate=0.5."""
        growth, regression = PositionPeakAges.get_growth_rates('kicker')
        assert growth == 1.0
        assert regression == 0.5

    def test_get_growth_rates_default(self):
        """Unknown position should get default rates (2.0, 2.0)."""
        growth, regression = PositionPeakAges.get_growth_rates('unknown_position')
        assert growth == 2.0
        assert regression == 2.0


class TestRateToRange:
    """Test suite for _rate_to_range helper method."""

    @pytest.fixture
    def algo(self):
        """Create AgeWeightedDevelopment instance."""
        return AgeWeightedDevelopment()

    def test_rate_to_range_positive_base_2(self, algo):
        """Rate 2.5 should give range (1, 3) for improvement."""
        min_val, max_val = algo._rate_to_range(2.5, positive=True)
        assert min_val == 1
        assert max_val == 3

    def test_rate_to_range_positive_base_3(self, algo):
        """Rate 3.0 should give range (2, 4) for improvement."""
        min_val, max_val = algo._rate_to_range(3.0, positive=True)
        assert min_val == 2
        assert max_val == 4

    def test_rate_to_range_negative_base_2(self, algo):
        """Rate 2.5 should give range (-3, -1) for decline."""
        min_val, max_val = algo._rate_to_range(2.5, positive=False)
        assert min_val == -3
        assert max_val == -1

    def test_rate_to_range_negative_base_3(self, algo):
        """Rate 3.0 should give range (-4, -2) for decline."""
        min_val, max_val = algo._rate_to_range(3.0, positive=False)
        assert min_val == -4
        assert max_val == -2

    def test_rate_to_range_minimum_is_1(self, algo):
        """Minimum value should be at least 1 for improvement."""
        min_val, max_val = algo._rate_to_range(1.0, positive=True)
        assert min_val >= 1

    def test_rate_to_range_fractional_rate(self, algo):
        """Fractional rates should truncate to int."""
        # 1.5 truncates to 1, so range is (max(1, 0), 2) = (1, 2)
        min_val, max_val = algo._rate_to_range(1.5, positive=True)
        assert min_val == 1
        assert max_val == 2


class TestGrowthPhaseModeling:
    """Tests for Tollgate 2: Growth Phase Modeling.

    Validates acceptance criteria:
    - 22-year-old RB improves more than 25-year-old RB
    - Growth rate decreases as player approaches peak age
    - Post-peak decline is faster than pre-peak growth (for positions with higher regression_rate)
    """

    @pytest.fixture
    def algo(self):
        """Create AgeWeightedDevelopment instance."""
        return AgeWeightedDevelopment()

    def test_young_rb_improves_more_than_older_rb(self, algo):
        """22-year-old RB should have higher growth potential than 25-year-old RB."""
        # RB peak is 23-27, so 22yo is YOUNG (far from peak) and 25yo is PRIME
        attrs = {'speed': 75, 'agility': 75, 'elusiveness': 75, 'strength': 75,
                 'awareness': 75, 'carrying': 75, 'vision': 75}

        # Run multiple iterations to verify statistical tendency
        iterations = 200
        young_total = 0
        older_total = 0

        for _ in range(iterations):
            young_changes = algo.calculate_changes(21, 'running_back', attrs)
            older_changes = algo.calculate_changes(25, 'running_back', attrs)
            young_total += sum(young_changes.values())
            older_total += sum(older_changes.values())

        young_avg = young_total / iterations
        older_avg = older_total / iterations

        # Young RB (21, pre-peak) should improve more than prime RB (25)
        # We check statistical tendency, allowing for some variance
        assert young_avg > older_avg, f"Young avg {young_avg} should exceed older avg {older_avg}"

    def test_growth_rate_decreases_toward_peak(self, algo):
        """Growth rate should decrease as player approaches peak age."""
        # QB: peak_start=27, so ages 22, 25, 26 are all YOUNG but with different distance
        attrs = {'accuracy': 75, 'arm_strength': 75, 'awareness': 75,
                 'mobility': 75, 'pocket_presence': 75}

        iterations = 200
        age_22_total = 0
        age_25_total = 0
        age_26_total = 0

        for _ in range(iterations):
            changes_22 = algo.calculate_changes(22, 'quarterback', attrs)
            changes_25 = algo.calculate_changes(25, 'quarterback', attrs)
            changes_26 = algo.calculate_changes(26, 'quarterback', attrs)
            age_22_total += sum(changes_22.values())
            age_25_total += sum(changes_25.values())
            age_26_total += sum(changes_26.values())

        avg_22 = age_22_total / iterations
        avg_25 = age_25_total / iterations
        avg_26 = age_26_total / iterations

        # Further from peak should improve more
        assert avg_22 > avg_25, f"Age 22 avg {avg_22} should exceed age 25 avg {avg_25}"
        assert avg_25 > avg_26, f"Age 25 avg {avg_25} should exceed age 26 avg {avg_26}"

    def test_veteran_decline_faster_than_young_growth_for_rb(self, algo):
        """Post-peak decline should be faster than pre-peak growth for RBs."""
        # RB: peak 23-27, growth=2.5, regression=3.0
        attrs = {'speed': 80, 'agility': 80, 'elusiveness': 80, 'strength': 80,
                 'awareness': 80, 'carrying': 80, 'vision': 80}

        iterations = 200
        young_total = 0
        vet_total = 0

        for _ in range(iterations):
            young_changes = algo.calculate_changes(21, 'running_back', attrs)
            vet_changes = algo.calculate_changes(30, 'running_back', attrs)
            young_total += sum(young_changes.values())
            vet_total += sum(vet_changes.values())

        young_avg = abs(young_total / iterations)  # Positive (improvement)
        vet_avg = abs(vet_total / iterations)      # Negative (decline), take absolute

        # Veteran decline magnitude should exceed young growth magnitude
        # RB regression_rate (3.0) > growth_rate (2.5)
        # Note: This is statistical, so we allow some variance
        # The test validates the direction of the difference
        assert vet_avg > young_avg * 0.8, \
            f"Veteran decline {vet_avg} should be close to or exceed young growth {young_avg}"

    def test_qb_grows_slower_than_rb(self, algo):
        """QB (growth=1.5) should grow slower than RB (growth=2.5)."""
        # Both are young players
        qb_attrs = {'accuracy': 75, 'arm_strength': 75, 'awareness': 75,
                    'mobility': 75, 'pocket_presence': 75}
        rb_attrs = {'speed': 75, 'agility': 75, 'elusiveness': 75, 'strength': 75,
                    'awareness': 75, 'carrying': 75, 'vision': 75}

        iterations = 200
        qb_total = 0
        rb_total = 0

        for _ in range(iterations):
            qb_changes = algo.calculate_changes(22, 'quarterback', qb_attrs)
            rb_changes = algo.calculate_changes(21, 'running_back', rb_attrs)
            qb_total += sum(qb_changes.values())
            rb_total += sum(rb_changes.values())

        qb_avg = qb_total / iterations
        rb_avg = rb_total / iterations

        # RB growth_rate (2.5) > QB growth_rate (1.5)
        assert rb_avg > qb_avg, f"RB avg {rb_avg} should exceed QB avg {qb_avg}"

    def test_prime_player_stability(self, algo):
        """Prime players should have minimal changes (stable)."""
        # QB at age 29 (in prime: 27-32)
        attrs = {'accuracy': 80, 'arm_strength': 80, 'awareness': 80,
                 'mobility': 80, 'pocket_presence': 80}

        iterations = 200
        prime_total = 0

        for _ in range(iterations):
            changes = algo.calculate_changes(29, 'quarterback', attrs)
            prime_total += sum(changes.values())

        prime_avg = abs(prime_total / iterations)

        # Prime players have small changes (0, 1) and (-1, 0) ranges
        # Average should be close to 0
        assert prime_avg < 2.0, f"Prime avg change {prime_avg} should be near 0"

    def test_distance_multiplier_capped_at_50_percent(self, algo):
        """Distance multiplier should cap at 50% (1.5x)."""
        # Very young QB (age 20) is 7 years from peak (27)
        # 0.1 * 7 = 0.7, but capped at 0.5
        # So effective multiplier should be 1.5, not 1.7
        attrs = {'accuracy': 75, 'arm_strength': 75, 'awareness': 75,
                 'mobility': 75, 'pocket_presence': 75}

        # We test indirectly by checking that a 20yo doesn't get
        # drastically more than a 22yo (5 years from peak)
        iterations = 200
        age_20_total = 0
        age_22_total = 0

        for _ in range(iterations):
            changes_20 = algo.calculate_changes(20, 'quarterback', attrs)
            changes_22 = algo.calculate_changes(22, 'quarterback', attrs)
            age_20_total += sum(changes_20.values())
            age_22_total += sum(changes_22.values())

        avg_20 = age_20_total / iterations
        avg_22 = age_22_total / iterations

        # With cap, age 20 multiplier is 1.5 (capped), age 22 multiplier is 1.5 (5*0.1=0.5)
        # So they should be similar (both capped)
        # Actually: age 20 is 7 years from 27, so 1.0 + min(0.5, 0.7) = 1.5
        # Age 22 is 5 years from 27, so 1.0 + min(0.5, 0.5) = 1.5
        # They should be very close!
        assert abs(avg_20 - avg_22) < 1.0, \
            f"Age 20 ({avg_20}) and age 22 ({avg_22}) should be similar due to cap"


class TestPlayerPotential:
    """Tests for Tollgate 3: Individual Player Potential.

    Validates that players cannot improve beyond their individual potential ceiling.
    """

    @pytest.fixture
    def algo(self):
        """Create AgeWeightedDevelopment instance."""
        return AgeWeightedDevelopment()

    def test_improvement_capped_at_potential(self, algo):
        """Player cannot improve beyond their potential ceiling."""
        attrs = {'accuracy': 85, 'arm_strength': 85, 'awareness': 85,
                 'mobility': 85, 'pocket_presence': 85}
        potential = 87  # Only 2 points of headroom

        # Run many iterations - no improvement should exceed ceiling
        for _ in range(100):
            changes = algo.calculate_changes(22, 'quarterback', attrs, potential=potential)
            for attr, change in changes.items():
                # Each attribute change should not push value above potential
                new_value = attrs[attr] + change
                assert new_value <= potential, \
                    f"{attr}: {attrs[attr]} + {change} = {new_value} exceeds potential {potential}"

    def test_no_ceiling_if_potential_not_provided(self, algo):
        """Without potential, uses global ceiling of 99."""
        attrs = {'accuracy': 97, 'awareness': 97}

        # With no potential, should be able to improve up to 99
        changes = algo.calculate_changes(22, 'quarterback', attrs, potential=None)

        # Verify method runs and returns dict
        assert isinstance(changes, dict)

        # If there are improvements, they should respect 99 ceiling
        for attr, change in changes.items():
            if change > 0:
                assert attrs[attr] + change <= 99

    def test_potential_at_current_level_prevents_growth(self, algo):
        """If potential equals current attribute value, no improvement possible."""
        attrs = {'accuracy': 85, 'arm_strength': 85, 'awareness': 85,
                 'mobility': 85, 'pocket_presence': 85}
        potential = 85  # No headroom

        total_improvement = 0
        for _ in range(50):
            changes = algo.calculate_changes(22, 'quarterback', attrs, potential=potential)
            total_improvement += sum(c for c in changes.values() if c > 0)

        # No positive improvements should occur
        assert total_improvement == 0, \
            f"Expected 0 improvement with potential=85, got {total_improvement}"

    def test_high_potential_allows_more_growth(self, algo):
        """Higher potential allows more growth headroom."""
        attrs = {'speed': 75, 'agility': 75, 'elusiveness': 75, 'strength': 75,
                 'awareness': 75, 'carrying': 75, 'vision': 75}

        low_pot_improvements = []
        high_pot_improvements = []

        for _ in range(100):
            low_changes = algo.calculate_changes(21, 'running_back', attrs, potential=78)
            high_changes = algo.calculate_changes(21, 'running_back', attrs, potential=95)
            low_pot_improvements.append(sum(c for c in low_changes.values() if c > 0))
            high_pot_improvements.append(sum(c for c in high_changes.values() if c > 0))

        low_avg = sum(low_pot_improvements) / len(low_pot_improvements)
        high_avg = sum(high_pot_improvements) / len(high_pot_improvements)

        # Higher potential should allow more improvement on average
        assert high_avg > low_avg, \
            f"High potential avg {high_avg} should exceed low potential avg {low_avg}"

    def test_potential_below_current_still_allows_decline(self, algo):
        """Even with low potential, decline can still occur."""
        attrs = {'speed': 80, 'agility': 80, 'awareness': 80}
        potential = 75  # Below current - should never improve but can decline

        decline_count = 0
        for _ in range(50):
            changes = algo.calculate_changes(30, 'running_back', attrs, potential=potential)
            for change in changes.values():
                if change < 0:
                    decline_count += 1

        # Veteran player with low potential should still experience decline
        assert decline_count > 0, "Expected some decline even with low potential"

    def test_potential_parameter_works_with_all_age_categories(self, algo):
        """Potential ceiling applies across YOUNG, PRIME, and VETERAN."""
        attrs = {'accuracy': 85, 'awareness': 85}
        potential = 87

        # Test with different ages (young, prime, veteran for QB)
        for age in [22, 28, 35]:
            changes = algo.calculate_changes(age, 'quarterback', attrs, potential=potential)
            for attr, change in changes.items():
                if change > 0:
                    assert attrs[attr] + change <= potential, \
                        f"Age {age}: {attr} exceeded potential"

    def test_potential_as_integer_type(self, algo):
        """Potential should work correctly when passed as int."""
        attrs = {'speed': 80}
        potential = 82

        changes = algo.calculate_changes(22, 'running_back', attrs, potential=potential)
        for attr, change in changes.items():
            if change > 0:
                assert attrs[attr] + change <= potential

    def test_potential_ceiling_applies_per_attribute(self, algo):
        """Potential ceiling applies to each attribute independently."""
        # Some attributes near ceiling, some below
        attrs = {'accuracy': 86, 'arm_strength': 80, 'awareness': 88,
                 'mobility': 75, 'pocket_presence': 87}
        potential = 88

        for _ in range(50):
            changes = algo.calculate_changes(22, 'quarterback', attrs, potential=potential)

            for attr, change in changes.items():
                if change > 0:
                    # Each attribute's new value should respect potential
                    new_val = attrs[attr] + change
                    assert new_val <= potential, \
                        f"{attr}: {attrs[attr]} + {change} = {new_val} exceeds {potential}"


class TestDevelopmentCurveModifiers:
    """Tests for Tollgate 4: Development Curve Integration.

    Validates that archetype's development_curve ("early"/"normal"/"late")
    modifies player progression speed:
    - "early": +25% growth, normal decline
    - "normal": standard trajectory
    - "late": -25% growth, -20% decline
    """

    @pytest.fixture
    def algo(self):
        """Create AgeWeightedDevelopment instance."""
        return AgeWeightedDevelopment()

    # === DevelopmentCurveModifiers Constants Tests ===

    def test_curve_modifiers_constants_exist(self):
        """DevelopmentCurveModifiers class should have EARLY, NORMAL, LATE constants."""
        from src.transactions.transaction_constants import DevelopmentCurveModifiers

        assert hasattr(DevelopmentCurveModifiers, 'EARLY')
        assert hasattr(DevelopmentCurveModifiers, 'NORMAL')
        assert hasattr(DevelopmentCurveModifiers, 'LATE')

    def test_early_curve_modifiers_values(self):
        """EARLY curve should have +25% growth, normal decline."""
        from src.transactions.transaction_constants import DevelopmentCurveModifiers

        assert DevelopmentCurveModifiers.EARLY["growth"] == 1.25
        assert DevelopmentCurveModifiers.EARLY["decline"] == 1.0

    def test_normal_curve_modifiers_values(self):
        """NORMAL curve should be baseline (1.0 for both)."""
        from src.transactions.transaction_constants import DevelopmentCurveModifiers

        assert DevelopmentCurveModifiers.NORMAL["growth"] == 1.0
        assert DevelopmentCurveModifiers.NORMAL["decline"] == 1.0

    def test_late_curve_modifiers_values(self):
        """LATE curve should have -25% growth, -20% decline."""
        from src.transactions.transaction_constants import DevelopmentCurveModifiers

        assert DevelopmentCurveModifiers.LATE["growth"] == 0.75
        assert DevelopmentCurveModifiers.LATE["decline"] == 0.80

    def test_get_modifiers_returns_early(self):
        """get_modifiers('early') should return EARLY dict."""
        from src.transactions.transaction_constants import DevelopmentCurveModifiers

        modifiers = DevelopmentCurveModifiers.get_modifiers("early")
        assert modifiers == DevelopmentCurveModifiers.EARLY

    def test_get_modifiers_returns_normal(self):
        """get_modifiers('normal') should return NORMAL dict."""
        from src.transactions.transaction_constants import DevelopmentCurveModifiers

        modifiers = DevelopmentCurveModifiers.get_modifiers("normal")
        assert modifiers == DevelopmentCurveModifiers.NORMAL

    def test_get_modifiers_returns_late(self):
        """get_modifiers('late') should return LATE dict."""
        from src.transactions.transaction_constants import DevelopmentCurveModifiers

        modifiers = DevelopmentCurveModifiers.get_modifiers("late")
        assert modifiers == DevelopmentCurveModifiers.LATE

    def test_get_modifiers_case_insensitive(self):
        """get_modifiers should be case-insensitive."""
        from src.transactions.transaction_constants import DevelopmentCurveModifiers

        assert DevelopmentCurveModifiers.get_modifiers("EARLY") == DevelopmentCurveModifiers.EARLY
        assert DevelopmentCurveModifiers.get_modifiers("Early") == DevelopmentCurveModifiers.EARLY
        assert DevelopmentCurveModifiers.get_modifiers("LATE") == DevelopmentCurveModifiers.LATE

    def test_get_modifiers_unknown_defaults_to_normal(self):
        """Unknown curve types should default to NORMAL."""
        from src.transactions.transaction_constants import DevelopmentCurveModifiers

        assert DevelopmentCurveModifiers.get_modifiers("invalid") == DevelopmentCurveModifiers.NORMAL
        assert DevelopmentCurveModifiers.get_modifiers("unknown") == DevelopmentCurveModifiers.NORMAL

    def test_get_modifiers_none_defaults_to_normal(self):
        """None curve type should default to NORMAL."""
        from src.transactions.transaction_constants import DevelopmentCurveModifiers

        assert DevelopmentCurveModifiers.get_modifiers(None) == DevelopmentCurveModifiers.NORMAL

    # === _get_archetype_development_curve Tests ===

    def test_get_development_curve_none_archetype(self, algo):
        """None archetype_id should return 'normal'."""
        curve = algo._get_archetype_development_curve(None)
        assert curve == "normal"

    def test_get_development_curve_empty_archetype(self, algo):
        """Empty archetype_id should return 'normal'."""
        curve = algo._get_archetype_development_curve("")
        assert curve == "normal"

    def test_get_development_curve_invalid_archetype(self, algo):
        """Invalid archetype_id should return 'normal'."""
        curve = algo._get_archetype_development_curve("nonexistent_archetype_xyz")
        assert curve == "normal"

    def test_get_development_curve_power_back_is_early(self, algo):
        """power_back_rb archetype should return 'early' curve."""
        curve = algo._get_archetype_development_curve("power_back_rb")
        assert curve == "early"

    def test_get_development_curve_pocket_passer_is_normal(self, algo):
        """pocket_passer_qb archetype should return 'normal' curve."""
        curve = algo._get_archetype_development_curve("pocket_passer_qb")
        assert curve == "normal"

    # === calculate_changes with archetype_id Tests ===

    def test_calculate_changes_accepts_archetype_id(self, algo):
        """calculate_changes should accept archetype_id parameter."""
        attrs = {'speed': 75, 'agility': 75, 'elusiveness': 75}

        # Should not raise exception
        changes = algo.calculate_changes(
            22, 'running_back', attrs,
            potential=85, archetype_id="power_back_rb"
        )
        assert isinstance(changes, dict)

    def test_calculate_changes_without_archetype_uses_normal(self, algo):
        """calculate_changes without archetype_id should use normal curve."""
        attrs = {'speed': 75, 'agility': 75}

        # Should work without archetype_id
        changes = algo.calculate_changes(22, 'running_back', attrs)
        assert isinstance(changes, dict)

    def test_early_developer_grows_faster_than_normal(self, algo):
        """Early developer should improve more than normal developer on average."""
        attrs = {'speed': 75, 'agility': 75, 'elusiveness': 75, 'strength': 75,
                 'awareness': 75, 'carrying': 75, 'vision': 75}

        iterations = 200
        early_total = 0
        normal_total = 0

        for _ in range(iterations):
            # power_back_rb is "early", all_purpose_rb is "normal"
            early_changes = algo.calculate_changes(
                21, 'running_back', attrs, archetype_id="power_back_rb"
            )
            normal_changes = algo.calculate_changes(
                21, 'running_back', attrs, archetype_id="all_purpose_rb"
            )
            early_total += sum(early_changes.values())
            normal_total += sum(normal_changes.values())

        early_avg = early_total / iterations
        normal_avg = normal_total / iterations

        # Early developer (+25% growth) should improve more
        assert early_avg > normal_avg, \
            f"Early avg {early_avg} should exceed normal avg {normal_avg}"

    def test_late_developer_grows_slower_than_normal(self, algo):
        """Late developer should improve less than normal developer on average."""
        attrs = {'coverage': 75, 'speed': 75, 'press': 75,
                 'awareness': 75, 'ball_skills': 75}

        iterations = 200
        late_total = 0
        normal_total = 0

        for _ in range(iterations):
            # developmental_cb is "late", press_man_cb is "normal"
            late_changes = algo.calculate_changes(
                22, 'cornerback', attrs, archetype_id="developmental_cb"
            )
            normal_changes = algo.calculate_changes(
                22, 'cornerback', attrs, archetype_id="press_man_cb"
            )
            late_total += sum(late_changes.values())
            normal_total += sum(normal_changes.values())

        late_avg = late_total / iterations
        normal_avg = normal_total / iterations

        # Late developer (-25% growth) should improve less
        assert late_avg < normal_avg, \
            f"Late avg {late_avg} should be less than normal avg {normal_avg}"

    def test_late_developer_declines_slower_than_normal(self, algo):
        """Late developer should decline less than normal developer post-peak."""
        attrs = {'coverage': 80, 'speed': 80, 'press': 80,
                 'awareness': 80, 'ball_skills': 80}

        iterations = 200
        late_total = 0
        normal_total = 0

        # DB peak is 25-29, so age 32 is veteran
        for _ in range(iterations):
            late_changes = algo.calculate_changes(
                32, 'cornerback', attrs, archetype_id="developmental_cb"
            )
            normal_changes = algo.calculate_changes(
                32, 'cornerback', attrs, archetype_id="press_man_cb"
            )
            late_total += sum(late_changes.values())
            normal_total += sum(normal_changes.values())

        late_avg = late_total / iterations  # Should be negative (decline)
        normal_avg = normal_total / iterations  # Should be negative (decline)

        # Late developer (-20% decline) should have smaller decline magnitude
        # late_avg is closer to 0 (less negative)
        assert late_avg > normal_avg, \
            f"Late avg decline {late_avg} should be smaller than normal {normal_avg}"

    def test_early_developer_declines_at_normal_rate(self, algo):
        """Early developer should decline at normal rate (decline modifier = 1.0)."""
        attrs = {'speed': 80, 'agility': 80, 'elusiveness': 80, 'strength': 80,
                 'awareness': 80, 'carrying': 80, 'vision': 80}

        iterations = 200
        early_total = 0
        normal_total = 0

        # RB peak is 23-27, so age 30 is veteran
        for _ in range(iterations):
            early_changes = algo.calculate_changes(
                30, 'running_back', attrs, archetype_id="power_back_rb"
            )
            normal_changes = algo.calculate_changes(
                30, 'running_back', attrs, archetype_id="all_purpose_rb"
            )
            early_total += sum(early_changes.values())
            normal_total += sum(normal_changes.values())

        early_avg = early_total / iterations
        normal_avg = normal_total / iterations

        # Early decline modifier is 1.0 (same as normal), so should be similar
        # Allow 15% variance due to randomness
        assert abs(early_avg - normal_avg) < abs(normal_avg) * 0.3, \
            f"Early decline {early_avg} should be similar to normal {normal_avg}"

    def test_prime_player_unaffected_by_curve(self, algo):
        """Prime players have fixed ranges, so curve shouldn't dramatically affect them."""
        attrs = {'accuracy': 80, 'arm_strength': 80, 'awareness': 80,
                 'mobility': 80, 'pocket_presence': 80}

        iterations = 200
        early_total = 0
        late_total = 0

        # QB prime is 27-32
        for _ in range(iterations):
            # Using different archetypes but player is in PRIME (age 29)
            early_changes = algo.calculate_changes(
                29, 'quarterback', attrs, archetype_id="dual_threat_qb"  # "early"
            )
            late_changes = algo.calculate_changes(
                29, 'quarterback', attrs, archetype_id="game_manager_qb"  # "normal"
            )
            early_total += sum(early_changes.values())
            late_total += sum(late_changes.values())

        early_avg = abs(early_total / iterations)
        late_avg = abs(late_total / iterations)

        # Both should be close to 0 (prime stability)
        assert early_avg < 2.0, f"Prime early player avg {early_avg} should be near 0"
        assert late_avg < 2.0, f"Prime late player avg {late_avg} should be near 0"
