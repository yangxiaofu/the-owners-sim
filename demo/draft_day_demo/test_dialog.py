"""
Test Script for Draft Day Dialog

Quick test to verify the dialog works with mock data.
"""

import sys
from PySide6.QtWidgets import QApplication
from database_setup import setup_in_memory_database, verify_schema
from mock_data_generator import populate_mock_data
from draft_day_dialog import DraftDayDialog


def main():
    """Run the draft day dialog test."""
    print("Setting up mock database...")

    # Set up database
    conn, cursor = setup_in_memory_database()

    # Verify schema
    if not verify_schema(cursor):
        print("Schema verification failed!")
        return

    # Populate mock data
    dynasty_id = "test_dynasty"
    season_year = 2026
    user_team_id = 22  # Detroit Lions

    counts = populate_mock_data(cursor, dynasty_id, season_year)
    conn.commit()

    print(f"Mock data created:")
    print(f"  - {counts['prospects']} prospects")
    print(f"  - {counts['teams']} teams")
    print(f"  - {counts['picks']} draft picks")
    print(f"\nUser team: Detroit Lions (ID: {user_team_id})")

    # Close connection (dialog will reopen)
    conn.close()

    # Create Qt application
    app = QApplication(sys.argv)

    # Create and show dialog
    dialog = DraftDayDialog(
        db_path=":memory:",  # Note: This won't work - need to use same connection
        dynasty_id=dynasty_id,
        season=season_year,
        user_team_id=user_team_id
    )

    print("\nLaunching Draft Day Dialog...")
    print("Note: In-memory database won't persist between connections.")
    print("For full demo, use draft_day_demo.py with file-based database.\n")

    dialog.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
