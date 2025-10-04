"""
Salary Cap Demo Database Setup Script

This script initializes the salary cap demonstration database with the following:
1. Creates a dedicated demo database (cap_demo.db)
2. Runs the salary cap schema migration (002_salary_cap_schema.sql)
3. Initializes the 2025 NFL salary cap at $255,000,000
4. Sets up cap tracking for all 32 NFL teams for the 2025 season
5. Uses dynasty_id="cap_demo" for demo isolation

The script handles existing database scenarios gracefully, offering to
recreate or skip initialization as needed.

Usage:
    PYTHONPATH=src python demo/cap_calculator_demo/cap_demo_database_setup.py

Requirements:
    - src/database/migrations/002_salary_cap_schema.sql
    - src/salary_cap/cap_database_api.py
    - src/constants/team_ids.py
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import date

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from salary_cap.cap_database_api import CapDatabaseAPI
from constants.team_ids import TeamIDs


# Constants
DEMO_DB_PATH = Path(__file__).parent / "cap_demo.db"
DYNASTY_ID = "cap_demo"
SEASON_YEAR = 2025
SALARY_CAP_2025 = 255_000_000  # $255M for 2025 season


def database_exists() -> bool:
    """Check if demo database already exists."""
    return DEMO_DB_PATH.exists()


def prompt_user_for_recreation() -> bool:
    """
    Ask user if they want to recreate existing database.

    Returns:
        True if user wants to recreate, False to skip
    """
    while True:
        response = input("\nDatabase already exists. Recreate it? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'")


def delete_database() -> None:
    """Delete existing database file."""
    if DEMO_DB_PATH.exists():
        DEMO_DB_PATH.unlink()
        print(f"✓ Deleted existing database: {DEMO_DB_PATH}")


def create_database() -> None:
    """Create empty database file."""
    DEMO_DB_PATH.touch()
    print(f"✓ Created database: {DEMO_DB_PATH}")


def run_schema_migration() -> None:
    """
    Run salary cap schema migration.

    The CapDatabaseAPI automatically runs the migration if tables don't exist,
    so we just need to instantiate it with our database path.
    """
    print("\n=== Running Schema Migration ===")

    # Initialize API (this triggers schema creation)
    api = CapDatabaseAPI(database_path=str(DEMO_DB_PATH))

    print("✓ Schema initialized successfully")
    print("  - player_contracts table created")
    print("  - contract_year_details table created")
    print("  - team_salary_cap table created")
    print("  - franchise_tags table created")
    print("  - rfa_tenders table created")
    print("  - dead_money table created")
    print("  - cap_transactions table created")
    print("  - league_salary_cap_history table created")
    print("  - Views and indexes created")


def set_2025_salary_cap() -> None:
    """
    Set the 2025 salary cap in league_salary_cap_history.

    The migration pre-populates this table, but we verify/update it here.
    Also recalculates increase values based on 2024 cap.
    """
    print("\n=== Setting 2025 Salary Cap ===")

    with sqlite3.connect(str(DEMO_DB_PATH)) as conn:
        # Get 2024 cap for calculating increase
        cursor = conn.execute(
            "SELECT salary_cap_amount FROM league_salary_cap_history WHERE season = ?",
            (2024,)
        )
        cap_2024_row = cursor.fetchone()
        cap_2024 = cap_2024_row[0] if cap_2024_row else 255_400_000

        # Calculate increase and percentage
        increase = SALARY_CAP_2025 - cap_2024
        percentage = (increase / cap_2024) * 100 if cap_2024 > 0 else 0

        # Check if 2025 cap already exists from migration
        cursor = conn.execute(
            "SELECT salary_cap_amount FROM league_salary_cap_history WHERE season = ?",
            (SEASON_YEAR,)
        )
        existing_cap = cursor.fetchone()

        if existing_cap:
            current_amount = existing_cap[0]
            if current_amount == SALARY_CAP_2025:
                print(f"✓ 2025 salary cap already set: ${SALARY_CAP_2025:,}")
            else:
                # Update to our desired amount with recalculated values
                conn.execute('''
                    UPDATE league_salary_cap_history
                    SET salary_cap_amount = ?,
                        increase_from_previous = ?,
                        increase_percentage = ?
                    WHERE season = ?
                ''', (SALARY_CAP_2025, increase, round(percentage, 1), SEASON_YEAR))
                conn.commit()
                print(f"✓ Updated 2025 salary cap: ${current_amount:,} → ${SALARY_CAP_2025:,}")
                print(f"  Increase from 2024: ${increase:,} ({percentage:.1f}%)")
        else:
            # Insert if somehow missing
            conn.execute('''
                INSERT INTO league_salary_cap_history
                (season, salary_cap_amount, increase_from_previous, increase_percentage)
                VALUES (?, ?, ?, ?)
            ''', (SEASON_YEAR, SALARY_CAP_2025, increase, round(percentage, 1)))
            conn.commit()
            print(f"✓ Inserted 2025 salary cap: ${SALARY_CAP_2025:,}")
            print(f"  Increase from 2024: ${increase:,} ({percentage:.1f}%)")


def initialize_all_teams_cap() -> None:
    """
    Initialize salary cap tracking for all 32 NFL teams for 2025 season.

    Uses the CapDatabaseAPI.initialize_team_cap() method for each team.
    """
    print("\n=== Initializing Team Cap Summaries ===")
    print(f"Dynasty ID: {DYNASTY_ID}")
    print(f"Season: {SEASON_YEAR}")
    print(f"Teams: All 32 NFL teams")
    print()

    api = CapDatabaseAPI(database_path=str(DEMO_DB_PATH))

    # Get all team IDs (use set to deduplicate in case of method issues)
    all_team_ids = sorted(set(TeamIDs.get_all_team_ids()))

    initialized_count = 0
    for team_id in all_team_ids:
        try:
            api.initialize_team_cap(
                team_id=team_id,
                season=SEASON_YEAR,
                dynasty_id=DYNASTY_ID,
                salary_cap_limit=SALARY_CAP_2025,
                carryover_from_previous=0  # No carryover for demo
            )
            initialized_count += 1

            # Print progress every 8 teams (one division)
            if initialized_count % 8 == 0:
                print(f"  ✓ {initialized_count}/32 teams initialized...")
        except Exception as e:
            print(f"  ✗ Error initializing team {team_id}: {e}")

    print(f"\n✓ Successfully initialized {initialized_count}/32 teams")


def verify_setup() -> None:
    """Verify database setup was successful."""
    print("\n=== Verifying Setup ===")

    with sqlite3.connect(str(DEMO_DB_PATH)) as conn:
        # Check league cap
        cursor = conn.execute(
            "SELECT salary_cap_amount FROM league_salary_cap_history WHERE season = ?",
            (SEASON_YEAR,)
        )
        cap_amount = cursor.fetchone()
        if cap_amount:
            print(f"✓ League salary cap verified: ${cap_amount[0]:,}")
        else:
            print("✗ League salary cap not found!")

        # Check team caps
        cursor = conn.execute(
            "SELECT COUNT(*) FROM team_salary_cap WHERE season = ? AND dynasty_id = ?",
            (SEASON_YEAR, DYNASTY_ID)
        )
        team_count = cursor.fetchone()[0]
        print(f"✓ Team cap records: {team_count}/32")

        # Check a sample team
        cursor = conn.execute("""
            SELECT * FROM vw_team_cap_summary
            WHERE season = ? AND dynasty_id = ?
            LIMIT 1
        """, (SEASON_YEAR, DYNASTY_ID))
        sample = cursor.fetchone()
        if sample:
            print(f"✓ Sample team cap view working correctly")
        else:
            print("✗ Cap summary view returned no results!")


def main():
    """Main setup routine."""
    print("=" * 60)
    print("NFL SALARY CAP DEMO - DATABASE SETUP")
    print("=" * 60)
    print(f"\nDatabase: {DEMO_DB_PATH}")
    print(f"Season: {SEASON_YEAR}")
    print(f"Salary Cap: ${SALARY_CAP_2025:,}")
    print(f"Dynasty ID: {DYNASTY_ID}")
    print("=" * 60)

    # Check if database exists
    if database_exists():
        print(f"\n⚠️  Database already exists: {DEMO_DB_PATH}")
        if not prompt_user_for_recreation():
            print("\n✓ Skipping setup - using existing database")
            print("\nTo view the database, use:")
            print(f"  sqlite3 {DEMO_DB_PATH}")
            return

        # User wants to recreate
        delete_database()

    # Create fresh database
    print("\n=== Creating Database ===")
    create_database()

    # Run schema migration
    run_schema_migration()

    # Set 2025 salary cap
    set_2025_salary_cap()

    # Initialize all teams
    initialize_all_teams_cap()

    # Verify everything worked
    verify_setup()

    # Success message
    print("\n" + "=" * 60)
    print("✓ SETUP COMPLETE")
    print("=" * 60)
    print("\nThe demo database is ready to use!")
    print(f"\nDatabase location: {DEMO_DB_PATH}")
    print("\nNext steps:")
    print("  1. Run cap calculator demos")
    print("  2. View data with: sqlite3 demo/cap_calculator_demo/cap_demo.db")
    print("  3. Query teams: SELECT * FROM vw_team_cap_summary;")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
