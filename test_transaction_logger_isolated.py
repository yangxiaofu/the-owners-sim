#!/usr/bin/env python3
"""
Isolated test for TransactionLogger to verify database writes work.

This test creates a mock trade transaction and verifies it's written to the database.
"""
import sys
from pathlib import Path
from datetime import date

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from persistence.transaction_logger import TransactionLogger
import sqlite3

DB_PATH = "data/database/nfl_simulation.db"

def test_transaction_logger():
    """Test that TransactionLogger can write to player_transactions table."""
    print("=" * 80)
    print("TRANSACTION LOGGER ISOLATED TEST")
    print("=" * 80)

    # Initialize logger
    print("\n1. Initializing TransactionLogger...")
    logger = TransactionLogger(DB_PATH)
    print("   ✅ Logger initialized")

    # Test data for a mock trade
    test_data = {
        "dynasty_id": "1st",  # Match the dynasty_id in players table
        "season": 2024,
        "transaction_type": "TRADE",
        "player_id": 999999,  # Mock player ID
        "player_name": "Test Player",
        "position": "QB",
        "from_team_id": 1,
        "to_team_id": 2,
        "transaction_date": date.today(),
        "details": {"trade_partner": "Test Team 2"},
        "event_id": "test_event_123"
    }

    print(f"\n2. Test data:")
    print(f"   Dynasty ID: {test_data['dynasty_id']}")
    print(f"   Player: {test_data['player_name']} (ID: {test_data['player_id']})")
    print(f"   Type: {test_data['transaction_type']}")
    print(f"   From Team: {test_data['from_team_id']} → To Team: {test_data['to_team_id']}")

    # Attempt to log transaction
    print("\n3. Attempting to log transaction...")
    try:
        transaction_id = logger.log_transaction(**test_data)
        print(f"   ✅ Transaction logged successfully!")
        print(f"   Transaction ID: {transaction_id}")
    except Exception as e:
        print(f"   ❌ FAILED to log transaction: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify transaction was written to database
    print("\n4. Verifying transaction in database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT transaction_id, player_name, transaction_type,
               from_team_id, to_team_id, dynasty_id
        FROM player_transactions
        WHERE transaction_id = ?
    """, (transaction_id,))

    result = cursor.fetchone()
    conn.close()

    if result:
        print(f"   ✅ Transaction found in database!")
        print(f"   ID: {result[0]}")
        print(f"   Player: {result[1]}")
        print(f"   Type: {result[2]}")
        print(f"   Movement: Team {result[3]} → Team {result[4]}")
        print(f"   Dynasty: {result[5]}")
    else:
        print(f"   ❌ Transaction NOT found in database!")
        return False

    # Check total count
    print("\n5. Checking total transaction count...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM player_transactions")
    total = cursor.fetchone()[0]
    conn.close()
    print(f"   Total transactions in table: {total}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE - TransactionLogger is working correctly!")
    print("=" * 80)
    print("\nCONCLUSION:")
    print("If this test passed but trades still don't log transactions,")
    print("the issue is in trade_events.py, NOT in TransactionLogger.")
    print("\nNext step: Check if get_player_by_id() is returning None")

    return True

if __name__ == "__main__":
    success = test_transaction_logger()
    sys.exit(0 if success else 1)
