"""
Unit Tests for CapCalculator

Tests all core salary cap calculation formulas including:
- Signing bonus proration (5-year max rule)
- Dead money calculations
- Contract restructure impact
- Cap space calculations (top-51 vs 53-man)
- Transaction validation
- Spending floor compliance

Based on 2024-2025 NFL CBA rules.
"""

import pytest
from salary_cap.cap_calculator import CapCalculator


class TestSigningBonusProration:
    """Test signing bonus proration formula with 5-year max rule."""

    def test_4_year_contract_proration(self, cap_calculator):
        """Test proration for 4-year contract."""
        proration = cap_calculator.calculate_signing_bonus_proration(
            signing_bonus=20_000_000,
            contract_years=4
        )
        # $20M / 4 years = $5M per year
        assert proration == 5_000_000

    def test_5_year_max_rule_with_7_year_contract(self, cap_calculator):
        """
        Test that 7-year contract is still prorated over 5 years max.

        This is the KEY rule: bonuses CANNOT be prorated beyond 5 years.
        """
        proration = cap_calculator.calculate_signing_bonus_proration(
            signing_bonus=35_000_000,
            contract_years=7
        )
        # $35M / 5 years (NOT 7!) = $7M per year
        assert proration == 7_000_000

    def test_5_year_max_rule_with_10_year_contract(self, cap_calculator):
        """Test extreme case: 10-year contract still uses 5-year max."""
        proration = cap_calculator.calculate_signing_bonus_proration(
            signing_bonus=50_000_000,
            contract_years=10
        )
        # $50M / 5 years (NOT 10!) = $10M per year
        assert proration == 10_000_000

    def test_1_year_contract(self, cap_calculator):
        """Test 1-year contract (full bonus in single year)."""
        proration = cap_calculator.calculate_signing_bonus_proration(
            signing_bonus=10_000_000,
            contract_years=1
        )
        # $10M / 1 year = $10M
        assert proration == 10_000_000

    def test_zero_signing_bonus(self, cap_calculator):
        """Test contract with no signing bonus."""
        proration = cap_calculator.calculate_signing_bonus_proration(
            signing_bonus=0,
            contract_years=4
        )
        assert proration == 0

    def test_invalid_contract_years_raises_error(self, cap_calculator):
        """Test that zero or negative years raises error."""
        with pytest.raises(ValueError):
            cap_calculator.calculate_signing_bonus_proration(
                signing_bonus=10_000_000,
                contract_years=0
            )

        with pytest.raises(ValueError):
            cap_calculator.calculate_signing_bonus_proration(
                signing_bonus=10_000_000,
                contract_years=-1
            )


class TestDeadMoneyCalculations:
    """Test dead money calculations for player releases."""

    def test_dead_money_standard_release_year_3_of_5(
        self,
        cap_calculator,
        cap_database_api,
        test_team_id,
        test_player_id,
        test_dynasty_id
    ):
        """
        Test dead money for standard release in Year 3 of 5-year contract.

        Contract: 5 years, $25M signing bonus ($5M/year proration)
        Release: After Year 2 (start of Year 3)
        Expected: 3 remaining years × $5M = $15M dead money
        """
        # Create contract
        contract_id = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=2024,
            end_year=2028,
            contract_years=5,
            contract_type="VETERAN",
            total_value=50_000_000,
            signing_bonus=25_000_000,
            signing_bonus_proration=5_000_000
        )

        # Add year details
        for year in range(1, 6):
            cap_database_api.insert_contract_year_details(
                contract_id=contract_id,
                contract_year=year,
                season_year=2023 + year,
                base_salary=5_000_000,
                total_cap_hit=10_000_000,
                cash_paid=5_000_000 if year > 1 else 30_000_000,
                signing_bonus_proration=5_000_000
            )

        # Calculate dead money for release in Year 3 (2026)
        current_dead, next_year_dead = cap_calculator.calculate_dead_money(
            contract_id=contract_id,
            release_year=2026,
            june_1_designation=False
        )

        # All remaining proration (3 years × $5M) = $15M in current year
        assert current_dead == 15_000_000
        assert next_year_dead == 0

    def test_dead_money_june_1_designation(
        self,
        cap_calculator,
        cap_database_api,
        test_team_id,
        test_player_id,
        test_dynasty_id
    ):
        """
        Test June 1 designation splits dead money across 2 years.

        Same contract as above, but with June 1 designation:
        - Current year: 1 year of proration = $5M
        - Next year: 2 years of proration = $10M
        """
        # Create contract
        contract_id = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=2024,
            end_year=2028,
            contract_years=5,
            contract_type="VETERAN",
            total_value=50_000_000,
            signing_bonus=25_000_000,
            signing_bonus_proration=5_000_000
        )

        # Add year details
        for year in range(1, 6):
            cap_database_api.insert_contract_year_details(
                contract_id=contract_id,
                contract_year=year,
                season_year=2023 + year,
                base_salary=5_000_000,
                total_cap_hit=10_000_000,
                cash_paid=5_000_000,
                signing_bonus_proration=5_000_000
            )

        # Calculate dead money with June 1 designation
        current_dead, next_year_dead = cap_calculator.calculate_dead_money(
            contract_id=contract_id,
            release_year=2026,
            june_1_designation=True
        )

        # Current year: $5M (1 year proration)
        # Next year: $10M (2 years proration)
        assert current_dead == 5_000_000
        assert next_year_dead == 10_000_000

    def test_dead_money_with_guaranteed_salary(
        self,
        cap_calculator,
        cap_database_api,
        test_team_id,
        test_player_id,
        test_dynasty_id
    ):
        """
        Test dead money includes guaranteed base salary.

        Dead money = remaining bonus proration + guaranteed salary
        """
        # Create contract with guaranteed salaries
        contract_id = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=2024,
            end_year=2027,
            contract_years=4,
            contract_type="VETERAN",
            total_value=40_000_000,
            signing_bonus=16_000_000,
            signing_bonus_proration=4_000_000
        )

        # Year 1: $1M base (guaranteed)
        # Year 2: $6M base (guaranteed)
        # Years 3-4: Not guaranteed
        year_configs = [
            (1, 2024, 1_000_000, True),
            (2, 2025, 6_000_000, True),
            (3, 2026, 8_000_000, False),
            (4, 2027, 9_000_000, False)
        ]

        for year, season, base_salary, guaranteed in year_configs:
            cap_database_api.insert_contract_year_details(
                contract_id=contract_id,
                contract_year=year,
                season_year=season,
                base_salary=base_salary,
                total_cap_hit=base_salary + 4_000_000,
                cash_paid=base_salary,
                signing_bonus_proration=4_000_000,
                base_salary_guaranteed=guaranteed
            )

        # Release after Year 1 (start of Year 2)
        # Dead money = 3 years bonus ($12M) + Year 2 guaranteed ($6M) = $18M
        current_dead, next_year_dead = cap_calculator.calculate_dead_money(
            contract_id=contract_id,
            release_year=2025,
            june_1_designation=False
        )

        assert current_dead == 18_000_000


class TestContractRestructureCalculations:
    """Test contract restructure impact calculations."""

    def test_restructure_creates_cap_savings(self, cap_calculator):
        """
        Test restructure converts base salary to bonus for immediate savings.

        Example: Year 2 of 4-year contract
        Convert $9M base to bonus with 3 years remaining
        - New proration: $9M / 3 = $3M/year
        - Current year savings: $9M - $3M = $6M
        - Future years: +$3M each year
        """
        impact = cap_calculator.calculate_restructure_impact(
            base_salary_to_convert=9_000_000,
            remaining_contract_years=3
        )

        assert impact['cap_savings_current_year'] == 6_000_000
        assert impact['annual_increase_future_years'] == 3_000_000
        assert impact['new_proration'] == 3_000_000
        assert impact['dead_money_increase'] == 6_000_000  # 2 years × $3M

    def test_restructure_with_1_year_remaining_no_savings(self, cap_calculator):
        """
        Test restructure with only 1 year left provides no savings.

        With 1 year remaining, full amount still hits this year's cap.
        """
        impact = cap_calculator.calculate_restructure_impact(
            base_salary_to_convert=10_000_000,
            remaining_contract_years=1
        )

        # $10M / 1 year = $10M proration (same as base salary)
        assert impact['cap_savings_current_year'] == 0
        assert impact['annual_increase_future_years'] == 10_000_000
        assert impact['dead_money_increase'] == 0  # No future years


class TestCapSpaceCalculations:
    """Test team cap space calculations."""

    def test_cap_space_with_no_contracts(
        self,
        cap_calculator,
        initialized_team_cap,
        test_team_id,
        test_season,
        test_dynasty_id
    ):
        """
        Test cap space with no contracts = full cap available.
        """
        cap_space = cap_calculator.calculate_team_cap_space(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id
        )

        # 2025 cap = $279.2M, no contracts = full amount available
        assert cap_space == 279_200_000

    def test_cap_space_decreases_with_contracts(
        self,
        cap_calculator,
        cap_database_api,
        contract_manager,
        initialized_team_cap,
        test_team_id,
        test_player_id,
        test_season,
        test_dynasty_id
    ):
        """
        Test that signing contract reduces available cap space.
        """
        # Get initial cap space
        initial_cap = cap_calculator.calculate_team_cap_space(
            test_team_id, test_season, test_dynasty_id
        )

        # Create contract with $10M Year 1 cap hit
        contract_id = contract_manager.create_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            base_salaries=[1_000_000, 8_000_000, 10_000_000, 11_000_000],
            season=test_season
        )

        # Update team cap with this contract
        # Year 1 cap hit = $1M base + $4M proration = $5M
        cap_database_api.update_team_cap(
            test_team_id,
            test_season,
            test_dynasty_id,
            active_contracts_total=5_000_000
        )

        # Calculate new cap space
        new_cap = cap_calculator.calculate_team_cap_space(
            test_team_id, test_season, test_dynasty_id
        )

        # Should decrease by $5M
        assert new_cap == initial_cap - 5_000_000


class TestTransactionValidation:
    """Test transaction validation against cap space."""

    def test_validate_transaction_with_sufficient_cap(
        self,
        cap_calculator,
        initialized_team_cap,
        test_team_id,
        test_season,
        test_dynasty_id
    ):
        """Test validation passes with sufficient cap space."""
        # Try to sign player for $10M (team has $279.2M available)
        is_valid, message = cap_calculator.validate_transaction(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            cap_impact=-10_000_000
        )

        assert is_valid is True
        assert message == ""

    def test_validate_transaction_with_insufficient_cap(
        self,
        cap_calculator,
        cap_database_api,
        initialized_team_cap,
        test_team_id,
        test_season,
        test_dynasty_id
    ):
        """Test validation fails when over cap."""
        # Set team to have only $5M cap space
        cap_database_api.update_team_cap(
            test_team_id,
            test_season,
            test_dynasty_id,
            active_contracts_total=274_200_000  # Leaves $5M
        )

        # Try to sign player for $10M (only $5M available)
        is_valid, message = cap_calculator.validate_transaction(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            cap_impact=-10_000_000
        )

        assert is_valid is False
        assert "Insufficient cap space" in message
        assert "5,000,000" in message  # Shows shortage amount


class TestSpendingFloorCompliance:
    """Test 89% spending floor calculations."""

    def test_spending_floor_compliance_when_met(
        self,
        cap_calculator,
        cap_database_api,
        test_team_id,
        test_dynasty_id
    ):
        """
        Test spending floor compliance when team meets 89% requirement.

        4-year period: 2021-2024
        Total caps: Assume $1B
        Required: $890M (89%)
        Team spent: $900M
        Result: Compliant
        """
        # Initialize caps for 4-year period
        for year in range(2021, 2025):
            cap_database_api.initialize_team_cap(
                test_team_id, year, test_dynasty_id,
                salary_cap_limit=250_000_000,
                carryover_from_previous=0
            )
            # Set cash spending to 90% (above 89% floor)
            cap_database_api.update_team_cap(
                test_team_id, year, test_dynasty_id,
                cash_spent_this_year=225_000_000
            )

        # Check compliance
        is_compliant, shortfall = cap_calculator.check_spending_floor_compliance(
            test_team_id, 2021, 2024, test_dynasty_id
        )

        # Total spent: 4 × $225M = $900M
        # Required: 4 × $250M × 0.89 = $890M
        # Compliant with $10M buffer
        assert is_compliant is True
        assert shortfall == 0

    def test_spending_floor_violation_calculates_shortfall(
        self,
        cap_calculator,
        cap_database_api,
        test_team_id,
        test_dynasty_id
    ):
        """
        Test spending floor violation calculates correct shortfall.

        Team spent only 80%, should have penalty.
        """
        # Initialize caps for 4-year period
        for year in range(2021, 2025):
            cap_database_api.initialize_team_cap(
                test_team_id, year, test_dynasty_id,
                salary_cap_limit=250_000_000,
                carryover_from_previous=0
            )
            # Set cash spending to only 80%
            cap_database_api.update_team_cap(
                test_team_id, year, test_dynasty_id,
                cash_spent_this_year=200_000_000
            )

        # Check compliance
        is_compliant, shortfall = cap_calculator.check_spending_floor_compliance(
            test_team_id, 2021, 2024, test_dynasty_id
        )

        # Total spent: 4 × $200M = $800M
        # Required: 4 × $250M × 0.89 = $890M
        # Shortfall: $90M
        assert is_compliant is False
        assert shortfall == 90_000_000


class TestRealWorldValidation:
    """Test calculations against real NFL contracts."""

    def test_patrick_mahomes_contract_proration(self, cap_calculator):
        """
        Validate against Patrick Mahomes' real contract.

        Real contract: 10 years, ~$450M, $141M signing bonus
        Bonus prorates over 5 years (max): $141M / 5 = $28.2M/year
        """
        proration = cap_calculator.calculate_signing_bonus_proration(
            signing_bonus=141_000_000,
            contract_years=10
        )

        # Should use 5-year max, not 10 years
        expected_proration = 141_000_000 // 5  # $28.2M
        assert proration == expected_proration

    def test_russell_wilson_dead_money_scenario(self, cap_calculator):
        """
        Test scenario similar to Russell Wilson's $85M dead cap hit.

        This was one of the largest dead money hits in NFL history.
        """
        # Simplified version: $50M remaining bonus + $35M guaranteed salary
        current_dead, next_year_dead = cap_calculator.calculate_dead_money_from_values(
            remaining_bonus_proration=50_000_000,
            guaranteed_salary=35_000_000,
            annual_proration=10_000_000,
            june_1_designation=False
        )

        total_dead = current_dead + next_year_dead
        # Should be close to $85M
        assert total_dead == 85_000_000
        assert current_dead == 85_000_000  # All in one year
        assert next_year_dead == 0
