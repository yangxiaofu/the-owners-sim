#!/usr/bin/env python3
"""
Demo Initialization Script

Prepares the offseason demo database by:
1. Checking if offseason_demo.db exists
2. If not: creates database, generates mock data, schedules events
3. If yes: validates data integrity
4. Returns: ready-to-use database path

Usage:
    python demo/offseason_demo/initialize_demo.py
    python demo/offseason_demo/initialize_demo.py --reset
    python demo/offseason_demo/initialize_demo.py --database custom.db
"""

import os
import sys
import argparse
import sqlite3
from pathlib import Path
from typing import Dict, Optional

# Add src directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import demo modules
from mock_data_generator import generate_mock_data
from event_scheduler import schedule_offseason_events


class DemoInitializer:
    """
    Manages initialization and validation of the offseason demo database.
    """

    def __init__(
        self,
        database_path: str = "data/database/offseason_demo.db",
        dynasty_id: str = "ui_offseason_demo",
        season_year: int = 2024
    ):
        """
        Initialize demo initializer.

        Args:
            database_path: Path to demo database file
            dynasty_id: Dynasty identifier for data isolation
            season_year: NFL season year
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.season_year = season_year

        # Convert to absolute path
        if not os.path.isabs(self.database_path):
            self.database_path = os.path.join(project_root, self.database_path)

    def database_exists(self) -> bool:
        """Check if database file exists."""
        return os.path.exists(self.database_path)

    def create_database_directory(self) -> None:
        """Create database directory if it doesn't exist."""
        db_dir = os.path.dirname(self.database_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"✓ Created database directory: {db_dir}")

    def validate_database_schema(self) -> Dict[str, bool]:
        """
        Validate that database has required tables.

        Returns:
            Dictionary mapping table names to existence status
        """
        if not self.database_exists():
            return {}

        required_tables = [
            "players",
            "player_contracts",
            "team_salary_cap",
            "events",
            "team_rosters",
            "dynasty_state"
        ]

        validation_results = {}

        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()

            for table in required_tables:
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,)
                )
                exists = cursor.fetchone() is not None
                validation_results[table] = exists

            conn.close()

        except sqlite3.Error as e:
            print(f"✗ Database validation error: {e}")
            return {}

        return validation_results

    def validate_data_counts(self) -> Dict[str, int]:
        """
        Validate that database has expected data counts.

        Returns:
            Dictionary mapping data types to record counts
        """
        if not self.database_exists():
            return {}

        counts = {}

        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()

            # Count players for this dynasty
            cursor.execute(
                "SELECT COUNT(*) FROM players WHERE dynasty_id = ?",
                (self.dynasty_id,)
            )
            counts['players'] = cursor.fetchone()[0]

            # Count contracts for this dynasty
            cursor.execute(
                "SELECT COUNT(*) FROM player_contracts WHERE dynasty_id = ?",
                (self.dynasty_id,)
            )
            counts['contracts'] = cursor.fetchone()[0]

            # Count roster records for this dynasty
            cursor.execute(
                "SELECT COUNT(*) FROM team_rosters WHERE dynasty_id = ?",
                (self.dynasty_id,)
            )
            counts['rosters'] = cursor.fetchone()[0]

            # Count salary cap records for this dynasty
            cursor.execute(
                "SELECT COUNT(*) FROM team_salary_cap WHERE dynasty_id = ?",
                (self.dynasty_id,)
            )
            counts['salary_cap'] = cursor.fetchone()[0]

            # Count events for this dynasty
            cursor.execute(
                "SELECT COUNT(*) FROM events WHERE dynasty_id = ?",
                (self.dynasty_id,)
            )
            counts['events'] = cursor.fetchone()[0]

            conn.close()

        except sqlite3.Error as e:
            print(f"✗ Data count validation error: {e}")
            return {}

        return counts

    def is_database_valid(self) -> bool:
        """
        Check if database exists and has valid data.

        Returns:
            True if database is valid and ready to use
        """
        if not self.database_exists():
            return False

        # Validate schema
        schema = self.validate_database_schema()
        if not all(schema.values()):
            missing_tables = [table for table, exists in schema.items() if not exists]
            print(f"✗ Missing required tables: {missing_tables}")
            return False

        # Validate data counts
        counts = self.validate_data_counts()
        if not counts:
            print("✗ Failed to retrieve data counts")
            return False

        # Check expected counts
        if counts.get('players', 0) < 500:
            print(f"✗ Expected ~532+ players, found {counts.get('players', 0)}")
            return False

        if counts.get('contracts', 0) < 500:
            print(f"✗ Expected ~532+ contracts, found {counts.get('contracts', 0)}")
            return False

        if counts.get('rosters', 0) < 500:
            print(f"✗ Expected ~532+ roster records, found {counts.get('rosters', 0)}")
            return False

        if counts.get('salary_cap', 0) != 32:
            print(f"✗ Expected 32 salary cap records, found {counts.get('salary_cap', 0)}")
            return False

        if counts.get('events', 0) < 10:
            print(f"✗ Expected ~14 events, found {counts.get('events', 0)}")
            return False

        return True

    def delete_database(self) -> None:
        """Delete existing database file."""
        if self.database_exists():
            os.remove(self.database_path)
            print(f"✓ Deleted existing database: {self.database_path}")

    def generate_demo_data(self) -> Dict[str, int]:
        """
        Generate all mock data for the demo.

        Returns:
            Dictionary with counts of generated records
        """
        print("\n=== Generating Mock Data ===")
        print(f"Database: {self.database_path}")
        print(f"Dynasty: {self.dynasty_id}")
        print(f"Season: {self.season_year}")
        print()

        # Generate mock data
        counts = generate_mock_data(
            database_path=self.database_path,
            dynasty_id=self.dynasty_id,
            current_season=self.season_year + 1  # Offseason is after 2024 season
        )

        print(f"\n✓ Generated {counts['players']} players across 32 teams")
        print(f"✓ Generated {counts['contracts']} contracts")
        print(f"✓ Generated 32 salary cap records")

        return counts

    def initialize_dynasty_state(self) -> None:
        """
        Initialize dynasty_state table with demo starting conditions.

        Sets:
        - current_date: Feb 9, 2025 (Super Bowl - start of offseason)
        - current_phase: offseason
        - season: 2024 (the season that just finished)
        - current_week: NULL (not in regular season)
        """
        print("\n=== Initializing Dynasty State ===")

        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()

            # Check if dynasty state already exists
            cursor.execute(
                "SELECT COUNT(*) FROM dynasty_state WHERE dynasty_id = ?",
                (self.dynasty_id,)
            )
            exists = cursor.fetchone()[0] > 0

            if exists:
                # Update existing state (use quoted column names to avoid SQLite auto-fill)
                cursor.execute(
                    """
                    UPDATE dynasty_state
                    SET "current_date" = ?,
                        current_phase = ?,
                        season = ?,
                        current_week = NULL
                    WHERE dynasty_id = ?
                    """,
                    ("2025-02-09", "offseason", self.season_year, self.dynasty_id)
                )
                print(f"✓ Updated dynasty state for '{self.dynasty_id}'")
            else:
                # Insert new state (use quoted "current_date" to avoid SQLite auto-fill bug)
                cursor.execute(
                    """
                    INSERT INTO dynasty_state (dynasty_id, season, "current_date", current_phase, current_week)
                    VALUES (?, ?, ?, ?, NULL)
                    """,
                    (self.dynasty_id, self.season_year, "2025-02-09", "offseason")
                )
                print(f"✓ Created dynasty state for '{self.dynasty_id}'")

            conn.commit()
            conn.close()

            print(f"  Date: February 9, 2025 (Super Bowl)")
            print(f"  Phase: Offseason")
            print(f"  Season: {self.season_year}")

        except sqlite3.Error as e:
            print(f"✗ Failed to initialize dynasty state: {e}")
            raise

    def schedule_demo_events(self) -> int:
        """
        Schedule all offseason events.

        Returns:
            Number of events scheduled
        """
        print("\n=== Scheduling Offseason Events ===")

        event_ids = schedule_offseason_events(
            database_path=self.database_path,
            dynasty_id=self.dynasty_id,
            season_year=self.season_year
        )

        print(f"\n✓ Scheduled {len(event_ids)} offseason events")

        return len(event_ids)

    def initialize(self, force_reset: bool = False) -> str:
        """
        Initialize the demo database.

        Args:
            force_reset: If True, delete and recreate database

        Returns:
            Path to initialized database
        """
        print("=" * 80)
        print("OFFSEASON DEMO INITIALIZATION")
        print("=" * 80)

        # Check if reset requested
        if force_reset and self.database_exists():
            print("\n⚠️  Reset requested - deleting existing database")
            self.delete_database()

        # Check if database already valid
        if self.database_exists() and self.is_database_valid():
            print("\n✓ Database already exists and is valid")
            print(f"  Path: {self.database_path}")

            # Show current data counts
            counts = self.validate_data_counts()
            print(f"\n  Players: {counts.get('players', 0)}")
            print(f"  Contracts: {counts.get('contracts', 0)}")
            print(f"  Roster Records: {counts.get('rosters', 0)}")
            print(f"  Salary Cap Records: {counts.get('salary_cap', 0)}")
            print(f"  Events: {counts.get('events', 0)}")

            print("\n✓ Demo database is ready to use")
            print(f"  Run with --reset to recreate database")
            return self.database_path

        # Database doesn't exist or is invalid - create it
        print("\n📦 Creating new demo database...")

        # Create database directory
        self.create_database_directory()

        # Generate mock data
        data_counts = self.generate_demo_data()

        # Initialize dynasty state (current date, phase, season)
        self.initialize_dynasty_state()

        # Schedule events
        event_count = self.schedule_demo_events()

        # Validate final database
        print("\n=== Validating Database ===")
        if self.is_database_valid():
            print("✓ Database validation successful")

            counts = self.validate_data_counts()
            print(f"\nFinal Counts:")
            print(f"  Players: {counts.get('players', 0)}")
            print(f"  Contracts: {counts.get('contracts', 0)}")
            print(f"  Roster Records: {counts.get('rosters', 0)}")
            print(f"  Salary Cap Records: {counts.get('salary_cap', 0)}")
            print(f"  Events: {counts.get('events', 0)}")

            print("\n" + "=" * 80)
            print("✓ DEMO INITIALIZATION COMPLETE")
            print("=" * 80)
            print(f"\nDatabase Path: {self.database_path}")
            print(f"Dynasty ID: {self.dynasty_id}")
            print(f"Season Year: {self.season_year}")
            print("\nYou can now run: python demo/offseason_demo/main_offseason_demo.py")

            return self.database_path
        else:
            print("✗ Database validation failed")
            raise RuntimeError("Failed to create valid demo database")


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Initialize offseason demo database"
    )
    parser.add_argument(
        "--database",
        default="data/database/offseason_demo.db",
        help="Path to demo database file"
    )
    parser.add_argument(
        "--dynasty",
        default="ui_offseason_demo",
        help="Dynasty ID for data isolation"
    )
    parser.add_argument(
        "--season",
        type=int,
        default=2024,
        help="NFL season year"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate database"
    )

    args = parser.parse_args()

    # Create initializer
    initializer = DemoInitializer(
        database_path=args.database,
        dynasty_id=args.dynasty,
        season_year=args.season
    )

    # Initialize database
    try:
        db_path = initializer.initialize(force_reset=args.reset)
        print(f"\n✓ Success! Database ready at: {db_path}")
        return 0
    except Exception as e:
        print(f"\n✗ Initialization failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
