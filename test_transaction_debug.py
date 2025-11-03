#!/usr/bin/env python3
"""
Test script for transaction debug dialog functionality.
"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test that all required imports work."""
    print("Testing imports...")

    try:
        from constants.team_ids import TeamIDs
        print("✓ TeamIDs imported")

        from team_management.teams.team_loader import get_team_by_id
        print("✓ get_team_by_id imported")

        from persistence.transaction_api import TransactionAPI
        print("✓ TransactionAPI imported")

        from ui.dialogs.transaction_log_dialog import TransactionLogDialog
        print("✓ TransactionLogDialog imported")

        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_transaction_api():
    """Test transaction API functionality."""
    print("\nTesting TransactionAPI...")

    try:
        from persistence.transaction_api import TransactionAPI
        from constants.team_ids import TeamIDs
        import random

        # Create API instance
        api = TransactionAPI("data/database/nfl_simulation.db")
        print("✓ TransactionAPI created")

        # Get random team
        random_team_id = random.choice(TeamIDs.get_all_team_ids())
        print(f"✓ Random team selected: {random_team_id}")

        # Query transactions
        transactions = api.get_team_transactions(
            team_id=random_team_id,
            dynasty_id="default"
        )
        print(f"✓ Transactions queried: {len(transactions)} found")

        # Show first few transactions
        if transactions:
            print("\nSample transactions:")
            for txn in transactions[:3]:
                print(f"  - {txn.get('transaction_date')}: {txn.get('transaction_type')} - {txn.get('player_name')}")
        else:
            print("  (No transactions found for this team)")

        return True
    except Exception as e:
        print(f"✗ TransactionAPI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_team_data():
    """Test team data loading."""
    print("\nTesting team data loading...")

    try:
        from constants.team_ids import TeamIDs
        from team_management.teams.team_loader import get_team_by_id
        import random

        # Get all team IDs
        all_team_ids = TeamIDs.get_all_team_ids()
        print(f"✓ Found {len(all_team_ids)} teams")

        # Get random team
        random_team_id = random.choice(all_team_ids)
        team = get_team_by_id(random_team_id)
        print(f"✓ Random team loaded: {team.full_name} (ID: {random_team_id})")

        return True
    except Exception as e:
        print(f"✗ Team data test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Transaction Debug Dialog Test Suite")
    print("=" * 60)

    results = []

    # Test imports
    results.append(("Imports", test_imports()))

    # Test team data
    results.append(("Team Data", test_team_data()))

    # Test transaction API
    results.append(("TransactionAPI", test_transaction_api()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name:20} {status}")

    all_passed = all(passed for _, passed in results)
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed!"))
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
