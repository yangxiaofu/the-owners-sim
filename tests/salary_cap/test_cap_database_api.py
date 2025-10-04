"""
Unit Tests for CapDatabaseAPI

Tests all database operations for the salary cap system including:
- Contract CRUD operations
- Team cap operations
- Franchise tag and RFA tender operations
- Dead money operations
- Transaction logging
- Dynasty isolation verification
- Database constraint validation
"""

import pytest
import sqlite3
from datetime import date


class TestContractOperations:
    """Test contract CRUD operations."""

    def test_insert_contract(self, cap_database_api, test_team_id, test_player_id,
                             test_season, test_dynasty_id):
        """Test inserting a new contract."""
        contract_id = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            contract_type='VETERAN',
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            total_guaranteed=23_000_000,
            start_year=test_season,
            end_year=test_season + 3
        )

        assert contract_id is not None
        assert contract_id > 0

    def test_get_contract(self, cap_database_api, test_team_id, test_player_id,
                         test_season, test_dynasty_id):
        """Test retrieving a contract by ID."""
        # Insert contract
        contract_id = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            contract_type='VETERAN',
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            total_guaranteed=23_000_000,
            start_year=test_season,
            end_year=test_season + 3
        )

        # Retrieve contract
        contract = cap_database_api.get_contract(contract_id)

        assert contract is not None
        assert contract['contract_id'] == contract_id
        assert contract['player_id'] == test_player_id
        assert contract['team_id'] == test_team_id
        assert contract['dynasty_id'] == test_dynasty_id
        assert contract['contract_type'] == 'VETERAN'
        assert contract['contract_years'] == 4
        assert contract['total_value'] == 40_000_000
        assert contract['signing_bonus'] == 16_000_000
        assert contract['total_guaranteed'] == 23_000_000
        assert contract['is_active'] == 1

    def test_get_team_contracts(self, cap_database_api, test_team_id, test_player_id,
                                test_season, test_dynasty_id):
        """Test retrieving all contracts for a team."""
        # Insert multiple contracts
        contract_id_1 = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            contract_type='VETERAN',
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            total_guaranteed=23_000_000,
            start_year=test_season,
            end_year=test_season + 3
        )

        contract_id_2 = cap_database_api.insert_contract(
            player_id=test_player_id + 1,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            contract_type='ROOKIE',
            contract_years=4,
            total_value=20_000_000,
            signing_bonus=10_000_000,
            total_guaranteed=20_000_000,
            start_year=test_season,
            end_year=test_season + 3
        )

        # Retrieve all contracts
        contracts = cap_database_api.get_team_contracts(test_team_id, test_season, test_dynasty_id)

        assert len(contracts) == 2
        contract_ids = [c['contract_id'] for c in contracts]
        assert contract_id_1 in contract_ids
        assert contract_id_2 in contract_ids

    def test_get_player_contract(self, cap_database_api, test_team_id, test_player_id,
                                 test_season, test_dynasty_id):
        """Test retrieving active contract for a player."""
        # Insert contract
        contract_id = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            contract_type='VETERAN',
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            total_guaranteed=23_000_000,
            start_year=test_season,
            end_year=test_season + 3
        )

        # Retrieve player's active contract
        contract = cap_database_api.get_player_contract(test_player_id, test_dynasty_id)

        assert contract is not None
        assert contract['contract_id'] == contract_id
        assert contract['player_id'] == test_player_id
        assert contract['is_active'] == 1

    def test_void_contract(self, cap_database_api, test_team_id, test_player_id,
                          test_season, test_dynasty_id):
        """Test voiding a contract."""
        # Insert contract
        contract_id = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            contract_type='VETERAN',
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            total_guaranteed=23_000_000,
            start_year=test_season,
            end_year=test_season + 3
        )

        # Void contract
        result = cap_database_api.void_contract(contract_id)

        assert result == True

        # Verify contract is no longer active
        contract = cap_database_api.get_contract(contract_id)
        assert contract['is_active'] == 0


class TestContractYearDetails:
    """Test contract year detail operations."""

    def test_insert_contract_year_details(self, cap_database_api, test_team_id,
                                          test_player_id, test_season, test_dynasty_id):
        """Test inserting contract year details."""
        # Insert contract
        contract_id = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            contract_type='VETERAN',
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            total_guaranteed=23_000_000,
            start_year=test_season,
            end_year=test_season + 3
        )

        # Insert year details
        detail_id = cap_database_api.insert_contract_year_details(
            contract_id=contract_id,
            contract_year=1,
            season_year=test_season,
            base_salary=1_000_000,
            signing_bonus_proration=4_000_000,
            roster_bonus=0,
            workout_bonus=0,
            guaranteed_amount=1_000_000,
            total_cap_hit=5_000_000,
            cash_paid=17_000_000
        )

        assert detail_id is not None
        assert detail_id > 0

    def test_get_contract_year_details(self, cap_database_api, test_team_id,
                                       test_player_id, test_season, test_dynasty_id):
        """Test retrieving contract year details."""
        # Insert contract
        contract_id = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            contract_type='VETERAN',
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            total_guaranteed=23_000_000,
            start_year=test_season,
            end_year=test_season + 3
        )

        # Insert year details for all 4 years
        for year in range(1, 5):
            cap_database_api.insert_contract_year_details(
                contract_id=contract_id,
                contract_year=year,
                season_year=test_season + year - 1,
                base_salary=6_000_000 + year * 1_000_000,
                signing_bonus_proration=4_000_000,
                roster_bonus=0,
                workout_bonus=0,
                guaranteed_amount=6_000_000 if year <= 2 else 0,
                total_cap_hit=10_000_000 + year * 1_000_000,
                cash_paid=6_000_000 + year * 1_000_000
            )

        # Retrieve all year details
        details = cap_database_api.get_contract_year_details(contract_id)

        assert len(details) == 4
        assert details[0]['contract_year'] == 1
        assert details[3]['contract_year'] == 4

    def test_get_year_details_for_season(self, cap_database_api, test_team_id,
                                         test_player_id, test_season, test_dynasty_id):
        """Test retrieving year details for specific season."""
        # Insert contract
        contract_id = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            contract_type='VETERAN',
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            total_guaranteed=23_000_000,
            start_year=test_season,
            end_year=test_season + 3
        )

        # Insert year details
        cap_database_api.insert_contract_year_details(
            contract_id=contract_id,
            contract_year=2,
            season_year=test_season + 1,
            base_salary=6_000_000,
            signing_bonus_proration=4_000_000,
            roster_bonus=0,
            workout_bonus=0,
            guaranteed_amount=6_000_000,
            total_cap_hit=10_000_000,
            cash_paid=6_000_000
        )

        # Retrieve specific year
        detail = cap_database_api.get_year_details_for_season(contract_id, test_season + 1)

        assert detail is not None
        assert detail['season_year'] == test_season + 1
        assert detail['contract_year'] == 2
        assert detail['base_salary'] == 6_000_000


class TestTeamCapOperations:
    """Test team salary cap operations."""

    def test_initialize_team_cap(self, cap_database_api, test_team_id, test_season,
                                 test_dynasty_id):
        """Test initializing team salary cap."""
        cap_id = cap_database_api.initialize_team_cap(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            salary_cap_limit=279_200_000,
            carryover_from_previous=0
        )

        assert cap_id is not None
        assert cap_id > 0

    def test_get_team_cap(self, cap_database_api, test_team_id, test_season,
                         test_dynasty_id):
        """Test retrieving team salary cap."""
        # Initialize cap
        cap_id = cap_database_api.initialize_team_cap(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            salary_cap_limit=279_200_000,
            carryover_from_previous=2_000_000
        )

        # Retrieve cap
        cap = cap_database_api.get_team_cap(test_team_id, test_season, test_dynasty_id)

        assert cap is not None
        assert cap['cap_id'] == cap_id
        assert cap['team_id'] == test_team_id
        assert cap['season'] == test_season
        assert cap['salary_cap_limit'] == 279_200_000
        assert cap['carryover_from_previous'] == 2_000_000
        assert cap['total_cap_available'] == 281_200_000

    def test_update_team_cap_usage(self, cap_database_api, initialized_team_cap,
                                   test_team_id, test_season, test_dynasty_id):
        """Test updating team cap usage."""
        # Update cap usage
        result = cap_database_api.update_team_cap_usage(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            active_contracts_total=200_000_000,
            dead_money_total=5_000_000,
            ltbe_incentives_total=2_000_000,
            practice_squad_total=3_000_000
        )

        assert result == True

        # Verify updates
        cap = cap_database_api.get_team_cap(test_team_id, test_season, test_dynasty_id)
        assert cap['active_contracts_total'] == 200_000_000
        assert cap['dead_money_total'] == 5_000_000
        assert cap['ltbe_incentives_total'] == 2_000_000
        assert cap['practice_squad_total'] == 3_000_000
        assert cap['total_cap_used'] == 210_000_000
        assert cap['cap_space_available'] == 69_200_000

    def test_get_team_cap_summary(self, cap_database_api, initialized_team_cap,
                                  test_team_id, test_season, test_dynasty_id):
        """Test retrieving team cap summary."""
        # Update cap usage
        cap_database_api.update_team_cap_usage(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            active_contracts_total=200_000_000,
            dead_money_total=5_000_000,
            ltbe_incentives_total=2_000_000,
            practice_squad_total=3_000_000
        )

        # Get summary
        summary = cap_database_api.get_team_cap_summary(test_team_id, test_season, test_dynasty_id)

        assert summary is not None
        assert summary['team_id'] == test_team_id
        assert summary['season'] == test_season
        assert summary['salary_cap_limit'] == 279_200_000
        assert summary['total_cap_available'] == 279_200_000
        assert summary['total_cap_used'] == 210_000_000
        assert summary['cap_space_available'] == 69_200_000


class TestFranchiseTagOperations:
    """Test franchise tag operations."""

    def test_insert_franchise_tag(self, cap_database_api, test_team_id, test_player_id,
                                  test_season, test_dynasty_id):
        """Test inserting a franchise tag."""
        tag_id = cap_database_api.insert_franchise_tag(
            team_id=test_team_id,
            player_id=test_player_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            tag_type='EXCLUSIVE',
            tag_amount=32_000_000,
            times_tagged=1
        )

        assert tag_id is not None
        assert tag_id > 0

    def test_get_team_franchise_tags(self, cap_database_api, test_team_id, test_player_id,
                                     test_season, test_dynasty_id):
        """Test retrieving franchise tags for a team."""
        # Insert tag
        tag_id = cap_database_api.insert_franchise_tag(
            team_id=test_team_id,
            player_id=test_player_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            tag_type='EXCLUSIVE',
            tag_amount=32_000_000,
            times_tagged=1
        )

        # Retrieve tags
        tags = cap_database_api.get_team_franchise_tags(test_team_id, test_season, test_dynasty_id)

        assert len(tags) == 1
        assert tags[0]['tag_id'] == tag_id
        assert tags[0]['tag_type'] == 'EXCLUSIVE'
        assert tags[0]['tag_amount'] == 32_000_000


class TestRFATenderOperations:
    """Test RFA tender operations."""

    def test_insert_rfa_tender(self, cap_database_api, test_team_id, test_player_id,
                              test_season, test_dynasty_id):
        """Test inserting an RFA tender."""
        tender_id = cap_database_api.insert_rfa_tender(
            team_id=test_team_id,
            player_id=test_player_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            tender_level='FIRST_ROUND',
            tender_amount=5_000_000
        )

        assert tender_id is not None
        assert tender_id > 0

    def test_get_team_rfa_tenders(self, cap_database_api, test_team_id, test_player_id,
                                 test_season, test_dynasty_id):
        """Test retrieving RFA tenders for a team."""
        # Insert tender
        tender_id = cap_database_api.insert_rfa_tender(
            team_id=test_team_id,
            player_id=test_player_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            tender_level='FIRST_ROUND',
            tender_amount=5_000_000
        )

        # Retrieve tenders
        tenders = cap_database_api.get_team_rfa_tenders(test_team_id, test_season, test_dynasty_id)

        assert len(tenders) == 1
        assert tenders[0]['tender_id'] == tender_id
        assert tenders[0]['tender_level'] == 'FIRST_ROUND'
        assert tenders[0]['tender_amount'] == 5_000_000


class TestDeadMoneyOperations:
    """Test dead money operations."""

    def test_insert_dead_money(self, cap_database_api, test_team_id, test_player_id,
                              test_season, test_dynasty_id):
        """Test inserting dead money."""
        dead_money_id = cap_database_api.insert_dead_money(
            team_id=test_team_id,
            player_id=test_player_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            dead_cap_amount=10_000_000,
            source='RELEASE',
            is_june_1_designation=False
        )

        assert dead_money_id is not None
        assert dead_money_id > 0

    def test_get_team_dead_money(self, cap_database_api, test_team_id, test_player_id,
                                 test_season, test_dynasty_id):
        """Test retrieving dead money for a team."""
        # Insert dead money
        dead_money_id = cap_database_api.insert_dead_money(
            team_id=test_team_id,
            player_id=test_player_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            dead_cap_amount=10_000_000,
            source='RELEASE',
            is_june_1_designation=False
        )

        # Retrieve dead money
        dead_money_records = cap_database_api.get_team_dead_money(
            test_team_id, test_season, test_dynasty_id
        )

        assert len(dead_money_records) == 1
        assert dead_money_records[0]['dead_money_id'] == dead_money_id
        assert dead_money_records[0]['dead_cap_amount'] == 10_000_000
        assert dead_money_records[0]['source'] == 'RELEASE'

    def test_june_1_designation_dead_money(self, cap_database_api, test_team_id,
                                          test_player_id, test_season, test_dynasty_id):
        """Test June 1 designation dead money."""
        # Insert current year dead money
        dead_money_id_1 = cap_database_api.insert_dead_money(
            team_id=test_team_id,
            player_id=test_player_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            dead_cap_amount=5_000_000,
            source='RELEASE',
            is_june_1_designation=True
        )

        # Insert next year dead money
        dead_money_id_2 = cap_database_api.insert_dead_money(
            team_id=test_team_id,
            player_id=test_player_id,
            season=test_season + 1,
            dynasty_id=test_dynasty_id,
            dead_cap_amount=15_000_000,
            source='RELEASE',
            is_june_1_designation=True
        )

        # Verify current year
        current_year_dead_money = cap_database_api.get_team_dead_money(
            test_team_id, test_season, test_dynasty_id
        )
        assert len(current_year_dead_money) == 1
        assert current_year_dead_money[0]['dead_cap_amount'] == 5_000_000
        assert current_year_dead_money[0]['is_june_1_designation'] == 1

        # Verify next year
        next_year_dead_money = cap_database_api.get_team_dead_money(
            test_team_id, test_season + 1, test_dynasty_id
        )
        assert len(next_year_dead_money) == 1
        assert next_year_dead_money[0]['dead_cap_amount'] == 15_000_000


class TestTransactionLogging:
    """Test cap transaction logging."""

    def test_log_transaction(self, cap_database_api, test_team_id, test_season,
                            test_dynasty_id):
        """Test logging a cap transaction."""
        transaction_id = cap_database_api.log_transaction(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            transaction_type='SIGNING',
            transaction_date=date.today().isoformat(),
            description='Signed QB to 4-year deal',
            cap_impact=10_000_000
        )

        assert transaction_id is not None
        assert transaction_id > 0

    def test_get_team_transactions(self, cap_database_api, test_team_id, test_season,
                                   test_dynasty_id):
        """Test retrieving team transactions."""
        # Log multiple transactions
        cap_database_api.log_transaction(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            transaction_type='SIGNING',
            transaction_date=date.today().isoformat(),
            description='Signed QB',
            cap_impact=10_000_000
        )

        cap_database_api.log_transaction(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=test_dynasty_id,
            transaction_type='RELEASE',
            transaction_date=date.today().isoformat(),
            description='Released WR',
            cap_impact=-5_000_000
        )

        # Retrieve transactions
        transactions = cap_database_api.get_team_transactions(
            test_team_id, test_season, test_dynasty_id
        )

        assert len(transactions) == 2
        assert transactions[0]['transaction_type'] == 'SIGNING'
        assert transactions[1]['transaction_type'] == 'RELEASE'


class TestDynastyIsolation:
    """Test dynasty isolation across all operations."""

    def test_contract_dynasty_isolation(self, cap_database_api, test_team_id,
                                       test_player_id, test_season):
        """Test that contracts are isolated by dynasty."""
        dynasty_1 = "dynasty_1"
        dynasty_2 = "dynasty_2"

        # Insert contract in dynasty 1
        contract_id_1 = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=dynasty_1,
            contract_type='VETERAN',
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            total_guaranteed=23_000_000,
            start_year=test_season,
            end_year=test_season + 3
        )

        # Insert contract in dynasty 2
        contract_id_2 = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=dynasty_2,
            contract_type='VETERAN',
            contract_years=3,
            total_value=30_000_000,
            signing_bonus=12_000_000,
            total_guaranteed=18_000_000,
            start_year=test_season,
            end_year=test_season + 2
        )

        # Verify isolation
        contracts_1 = cap_database_api.get_team_contracts(test_team_id, test_season, dynasty_1)
        contracts_2 = cap_database_api.get_team_contracts(test_team_id, test_season, dynasty_2)

        assert len(contracts_1) == 1
        assert len(contracts_2) == 1
        assert contracts_1[0]['contract_id'] == contract_id_1
        assert contracts_1[0]['contract_years'] == 4
        assert contracts_2[0]['contract_id'] == contract_id_2
        assert contracts_2[0]['contract_years'] == 3

    def test_team_cap_dynasty_isolation(self, cap_database_api, test_team_id, test_season):
        """Test that team caps are isolated by dynasty."""
        dynasty_1 = "dynasty_1"
        dynasty_2 = "dynasty_2"

        # Initialize cap in dynasty 1
        cap_database_api.initialize_team_cap(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=dynasty_1,
            salary_cap_limit=279_200_000,
            carryover_from_previous=2_000_000
        )

        # Initialize cap in dynasty 2
        cap_database_api.initialize_team_cap(
            team_id=test_team_id,
            season=test_season,
            dynasty_id=dynasty_2,
            salary_cap_limit=279_200_000,
            carryover_from_previous=5_000_000
        )

        # Verify isolation
        cap_1 = cap_database_api.get_team_cap(test_team_id, test_season, dynasty_1)
        cap_2 = cap_database_api.get_team_cap(test_team_id, test_season, dynasty_2)

        assert cap_1['carryover_from_previous'] == 2_000_000
        assert cap_1['total_cap_available'] == 281_200_000
        assert cap_2['carryover_from_previous'] == 5_000_000
        assert cap_2['total_cap_available'] == 284_200_000

    def test_dead_money_dynasty_isolation(self, cap_database_api, test_team_id,
                                         test_player_id, test_season):
        """Test that dead money is isolated by dynasty."""
        dynasty_1 = "dynasty_1"
        dynasty_2 = "dynasty_2"

        # Insert dead money in dynasty 1
        cap_database_api.insert_dead_money(
            team_id=test_team_id,
            player_id=test_player_id,
            season=test_season,
            dynasty_id=dynasty_1,
            dead_cap_amount=10_000_000,
            source='RELEASE',
            is_june_1_designation=False
        )

        # Insert dead money in dynasty 2
        cap_database_api.insert_dead_money(
            team_id=test_team_id,
            player_id=test_player_id,
            season=test_season,
            dynasty_id=dynasty_2,
            dead_cap_amount=15_000_000,
            source='RELEASE',
            is_june_1_designation=False
        )

        # Verify isolation
        dead_money_1 = cap_database_api.get_team_dead_money(test_team_id, test_season, dynasty_1)
        dead_money_2 = cap_database_api.get_team_dead_money(test_team_id, test_season, dynasty_2)

        assert len(dead_money_1) == 1
        assert len(dead_money_2) == 1
        assert dead_money_1[0]['dead_cap_amount'] == 10_000_000
        assert dead_money_2[0]['dead_cap_amount'] == 15_000_000


class TestDatabaseConstraints:
    """Test database constraint validation."""

    def test_unique_active_contract_constraint(self, cap_database_api, test_team_id,
                                              test_player_id, test_season, test_dynasty_id):
        """Test that only one active contract per player per dynasty is enforced."""
        # Insert first contract
        contract_id_1 = cap_database_api.insert_contract(
            player_id=test_player_id,
            team_id=test_team_id,
            dynasty_id=test_dynasty_id,
            contract_type='VETERAN',
            contract_years=4,
            total_value=40_000_000,
            signing_bonus=16_000_000,
            total_guaranteed=23_000_000,
            start_year=test_season,
            end_year=test_season + 3
        )

        # Try to insert second active contract for same player
        with pytest.raises(sqlite3.IntegrityError):
            cap_database_api.insert_contract(
                player_id=test_player_id,
                team_id=test_team_id,
                dynasty_id=test_dynasty_id,
                contract_type='VETERAN',
                contract_years=3,
                total_value=30_000_000,
                signing_bonus=12_000_000,
                total_guaranteed=18_000_000,
                start_year=test_season,
                end_year=test_season + 2
            )

    def test_foreign_key_constraints(self, cap_database_api, test_team_id, test_season,
                                    test_dynasty_id):
        """Test foreign key constraints are enforced."""
        # Try to insert contract year details for non-existent contract
        with pytest.raises(sqlite3.IntegrityError):
            cap_database_api.insert_contract_year_details(
                contract_id=99999,  # Non-existent contract
                contract_year=1,
                season_year=test_season,
                base_salary=1_000_000,
                signing_bonus_proration=4_000_000,
                roster_bonus=0,
                workout_bonus=0,
                guaranteed_amount=1_000_000,
                total_cap_hit=5_000_000,
                cash_paid=17_000_000
            )
