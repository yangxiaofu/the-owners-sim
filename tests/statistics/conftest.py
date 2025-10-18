"""
Shared pytest fixtures for Statistics API tests.

Provides in-memory database with sample player stats for testing.
"""
import pytest
import sqlite3
from typing import Generator


@pytest.fixture
def in_memory_db() -> Generator[sqlite3.Connection, None, None]:
    """
    Create in-memory SQLite database with player_game_stats table.

    Yields:
        Database connection with schema and sample data
    """
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Create player_game_stats table (matches schema from docs/schema/database_schema.md)
    cursor.execute("""
        CREATE TABLE player_game_stats (
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            season_type TEXT DEFAULT 'regular_season',
            player_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            position TEXT NOT NULL,
            passing_yards INTEGER DEFAULT 0,
            passing_tds INTEGER DEFAULT 0,
            passing_completions INTEGER DEFAULT 0,
            passing_attempts INTEGER DEFAULT 0,
            passing_interceptions INTEGER DEFAULT 0,
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
            PRIMARY KEY (dynasty_id, game_id, player_id)
        )
    """)

    # Insert sample QB data (20 QBs with realistic stats)
    qb_data = [
        # Elite QBs with known passer ratings
        ('test_dynasty', 'game_001', 'regular_season', 'qb_001', 'Patrick Mahomes', 7, 'QB',
         384, 5, 31, 44, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~122.3 rating
        ('test_dynasty', 'game_002', 'regular_season', 'qb_002', 'Aaron Rodgers 2011', 10, 'QB',
         343, 4, 26, 35, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~139.9 rating
        ('test_dynasty', 'game_003', 'regular_season', 'qb_003', 'Perfect QB', 3, 'QB',
         400, 4, 20, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # 158.3 perfect rating
        ('test_dynasty', 'game_004', 'regular_season', 'qb_004', 'Joe Burrow', 8, 'QB',
         325, 3, 25, 38, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~98.5 rating

        # Good QBs
        ('test_dynasty', 'game_005', 'regular_season', 'qb_005', 'Josh Allen', 2, 'QB',
         287, 2, 22, 33, 1, 45, 1, 6, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~95.8 rating
        ('test_dynasty', 'game_006', 'regular_season', 'qb_006', 'Justin Herbert', 13, 'QB',
         298, 2, 26, 39, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~78.5 rating
        ('test_dynasty', 'game_007', 'regular_season', 'qb_007', 'Lamar Jackson', 21, 'QB',
         218, 1, 18, 28, 0, 89, 1, 12, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~92.4 rating
        ('test_dynasty', 'game_008', 'regular_season', 'qb_008', 'Jalen Hurts', 20, 'QB',
         285, 2, 21, 31, 1, 62, 1, 10, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~98.7 rating

        # Average QBs
        ('test_dynasty', 'game_009', 'regular_season', 'qb_009', 'Kirk Cousins', 1, 'QB',
         265, 2, 23, 36, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~88.4 rating
        ('test_dynasty', 'game_010', 'regular_season', 'qb_010', 'Derek Carr', 15, 'QB',
         248, 1, 20, 32, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~76.6 rating
        ('test_dynasty', 'game_011', 'regular_season', 'qb_011', 'Geno Smith', 24, 'QB',
         275, 2, 24, 35, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~82.1 rating
        ('test_dynasty', 'game_012', 'regular_season', 'qb_012', 'Baker Mayfield', 28, 'QB',
         312, 3, 28, 42, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~95.2 rating

        # Below Average QBs
        ('test_dynasty', 'game_013', 'regular_season', 'qb_013', 'Sam Darnold', 14, 'QB',
         198, 1, 18, 31, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~62.5 rating
        ('test_dynasty', 'game_014', 'regular_season', 'qb_014', 'Ryan Tannehill', 29, 'QB',
         225, 1, 19, 29, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~78.7 rating
        ('test_dynasty', 'game_015', 'regular_season', 'qb_015', 'Jacoby Brissett', 6, 'QB',
         189, 0, 15, 28, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~56.3 rating

        # Young/Backup QBs
        ('test_dynasty', 'game_016', 'regular_season', 'qb_016', 'Tua Tagovailoa', 16, 'QB',
         291, 2, 25, 34, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~103.4 rating
        ('test_dynasty', 'game_017', 'regular_season', 'qb_017', 'Trevor Lawrence', 27, 'QB',
         302, 2, 23, 38, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~90.5 rating
        ('test_dynasty', 'game_018', 'regular_season', 'qb_018', 'Mac Jones', 19, 'QB',
         213, 1, 19, 32, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~66.8 rating
        ('test_dynasty', 'game_019', 'regular_season', 'qb_019', 'Justin Fields', 4, 'QB',
         178, 1, 14, 25, 1, 82, 1, 10, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~78.9 rating
        ('test_dynasty', 'game_020', 'regular_season', 'qb_020', 'Bryce Young', 5, 'QB',
         156, 0, 12, 26, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),  # ~42.3 rating
    ]

    # Insert sample RB data (20 RBs with rushing stats)
    rb_data = [
        # Elite RBs
        ('test_dynasty', 'game_001', 'regular_season', 'rb_001', 'Christian McCaffrey', 23, 'RB',
         0, 0, 0, 0, 0, 142, 2, 22, 85, 1, 8, 10, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_002', 'regular_season', 'rb_002', 'Derrick Henry', 29, 'RB',
         0, 0, 0, 0, 0, 165, 2, 28, 15, 0, 2, 3, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_003', 'regular_season', 'rb_003', 'Nick Chubb', 6, 'RB',
         0, 0, 0, 0, 0, 128, 1, 24, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_004', 'regular_season', 'rb_004', 'Saquon Barkley', 18, 'RB',
         0, 0, 0, 0, 0, 112, 1, 20, 48, 0, 4, 5, 0, 0.0, 0, 0, 0, 0, 0),

        # Good RBs
        ('test_dynasty', 'game_005', 'regular_season', 'rb_005', 'Josh Jacobs', 15, 'RB',
         0, 0, 0, 0, 0, 98, 1, 19, 22, 0, 3, 4, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_006', 'regular_season', 'rb_006', 'Tony Pollard', 11, 'RB',
         0, 0, 0, 0, 0, 105, 1, 18, 35, 0, 4, 5, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_007', 'regular_season', 'rb_007', 'Travis Etienne', 27, 'RB',
         0, 0, 0, 0, 0, 88, 1, 16, 42, 0, 5, 6, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_008', 'regular_season', 'rb_008', 'Aaron Jones', 10, 'RB',
         0, 0, 0, 0, 0, 92, 0, 15, 51, 1, 6, 7, 0, 0.0, 0, 0, 0, 0, 0),

        # Average RBs
        ('test_dynasty', 'game_009', 'regular_season', 'rb_009', 'Miles Sanders', 5, 'RB',
         0, 0, 0, 0, 0, 78, 1, 17, 18, 0, 2, 3, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_010', 'regular_season', 'rb_010', 'Dameon Pierce', 30, 'RB',
         0, 0, 0, 0, 0, 68, 0, 14, 12, 0, 2, 3, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_011', 'regular_season', 'rb_011', 'Kenneth Walker', 24, 'RB',
         0, 0, 0, 0, 0, 85, 1, 16, 8, 0, 1, 2, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_012', 'regular_season', 'rb_012', 'Najee Harris', 22, 'RB',
         0, 0, 0, 0, 0, 72, 0, 18, 28, 0, 3, 4, 0, 0.0, 0, 0, 0, 0, 0),

        # Below Average RBs
        ('test_dynasty', 'game_013', 'regular_season', 'rb_013', 'James Conner', 32, 'RB',
         0, 0, 0, 0, 0, 58, 0, 13, 22, 0, 3, 4, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_014', 'regular_season', 'rb_014', 'David Montgomery', 9, 'RB',
         0, 0, 0, 0, 0, 64, 1, 15, 15, 0, 2, 2, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_015', 'regular_season', 'rb_015', 'Ezekiel Elliott', 19, 'RB',
         0, 0, 0, 0, 0, 52, 0, 12, 18, 0, 2, 3, 0, 0.0, 0, 0, 0, 0, 0),

        # Backup RBs
        ('test_dynasty', 'game_016', 'regular_season', 'rb_016', 'Khalil Herbert', 4, 'RB',
         0, 0, 0, 0, 0, 48, 0, 10, 0, 0, 0, 0, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_017', 'regular_season', 'rb_017', 'Jamaal Williams', 15, 'RB',
         0, 0, 0, 0, 0, 42, 1, 11, 8, 0, 1, 1, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_018', 'regular_season', 'rb_018', 'AJ Dillon', 10, 'RB',
         0, 0, 0, 0, 0, 55, 0, 13, 12, 0, 2, 2, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_019', 'regular_season', 'rb_019', 'Cam Akers', 17, 'RB',
         0, 0, 0, 0, 0, 38, 0, 9, 5, 0, 1, 1, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_020', 'regular_season', 'rb_020', 'Rachaad White', 28, 'RB',
         0, 0, 0, 0, 0, 45, 0, 12, 24, 0, 3, 4, 0, 0.0, 0, 0, 0, 0, 0),
    ]

    # Insert sample WR/TE data (20 WRs/TEs with receiving stats)
    wr_data = [
        # Elite WRs
        ('test_dynasty', 'game_001', 'regular_season', 'wr_001', 'Tyreek Hill', 16, 'WR',
         0, 0, 0, 0, 0, 0, 0, 0, 152, 2, 10, 12, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_002', 'regular_season', 'wr_002', 'Justin Jefferson', 14, 'WR',
         0, 0, 0, 0, 0, 0, 0, 0, 128, 1, 9, 11, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_003', 'regular_season', 'wr_003', 'Stefon Diggs', 2, 'WR',
         0, 0, 0, 0, 0, 0, 0, 0, 115, 1, 8, 10, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_004', 'regular_season', 'wr_004', 'CeeDee Lamb', 11, 'WR',
         0, 0, 0, 0, 0, 0, 0, 0, 142, 2, 11, 13, 0, 0.0, 0, 0, 0, 0, 0),

        # Good WRs
        ('test_dynasty', 'game_005', 'regular_season', 'wr_005', 'AJ Brown', 20, 'WR',
         0, 0, 0, 0, 0, 0, 0, 0, 98, 1, 7, 9, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_006', 'regular_season', 'wr_006', 'Amon-Ra St Brown', 9, 'WR',
         0, 0, 0, 0, 0, 0, 0, 0, 88, 1, 9, 11, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_007', 'regular_season', 'wr_007', 'DeVonta Smith', 20, 'WR',
         0, 0, 0, 0, 0, 0, 0, 0, 75, 0, 6, 8, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_008', 'regular_season', 'wr_008', 'Garrett Wilson', 18, 'WR',
         0, 0, 0, 0, 0, 0, 0, 0, 82, 1, 7, 10, 0, 0.0, 0, 0, 0, 0, 0),

        # Elite TEs
        ('test_dynasty', 'game_009', 'regular_season', 'te_001', 'Travis Kelce', 7, 'TE',
         0, 0, 0, 0, 0, 0, 0, 0, 92, 1, 8, 9, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_010', 'regular_season', 'te_002', 'Mark Andrews', 21, 'TE',
         0, 0, 0, 0, 0, 0, 0, 0, 78, 1, 6, 8, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_011', 'regular_season', 'te_003', 'George Kittle', 23, 'TE',
         0, 0, 0, 0, 0, 0, 0, 0, 85, 0, 7, 8, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_012', 'regular_season', 'te_004', 'TJ Hockenson', 14, 'TE',
         0, 0, 0, 0, 0, 0, 0, 0, 68, 1, 7, 9, 0, 0.0, 0, 0, 0, 0, 0),

        # Average WRs
        ('test_dynasty', 'game_013', 'regular_season', 'wr_009', 'Christian Kirk', 27, 'WR',
         0, 0, 0, 0, 0, 0, 0, 0, 65, 0, 6, 8, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_014', 'regular_season', 'wr_010', 'Diontae Johnson', 22, 'WR',
         0, 0, 0, 0, 0, 0, 0, 0, 72, 0, 8, 11, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_015', 'regular_season', 'wr_011', 'Michael Pittman', 12, 'WR',
         0, 0, 0, 0, 0, 0, 0, 0, 58, 0, 5, 7, 0, 0.0, 0, 0, 0, 0, 0),

        # Average TEs
        ('test_dynasty', 'game_016', 'regular_season', 'te_005', 'Dallas Goedert', 20, 'TE',
         0, 0, 0, 0, 0, 0, 0, 0, 55, 0, 5, 6, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_017', 'regular_season', 'te_006', 'Kyle Pitts', 1, 'TE',
         0, 0, 0, 0, 0, 0, 0, 0, 48, 0, 4, 6, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_018', 'regular_season', 'te_007', 'Pat Freiermuth', 22, 'TE',
         0, 0, 0, 0, 0, 0, 0, 0, 42, 1, 4, 5, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_019', 'regular_season', 'te_008', 'Tyler Higbee', 17, 'TE',
         0, 0, 0, 0, 0, 0, 0, 0, 38, 0, 4, 5, 0, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_020', 'regular_season', 'te_009', 'Hayden Hurst', 5, 'TE',
         0, 0, 0, 0, 0, 0, 0, 0, 32, 0, 3, 4, 0, 0.0, 0, 0, 0, 0, 0),
    ]

    # Insert sample defensive player data (10 defenders)
    def_data = [
        # Elite pass rushers
        ('test_dynasty', 'game_001', 'regular_season', 'def_001', 'Micah Parsons', 11, 'LB',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 2.5, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_002', 'regular_season', 'def_002', 'Nick Bosa', 23, 'DE',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 6, 2.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_003', 'regular_season', 'def_003', 'Myles Garrett', 6, 'DE',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7, 3.0, 0, 0, 0, 0, 0),

        # Good linebackers
        ('test_dynasty', 'game_004', 'regular_season', 'def_004', 'Fred Warner', 23, 'LB',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0.5, 1, 0, 0, 0, 0),
        ('test_dynasty', 'game_005', 'regular_season', 'def_005', 'Roquan Smith', 21, 'LB',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 11, 0.0, 0, 0, 0, 0, 0),
        ('test_dynasty', 'game_006', 'regular_season', 'def_006', 'Bobby Wagner', 24, 'LB',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 0.5, 0, 0, 0, 0, 0),

        # Elite DBs
        ('test_dynasty', 'game_007', 'regular_season', 'def_007', 'Sauce Gardner', 18, 'CB',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0.0, 2, 0, 0, 0, 0),
        ('test_dynasty', 'game_008', 'regular_season', 'def_008', 'Derwin James', 13, 'S',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 9, 0.5, 1, 0, 0, 0, 0),
        ('test_dynasty', 'game_009', 'regular_season', 'def_009', 'Patrick Surtain', 3, 'CB',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 0.0, 2, 0, 0, 0, 0),
        ('test_dynasty', 'game_010', 'regular_season', 'def_010', 'Jalen Ramsey', 16, 'CB',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 6, 0.0, 1, 0, 0, 0, 0),
    ]

    # Insert sample kicker data (5 kickers)
    k_data = [
        ('test_dynasty', 'game_001', 'regular_season', 'k_001', 'Justin Tucker', 21, 'K',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 4, 4, 3, 3),
        ('test_dynasty', 'game_002', 'regular_season', 'k_002', 'Harrison Butker', 7, 'K',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 3, 3, 4, 4),
        ('test_dynasty', 'game_003', 'regular_season', 'k_003', 'Daniel Carlson', 15, 'K',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 2, 3, 2, 2),
        ('test_dynasty', 'game_004', 'regular_season', 'k_004', 'Jake Elliott', 20, 'K',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 3, 4, 1, 1),
        ('test_dynasty', 'game_005', 'regular_season', 'k_005', 'Younghoe Koo', 1, 'K',
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0, 4, 5, 2, 2),
    ]

    # Insert all data
    cursor.executemany("""
        INSERT INTO player_game_stats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, qb_data + rb_data + wr_data + def_data + k_data)

    conn.commit()

    yield conn

    conn.close()


@pytest.fixture
def sample_qb_stats(in_memory_db: sqlite3.Connection) -> list:
    """
    Get sample QB statistics from database.

    Returns:
        List of QB stat dictionaries with calculated fields
    """
    cursor = in_memory_db.cursor()
    cursor.execute("""
        SELECT
            player_id,
            player_name,
            team_id,
            position,
            passing_yards,
            passing_tds,
            passing_completions,
            passing_attempts,
            passing_interceptions,
            rushing_yards,
            rushing_tds
        FROM player_game_stats
        WHERE position = 'QB'
        ORDER BY passing_yards DESC
    """)

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


@pytest.fixture
def sample_rb_stats(in_memory_db: sqlite3.Connection) -> list:
    """Get sample RB statistics"""
    cursor = in_memory_db.cursor()
    cursor.execute("""
        SELECT
            player_id,
            player_name,
            team_id,
            position,
            rushing_yards,
            rushing_tds,
            rushing_attempts,
            receiving_yards,
            receiving_tds,
            receptions
        FROM player_game_stats
        WHERE position = 'RB'
        ORDER BY rushing_yards DESC
    """)

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


@pytest.fixture
def sample_wr_stats(in_memory_db: sqlite3.Connection) -> list:
    """Get sample WR statistics"""
    cursor = in_memory_db.cursor()
    cursor.execute("""
        SELECT
            player_id,
            player_name,
            team_id,
            position,
            receiving_yards,
            receiving_tds,
            receptions,
            targets
        FROM player_game_stats
        WHERE position IN ('WR', 'TE')
        ORDER BY receiving_yards DESC
    """)

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


@pytest.fixture
def sample_all_stats(in_memory_db: sqlite3.Connection) -> list:
    """Get all player statistics (all positions)"""
    cursor = in_memory_db.cursor()
    cursor.execute("""
        SELECT
            player_id,
            player_name,
            team_id,
            position,
            passing_yards,
            passing_tds,
            passing_completions,
            passing_attempts,
            passing_interceptions,
            rushing_yards,
            rushing_tds,
            rushing_attempts,
            receiving_yards,
            receiving_tds,
            receptions,
            targets,
            tackles_total,
            sacks,
            interceptions,
            field_goals_made,
            field_goals_attempted,
            extra_points_made,
            extra_points_attempted
        FROM player_game_stats
        ORDER BY player_id
    """)

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


@pytest.fixture
def known_passer_ratings() -> dict:
    """
    Known passer ratings for validation.

    Returns:
        Dict mapping player_name to expected passer rating
    """
    return {
        'Patrick Mahomes': 122.3,
        'Aaron Rodgers 2011': 139.9,
        'Perfect QB': 158.3,
        'Joe Burrow': 98.5,
        'Josh Allen': 95.8,
        'Justin Herbert': 78.5,
        'Lamar Jackson': 92.4,
        'Jalen Hurts': 98.7,
        'Kirk Cousins': 88.4,
        'Derek Carr': 76.6,
        'Geno Smith': 82.1,
        'Baker Mayfield': 95.2,
        'Sam Darnold': 62.5,
        'Ryan Tannehill': 78.7,
        'Jacoby Brissett': 56.3,
        'Tua Tagovailoa': 103.4,
        'Trevor Lawrence': 90.5,
        'Mac Jones': 66.8,
        'Justin Fields': 78.9,
        'Bryce Young': 42.3,
    }


@pytest.fixture
def sample_teams() -> list:
    """
    Sample team IDs for testing.

    Returns:
        List of (team_id, team_name, conference, division) tuples
    """
    return [
        # AFC East
        (2, 'Buffalo Bills', 'AFC', 'East'),
        (16, 'Miami Dolphins', 'AFC', 'East'),
        (19, 'New England Patriots', 'AFC', 'East'),
        (18, 'New York Jets', 'AFC', 'East'),

        # AFC North
        (21, 'Baltimore Ravens', 'AFC', 'North'),
        (8, 'Cincinnati Bengals', 'AFC', 'North'),
        (6, 'Cleveland Browns', 'AFC', 'North'),
        (22, 'Pittsburgh Steelers', 'AFC', 'North'),

        # AFC South
        (30, 'Houston Texans', 'AFC', 'South'),
        (12, 'Indianapolis Colts', 'AFC', 'South'),
        (27, 'Jacksonville Jaguars', 'AFC', 'South'),
        (29, 'Tennessee Titans', 'AFC', 'South'),

        # AFC West
        (3, 'Denver Broncos', 'AFC', 'West'),
        (7, 'Kansas City Chiefs', 'AFC', 'West'),
        (15, 'Las Vegas Raiders', 'AFC', 'West'),
        (13, 'Los Angeles Chargers', 'AFC', 'West'),

        # NFC East
        (11, 'Dallas Cowboys', 'NFC', 'East'),
        (18, 'New York Giants', 'NFC', 'East'),
        (20, 'Philadelphia Eagles', 'NFC', 'East'),
        (31, 'Washington Commanders', 'NFC', 'East'),

        # NFC North
        (4, 'Chicago Bears', 'NFC', 'North'),
        (9, 'Detroit Lions', 'NFC', 'North'),
        (10, 'Green Bay Packers', 'NFC', 'North'),
        (14, 'Minnesota Vikings', 'NFC', 'North'),

        # NFC South
        (1, 'Atlanta Falcons', 'NFC', 'South'),
        (5, 'Carolina Panthers', 'NFC', 'South'),
        (15, 'New Orleans Saints', 'NFC', 'South'),
        (28, 'Tampa Bay Buccaneers', 'NFC', 'South'),

        # NFC West
        (32, 'Arizona Cardinals', 'NFC', 'West'),
        (17, 'Los Angeles Rams', 'NFC', 'West'),
        (23, 'San Francisco 49ers', 'NFC', 'West'),
        (24, 'Seattle Seahawks', 'NFC', 'West'),
    ]
