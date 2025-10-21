"""
Test script for draft tables database migration.

This script validates:
1. SQL syntax is valid
2. Tables can be created successfully
3. Indexes are created properly
4. Foreign key constraints work correctly
5. Unique constraints are enforced
"""

import sqlite3
import tempfile
import os
from pathlib import Path


def test_draft_tables_migration():
    """Test the draft tables migration SQL script."""

    # Get the migration SQL file path
    migrations_dir = Path(__file__).parent.parent.parent / "src" / "database" / "migrations"
    migration_file = migrations_dir / "add_draft_tables.sql"

    print(f"Testing migration file: {migration_file}")
    print(f"File exists: {migration_file.exists()}")

    # Read the migration SQL
    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    print(f"\nMigration SQL length: {len(migration_sql)} characters")

    # Create a temporary in-memory database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Enable foreign key constraints FIRST (SQLite requires this)
    cursor.execute("PRAGMA foreign_keys = ON")

    print("\n" + "="*80)
    print("TEST 1: Create dynasties table (prerequisite)")
    print("="*80)

    # Create the dynasties table first (required for foreign keys)
    cursor.execute("""
        CREATE TABLE dynasties (
            dynasty_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Dynasties table created successfully")

    print("\n" + "="*80)
    print("TEST 2: Execute migration SQL")
    print("="*80)

    try:
        # Execute the migration SQL
        cursor.executescript(migration_sql)
        print("✓ Migration SQL executed successfully")
    except sqlite3.Error as e:
        print(f"✗ Migration SQL failed: {e}")
        conn.close()
        return False

    print("\n" + "="*80)
    print("TEST 3: Verify tables were created")
    print("="*80)

    # Check that tables exist
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name IN ('draft_classes', 'draft_prospects')
        ORDER BY name
    """)
    tables = cursor.fetchall()
    print(f"Tables found: {[t[0] for t in tables]}")

    if len(tables) != 2:
        print(f"✗ Expected 2 tables, found {len(tables)}")
        conn.close()
        return False
    print("✓ Both tables created successfully")

    print("\n" + "="*80)
    print("TEST 4: Verify indexes were created")
    print("="*80)

    # Check that indexes exist
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name LIKE 'idx_%'
        ORDER BY name
    """)
    indexes = cursor.fetchall()
    print(f"Indexes found ({len(indexes)}):")
    for idx in indexes:
        print(f"  - {idx[0]}")

    expected_indexes = [
        'idx_draft_classes_dynasty',
        'idx_draft_classes_season',
        'idx_prospects_draft_class',
        'idx_prospects_dynasty',
        'idx_prospects_position',
        'idx_prospects_available',
        'idx_prospects_overall',
        'idx_prospects_player_id'
    ]

    if len(indexes) != len(expected_indexes):
        print(f"✗ Expected {len(expected_indexes)} indexes, found {len(indexes)}")
        conn.close()
        return False
    print(f"✓ All {len(indexes)} indexes created successfully")

    print("\n" + "="*80)
    print("TEST 5: Test data insertion")
    print("="*80)

    # Insert test dynasty
    cursor.execute("INSERT INTO dynasties (dynasty_id) VALUES ('test_dynasty')")
    print("✓ Test dynasty inserted")

    # Insert test draft class
    cursor.execute("""
        INSERT INTO draft_classes (draft_class_id, dynasty_id, season, total_prospects)
        VALUES ('DRAFT_test_dynasty_2024', 'test_dynasty', 2024, 10)
    """)
    print("✓ Test draft class inserted")

    # Insert test prospect
    cursor.execute("""
        INSERT INTO draft_prospects (
            player_id, draft_class_id, dynasty_id,
            first_name, last_name, position, age,
            draft_round, draft_pick, overall, attributes
        )
        VALUES (
            1, 'DRAFT_test_dynasty_2024', 'test_dynasty',
            'John', 'Doe', 'QB', 21,
            1, 1, 95, '{"awareness": 90, "speed": 85}'
        )
    """)
    print("✓ Test prospect inserted")

    # Verify data
    cursor.execute("SELECT COUNT(*) FROM draft_classes")
    draft_class_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM draft_prospects")
    prospect_count = cursor.fetchone()[0]

    print(f"✓ Draft classes: {draft_class_count}, Prospects: {prospect_count}")

    print("\n" + "="*80)
    print("TEST 6: Test unique constraint (dynasty + season)")
    print("="*80)

    try:
        cursor.execute("""
            INSERT INTO draft_classes (draft_class_id, dynasty_id, season)
            VALUES ('DRAFT_test_dynasty_2024_duplicate', 'test_dynasty', 2024)
        """)
        print("✗ Unique constraint NOT enforced (should have failed)")
        conn.close()
        return False
    except sqlite3.IntegrityError:
        print("✓ Unique constraint enforced correctly")

    print("\n" + "="*80)
    print("TEST 7: Test foreign key constraint (cascade delete)")
    print("="*80)

    # Verify foreign keys are enabled
    cursor.execute("PRAGMA foreign_keys")
    fk_enabled = cursor.fetchone()[0]
    print(f"Foreign keys enabled: {bool(fk_enabled)}")

    # Delete the draft class
    cursor.execute("DELETE FROM draft_classes WHERE draft_class_id = 'DRAFT_test_dynasty_2024'")

    # Check that prospect was also deleted
    cursor.execute("SELECT COUNT(*) FROM draft_prospects WHERE draft_class_id = 'DRAFT_test_dynasty_2024'")
    remaining_prospects = cursor.fetchone()[0]

    if remaining_prospects == 0:
        print("✓ Foreign key cascade delete working correctly")
    else:
        print(f"✗ Foreign key cascade delete failed ({remaining_prospects} prospects remaining)")
        conn.close()
        return False

    print("\n" + "="*80)
    print("TEST 8: Verify column definitions")
    print("="*80)

    # Check draft_classes columns
    cursor.execute("PRAGMA table_info(draft_classes)")
    draft_classes_columns = {col[1]: col[2] for col in cursor.fetchall()}
    print(f"draft_classes columns ({len(draft_classes_columns)}):")
    for col_name, col_type in draft_classes_columns.items():
        print(f"  - {col_name}: {col_type}")

    # Check draft_prospects columns
    cursor.execute("PRAGMA table_info(draft_prospects)")
    draft_prospects_columns = {col[1]: col[2] for col in cursor.fetchall()}
    print(f"\ndraft_prospects columns ({len(draft_prospects_columns)}):")
    for col_name, col_type in draft_prospects_columns.items():
        print(f"  - {col_name}: {col_type}")

    # Verify key columns exist
    required_draft_class_cols = ['draft_class_id', 'dynasty_id', 'season', 'total_prospects', 'status']
    required_prospect_cols = ['player_id', 'draft_class_id', 'dynasty_id', 'position', 'overall', 'attributes']

    missing_draft_cols = [col for col in required_draft_class_cols if col not in draft_classes_columns]
    missing_prospect_cols = [col for col in required_prospect_cols if col not in draft_prospects_columns]

    if missing_draft_cols:
        print(f"\n✗ Missing draft_classes columns: {missing_draft_cols}")
        conn.close()
        return False

    if missing_prospect_cols:
        print(f"\n✗ Missing draft_prospects columns: {missing_prospect_cols}")
        conn.close()
        return False

    print("\n✓ All required columns present")

    # Close connection
    conn.close()

    print("\n" + "="*80)
    print("ALL TESTS PASSED ✓")
    print("="*80)
    print("\nMigration is ready for production use!")


if __name__ == "__main__":
    success = test_draft_tables_migration()
    exit(0 if success else 1)
