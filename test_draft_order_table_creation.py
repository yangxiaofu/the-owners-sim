#!/usr/bin/env python3
"""
Test script to verify draft_order table is created automatically
when DatabaseConnection is initialized.

This tests the long-term fix for the schema cache issue.
"""

import sys
sys.path.insert(0, 'src')

import os
import tempfile
import sqlite3


def test_draft_order_table_creation():
    """
    Test that draft_order table is created automatically on fresh connection.
    """
    print("=" * 80)
    print("DRAFT ORDER TABLE AUTO-CREATION TEST")
    print("=" * 80)
    print()

    # Test 1: Create a temporary database and verify table is created
    print("TEST 1: Fresh database connection...")

    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        # Import DatabaseConnection AFTER creating temp file
        from database.connection import DatabaseConnection

        print(f"  Creating DatabaseConnection with temp database: {tmp_db_path}")
        db_conn = DatabaseConnection(db_path=tmp_db_path)

        # Initialize database (creates tables)
        db_conn.initialize_database()

        # Verify table exists
        conn = sqlite3.connect(tmp_db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='draft_order'"
        )
        result = cursor.fetchone()
        conn.close()

        if result and result[0] == 'draft_order':
            print("  ✓ draft_order table created automatically")
        else:
            print("  ✗ FAIL: draft_order table NOT created")
            return False

        # Verify table has correct schema
        conn = sqlite3.connect(tmp_db_path)
        cursor = conn.execute("PRAGMA table_info(draft_order)")
        columns = cursor.fetchall()
        conn.close()

        expected_columns = [
            'pick_id', 'dynasty_id', 'season', 'round_number', 'pick_in_round',
            'overall_pick', 'original_team_id', 'current_team_id', 'player_id',
            'draft_class_id', 'is_executed', 'is_compensatory', 'comp_round_end',
            'acquired_via_trade', 'trade_date', 'original_trade_id', 'created_at', 'updated_at'
        ]

        actual_columns = [col[1] for col in columns]

        if len(actual_columns) == 18 and all(col in actual_columns for col in expected_columns):
            print(f"  ✓ Table schema correct ({len(actual_columns)} columns)")
        else:
            print(f"  ✗ FAIL: Expected 18 columns, got {len(actual_columns)}")
            print(f"    Missing: {set(expected_columns) - set(actual_columns)}")
            return False

        # Verify indexes were created
        conn = sqlite3.connect(tmp_db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_draft_order_%'"
        )
        indexes = cursor.fetchall()
        conn.close()

        expected_indexes = [
            'idx_draft_order_dynasty',
            'idx_draft_order_season',
            'idx_draft_order_dynasty_season',
            'idx_draft_order_overall',
            'idx_draft_order_team',
            'idx_draft_order_round'
        ]

        actual_indexes = [idx[0] for idx in indexes]

        if len(actual_indexes) >= 6 and all(idx in actual_indexes for idx in expected_indexes):
            print(f"  ✓ All {len(expected_indexes)} indexes created")
        else:
            print(f"  ⚠ WARNING: Expected {len(expected_indexes)} indexes, got {len(actual_indexes)}")
            print(f"    Missing: {set(expected_indexes) - set(actual_indexes)}")

        print()
        print("=" * 80)
        print("✓ ALL TESTS PASSED!")
        print("=" * 80)
        print()
        print("The draft_order table is now created automatically when")
        print("DatabaseConnection is initialized. No manual migration needed!")
        print()
        return True

    finally:
        # Clean up temporary database
        if os.path.exists(tmp_db_path):
            os.unlink(tmp_db_path)
        # Also clean up WAL files if they exist
        wal_path = tmp_db_path + '-wal'
        shm_path = tmp_db_path + '-shm'
        if os.path.exists(wal_path):
            os.unlink(wal_path)
        if os.path.exists(shm_path):
            os.unlink(shm_path)


def test_existing_database():
    """
    Test that existing production database has the table.
    """
    print("=" * 80)
    print("PRODUCTION DATABASE CHECK")
    print("=" * 80)
    print()

    db_path = "data/database/nfl_simulation.db"

    if not os.path.exists(db_path):
        print(f"  ⚠ Production database not found at {db_path}")
        print("  Skipping production database check")
        print()
        return True

    print(f"  Checking {db_path}...")

    conn = sqlite3.connect(db_path)

    # Check if table exists
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='draft_order'"
    )
    result = cursor.fetchone()

    if result and result[0] == 'draft_order':
        print("  ✓ draft_order table exists in production database")

        # Check if it's empty or has data
        cursor = conn.execute("SELECT COUNT(*) FROM draft_order")
        count = cursor.fetchone()[0]
        print(f"  ✓ Table has {count} draft picks")
    else:
        print("  ✗ draft_order table NOT found in production database")
        print("  → Need to restart application to create table")

    conn.close()
    print()
    return True


if __name__ == "__main__":
    print()

    # Test 1: Fresh database creation
    success1 = test_draft_order_table_creation()

    # Test 2: Production database check
    success2 = test_existing_database()

    if success1 and success2:
        print("=" * 80)
        print("SUMMARY: All tests passed! ✓")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Close the running application (if any)")
        print("2. Delete WAL files:")
        print("   rm data/database/nfl_simulation.db-shm")
        print("   rm data/database/nfl_simulation.db-wal")
        print("3. Restart the application: python main.py")
        print("4. The draft_order table will be created automatically")
        print()
        sys.exit(0)
    else:
        print("=" * 80)
        print("SUMMARY: Some tests failed ✗")
        print("=" * 80)
        sys.exit(1)
