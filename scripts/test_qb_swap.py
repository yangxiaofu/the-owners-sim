#!/usr/bin/env python3
"""
Test script to swap Lamar Jackson with Joe Flacco when initializing a dynasty.

This script:
1. Creates a new dynasty
2. Finds Lamar Jackson (Ravens) and Joe Flacco (Browns) in the database
3. Swaps their team assignments
4. Prints verification

Usage:
    python scripts/test_qb_swap.py
"""

import os
import sys
import sqlite3
import shutil
from pathlib import Path

# Setup paths like main2.py does
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Ensure we're using a fresh test database
TEST_DB_PATH = os.path.join(project_root, "data/database/game_cycle/test_qb_swap.db")


def main():
    # Clean up any existing test database
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        print(f"Removed existing test database: {TEST_DB_PATH}")

    # Also remove WAL files if they exist
    for ext in ["-shm", "-wal"]:
        wal_path = TEST_DB_PATH + ext
        if os.path.exists(wal_path):
            os.remove(wal_path)

    # Import after path setup
    from game_cycle.services.initialization_service import GameCycleInitializer
    import uuid

    # Initialize dynasty (let's say user picks Ravens - team 5)
    user_team_id = 5  # Baltimore Ravens
    dynasty_id = f"qbswap_{uuid.uuid4().hex[:8]}"
    season = 2025

    print("\n=== STEP 1: Initializing Dynasty ===")
    print(f"Creating dynasty: {dynasty_id}")
    init_service = GameCycleInitializer(
        db_path=TEST_DB_PATH,
        dynasty_id=dynasty_id,
        season=season
    )
    success = init_service.initialize_dynasty(team_id=user_team_id)

    if not success:
        print("ERROR: Failed to initialize dynasty!")
        return 1
    print(f"Dynasty created: {dynasty_id}")

    # Now connect and find the players
    print("\n=== STEP 2: Finding Players ===")
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find Lamar Jackson (originally Ravens, team 5)
    cursor.execute("""
        SELECT player_id, first_name, last_name, team_id
        FROM players
        WHERE dynasty_id = ? AND first_name = 'Lamar' AND last_name = 'Jackson'
    """, (dynasty_id,))
    lamar = cursor.fetchone()

    if not lamar:
        print("ERROR: Lamar Jackson not found!")
        return 1
    print(f"Found Lamar Jackson: player_id={lamar['player_id']}, team_id={lamar['team_id']}")

    # Find Joe Flacco (originally Browns, team 7)
    cursor.execute("""
        SELECT player_id, first_name, last_name, team_id
        FROM players
        WHERE dynasty_id = ? AND first_name = 'Joe' AND last_name = 'Flacco'
    """, (dynasty_id,))
    flacco = cursor.fetchone()

    if not flacco:
        print("ERROR: Joe Flacco not found!")
        return 1
    print(f"Found Joe Flacco: player_id={flacco['player_id']}, team_id={flacco['team_id']}")

    lamar_id = lamar['player_id']
    flacco_id = flacco['player_id']
    ravens_team_id = 5
    browns_team_id = 7

    # Swap teams
    print("\n=== STEP 3: Swapping Teams ===")

    # Update Lamar to Browns
    cursor.execute("""
        UPDATE players SET team_id = ? WHERE dynasty_id = ? AND player_id = ?
    """, (browns_team_id, dynasty_id, lamar_id))
    print(f"Moved Lamar Jackson to Browns (team {browns_team_id})")

    # Update Flacco to Ravens
    cursor.execute("""
        UPDATE players SET team_id = ? WHERE dynasty_id = ? AND player_id = ?
    """, (ravens_team_id, dynasty_id, flacco_id))
    print(f"Moved Joe Flacco to Ravens (team {ravens_team_id})")

    # Update team_rosters table as well
    cursor.execute("""
        UPDATE team_rosters SET team_id = ? WHERE dynasty_id = ? AND player_id = ?
    """, (browns_team_id, dynasty_id, lamar_id))
    cursor.execute("""
        UPDATE team_rosters SET team_id = ? WHERE dynasty_id = ? AND player_id = ?
    """, (ravens_team_id, dynasty_id, flacco_id))
    print("Updated team_rosters table")

    # Update contracts table if it exists
    cursor.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='contracts'
    """)
    if cursor.fetchone():
        cursor.execute("""
            UPDATE contracts SET team_id = ? WHERE dynasty_id = ? AND player_id = ?
        """, (browns_team_id, dynasty_id, lamar_id))
        cursor.execute("""
            UPDATE contracts SET team_id = ? WHERE dynasty_id = ? AND player_id = ?
        """, (ravens_team_id, dynasty_id, flacco_id))
        print("Updated contracts table")

    conn.commit()

    # Verify the swap
    print("\n=== STEP 4: Verification ===")

    cursor.execute("""
        SELECT p.player_id, p.first_name, p.last_name, p.team_id,
               (SELECT name FROM teams t WHERE t.team_id = p.team_id) as team_name
        FROM players p
        WHERE dynasty_id = ? AND (
            (first_name = 'Lamar' AND last_name = 'Jackson') OR
            (first_name = 'Joe' AND last_name = 'Flacco')
        )
    """, (dynasty_id,))

    print("\nAfter swap:")
    for row in cursor.fetchall():
        print(f"  {row['first_name']} {row['last_name']}: team_id={row['team_id']} ({row['team_name']})")

    # Show Ravens QB roster
    print("\n=== Ravens QB Roster ===")
    cursor.execute("""
        SELECT p.first_name, p.last_name, p.positions
        FROM players p
        WHERE p.dynasty_id = ? AND p.team_id = 5 AND p.positions LIKE '%quarterback%'
    """, (dynasty_id,))
    for row in cursor.fetchall():
        print(f"  {row['first_name']} {row['last_name']} - {row['positions']}")

    # Show Browns QB roster
    print("\n=== Browns QB Roster ===")
    cursor.execute("""
        SELECT p.first_name, p.last_name, p.positions
        FROM players p
        WHERE p.dynasty_id = ? AND p.team_id = 7 AND p.positions LIKE '%quarterback%'
    """, (dynasty_id,))
    for row in cursor.fetchall():
        print(f"  {row['first_name']} {row['last_name']} - {row['positions']}")

    conn.close()

    print("\n=== SUCCESS! ===")
    print(f"Test database created at: {TEST_DB_PATH}")
    print("You can now run 'python main2.py' and load this database to play with the swapped QBs.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
