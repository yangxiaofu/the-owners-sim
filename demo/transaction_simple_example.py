"""
Simple TransactionContext Integration Example

A straightforward demonstration of using TransactionContext
with real database operations that work with the existing schema.

Run with:
    PYTHONPATH=src python demo/transaction_simple_example.py
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import DatabaseConnection, TransactionContext


def example_1_simple_insert():
    """Example 1: Simple multi-row insert with auto-commit."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Simple Multi-Row Insert (Auto-Commit)")
    print("="*80)

    db_conn = DatabaseConnection(":memory:")
    db_conn.initialize_database()
    conn = db_conn.get_connection()
    cursor = conn.cursor()

    # Setup test data
    cursor.execute("INSERT INTO dynasties (dynasty_id, dynasty_name, team_id) VALUES ('demo1', 'Demo Dynasty 1', 1)")
    conn.commit()

    print("\nInserting 3 players atomically...")
    with TransactionContext(conn, mode="IMMEDIATE") as tx:
        for i in range(1, 4):
            cursor.execute("""
                INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, attributes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ('demo1', i, f'Player{i}', f'Last{i}', 10+i, 1, '["QB"]', '{"overall": 85}'))
            print(f"   Inserted Player {i}")

    cursor.execute("SELECT COUNT(*) FROM players WHERE dynasty_id = 'demo1'")
    count = cursor.fetchone()[0]
    print(f"\n✓ Success: {count} players in database (auto-committed)")


def example_2_rollback_on_error():
    """Example 2: Automatic rollback on error."""
    print("\n" + "="*80)
    print("EXAMPLE 2: Automatic Rollback on Error")
    print("="*80)

    db_conn = DatabaseConnection(":memory:")
    db_conn.initialize_database()
    conn = db_conn.get_connection()
    cursor = conn.cursor()

    # Setup test data
    cursor.execute("INSERT INTO dynasties (dynasty_id, dynasty_name, team_id) VALUES ('demo2', 'Demo Dynasty 2', 1)")
    conn.commit()

    print("\nAttempting to insert 3 players, but will fail on 3rd...")
    try:
        with TransactionContext(conn, mode="IMMEDIATE") as tx:
            cursor.execute("""
                INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, attributes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ('demo2', 1, 'Player1', 'Last1', 11, 1, '["QB"]', '{"overall": 85}'))
            print("   Inserted Player 1")

            cursor.execute("""
                INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, attributes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ('demo2', 2, 'Player2', 'Last2', 12, 1, '["RB"]', '{"overall": 82}'))
            print("   Inserted Player 2")

            # This will fail - simulating an error
            raise ValueError("Simulated validation error")

    except ValueError as e:
        print(f"   ERROR: {e}")

    cursor.execute("SELECT COUNT(*) FROM players WHERE dynasty_id = 'demo2'")
    count = cursor.fetchone()[0]
    print(f"\n✓ Success: {count} players in database (all rolled back)")


def example_3_update_standings():
    """Example 3: Update standings for multiple teams."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Update Team Standings Atomically")
    print("="*80)

    db_conn = DatabaseConnection(":memory:")
    db_conn.initialize_database()
    conn = db_conn.get_connection()
    cursor = conn.cursor()

    # Setup test data
    cursor.execute("INSERT INTO dynasties (dynasty_id, dynasty_name, team_id) VALUES ('demo3', 'Demo Dynasty 3', 1)")
    cursor.execute("""
        INSERT INTO standings (dynasty_id, team_id, season, season_type, wins, losses, points_for, points_against)
        VALUES ('demo3', 1, 2024, 'regular_season', 5, 3, 180, 150)
    """)
    cursor.execute("""
        INSERT INTO standings (dynasty_id, team_id, season, season_type, wins, losses, points_for, points_against)
        VALUES ('demo3', 2, 2024, 'regular_season', 4, 4, 170, 160)
    """)
    conn.commit()

    print("\nRecording game result: Team 1 (28) vs Team 2 (24)...")
    with TransactionContext(conn, mode="IMMEDIATE") as tx:
        # Update winner (Team 1)
        cursor.execute("""
            UPDATE standings
            SET wins = wins + 1, points_for = points_for + 28, points_against = points_against + 24
            WHERE dynasty_id = 'demo3' AND team_id = 1 AND season = 2024 AND season_type = 'regular_season'
        """)
        print("   Updated Team 1 standings (winner)")

        # Update loser (Team 2)
        cursor.execute("""
            UPDATE standings
            SET losses = losses + 1, points_for = points_for + 24, points_against = points_against + 28
            WHERE dynasty_id = 'demo3' AND team_id = 2 AND season = 2024 AND season_type = 'regular_season'
        """)
        print("   Updated Team 2 standings (loser)")

    # Verify results
    cursor.execute("SELECT wins, losses, points_for, points_against FROM standings WHERE dynasty_id = 'demo3' AND team_id = 1")
    wins, losses, pf, pa = cursor.fetchone()
    print(f"\n✓ Team 1 Final: {wins}-{losses}, PF: {pf}, PA: {pa}")

    cursor.execute("SELECT wins, losses, points_for, points_against FROM standings WHERE dynasty_id = 'demo3' AND team_id = 2")
    wins, losses, pf, pa = cursor.fetchone()
    print(f"✓ Team 2 Final: {wins}-{losses}, PF: {pf}, PA: {pa}")


def example_4_nested_transactions():
    """Example 4: Nested transactions with savepoints."""
    print("\n" + "="*80)
    print("EXAMPLE 4: Nested Transactions (Savepoints)")
    print("="*80)

    db_conn = DatabaseConnection(":memory:")
    db_conn.initialize_database()
    conn = db_conn.get_connection()
    cursor = conn.cursor()

    # Setup test data
    cursor.execute("INSERT INTO dynasties (dynasty_id, dynasty_name, team_id) VALUES ('demo4', 'Demo Dynasty 4', 1)")
    conn.commit()

    print("\nOuter transaction: Adding 2 players...")
    with TransactionContext(conn, mode="IMMEDIATE") as outer_tx:
        cursor.execute("""
            INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, attributes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('demo4', 1, 'Player1', 'Last1', 11, 1, '["QB"]', '{"overall": 90}'))
        print("   Added Player 1 (outer transaction)")

        print("\n   Inner transaction: Trying to add Player 2 (will fail)...")
        try:
            with TransactionContext(conn) as inner_tx:
                cursor.execute("""
                    INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, attributes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, ('demo4', 2, 'Player2', 'Last2', 12, 1, '["RB"]', '{"overall": 88}'))
                print("      Added Player 2 (inner transaction)")
                raise ValueError("Inner transaction validation failed")
        except ValueError as e:
            print(f"      ERROR: {e}")
            print("      Inner transaction rolled back")

        print("\n   Continuing outer transaction: Adding Player 3...")
        cursor.execute("""
            INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, attributes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('demo4', 3, 'Player3', 'Last3', 13, 1, '["WR"]', '{"overall": 85}'))
        print("   Added Player 3 (outer transaction)")

    cursor.execute("SELECT player_id, first_name FROM players WHERE dynasty_id = 'demo4' ORDER BY player_id")
    players = cursor.fetchall()
    print(f"\n✓ Final result: {len(players)} players committed:")
    for player_id, first_name in players:
        print(f"   - Player {player_id}: {first_name}")
    print("   (Player 2 was rolled back, Player 1 and 3 were committed)")


def example_5_explicit_commit():
    """Example 5: Explicit commit with continued operations."""
    print("\n" + "="*80)
    print("EXAMPLE 5: Explicit Commit with Continued Operations")
    print("="*80)

    db_conn = DatabaseConnection(":memory:")
    db_conn.initialize_database()
    conn = db_conn.get_connection()
    cursor = conn.cursor()

    # Setup test data
    cursor.execute("INSERT INTO dynasties (dynasty_id, dynasty_name, team_id) VALUES ('demo5', 'Demo Dynasty 5', 1)")
    conn.commit()

    print("\nInserting Player 1, then explicitly committing...")
    with TransactionContext(conn, mode="IMMEDIATE") as tx:
        cursor.execute("""
            INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, attributes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('demo5', 1, 'Player1', 'Last1', 11, 1, '["QB"]', '{"overall": 92}'))
        print("   Inserted Player 1")

        tx.commit()
        print("   Explicitly committed")

        print("\nContinuing after explicit commit: Inserting Player 2...")
        cursor.execute("""
            INSERT INTO players (dynasty_id, player_id, first_name, last_name, number, team_id, positions, attributes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('demo5', 2, 'Player2', 'Last2', 12, 1, '["WR"]', '{"overall": 88}'))
        print("   Inserted Player 2")

    cursor.execute("SELECT COUNT(*) FROM players WHERE dynasty_id = 'demo5'")
    count = cursor.fetchone()[0]
    print(f"\n✓ Success: {count} players committed (both before and after explicit commit)")


def main():
    """Run all examples."""
    print("\n" + "#"*80)
    print("#" + " "*22 + "TransactionContext Simple Examples" + " "*24 + "#")
    print("#"*80)

    try:
        example_1_simple_insert()
        example_2_rollback_on_error()
        example_3_update_standings()
        example_4_nested_transactions()
        example_5_explicit_commit()

        print("\n" + "="*80)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
