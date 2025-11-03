"""
Test Trade Events System (Phase 1.6)

Comprehensive tests for the trade event execution layer that bridges AI-generated
trade proposals with database persistence. Tests player-for-player trades,
validation, cap space checking, contract transfers, and transaction logging.

Phase 1.6 of ai_transactions_plan.md
"""

import pytest
from datetime import datetime
import sqlite3
import tempfile
import os

# Add src to path for testing
import sys
from pathlib import Path
src_path = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, src_path)

from events.trade_events import PlayerForPlayerTradeEvent
from events.base_event import EventResult
from calendar.date_models import Date
from salary_cap import EventCapBridge, TradeEventHandler
from salary_cap.event_integration import ValidationMiddleware


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def trade_db_path():
    """
    Create temporary database for trade testing.

    Yields:
        Path to temporary database file

    Cleanup:
        Removes database after test
    """
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Initialize database with required tables
    conn = sqlite3.connect(path)
    conn.execute('PRAGMA foreign_keys = ON')

    # Create dynasties table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        )
    ''')

    # Create player_contracts table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS player_contracts (
            contract_id TEXT PRIMARY KEY,
            player_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            current_year_cap_hit INTEGER DEFAULT 0,
            base_salary INTEGER DEFAULT 0,
            signing_bonus INTEGER DEFAULT 0,
            total_value INTEGER DEFAULT 0,
            years_remaining INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',
            dynasty_id TEXT NOT NULL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        )
    ''')

    # Create cap_transactions table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cap_transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            transaction_date TEXT NOT NULL,
            cap_impact_current INTEGER DEFAULT 0,
            description TEXT,
            dynasty_id TEXT NOT NULL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        )
    ''')

    # Create team_salary_cap table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS team_salary_cap (
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            dynasty_id TEXT NOT NULL,
            salary_cap INTEGER DEFAULT 255400000,
            cap_space INTEGER DEFAULT 0,
            active_contracts_total INTEGER DEFAULT 0,
            is_over_cap INTEGER DEFAULT 0,
            PRIMARY KEY (team_id, season, dynasty_id),
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        )
    ''')

    conn.commit()
    conn.close()

    yield path

    # Cleanup
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def dynasties_setup(trade_db_path):
    """
    Create test dynasties in the database.

    Returns:
        Dict with dynasty_id keys for easy reference
    """
    conn = sqlite3.connect(trade_db_path)

    dynasties = {
        'eagles_dynasty': datetime.now().isoformat(),
        'chiefs_dynasty': datetime.now().isoformat(),
        'test_dynasty': datetime.now().isoformat()
    }

    for dynasty_id, created_at in dynasties.items():
        conn.execute(
            'INSERT INTO dynasties (dynasty_id, created_at) VALUES (?, ?)',
            (dynasty_id, created_at)
        )

    conn.commit()
    conn.close()

    return dynasties


@pytest.fixture
def sample_contracts(trade_db_path, dynasties_setup):
    """
    Create sample player contracts for testing.

    Creates contracts for 4 players (2 per team) with realistic cap hits.

    Returns:
        Dict with contract details
    """
    conn = sqlite3.connect(trade_db_path)

    contracts = {
        'player_1001': {
            'contract_id': 'contract_1001',
            'player_id': 'player_1001',
            'team_id': 7,  # Eagles
            'season': 2025,
            'current_year_cap_hit': 15000000,  # $15M
            'base_salary': 12000000,
            'signing_bonus': 3000000,
            'total_value': 60000000,
            'years_remaining': 4,
            'status': 'active',
            'dynasty_id': 'test_dynasty'
        },
        'player_1002': {
            'contract_id': 'contract_1002',
            'player_id': 'player_1002',
            'team_id': 7,  # Eagles
            'season': 2025,
            'current_year_cap_hit': 8000000,  # $8M
            'base_salary': 7000000,
            'signing_bonus': 1000000,
            'total_value': 32000000,
            'years_remaining': 4,
            'status': 'active',
            'dynasty_id': 'test_dynasty'
        },
        'player_2001': {
            'contract_id': 'contract_2001',
            'player_id': 'player_2001',
            'team_id': 22,  # Lions
            'season': 2025,
            'current_year_cap_hit': 12000000,  # $12M
            'base_salary': 10000000,
            'signing_bonus': 2000000,
            'total_value': 48000000,
            'years_remaining': 4,
            'status': 'active',
            'dynasty_id': 'test_dynasty'
        },
        'player_2002': {
            'contract_id': 'contract_2002',
            'player_id': 'player_2002',
            'team_id': 22,  # Lions
            'season': 2025,
            'current_year_cap_hit': 6000000,  # $6M
            'base_salary': 5500000,
            'signing_bonus': 500000,
            'total_value': 24000000,
            'years_remaining': 4,
            'status': 'active',
            'dynasty_id': 'test_dynasty'
        }
    }

    for player_id, contract in contracts.items():
        conn.execute('''
            INSERT INTO player_contracts (
                contract_id, player_id, team_id, season,
                current_year_cap_hit, base_salary, signing_bonus,
                total_value, years_remaining, status, dynasty_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            contract['contract_id'], contract['player_id'], contract['team_id'],
            contract['season'], contract['current_year_cap_hit'],
            contract['base_salary'], contract['signing_bonus'],
            contract['total_value'], contract['years_remaining'],
            contract['status'], contract['dynasty_id']
        ))

    conn.commit()
    conn.close()

    return contracts


@pytest.fixture
def team_cap_setup(trade_db_path, dynasties_setup):
    """
    Initialize team salary cap records.

    Both teams have enough cap space to handle typical trades.

    Returns:
        Dict with team cap status
    """
    conn = sqlite3.connect(trade_db_path)

    teams = {
        7: {  # Eagles
            'team_id': 7,
            'season': 2025,
            'dynasty_id': 'test_dynasty',
            'salary_cap': 255400000,
            'cap_space': 50000000,  # $50M cap space
            'active_contracts_total': 205400000,
            'is_over_cap': 0
        },
        22: {  # Lions
            'team_id': 22,
            'season': 2025,
            'dynasty_id': 'test_dynasty',
            'salary_cap': 255400000,
            'cap_space': 40000000,  # $40M cap space
            'active_contracts_total': 215400000,
            'is_over_cap': 0
        }
    }

    for team_id, cap_status in teams.items():
        conn.execute('''
            INSERT INTO team_salary_cap (
                team_id, season, dynasty_id, salary_cap,
                cap_space, active_contracts_total, is_over_cap
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            cap_status['team_id'], cap_status['season'],
            cap_status['dynasty_id'], cap_status['salary_cap'],
            cap_status['cap_space'], cap_status['active_contracts_total'],
            cap_status['is_over_cap']
        ))

    conn.commit()
    conn.close()

    return teams


# ============================================================================
# TEST: BASIC TRADE EXECUTION
# ============================================================================

class TestBasicTradeExecution:
    """Test basic player-for-player trade execution."""

    def test_simple_1_for_1_trade(
        self, trade_db_path, sample_contracts, team_cap_setup
    ):
        """
        Test simple 1-for-1 player trade.

        Eagles send player_1001 ($15M) to Lions
        Lions send player_2001 ($12M) to Eagles
        """
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['player_1001'],
            team2_player_ids=['player_2001'],
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='test_dynasty',
            database_path=trade_db_path
        )

        result = trade_event.simulate()

        assert result.success, f"Trade should succeed: {result.error_message}"
        assert result.event_type == "PLAYER_TRADE"
        assert result.data['team1_id'] == 7
        assert result.data['team2_id'] == 22

    def test_multi_player_2_for_2_trade(
        self, trade_db_path, sample_contracts, team_cap_setup
    ):
        """
        Test 2-for-2 player trade.

        Eagles send player_1001 ($15M) + player_1002 ($8M) = $23M
        Lions send player_2001 ($12M) + player_2002 ($6M) = $18M
        """
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['player_1001', 'player_1002'],
            team2_player_ids=['player_2001', 'player_2002'],
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='test_dynasty',
            database_path=trade_db_path
        )

        result = trade_event.simulate()

        assert result.success, f"Trade should succeed: {result.error_message}"
        assert len(result.data['team1_players_sent']) == 2
        assert len(result.data['team2_players_sent']) == 2


# ============================================================================
# TEST: TRADE VALIDATION
# ============================================================================

class TestTradeValidation:
    """Test trade validation before execution."""

    def test_validate_preconditions_same_team_rejected(self):
        """Test that trading with same team is rejected in precondition check."""
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=7,  # Same team!
            team1_player_ids=['player_1001'],
            team2_player_ids=['player_2001'],
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='test_dynasty',
            database_path=':memory:'
        )

        is_valid, error_msg = trade_event.validate_preconditions()

        assert not is_valid
        assert 'same team' in error_msg.lower()

    def test_validate_preconditions_empty_player_list_rejected(self):
        """Test that empty player list is rejected."""
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=[],  # Empty!
            team2_player_ids=['player_2001'],
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='test_dynasty',
            database_path=':memory:'
        )

        is_valid, error_msg = trade_event.validate_preconditions()

        assert not is_valid
        assert 'at least one player' in error_msg.lower()

    def test_duplicate_player_validation(
        self, trade_db_path, sample_contracts, team_cap_setup
    ):
        """
        Test that duplicate players are rejected.

        Attempt to trade player_1001 on both sides (invalid).
        """
        bridge = EventCapBridge(trade_db_path)
        validator = ValidationMiddleware(
            cap_calculator=bridge.calculator,
            cap_validator=bridge.validator,
            tag_manager=bridge.tag_mgr,
            cap_db=bridge.cap_db
        )

        is_valid, error_msg = validator.validate_player_trade(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['player_1001'],
            team2_player_ids=['player_1001'],  # Duplicate!
            season=2025,
            dynasty_id='test_dynasty',
            trade_date=datetime(2025, 10, 15).date()
        )

        assert not is_valid
        assert 'duplicate' in error_msg.lower()

    def test_player_without_contract_validation(
        self, trade_db_path, sample_contracts, team_cap_setup
    ):
        """
        Test that player without active contract is rejected.
        """
        bridge = EventCapBridge(trade_db_path)
        validator = ValidationMiddleware(
            cap_calculator=bridge.calculator,
            cap_validator=bridge.validator,
            tag_manager=bridge.tag_mgr,
            cap_db=bridge.cap_db
        )

        is_valid, error_msg = validator.validate_player_trade(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['player_9999'],  # Doesn't exist
            team2_player_ids=['player_2001'],
            season=2025,
            dynasty_id='test_dynasty',
            trade_date=datetime(2025, 10, 15).date()
        )

        assert not is_valid
        assert 'contract' in error_msg.lower() or 'not found' in error_msg.lower()


# ============================================================================
# TEST: CAP SPACE VALIDATION
# ============================================================================

class TestCapSpaceValidation:
    """Test salary cap space validation for trades."""

    def test_insufficient_cap_space_rejected(self, trade_db_path, dynasties_setup):
        """
        Test that trade is rejected if team lacks cap space.

        Create team with only $5M cap space, attempt to trade in $15M player.
        """
        conn = sqlite3.connect(trade_db_path)

        # Create contracts
        conn.execute('''
            INSERT INTO player_contracts (
                contract_id, player_id, team_id, season,
                current_year_cap_hit, base_salary, signing_bonus,
                total_value, years_remaining, status, dynasty_id
            ) VALUES
            ('c1', 'p1', 7, 2025, 5000000, 5000000, 0, 20000000, 4, 'active', 'test_dynasty'),
            ('c2', 'p2', 22, 2025, 15000000, 15000000, 0, 60000000, 4, 'active', 'test_dynasty')
        ''')

        # Create team caps - Team 7 only has $5M space
        conn.execute('''
            INSERT INTO team_salary_cap (
                team_id, season, dynasty_id, salary_cap, cap_space
            ) VALUES
            (7, 2025, 'test_dynasty', 255400000, 5000000),
            (22, 2025, 'test_dynasty', 255400000, 50000000)
        ''')

        conn.commit()
        conn.close()

        # Attempt trade: Team 7 gets $15M player but only has $5M space
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['p1'],  # Sending $5M
            team2_player_ids=['p2'],  # Receiving $15M (needs $10M net space)
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='test_dynasty',
            database_path=trade_db_path
        )

        result = trade_event.simulate()

        assert not result.success
        assert 'cap space' in result.error_message.lower()

    def test_trade_with_sufficient_cap_space_succeeds(
        self, trade_db_path, sample_contracts, team_cap_setup
    ):
        """
        Test that trade succeeds when both teams have sufficient cap space.
        """
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['player_1001'],  # $15M
            team2_player_ids=['player_2001'],  # $12M
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='test_dynasty',
            database_path=trade_db_path
        )

        result = trade_event.simulate()

        assert result.success, f"Trade should succeed: {result.error_message}"


# ============================================================================
# TEST: CONTRACT TRANSFERS
# ============================================================================

class TestContractTransfers:
    """Test that player contracts are correctly transferred between teams."""

    def test_contract_team_id_updated(
        self, trade_db_path, sample_contracts, team_cap_setup
    ):
        """
        Test that contract team_id is updated after trade.
        """
        # Execute trade
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['player_1001'],
            team2_player_ids=['player_2001'],
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='test_dynasty',
            database_path=trade_db_path
        )

        result = trade_event.simulate()
        assert result.success

        # Verify contract team_id changed
        conn = sqlite3.connect(trade_db_path)
        cursor = conn.cursor()

        # player_1001 should now be on team 22
        cursor.execute('''
            SELECT team_id FROM player_contracts
            WHERE player_id = ? AND season = ?
        ''', ('player_1001', 2025))
        team_id = cursor.fetchone()[0]
        assert team_id == 22, "player_1001 should now be on team 22"

        # player_2001 should now be on team 7
        cursor.execute('''
            SELECT team_id FROM player_contracts
            WHERE player_id = ? AND season = ?
        ''', ('player_2001', 2025))
        team_id = cursor.fetchone()[0]
        assert team_id == 7, "player_2001 should now be on team 7"

        conn.close()

    def test_contract_details_preserved(
        self, trade_db_path, sample_contracts, team_cap_setup
    ):
        """
        Test that contract details (cap hit, years, etc.) are preserved.
        """
        # Execute trade
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['player_1001'],
            team2_player_ids=['player_2001'],
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='test_dynasty',
            database_path=trade_db_path
        )

        result = trade_event.simulate()
        assert result.success

        # Verify contract details unchanged
        conn = sqlite3.connect(trade_db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT current_year_cap_hit, base_salary, signing_bonus,
                   years_remaining, status
            FROM player_contracts
            WHERE player_id = ?
        ''', ('player_1001',))

        row = cursor.fetchone()
        assert row[0] == 15000000, "Cap hit should be preserved"
        assert row[1] == 12000000, "Base salary should be preserved"
        assert row[2] == 3000000, "Signing bonus should be preserved"
        assert row[3] == 4, "Years remaining should be preserved"
        assert row[4] == 'active', "Status should remain active"

        conn.close()


# ============================================================================
# TEST: TRANSACTION LOGGING
# ============================================================================

class TestTransactionLogging:
    """Test that trades are properly logged in cap_transactions table."""

    def test_two_transactions_created(
        self, trade_db_path, sample_contracts, team_cap_setup
    ):
        """
        Test that 2 transaction records are created (one per team).
        """
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['player_1001'],
            team2_player_ids=['player_2001'],
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='test_dynasty',
            database_path=trade_db_path
        )

        result = trade_event.simulate()
        assert result.success

        # Verify 2 transaction records
        conn = sqlite3.connect(trade_db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) FROM cap_transactions
            WHERE transaction_type = 'TRADE' AND dynasty_id = 'test_dynasty'
        ''')

        count = cursor.fetchone()[0]
        assert count == 2, "Should create exactly 2 transaction records"

        conn.close()

    def test_transaction_cap_impact_correct(
        self, trade_db_path, sample_contracts, team_cap_setup
    ):
        """
        Test that transaction cap impact is correctly calculated.

        Eagles send $15M, receive $12M → Net -$3M (freed cap)
        Lions send $12M, receive $15M → Net +$3M (used cap)
        """
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['player_1001'],  # $15M
            team2_player_ids=['player_2001'],  # $12M
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='test_dynasty',
            database_path=trade_db_path
        )

        result = trade_event.simulate()
        assert result.success

        # Verify cap impact in result
        assert result.data['team1_net_cap_change'] == -3000000, \
            "Team 7 should free $3M cap space"
        assert result.data['team2_net_cap_change'] == 3000000, \
            "Team 22 should use $3M cap space"

    def test_transaction_description(
        self, trade_db_path, sample_contracts, team_cap_setup
    ):
        """
        Test that transaction description is properly formatted.
        """
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['player_1001'],
            team2_player_ids=['player_2001'],
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='test_dynasty',
            database_path=trade_db_path
        )

        result = trade_event.simulate()
        assert result.success

        # Verify transaction descriptions
        conn = sqlite3.connect(trade_db_path)
        cursor = conn.cursor()

        # Team 7's transaction
        cursor.execute('''
            SELECT description FROM cap_transactions
            WHERE team_id = 7 AND transaction_type = 'TRADE'
        ''')
        desc = cursor.fetchone()[0]
        assert 'team 22' in desc.lower()
        assert 'sent 1 player' in desc.lower()
        assert 'received 1 player' in desc.lower()

        conn.close()


# ============================================================================
# TEST: DYNASTY ISOLATION
# ============================================================================

class TestDynastyIsolation:
    """Test that trades respect dynasty boundaries."""

    def test_trade_only_affects_correct_dynasty(self, trade_db_path, dynasties_setup):
        """
        Test that trade in one dynasty doesn't affect another dynasty.
        """
        conn = sqlite3.connect(trade_db_path)

        # Create identical players in two dynasties
        for dynasty in ['eagles_dynasty', 'chiefs_dynasty']:
            conn.execute('''
                INSERT INTO player_contracts (
                    contract_id, player_id, team_id, season,
                    current_year_cap_hit, status, dynasty_id
                ) VALUES
                (?, 'p1', 7, 2025, 10000000, 'active', ?),
                (?, 'p2', 22, 2025, 10000000, 'active', ?)
            ''', (f'c1_{dynasty}', dynasty, f'c2_{dynasty}', dynasty))

            conn.execute('''
                INSERT INTO team_salary_cap (
                    team_id, season, dynasty_id, cap_space
                ) VALUES (7, 2025, ?, 50000000), (22, 2025, ?, 50000000)
            ''', (dynasty, dynasty))

        conn.commit()
        conn.close()

        # Execute trade in eagles_dynasty only
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['p1'],
            team2_player_ids=['p2'],
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='eagles_dynasty',
            database_path=trade_db_path
        )

        result = trade_event.simulate()
        assert result.success

        # Verify eagles_dynasty contracts updated
        conn = sqlite3.connect(trade_db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT team_id FROM player_contracts
            WHERE player_id = 'p1' AND dynasty_id = 'eagles_dynasty'
        ''')
        assert cursor.fetchone()[0] == 22, "p1 should be on team 22 in eagles_dynasty"

        # Verify chiefs_dynasty contracts UNCHANGED
        cursor.execute('''
            SELECT team_id FROM player_contracts
            WHERE player_id = 'p1' AND dynasty_id = 'chiefs_dynasty'
        ''')
        assert cursor.fetchone()[0] == 7, "p1 should still be on team 7 in chiefs_dynasty"

        conn.close()


# ============================================================================
# TEST: ERROR HANDLING
# ============================================================================

class TestErrorHandling:
    """Test error handling for various failure scenarios."""

    def test_trade_returns_failed_result_on_validation_failure(
        self, trade_db_path, dynasties_setup
    ):
        """
        Test that validation failure returns EventResult with success=False.
        """
        # No contracts created - validation will fail
        conn = sqlite3.connect(trade_db_path)
        conn.execute('''
            INSERT INTO team_salary_cap (team_id, season, dynasty_id, cap_space)
            VALUES (7, 2025, 'test_dynasty', 50000000), (22, 2025, 'test_dynasty', 50000000)
        ''')
        conn.commit()
        conn.close()

        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['nonexistent'],
            team2_player_ids=['nonexistent2'],
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='test_dynasty',
            database_path=trade_db_path
        )

        result = trade_event.simulate()

        assert not result.success
        assert result.error_message is not None
        assert len(result.error_message) > 0

    def test_exception_in_execution_returns_failed_result(self, trade_db_path):
        """
        Test that exceptions during execution are caught and returned as failed result.
        """
        # Database not properly initialized - should cause exception
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['p1'],
            team2_player_ids=['p2'],
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='nonexistent_dynasty',
            database_path=trade_db_path
        )

        result = trade_event.simulate()

        assert not result.success
        assert result.error_message is not None


# ============================================================================
# TEST: EVENT SERIALIZATION
# ============================================================================

class TestEventSerialization:
    """Test event parameter serialization."""

    def test_get_parameters_returns_all_fields(self):
        """Test that _get_parameters() returns all event parameters."""
        trade_event = PlayerForPlayerTradeEvent(
            team1_id=7,
            team2_id=22,
            team1_player_ids=['p1'],
            team2_player_ids=['p2'],
            season=2025,
            event_date=Date(2025, 10, 15),
            dynasty_id='test_dynasty',
            database_path=':memory:'
        )

        params = trade_event._get_parameters()

        assert params['team1_id'] == 7
        assert params['team2_id'] == 22
        assert params['team1_player_ids'] == ['p1']
        assert params['team2_player_ids'] == ['p2']
        assert params['season'] == 2025
        assert params['dynasty_id'] == 'test_dynasty'
        assert 'event_date' in params


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
