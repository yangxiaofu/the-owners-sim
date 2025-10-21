"""
Test script for TransactionAPI.

Demonstrates usage of all TransactionAPI methods with sample data.
"""

import sys
import os
from datetime import date, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from persistence.transaction_api import TransactionAPI
from salary_cap.cap_database_api import CapDatabaseAPI
from database.connection import DatabaseConnection


def setup_test_data(db_path: str, dynasty_id: str):
    """Create sample transaction data for testing."""
    cap_api = CapDatabaseAPI(db_path)

    # Create test transactions
    today = date.today()

    # Transaction 1: Franchise tag for team 7
    cap_api.log_transaction(
        team_id=7,
        season=2025,
        dynasty_id=dynasty_id,
        transaction_type='TAG',
        transaction_date=today - timedelta(days=30),
        player_id=12345,
        cap_impact_current=25000000,
        description="Franchise tag applied to QB"
    )

    # Transaction 2: UFA signing for team 7
    cap_api.log_transaction(
        team_id=7,
        season=2025,
        dynasty_id=dynasty_id,
        transaction_type='SIGNING',
        transaction_date=today - timedelta(days=25),
        player_id=12346,
        cap_impact_current=15000000,
        cash_impact=40000000,
        description="UFA signing - 4 years, $40M"
    )

    # Transaction 3: Player release for team 7
    cap_api.log_transaction(
        team_id=7,
        season=2025,
        dynasty_id=dynasty_id,
        transaction_type='RELEASE',
        transaction_date=today - timedelta(days=20),
        player_id=12347,
        cap_impact_current=-8000000,
        dead_money_created=12000000,
        description="Released WR - $12M dead money"
    )

    # Transaction 4: Restructure for team 7
    cap_api.log_transaction(
        team_id=7,
        season=2025,
        dynasty_id=dynasty_id,
        transaction_type='RESTRUCTURE',
        transaction_date=today - timedelta(days=15),
        player_id=12348,
        cap_impact_current=-6000000,
        cap_impact_future={"2026": 2000000, "2027": 2000000, "2028": 2000000},
        description="Converted $9M salary to bonus"
    )

    # Transaction 5: Tag for team 9 (different team)
    cap_api.log_transaction(
        team_id=9,
        season=2025,
        dynasty_id=dynasty_id,
        transaction_type='TAG',
        transaction_date=today - timedelta(days=10),
        player_id=12349,
        cap_impact_current=18000000,
        description="Franchise tag applied to DE"
    )

    # Transaction 6: Recent signing for team 7
    cap_api.log_transaction(
        team_id=7,
        season=2025,
        dynasty_id=dynasty_id,
        transaction_type='SIGNING',
        transaction_date=today - timedelta(days=5),
        player_id=12350,
        cap_impact_current=8000000,
        cash_impact=24000000,
        description="UFA signing - 3 years, $24M"
    )

    print("✓ Created 6 sample transactions")


def test_transaction_api():
    """Test all TransactionAPI methods."""
    print("\n" + "="*70)
    print("TransactionAPI Test Script")
    print("="*70)

    # Setup
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    dynasty_id = "test_dynasty"

    try:
        # Initialize database with cap tables
        # Note: CapDatabaseAPI.__init__ will ensure schema exists
        cap_api_init = CapDatabaseAPI(db_path)

        # Create test data
        print("\n--- Setting up test data ---")
        setup_test_data(db_path, dynasty_id)

        # Initialize API
        api = TransactionAPI(db_path)

        # Test 1: Get player transactions
        print("\n--- Test 1: Get player transactions ---")
        player_txns = api.get_player_transactions(12345, dynasty_id)
        print(f"Found {len(player_txns)} transaction(s) for player 12345")
        if player_txns:
            txn = player_txns[0]
            print(f"  Type: {txn['transaction_type']}")
            print(f"  Date: {txn['transaction_date']}")
            print(f"  Cap Impact: ${txn['cap_impact_current']:,}")

        # Test 2: Get team transactions
        print("\n--- Test 2: Get team transactions ---")
        team_txns = api.get_team_transactions(7, dynasty_id)
        print(f"Found {len(team_txns)} transaction(s) for team 7")
        for txn in team_txns[:3]:  # Show first 3
            print(f"  {txn['transaction_date']}: {txn['transaction_type']} - {txn['description']}")

        # Test 3: Get team transactions for specific season
        print("\n--- Test 3: Get team transactions (season filter) ---")
        season_txns = api.get_team_transactions(7, dynasty_id, season=2025)
        print(f"Found {len(season_txns)} transaction(s) for team 7 in 2025")

        # Test 4: Get recent transactions
        print("\n--- Test 4: Get recent transactions (league-wide) ---")
        recent = api.get_recent_transactions(dynasty_id, limit=10)
        print(f"Found {len(recent)} recent transaction(s)")
        for txn in recent[:3]:
            print(f"  Team {txn['team_id']}: {txn['transaction_type']}")

        # Test 5: Get transactions by type
        print("\n--- Test 5: Get transactions by type (TAG) ---")
        tag_txns = api.get_transactions_by_type('TAG', dynasty_id)
        print(f"Found {len(tag_txns)} franchise tag transaction(s)")
        for txn in tag_txns:
            print(f"  Team {txn['team_id']}: Player {txn['player_id']} - ${txn['cap_impact_current']:,}")

        print("\n--- Test 6: Get transactions by type (SIGNING) ---")
        signing_txns = api.get_transactions_by_type('SIGNING', dynasty_id)
        print(f"Found {len(signing_txns)} signing transaction(s)")

        # Test 7: Get transactions by date range
        print("\n--- Test 7: Get transactions by date range ---")
        start = date.today() - timedelta(days=30)
        end = date.today()
        range_txns = api.get_transactions_by_date_range(dynasty_id, start, end)
        print(f"Found {len(range_txns)} transaction(s) in date range")
        print(f"  Start: {start}")
        print(f"  End: {end}")

        # Test 8: Get transaction count by team
        print("\n--- Test 8: Get transaction count by team ---")
        counts = api.get_transaction_count_by_team(dynasty_id, 2025)
        print(f"Transaction counts for {len(counts)} team(s):")
        for team_data in counts:
            print(f"  Team {team_data['team_id']}: {team_data['total_transactions']} total")
            print(f"    Signings: {team_data['signings']}, Releases: {team_data['releases']}, "
                  f"Tags: {team_data['tags']}, Restructures: {team_data['restructures']}")

        # Test 9: Get transaction summary
        print("\n--- Test 9: Get transaction summary ---")
        summary = api.get_transaction_summary(dynasty_id, 2025)
        print(f"Season 2025 Summary:")
        print(f"  Total transactions: {summary['total_transactions']}")
        print(f"  By type:")
        for txn_type, count in summary['transactions_by_type'].items():
            if count > 0:
                print(f"    {txn_type}: {count}")
        print(f"  Total cap impact: ${summary['total_cap_impact']:,}")
        print(f"  Total cash impact: ${summary['total_cash_impact']:,}")
        print(f"  Total dead money: ${summary['total_dead_money']:,}")

        print("\n" + "="*70)
        print("All tests completed successfully!")
        print("="*70 + "\n")

    finally:
        # Clean up test database
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    test_transaction_api()
