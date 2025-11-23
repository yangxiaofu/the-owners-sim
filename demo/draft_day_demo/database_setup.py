"""
Database Setup for Draft Day Demo

Creates in-memory SQLite database with all required tables for draft simulation.
"""

import sqlite3
from typing import Tuple


def setup_in_memory_database() -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
    """
    Create in-memory SQLite database with all required tables.

    Returns:
        Tuple of (connection, cursor) for database operations
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

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

    conn.commit()

    return conn, cursor


def verify_schema(cursor: sqlite3.Cursor) -> bool:
    """
    Verify all required tables exist.

    Args:
        cursor: SQLite cursor

    Returns:
        True if all tables exist, False otherwise
    """
    required_tables = [
        'dynasties',
        'draft_classes',
        'draft_prospects',
        'draft_order',
        'players',
        'team_rosters',
        'gm_personalities',
        'team_needs'
    ]

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cursor.fetchall()}

    missing_tables = set(required_tables) - existing_tables

    if missing_tables:
        print(f"Missing tables: {missing_tables}")
        return False

    return True
