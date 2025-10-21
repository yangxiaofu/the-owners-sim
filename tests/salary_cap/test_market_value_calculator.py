"""
Unit tests for Market Value Calculator

Tests contract value calculations for free agents and franchise tags.
"""

import pytest
from offseason.market_value_calculator import MarketValueCalculator


class TestMarketValueCalculator:
    """Test suite for MarketValueCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance for testing."""
        return MarketValueCalculator()

    def test_elite_qb_contract(self, calculator):
        """Test contract for elite QB (Patrick Mahomes clone)."""
        contract = calculator.calculate_player_value(
            position='quarterback',
            overall=95,
            age=28,
            years_pro=7
        )

        # Elite QB (95 OVR) should get massive contract
        assert contract['aav'] >= 85.0  # At least $85M/year
        assert contract['years'] == 4  # QBs get 4-year deals
        assert contract['total_value'] >= 340.0  # At least $340M total
        assert contract['guarantee_percentage'] >= 65.0  # Elite guarantees

    def test_average_rb_contract(self, calculator):
        """Test contract for average RB."""
        contract = calculator.calculate_player_value(
            position='running_back',
            overall=75,
            age=26,
            years_pro=4
        )

        # Average RB (75 OVR) should get modest contract
        assert 5.0 <= contract['aav'] <= 8.0  # $5-8M range
        assert contract['years'] == 2  # RBs get short deals
        assert contract['total_value'] <= 20.0  # Not expensive
        assert contract['guarantee_percentage'] <= 45.0  # Lower guarantees

    def test_good_wr_with_age_discount(self, calculator):
        """Test contract for good WR past peak age."""
        contract = calculator.calculate_player_value(
            position='wide_receiver',
            overall=85,
            age=32,
            years_pro=10
        )

        # Good WR (85 OVR) but old (32) should have age discount
        baseline_contract = calculator.calculate_player_value(
            position='wide_receiver',
            overall=85,
            age=27,  # Peak age
            years_pro=5
        )

        # Older player should get less AAV
        assert contract['aav'] < baseline_contract['aav']
        # Older player should get shorter contract
        assert contract['years'] <= baseline_contract['years']

    def test_young_player_slight_discount(self, calculator):
        """Test that very young players get slight discount."""
        young_contract = calculator.calculate_player_value(
            position='cornerback',
            overall=85,
            age=23,
            years_pro=2
        )

        peak_contract = calculator.calculate_player_value(
            position='cornerback',
            overall=85,
            age=27,  # Peak age
            years_pro=5
        )

        # Young player (23) should get slightly less than peak age (27)
        assert young_contract['aav'] < peak_contract['aav']
        # But discount should be reasonable (upside potential vs less experience)
        # Young player has 0.85 age multiplier and 0.9 experience multiplier = 0.765x total
        assert young_contract['aav'] >= peak_contract['aav'] * 0.70

    def test_backup_player_low_value(self, calculator):
        """Test that backup players get low contracts."""
        contract = calculator.calculate_player_value(
            position='linebacker',
            overall=65,
            age=25,
            years_pro=3
        )

        # Backup (65 OVR) should get minimal contract
        assert contract['aav'] <= 5.0  # Very cheap
        assert contract['guarantee_percentage'] <= 30.0  # Low guarantees

    def test_franchise_tag_qb(self, calculator):
        """Test franchise tag value for QB."""
        tag_value = calculator.calculate_franchise_tag_value('quarterback')

        # QB tag should be ~120% of $45M base = $54M
        assert tag_value == 54_000_000

    def test_franchise_tag_rb(self, calculator):
        """Test franchise tag value for RB."""
        tag_value = calculator.calculate_franchise_tag_value('running_back')

        # RB tag should be ~120% of $12M base = $14.4M
        # Allow for floating point rounding (within $1)
        assert abs(tag_value - 14_400_000) <= 1

    def test_franchise_tag_edge_rusher(self, calculator):
        """Test franchise tag value for edge rusher (defensive end)."""
        tag_value = calculator.calculate_franchise_tag_value('defensive_end')

        # Edge rusher tag should be ~120% of $25M base = $30M
        assert tag_value == 30_000_000

    def test_premium_position_bonus_guarantees(self, calculator):
        """Test that premium positions get higher guarantee percentages."""
        qb_contract = calculator.calculate_player_value(
            position='quarterback',
            overall=85,
            age=28,
            years_pro=5
        )

        wr_contract = calculator.calculate_player_value(
            position='wide_receiver',
            overall=85,
            age=27,
            years_pro=5
        )

        # QB should get higher guarantee % than WR (both 85 OVR)
        assert qb_contract['guarantee_percentage'] > wr_contract['guarantee_percentage']

    def test_signing_bonus_calculation(self, calculator):
        """Test that signing bonus is ~35% of total value."""
        contract = calculator.calculate_player_value(
            position='left_tackle',
            overall=85,
            age=26,
            years_pro=4
        )

        expected_bonus = contract['total_value'] * 0.35
        # Allow small rounding difference
        assert abs(contract['signing_bonus'] - expected_bonus) < 0.1

    def test_contract_length_by_position(self, calculator):
        """Test that contract length varies by position."""
        qb_contract = calculator.calculate_player_value(
            position='quarterback',
            overall=85,
            age=27,
            years_pro=5
        )

        rb_contract = calculator.calculate_player_value(
            position='running_back',
            overall=85,
            age=26,
            years_pro=4
        )

        # QBs get 4-year deals, RBs get 2-year deals
        assert qb_contract['years'] == 4
        assert rb_contract['years'] == 2

    def test_age_30_plus_shorter_contracts(self, calculator):
        """Test that 30+ year old players get shorter contracts."""
        young_contract = calculator.calculate_player_value(
            position='wide_receiver',
            overall=85,
            age=26,
            years_pro=5
        )

        old_contract = calculator.calculate_player_value(
            position='wide_receiver',
            overall=85,
            age=31,
            years_pro=9
        )

        # Old player should get shorter deal (max 2 years)
        assert old_contract['years'] <= 2
        assert old_contract['years'] < young_contract['years']

    def test_rating_multiplier_scaling(self, calculator):
        """Test that rating multiplier scales correctly across ranges."""
        # Elite player (95 OVR)
        elite_contract = calculator.calculate_player_value(
            position='cornerback',
            overall=95,
            age=27,
            years_pro=5
        )

        # Good player (85 OVR)
        good_contract = calculator.calculate_player_value(
            position='cornerback',
            overall=85,
            age=27,
            years_pro=5
        )

        # Average player (75 OVR)
        avg_contract = calculator.calculate_player_value(
            position='cornerback',
            overall=75,
            age=27,
            years_pro=5
        )

        # Elite should get ~2x good, good should get ~2x average
        assert elite_contract['aav'] > good_contract['aav'] * 1.4
        assert good_contract['aav'] > avg_contract['aav'] * 1.5

    def test_unknown_position_default_values(self, calculator):
        """Test that unknown positions get default values."""
        contract = calculator.calculate_player_value(
            position='unknown_position',
            overall=85,
            age=27,
            years_pro=5
        )

        # Should use default base AAV of $10M
        # With 85 OVR (1.0x multiplier), age 27 (1.0x), 5 years (1.0x)
        # AAV should be ~$10M
        assert 9.0 <= contract['aav'] <= 11.0
        assert contract['years'] == 3  # Default length

    def test_veteran_experience_discount(self, calculator):
        """Test that veterans (9+ years) get slight discount."""
        veteran_contract = calculator.calculate_player_value(
            position='safety',
            overall=85,
            age=28,
            years_pro=10
        )

        prime_contract = calculator.calculate_player_value(
            position='safety',
            overall=85,
            age=28,
            years_pro=6
        )

        # Veteran should get slightly less (0.95x vs 1.0x)
        assert veteran_contract['aav'] < prime_contract['aav']
        assert veteran_contract['aav'] >= prime_contract['aav'] * 0.92

    def test_guarantee_percentage_caps_at_75(self, calculator):
        """Test that guarantee percentage never exceeds 75%."""
        # Even for elite QB (highest guarantees)
        contract = calculator.calculate_player_value(
            position='quarterback',
            overall=99,
            age=28,
            years_pro=7
        )

        assert contract['guarantee_percentage'] <= 75.0
