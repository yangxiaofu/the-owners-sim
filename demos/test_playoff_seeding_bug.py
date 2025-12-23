#!/usr/bin/env python3
"""
Diagnostic script to test playoff bracket seeding flow.

This tests the suspected bug where Divisional matchups are empty after Wild Card
because the database connection might not see recently committed winners.

Run with: python demos/test_playoff_seeding_bug.py
"""

import os
import sqlite3
import tempfile


def setup_test_database():
    """Create a temporary test database with playoff bracket schema."""
    temp_fd, temp_path = tempfile.mkstemp(suffix='.db')
    os.close(temp_fd)

    conn = sqlite3.connect(temp_path)
    conn.execute("PRAGMA journal_mode = WAL")  # Enable WAL mode like production
    conn.execute('''
        CREATE TABLE playoff_bracket (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            round_name TEXT NOT NULL CHECK(round_name IN ('wild_card', 'divisional', 'conference', 'super_bowl')),
            conference TEXT NOT NULL CHECK(conference IN ('AFC', 'NFC', 'SUPER_BOWL')),
            game_number INTEGER NOT NULL,
            higher_seed INTEGER NOT NULL,
            lower_seed INTEGER NOT NULL,
            winner INTEGER,
            home_score INTEGER,
            away_score INTEGER,
            UNIQUE(dynasty_id, season, round_name, conference, game_number)
        )
    ''')
    conn.commit()
    conn.close()

    return temp_path


def insert_matchup(conn, dynasty_id, season, round_name, conference, game_num, higher, lower):
    """Insert a matchup into playoff_bracket."""
    conn.execute(
        """INSERT INTO playoff_bracket (dynasty_id, season, round_name, conference, game_number, higher_seed, lower_seed)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (dynasty_id, season, round_name, conference, game_num, higher, lower)
    )
    conn.commit()


def update_result(conn, dynasty_id, season, round_name, conference, game_num, home_score, away_score, winner):
    """Update a matchup with game result."""
    conn.execute(
        """UPDATE playoff_bracket
           SET home_score = ?, away_score = ?, winner = ?
           WHERE dynasty_id = ? AND season = ? AND round_name = ? AND conference = ? AND game_number = ?""",
        (home_score, away_score, winner, dynasty_id, season, round_name, conference, game_num)
    )
    conn.commit()


def get_round_winners(conn, dynasty_id, season, round_name, conference):
    """Get winners from a playoff round."""
    cursor = conn.execute(
        """SELECT winner FROM playoff_bracket
           WHERE dynasty_id = ? AND season = ? AND round_name = ?
                 AND conference = ? AND winner IS NOT NULL""",
        (dynasty_id, season, round_name, conference)
    )
    return [row[0] for row in cursor.fetchall()]


def test_seeding_flow(db_path: str):
    """
    Test the exact flow that happens during playoff progression:
    1. Seed Wild Card matchups with connection 1
    2. Update bracket with winners with connection 2
    3. Query for winners with connection 3 (simulating divisional seeding)
    """
    dynasty_id = "TestDynasty"
    season = 2025

    print("\n" + "="*70)
    print("TEST: Playoff Seeding Database Connection Issue")
    print("="*70)

    # Step 1: Seed Wild Card matchups (using connection 1)
    print("\n[STEP 1] Seeding Wild Card matchups with CONNECTION 1...")
    conn1 = sqlite3.connect(db_path)
    conn1.execute("PRAGMA journal_mode = WAL")

    afc_matchups = [(2, 7), (3, 6), (4, 5)]
    nfc_matchups = [(22, 27), (23, 26), (24, 25)]

    for i, (higher, lower) in enumerate(afc_matchups, 1):
        insert_matchup(conn1, dynasty_id, season, "wild_card", "AFC", i, higher, lower)
        print(f"  Inserted AFC game {i}: Team {higher} vs Team {lower}")

    for i, (higher, lower) in enumerate(nfc_matchups, 1):
        insert_matchup(conn1, dynasty_id, season, "wild_card", "NFC", i, higher, lower)
        print(f"  Inserted NFC game {i}: Team {higher} vs Team {lower}")

    conn1.close()
    print("  Connection 1 closed.")

    # Step 2: Update bracket with game results (using connection 2)
    print("\n[STEP 2] Updating bracket with winners using CONNECTION 2...")
    conn2 = sqlite3.connect(db_path)
    conn2.execute("PRAGMA journal_mode = WAL")

    afc_winners = [(1, 28, 21, 2), (2, 24, 17, 3), (3, 21, 24, 5)]
    for game_num, home_score, away_score, winner in afc_winners:
        update_result(conn2, dynasty_id, season, "wild_card", "AFC", game_num, home_score, away_score, winner)
        print(f"  Updated AFC game {game_num}: winner={winner}")

    nfc_winners = [(1, 31, 21, 22), (2, 27, 20, 23), (3, 17, 24, 25)]
    for game_num, home_score, away_score, winner in nfc_winners:
        update_result(conn2, dynasty_id, season, "wild_card", "NFC", game_num, home_score, away_score, winner)
        print(f"  Updated NFC game {game_num}: winner={winner}")

    conn2.close()
    print("  Connection 2 closed.")

    # Step 3: Query for winners using NEW connection 3
    print("\n[STEP 3] Querying for winners using CONNECTION 3...")
    conn3 = sqlite3.connect(db_path)
    conn3.execute("PRAGMA journal_mode = WAL")

    afc_winners_found = get_round_winners(conn3, dynasty_id, season, "wild_card", "AFC")
    nfc_winners_found = get_round_winners(conn3, dynasty_id, season, "wild_card", "NFC")

    print(f"\n  AFC Wild Card winners found: {afc_winners_found}")
    print(f"  NFC Wild Card winners found: {nfc_winners_found}")

    conn3.close()

    # Expected: AFC = [2, 3, 5], NFC = [22, 23, 25]
    expected_afc = {2, 3, 5}
    expected_nfc = {22, 23, 25}

    afc_ok = set(afc_winners_found) == expected_afc
    nfc_ok = set(nfc_winners_found) == expected_nfc

    print("\n" + "="*70)
    if afc_ok and nfc_ok:
        print("RESULT: SUCCESS - Winners are visible to new connections")
        print("The database connection issue is NOT the root cause.")
        print("\nThis means the bug is likely elsewhere:")
        print("  - Check if seeding is called before games finish")
        print("  - Check if there's a data mismatch (wrong dynasty_id or season)")
        print("  - Check the actual production code flow with added logging")
    else:
        print("RESULT: FAILURE - Winners NOT visible to new connections!")
        print(f"  Expected AFC: {expected_afc}, Got: {set(afc_winners_found)}")
        print(f"  Expected NFC: {expected_nfc}, Got: {set(nfc_winners_found)}")
        print("This confirms the database connection timing bug!")
    print("="*70)

    return afc_ok and nfc_ok


def test_same_connection():
    """Test if same connection sees its own writes."""
    print("\n" + "="*70)
    print("TEST: Same Connection Visibility")
    print("="*70)

    temp_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(temp_fd)

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute('''
            CREATE TABLE test (id INTEGER PRIMARY KEY, val INTEGER)
        ''')
        conn.execute("INSERT INTO test (val) VALUES (42)")
        conn.commit()

        cursor = conn.execute("SELECT val FROM test WHERE id = 1")
        result = cursor.fetchone()
        print(f"  Same connection read: {result}")
        conn.close()

        # Read with new connection
        conn2 = sqlite3.connect(db_path)
        cursor2 = conn2.execute("SELECT val FROM test WHERE id = 1")
        result2 = cursor2.fetchone()
        print(f"  New connection read: {result2}")
        conn2.close()

        if result and result[0] == 42 and result2 and result2[0] == 42:
            print("  PASS: Both connections see the data")
        else:
            print("  FAIL: Data visibility issue")
    finally:
        os.unlink(db_path)


def main():
    # Run basic test first
    test_same_connection()

    # Create test database
    db_path = setup_test_database()
    print(f"\nUsing temporary database: {db_path}")

    try:
        # Run main test
        test_seeding_flow(db_path)

        # Verify data in database
        print("\n[EXTRA] Direct database dump:")
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT round_name, conference, game_number, higher_seed, lower_seed, winner, home_score, away_score FROM playoff_bracket"
        )
        for row in cursor.fetchall():
            print(f"  {row}")
        conn.close()

    finally:
        os.unlink(db_path)
        print(f"\nCleaned up: {db_path}")


if __name__ == "__main__":
    main()
