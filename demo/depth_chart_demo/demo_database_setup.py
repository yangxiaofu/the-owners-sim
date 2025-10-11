"""
Demo Database Setup for Depth Chart API Demo

Creates an isolated SQLite database with mock data for testing depth chart operations.
"""

import sqlite3
import json
import os


def create_demo_database(db_path="demo.db"):
    """
    Create and populate demo database with mock data.

    Creates:
    - 2 teams (Detroit Lions, Chicago Bears)
    - ~53 players per team
    - Team 1 (Lions): Proper depth charts assigned
    - Team 2 (Bears): All depth_chart_order = 99 (unassigned)
    """
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"🗑️  Removed existing {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"📦 Creating demo database: {db_path}")

    # Create schema
    _create_schema(cursor)

    # Insert dynasty
    _insert_dynasty(cursor)

    # Generate mock players for Team 9 (Detroit Lions)
    print("\n📝 Generating Team 9 (Detroit Lions) - WITH depth charts")
    lions_players = _generate_team_players(team_id=9, team_name="Lions")
    _insert_players(cursor, lions_players, dynasty_id="demo_dynasty", with_depth_chart=True)

    # Generate mock players for Team 3 (Chicago Bears)
    print("\n📝 Generating Team 3 (Chicago Bears) - WITHOUT depth charts (all unassigned)")
    bears_players = _generate_team_players(team_id=3, team_name="Bears")
    _insert_players(cursor, bears_players, dynasty_id="demo_dynasty", with_depth_chart=False)

    conn.commit()
    conn.close()

    print(f"\n✅ Demo database created successfully: {db_path}")
    print(f"   Total players: {len(lions_players) + len(bears_players)}")
    print(f"   Team 9 (Lions): {len(lions_players)} players with proper depth charts")
    print(f"   Team 3 (Bears): {len(bears_players)} players with unassigned depth charts")


def _create_schema(cursor):
    """Create database schema."""
    print("  Creating schema...")

    # Dynasties table
    cursor.execute('''
        CREATE TABLE dynasties (
            dynasty_id TEXT PRIMARY KEY,
            team_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Players table
    cursor.execute('''
        CREATE TABLE players (
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            source_player_id TEXT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            number INTEGER,
            team_id INTEGER NOT NULL,
            positions TEXT NOT NULL,
            attributes TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            years_pro INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (dynasty_id, player_id),
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        )
    ''')

    # Team rosters table
    cursor.execute('''
        CREATE TABLE team_rosters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            depth_chart_order INTEGER DEFAULT 99,
            roster_status TEXT DEFAULT 'active',
            joined_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, team_id, player_id)
        )
    ''')

    print("  ✅ Schema created")


def _insert_dynasty(cursor):
    """Insert demo dynasty."""
    cursor.execute('''
        INSERT INTO dynasties (dynasty_id, team_id)
        VALUES ('demo_dynasty', 9)
    ''')
    print("  ✅ Dynasty 'demo_dynasty' created")


def _generate_team_players(team_id, team_name):
    """
    Generate mock players for a team.

    Returns list of player dicts.
    """
    players = []
    player_id_counter = team_id * 1000  # Lions: 9000+, Bears: 3000+

    # Quarterbacks (3)
    for i in range(1, 4):
        players.append({
            'player_id': player_id_counter,
            'first_name': f'Demo QB{i}',
            'last_name': team_name,
            'number': i,
            'positions': ['quarterback'],
            'attributes': {
                'overall': 90 - (i - 1) * 10,  # 90, 80, 70
                'speed': 75,
                'accuracy': 85,
                'arm_strength': 80,
                'awareness': 85,
                'discipline': 85
            }
        })
        player_id_counter += 1

    # Running Backs (4)
    for i in range(1, 5):
        players.append({
            'player_id': player_id_counter,
            'first_name': f'Demo RB{i}',
            'last_name': team_name,
            'number': 20 + i,
            'positions': ['running_back'],
            'attributes': {
                'overall': 85 - (i - 1) * 5,  # 85, 80, 75, 70
                'speed': 90,
                'strength': 80,
                'agility': 85,
                'hands': 75,
                'awareness': 80,
                'discipline': 80
            }
        })
        player_id_counter += 1

    # Wide Receivers (6)
    for i in range(1, 7):
        players.append({
            'player_id': player_id_counter,
            'first_name': f'Demo WR{i}',
            'last_name': team_name,
            'number': 10 + i,
            'positions': ['wide_receiver'],
            'attributes': {
                'overall': 88 - (i - 1) * 4,  # 88, 84, 80, 76, 72, 68
                'speed': 92,
                'hands': 85,
                'route_running': 80,
                'awareness': 80,
                'discipline': 78
            }
        })
        player_id_counter += 1

    # Tight Ends (3)
    for i in range(1, 4):
        players.append({
            'player_id': player_id_counter,
            'first_name': f'Demo TE{i}',
            'last_name': team_name,
            'number': 80 + i,
            'positions': ['tight_end'],
            'attributes': {
                'overall': 82 - (i - 1) * 5,  # 82, 77, 72
                'speed': 80,
                'hands': 82,
                'blocking': 75,
                'awareness': 78,
                'discipline': 80
            }
        })
        player_id_counter += 1

    # Offensive Line (8)
    ol_positions = ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle', 'guard', 'guard', 'tackle']
    for i, pos in enumerate(ol_positions, 1):
        players.append({
            'player_id': player_id_counter,
            'first_name': f'Demo OL{i}',
            'last_name': team_name,
            'number': 60 + i,
            'positions': [pos],
            'attributes': {
                'overall': 82 - (i - 1) * 3,  # 82, 79, 76, 73...
                'strength': 90,
                'blocking': 85,
                'awareness': 75,
                'discipline': 80
            }
        })
        player_id_counter += 1

    # Defensive Line (6)
    dl_positions = ['defensive_end', 'defensive_end', 'defensive_tackle', 'defensive_tackle', 'nose_tackle', 'defensive_end']
    for i, pos in enumerate(dl_positions, 1):
        players.append({
            'player_id': player_id_counter,
            'first_name': f'Demo DL{i}',
            'last_name': team_name,
            'number': 90 + i,
            'positions': [pos],
            'attributes': {
                'overall': 88 - (i - 1) * 4,  # 88, 84, 80, 76, 72, 68
                'strength': 92,
                'speed': 78,
                'pass_rush': 85,
                'awareness': 75,
                'discipline': 78
            }
        })
        player_id_counter += 1

    # Linebackers (5)
    lb_positions = ['linebacker', 'linebacker', 'linebacker', 'linebacker', 'linebacker']
    for i, pos in enumerate(lb_positions, 1):
        players.append({
            'player_id': player_id_counter,
            'first_name': f'Demo LB{i}',
            'last_name': team_name,
            'number': 50 + i,
            'positions': [pos],
            'attributes': {
                'overall': 85 - (i - 1) * 4,  # 85, 81, 77, 73, 69
                'speed': 85,
                'strength': 80,
                'coverage': 78,
                'awareness': 82,
                'discipline': 80
            }
        })
        player_id_counter += 1

    # Defensive Backs (6)
    db_positions = ['cornerback', 'cornerback', 'cornerback', 'safety', 'safety', 'cornerback']
    for i, pos in enumerate(db_positions, 1):
        players.append({
            'player_id': player_id_counter,
            'first_name': f'Demo DB{i}',
            'last_name': team_name,
            'number': 20 + i,
            'positions': [pos],
            'attributes': {
                'overall': 87 - (i - 1) * 4,  # 87, 83, 79, 75, 71, 67
                'speed': 92,
                'coverage': 85,
                'awareness': 80,
                'discipline': 78
            }
        })
        player_id_counter += 1

    # Special Teams (3)
    st_players = [
        ('kicker', 4, 82),
        ('punter', 8, 78),
        ('long_snapper', 46, 75)
    ]
    for pos, num, ovr in st_players:
        players.append({
            'player_id': player_id_counter,
            'first_name': f'Demo {pos.upper()}',
            'last_name': team_name,
            'number': num,
            'positions': [pos],
            'attributes': {
                'overall': ovr,
                'kick_power': 85 if pos == 'kicker' else 80,
                'kick_accuracy': 80,
                'awareness': 75,
                'discipline': 80
            }
        })
        player_id_counter += 1

    return players


def _insert_players(cursor, players, dynasty_id, with_depth_chart=True):
    """Insert players and team roster entries."""
    # Track depth by position for sequential assignment
    depth_by_position = {}

    for player in players:
        # Insert into players table
        cursor.execute('''
            INSERT INTO players
                (dynasty_id, player_id, source_player_id, first_name, last_name, number,
                 team_id, positions, attributes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dynasty_id,
            player['player_id'],
            f"DEMO_{player['player_id']}",
            player['first_name'],
            player['last_name'],
            player['number'],
            players[0]['player_id'] // 1000,  # Extract team_id from player_id range
            json.dumps(player['positions']),
            json.dumps(player['attributes'])
        ))

        # Determine depth_chart_order
        position = player['positions'][0]

        if with_depth_chart:
            # Assign sequential depth orders (1, 2, 3...)
            if position not in depth_by_position:
                depth_by_position[position] = 1
            depth_order = depth_by_position[position]
            depth_by_position[position] += 1
        else:
            # Assign 99 (unassigned)
            depth_order = 99

        # Insert into team_rosters table
        team_id = players[0]['player_id'] // 1000
        cursor.execute('''
            INSERT INTO team_rosters
                (dynasty_id, team_id, player_id, depth_chart_order)
            VALUES (?, ?, ?, ?)
        ''', (dynasty_id, team_id, player['player_id'], depth_order))

    print(f"  ✅ Inserted {len(players)} players")


if __name__ == "__main__":
    create_demo_database()
