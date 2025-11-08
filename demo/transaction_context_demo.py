"""
TransactionContext Usage Demo

Demonstrates real-world usage patterns for atomic database transactions
in the NFL simulation system.

Run with:
    PYTHONPATH=src python demo/transaction_context_demo.py
"""

import sqlite3
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.transaction_context import TransactionContext, transaction


def demo_basic_transaction():
    """Demonstrate basic transaction usage."""
    print("\n" + "="*80)
    print("DEMO 1: Basic Transaction - Auto Commit/Rollback")
    print("="*80)

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Setup test table
    cursor.execute('''
        CREATE TABLE players (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            team TEXT,
            salary INTEGER
        )
    ''')

    print("\n1. Successful transaction (auto-commit):")
    with TransactionContext(conn) as tx:
        print(f"   Transaction state: {tx.state.value}")
        cursor.execute("INSERT INTO players (name, team, salary) VALUES (?, ?, ?)",
                      ("Patrick Mahomes", "Kansas City Chiefs", 45000000))
        cursor.execute("INSERT INTO players (name, team, salary) VALUES (?, ?, ?)",
                      ("Joe Burrow", "Cincinnati Bengals", 55000000))
        print("   Inserted 2 players")

    cursor.execute("SELECT COUNT(*) FROM players")
    print(f"   Players in database: {cursor.fetchone()[0]}")

    print("\n2. Failed transaction (auto-rollback):")
    try:
        with TransactionContext(conn) as tx:
            print(f"   Transaction state: {tx.state.value}")
            cursor.execute("INSERT INTO players (name, team, salary) VALUES (?, ?, ?)",
                          ("Josh Allen", "Buffalo Bills", 43000000))
            print("   Inserted 1 player")
            raise Exception("Simulated error (e.g., validation failure)")
    except Exception as e:
        print(f"   Exception occurred: {e}")

    cursor.execute("SELECT COUNT(*) FROM players")
    print(f"   Players in database: {cursor.fetchone()[0]} (rollback successful)")

    conn.close()


def demo_transaction_modes():
    """Demonstrate different transaction isolation modes."""
    print("\n" + "="*80)
    print("DEMO 2: Transaction Modes - DEFERRED, IMMEDIATE, EXCLUSIVE")
    print("="*80)

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE salary_cap (
            team_id INTEGER PRIMARY KEY,
            cap_space INTEGER,
            cap_used INTEGER
        )
    ''')

    print("\n1. DEFERRED mode (default - lock on first write):")
    with TransactionContext(conn, mode="DEFERRED") as tx:
        print(f"   Mode: {tx.mode}")
        cursor.execute("INSERT INTO salary_cap VALUES (1, 224800000, 180000000)")
        print("   Updated salary cap data")

    print("\n2. IMMEDIATE mode (immediate write lock):")
    with TransactionContext(conn, mode="IMMEDIATE") as tx:
        print(f"   Mode: {tx.mode}")
        cursor.execute("UPDATE salary_cap SET cap_used = cap_used + 5000000 WHERE team_id = 1")
        print("   Updated salary cap (locked immediately)")

    print("\n3. EXCLUSIVE mode (exclusive lock, blocks all other connections):")
    with TransactionContext(conn, mode="EXCLUSIVE") as tx:
        print(f"   Mode: {tx.mode}")
        cursor.execute("DELETE FROM salary_cap WHERE team_id = 1")
        print("   Deleted salary cap record (exclusive access)")

    conn.close()


def demo_nested_transactions():
    """Demonstrate nested transaction support using savepoints."""
    print("\n" + "="*80)
    print("DEMO 3: Nested Transactions - Savepoints")
    print("="*80)

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE contracts (
            id INTEGER PRIMARY KEY,
            player_name TEXT,
            total_value INTEGER,
            status TEXT
        )
    ''')

    print("\n1. Nested transaction - both commit:")
    with TransactionContext(conn) as outer_tx:
        print(f"   Outer transaction: {outer_tx.state.value}")
        cursor.execute("INSERT INTO contracts VALUES (1, 'Player A', 10000000, 'active')")

        with TransactionContext(conn) as inner_tx:
            print(f"   Inner transaction (nested): {inner_tx.is_nested}, savepoint: {inner_tx.savepoint_name}")
            cursor.execute("INSERT INTO contracts VALUES (2, 'Player B', 8000000, 'active')")
            print("   Inserted Player B in nested transaction")

        print("   Inner transaction committed, continuing outer transaction")
        cursor.execute("INSERT INTO contracts VALUES (3, 'Player C', 12000000, 'active')")

    cursor.execute("SELECT COUNT(*) FROM contracts")
    print(f"   Total contracts: {cursor.fetchone()[0]}")

    print("\n2. Nested transaction - inner rollback, outer commit:")
    try:
        with TransactionContext(conn) as outer_tx:
            cursor.execute("INSERT INTO contracts VALUES (4, 'Player D', 15000000, 'active')")

            try:
                with TransactionContext(conn) as inner_tx:
                    cursor.execute("INSERT INTO contracts VALUES (5, 'Player E', 20000000, 'active')")
                    print("   Inserted Player E in nested transaction")
                    raise ValueError("Contract validation failed")
            except ValueError as e:
                print(f"   Inner transaction failed: {e}")

            cursor.execute("INSERT INTO contracts VALUES (6, 'Player F', 9000000, 'active')")
            print("   Outer transaction continues after inner rollback")

    except Exception as e:
        print(f"   Unexpected error: {e}")

    cursor.execute("SELECT COUNT(*) FROM contracts")
    print(f"   Total contracts: {cursor.fetchone()[0]} (Player D and F added, Player E rolled back)")

    conn.close()


def demo_real_world_scenario():
    """Demonstrate a real-world NFL simulation scenario."""
    print("\n" + "="*80)
    print("DEMO 4: Real-World Scenario - Player Trade Transaction")
    print("="*80)

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Setup schema
    cursor.execute('''
        CREATE TABLE players (
            id INTEGER PRIMARY KEY,
            name TEXT,
            team_id INTEGER,
            salary INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE team_cap (
            team_id INTEGER PRIMARY KEY,
            cap_space INTEGER,
            cap_used INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            from_team INTEGER,
            to_team INTEGER,
            trade_date TEXT
        )
    ''')

    # Initialize data
    cursor.execute("INSERT INTO players VALUES (1, 'Star QB', 1, 30000000)")
    cursor.execute("INSERT INTO players VALUES (2, 'Backup QB', 2, 2000000)")
    cursor.execute("INSERT INTO team_cap VALUES (1, 224800000, 200000000)")
    cursor.execute("INSERT INTO team_cap VALUES (2, 224800000, 180000000)")
    conn.commit()

    print("\n1. Successful trade transaction:")
    print("   Trading 'Star QB' from Team 1 to Team 2")

    player_id = 1
    from_team = 1
    to_team = 2
    player_salary = 30000000

    with TransactionContext(conn, mode="IMMEDIATE") as tx:
        # Step 1: Check cap space
        cursor.execute("SELECT cap_space, cap_used FROM team_cap WHERE team_id = ?", (to_team,))
        cap_space, cap_used = cursor.fetchone()

        if cap_space - cap_used < player_salary:
            print("   ERROR: Insufficient cap space!")
            tx.rollback()
        else:
            # Step 2: Update player's team
            cursor.execute("UPDATE players SET team_id = ? WHERE id = ?", (to_team, player_id))
            print(f"   Updated player {player_id} team assignment")

            # Step 3: Update cap space
            cursor.execute("UPDATE team_cap SET cap_used = cap_used - ? WHERE team_id = ?",
                          (player_salary, from_team))
            cursor.execute("UPDATE team_cap SET cap_used = cap_used + ? WHERE team_id = ?",
                          (player_salary, to_team))
            print(f"   Updated cap space for both teams")

            # Step 4: Record trade history
            cursor.execute("INSERT INTO trade_history (player_id, from_team, to_team, trade_date) VALUES (?, ?, ?, date('now'))",
                          (player_id, from_team, to_team))
            print(f"   Recorded trade in history")

            print("   TRADE SUCCESSFUL - All changes committed atomically")

    # Verify results
    cursor.execute("SELECT team_id FROM players WHERE id = ?", (player_id,))
    print(f"   Player now on Team: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM trade_history")
    print(f"   Trade history records: {cursor.fetchone()[0]}")

    print("\n2. Failed trade transaction (insufficient cap space):")
    print("   Attempting to trade 'Backup QB' from Team 2 to Team 1 (insufficient cap)")

    player_id = 2
    from_team = 2
    to_team = 1
    player_salary = 2000000

    # Manually set Team 1 cap to insufficient
    cursor.execute("UPDATE team_cap SET cap_used = 224500000 WHERE team_id = 1")
    conn.commit()

    try:
        with TransactionContext(conn, mode="IMMEDIATE") as tx:
            cursor.execute("SELECT cap_space, cap_used FROM team_cap WHERE team_id = ?", (to_team,))
            cap_space, cap_used = cursor.fetchone()

            available_cap = cap_space - cap_used
            print(f"   Team {to_team} available cap: ${available_cap:,}")
            print(f"   Player salary: ${player_salary:,}")

            if available_cap < player_salary:
                print("   TRADE BLOCKED - Insufficient cap space!")
                raise ValueError(f"Insufficient cap space: need ${player_salary:,}, have ${available_cap:,}")

            # This won't execute due to cap check
            cursor.execute("UPDATE players SET team_id = ? WHERE id = ?", (to_team, player_id))

    except ValueError as e:
        print(f"   Transaction rolled back: {e}")

    # Verify rollback
    cursor.execute("SELECT team_id FROM players WHERE id = ?", (player_id,))
    print(f"   Player still on Team: {cursor.fetchone()[0]} (rollback successful)")

    conn.close()


def demo_explicit_commit_rollback():
    """Demonstrate explicit commit and rollback within transaction."""
    print("\n" + "="*80)
    print("DEMO 5: Explicit Commit/Rollback - Conditional Logic")
    print("="*80)

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE draft_picks (
            pick_number INTEGER PRIMARY KEY,
            team_id INTEGER,
            player_name TEXT,
            validated BOOLEAN
        )
    ''')

    print("\n1. Conditional commit based on validation:")
    with TransactionContext(conn) as tx:
        # Insert draft pick
        cursor.execute("INSERT INTO draft_picks VALUES (1, 15, 'Rookie QB', 0)")
        print("   Inserted draft pick")

        # Validate pick
        cursor.execute("SELECT player_name FROM draft_picks WHERE pick_number = 1")
        player_name = cursor.fetchone()[0]

        if "QB" in player_name:
            cursor.execute("UPDATE draft_picks SET validated = 1 WHERE pick_number = 1")
            tx.commit()
            print("   Pick validated and committed")
        else:
            tx.rollback()
            print("   Pick invalid, rolling back")

        # Can continue after explicit commit
        cursor.execute("INSERT INTO draft_picks VALUES (2, 16, 'Star WR', 1)")
        print("   Added another pick after explicit commit")

    cursor.execute("SELECT COUNT(*) FROM draft_picks")
    print(f"   Total draft picks: {cursor.fetchone()[0]}")

    conn.close()


def demo_convenience_function():
    """Demonstrate the transaction() convenience function."""
    print("\n" + "="*80)
    print("DEMO 6: Convenience Function - Simplified Syntax")
    print("="*80)

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE game_results (
            game_id INTEGER PRIMARY KEY,
            home_team INTEGER,
            away_team INTEGER,
            home_score INTEGER,
            away_score INTEGER
        )
    ''')

    print("\n1. Using transaction() convenience function:")
    with transaction(conn, mode="IMMEDIATE") as tx:
        print(f"   Transaction type: {type(tx).__name__}")
        print(f"   Transaction mode: {tx.mode}")
        cursor.execute("INSERT INTO game_results VALUES (1, 7, 9, 28, 24)")
        cursor.execute("INSERT INTO game_results VALUES (2, 12, 15, 31, 27)")
        print("   Inserted 2 game results")

    cursor.execute("SELECT COUNT(*) FROM game_results")
    print(f"   Games in database: {cursor.fetchone()[0]}")

    print("\n2. Default mode (DEFERRED):")
    with transaction(conn) as tx:
        print(f"   Transaction mode: {tx.mode}")
        cursor.execute("INSERT INTO game_results VALUES (3, 20, 22, 35, 17)")
        print("   Inserted 1 game result")

    cursor.execute("SELECT COUNT(*) FROM game_results")
    print(f"   Games in database: {cursor.fetchone()[0]}")

    conn.close()


def main():
    """Run all transaction context demos."""
    print("\n" + "#"*80)
    print("#" + " "*78 + "#")
    print("#" + " "*20 + "TransactionContext Usage Demo" + " "*29 + "#")
    print("#" + " "*78 + "#")
    print("#"*80)

    try:
        demo_basic_transaction()
        demo_transaction_modes()
        demo_nested_transactions()
        demo_real_world_scenario()
        demo_explicit_commit_rollback()
        demo_convenience_function()

        print("\n" + "="*80)
        print("ALL DEMOS COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n\nERROR in demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
