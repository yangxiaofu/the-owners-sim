#!/usr/bin/env python3
"""
Database verification script for player_transactions table.
Checks if table exists, has data, and can be queried.
"""
import sqlite3
from pathlib import Path

DB_PATH = "data/database/nfl_simulation.db"

def verify_player_transactions():
    print("=" * 80)
    print("PLAYER TRANSACTIONS TABLE DIAGNOSTIC")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Check if table exists
    print("\n1. Checking if player_transactions table exists...")
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='player_transactions'
    """)
    table_exists = cursor.fetchone()
    print(f"   Table exists: {table_exists is not None}")

    if not table_exists:
        print("   ❌ ERROR: player_transactions table does NOT exist!")
        print("   Run migration 003_player_transactions_table.sql")
        conn.close()
        return

    # 2. Get table schema
    print("\n2. Table schema:")
    cursor.execute("PRAGMA table_info(player_transactions)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"   {col[1]} ({col[2]})")

    # 3. Count total rows (all dynasties)
    print("\n3. Total rows in table (all dynasties):")
    cursor.execute("SELECT COUNT(*) FROM player_transactions")
    total_count = cursor.fetchone()[0]
    print(f"   Total rows: {total_count}")

    # 4. Count by dynasty
    print("\n4. Rows per dynasty:")
    cursor.execute("""
        SELECT dynasty_id, COUNT(*)
        FROM player_transactions
        GROUP BY dynasty_id
    """)
    dynasty_counts = cursor.fetchall()
    if dynasty_counts:
        for dynasty_id, count in dynasty_counts:
            print(f"   {dynasty_id}: {count} transactions")
    else:
        print("   No transactions found in any dynasty")

    # 5. Show recent transactions
    print("\n5. Most recent 5 transactions:")
    cursor.execute("""
        SELECT transaction_id, dynasty_id, transaction_type,
               player_name, from_team_id, to_team_id, transaction_date
        FROM player_transactions
        ORDER BY created_at DESC
        LIMIT 5
    """)
    recent = cursor.fetchall()
    if recent:
        for row in recent:
            print(f"   ID={row[0]} | {row[2]} | {row[3]} | {row[4]}→{row[5]} | {row[6]}")
    else:
        print("   No transactions found")

    # 6. Check specific dynasty (ask user)
    print("\n6. Checking 'default' dynasty:")
    cursor.execute("""
        SELECT COUNT(*) FROM player_transactions
        WHERE dynasty_id = 'default'
    """)
    default_count = cursor.fetchone()[0]
    print(f"   'default' dynasty: {default_count} transactions")

    # 7. Check players table
    print("\n7. Players table verification:")
    cursor.execute("SELECT COUNT(*) FROM players")
    players_count = cursor.fetchone()[0]
    print(f"   Total players: {players_count}")

    cursor.execute("SELECT COUNT(DISTINCT dynasty_id) FROM players")
    dynasties_count = cursor.fetchone()[0]
    print(f"   Dynasties with players: {dynasties_count}")

    # 8. Show distinct dynasty IDs in players table
    print("\n8. Dynasty IDs in players table:")
    cursor.execute("SELECT DISTINCT dynasty_id FROM players LIMIT 10")
    dynasty_ids = cursor.fetchall()
    for dynasty_id_tuple in dynasty_ids:
        print(f"   - {dynasty_id_tuple[0]}")

    # 9. Check cap_transactions table for comparison
    print("\n9. Cap transactions table (for comparison):")
    cursor.execute("SELECT COUNT(*) FROM cap_transactions")
    cap_count = cursor.fetchone()[0]
    print(f"   Total cap_transactions rows: {cap_count}")

    if cap_count > 0:
        cursor.execute("""
            SELECT COUNT(*) FROM cap_transactions
            WHERE transaction_type = 'TRADE'
        """)
        trade_count = cursor.fetchone()[0]
        print(f"   Trade cap_transactions: {trade_count}")

    conn.close()
    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print("\nNEXT STEPS:")
    print("1. Run the UI and execute a trade")
    print("2. Watch terminal output for [TRANSACTION_DEBUG] messages")
    print("3. Run this script again to see if transactions were logged")

if __name__ == "__main__":
    verify_player_transactions()
