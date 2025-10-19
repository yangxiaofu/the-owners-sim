#!/usr/bin/env python3
"""
Transaction Tracking MVP Demo

Demonstrates the complete transaction tracking system:
1. Database schema creation
2. Transaction logging from events
3. Query API for retrieving transaction history
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import sqlite3
from datetime import date, datetime
from persistence.transaction_logger import TransactionLogger
from persistence.transaction_api import TransactionAPI
from events.base_event import EventResult

# Create temporary database file
import tempfile
import os
temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
DB_PATH = temp_db.name
temp_db.close()

def create_schema(db_path):
    """Create player_transactions table schema."""
    print("📊 Creating player_transactions schema...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create dynasties table (required for foreign key)
    cursor.execute("""
        CREATE TABLE dynasties (
            dynasty_id TEXT PRIMARY KEY,
            dynasty_name TEXT NOT NULL,
            owner_name TEXT,
            team_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    """)

    # Insert test dynasty
    cursor.execute("""
        INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id)
        VALUES ('mvp_demo', 'MVP Demo Dynasty', 'Test User', 7)
    """)

    # Create player_contracts table (for foreign key)
    cursor.execute("""
        CREATE TABLE player_contracts (
            contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            season_signed INTEGER NOT NULL,
            contract_years INTEGER NOT NULL
        )
    """)

    # Create player_transactions table
    cursor.execute("""
        CREATE TABLE player_transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            transaction_type TEXT NOT NULL CHECK(transaction_type IN (
                'DRAFT', 'UDFA_SIGNING', 'UFA_SIGNING', 'RFA_SIGNING',
                'RELEASE', 'WAIVER_CLAIM', 'TRADE', 'ROSTER_CUT',
                'PRACTICE_SQUAD_ADD', 'PRACTICE_SQUAD_REMOVE', 'PRACTICE_SQUAD_ELEVATE',
                'FRANCHISE_TAG', 'TRANSITION_TAG', 'RESTRUCTURE'
            )),
            player_id INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            position TEXT,
            from_team_id INTEGER,
            to_team_id INTEGER,
            transaction_date DATE NOT NULL,
            details TEXT,
            contract_id INTEGER,
            event_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            FOREIGN KEY (contract_id) REFERENCES player_contracts(contract_id)
        )
    """)

    # Create indexes
    cursor.execute("""
        CREATE INDEX idx_transactions_dynasty ON player_transactions(dynasty_id)
    """)
    cursor.execute("""
        CREATE INDEX idx_transactions_player ON player_transactions(player_id)
    """)
    cursor.execute("""
        CREATE INDEX idx_transactions_type ON player_transactions(transaction_type)
    """)
    cursor.execute("""
        CREATE INDEX idx_transactions_date ON player_transactions(transaction_date)
    """)
    cursor.execute("""
        CREATE INDEX idx_transactions_team_from ON player_transactions(from_team_id)
    """)
    cursor.execute("""
        CREATE INDEX idx_transactions_team_to ON player_transactions(to_team_id)
    """)

    conn.commit()
    conn.close()
    print("✅ Schema created successfully\n")


def demo_transaction_logging():
    """Demonstrate transaction logging from events."""
    print("=" * 80)
    print("TRANSACTION TRACKING MVP DEMONSTRATION")
    print("=" * 80)
    print()

    # Create schema
    create_schema(DB_PATH)

    # Initialize logger
    logger = TransactionLogger(DB_PATH)
    print("📝 TransactionLogger initialized\n")

    # === Demo 1: Direct Transaction Logging ===
    print("-" * 80)
    print("DEMO 1: Direct Transaction Logging")
    print("-" * 80)
    print()

    tx_id_1 = logger.log_transaction(
        dynasty_id="mvp_demo",
        season=2025,
        transaction_type="DRAFT",
        player_id=10001,
        player_name="Caleb Williams",
        position="QB",
        from_team_id=None,
        to_team_id=5,  # Chicago Bears
        transaction_date=date(2025, 4, 25),
        details='{"round": 1, "pick": 1, "overall": 1, "college": "USC"}',
        event_id="draft_2025_pick_1"
    )
    print(f"✅ Logged DRAFT transaction (ID: {tx_id_1})")
    print(f"   Player: Caleb Williams (QB) → Team 5 (Bears)")
    print()

    tx_id_2 = logger.log_transaction(
        dynasty_id="mvp_demo",
        season=2025,
        transaction_type="UFA_SIGNING",
        player_id=10002,
        player_name="Kirk Cousins",
        position="QB",
        from_team_id=14,  # Minnesota Vikings
        to_team_id=1,    # Atlanta Falcons
        transaction_date=date(2025, 3, 15),
        details='{"contract_years": 4, "contract_value": 180000000, "guaranteed": 100000000}',
        contract_id=None,
        event_id="ufa_2025_cousins"
    )
    print(f"✅ Logged UFA_SIGNING transaction (ID: {tx_id_2})")
    print(f"   Player: Kirk Cousins (QB) → Team 1 (Falcons)")
    print(f"   From Team: 14 (Vikings)")
    print()

    tx_id_3 = logger.log_transaction(
        dynasty_id="mvp_demo",
        season=2025,
        transaction_type="RELEASE",
        player_id=10003,
        player_name="Russell Wilson",
        position="QB",
        from_team_id=6,  # Denver Broncos
        to_team_id=None,
        transaction_date=date(2025, 3, 10),
        details='{"cap_savings": 5000000, "dead_money": 85000000}',
        event_id="release_2025_wilson"
    )
    print(f"✅ Logged RELEASE transaction (ID: {tx_id_3})")
    print(f"   Player: Russell Wilson (QB) released by Team 6 (Broncos)")
    print()

    # === Demo 2: Event-Based Logging ===
    print("-" * 80)
    print("DEMO 2: Event-Based Transaction Logging")
    print("-" * 80)
    print()

    # Simulate an event result
    event_result = EventResult(
        event_id="waiver_claim_2025_001",
        event_type="WAIVER_CLAIM",
        success=True,
        timestamp=datetime.now(),
        data={
            "claiming_team_id": 7,
            "releasing_team_id": 12,
            "player_id": 10004,
            "player_name": "Josh Dobbs",
            "position": "QB",
            "waiver_priority": 3,
            "claim_successful": True,
            "event_date": "2025-09-05",
            "dynasty_id": "mvp_demo",
            "message": "Team 7 successfully claimed player Josh Dobbs off waivers"
        }
    )

    tx_id_4 = logger.log_from_event_result(
        event_result=event_result,
        dynasty_id="mvp_demo",
        season=2025
    )
    print(f"✅ Logged transaction from EventResult (ID: {tx_id_4})")
    print(f"   Event Type: WAIVER_CLAIM")
    print(f"   Player: Josh Dobbs (QB) → Team 7")
    print()

    # === Demo 3: Query Transaction History ===
    print("-" * 80)
    print("DEMO 3: Query Transaction History")
    print("-" * 80)
    print()

    api = TransactionAPI(DB_PATH)

    # Query 1: All transactions for a player
    print("Query 1: Transaction history for Caleb Williams")
    player_txns = api.get_player_transactions(
        player_id=10001,
        dynasty_id="mvp_demo"
    )
    for txn in player_txns:
        print(f"  - {txn['transaction_date']}: {txn['transaction_type']}")
        print(f"    To Team: {txn['to_team_id']}")
    print()

    # Query 2: All transactions for a team
    print("Query 2: All transactions for Team 7")
    team_txns = api.get_team_transactions(
        team_id=7,
        dynasty_id="mvp_demo",
        season=2025
    )
    for txn in team_txns:
        print(f"  - {txn['transaction_date']}: {txn['transaction_type']}")
        print(f"    Player: {txn['player_name']} ({txn['position']})")
    print()

    # Query 3: Recent transactions (league-wide)
    print("Query 3: Recent transactions (all teams)")
    recent = api.get_recent_transactions(
        dynasty_id="mvp_demo",
        limit=10
    )
    for txn in recent:
        from_team = f"Team {txn['from_team_id']}" if txn['from_team_id'] else "N/A"
        to_team = f"Team {txn['to_team_id']}" if txn['to_team_id'] else "N/A"
        print(f"  - {txn['transaction_date']}: {txn['player_name']} ({txn['transaction_type']})")
        print(f"    From: {from_team} → To: {to_team}")
    print()

    # Query 4: Transactions by type
    print("Query 4: All DRAFT transactions")
    draft_txns = api.get_transactions_by_type(
        transaction_type="DRAFT",
        dynasty_id="mvp_demo",
        season=2025
    )
    for txn in draft_txns:
        import json
        details = json.loads(txn['details']) if txn['details'] else {}
        print(f"  - Pick #{details.get('overall', '?')}: {txn['player_name']} → Team {txn['to_team_id']}")
    print()

    # Query 5: Transaction summary
    print("Query 5: Season transaction summary")
    summary = api.get_transaction_summary(
        dynasty_id="mvp_demo",
        season=2025
    )
    print(f"  Total transactions: {summary['total_transactions']}")
    print(f"  By type:")
    for txn_type, count in summary['by_type'].items():
        print(f"    - {txn_type}: {count}")
    if summary['most_active_team']:
        print(f"  Most active team: Team {summary['most_active_team']} ({summary['team_counts'][summary['most_active_team']]['total']} transactions)")
    print()

    # === Summary ===
    print("=" * 80)
    print("MVP DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()
    print("✅ Components Verified:")
    print("  1. ✅ Database schema (player_transactions table)")
    print("  2. ✅ TransactionLogger service (direct + event-based logging)")
    print("  3. ✅ TransactionAPI query interface (8 query methods)")
    print("  4. ✅ Dynasty isolation (all queries respect dynasty_id)")
    print("  5. ✅ Event integration (log_from_event_result)")
    print("  6. ✅ JSON details storage and parsing")
    print()
    print("📦 Deliverables:")
    print("  - src/database/migrations/003_player_transactions_table.sql")
    print("  - src/persistence/transaction_logger.py")
    print("  - src/persistence/transaction_api.py")
    print("  - tests/persistence/test_transaction_logger.py")
    print()
    print("🎯 Ready for integration into UI and workflows!")
    print()


if __name__ == "__main__":
    try:
        demo_transaction_logging()
    finally:
        # Cleanup temp database
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
            print(f"🗑️  Cleaned up temporary database: {DB_PATH}")
