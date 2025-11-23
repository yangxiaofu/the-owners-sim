"""
Verification Script for Draft Day Dialog

Tests all dependencies and functionality before running the dialog.
"""

import sys
import os

print('=' * 60)
print('DRAFT DAY DIALOG - VERIFICATION')
print('=' * 60)
print()

# Test 1: Import main dialog
print('Test 1: Importing DraftDayDialog...')
try:
    from draft_day_dialog import DraftDayDialog, NumericTableWidgetItem
    print('✓ DraftDayDialog class imported successfully')
    print('✓ NumericTableWidgetItem class imported successfully')
except Exception as e:
    print(f'✗ Import failed: {e}')
    sys.exit(1)

# Test 2: Import dependencies
print()
print('Test 2: Importing dependencies...')
try:
    from database_setup import setup_in_memory_database, verify_schema
    print('✓ database_setup imported')
except Exception as e:
    print(f'✗ database_setup import failed: {e}')
    sys.exit(1)

try:
    from mock_data_generator import populate_mock_data
    print('✓ mock_data_generator imported')
except Exception as e:
    print(f'✗ mock_data_generator import failed: {e}')
    sys.exit(1)

# Test 3: Verify PySide6
print()
print('Test 3: Verifying PySide6...')
try:
    from PySide6.QtWidgets import QApplication, QDialog
    from PySide6.QtCore import Qt, QTimer
    print('✓ PySide6 available')
except Exception as e:
    print(f'✗ PySide6 not available: {e}')
    print('  Run: pip install -r requirements-ui.txt')
    sys.exit(1)

# Test 4: Check team loader
print()
print('Test 4: Checking team loader integration...')
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
    from team_management.teams.team_loader import get_team_by_id

    test_team = get_team_by_id(22)
    if test_team:
        print(f'✓ Team loader working (Detroit Lions: {test_team.full_name})')
    else:
        print('✗ Team loader returned None')
        sys.exit(1)
except Exception as e:
    print(f'✗ Team loader failed: {e}')
    sys.exit(1)

# Test 5: Verify database schema
print()
print('Test 5: Verifying database schema...')
try:
    import sqlite3
    conn, cursor = setup_in_memory_database()
    if verify_schema(cursor):
        print('✓ Database schema verified')

        # Count tables
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        print(f'  {table_count} tables created')
    else:
        print('✗ Schema verification failed')
        sys.exit(1)
    conn.close()
except Exception as e:
    print(f'✗ Database schema test failed: {e}')
    sys.exit(1)

# Test 6: Mock data generation
print()
print('Test 6: Testing mock data generation...')
try:
    import sqlite3
    conn, cursor = setup_in_memory_database()
    counts = populate_mock_data(cursor, 'test_dynasty', 2026)
    conn.commit()

    print(f'✓ Mock data generated:')
    print(f'  - {counts["prospects"]} prospects')
    print(f'  - {counts["teams"]} teams')
    print(f'  - {counts["picks"]} draft picks')

    conn.close()
except Exception as e:
    print(f'✗ Mock data generation failed: {e}')
    sys.exit(1)

# Summary
print()
print('=' * 60)
print('ALL TESTS PASSED!')
print('=' * 60)
print()
print('The Draft Day Dialog is ready to use.')
print()
print('To launch the demo:')
print('  python launch_dialog.py')
print()
