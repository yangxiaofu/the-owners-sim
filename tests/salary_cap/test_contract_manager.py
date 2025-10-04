"""
Unit Tests for ContractManager

Tests high-level contract lifecycle operations including:
- Contract creation (veteran and rookie)
- Contract restructuring
- Player releases (standard and June 1)
- Contract extensions
- Contract details retrieval
- Dead money projections
- Integration with CapCalculator and CapDatabaseAPI
"""

import pytest
from datetime import date


class TestContractCreation:
    """Test contract creation operations."""

    def test_create_veteran_contract(self, contract_manager, test_team_id, test_player_id,
                                     test_season, test_dynasty_id, sample_veteran_contract):
        """Test creating a veteran contract."""
        contract_id = contract_manager.create_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            **sample_veteran_contract
        )

        assert contract_id is not None
        assert contract_id > 0

        # Verify contract was created correctly
        details = contract_manager.get_contract_details(contract_id)
        assert details['contract']['contract_id'] == contract_id
        assert details['contract']['player_id'] == test_player_id
        assert details['contract']['team_id'] == test_team_id
        assert details['contract']['contract_type'] == 'VETERAN'
        assert details['contract']['total_value'] == 40_000_000
        assert details['contract']['signing_bonus'] == 16_000_000

    def test_create_rookie_contract(self, contract_manager, test_team_id, test_player_id,
                                    test_season, test_dynasty_id, sample_rookie_contract):
        """Test creating a rookie contract."""
        contract_id = contract_manager.create_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            **sample_rookie_contract
        )

        assert contract_id is not None
        assert contract_id > 0

        # Verify rookie contract specifics
        details = contract_manager.get_contract_details(contract_id)
        assert details['contract']['contract_type'] == 'ROOKIE'
        assert details['contract']['total_value'] == 20_000_000
        assert details['contract']['total_guaranteed'] == 20_000_000  # Fully guaranteed

    def test_create_contract_with_year_details(self, contract_manager, test_team_id,
                                              test_player_id, test_season, test_dynasty_id,
                                              sample_veteran_contract):
        """Test that contract creation generates correct year-by-year details."""
        contract_id = contract_manager.create_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            **sample_veteran_contract
        )

        # Verify year details were created
        details = contract_manager.get_contract_details(contract_id)
        year_details = details['year_details']

        assert len(year_details) == 4  # 4-year contract

        # Verify proration (16M / 4 = 4M per year)
        for detail in year_details:
            assert detail['signing_bonus_proration'] == 4_000_000

        # Verify base salaries match input
        base_salaries = [d['base_salary'] for d in year_details]
        assert base_salaries == sample_veteran_contract['base_salaries']

    def test_contract_cap_hit_calculation(self, contract_manager, test_team_id,
                                         test_player_id, test_season, test_dynasty_id):
        """Test that cap hits are calculated correctly."""
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

        details = contract_manager.get_contract_details(contract_id)
        year_details = details['year_details']

        # Year 1: 1M base + 4M proration = 5M cap hit
        assert year_details[0]['total_cap_hit'] == 5_000_000

        # Year 2: 6M base + 4M proration = 10M cap hit
        assert year_details[1]['total_cap_hit'] == 10_000_000

        # Year 3: 8M base + 4M proration = 12M cap hit
        assert year_details[2]['total_cap_hit'] == 12_000_000

        # Year 4: 9M base + 4M proration = 13M cap hit
        assert year_details[3]['total_cap_hit'] == 13_000_000


class TestContractRestructuring:
    """Test contract restructuring operations."""

    def test_restructure_contract_basic(self, contract_manager, test_team_id,
                                        test_player_id, test_season, test_dynasty_id):
        """Test basic contract restructuring."""
        # Create contract
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

        # Restructure year 2: convert 4M base salary to bonus
        result = contract_manager.restructure_contract(
            contract_id=contract_id,
            year_to_restructure=2,
            amount_to_convert=4_000_000,
            dynasty_id=test_dynasty_id
        )

        assert result['success'] == True
        assert result['current_year_savings'] == 3_000_000  # 4M - 1M (new proration)

    def test_restructure_multiple_years(self, contract_manager, test_team_id,
                                       test_player_id, test_season, test_dynasty_id):
        """Test restructuring creates correct multi-year proration."""
        # Create contract
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

        # Restructure year 2: convert 4M to bonus (3 years remaining)
        result = contract_manager.restructure_contract(
            contract_id=contract_id,
            year_to_restructure=2,
            amount_to_convert=4_000_000,
            dynasty_id=test_dynasty_id
        )

        # New proration: 4M / 3 years = 1.33M per year (rounded down to 1M)
        # Year 2 savings: 4M - 1M = 3M
        assert result['current_year_savings'] == 3_000_000

        # Verify updated contract details
        details = contract_manager.get_contract_details(contract_id)
        year_details = details['year_details']

        # Year 2 should have reduced base salary
        assert year_details[1]['base_salary'] == 2_000_000  # 6M - 4M

    def test_restructure_with_5_year_max(self, contract_manager, test_team_id,
                                        test_player_id, test_season, test_dynasty_id):
        """Test restructuring respects 5-year maximum proration."""
        # Create 7-year contract
        contract_id = contract_manager.create_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=7,
            total_value=140_000_000,
            signing_bonus=35_000_000,  # Will prorate over 5 years (max)
            base_salaries=[5_000_000, 10_000_000, 15_000_000, 15_000_000,
                          15_000_000, 15_000_000, 15_000_000],
            guaranteed_amounts=[5_000_000, 10_000_000, 15_000_000, 0, 0, 0, 0],
            contract_type='VETERAN'
        )

        # Restructure year 1: convert 10M to bonus
        result = contract_manager.restructure_contract(
            contract_id=contract_id,
            year_to_restructure=1,
            amount_to_convert=10_000_000,
            dynasty_id=test_dynasty_id
        )

        # Should apply 5-year max (7 years remaining, but capped at 5)
        # New proration: 10M / 5 = 2M per year
        assert result['current_year_savings'] == 8_000_000  # 10M - 2M


class TestPlayerReleases:
    """Test player release operations."""

    def test_standard_release(self, contract_manager, test_team_id, test_player_id,
                              test_season, test_dynasty_id):
        """Test standard player release (all dead money hits current year)."""
        # Create contract
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

        # Release after year 2
        result = contract_manager.release_player(
            contract_id=contract_id,
            release_date=f"{test_season + 1}-03-15",
            june_1_designation=False,
            dynasty_id=test_dynasty_id
        )

        assert result['success'] == True
        assert result['dead_money_current_year'] > 0
        assert result['dead_money_next_year'] == 0  # Standard release = all current year
        assert result['cap_savings'] > 0

    def test_june_1_release(self, contract_manager, test_team_id, test_player_id,
                           test_season, test_dynasty_id):
        """Test June 1 designation release (split dead money)."""
        # Create contract
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

        # Release with June 1 designation after year 2
        result = contract_manager.release_player(
            contract_id=contract_id,
            release_date=f"{test_season + 1}-03-15",
            june_1_designation=True,
            dynasty_id=test_dynasty_id
        )

        assert result['success'] == True
        assert result['dead_money_current_year'] > 0
        assert result['dead_money_next_year'] > 0  # June 1 = split across years
        assert result['june_1_designation'] == True

    def test_release_with_guaranteed_salary(self, contract_manager, test_team_id,
                                           test_player_id, test_season, test_dynasty_id):
        """Test release includes guaranteed salary in dead money."""
        # Create contract
        contract_id = contract_manager.create_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            base_salaries=[1_000_000, 6_000_000, 8_000_000, 9_000_000],
            guaranteed_amounts=[1_000_000, 6_000_000, 8_000_000, 0],  # Year 3 guaranteed
            contract_type='VETERAN'
        )

        # Release after year 2 (year 3 base is guaranteed)
        result = contract_manager.release_player(
            contract_id=contract_id,
            release_date=f"{test_season + 1}-03-15",
            june_1_designation=False,
            dynasty_id=test_dynasty_id
        )

        # Dead money should include:
        # - Remaining signing bonus proration (2 years @ 4M = 8M)
        # - Guaranteed year 3 salary (8M)
        # Total = 16M
        assert result['dead_money_current_year'] == 16_000_000

    def test_release_updates_contract_status(self, contract_manager, test_team_id,
                                            test_player_id, test_season, test_dynasty_id):
        """Test that releasing a player voids the contract."""
        # Create contract
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

        # Release player
        contract_manager.release_player(
            contract_id=contract_id,
            release_date=f"{test_season + 1}-03-15",
            june_1_designation=False,
            dynasty_id=test_dynasty_id
        )

        # Verify contract is voided
        details = contract_manager.get_contract_details(contract_id)
        assert details['contract']['is_active'] == 0


class TestDeadMoneyProjections:
    """Test dead money projection calculations."""

    def test_get_dead_money_projections(self, contract_manager, test_team_id,
                                       test_player_id, test_season, test_dynasty_id):
        """Test dead money projections for all release scenarios."""
        # Create contract
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

        # Get projections
        projections = contract_manager.get_dead_money_projections(
            contract_id=contract_id,
            dynasty_id=test_dynasty_id
        )

        # Should have projections for all 4 years
        assert len(projections) == 4

        # Verify each year has all three scenarios
        for season, proj in projections.items():
            assert 'standard' in proj
            assert 'june_1_current' in proj
            assert 'june_1_next' in proj

    def test_dead_money_decreases_over_time(self, contract_manager, test_team_id,
                                           test_player_id, test_season, test_dynasty_id):
        """Test that dead money decreases as contract progresses."""
        # Create contract
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

        projections = contract_manager.get_dead_money_projections(
            contract_id=contract_id,
            dynasty_id=test_dynasty_id
        )

        # Year 1 should have highest dead money (all proration remaining)
        year_1_dead = projections[test_season]['standard']
        year_4_dead = projections[test_season + 3]['standard']

        assert year_1_dead > year_4_dead


class TestContractExtensions:
    """Test contract extension operations."""

    def test_extend_contract(self, contract_manager, test_team_id, test_player_id,
                            test_season, test_dynasty_id):
        """Test extending an existing contract."""
        # Create initial 4-year contract
        original_contract_id = contract_manager.create_contract(
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

        # Extend contract with 3 additional years
        result = contract_manager.extend_contract(
            contract_id=original_contract_id,
            additional_years=3,
            additional_value=45_000_000,
            new_signing_bonus=20_000_000,
            new_base_salaries=[10_000_000, 12_000_000, 13_000_000],
            new_guaranteed_amounts=[10_000_000, 0, 0],
            dynasty_id=test_dynasty_id
        )

        assert result['success'] == True
        assert result['new_contract_id'] is not None

        # Verify new contract details
        new_contract_id = result['new_contract_id']
        details = contract_manager.get_contract_details(new_contract_id)

        assert details['contract']['contract_years'] == 7  # 4 + 3
        assert details['contract']['total_value'] == 85_000_000  # 40M + 45M

    def test_extension_voids_original_contract(self, contract_manager, test_team_id,
                                              test_player_id, test_season, test_dynasty_id):
        """Test that extending a contract voids the original."""
        # Create and extend contract
        original_contract_id = contract_manager.create_contract(
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

        contract_manager.extend_contract(
            contract_id=original_contract_id,
            additional_years=3,
            additional_value=45_000_000,
            new_signing_bonus=20_000_000,
            new_base_salaries=[10_000_000, 12_000_000, 13_000_000],
            new_guaranteed_amounts=[10_000_000, 0, 0],
            dynasty_id=test_dynasty_id
        )

        # Verify original contract is voided
        original_details = contract_manager.get_contract_details(original_contract_id)
        assert original_details['contract']['is_active'] == 0


class TestContractRetrieval:
    """Test contract details retrieval operations."""

    def test_get_contract_details(self, contract_manager, test_team_id, test_player_id,
                                  test_season, test_dynasty_id, sample_veteran_contract):
        """Test retrieving complete contract details."""
        contract_id = contract_manager.create_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            **sample_veteran_contract
        )

        details = contract_manager.get_contract_details(contract_id)

        # Verify structure
        assert 'contract' in details
        assert 'year_details' in details

        # Verify contract info
        assert details['contract']['contract_id'] == contract_id
        assert details['contract']['player_id'] == test_player_id
        assert details['contract']['team_id'] == test_team_id

        # Verify year details
        assert len(details['year_details']) == 4

    def test_get_team_contracts(self, contract_manager, test_team_id, test_season,
                               test_dynasty_id):
        """Test retrieving all contracts for a team."""
        # Create multiple contracts
        contract_id_1 = contract_manager.create_contract(
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

        contract_id_2 = contract_manager.create_contract(
            player_id=1002,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            contract_years=4,
            total_value=20_000_000,
            signing_bonus=10_000_000,
            base_salaries=[840_000, 2_500_000, 3_330_000, 3_330_000],
            guaranteed_amounts=[840_000, 2_500_000, 3_330_000, 3_330_000],
            contract_type='ROOKIE'
        )

        # Retrieve all team contracts
        contracts = contract_manager.get_team_contracts(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id
        )

        assert len(contracts) == 2
        contract_ids = [c['contract_id'] for c in contracts]
        assert contract_id_1 in contract_ids
        assert contract_id_2 in contract_ids

    def test_get_player_contract(self, contract_manager, test_team_id, test_player_id,
                                 test_season, test_dynasty_id, sample_veteran_contract):
        """Test retrieving active contract for a specific player."""
        contract_id = contract_manager.create_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            start_year=test_season,
            **sample_veteran_contract
        )

        contract = contract_manager.get_player_contract(
            player_id=test_player_id,
            dynasty_id=test_dynasty_id
        )

        assert contract is not None
        assert contract['contract_id'] == contract_id
        assert contract['player_id'] == test_player_id
        assert contract['is_active'] == 1


class TestIntegrationWithCalculator:
    """Test integration between ContractManager and CapCalculator."""

    def test_contract_uses_calculator_formulas(self, contract_manager, test_team_id,
                                              test_player_id, test_season, test_dynasty_id):
        """Test that ContractManager uses CapCalculator for all calculations."""
        # Create contract with known values
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

        details = contract_manager.get_contract_details(contract_id)

        # Verify proration calculation (should use CapCalculator)
        # 16M signing bonus / 4 years = 4M per year
        for year_detail in details['year_details']:
            assert year_detail['signing_bonus_proration'] == 4_000_000

    def test_restructure_uses_calculator(self, contract_manager, test_team_id,
                                        test_player_id, test_season, test_dynasty_id):
        """Test that restructuring uses CapCalculator formulas."""
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

        # Restructure should use CapCalculator.calculate_restructure_savings
        result = contract_manager.restructure_contract(
            contract_id=contract_id,
            year_to_restructure=2,
            amount_to_convert=4_000_000,
            dynasty_id=test_dynasty_id
        )

        # Verify savings calculation is correct
        # 4M converted, 3 years remaining
        # New proration: 4M / 3 = 1.33M (rounds to 1M)
        # Savings: 4M - 1M = 3M
        assert result['current_year_savings'] == 3_000_000

    def test_release_uses_calculator(self, contract_manager, test_team_id,
                                    test_player_id, test_season, test_dynasty_id):
        """Test that releases use CapCalculator dead money formulas."""
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

        # Release after year 2 should use CapCalculator.calculate_dead_money
        result = contract_manager.release_player(
            contract_id=contract_id,
            release_date=f"{test_season + 1}-03-15",
            june_1_designation=False,
            dynasty_id=test_dynasty_id
        )

        # Verify dead money calculation
        # Remaining proration: 2 years @ 4M = 8M
        # No guaranteed salary in future years
        # Total dead money = 8M
        assert result['dead_money_current_year'] == 8_000_000


class TestErrorHandling:
    """Test error handling and validation."""

    def test_invalid_contract_values(self, contract_manager, test_team_id, test_player_id,
                                    test_season, test_dynasty_id):
        """Test that invalid contract values are rejected."""
        with pytest.raises(ValueError):
            contract_manager.create_contract(
                player_id=test_player_id,
                team_id=test_team_id,
                dynasty_id=test_dynasty_id,
                start_year=test_season,
                contract_years=0,  # Invalid: must be > 0
                total_value=40_000_000,
                signing_bonus=16_000_000,
                base_salaries=[],
                guaranteed_amounts=[],
                contract_type='VETERAN'
            )

    def test_mismatched_base_salaries(self, contract_manager, test_team_id, test_player_id,
                                     test_season, test_dynasty_id):
        """Test that mismatched base salary counts are rejected."""
        with pytest.raises(ValueError):
            contract_manager.create_contract(
                player_id=test_player_id,
                team_id=test_team_id,
                dynasty_id=test_dynasty_id,
                start_year=test_season,
                contract_years=4,
                total_value=40_000_000,
                signing_bonus=16_000_000,
                base_salaries=[1_000_000, 6_000_000],  # Only 2, should be 4
                guaranteed_amounts=[1_000_000, 6_000_000, 0, 0],
                contract_type='VETERAN'
            )

    def test_restructure_nonexistent_contract(self, contract_manager, test_dynasty_id):
        """Test that restructuring nonexistent contract fails gracefully."""
        with pytest.raises(Exception):
            contract_manager.restructure_contract(
                contract_id=99999,  # Doesn't exist
                year_to_restructure=2,
                amount_to_convert=4_000_000,
                dynasty_id=test_dynasty_id
            )

    def test_release_nonexistent_contract(self, contract_manager, test_season, test_dynasty_id):
        """Test that releasing nonexistent contract fails gracefully."""
        with pytest.raises(Exception):
            contract_manager.release_player(
                contract_id=99999,  # Doesn't exist
                release_date=f"{test_season}-03-15",
                june_1_designation=False,
                dynasty_id=test_dynasty_id
            )
