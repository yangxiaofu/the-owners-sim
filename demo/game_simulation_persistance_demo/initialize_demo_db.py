#!/usr/bin/env python3
"""
Initialize Demo Database Schema

Creates the necessary tables in the demo database for persistence demonstration.
Copies schema from main database but uses isolated demo database.
"""

import sys
import sqlite3
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from database.connection import DatabaseConnection


def initialize_demo_database(demo_db_path: str):
    """
    Initialize demo database with necessary tables.

    Creates tables for:
    - games
    - player_game_stats
    - standings
    """
    print(f"Initializing demo database: {demo_db_path}")

    conn = sqlite3.connect(demo_db_path)
    cursor = conn.cursor()

    # Create games table
    print("  Creating games table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            game_type TEXT DEFAULT 'regular',
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            home_score INTEGER NOT NULL,
            away_score INTEGER NOT NULL,
            total_plays INTEGER,
            game_duration_minutes INTEGER,
            overtime_periods INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    # Create player_game_stats table
    print("  Creating player_game_stats table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_game_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            position TEXT NOT NULL,
            passing_yards INTEGER DEFAULT 0,
            passing_tds INTEGER DEFAULT 0,
            passing_completions INTEGER DEFAULT 0,
            passing_attempts INTEGER DEFAULT 0,
            rushing_yards INTEGER DEFAULT 0,
            rushing_tds INTEGER DEFAULT 0,
            rushing_attempts INTEGER DEFAULT 0,
            receiving_yards INTEGER DEFAULT 0,
            receiving_tds INTEGER DEFAULT 0,
            receptions INTEGER DEFAULT 0,
            targets INTEGER DEFAULT 0,
            tackles_total INTEGER DEFAULT 0,
            sacks REAL DEFAULT 0,
            interceptions INTEGER DEFAULT 0,
            field_goals_made INTEGER DEFAULT 0,
            field_goals_attempted INTEGER DEFAULT 0,
            extra_points_made INTEGER DEFAULT 0,
            extra_points_attempted INTEGER DEFAULT 0,
            offensive_snaps INTEGER DEFAULT 0,
            defensive_snaps INTEGER DEFAULT 0,
            total_snaps INTEGER DEFAULT 0,
            FOREIGN KEY (game_id) REFERENCES games(game_id)
        )
    """)

    # Create standings table
    print("  Creating standings table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            ties INTEGER DEFAULT 0,
            points_for INTEGER DEFAULT 0,
            points_against INTEGER DEFAULT 0,
            division_wins INTEGER DEFAULT 0,
            division_losses INTEGER DEFAULT 0,
            conference_wins INTEGER DEFAULT 0,
            conference_losses INTEGER DEFAULT 0,
            home_wins INTEGER DEFAULT 0,
            home_losses INTEGER DEFAULT 0,
            away_wins INTEGER DEFAULT 0,
            away_losses INTEGER DEFAULT 0,
            current_streak TEXT,
            division_rank INTEGER,
            UNIQUE(dynasty_id, team_id, season)
        )
    """)

    # Create indices
    print("  Creating indices...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_dynasty ON games(dynasty_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_week ON games(week)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_game ON player_game_stats(game_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_game_stats(player_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_standings_dynasty ON standings(dynasty_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_standings_team ON standings(team_id)")

    conn.commit()
    conn.close()

    print(f"✅ Demo database initialized successfully")


if __name__ == "__main__":
    demo_db_path = "demo/game_simulation_persistance_demo/data/demo_events.db"
    initialize_demo_database(demo_db_path)
