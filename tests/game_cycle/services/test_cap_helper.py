"""
Tests for CapHelper service.

Tests the unified cap operations helper for game cycle services.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestCapHelper:
    """Test suite for CapHelper class."""

    @pytest.fixture
    def cap_helper(self):
        """Create a CapHelper instance with mocked dependencies."""
        with patch('src.game_cycle.services.cap_helper.CapCalculator') as mock_calc, \
             patch('src.game_cycle.services.cap_helper.CapDatabaseAPI') as mock_db_api:

            from src.game_cycle.services.cap_helper import CapHelper

            helper = CapHelper(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025
            )
            helper._mock_calc = mock_calc.return_value
            helper._mock_db_api = mock_db_api.return_value
            return helper

    def test_get_cap_summary_returns_expected_structure(self, cap_helper):
        """Test that get_cap_summary returns all expected fields."""
        cap_helper._mock_calc.calculate_team_cap_space.return_value = 50_000_000
        cap_helper._mock_db_api.get_team_cap_summary.return_value = {
            "salary_cap_limit": 255_400_000,
            "carryover_from_previous": 5_000_000,
            "dead_money_total": 10_000_000,
            "active_contracts_total": 200_000_000
        }

        result = cap_helper.get_cap_summary(team_id=1)

        assert "salary_cap_limit" in result
        assert "total_spending" in result
        assert "available_space" in result
        assert "dead_money" in result
        assert "is_compliant" in result
        assert "carryover" in result

    def test_get_cap_summary_calculates_correctly(self, cap_helper):
        """Test cap summary calculation is correct."""
        cap_helper._mock_calc.calculate_team_cap_space.return_value = 45_400_000
        cap_helper._mock_db_api.get_team_cap_summary.return_value = {
            "salary_cap_limit": 255_400_000,
            "carryover_from_previous": 5_000_000,
            "dead_money_total": 10_000_000,
            "active_contracts_total": 200_000_000
        }

        result = cap_helper.get_cap_summary(team_id=1)

        assert result["available_space"] == 45_400_000
        assert result["total_spending"] == 210_000_000  # 200M active + 10M dead
        assert result["is_compliant"] is True

    def test_get_cap_summary_detects_non_compliance(self, cap_helper):
        """Test that negative cap space is flagged as non-compliant."""
        cap_helper._mock_calc.calculate_team_cap_space.return_value = -5_000_000
        cap_helper._mock_db_api.get_team_cap_summary.return_value = {
            "salary_cap_limit": 255_400_000,
            "active_contracts_total": 260_000_000,
            "dead_money_total": 5_000_000
        }

        result = cap_helper.get_cap_summary(team_id=1)

        assert result["is_compliant"] is False
        assert result["available_space"] < 0

    def test_get_cap_summary_handles_missing_summary(self, cap_helper):
        """Test fallback when no cap summary exists in database."""
        cap_helper._mock_calc.calculate_team_cap_space.return_value = 255_400_000
        cap_helper._mock_db_api.get_team_cap_summary.return_value = None

        result = cap_helper.get_cap_summary(team_id=1)

        assert result["salary_cap_limit"] == 255_400_000
        assert result["total_spending"] == 0
        assert result["is_compliant"] is True

    def test_validate_signing_allows_valid_transaction(self, cap_helper):
        """Test that valid signings are approved."""
        cap_helper._mock_calc.calculate_team_cap_space.return_value = 20_000_000

        is_valid, error_msg = cap_helper.validate_signing(team_id=1, cap_hit=15_000_000)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_signing_rejects_over_cap(self, cap_helper):
        """Test that over-cap signings are rejected."""
        cap_helper._mock_calc.calculate_team_cap_space.return_value = 10_000_000

        is_valid, error_msg = cap_helper.validate_signing(team_id=1, cap_hit=15_000_000)

        assert is_valid is False
        assert "Insufficient cap space" in error_msg
        assert "Over cap by" in error_msg

    def test_calculate_signing_cap_hit_basic(self, cap_helper):
        """Test basic cap hit calculation."""
        # $20M total, $5M bonus, 4 years
        # Bonus proration: $5M / 4 = $1.25M
        # Base salary: $15M / 4 = $3.75M
        # Year 1 cap hit: $1.25M + $3.75M = $5M

        cap_hit = cap_helper.calculate_signing_cap_hit(
            total_value=20_000_000,
            signing_bonus=5_000_000,
            years=4
        )

        assert cap_hit == 5_000_000

    def test_calculate_signing_cap_hit_five_year_max_proration(self, cap_helper):
        """Test that signing bonus proration is capped at 5 years."""
        # $60M total, $30M bonus, 6 years
        # Bonus proration: $30M / 5 (capped) = $6M
        # Base salary: $30M / 6 = $5M
        # Year 1 cap hit: $6M + $5M = $11M

        cap_hit = cap_helper.calculate_signing_cap_hit(
            total_value=60_000_000,
            signing_bonus=30_000_000,
            years=6
        )

        assert cap_hit == 11_000_000

    def test_calculate_signing_cap_hit_handles_zero_years(self, cap_helper):
        """Test edge case of zero-year contract."""
        cap_hit = cap_helper.calculate_signing_cap_hit(
            total_value=10_000_000,
            signing_bonus=2_000_000,
            years=0
        )

        assert cap_hit == 0

    def test_estimate_rookie_cap_hit_first_pick(self, cap_helper):
        """Test rookie cap hit estimate for #1 overall pick."""
        cap_hit = cap_helper.estimate_rookie_cap_hit(overall_pick=1)
        assert cap_hit == 10_000_000

    def test_estimate_rookie_cap_hit_top_5(self, cap_helper):
        """Test rookie cap hit estimate for top 5 picks."""
        cap_hit_3 = cap_helper.estimate_rookie_cap_hit(overall_pick=3)
        cap_hit_5 = cap_helper.estimate_rookie_cap_hit(overall_pick=5)

        assert cap_hit_3 > cap_hit_5
        assert cap_hit_5 >= 7_000_000

    def test_estimate_rookie_cap_hit_seventh_round(self, cap_helper):
        """Test rookie cap hit estimate for 7th round pick."""
        cap_hit = cap_helper.estimate_rookie_cap_hit(overall_pick=220)
        assert cap_hit == 750_000

    def test_get_minimum_salary_rookie(self, cap_helper):
        """Test minimum salary for rookies."""
        min_salary = cap_helper.get_minimum_salary(years_pro=0)
        assert min_salary == 795_000

    def test_get_minimum_salary_veteran(self, cap_helper):
        """Test minimum salary for veterans."""
        min_salary = cap_helper.get_minimum_salary(years_pro=6)
        assert min_salary == 1_290_000

    def test_get_minimum_salary_caps_at_6_years(self, cap_helper):
        """Test that minimum salary caps at 6+ years."""
        min_salary_10 = cap_helper.get_minimum_salary(years_pro=10)
        min_salary_6 = cap_helper.get_minimum_salary(years_pro=6)
        assert min_salary_10 == min_salary_6


class TestCapHelperReleaseImpact:
    """Test suite for release impact calculations."""

    @pytest.fixture
    def cap_helper(self):
        """Create a CapHelper instance with mocked dependencies."""
        with patch('src.game_cycle.services.cap_helper.CapCalculator'), \
             patch('src.game_cycle.services.cap_helper.CapDatabaseAPI') as mock_db_api:

            from src.game_cycle.services.cap_helper import CapHelper

            helper = CapHelper(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025
            )
            helper._mock_db_api = mock_db_api.return_value
            return helper

    def test_release_impact_with_valid_contract(self, cap_helper):
        """Test release impact calculation with full contract details."""
        cap_helper._mock_db_api.get_player_contract.return_value = {
            "contract_id": 1,
            "player_id": 100,
            "total_value": 40_000_000,
            "contract_years": 4,
            "signing_bonus": 8_000_000
        }
        cap_helper._mock_db_api.get_contract_year_details.return_value = {
            "cap_hit": 12_000_000,
            "base_salary": 10_000_000,
            "prorated_signing_bonus": 2_000_000,
            "guaranteed_remaining": 5_000_000
        }

        result = cap_helper.calculate_release_impact(player_id=100, team_id=1)

        assert result["can_release"] is True
        assert result["cap_savings"] == 12_000_000
        assert result["dead_money"] == 7_000_000  # 2M prorated + 5M guaranteed
        assert result["net_cap_change"] == 5_000_000  # 12M - 7M

    def test_release_impact_no_contract(self, cap_helper):
        """Test release impact when no contract exists."""
        cap_helper._mock_db_api.get_player_contract.return_value = None

        result = cap_helper.calculate_release_impact(player_id=100, team_id=1)

        assert result["can_release"] is False
        assert result["cap_savings"] == 0
        assert result["dead_money"] == 0

    def test_release_impact_estimates_from_contract(self, cap_helper):
        """Test release impact estimation when year details missing."""
        cap_helper._mock_db_api.get_player_contract.return_value = {
            "contract_id": 1,
            "player_id": 100,
            "total_value": 20_000_000,
            "contract_years": 4,
            "signing_bonus": 4_000_000
        }
        cap_helper._mock_db_api.get_contract_year_details.return_value = None

        result = cap_helper.calculate_release_impact(player_id=100, team_id=1)

        assert result["can_release"] is True
        # Average yearly: 20M / 4 = 5M
        assert result["cap_savings"] == 5_000_000
        # Bonus proration: 4M / 4 = 1M
        assert result["dead_money"] == 1_000_000