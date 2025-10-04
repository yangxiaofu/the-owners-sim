"""
Integration Tests for Salary Cap System

Tests complete workflows involving all components:
- Full contract lifecycle (create → restructure → release)
- Team cap management across multiple contracts
- Compliance validation and enforcement
- Dynasty isolation in complex scenarios
- Real-world NFL contract simulations
"""

import pytest
from datetime import date


class TestFullContractLifecycle:
    """Test complete contract lifecycle from creation to termination."""

    def test_create_manage_release_contract(self, contract_manager, cap_validator,
                                           test_team_id, test_player_id,
                                           test_season, test_dynasty_id):
        """Test full lifecycle: create → manage → release."""
        # Step 1: Create contract
        contract_id = contract_manager.create_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            base_salaries=[1_000_000, 6_000_000, 8_000_000, 9_000_000],
            guaranteed_amounts=[1_000_000, 6_000_000, 0, 0],
            contract_type='VETERAN'
        )

        assert contract_id is not None

        # Step 2: Verify contract details
        details = contract_manager.get_contract_details(contract_id)
        assert details['contract']['is_active'] == 1
        assert len(details['year_details']) == 4

        # Step 3: Restructure in year 2
        restructure_result = contract_manager.restructure_contract(
            contract_id=contract_id,
            year_to_restructure=2,
            amount_to_convert=4_000_000,
            dynasty_id=test_dynasty_id
        )

        assert restructure_result['success'] == True
        assert restructure_result['current_year_savings'] == 3_000_000

        # Step 4: Release player in year 3
        release_result = contract_manager.release_player(
            contract_id=contract_id,
            release_date=f"{test_season + 2}-03-15",
            june_1_designation=False,
            dynasty_id=test_dynasty_id
        )

        assert release_result['success'] == True
        assert release_result['dead_money_current_year'] > 0

        # Step 5: Verify contract is voided
        final_details = contract_manager.get_contract_details(contract_id)
        assert final_details['contract']['is_active'] == 0


class TestTeamCapManagement:
    """Test team cap management with multiple contracts."""

    def test_multiple_contracts_team_cap(self, contract_manager, cap_calculator,
                                        cap_database_api, initialized_team_cap,
                                        test_team_id, test_season, test_dynasty_id):
        """Test managing team cap with multiple contracts."""
        # Create multiple contracts
        contracts = []

        # QB - $40M total
        qb_contract = contract_manager.create_contract(
            player_id=1001,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            base_salaries=[1_000_000, 6_000_000, 8_000_000, 9_000_000],
            guaranteed_amounts=[1_000_000, 6_000_000, 0, 0],
            contract_type='VETERAN'
        )
        contracts.append(qb_contract)

        # WR - $20M total
        wr_contract = contract_manager.create_contract(
            player_id=1002,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=3,
            total_value=20_000_000,
            signing_bonus=8_000_000,
            base_salaries=[2_000_000, 5_000_000, 5_000_000],
            guaranteed_amounts=[2_000_000, 5_000_000, 0],
            contract_type='VETERAN'
        )
        contracts.append(wr_contract)

        # DE - $15M total
        de_contract = contract_manager.create_contract(
            player_id=1003,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=3,
            total_value=15_000_000,
            signing_bonus=6_000_000,
            base_salaries=[1_500_000, 3_750_000, 3_750_000],
            guaranteed_amounts=[1_500_000, 0, 0],
            contract_type='VETERAN'
        )
        contracts.append(de_contract)

        # Calculate total cap hit for year 1
        total_cap_hit = 0
        for contract_id in contracts:
            details = contract_manager.get_contract_details(contract_id)
            year_1_detail = details['year_details'][0]
            total_cap_hit += year_1_detail['total_cap_hit']

        # QB Year 1: 1M + 4M = 5M
        # WR Year 1: 2M + 2.67M = 4.67M (rounds to 4M)
        # DE Year 1: 1.5M + 2M = 3.5M
        # Total ≈ 12.5M
        assert total_cap_hit > 0

        # Update team cap usage
        cap_database_api.update_team_cap_usage(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            active_contracts_total=total_cap_hit,
            dead_money_total=0,
            ltbe_incentives_total=0,
            practice_squad_total=0
        )

        # Verify cap space
        cap_space = cap_calculator.calculate_team_cap_space(
            test_team_id, test_season, test_dynasty_id
        )

        # Should have ~266M available (279M - 12.5M)
        assert cap_space > 260_000_000

    def test_team_over_cap_scenario(self, contract_manager, cap_calculator,
                                   cap_database_api, cap_validator,
                                   test_team_id, test_season, test_dynasty_id):
        """Test scenario where team goes over cap and must fix it."""
        # Initialize team cap
        cap_database_api.initialize_team_cap(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            salary_cap_limit=279_200_000,
            carryover_from_previous=0
        )

        # Create large contracts that exceed cap
        # QB - $50M year 1 cap hit
        contract_manager.create_contract(
            player_id=2001,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=1,
            total_value=50_000_000,
            signing_bonus=0,
            base_salaries=[50_000_000],
            guaranteed_amounts=[50_000_000],
            contract_type='VETERAN'
        )

        # Update team cap
        cap_database_api.update_team_cap_usage(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            active_contracts_total=50_000_000,
            dead_money_total=0,
            ltbe_incentives_total=0,
            practice_squad_total=0
        )

        # Add more contracts to push over cap
        # WR - $100M year 1 cap hit
        contract_manager.create_contract(
            player_id=2002,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=1,
            total_value=100_000_000,
            signing_bonus=0,
            base_salaries=[100_000_000],
            guaranteed_amounts=[100_000_000],
            contract_type='VETERAN'
        )

        # DE - $150M year 1 cap hit
        contract_manager.create_contract(
            player_id=2003,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=1,
            total_value=150_000_000,
            signing_bonus=0,
            base_salaries=[150_000_000],
            guaranteed_amounts=[150_000_000],
            contract_type='VETERAN'
        )

        # Update with total usage (300M)
        cap_database_api.update_team_cap_usage(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            active_contracts_total=300_000_000,
            dead_money_total=0,
            ltbe_incentives_total=0,
            practice_squad_total=0
        )

        # Check compliance - should be over cap
        is_compliant, message = cap_validator.check_league_year_compliance(
            test_team_id, test_season, test_dynasty_id
        )

        assert is_compliant == False
        assert "over" in message.lower()

        # Verify cap space is negative
        cap_space = cap_calculator.calculate_team_cap_space(
            test_team_id, test_season, test_dynasty_id
        )

        assert cap_space < 0  # Over cap


class TestComplianceValidation:
    """Test compliance validation across different scenarios."""

    def test_compliant_team(self, contract_manager, cap_calculator, cap_database_api,
                           cap_validator, test_team_id, test_season, test_dynasty_id):
        """Test validation of compliant team."""
        # Initialize team cap
        cap_database_api.initialize_team_cap(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            salary_cap_limit=279_200_000,
            carryover_from_previous=0
        )

        # Create modest contracts (under cap)
        contract_manager.create_contract(
            player_id=3001,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            base_salaries=[1_000_000, 6_000_000, 8_000_000, 9_000_000],
            guaranteed_amounts=[1_000_000, 6_000_000, 0, 0],
            contract_type='VETERAN'
        )

        # Update team cap (5M year 1)
        cap_database_api.update_team_cap_usage(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            active_contracts_total=5_000_000,
            dead_money_total=0,
            ltbe_incentives_total=0,
            practice_squad_total=0
        )

        # Check compliance
        is_compliant, message = cap_validator.check_league_year_compliance(
            test_team_id, test_season, test_dynasty_id
        )

        assert is_compliant == True
        assert "compliant" in message.lower()

    def test_compliance_report_generation(self, contract_manager, cap_database_api,
                                         cap_validator, test_team_id, test_season,
                                         test_dynasty_id):
        """Test comprehensive compliance report generation."""
        # Initialize team cap
        cap_database_api.initialize_team_cap(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            salary_cap_limit=279_200_000,
            carryover_from_previous=0
        )

        # Create contract
        contract_manager.create_contract(
            player_id=4001,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            base_salaries=[1_000_000, 6_000_000, 8_000_000, 9_000_000],
            guaranteed_amounts=[1_000_000, 6_000_000, 0, 0],
            contract_type='VETERAN'
        )

        # Update cap
        cap_database_api.update_team_cap_usage(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            active_contracts_total=5_000_000,
            dead_money_total=0,
            ltbe_incentives_total=0,
            practice_squad_total=0
        )

        # Generate report
        report = cap_validator.generate_compliance_report(
            test_team_id, test_season, test_dynasty_id
        )

        # Verify report structure
        assert 'team_id' in report
        assert 'season' in report
        assert 'cap_compliance' in report
        assert 'cap_space' in report
        assert 'cap_summary' in report
        assert 'violations' in report
        assert 'warnings' in report
        assert 'recommendations' in report

        # Should be compliant
        assert report['cap_compliance']['is_compliant'] == True


class TestDynastyIsolationComplex:
    """Test dynasty isolation in complex multi-team scenarios."""

    def test_multiple_dynasties_same_team(self, contract_manager, cap_database_api,
                                         cap_calculator, test_team_id, test_season):
        """Test that same team in different dynasties has separate caps."""
        dynasty_a = "dynasty_a"
        dynasty_b = "dynasty_b"

        # Initialize caps for both dynasties
        cap_database_api.initialize_team_cap(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=dynasty_a,
            salary_cap_limit=279_200_000,
            carryover_from_previous=0
        )

        cap_database_api.initialize_team_cap(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=dynasty_b,
            salary_cap_limit=279_200_000,
            carryover_from_previous=0
        )

        # Create contract in dynasty A
        contract_a = contract_manager.create_contract(
            player_id=5001,
            team_id=test_team_id,
            dynasty_id=dynasty_a,
            start_year=test_season,
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            base_salaries=[1_000_000, 6_000_000, 8_000_000, 9_000_000],
            guaranteed_amounts=[1_000_000, 6_000_000, 0, 0],
            contract_type='VETERAN'
        )

        # Create different contract in dynasty B
        contract_b = contract_manager.create_contract(
            player_id=5001,  # Same player ID, different dynasty
            team_id=test_team_id,
            dynasty_id=dynasty_b,
            start_year=test_season,
            contract_years=3,
            total_value=30_000_000,
            signing_bonus=12_000_000,
            base_salaries=[2_000_000, 5_000_000, 5_000_000],
            guaranteed_amounts=[2_000_000, 5_000_000, 0],
            contract_type='VETERAN'
        )

        # Update caps separately
        cap_database_api.update_team_cap_usage(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=dynasty_a,
            active_contracts_total=5_000_000,  # QB contract year 1
            dead_money_total=0,
            ltbe_incentives_total=0,
            practice_squad_total=0
        )

        cap_database_api.update_team_cap_usage(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=dynasty_b,
            active_contracts_total=6_000_000,  # Different contract year 1
            dead_money_total=0,
            ltbe_incentives_total=0,
            practice_squad_total=0
        )

        # Verify isolation - cap space should be different
        cap_space_a = cap_calculator.calculate_team_cap_space(
            test_team_id, test_season, dynasty_a
        )

        cap_space_b = cap_calculator.calculate_team_cap_space(
            test_team_id, test_season, dynasty_b
        )

        assert cap_space_a != cap_space_b
        assert cap_space_a == 279_200_000 - 5_000_000
        assert cap_space_b == 279_200_000 - 6_000_000


class TestRealWorldScenarios:
    """Test real-world NFL contract scenarios."""

    def test_patrick_mahomes_style_contract(self, contract_manager, cap_calculator,
                                           cap_database_api, test_team_id, test_season,
                                           test_dynasty_id):
        """Test 10-year mega-contract similar to Patrick Mahomes."""
        # Initialize team cap
        cap_database_api.initialize_team_cap(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            salary_cap_limit=279_200_000,
            carryover_from_previous=0
        )

        # Mahomes: 10-year, $450M, $40M signing bonus
        mahomes_contract = contract_manager.create_contract(
            player_id=15,  # Mahomes
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=10,
            total_value=450_000_000,
            signing_bonus=40_000_000,
            base_salaries=[
                5_000_000,   # Year 1
                24_000_000,  # Year 2
                40_000_000,  # Year 3
                45_000_000,  # Year 4
                45_000_000,  # Year 5
                46_000_000,  # Year 6
                49_000_000,  # Year 7
                52_000_000,  # Year 8
                57_000_000,  # Year 9
                47_000_000   # Year 10
            ],
            guaranteed_amounts=[5_000_000, 24_000_000, 40_000_000, 0, 0, 0, 0, 0, 0, 0],
            contract_type='VETERAN'
        )

        # Verify contract creation
        details = contract_manager.get_contract_details(mahomes_contract)
        assert details['contract']['total_value'] == 450_000_000

        # Verify 5-year max proration (40M / 5 = 8M per year)
        year_1_detail = details['year_details'][0]
        assert year_1_detail['signing_bonus_proration'] == 8_000_000

        # Year 1 cap hit: 5M base + 8M proration = 13M
        assert year_1_detail['total_cap_hit'] == 13_000_000

    def test_russell_wilson_dead_money(self, contract_manager, cap_calculator,
                                       cap_database_api, test_team_id, test_season,
                                       test_dynasty_id):
        """Test massive dead money hit similar to Russell Wilson."""
        # Initialize team cap
        cap_database_api.initialize_team_cap(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            salary_cap_limit=279_200_000,
            carryover_from_previous=0
        )

        # Wilson-style contract: Large signing bonus, then released
        wilson_contract = contract_manager.create_contract(
            player_id=3,  # Wilson
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=5,
            total_value=245_000_000,
            signing_bonus=100_000_000,  # Huge signing bonus
            base_salaries=[5_000_000, 19_000_000, 22_000_000, 49_000_000, 50_000_000],
            guaranteed_amounts=[5_000_000, 19_000_000, 22_000_000, 0, 0],
            contract_type='VETERAN'
        )

        # Release after year 2
        release_result = contract_manager.release_player(
            contract_id=wilson_contract,
            release_date=f"{test_season + 1}-03-15",
            june_1_designation=False,
            dynasty_id=test_dynasty_id
        )

        # Should have massive dead money
        # Remaining proration: 100M / 5 = 20M per year * 3 years = 60M
        # Plus guaranteed year 3 base: 22M
        # Total: 82M dead money
        assert release_result['dead_money_current_year'] >= 80_000_000

    def test_franchise_tag_workflow(self, contract_manager, cap_database_api,
                                   cap_calculator, test_team_id, test_season,
                                   test_dynasty_id):
        """Test franchise tag to long-term contract workflow."""
        # Initialize team cap
        cap_database_api.initialize_team_cap(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            salary_cap_limit=279_200_000,
            carryover_from_previous=0
        )

        # Step 1: Apply franchise tag
        tag_id = cap_database_api.insert_franchise_tag(
            team_id=test_team_id,
            player_id=7001,
            season=test_season,
            dynasty_id=test_dynasty_id,
            tag_type='EXCLUSIVE',
            tag_amount=32_000_000,
            times_tagged=1
        )

        assert tag_id is not None

        # Update cap with tag
        cap_database_api.update_team_cap_usage(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            active_contracts_total=32_000_000,
            dead_money_total=0,
            ltbe_incentives_total=0,
            practice_squad_total=0
        )

        # Step 2: Sign to long-term contract in next season
        long_term_contract = contract_manager.create_contract(
            player_id=7001,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season + 1,
            contract_years=4,
            total_value=100_000_000,
            signing_bonus=40_000_000,
            base_salaries=[5_000_000, 15_000_000, 20_000_000, 20_000_000],
            guaranteed_amounts=[5_000_000, 15_000_000, 20_000_000, 0],
            contract_type='VETERAN'
        )

        # Verify long-term contract
        details = contract_manager.get_contract_details(long_term_contract)
        assert details['contract']['total_value'] == 100_000_000
        assert details['contract']['start_year'] == test_season + 1


class TestCapManipulationStrategies:
    """Test common cap manipulation strategies used by NFL teams."""

    def test_backloaded_contract(self, contract_manager, test_team_id, test_season,
                                test_dynasty_id):
        """Test backloaded contract structure."""
        # Create backloaded contract (low early years, high later years)
        contract_id = contract_manager.create_contract(
            player_id=8001,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=5,
            total_value=100_000_000,
            signing_bonus=20_000_000,
            base_salaries=[5_000_000, 10_000_000, 15_000_000, 25_000_000, 25_000_000],
            guaranteed_amounts=[5_000_000, 10_000_000, 0, 0, 0],
            contract_type='VETERAN'
        )

        details = contract_manager.get_contract_details(contract_id)
        year_details = details['year_details']

        # Verify cap hits increase over time
        cap_hit_year_1 = year_details[0]['total_cap_hit']
        cap_hit_year_5 = year_details[4]['total_cap_hit']

        assert cap_hit_year_5 > cap_hit_year_1

    def test_void_years_strategy(self, contract_manager, test_team_id, test_season,
                                 test_dynasty_id):
        """Test void years strategy (reduce current cap hit)."""
        # Create contract with void years structure
        # 3 real years + 2 void years for proration
        contract_id = contract_manager.create_contract(
            player_id=8002,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=5,
            total_value=50_000_000,
            signing_bonus=25_000_000,  # Spread over 5 years
            base_salaries=[5_000_000, 10_000_000, 10_000_000, 0, 0],  # Last 2 are void
            guaranteed_amounts=[5_000_000, 10_000_000, 0, 0, 0],
            contract_type='VETERAN'
        )

        details = contract_manager.get_contract_details(contract_id)

        # Proration: 25M / 5 = 5M per year (including void years)
        # Year 1: 5M base + 5M proration = 10M (vs 5M base + 8.33M without void = 13.33M)
        year_1_detail = details['year_details'][0]
        assert year_1_detail['signing_bonus_proration'] == 5_000_000
        assert year_1_detail['total_cap_hit'] == 10_000_000


class TestTransactionHistory:
    """Test transaction logging and history tracking."""

    def test_transaction_logging(self, contract_manager, cap_database_api,
                                test_team_id, test_season, test_dynasty_id):
        """Test that all transactions are properly logged."""
        # Initialize cap
        cap_database_api.initialize_team_cap(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            salary_cap_limit=279_200_000,
            carryover_from_previous=0
        )

        # Transaction 1: Sign player
        contract_id = contract_manager.create_contract(
            player_id=9001,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            base_salaries=[1_000_000, 6_000_000, 8_000_000, 9_000_000],
            guaranteed_amounts=[1_000_000, 6_000_000, 0, 0],
            contract_type='VETERAN'
        )

        cap_database_api.log_transaction(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            transaction_type='SIGNING',
            transaction_date=date.today().isoformat(),
            description=f'Signed player 9001 to 4-year contract',
            cap_impact=5_000_000  # Year 1 cap hit
        )

        # Transaction 2: Restructure
        contract_manager.restructure_contract(
            contract_id=contract_id,
            year_to_restructure=2,
            amount_to_convert=4_000_000,
            dynasty_id=test_dynasty_id
        )

        cap_database_api.log_transaction(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            transaction_type='RESTRUCTURE',
            transaction_date=date.today().isoformat(),
            description=f'Restructured contract {contract_id}',
            cap_impact=-3_000_000  # Cap savings
        )

        # Transaction 3: Release
        contract_manager.release_player(
            contract_id=contract_id,
            release_date=f"{test_season + 2}-03-15",
            june_1_designation=False,
            dynasty_id=test_dynasty_id
        )

        cap_database_api.log_transaction(
            team_id=test_team_id,
            season=test_season + 2,
            dynasty_id=test_dynasty_id,
            transaction_type='RELEASE',
            transaction_date=f"{test_season + 2}-03-15",
            description=f'Released player 9001',
            cap_impact=8_000_000  # Dead money
        )

        # Retrieve all transactions
        transactions = cap_database_api.get_team_transactions(
            test_team_id, test_season, test_dynasty_id
        )

        # Should have at least 2 transactions for this season (signing + restructure)
        assert len(transactions) >= 2

        # Verify transaction types
        transaction_types = [t['transaction_type'] for t in transactions]
        assert 'SIGNING' in transaction_types
        assert 'RESTRUCTURE' in transaction_types
