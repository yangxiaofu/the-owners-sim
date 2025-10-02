#!/usr/bin/env python3
"""
Initialize Season Database

Creates the necessary database schema for the interactive season simulator.
Sets up tables for games, player stats, standings, and events.
"""

import sys
import sqlite3
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def initialize_season_database(db_path: str):
    """
    Initialize season database with all required tables.

    Creates:
    - events table (for scheduled games)
    - games table (for game results)
    - player_game_stats table (for player statistics)
    - standings table (for team records)

    Args:
        db_path: Path to database file
    """
    print(f"Initializing season database: {db_path}")
    print("=" * 80)

    # Ensure directory exists
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create events table
    print("  Creating events table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            game_id TEXT NOT NULL,
            data TEXT NOT NULL
        )
    """)

    # Create indices for events
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_id ON events(game_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)")

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

    # Create indices for games
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_dynasty ON games(dynasty_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_week ON games(week)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_season ON games(season)")

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

    # Create indices for player_game_stats
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_game ON player_game_stats(game_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_game_stats(player_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_dynasty ON player_game_stats(dynasty_id)")

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

    # Create indices for standings
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_standings_dynasty ON standings(dynasty_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_standings_team ON standings(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_standings_season ON standings(season)")

    # Commit and close
    conn.commit()
    conn.close()

    print("=" * 80)
    print(f"✅ Database initialized successfully: {db_path}")
    print()
    print("Tables created:")
    print("  - events (for scheduled games)")
    print("  - games (for game results)")
    print("  - player_game_stats (for player statistics)")
    print("  - standings (for team records)")
    print()
    print("Indices created for optimal query performance")


def main():
    """Main entry point."""
    # Default database path
    default_path = "demo/interactive_season_sim/data/season_2024.db"

    # Allow custom path from command line
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = default_path

    try:
        initialize_season_database(db_path)
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
