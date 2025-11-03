#!/usr/bin/env python3
"""
Complete trade flow test using real player data from database.

Tests the entire PlayerForPlayerTradeEvent.simulate() flow to identify
where transaction logging is failing.
"""
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from events.trade_events import PlayerForPlayerTradeEvent
from calendar.date_models import Date
from database.player_roster_api import PlayerRosterAPI
import sqlite3

DB_PATH = "data/database/nfl_simulation.db"
DYNASTY_ID = "1st"

def test_complete_trade_flow():
    """Test complete trade execution with real player IDs."""
    print("=" * 80)
    print("COMPLETE TRADE FLOW TEST")
    print("=" * 80)

    # Step 1: Get real player IDs from database
    print("\n1. Fetching real player IDs from database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get 2 players from team 1
    cursor.execute("""
        SELECT player_id, first_name, last_name, positions
        FROM players
        WHERE dynasty_id = ? AND team_id = 1
        LIMIT 2
    """, (DYNASTY_ID,))
    team1_players = cursor.fetchall()

    # Get 2 players from team 2
    cursor.execute("""
        SELECT player_id, first_name, last_name, positions
        FROM players
        WHERE dynasty_id = ? AND team_id = 2
        LIMIT 2
    """, (DYNASTY_ID,))
    team2_players = cursor.fetchall()
    conn.close()

    if not team1_players or not team2_players:
        print("   ❌ ERROR: No players found for teams 1 and 2!")
        return False

    team1_player_ids = [str(p[0]) for p in team1_players]
    team2_player_ids = [str(p[0]) for p in team2_players]

    print(f"   Team 1 players: {', '.join([f'{p[1]} {p[2]} (ID: {p[0]})' for p in team1_players])}")
    print(f"   Team 2 players: {', '.join([f'{p[1]} {p[2]} (ID: {p[0]})' for p in team2_players])}")

    # Step 2: Check player_transactions table BEFORE trade
    print("\n2. Checking player_transactions table BEFORE trade...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM player_transactions")
    count_before = cursor.fetchone()[0]
    conn.close()
    print(f"   Rows before trade: {count_before}")

    # Step 3: Create and execute trade event
    print("\n3. Creating PlayerForPlayerTradeEvent...")
    current_date = Date(year=2024, month=9, day=15)

    trade_event = PlayerForPlayerTradeEvent(
        team1_id=1,
        team2_id=2,
        team1_player_ids=team1_player_ids[:1],  # Trade 1 player each for simplicity
        team2_player_ids=team2_player_ids[:1],
        season=2025,  # FIXED: Use 2025 to match contract years
        event_date=current_date,
        dynasty_id=DYNASTY_ID,
        database_path=DB_PATH
    )

    print(f"   Event created:")
    print(f"   - Team 1 sends: {team1_player_ids[:1]}")
    print(f"   - Team 2 sends: {team2_player_ids[:1]}")
    print(f"   - Dynasty ID: {DYNASTY_ID}")
    print(f"   - Season: 2025")

    # Step 4: Execute trade
    print("\n4. Executing trade event (calling simulate())...")
    print("   Watch for [TRANSACTION_DEBUG] messages below...")
    print("   " + "-" * 76)

    try:
        result = trade_event.simulate()

        print("   " + "-" * 76)
        print(f"\n   Trade result:")
        print(f"   - Success: {result.success}")
        if not result.success:
            print(f"   - Error: {result.error_message}")
        else:
            print(f"   - Event ID: {result.event_id}")
            print(f"   - Timestamp: {result.timestamp}")

    except Exception as e:
        print("   " + "-" * 76)
        print(f"\n   ❌ EXCEPTION during trade execution: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 5: Check player_transactions table AFTER trade
    print("\n5. Checking player_transactions table AFTER trade...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM player_transactions")
    count_after = cursor.fetchone()[0]

    cursor.execute("""
        SELECT transaction_id, player_name, transaction_type, from_team_id, to_team_id
        FROM player_transactions
        ORDER BY created_at DESC
        LIMIT 5
    """)
    recent_transactions = cursor.fetchall()
    conn.close()

    print(f"   Rows after trade: {count_after}")
    print(f"   New transactions: {count_after - count_before}")

    if recent_transactions:
        print(f"\n   Recent transactions:")
        for tx in recent_transactions:
            print(f"   - ID {tx[0]}: {tx[1]} ({tx[2]}) Team {tx[3]}→{tx[4]}")

    # Step 6: Analysis
    print("\n" + "=" * 80)
    if count_after > count_before:
        print("✅ SUCCESS: Transactions were logged!")
        print("=" * 80)
        return True
    else:
        print("❌ FAILURE: NO transactions were logged!")
        print("=" * 80)
        print("\nANALYSIS:")
        if not result.success:
            print(f"- Trade failed validation: {result.error_message}")
            print("- Transaction logging code never executed")
        else:
            print("- Trade succeeded BUT transaction logging failed")
            print("- Likely cause: get_player_by_id() returned None (silent skip)")
            print("- Check [TRANSACTION_DEBUG] output above for details")
        return False

if __name__ == "__main__":
    success = test_complete_trade_flow()
    sys.exit(0 if success else 1)
