#!/usr/bin/env python3
"""
Seed Season Recap Data - Populate database with test data for Season Recap view.

Creates mock data matching the --mock mode in season_recap_demo.py:
- Dynasty: test_recap_2025, Bills (team_id=1), Season 2025
- Super Bowl: Bills 34, Rams 28 (week 22, playoffs)
- SB MVP: James Cook (RB, Bills)
- League MVP: Josh Allen (QB, Bills)
- Retirements: Aaron Rodgers (notable), DeAndre Hopkins (notable), 2 others

Usage:
    PYTHONPATH=src python demos/seed_season_recap_data.py

    # Then run the demo in database mode
    python demos/season_recap_demo.py
"""

import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Database path
DB_PATH = project_root / "data" / "database" / "game_cycle" / "game_cycle.db"
SCHEMA_PATH = project_root / "src" / "game_cycle" / "database" / "full_schema.sql"

# Test dynasty ID
DYNASTY_ID = "test_recap_2025"
SEASON = 2025


def ensure_database_exists():
    """Create database directory if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def initialize_schema(conn: sqlite3.Connection):
    """Initialize database schema from full_schema.sql."""
    print("  Initializing schema...")

    if not SCHEMA_PATH.exists():
        print(f"    Warning: Schema file not found at {SCHEMA_PATH}")
        print("    Using minimal schema...")
        _create_minimal_schema(conn)
        return

    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)
    conn.commit()
    print("    Schema initialized from full_schema.sql")


def _create_minimal_schema(conn: sqlite3.Connection):
    """Create minimal schema for Season Recap testing."""
    conn.executescript("""
        -- Dynasties
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            dynasty_name TEXT NOT NULL,
            owner_name TEXT,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL DEFAULT 2025,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Players
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            team_id INTEGER,
            positions TEXT,
            years_pro INTEGER DEFAULT 1,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, player_id)
        );

        -- Games
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            season_type TEXT NOT NULL DEFAULT 'regular_season',
            game_type TEXT DEFAULT 'regular',
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            home_score INTEGER NOT NULL DEFAULT 0,
            away_score INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        );

        -- Award Definitions
        CREATE TABLE IF NOT EXISTS award_definitions (
            award_id TEXT PRIMARY KEY,
            award_name TEXT NOT NULL,
            award_type TEXT,
            category TEXT,
            description TEXT
        );

        -- Award Winners
        CREATE TABLE IF NOT EXISTS award_winners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            award_id TEXT NOT NULL,
            player_id INTEGER,
            team_id INTEGER NOT NULL,
            vote_points INTEGER,
            vote_share REAL,
            rank INTEGER,
            is_winner INTEGER DEFAULT 0,
            voting_date DATE,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        );

        -- Retired Players
        CREATE TABLE IF NOT EXISTS retired_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            retirement_season INTEGER NOT NULL,
            retirement_reason TEXT NOT NULL,
            final_team_id INTEGER NOT NULL,
            years_played INTEGER NOT NULL,
            age_at_retirement INTEGER NOT NULL,
            hall_of_fame_eligible_season INTEGER,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, player_id)
        );

        -- Career Summaries
        CREATE TABLE IF NOT EXISTS career_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            position TEXT NOT NULL,
            seasons_played INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            pass_yards INTEGER DEFAULT 0,
            pass_tds INTEGER DEFAULT 0,
            rush_yards INTEGER DEFAULT 0,
            rush_tds INTEGER DEFAULT 0,
            rec_yards INTEGER DEFAULT 0,
            rec_tds INTEGER DEFAULT 0,
            tackles INTEGER DEFAULT 0,
            sacks REAL DEFAULT 0,
            interceptions INTEGER DEFAULT 0,
            pro_bowls INTEGER DEFAULT 0,
            all_pro_first_team INTEGER DEFAULT 0,
            all_pro_second_team INTEGER DEFAULT 0,
            mvp_awards INTEGER DEFAULT 0,
            super_bowl_wins INTEGER DEFAULT 0,
            super_bowl_mvps INTEGER DEFAULT 0,
            hall_of_fame_score INTEGER DEFAULT 0,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, player_id)
        );
    """)
    conn.commit()


def clear_existing_test_data(conn: sqlite3.Connection):
    """Remove existing test dynasty data."""
    print("  Clearing existing test data...")

    # Enable foreign keys for CASCADE to work
    conn.execute("PRAGMA foreign_keys = ON")

    # Manually delete from tables that reference dynasty
    # (in case foreign keys were disabled when data was inserted)
    tables_to_clear = [
        "player_game_stats",
        "player_season_grades",
        "standings",
        "players",
        "games",
        "award_winners",
        "super_bowl_mvp",
        "career_summaries",
        "retired_players",
    ]

    for table in tables_to_clear:
        try:
            conn.execute(f"DELETE FROM {table} WHERE dynasty_id = ?", (DYNASTY_ID,))
        except Exception:
            pass  # Table might not exist

    # Delete dynasty
    conn.execute("DELETE FROM dynasties WHERE dynasty_id = ?", (DYNASTY_ID,))
    conn.commit()
    print(f"    Cleared dynasty '{DYNASTY_ID}'")


def insert_teams(conn: sqlite3.Connection):
    """Insert teams from existing teams.json data."""
    print("  Inserting teams...")

    teams_json_path = Path(__file__).parent.parent / "src" / "data" / "teams.json"
    with open(teams_json_path) as f:
        teams_data = json.load(f)

    count = 0
    for team in teams_data["teams"].values():
        try:
            conn.execute("""
                INSERT OR IGNORE INTO teams (team_id, name, abbreviation, conference, division)
                VALUES (?, ?, ?, ?, ?)
            """, (team["team_id"], team["full_name"], team["abbreviation"], team["conference"], team["division"]))
            count += 1
        except Exception:
            pass  # Team already exists

    conn.commit()
    print(f"    Ensured {count} teams exist")


def insert_dynasty(conn: sqlite3.Connection):
    """Insert test dynasty."""
    print("  Inserting dynasty...")

    conn.execute("""
        INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id, season_year)
        VALUES (?, ?, ?, ?, ?)
    """, (DYNASTY_ID, "Season Recap Test", "Test Owner", 1, SEASON))

    conn.commit()
    print(f"    Created dynasty: {DYNASTY_ID} (Bills, Season {SEASON})")


def insert_players(conn: sqlite3.Connection):
    """Insert test players from JSON config."""
    print("  Inserting players...")

    players_json_path = Path(__file__).parent / "test_data" / "season_recap_players.json"
    with open(players_json_path) as f:
        data = json.load(f)

    position_templates = data["position_templates"]
    players_data = data["players"]

    count = 0
    for player in players_data:
        # Get position template (use first position if list, handle LT/RT/LG/RG mapping to OT/OG)
        pos = player["position"]
        template_pos = pos
        if pos in ["LT", "RT"]:
            template_pos = "OT"
        elif pos in ["LG", "RG"]:
            template_pos = "OG"
        elif pos in ["FS", "SS"]:
            template_pos = "S"
        elif pos in ["LOLB", "ROLB", "MLB"]:
            template_pos = "LB"
        elif pos == "KR":
            template_pos = "WR"  # Return specialists use WR template

        attrs = json.dumps(position_templates.get(template_pos, position_templates.get("QB")))
        positions_json = json.dumps([pos])

        conn.execute("""
            INSERT OR REPLACE INTO players
            (dynasty_id, player_id, first_name, last_name, number, team_id, positions, attributes, years_pro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            DYNASTY_ID,
            player["id"],
            player["first_name"],
            player["last_name"],
            player["jersey_number"],
            player["team_id"],
            positions_json,
            attrs,
            player["years_pro"]
        ))
        count += 1

    conn.commit()
    print(f"    Inserted {count} players")


def insert_standings(conn: sqlite3.Connection):
    """Insert team standings for award calculations."""
    print("  Inserting standings...")

    # Standings with playoff seed for team success factor
    # (dynasty_id, team_id, season, season_type, wins, losses, playoff_seed, made_playoffs)
    standings = [
        # AFC East
        (DYNASTY_ID, 1, SEASON, "regular_season", 13, 4, 1, 1),   # Bills - #1 seed, SB winner
        (DYNASTY_ID, 2, SEASON, "regular_season", 10, 7, 5, 1),   # Dolphins
        (DYNASTY_ID, 3, SEASON, "regular_season", 4, 13, None, 0), # Patriots
        (DYNASTY_ID, 4, SEASON, "regular_season", 7, 10, None, 0), # Jets
        # AFC North
        (DYNASTY_ID, 5, SEASON, "regular_season", 12, 5, 2, 1),   # Ravens
        (DYNASTY_ID, 6, SEASON, "regular_season", 10, 7, 6, 1),   # Bengals
        (DYNASTY_ID, 7, SEASON, "regular_season", 8, 9, None, 0), # Browns
        (DYNASTY_ID, 8, SEASON, "regular_season", 9, 8, 7, 1),    # Steelers
        # AFC South
        (DYNASTY_ID, 9, SEASON, "regular_season", 9, 8, None, 0), # Texans
        (DYNASTY_ID, 10, SEASON, "regular_season", 7, 10, None, 0), # Colts
        (DYNASTY_ID, 11, SEASON, "regular_season", 4, 13, None, 0), # Jaguars
        (DYNASTY_ID, 12, SEASON, "regular_season", 5, 12, None, 0), # Titans
        # AFC West
        (DYNASTY_ID, 13, SEASON, "regular_season", 8, 9, None, 0), # Broncos
        (DYNASTY_ID, 14, SEASON, "regular_season", 11, 6, 4, 1),  # Chiefs
        (DYNASTY_ID, 15, SEASON, "regular_season", 6, 11, None, 0), # Raiders
        (DYNASTY_ID, 16, SEASON, "regular_season", 9, 8, None, 0), # Chargers
        # NFC East
        (DYNASTY_ID, 17, SEASON, "regular_season", 10, 7, 5, 1),  # Cowboys
        (DYNASTY_ID, 18, SEASON, "regular_season", 6, 11, None, 0), # Giants
        (DYNASTY_ID, 19, SEASON, "regular_season", 12, 5, 2, 1),  # Eagles
        (DYNASTY_ID, 20, SEASON, "regular_season", 7, 10, None, 0), # Commanders
        # NFC North
        (DYNASTY_ID, 21, SEASON, "regular_season", 9, 8, None, 0), # Bears
        (DYNASTY_ID, 22, SEASON, "regular_season", 11, 6, 3, 1),  # Lions
        (DYNASTY_ID, 23, SEASON, "regular_season", 8, 9, None, 0), # Packers
        (DYNASTY_ID, 24, SEASON, "regular_season", 10, 7, 6, 1),  # Vikings
        # NFC South
        (DYNASTY_ID, 25, SEASON, "regular_season", 8, 9, None, 0), # Falcons
        (DYNASTY_ID, 26, SEASON, "regular_season", 4, 13, None, 0), # Panthers
        (DYNASTY_ID, 27, SEASON, "regular_season", 7, 10, None, 0), # Saints
        (DYNASTY_ID, 28, SEASON, "regular_season", 9, 8, 7, 1),   # Buccaneers
        # NFC West
        (DYNASTY_ID, 29, SEASON, "regular_season", 7, 10, None, 0), # Cardinals
        (DYNASTY_ID, 30, SEASON, "regular_season", 9, 8, None, 0), # Rams (SB loser)
        (DYNASTY_ID, 31, SEASON, "regular_season", 11, 6, 4, 1),  # 49ers
        (DYNASTY_ID, 32, SEASON, "regular_season", 8, 9, None, 0), # Seahawks
    ]

    conn.executemany("""
        INSERT INTO standings (dynasty_id, team_id, season, season_type, wins, losses, playoff_seed, made_playoffs)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, standings)

    conn.commit()
    print(f"    Inserted standings for {len(standings)} teams")


def insert_season_games(conn: sqlite3.Connection):
    """Insert fake regular season games for player stats references."""
    print("  Inserting season games...")

    # Create 17 game placeholders per team (we only need game_ids for stats)
    games = []
    for week in range(1, 18):
        # Just create games for teams with award candidates
        game_id = f"GAME_{SEASON}_W{week:02d}_{DYNASTY_ID}"
        games.append((
            game_id, DYNASTY_ID, SEASON, week, "regular_season", "regular",
            1, 2, 27, 24  # Placeholder scores
        ))

    conn.executemany("""
        INSERT INTO games (game_id, dynasty_id, season, week, season_type, game_type,
                          home_team_id, away_team_id, home_score, away_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, games)

    conn.commit()
    print(f"    Inserted {len(games)} regular season games")


def insert_player_stats(conn: sqlite3.Connection):
    """Insert player season stats for awards calculation."""
    print("  Inserting player stats...")

    # We'll insert aggregate season stats (one row per player, using a game_id that exists in games table)
    # Format: (dynasty_id, game_id, season_type, player_id, player_name, team_id, position, ...stats...)
    # Use Week 1 game_id since it exists in games table (required for JOIN in stats aggregation)
    game_id = f"GAME_{SEASON}_W01_{DYNASTY_ID}"  # Must match an existing game for stats JOIN

    stats = [
        # QBs - MVP candidates
        # (dynasty_id, game_id, season_type, player_id, player_name, team_id, position,
        #  passing_yards, passing_tds, passing_attempts, passing_completions, passing_interceptions, passing_rating,
        #  rushing_yards, rushing_tds, rushing_attempts)
        (DYNASTY_ID, game_id, "regular_season", "10001", "Josh Allen", 1, "QB",
         4689, 38, 580, 385, 8, 108.5, 524, 7, 90),  # MVP frontrunner
        (DYNASTY_ID, game_id, "regular_season", "10003", "Lamar Jackson", 5, "QB",
         3900, 32, 490, 330, 7, 105.2, 821, 5, 135),  # Dual threat
        (DYNASTY_ID, game_id, "regular_season", "10004", "Jalen Hurts", 19, "QB",
         3650, 28, 480, 310, 10, 98.5, 605, 12, 120),
        (DYNASTY_ID, game_id, "regular_season", "10005", "Patrick Mahomes", 14, "QB",
         4200, 30, 550, 365, 11, 101.3, 320, 2, 55),

        # RBs - OPOY candidates
        (DYNASTY_ID, game_id, "regular_season", "10002", "James Cook", 1, "RB",
         0, 0, 0, 0, 0, 0.0, 1420, 13, 285),
        (DYNASTY_ID, game_id, "regular_season", "10010", "Saquon Barkley", 19, "RB",
         0, 0, 0, 0, 0, 0.0, 2005, 13, 345),  # OPOY frontrunner - 2000 yard season
        (DYNASTY_ID, game_id, "regular_season", "10011", "Derrick Henry", 5, "RB",
         0, 0, 0, 0, 0, 0.0, 1780, 16, 325),
        (DYNASTY_ID, game_id, "regular_season", "10012", "Bijan Robinson", 25, "RB",
         0, 0, 0, 0, 0, 0.0, 1350, 10, 275),

        # WRs - OPOY candidates
        (DYNASTY_ID, game_id, "regular_season", "10020", "Ja'Marr Chase", 6, "WR",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),  # Receiving stats below
        (DYNASTY_ID, game_id, "regular_season", "10021", "Tyreek Hill", 2, "WR",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10022", "CeeDee Lamb", 17, "WR",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10023", "Amon-Ra St. Brown", 22, "WR",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10024", "Davante Adams", 4, "WR",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10025", "A.J. Brown", 19, "WR",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10026", "Justin Jefferson", 24, "WR",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10027", "Stefon Diggs", 9, "WR",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),

        # TEs
        (DYNASTY_ID, game_id, "regular_season", "10110", "Travis Kelce", 14, "TE",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10111", "George Kittle", 31, "TE",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10112", "Mark Andrews", 5, "TE",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10113", "T.J. Hockenson", 24, "TE",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10114", "Dalton Kincaid", 1, "TE",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10115", "Sam LaPorta", 22, "TE",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10116", "David Njoku", 7, "TE",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10117", "Dallas Goedert", 19, "TE",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),

        # Rookies - OROY
        (DYNASTY_ID, game_id, "regular_season", "10060", "Caleb Williams", 21, "QB",
         3425, 25, 520, 325, 12, 92.1, 280, 3, 55),
        (DYNASTY_ID, game_id, "regular_season", "10061", "Marvin Harrison Jr", 29, "WR",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),
        (DYNASTY_ID, game_id, "regular_season", "10062", "Malik Nabers", 18, "WR",
         0, 0, 0, 0, 0, 0.0, 0, 0, 0),

        # CPOY
        (DYNASTY_ID, game_id, "regular_season", "10080", "Joe Burrow", 6, "QB",
         4150, 33, 530, 355, 9, 104.8, 180, 2, 35),  # Came back strong
    ]

    conn.executemany("""
        INSERT INTO player_game_stats (
            dynasty_id, game_id, season_type, player_id, player_name, team_id, position,
            passing_yards, passing_tds, passing_attempts, passing_completions, passing_interceptions, passing_rating,
            rushing_yards, rushing_tds, rushing_attempts
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, stats)

    # WR/TE receiving stats (separate inserts for clarity)
    wr_stats = [
        # (dynasty_id, game_id, season_type, player_id, player_name, team_id, position,
        #  receptions, receiving_yards, receiving_tds, targets)
        # WRs
        (DYNASTY_ID, game_id, "regular_season", "10020", "Ja'Marr Chase", 6, "WR", 115, 1708, 17, 155),
        (DYNASTY_ID, game_id, "regular_season", "10021", "Tyreek Hill", 2, "WR", 105, 1520, 10, 145),
        (DYNASTY_ID, game_id, "regular_season", "10022", "CeeDee Lamb", 17, "WR", 118, 1580, 12, 160),
        (DYNASTY_ID, game_id, "regular_season", "10023", "Amon-Ra St. Brown", 22, "WR", 125, 1450, 9, 165),
        (DYNASTY_ID, game_id, "regular_season", "10024", "Davante Adams", 4, "WR", 98, 1280, 9, 140),
        (DYNASTY_ID, game_id, "regular_season", "10025", "A.J. Brown", 19, "WR", 88, 1350, 11, 130),
        (DYNASTY_ID, game_id, "regular_season", "10026", "Justin Jefferson", 24, "WR", 110, 1620, 13, 152),
        (DYNASTY_ID, game_id, "regular_season", "10027", "Stefon Diggs", 9, "WR", 95, 1180, 8, 135),
        (DYNASTY_ID, game_id, "regular_season", "10061", "Marvin Harrison Jr", 29, "WR", 85, 1180, 10, 125),  # Rookie
        (DYNASTY_ID, game_id, "regular_season", "10062", "Malik Nabers", 18, "WR", 92, 1100, 8, 135),  # Rookie
        # TEs
        (DYNASTY_ID, game_id, "regular_season", "10110", "Travis Kelce", 14, "TE", 95, 1050, 8, 125),
        (DYNASTY_ID, game_id, "regular_season", "10111", "George Kittle", 31, "TE", 75, 920, 7, 105),
        (DYNASTY_ID, game_id, "regular_season", "10112", "Mark Andrews", 5, "TE", 68, 780, 6, 95),
        (DYNASTY_ID, game_id, "regular_season", "10113", "T.J. Hockenson", 24, "TE", 72, 850, 5, 100),
        (DYNASTY_ID, game_id, "regular_season", "10114", "Dalton Kincaid", 1, "TE", 78, 880, 6, 108),
        (DYNASTY_ID, game_id, "regular_season", "10115", "Sam LaPorta", 22, "TE", 82, 820, 7, 110),
        (DYNASTY_ID, game_id, "regular_season", "10116", "David Njoku", 7, "TE", 65, 720, 5, 90),
        (DYNASTY_ID, game_id, "regular_season", "10117", "Dallas Goedert", 19, "TE", 58, 680, 4, 85),
    ]

    for wr in wr_stats:
        conn.execute("""
            UPDATE player_game_stats
            SET receptions = ?, receiving_yards = ?, receiving_tds = ?, targets = ?
            WHERE dynasty_id = ? AND player_id = ?
        """, (wr[7], wr[8], wr[9], wr[10], wr[0], wr[3]))

    # Defensive stats for DPOY candidates
    def_stats = [
        # (dynasty_id, game_id, season_type, player_id, player_name, team_id, position,
        #  sacks, tackles_total, tackles_solo, interceptions, forced_fumbles, passes_defended)
        (DYNASTY_ID, game_id, "regular_season", "10030", "Myles Garrett", 7, "EDGE",
         16.0, 48, 38, 0, 4, 8),  # DPOY frontrunner
        (DYNASTY_ID, game_id, "regular_season", "10031", "Micah Parsons", 17, "EDGE",
         14.5, 62, 45, 0, 3, 5),
        (DYNASTY_ID, game_id, "regular_season", "10032", "T.J. Watt", 8, "EDGE",
         13.0, 55, 42, 1, 5, 7),
        (DYNASTY_ID, game_id, "regular_season", "10033", "Nick Bosa", 31, "EDGE",
         12.5, 50, 38, 0, 2, 6),
        (DYNASTY_ID, game_id, "regular_season", "10034", "Maxx Crosby", 15, "EDGE",
         11.5, 58, 42, 0, 3, 4),
        (DYNASTY_ID, game_id, "regular_season", "10037", "Rashan Gary", 23, "EDGE",
         10.0, 52, 38, 0, 2, 3),
        (DYNASTY_ID, game_id, "regular_season", "10035", "Fred Warner", 31, "MLB",
         2.0, 145, 98, 2, 2, 8),
        (DYNASTY_ID, game_id, "regular_season", "10036", "Roquan Smith", 5, "MLB",
         3.5, 155, 105, 3, 1, 6),
        (DYNASTY_ID, game_id, "regular_season", "10038", "Zack Baun", 19, "MLB",
         2.5, 138, 95, 2, 1, 5),
        (DYNASTY_ID, game_id, "regular_season", "10039", "Patrick Queen", 8, "MLB",
         2.0, 125, 88, 1, 2, 4),
        # DTs
        (DYNASTY_ID, game_id, "regular_season", "10150", "Chris Jones", 14, "DT",
         10.5, 45, 32, 0, 2, 3),
        (DYNASTY_ID, game_id, "regular_season", "10151", "Dexter Lawrence", 18, "DT",
         9.5, 52, 38, 0, 3, 2),
        (DYNASTY_ID, game_id, "regular_season", "10152", "Quinnen Williams", 4, "DT",
         8.0, 48, 35, 0, 2, 1),
        (DYNASTY_ID, game_id, "regular_season", "10153", "Javon Hargrave", 25, "DT",
         7.5, 42, 30, 0, 1, 2),
        (DYNASTY_ID, game_id, "regular_season", "10154", "Cameron Heyward", 8, "DT",
         7.0, 55, 40, 0, 2, 3),
        (DYNASTY_ID, game_id, "regular_season", "10155", "Leonard Williams", 32, "DT",
         6.5, 50, 35, 0, 1, 2),
        # OLBs
        (DYNASTY_ID, game_id, "regular_season", "10160", "Matthew Judon", 25, "LOLB",
         8.5, 48, 35, 0, 2, 3),
        (DYNASTY_ID, game_id, "regular_season", "10161", "Khalil Mack", 16, "LOLB",
         9.5, 52, 38, 0, 3, 4),
        (DYNASTY_ID, game_id, "regular_season", "10162", "Za'Darius Smith", 7, "ROLB",
         8.0, 45, 32, 1, 2, 3),
        (DYNASTY_ID, game_id, "regular_season", "10163", "Tremaine Edmunds", 21, "ROLB",
         2.0, 115, 82, 2, 1, 5),
        (DYNASTY_ID, game_id, "regular_season", "10164", "Harold Landry", 12, "LOLB",
         7.5, 42, 30, 0, 1, 2),
        (DYNASTY_ID, game_id, "regular_season", "10165", "Brian Burns", 18, "ROLB",
         10.0, 55, 40, 0, 3, 4),
        # CBs
        (DYNASTY_ID, game_id, "regular_season", "10040", "Sauce Gardner", 4, "CB",
         0.0, 62, 52, 5, 1, 18),
        (DYNASTY_ID, game_id, "regular_season", "10170", "Derek Stingley", 9, "CB",
         0.5, 55, 45, 4, 1, 15),
        (DYNASTY_ID, game_id, "regular_season", "10171", "Patrick Surtain", 13, "CB",
         0.0, 48, 38, 3, 0, 16),
        (DYNASTY_ID, game_id, "regular_season", "10172", "Denzel Ward", 7, "CB",
         0.0, 52, 42, 4, 1, 14),
        (DYNASTY_ID, game_id, "regular_season", "10173", "Jaylon Johnson", 21, "CB",
         0.5, 58, 48, 3, 0, 12),
        (DYNASTY_ID, game_id, "regular_season", "10174", "Jaire Alexander", 23, "CB",
         0.0, 45, 35, 2, 1, 13),
        (DYNASTY_ID, game_id, "regular_season", "10175", "Jaycee Horn", 26, "CB",
         0.0, 50, 40, 3, 0, 11),
        (DYNASTY_ID, game_id, "regular_season", "10176", "Trevon Diggs", 17, "CB",
         0.0, 55, 45, 5, 0, 10),
        (DYNASTY_ID, game_id, "regular_season", "10177", "Marlon Humphrey", 5, "CB",
         0.5, 60, 50, 3, 2, 12),
        (DYNASTY_ID, game_id, "regular_season", "10178", "Devon Witherspoon", 32, "CB",
         1.0, 65, 55, 4, 1, 14),
        # Safeties
        (DYNASTY_ID, game_id, "regular_season", "10041", "Derwin James", 16, "SS",
         2.5, 95, 72, 4, 2, 10),
        (DYNASTY_ID, game_id, "regular_season", "10180", "Jessie Bates", 25, "FS",
         1.0, 88, 65, 5, 1, 8),
        (DYNASTY_ID, game_id, "regular_season", "10181", "Minkah Fitzpatrick", 8, "FS",
         1.5, 82, 60, 4, 2, 9),
        (DYNASTY_ID, game_id, "regular_season", "10182", "Kyle Hamilton", 5, "SS",
         2.0, 105, 78, 3, 1, 7),
        (DYNASTY_ID, game_id, "regular_season", "10183", "Antoine Winfield", 28, "SS",
         3.0, 92, 68, 4, 2, 11),
        (DYNASTY_ID, game_id, "regular_season", "10184", "Kevin Byard", 21, "FS",
         0.5, 75, 55, 3, 0, 6),
        (DYNASTY_ID, game_id, "regular_season", "10185", "Jordan Poyer", 1, "FS",
         1.0, 78, 58, 3, 1, 7),
        (DYNASTY_ID, game_id, "regular_season", "10186", "Talanoa Hufanga", 31, "SS",
         2.5, 85, 62, 2, 2, 8),
        # DROY candidates
        (DYNASTY_ID, game_id, "regular_season", "10070", "Dallas Turner", 24, "EDGE",
         9.5, 42, 32, 0, 2, 4),  # DROY frontrunner
        (DYNASTY_ID, game_id, "regular_season", "10071", "Laiatu Latu", 10, "EDGE",
         8.0, 38, 28, 0, 1, 3),
        (DYNASTY_ID, game_id, "regular_season", "10072", "Byron Murphy", 32, "DT",
         6.5, 52, 35, 0, 3, 2),
        # CPOY defensive
        (DYNASTY_ID, game_id, "regular_season", "10081", "Aaron Donald", 30, "DT",
         10.0, 55, 40, 0, 3, 5),  # Came back from retirement
    ]

    conn.executemany("""
        INSERT INTO player_game_stats (
            dynasty_id, game_id, season_type, player_id, player_name, team_id, position,
            sacks, tackles_total, tackles_solo, interceptions, forced_fumbles, passes_defended
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, def_stats)

    conn.commit()
    print(f"    Inserted stats for {len(stats) + len(def_stats)} players")


def insert_player_grades(conn: sqlite3.Connection):
    """Insert player season grades for awards calculation."""
    print("  Inserting player grades...")

    # (dynasty_id, season, player_id, team_id, position, overall_grade, passing_grade, rushing_grade, etc.)
    grades = [
        # QBs
        (DYNASTY_ID, SEASON, 10001, 1, "QB", 94.5, 95.0, 85.0, None, None, None, None, None, None, None, 1200, 17),  # Josh Allen
        (DYNASTY_ID, SEASON, 10003, 5, "QB", 92.0, 91.5, 88.0, None, None, None, None, None, None, None, 1150, 17),  # Lamar
        (DYNASTY_ID, SEASON, 10004, 19, "QB", 88.5, 89.0, 82.0, None, None, None, None, None, None, None, 1100, 17), # Hurts
        (DYNASTY_ID, SEASON, 10005, 14, "QB", 90.0, 91.0, 75.0, None, None, None, None, None, None, None, 1180, 17), # Mahomes

        # RBs
        (DYNASTY_ID, SEASON, 10002, 1, "RB", 85.0, None, 86.5, 82.0, None, None, None, None, None, None, 650, 17),   # Cook
        (DYNASTY_ID, SEASON, 10010, 19, "RB", 93.0, None, 94.5, 88.0, None, None, None, None, None, None, 720, 17),  # Barkley - OPOY
        (DYNASTY_ID, SEASON, 10011, 5, "RB", 91.5, None, 92.0, 85.0, None, None, None, None, None, None, 700, 17),   # Henry
        (DYNASTY_ID, SEASON, 10012, 25, "RB", 84.0, None, 85.0, 80.0, None, None, None, None, None, None, 580, 17),  # Robinson

        # WRs
        (DYNASTY_ID, SEASON, 10020, 6, "WR", 93.5, None, None, 94.0, None, None, None, None, None, None, 950, 17),   # Chase
        (DYNASTY_ID, SEASON, 10021, 2, "WR", 90.0, None, None, 91.0, None, None, None, None, None, None, 900, 17),   # Hill
        (DYNASTY_ID, SEASON, 10022, 17, "WR", 91.0, None, None, 91.5, None, None, None, None, None, None, 920, 17),  # Lamb
        (DYNASTY_ID, SEASON, 10023, 22, "WR", 88.0, None, None, 89.0, None, None, None, None, None, None, 880, 17),  # St Brown

        # EDGE/DL - DPOY
        (DYNASTY_ID, SEASON, 10030, 7, "EDGE", 95.0, None, None, None, None, None, 96.0, 92.0, None, 90.0, 820, 17), # Garrett - DPOY
        (DYNASTY_ID, SEASON, 10031, 17, "EDGE", 93.0, None, None, None, None, None, 94.0, 90.0, None, 88.0, 800, 17), # Parsons
        (DYNASTY_ID, SEASON, 10032, 8, "EDGE", 91.5, None, None, None, None, None, 92.0, 89.0, None, 87.0, 780, 17),  # Watt
        (DYNASTY_ID, SEASON, 10033, 31, "EDGE", 90.5, None, None, None, None, None, 91.0, 88.0, None, 86.0, 760, 17), # Bosa

        # LBs
        (DYNASTY_ID, SEASON, 10035, 31, "MLB", 88.5, None, None, None, None, None, 75.0, 90.0, 89.0, 91.0, 1050, 17), # Warner
        (DYNASTY_ID, SEASON, 10036, 5, "MLB", 89.5, None, None, None, None, None, 78.0, 91.0, 88.0, 92.0, 1100, 17),  # Smith

        # DBs
        (DYNASTY_ID, SEASON, 10040, 4, "CB", 90.0, None, None, None, None, None, None, 82.0, 92.0, 88.0, 900, 17),    # Gardner
        (DYNASTY_ID, SEASON, 10041, 16, "SS", 88.0, None, None, None, None, None, 75.0, 85.0, 89.0, 90.0, 950, 17),   # James

        # OROY
        (DYNASTY_ID, SEASON, 10060, 21, "QB", 82.0, 83.0, 78.0, None, None, None, None, None, None, None, 1000, 17), # Caleb Williams
        (DYNASTY_ID, SEASON, 10061, 29, "WR", 80.5, None, None, 81.0, None, None, None, None, None, None, 750, 17),  # MHJ
        (DYNASTY_ID, SEASON, 10062, 18, "WR", 78.0, None, None, 79.0, None, None, None, None, None, None, 720, 17),  # Nabers

        # DROY
        (DYNASTY_ID, SEASON, 10070, 24, "EDGE", 81.5, None, None, None, None, None, 82.0, 80.0, None, 78.0, 680, 17), # Turner - DROY
        (DYNASTY_ID, SEASON, 10071, 10, "EDGE", 78.0, None, None, None, None, None, 79.0, 77.0, None, 75.0, 620, 17), # Latu
        (DYNASTY_ID, SEASON, 10072, 32, "DT", 76.5, None, None, None, None, None, 78.0, 80.0, None, 74.0, 600, 17),   # Murphy

        # CPOY
        (DYNASTY_ID, SEASON, 10080, 6, "QB", 91.0, 92.0, 78.0, None, None, None, None, None, None, None, 1100, 17),  # Burrow
        (DYNASTY_ID, SEASON, 10081, 30, "DT", 88.0, None, None, None, None, None, 90.0, 88.0, None, 85.0, 750, 17),  # Donald

        # === ALL PRO BOWL POSITIONS ===

        # Fullbacks (FB)
        (DYNASTY_ID, SEASON, 10100, 31, "FB", 85.0, None, 82.0, 75.0, 88.0, 90.0, None, None, None, None, 450, 17),  # Juszczyk
        (DYNASTY_ID, SEASON, 10101, 5, "FB", 83.0, None, 80.0, 72.0, 86.0, 88.0, None, None, None, None, 420, 17),   # Ricard
        (DYNASTY_ID, SEASON, 10102, 2, "FB", 80.0, None, 78.0, 70.0, 84.0, 86.0, None, None, None, None, 380, 17),   # Ingold
        (DYNASTY_ID, SEASON, 10103, 21, "FB", 78.0, None, 76.0, 68.0, 82.0, 84.0, None, None, None, None, 350, 17),  # Blasingame

        # More WRs
        (DYNASTY_ID, SEASON, 10024, 4, "WR", 87.0, None, None, 88.0, None, None, None, None, None, None, 850, 17),   # Adams
        (DYNASTY_ID, SEASON, 10025, 19, "WR", 89.5, None, None, 90.0, None, None, None, None, None, None, 870, 17),  # A.J. Brown
        (DYNASTY_ID, SEASON, 10026, 24, "WR", 92.0, None, None, 93.0, None, None, None, None, None, None, 940, 17),  # Jefferson
        (DYNASTY_ID, SEASON, 10027, 9, "WR", 86.0, None, None, 87.0, None, None, None, None, None, None, 820, 17),   # Diggs

        # Tight Ends (TE)
        (DYNASTY_ID, SEASON, 10110, 14, "TE", 91.0, None, None, 92.0, 85.0, 88.0, None, None, None, None, 800, 17),  # Kelce
        (DYNASTY_ID, SEASON, 10111, 31, "TE", 89.0, None, None, 88.0, 82.0, 90.0, None, None, None, None, 780, 17),  # Kittle
        (DYNASTY_ID, SEASON, 10112, 5, "TE", 86.0, None, None, 87.0, 78.0, 82.0, None, None, None, None, 720, 17),   # Andrews
        (DYNASTY_ID, SEASON, 10113, 24, "TE", 85.0, None, None, 86.0, 75.0, 80.0, None, None, None, None, 700, 17),  # Hockenson
        (DYNASTY_ID, SEASON, 10114, 1, "TE", 82.0, None, None, 83.0, 72.0, 78.0, None, None, None, None, 650, 17),   # Kincaid
        (DYNASTY_ID, SEASON, 10115, 22, "TE", 83.0, None, None, 84.0, 74.0, 80.0, None, None, None, None, 680, 17),  # LaPorta
        (DYNASTY_ID, SEASON, 10116, 7, "TE", 80.0, None, None, 81.0, 76.0, 82.0, None, None, None, None, 620, 17),   # Njoku
        (DYNASTY_ID, SEASON, 10117, 19, "TE", 81.0, None, None, 82.0, 78.0, 84.0, None, None, None, None, 640, 17),  # Goedert

        # Offensive Tackles (OT = LT + RT)
        (DYNASTY_ID, SEASON, 10120, 31, "LT", 94.0, None, None, None, 95.0, 93.0, None, None, None, None, 1100, 17), # Trent Williams
        (DYNASTY_ID, SEASON, 10121, 19, "RT", 92.0, None, None, None, 93.0, 91.0, None, None, None, None, 1080, 17), # Lane Johnson
        (DYNASTY_ID, SEASON, 10122, 9, "LT", 90.0, None, None, None, 91.0, 89.0, None, None, None, None, 1050, 17),  # Tunsil
        (DYNASTY_ID, SEASON, 10123, 22, "LT", 91.0, None, None, None, 92.0, 90.0, None, None, None, None, 1060, 17), # Sewell
        (DYNASTY_ID, SEASON, 10124, 16, "LT", 89.0, None, None, None, 90.0, 88.0, None, None, None, None, 1020, 17), # Slater
        (DYNASTY_ID, SEASON, 10125, 28, "RT", 90.0, None, None, None, 91.0, 89.0, None, None, None, None, 1040, 17), # Wirfs
        (DYNASTY_ID, SEASON, 10126, 1, "LT", 86.0, None, None, None, 87.0, 85.0, None, None, None, None, 980, 17),   # Dawkins
        (DYNASTY_ID, SEASON, 10127, 27, "RT", 87.0, None, None, None, 88.0, 86.0, None, None, None, None, 990, 17),  # Ramczyk
        (DYNASTY_ID, SEASON, 10128, 6, "LT", 85.0, None, None, None, 86.0, 84.0, None, None, None, None, 960, 17),   # O. Brown
        (DYNASTY_ID, SEASON, 10129, 4, "RT", 83.0, None, None, None, 84.0, 82.0, None, None, None, None, 920, 17),   # Moses

        # Offensive Guards (OG = LG + RG)
        (DYNASTY_ID, SEASON, 10130, 10, "LG", 93.0, None, None, None, 94.0, 92.0, None, None, None, None, 1080, 17), # Nelson
        (DYNASTY_ID, SEASON, 10131, 17, "RG", 91.0, None, None, None, 92.0, 90.0, None, None, None, None, 1050, 17), # Martin
        (DYNASTY_ID, SEASON, 10132, 7, "LG", 89.0, None, None, None, 90.0, 88.0, None, None, None, None, 1020, 17),  # Bitonio
        (DYNASTY_ID, SEASON, 10133, 25, "RG", 88.0, None, None, None, 89.0, 87.0, None, None, None, None, 1000, 17), # Lindstrom
        (DYNASTY_ID, SEASON, 10134, 14, "LG", 87.0, None, None, None, 88.0, 86.0, None, None, None, None, 980, 17),  # Thuney
        (DYNASTY_ID, SEASON, 10135, 19, "LG", 86.0, None, None, None, 87.0, 85.0, None, None, None, None, 960, 17),  # Dickerson
        (DYNASTY_ID, SEASON, 10136, 5, "RG", 85.0, None, None, None, 86.0, 84.0, None, None, None, None, 940, 17),   # Zeitler
        (DYNASTY_ID, SEASON, 10137, 17, "LG", 84.0, None, None, None, 85.0, 83.0, None, None, None, None, 920, 17),  # Tyler Smith
        (DYNASTY_ID, SEASON, 10138, 7, "RG", 86.0, None, None, None, 87.0, 85.0, None, None, None, None, 950, 17),   # Teller
        (DYNASTY_ID, SEASON, 10139, 22, "RG", 83.0, None, None, None, 84.0, 82.0, None, None, None, None, 900, 17),  # E. Brown

        # Centers (C)
        (DYNASTY_ID, SEASON, 10140, 14, "C", 92.0, None, None, None, 93.0, 91.0, None, None, None, None, 1070, 17),  # Humphrey
        (DYNASTY_ID, SEASON, 10141, 22, "C", 90.0, None, None, None, 91.0, 89.0, None, None, None, None, 1040, 17),  # Ragnow
        (DYNASTY_ID, SEASON, 10142, 5, "C", 88.0, None, None, None, 89.0, 87.0, None, None, None, None, 1010, 17),   # Linderbaum
        (DYNASTY_ID, SEASON, 10143, 19, "C", 89.0, None, None, None, 90.0, 88.0, None, None, None, None, 1020, 17),  # J. Kelce
        (DYNASTY_ID, SEASON, 10144, 4, "C", 82.0, None, None, None, 83.0, 81.0, None, None, None, None, 900, 17),    # McGovern
        (DYNASTY_ID, SEASON, 10145, 27, "C", 84.0, None, None, None, 85.0, 83.0, None, None, None, None, 920, 17),   # McCoy

        # More EDGE/DE
        (DYNASTY_ID, SEASON, 10034, 15, "EDGE", 89.0, None, None, None, None, None, 90.0, 87.0, None, 85.0, 740, 17), # Crosby
        (DYNASTY_ID, SEASON, 10037, 23, "EDGE", 86.0, None, None, None, None, None, 87.0, 84.0, None, 82.0, 700, 17), # Gary

        # Defensive Tackles (DT)
        (DYNASTY_ID, SEASON, 10150, 14, "DT", 91.0, None, None, None, None, None, 92.0, 90.0, None, 88.0, 780, 17),  # Jones
        (DYNASTY_ID, SEASON, 10151, 18, "DT", 89.0, None, None, None, None, None, 90.0, 88.0, None, 86.0, 760, 17),  # Lawrence
        (DYNASTY_ID, SEASON, 10152, 4, "DT", 87.0, None, None, None, None, None, 88.0, 86.0, None, 84.0, 740, 17),   # Q. Williams
        (DYNASTY_ID, SEASON, 10153, 25, "DT", 85.0, None, None, None, None, None, 86.0, 84.0, None, 82.0, 720, 17),  # Hargrave
        (DYNASTY_ID, SEASON, 10154, 8, "DT", 86.0, None, None, None, None, None, 87.0, 85.0, None, 83.0, 730, 17),   # Heyward
        (DYNASTY_ID, SEASON, 10155, 32, "DT", 83.0, None, None, None, None, None, 84.0, 82.0, None, 80.0, 700, 17),  # L. Williams

        # More LBs (ILB/MLB)
        (DYNASTY_ID, SEASON, 10038, 19, "MLB", 86.0, None, None, None, None, None, 72.0, 88.0, 85.0, 89.0, 1000, 17), # Baun
        (DYNASTY_ID, SEASON, 10039, 8, "MLB", 84.0, None, None, None, None, None, 70.0, 86.0, 83.0, 87.0, 980, 17),   # Queen

        # Outside Linebackers (OLB)
        (DYNASTY_ID, SEASON, 10160, 25, "LOLB", 85.0, None, None, None, None, None, 86.0, 83.0, 78.0, 82.0, 700, 17), # Judon
        (DYNASTY_ID, SEASON, 10161, 16, "LOLB", 87.0, None, None, None, None, None, 88.0, 85.0, 75.0, 84.0, 720, 17), # Mack
        (DYNASTY_ID, SEASON, 10162, 7, "ROLB", 84.0, None, None, None, None, None, 85.0, 82.0, 76.0, 81.0, 680, 17),  # Za'Darius
        (DYNASTY_ID, SEASON, 10163, 21, "ROLB", 82.0, None, None, None, None, None, 70.0, 84.0, 80.0, 86.0, 750, 17), # Edmunds
        (DYNASTY_ID, SEASON, 10164, 12, "LOLB", 83.0, None, None, None, None, None, 84.0, 81.0, 74.0, 80.0, 660, 17), # Landry
        (DYNASTY_ID, SEASON, 10165, 18, "ROLB", 86.0, None, None, None, None, None, 87.0, 84.0, 77.0, 83.0, 710, 17), # Burns

        # More Cornerbacks (CB)
        (DYNASTY_ID, SEASON, 10170, 9, "CB", 88.0, None, None, None, None, None, None, 80.0, 90.0, 86.0, 880, 17),    # Stingley
        (DYNASTY_ID, SEASON, 10171, 13, "CB", 89.0, None, None, None, None, None, None, 78.0, 91.0, 85.0, 890, 17),   # Surtain
        (DYNASTY_ID, SEASON, 10172, 7, "CB", 87.0, None, None, None, None, None, None, 79.0, 89.0, 84.0, 870, 17),    # Ward
        (DYNASTY_ID, SEASON, 10173, 21, "CB", 85.0, None, None, None, None, None, None, 77.0, 87.0, 82.0, 850, 17),   # J. Johnson
        (DYNASTY_ID, SEASON, 10174, 23, "CB", 86.0, None, None, None, None, None, None, 76.0, 88.0, 83.0, 860, 17),   # Alexander
        (DYNASTY_ID, SEASON, 10175, 26, "CB", 84.0, None, None, None, None, None, None, 75.0, 86.0, 81.0, 840, 17),   # Horn
        (DYNASTY_ID, SEASON, 10176, 17, "CB", 83.0, None, None, None, None, None, None, 74.0, 85.0, 80.0, 830, 17),   # T. Diggs
        (DYNASTY_ID, SEASON, 10177, 5, "CB", 86.5, None, None, None, None, None, None, 78.0, 88.0, 84.0, 865, 17),    # Humphrey
        (DYNASTY_ID, SEASON, 10178, 32, "CB", 85.5, None, None, None, None, None, None, 80.0, 87.0, 85.0, 855, 17),   # Witherspoon

        # Safeties (FS + SS)
        (DYNASTY_ID, SEASON, 10180, 25, "FS", 87.0, None, None, None, None, None, 72.0, 84.0, 88.0, 86.0, 920, 17),   # Bates
        (DYNASTY_ID, SEASON, 10181, 8, "FS", 88.0, None, None, None, None, None, 74.0, 86.0, 90.0, 87.0, 940, 17),    # Fitzpatrick
        (DYNASTY_ID, SEASON, 10182, 5, "SS", 89.0, None, None, None, None, None, 76.0, 87.0, 88.0, 89.0, 960, 17),    # Hamilton
        (DYNASTY_ID, SEASON, 10183, 28, "SS", 87.5, None, None, None, None, None, 78.0, 85.0, 87.0, 88.0, 930, 17),   # Winfield
        (DYNASTY_ID, SEASON, 10184, 21, "FS", 84.0, None, None, None, None, None, 70.0, 82.0, 86.0, 84.0, 880, 17),   # Byard
        (DYNASTY_ID, SEASON, 10185, 1, "FS", 85.0, None, None, None, None, None, 71.0, 83.0, 87.0, 85.0, 900, 17),    # Poyer
        (DYNASTY_ID, SEASON, 10186, 31, "SS", 86.0, None, None, None, None, None, 75.0, 84.0, 86.0, 87.0, 910, 17),   # Hufanga

        # Kickers (K)
        (DYNASTY_ID, SEASON, 10190, 5, "K", 95.0, None, None, None, None, None, None, None, None, None, 80, 17),     # Tucker
        (DYNASTY_ID, SEASON, 10191, 17, "K", 92.0, None, None, None, None, None, None, None, None, None, 75, 17),    # Aubrey
        (DYNASTY_ID, SEASON, 10192, 9, "K", 88.0, None, None, None, None, None, None, None, None, None, 70, 17),     # Fairbairn
        (DYNASTY_ID, SEASON, 10193, 31, "K", 86.0, None, None, None, None, None, None, None, None, None, 68, 17),    # Moody

        # Punters (P)
        (DYNASTY_ID, SEASON, 10195, 4, "P", 88.0, None, None, None, None, None, None, None, None, None, 85, 17),     # Mann
        (DYNASTY_ID, SEASON, 10196, 22, "P", 90.0, None, None, None, None, None, None, None, None, None, 90, 17),    # Fox
        (DYNASTY_ID, SEASON, 10197, 15, "P", 89.0, None, None, None, None, None, None, None, None, None, 88, 17),    # Cole
        (DYNASTY_ID, SEASON, 10198, 14, "P", 87.0, None, None, None, None, None, None, None, None, None, 82, 17),    # Townsend
        (DYNASTY_ID, SEASON, 10199, 21, "P", 85.0, None, None, None, None, None, None, None, None, None, 78, 17),    # Taylor

        # Long Snappers (LS)
        (DYNASTY_ID, SEASON, 10200, 12, "LS", 88.0, None, None, None, None, None, None, None, None, None, 60, 17),   # Cox
        (DYNASTY_ID, SEASON, 10201, 31, "LS", 90.0, None, None, None, None, None, None, None, None, None, 62, 17),   # Harris
        (DYNASTY_ID, SEASON, 10202, 23, "LS", 86.0, None, None, None, None, None, None, None, None, None, 58, 17),   # Bradley
        (DYNASTY_ID, SEASON, 10203, 11, "LS", 84.0, None, None, None, None, None, None, None, None, None, 55, 17),   # Matiscik

        # Return Specialists (RS - KR position)
        (DYNASTY_ID, SEASON, 10205, 17, "KR", 88.0, None, 85.0, None, None, None, None, None, None, None, 200, 17),  # Turpin
        (DYNASTY_ID, SEASON, 10206, 14, "KR", 82.0, None, 80.0, None, None, None, None, None, None, None, 180, 17),  # Toney
        (DYNASTY_ID, SEASON, 10207, 1, "KR", 84.0, None, 82.0, None, None, None, None, None, None, None, 190, 17),   # Harty
        (DYNASTY_ID, SEASON, 10208, 25, "KR", 83.0, None, 81.0, None, None, None, None, None, None, None, 185, 17),  # McCloud

        # Special Teamers (ST - KR position for coverage)
        (DYNASTY_ID, SEASON, 10210, 3, "KR", 90.0, None, None, None, None, None, None, 88.0, None, 92.0, 350, 17),   # Slater
        (DYNASTY_ID, SEASON, 10211, 32, "KR", 86.0, None, None, None, None, None, None, 84.0, None, 88.0, 320, 17),  # Bellore
        (DYNASTY_ID, SEASON, 10212, 3, "KR", 82.0, None, None, None, None, None, None, 80.0, None, 85.0, 280, 17),   # Schooler
        (DYNASTY_ID, SEASON, 10213, 1, "KR", 84.0, None, None, None, None, None, None, 82.0, None, 86.0, 300, 17),   # Matakevich
    ]

    conn.executemany("""
        INSERT INTO player_season_grades (
            dynasty_id, season, player_id, team_id, position, overall_grade,
            passing_grade, rushing_grade, receiving_grade, pass_blocking_grade, run_blocking_grade,
            pass_rush_grade, run_defense_grade, coverage_grade, tackling_grade, total_snaps, games_graded
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, grades)

    conn.commit()
    print(f"    Inserted grades for {len(grades)} players")


def insert_award_definitions(conn: sqlite3.Connection):
    """Insert award definitions if missing."""
    print("  Checking award definitions...")

    awards = [
        ("mvp", "Most Valuable Player", "INDIVIDUAL", "season", "Regular season MVP"),
        ("opoy", "Offensive Player of the Year", "INDIVIDUAL", "season", "Best offensive player"),
        ("dpoy", "Defensive Player of the Year", "INDIVIDUAL", "season", "Best defensive player"),
        ("oroy", "Offensive Rookie of the Year", "INDIVIDUAL", "season", "Best offensive rookie"),
        ("droy", "Defensive Rookie of the Year", "INDIVIDUAL", "season", "Best defensive rookie"),
        ("cpoy", "Comeback Player of the Year", "INDIVIDUAL", "season", "Best comeback player"),
        ("super_bowl_mvp", "Super Bowl MVP", "INDIVIDUAL", "playoffs", "Super Bowl game MVP"),
    ]

    for award in awards:
        conn.execute("""
            INSERT OR IGNORE INTO award_definitions (award_id, award_name, award_type, category, description)
            VALUES (?, ?, ?, ?, ?)
        """, award)

    conn.commit()
    print("    Award definitions ready")


def insert_super_bowl_game(conn: sqlite3.Connection):
    """Insert Super Bowl game."""
    print("  Inserting Super Bowl game...")

    conn.execute("""
        INSERT INTO games (
            game_id, dynasty_id, season, week, season_type, game_type,
            home_team_id, away_team_id, home_score, away_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        f"SB_{SEASON}_{DYNASTY_ID}",
        DYNASTY_ID,
        SEASON,
        22,  # Super Bowl week
        "playoffs",
        "super_bowl",
        1,   # Buffalo Bills (home/winner)
        30,  # Los Angeles Rams (away)
        34,  # Bills score
        28,  # Rams score
    ))

    conn.commit()
    print("    Super Bowl: Bills 34 - Rams 28")


def insert_super_bowl_mvp(conn: sqlite3.Connection):
    """Insert Super Bowl MVP only (other awards calculated by AwardsService)."""
    print("  Inserting Super Bowl MVP...")

    # Super Bowl MVP - James Cook (separate super_bowl_mvp table)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS super_bowl_mvp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            game_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            position TEXT,
            winning_team INTEGER DEFAULT 1,
            stat_line TEXT,
            mvp_score REAL DEFAULT 0,
            awarded_date TEXT,
            UNIQUE(dynasty_id, season)
        )
    """)

    conn.execute("""
        INSERT INTO super_bowl_mvp (
            dynasty_id, season, game_id, player_id, player_name, team_id,
            position, winning_team, stat_line, mvp_score, awarded_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        DYNASTY_ID, SEASON, f"SB_{SEASON}_{DYNASTY_ID}", 10002, "James Cook", 1,
        "RB", 1,
        '{"rushing_yards": 61, "rushing_tds": 2, "receiving_yards": 101, "receiving_tds": 1}',
        95.5, "2025-02-09"
    ))

    conn.commit()
    print("    Super Bowl MVP: James Cook (RB, Bills)")


def calculate_awards(db_path: str):
    """Run the awards calculation algorithm to determine all 6 major award winners."""
    print("  Calculating awards using AwardsService...")

    try:
        from game_cycle.services.awards_service import AwardsService

        service = AwardsService(str(db_path), DYNASTY_ID, SEASON)

        # Calculate all 6 major awards
        results = service.calculate_all_awards()

        # Print results
        for award_id, result in results.items():
            if result.has_winner:
                winner = result.winner
                print(f"    {award_id.upper()}: {winner.player_name} ({winner.position}, Team {winner.team_id}) - {winner.vote_share:.1%}")
            else:
                print(f"    {award_id.upper()}: No winner calculated")

        print(f"    Calculated {len(results)} awards")

        # Select Pro Bowl rosters
        print("  Selecting Pro Bowl rosters...")
        pro_bowl = service.select_pro_bowl_rosters()
        afc_count = sum(len(players) for players in pro_bowl.afc_roster.values())
        nfc_count = sum(len(players) for players in pro_bowl.nfc_roster.values())
        print(f"    Pro Bowl: {afc_count} AFC players, {nfc_count} NFC players")

        # Select All-Pro teams
        print("  Selecting All-Pro teams...")
        all_pro = service.select_all_pro_teams()
        print(f"    All-Pro: {all_pro.first_team_count} First Team, {all_pro.second_team_count} Second Team")

        # Record stat leaders
        print("  Recording stat leaders...")
        stat_leaders_result = service.record_statistical_leaders()
        print(f"    Stat Leaders: {stat_leaders_result.total_recorded} entries across {len(stat_leaders_result.leaders_by_category)} categories")

    except ImportError as e:
        print(f"    Warning: Could not import AwardsService: {e}")
        print("    Awards will NOT be calculated. Run 'PYTHONPATH=src python demos/seed_season_recap_data.py'")
    except Exception as e:
        print(f"    Error calculating awards: {e}")
        import traceback
        traceback.print_exc()


def insert_career_summaries(conn: sqlite3.Connection):
    """Insert career summaries for retired players."""
    print("  Inserting career summaries...")

    summaries = [
        # Aaron Rodgers - HOF-caliber
        (DYNASTY_ID, 10050, "Aaron Rodgers", "QB", 19, 242, 59055, 475, 0, 0, 0, 0, 0, 0.0, 0,
         10, 4, 1, 4, 1, 0, 95),
        # DeAndre Hopkins - Notable WR
        (DYNASTY_ID, 10051, "DeAndre Hopkins", "WR", 12, 180, 0, 0, 0, 0, 12500, 78, 0, 0.0, 0,
         5, 3, 1, 0, 0, 0, 62),
        # Mike Johnson - Journeyman
        (DYNASTY_ID, 10052, "Mike Johnson", "MLB", 8, 110, 0, 0, 0, 0, 0, 0, 450, 8.5, 2,
         0, 0, 0, 0, 0, 0, 15),
        # Chris Davis - Backup RB
        (DYNASTY_ID, 10053, "Chris Davis", "RB", 6, 85, 0, 0, 2100, 14, 450, 2, 0, 0.0, 0,
         0, 0, 0, 0, 0, 0, 8),
    ]

    conn.executemany("""
        INSERT INTO career_summaries (
            dynasty_id, player_id, full_name, position,
            seasons_played, games_played, pass_yards, pass_tds,
            rush_yards, rush_tds, rec_yards, rec_tds,
            tackles, sacks, interceptions,
            pro_bowls, all_pro_first_team, all_pro_second_team,
            mvp_awards, super_bowl_wins, super_bowl_mvps, hall_of_fame_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, summaries)

    conn.commit()
    print(f"    Inserted {len(summaries)} career summaries")


def insert_retirements(conn: sqlite3.Connection):
    """Insert retired players."""
    print("  Inserting retirements...")

    retirements = [
        # Aaron Rodgers - Notable (Jets)
        (DYNASTY_ID, 10050, SEASON, "age_decline", 4, 19, 41, SEASON + 1),
        # DeAndre Hopkins - Notable (Titans)
        (DYNASTY_ID, 10051, SEASON, "injury", 12, 12, 33, SEASON + 1),
        # Mike Johnson - Non-notable (last team Bills, released)
        (DYNASTY_ID, 10052, SEASON, "released", 1, 8, 32, None),
        # Chris Davis - Non-notable (Cowboys)
        (DYNASTY_ID, 10053, SEASON, "personal", 17, 6, 30, None),
    ]

    conn.executemany("""
        INSERT INTO retired_players (
            dynasty_id, player_id, retirement_season, retirement_reason,
            final_team_id, years_played, age_at_retirement, hall_of_fame_eligible_season
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, retirements)

    conn.commit()
    print(f"    Inserted {len(retirements)} retirements")


def verify_data(conn: sqlite3.Connection):
    """Verify all data was inserted correctly."""
    print("\nVerifying data...")

    # Check dynasty
    cursor = conn.execute(
        "SELECT dynasty_name, team_id, season_year FROM dynasties WHERE dynasty_id = ?",
        (DYNASTY_ID,)
    )
    dynasty = cursor.fetchone()
    if dynasty:
        print(f"  Dynasty: {dynasty[0]} (Team {dynasty[1]}, Season {dynasty[2]})")
    else:
        print("  ERROR: Dynasty not found!")
        return False

    # Check Super Bowl game
    cursor = conn.execute(
        "SELECT home_team_id, away_team_id, home_score, away_score FROM games WHERE dynasty_id = ? AND week = 22",
        (DYNASTY_ID,)
    )
    game = cursor.fetchone()
    if game:
        print(f"  Super Bowl: Team {game[0]} ({game[2]}) vs Team {game[1]} ({game[3]})")
    else:
        print("  ERROR: Super Bowl game not found!")
        return False

    # Check MVPs
    cursor = conn.execute(
        "SELECT award_id, player_id FROM award_winners WHERE dynasty_id = ? AND is_winner = 1",
        (DYNASTY_ID,)
    )
    awards = cursor.fetchall()
    print(f"  Awards: {len(awards)} winners")
    for award in awards:
        print(f"    - {award[0]}: Player {award[1]}")

    # Check retirements
    cursor = conn.execute(
        "SELECT COUNT(*) FROM retired_players WHERE dynasty_id = ? AND retirement_season = ?",
        (DYNASTY_ID, SEASON)
    )
    count = cursor.fetchone()[0]
    print(f"  Retirements: {count} players")

    return True


def main():
    """Main entry point."""
    print("=" * 60)
    print("SEED SEASON RECAP DATA")
    print("=" * 60)
    print()
    print(f"Database: {DB_PATH}")
    print(f"Dynasty:  {DYNASTY_ID}")
    print(f"Season:   {SEASON}")
    print()

    ensure_database_exists()

    conn = sqlite3.connect(str(DB_PATH))

    try:
        # Initialize schema
        initialize_schema(conn)

        # Clear existing test data
        clear_existing_test_data(conn)

        # Insert all data in dependency order
        insert_teams(conn)  # Reference data first
        insert_dynasty(conn)
        insert_players(conn)
        insert_standings(conn)
        insert_season_games(conn)
        insert_player_stats(conn)
        insert_player_grades(conn)
        insert_award_definitions(conn)
        insert_super_bowl_game(conn)
        insert_super_bowl_mvp(conn)
        insert_career_summaries(conn)
        insert_retirements(conn)

        # Close connection before running awards calculation
        conn.commit()
        conn.close()

        # Calculate all 6 major awards using the algorithm
        calculate_awards(DB_PATH)

        # Reopen connection for verification
        conn = sqlite3.connect(str(DB_PATH))

        # Verify
        success = verify_data(conn)

        if success:
            print()
            print("=" * 60)
            print("SUCCESS! Database seeded with Season Recap test data.")
            print("=" * 60)
            print()
            print("Next steps:")
            print("  1. Run the demo in database mode:")
            print("     python demos/season_recap_demo.py")
            print()
            print("  2. Or specify the dynasty directly:")
            print(f"     python demos/season_recap_demo.py --dynasty-id {DYNASTY_ID}")
            print()
        else:
            print()
            print("ERROR: Data verification failed!")
            return 1

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
