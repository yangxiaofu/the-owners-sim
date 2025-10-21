"""
Unit Tests for Contract Expiration Queries (Gap 1)

Tests the following CapDatabaseAPI methods:
- get_expiring_contracts()
- get_pending_free_agents()

Verifies:
- Contract expiration detection
- Player overall filtering
- Dynasty isolation
- Sorting behavior
"""

import pytest
from datetime import date
import json
import sqlite3
from salary_cap.cap_database_api import CapDatabaseAPI


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def insert_test_player(db_path, dynasty_id, team_id, overall, position='quarterback',
                      first_name='Test', last_name='Player', years_pro=5):
    """
    Helper to insert test player with attributes.

    Args:
        db_path: Path to test database
        dynasty_id: Dynasty context
        team_id: Team ID (1-32)
        overall: Player overall rating (0-100)
        position: Player position
        first_name: Player first name
        last_name: Player last name
        years_pro: Years of experience

    Returns:
        player_id of inserted player
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Build player data
    player_data = {
        'first_name': first_name,
        'last_name': last_name,
        'number': 99,
        'positions': json.dumps([position]),
        'attributes': json.dumps({'overall': overall}),
        'team_id': team_id,
        'years_pro': years_pro,
        'birthdate': '1995-01-01',
        'status': 'active'
    }

    # Insert player
    cursor = conn.execute("""
        INSERT INTO players (dynasty_id, first_name, last_name, number,
                           positions, attributes, team_id, years_pro, birthdate, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dynasty_id,
        player_data['first_name'],
        player_data['last_name'],
        player_data['number'],
        player_data['positions'],
        player_data['attributes'],
        player_data['team_id'],
        player_data['years_pro'],
        player_data['birthdate'],
        player_data['status']
    ))

    conn.commit()
    player_id = cursor.lastrowid
    conn.close()

    return player_id


def ensure_player_table_exists(db_path):
    """Ensure players table exists in test database."""
    conn = sqlite3.connect(db_path)

    # Check if players table exists
    cursor = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='players'
    """)

    if cursor.fetchone() is None:
        # Create minimal players table for testing
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                number INTEGER,
                positions TEXT,
                attributes TEXT,
                team_id INTEGER NOT NULL,
                years_pro INTEGER DEFAULT 0,
                birthdate TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    conn.close()


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def cap_api_with_players(test_db_with_schema):
    """Fixture providing CapDatabaseAPI with players table."""
    # Ensure players table exists
    ensure_player_table_exists(test_db_with_schema)

    # Return API instance
    return CapDatabaseAPI(test_db_with_schema)


# ============================================================================
# TEST: get_expiring_contracts()
# ============================================================================

class TestGetExpiringContracts:
    """Test get_expiring_contracts() method."""

    def test_empty_result_when_no_contracts(self, cap_api_with_players, test_dynasty_id):
        """Test returns empty list when no contracts exist."""
        result = cap_api_with_players.get_expiring_contracts(
            team_id=7,
            season=2024,
            dynasty_id=test_dynasty_id
        )

        assert result == []

    def test_single_expiring_contract(self, cap_api_with_players, test_dynasty_id, test_db_with_schema):
        """Test with single expiring contract."""
        # Insert test player
        player_id = insert_test_player(
            test_db_with_schema,
            test_dynasty_id,
            team_id=7,
            overall=85
        )

        # Insert expiring contract (ends in 2024)
        contract_id = cap_api_with_players.insert_contract(
            player_id=player_id,
            team_id=7,
            dynasty_id=test_dynasty_id,
            start_year=2020,
            end_year=2024,  # Expiring
            contract_years=5,
            contract_type='VETERAN',
            total_value=50_000_000
        )

        # Query expiring contracts
        result = cap_api_with_players.get_expiring_contracts(
            team_id=7,
            season=2024,
            dynasty_id=test_dynasty_id
        )

        # Verify
        assert len(result) == 1
        assert result[0]['contract_id'] == contract_id
        assert result[0]['end_year'] == 2024
        assert result[0]['player_name'] == 'Test Player'
        assert result[0]['positions'] is not None
        assert result[0]['attributes'] is not None

    def test_filters_by_team_id(self, cap_api_with_players, test_dynasty_id, test_db_with_schema):
        """Test that results are filtered by team_id."""
        # Insert players for two teams
        player1 = insert_test_player(test_db_with_schema, test_dynasty_id, team_id=7, overall=85)
        player2 = insert_test_player(test_db_with_schema, test_dynasty_id, team_id=9, overall=82)

        # Insert expiring contracts for both teams
        cap_api_with_players.insert_contract(
            player_id=player1, team_id=7, dynasty_id=test_dynasty_id,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=50_000_000
        )
        cap_api_with_players.insert_contract(
            player_id=player2, team_id=9, dynasty_id=test_dynasty_id,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=40_000_000
        )

        # Query for team 7 only
        result = cap_api_with_players.get_expiring_contracts(
            team_id=7,
            season=2024,
            dynasty_id=test_dynasty_id
        )

        # Should only return team 7's contract
        assert len(result) == 1
        assert result[0]['player_id'] == player1

    def test_filters_by_end_year(self, cap_api_with_players, test_dynasty_id, test_db_with_schema):
        """Test that only contracts ending in specified season are returned."""
        # Insert player
        player_id = insert_test_player(test_db_with_schema, test_dynasty_id, team_id=7, overall=85)

        # Insert contracts ending in different years
        cap_api_with_players.insert_contract(
            player_id=player_id, team_id=7, dynasty_id=test_dynasty_id,
            start_year=2020, end_year=2023, contract_years=4,
            contract_type='VETERAN', total_value=40_000_000
        )

        # Create another player for 2024 expiring contract
        player_id_2 = insert_test_player(
            test_db_with_schema, test_dynasty_id, team_id=7, overall=80,
            first_name='John', last_name='Doe'
        )
        cap_api_with_players.insert_contract(
            player_id=player_id_2, team_id=7, dynasty_id=test_dynasty_id,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=50_000_000
        )

        # Query for 2024 expiring contracts
        result = cap_api_with_players.get_expiring_contracts(
            team_id=7,
            season=2024,
            dynasty_id=test_dynasty_id
        )

        # Should only return 2024 contract
        assert len(result) == 1
        assert result[0]['end_year'] == 2024
        assert result[0]['player_id'] == player_id_2

    def test_sorts_by_total_value_desc(self, cap_api_with_players, test_dynasty_id, test_db_with_schema):
        """Test that results are sorted by total_value descending."""
        # Insert 3 players with different contract values
        player1 = insert_test_player(
            test_db_with_schema, test_dynasty_id, team_id=7, overall=70,
            first_name='Low', last_name='Value'
        )
        player2 = insert_test_player(
            test_db_with_schema, test_dynasty_id, team_id=7, overall=95,
            first_name='High', last_name='Value'
        )
        player3 = insert_test_player(
            test_db_with_schema, test_dynasty_id, team_id=7, overall=82,
            first_name='Mid', last_name='Value'
        )

        # Insert contracts with different values
        cap_api_with_players.insert_contract(
            player_id=player1, team_id=7, dynasty_id=test_dynasty_id,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=20_000_000  # Lowest
        )
        cap_api_with_players.insert_contract(
            player_id=player2, team_id=7, dynasty_id=test_dynasty_id,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=60_000_000  # Highest
        )
        cap_api_with_players.insert_contract(
            player_id=player3, team_id=7, dynasty_id=test_dynasty_id,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=35_000_000  # Middle
        )

        # Query
        result = cap_api_with_players.get_expiring_contracts(
            team_id=7,
            season=2024,
            dynasty_id=test_dynasty_id
        )

        # Verify sorted by total_value DESC
        assert len(result) == 3
        assert result[0]['total_value'] == 60_000_000
        assert result[0]['player_id'] == player2
        assert result[1]['total_value'] == 35_000_000
        assert result[1]['player_id'] == player3
        assert result[2]['total_value'] == 20_000_000
        assert result[2]['player_id'] == player1

    def test_active_only_filter(self, cap_api_with_players, test_dynasty_id, test_db_with_schema):
        """Test that active_only parameter filters voided contracts."""
        # Insert player
        player_id = insert_test_player(test_db_with_schema, test_dynasty_id, team_id=7, overall=85)

        # Insert contract and void it
        contract_id = cap_api_with_players.insert_contract(
            player_id=player_id, team_id=7, dynasty_id=test_dynasty_id,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=50_000_000
        )
        cap_api_with_players.void_contract(contract_id)

        # Query with active_only=True (default)
        result_active = cap_api_with_players.get_expiring_contracts(
            team_id=7,
            season=2024,
            dynasty_id=test_dynasty_id,
            active_only=True
        )

        # Should be empty (voided contract excluded)
        assert len(result_active) == 0

        # Query with active_only=False
        result_all = cap_api_with_players.get_expiring_contracts(
            team_id=7,
            season=2024,
            dynasty_id=test_dynasty_id,
            active_only=False
        )

        # Should include voided contract
        assert len(result_all) == 1
        assert result_all[0]['contract_id'] == contract_id


# ============================================================================
# TEST: get_pending_free_agents()
# ============================================================================

class TestGetPendingFreeAgents:
    """Test get_pending_free_agents() method."""

    def test_filters_by_min_overall(self, cap_api_with_players, test_dynasty_id, test_db_with_schema):
        """Test that results are filtered by min_overall."""
        # Insert 3 players with different overalls
        player_elite = insert_test_player(
            test_db_with_schema, test_dynasty_id, team_id=7, overall=90,
            first_name='Elite', last_name='QB'
        )
        player_good = insert_test_player(
            test_db_with_schema, test_dynasty_id, team_id=7, overall=75,
            first_name='Good', last_name='QB'
        )
        player_backup = insert_test_player(
            test_db_with_schema, test_dynasty_id, team_id=7, overall=65,
            first_name='Backup', last_name='QB'
        )

        # Insert expiring contracts
        cap_api_with_players.insert_contract(
            player_id=player_elite, team_id=7, dynasty_id=test_dynasty_id,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=50_000_000
        )
        cap_api_with_players.insert_contract(
            player_id=player_good, team_id=7, dynasty_id=test_dynasty_id,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=30_000_000
        )
        cap_api_with_players.insert_contract(
            player_id=player_backup, team_id=7, dynasty_id=test_dynasty_id,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=10_000_000
        )

        # Query with min_overall = 75
        result = cap_api_with_players.get_pending_free_agents(
            team_id=7,
            season=2024,
            dynasty_id=test_dynasty_id,
            min_overall=75
        )

        # Should only return 90 and 75 overall players
        assert len(result) == 2
        assert result[0]['overall'] == 90
        assert result[1]['overall'] == 75

    def test_sorted_by_overall_desc(self, cap_api_with_players, test_dynasty_id, test_db_with_schema):
        """Test that results are sorted by overall rating descending."""
        # Insert players in random overall order
        player1 = insert_test_player(
            test_db_with_schema, test_dynasty_id, team_id=7, overall=70,
            first_name='Player', last_name='70'
        )
        player2 = insert_test_player(
            test_db_with_schema, test_dynasty_id, team_id=7, overall=95,
            first_name='Player', last_name='95'
        )
        player3 = insert_test_player(
            test_db_with_schema, test_dynasty_id, team_id=7, overall=82,
            first_name='Player', last_name='82'
        )

        # Insert contracts
        for player_id in [player1, player2, player3]:
            cap_api_with_players.insert_contract(
                player_id=player_id, team_id=7, dynasty_id=test_dynasty_id,
                start_year=2020, end_year=2024, contract_years=5,
                contract_type='VETERAN', total_value=40_000_000
            )

        # Query
        result = cap_api_with_players.get_pending_free_agents(
            team_id=7,
            season=2024,
            dynasty_id=test_dynasty_id
        )

        # Verify sorted: 95, 82, 70
        assert len(result) == 3
        assert result[0]['overall'] == 95
        assert result[1]['overall'] == 82
        assert result[2]['overall'] == 70

    def test_includes_player_metadata(self, cap_api_with_players, test_dynasty_id, test_db_with_schema):
        """Test that result includes all expected player metadata."""
        # Insert player
        player_id = insert_test_player(
            test_db_with_schema, test_dynasty_id, team_id=7, overall=85,
            position='wide_receiver', years_pro=6
        )

        # Insert contract
        contract_id = cap_api_with_players.insert_contract(
            player_id=player_id, team_id=7, dynasty_id=test_dynasty_id,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=40_000_000
        )

        # Query
        result = cap_api_with_players.get_pending_free_agents(
            team_id=7,
            season=2024,
            dynasty_id=test_dynasty_id
        )

        # Verify all fields present
        assert len(result) == 1
        fa = result[0]

        assert fa['player_id'] == player_id
        assert fa['player_name'] == 'Test Player'
        assert fa['position'] == 'wide_receiver'
        assert fa['overall'] == 85
        assert fa['years_pro'] == 6
        assert fa['contract_id'] == contract_id
        assert fa['contract_value'] == 40_000_000
        assert fa['contract_years'] == 5
        assert fa['aav'] == 8_000_000  # 40M / 5 years

    def test_aav_calculation(self, cap_api_with_players, test_dynasty_id, test_db_with_schema):
        """Test that AAV (average annual value) is calculated correctly."""
        # Insert player
        player_id = insert_test_player(test_db_with_schema, test_dynasty_id, team_id=7, overall=85)

        # Insert contract: $60M over 4 years
        cap_api_with_players.insert_contract(
            player_id=player_id, team_id=7, dynasty_id=test_dynasty_id,
            start_year=2021, end_year=2024, contract_years=4,
            contract_type='VETERAN', total_value=60_000_000
        )

        # Query
        result = cap_api_with_players.get_pending_free_agents(
            team_id=7,
            season=2024,
            dynasty_id=test_dynasty_id
        )

        # AAV should be $15M per year
        assert len(result) == 1
        assert result[0]['aav'] == 15_000_000


# ============================================================================
# TEST: Dynasty Isolation
# ============================================================================

class TestDynastyIsolation:
    """Test dynasty isolation for contract queries."""

    def test_different_dynasties_isolated(self, cap_api_with_players, test_db_with_schema):
        """Test that contracts from different dynasties don't mix."""
        dynasty_1 = "dynasty_1"
        dynasty_2 = "dynasty_2"

        # Ensure both dynasties exist (using DatabaseConnection)
        from database.connection import DatabaseConnection
        db_conn = DatabaseConnection(test_db_with_schema)
        db_conn.ensure_dynasty_exists(dynasty_1)
        db_conn.ensure_dynasty_exists(dynasty_2)

        # Insert player and contract in dynasty 1
        player1 = insert_test_player(
            test_db_with_schema, dynasty_1, team_id=7, overall=85,
            first_name='Dynasty1', last_name='Player'
        )
        cap_api_with_players.insert_contract(
            player_id=player1, team_id=7, dynasty_id=dynasty_1,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=50_000_000
        )

        # Insert player and contract in dynasty 2
        player2 = insert_test_player(
            test_db_with_schema, dynasty_2, team_id=7, overall=82,
            first_name='Dynasty2', last_name='Player'
        )
        cap_api_with_players.insert_contract(
            player_id=player2, team_id=7, dynasty_id=dynasty_2,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=45_000_000
        )

        # Query dynasty 1 - should only see player1
        result1 = cap_api_with_players.get_pending_free_agents(
            team_id=7,
            season=2024,
            dynasty_id=dynasty_1
        )

        assert len(result1) == 1
        assert result1[0]['player_id'] == player1
        assert result1[0]['overall'] == 85

        # Query dynasty 2 - should only see player2
        result2 = cap_api_with_players.get_pending_free_agents(
            team_id=7,
            season=2024,
            dynasty_id=dynasty_2
        )

        assert len(result2) == 1
        assert result2[0]['player_id'] == player2
        assert result2[0]['overall'] == 82

    def test_empty_result_for_wrong_dynasty(self, cap_api_with_players, test_dynasty_id, test_db_with_schema):
        """Test that querying wrong dynasty returns empty result."""
        # Insert contract in test_dynasty_id
        player_id = insert_test_player(test_db_with_schema, test_dynasty_id, team_id=7, overall=85)
        cap_api_with_players.insert_contract(
            player_id=player_id, team_id=7, dynasty_id=test_dynasty_id,
            start_year=2020, end_year=2024, contract_years=5,
            contract_type='VETERAN', total_value=50_000_000
        )

        # Query different dynasty
        result = cap_api_with_players.get_pending_free_agents(
            team_id=7,
            season=2024,
            dynasty_id="different_dynasty"
        )

        assert result == []
