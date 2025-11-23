"""
Setup Draft Demo Database

Creates a persistent SQLite database with draft prospects, draft order,
and mock team data for the standalone draft day demo.
"""

import sqlite3
from pathlib import Path
from typing import Optional


def setup_draft_demo_database(db_path: Optional[str] = None) -> str:
    """
    Set up persistent draft demo database.
    
    Args:
        db_path: Optional custom database path. If None, uses default location.
        
    Returns:
        Dynasty ID string
    """
    if db_path is None:
        demo_dir = Path(__file__).parent
        db_path = str(demo_dir / "draft_demo.db")
    
    # Import mock data generator and database setup
    from demo.draft_day_demo.database_setup import setup_in_memory_database
    from demo.draft_day_demo.mock_data_generator import populate_mock_data
    
    dynasty_id = "draft_demo_dynasty"
    season_year = 2025
    
    # Create database connection (file-based)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create all tables (reuse schema from in-memory setup)
    # This is a bit hacky but avoids code duplication
    temp_conn, temp_cursor = setup_in_memory_database()
    
    # Get schema from temp database
    temp_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'")
    table_schemas = temp_cursor.fetchall()
    
    # Create tables in persistent database
    for (schema,) in table_schemas:
        if schema:  # Skip None values
            cursor.execute(schema)
    
    temp_conn.close()
    
    # Populate with mock data
    populate_mock_data(cursor, dynasty_id, season_year)
    conn.commit()
    
    print(f"✅ Database created: {db_path}")
    print(f"✅ Dynasty ID: {dynasty_id}")
    print(f"✅ Season Year: {season_year}")
    
    conn.close()
    
    return dynasty_id


if __name__ == "__main__":
    # Allow running this script directly to create database
    setup_draft_demo_database()
