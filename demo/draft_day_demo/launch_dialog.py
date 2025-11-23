"""
Launch Draft Day Dialog - Proper Demo with File Database

Creates a temporary file-based database and launches the interactive dialog.
"""

import sys
import os
import tempfile
import sqlite3
from PySide6.QtWidgets import QApplication
from database_setup import setup_in_memory_database, verify_schema
from mock_data_generator import populate_mock_data
from draft_day_dialog import DraftDayDialog


def create_temp_database() -> str:
    """
    Create temporary file-based database with mock data.

    Returns:
        Path to temporary database file
    """
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    db_path = os.path.join(temp_dir, "draft_day_demo.db")

    # Remove existing file if it exists
    if os.path.exists(db_path):
        os.remove(db_path)

    print(f"Creating database at: {db_path}")

    # Create and populate database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create schema
    print("Creating database schema...")
    create_schema(cursor)
    conn.commit()

    # Verify schema
    if not verify_schema(cursor):
        print("Schema verification failed!")
        conn.close()
        return None

    # Populate mock data
    dynasty_id = "draft_demo_dynasty"
    season_year = 2026

    print("Generating mock data...")
    counts = populate_mock_data(cursor, dynasty_id, season_year)
    conn.commit()

    print(f"\nMock data created:")
    print(f"  - {counts['prospects']} prospects")
    print(f"  - {counts['teams']} teams")
    print(f"  - {counts['picks']} draft picks")

    conn.close()

    return db_path


def create_schema(cursor: sqlite3.Cursor):
    """
    Create database schema (copied from database_setup for file-based DB).

    Args:
        cursor: SQLite cursor
    """
    # Create dynasties table
    cursor.execute("""
        CREATE TABLE dynasties (
            dynasty_id TEXT PRIMARY KEY,
            dynasty_name TEXT NOT NULL,
            user_team_id INTEGER,
            current_season INTEGER NOT NULL,
            current_week INTEGER,
            current_day INTEGER,
            created_at TEXT NOT NULL,
            last_simulated TEXT,
            total_seasons_simulated INTEGER DEFAULT 0,
            playoff_appearances INTEGER DEFAULT 0,
            championships_won INTEGER DEFAULT 0,
            settings_json TEXT,
            metadata_json TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)

    # Create draft_classes table
    cursor.execute("""
        CREATE TABLE draft_classes (
            class_id TEXT PRIMARY KEY,
            season_year INTEGER NOT NULL,
            dynasty_id TEXT NOT NULL,
            total_prospects INTEGER DEFAULT 0,
            generated_at TEXT NOT NULL,
            metadata_json TEXT,
            is_finalized INTEGER DEFAULT 0
        )
    """)

    # Create draft_prospects table
    cursor.execute("""
        CREATE TABLE draft_prospects (
            prospect_id TEXT PRIMARY KEY,
            class_id TEXT NOT NULL,
            dynasty_id TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            position TEXT NOT NULL,
            college TEXT,
            age INTEGER,
            height_inches INTEGER,
            weight_lbs INTEGER,
            overall_rating INTEGER,
            potential_rating INTEGER,
            speed INTEGER,
            strength INTEGER,
            awareness INTEGER,
            agility INTEGER,
            stamina INTEGER,
            injury_prone INTEGER,
            ceiling INTEGER,
            floor INTEGER,
            archetype TEXT,
            draft_grade TEXT,
            is_drafted INTEGER DEFAULT 0,
            drafted_by_team_id INTEGER,
            drafted_round INTEGER,
            drafted_pick INTEGER,
            metadata_json TEXT,
            FOREIGN KEY (class_id) REFERENCES draft_classes(class_id)
        )
    """)

    # Create draft_order table
    cursor.execute("""
        CREATE TABLE draft_order (
            pick_id TEXT PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            season_year INTEGER NOT NULL,
            round_number INTEGER NOT NULL,
            pick_in_round INTEGER NOT NULL,
            overall_pick INTEGER NOT NULL,
            original_team_id INTEGER NOT NULL,
            current_team_id INTEGER NOT NULL,
            prospect_id TEXT,
            player_id TEXT,
            is_compensatory INTEGER DEFAULT 0,
            trade_details_json TEXT,
            pick_made_at TEXT,
            time_on_clock_seconds INTEGER,
            was_traded INTEGER DEFAULT 0,
            metadata_json TEXT
        )
    """)

    # Create players table (simplified for demo)
    cursor.execute("""
        CREATE TABLE players (
            player_id TEXT PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            position TEXT NOT NULL,
            team_id INTEGER,
            age INTEGER,
            overall_rating INTEGER,
            potential_rating INTEGER,
            contract_years INTEGER,
            contract_value INTEGER,
            is_rookie INTEGER DEFAULT 0,
            draft_year INTEGER,
            draft_round INTEGER,
            draft_pick INTEGER,
            metadata_json TEXT
        )
    """)

    # Create team_rosters table
    cursor.execute("""
        CREATE TABLE team_rosters (
            roster_entry_id TEXT PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            season_year INTEGER NOT NULL,
            depth_position INTEGER,
            added_date TEXT,
            FOREIGN KEY (player_id) REFERENCES players(player_id)
        )
    """)

    # Create gm_personalities table (demo-specific)
    cursor.execute("""
        CREATE TABLE gm_personalities (
            team_id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            archetype TEXT NOT NULL,
            risk_tolerance REAL DEFAULT 0.5,
            win_now_mentality REAL DEFAULT 0.5,
            values_potential REAL DEFAULT 0.5,
            values_need REAL DEFAULT 0.5,
            trade_aggressiveness REAL DEFAULT 0.5,
            loyalty REAL DEFAULT 0.5,
            analytics_driven REAL DEFAULT 0.5,
            player_development_focus REAL DEFAULT 0.5,
            draft_bpa_tendency REAL DEFAULT 0.5,
            free_agency_activity REAL DEFAULT 0.5,
            veteran_preference REAL DEFAULT 0.5,
            salary_cap_flexibility REAL DEFAULT 0.5,
            rebuilding_patience REAL DEFAULT 0.5
        )
    """)

    # Create team_needs table (demo-specific)
    cursor.execute("""
        CREATE TABLE team_needs (
            need_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            dynasty_id TEXT NOT NULL,
            position TEXT NOT NULL,
            priority INTEGER NOT NULL,
            urgency_level TEXT
        )
    """)


def main():
    """Launch the draft day dialog."""
    print("=" * 60)
    print("DRAFT DAY DIALOG DEMO")
    print("=" * 60)
    print()

    # Create database
    db_path = create_temp_database()
    if not db_path:
        print("Failed to create database!")
        return

    # Configuration
    dynasty_id = "draft_demo_dynasty"
    season_year = 2026
    user_team_id = 22  # Detroit Lions

    print(f"\nUser team: Detroit Lions (ID: {user_team_id})")
    print(f"Dynasty: {dynasty_id}")
    print(f"Season: {season_year}")
    print()

    # Create Qt application
    app = QApplication(sys.argv)

    # Create and show dialog
    print("Launching Draft Day Dialog...")
    print()

    dialog = DraftDayDialog(
        db_path=db_path,
        dynasty_id=dynasty_id,
        season=season_year,
        user_team_id=user_team_id
    )

    dialog.show()

    # Run application
    exit_code = app.exec()

    # Cleanup
    print(f"\nCleaning up temporary database: {db_path}")
    try:
        os.remove(db_path)
    except Exception as e:
        print(f"Warning: Could not remove temporary database: {e}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
