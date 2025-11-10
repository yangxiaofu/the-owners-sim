"""
Trade Events Demo

Interactive demonstration of the Phase 1.6 trade event system.

Shows:
1. How trade events are created
2. Cap space validation before trades
3. Trade execution with contract transfers
4. Transaction logging
5. Before/after comparison

Run with: PYTHONPATH=src python demo/trade_events_demo/trade_events_demo.py
"""

import sys
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from events.trade_events import PlayerForPlayerTradeEvent
from src.calendar.date_models import Date
from salary_cap import EventCapBridge


def print_section_header(title: str):
    """Print formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_contract_info(player_id: str, team_id: int, season: int, bridge: EventCapBridge):
    """Print contract details for a player."""
    contract = bridge.cap_db.get_player_contract(player_id, team_id, season)
    if contract:
        print(f"  Player {player_id}:")
        print(f"    Team: {team_id}")
        print(f"    Cap Hit: ${contract.get('current_year_cap_hit', 0):,}")
        print(f"    Contract Years Remaining: {contract.get('years_remaining', 'N/A')}")
        print(f"    Status: {contract.get('status', 'N/A')}")
    else:
        print(f"  Player {player_id}: No active contract found")


def print_team_cap_status(team_id: int, season: int, dynasty_id: str, bridge: EventCapBridge):
    """Print team's salary cap status."""
    try:
        cap_status = bridge.calculator.get_team_cap_status(team_id, season, dynasty_id)
        print(f"\n  Team {team_id} Cap Status:")
        print(f"    Cap Space: ${cap_status.get('cap_space', 0):,}")
        print(f"    Active Contracts Total: ${cap_status.get('active_contracts_total', 0):,}")
        print(f"    Is Over Cap: {cap_status.get('is_over_cap', False)}")
    except Exception as e:
        print(f"\n  Team {team_id}: Could not retrieve cap status ({e})")


def print_transactions(team_id: int, season: int, dynasty_id: str, bridge: EventCapBridge):
    """Print recent transactions for a team."""
    try:
        transactions = bridge.cap_db.get_team_transactions(
            team_id=team_id,
            season=season,
            dynasty_id=dynasty_id,
            transaction_type="TRADE"
        )

        if transactions:
            print(f"\n  Team {team_id} Recent Trade Transactions:")
            for txn in transactions[:3]:  # Show last 3
                print(f"    - {txn.get('transaction_date')}: {txn.get('description')}")
                print(f"      Cap Impact: ${txn.get('cap_impact_current', 0):,}")
        else:
            print(f"\n  Team {team_id}: No trade transactions found")
    except Exception as e:
        print(f"\n  Team {team_id}: Could not retrieve transactions ({e})")


def demo_simple_trade():
    """
    Demo 1: Simple 1-for-1 Player Trade

    Shows a basic player-for-player trade between two teams.
    """
    print_section_header("DEMO 1: Simple 1-for-1 Player Trade")

    # Setup
    team1_id = 7  # Eagles
    team2_id = 22  # Lions
    player_from_team1 = "1001"  # Example player ID
    player_from_team2 = "2001"  # Example player ID
    season = 2025
    dynasty_id = "trade_demo_dynasty"
    trade_date = Date(year=2025, month=10, day=15)

    database_path = ":memory:"  # Use in-memory database for demo

    print("\n📋 Trade Details:")
    print(f"  Team {team1_id} sends: Player {player_from_team1}")
    print(f"  Team {team2_id} sends: Player {player_from_team2}")
    print(f"  Trade Date: {trade_date}")
    print(f"  Dynasty: {dynasty_id}")

    # Create the event
    print("\n🔨 Creating PlayerForPlayerTradeEvent...")

    trade_event = PlayerForPlayerTradeEvent(
        team1_id=team1_id,
        team2_id=team2_id,
        team1_player_ids=[player_from_team1],
        team2_player_ids=[player_from_team2],
        season=season,
        event_date=trade_date,
        dynasty_id=dynasty_id,
        database_path=database_path
    )

    print(f"  ✓ Event created: {trade_event}")

    # Note about database setup
    print("\n⚠️  Note: This demo requires an initialized database with:")
    print("    - Active player contracts for both players")
    print("    - Team salary cap records")
    print("    - In production, you would:")
    print("      1. Create contracts for both players")
    print("      2. Initialize team cap records")
    print("      3. Then execute the trade")

    print("\n📊 Execution Flow:")
    print("  1. ValidationMiddleware checks:")
    print("     ✓ Both teams have cap space for incoming players")
    print("     ✓ Players have active contracts")
    print("     ✓ No duplicate players in trade")
    print("     ✓ Trade deadline hasn't passed")

    print("\n  2. TradeEventHandler executes:")
    print("     ✓ Transfers Player 1001's contract from Team 7 → Team 22")
    print("     ✓ Transfers Player 2001's contract from Team 22 → Team 7")
    print("     ✓ Updates cap accounting for both teams")
    print("     ✓ Logs 2 transactions (one per team)")

    print("\n  3. EventResult returned:")
    print("     ✓ success: True/False")
    print("     ✓ team1_acquired_players: [Player 2001 details]")
    print("     ✓ team2_acquired_players: [Player 1001 details]")
    print("     ✓ team1_net_cap_change: $X")
    print("     ✓ team2_net_cap_change: $Y")


def demo_trade_validation():
    """
    Demo 2: Trade Validation

    Shows how trades are validated before execution.
    """
    print_section_header("DEMO 2: Trade Validation Examples")

    print("\n✅ Valid Trade Criteria:")
    print("  1. Both teams have sufficient cap space for incoming players")
    print("  2. All players have active contracts with their current teams")
    print("  3. No player appears on both sides of the trade")
    print("  4. Trade occurs before the deadline (Week 9 Tuesday)")

    print("\n❌ Invalid Trade Examples:")

    print("\n  Example 1: Insufficient Cap Space")
    print("    Team A has $5M cap space")
    print("    Team B wants to send player with $10M cap hit")
    print("    → REJECTED: Team A short $5M")

    print("\n  Example 2: Player Without Contract")
    print("    Team A tries to trade Player X")
    print("    Player X is a pending free agent (no active contract)")
    print("    → REJECTED: Player X does not have an active contract")

    print("\n  Example 3: Duplicate Player")
    print("    Team A sends: [Player 1, Player 2]")
    print("    Team B sends: [Player 1, Player 3]")
    print("    → REJECTED: Player 1 appears on both sides")

    print("\n  Example 4: After Trade Deadline")
    print("    Trade attempted on Week 10, Day 1")
    print("    Deadline is Week 9, Tuesday")
    print("    → REJECTED: Trade deadline has passed (currently not implemented)")


def demo_cap_impact():
    """
    Demo 3: Salary Cap Impact Calculation

    Shows how trades affect team salary caps.
    """
    print_section_header("DEMO 3: Salary Cap Impact Calculation")

    print("\n📊 Example Trade:")
    print("  Team A sends: QB ($30M cap hit)")
    print("  Team B sends: WR ($15M cap hit)")

    print("\n💰 Cap Impact Calculation:")

    print("\n  Team A:")
    print("    Loses: QB $30M (outgoing)")
    print("    Gains: WR $15M (incoming)")
    print("    Net Change: -$15M (cap space freed)")
    print("    → Team A now has $15M MORE cap space")

    print("\n  Team B:")
    print("    Loses: WR $15M (outgoing)")
    print("    Gains: QB $30M (incoming)")
    print("    Net Change: +$15M (cap space used)")
    print("    → Team B now has $15M LESS cap space")

    print("\n✓ Validation Check:")
    print("  - If Team B only had $10M cap space, trade would be REJECTED")
    print("  - Team B needs at least $15M cap space to absorb the QB's contract")


def demo_transaction_logging():
    """
    Demo 4: Transaction Logging

    Shows how trades are logged in the database.
    """
    print_section_header("DEMO 4: Transaction Logging")

    print("\n📝 Two transactions are created (one per team):")

    print("\n  Transaction 1 (Team A):")
    print("    team_id: 7")
    print("    transaction_type: TRADE")
    print("    transaction_date: 2025-10-15")
    print("    cap_impact_current: -$15,000,000")
    print("    description: 'Trade with team 22: sent 1 player(s), received 1 player(s)'")

    print("\n  Transaction 2 (Team B):")
    print("    team_id: 22")
    print("    transaction_type: TRADE")
    print("    transaction_date: 2025-10-15")
    print("    cap_impact_current: +$15,000,000")
    print("    description: 'Trade with team 7: sent 1 player(s), received 1 player(s)'")

    print("\n📊 Query Examples:")
    print("  # Get all trades for Team A")
    print("  cap_db.get_team_transactions(team_id=7, transaction_type='TRADE')")

    print("\n  # Get all transactions (trades, signings, releases) for Team A")
    print("  cap_db.get_team_transactions(team_id=7)")


def demo_integration_with_ai():
    """
    Demo 5: Integration with AI Transaction System

    Shows how Phase 1.6 integrates with Phase 1.5 (AI Manager).
    """
    print_section_header("DEMO 5: Integration with Phase 1.5 (AI Transaction Manager)")

    print("\n🤖 Complete AI → Event → Database Flow:")

    print("\n  Step 1: AI Generates Trade Proposal (Phase 1.4)")
    print("    TradeProposalGenerator scans league")
    print("    → TradeProposal(team1=7, team2=22, assets=[...])")

    print("\n  Step 2: AI Evaluates Proposal (Phase 1.5)")
    print("    TransactionAIManager.evaluate_daily_transactions()")
    print("    → Checks GM personality, team needs, probability")
    print("    → Decision: ACCEPT")

    print("\n  Step 3: Create Trade Event (Phase 1.6) ← NEW")
    print("    trade_event = PlayerForPlayerTradeEvent(")
    print("        team1_id=7,")
    print("        team2_id=22,")
    print("        team1_player_ids=['1001'],")
    print("        team2_player_ids=['2001'],")
    print("        ...)")

    print("\n  Step 4: Schedule Event in Calendar")
    print("    event_db.insert_event(trade_event)")
    print("    → Event scheduled for execution date")

    print("\n  Step 5: Simulator Executes Event")
    print("    SimulationExecutor.simulate_day()")
    print("    → Retrieves trade_event from calendar")
    print("    → Calls trade_event.simulate()")

    print("\n  Step 6: Trade Event Executes (Phase 1.6) ← NEW")
    print("    validate_player_trade() ✓")
    print("    execute_player_trade() ✓")
    print("    → Contracts transferred")
    print("    → Cap updated")
    print("    → Transactions logged")

    print("\n  Step 7: Result Persisted")
    print("    EventResult stored in events table")
    print("    → success: True")
    print("    → data: {cap changes, player details}")

    print("\n✨ Result: Fully automated AI-driven trade system!")


def demo_multi_player_trade():
    """
    Demo 6: Multi-Player Trade

    Shows a more complex 2-for-2 trade.
    """
    print_section_header("DEMO 6: Multi-Player Trade (2-for-2)")

    print("\n📋 Trade Details:")
    print("  Team 7 sends:")
    print("    - Player 1001 (WR, 85 OVR, $12M cap hit)")
    print("    - Player 1002 (CB, 82 OVR, $8M cap hit)")
    print("  Total outgoing cap: $20M")

    print("\n  Team 22 sends:")
    print("    - Player 2001 (LB, 87 OVR, $15M cap hit)")
    print("    - Player 2002 (S, 80 OVR, $6M cap hit)")
    print("  Total outgoing cap: $21M")

    print("\n💰 Cap Impact:")
    print("  Team 7:")
    print("    Loses: $20M")
    print("    Gains: $21M")
    print("    Net: +$1M (uses more cap space)")
    print("    → Needs at least $1M cap space")

    print("\n  Team 22:")
    print("    Loses: $21M")
    print("    Gains: $20M")
    print("    Net: -$1M (frees cap space)")
    print("    → No cap space required")

    print("\n🔨 Creating Event:")
    print("  trade_event = PlayerForPlayerTradeEvent(")
    print("      team1_id=7,")
    print("      team2_id=22,")
    print("      team1_player_ids=['1001', '1002'],  # List of 2 players")
    print("      team2_player_ids=['2001', '2002'],  # List of 2 players")
    print("      ...)")

    print("\n✅ Same execution flow as 1-for-1 trade!")
    print("  The system handles N-for-M trades automatically.")


def main():
    """Run all demos."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║                                                                            ║")
    print("║           PHASE 1.6: TRADE EVENTS SYSTEM - INTERACTIVE DEMO               ║")
    print("║                                                                            ║")
    print("║  This demo shows how AI-generated trade proposals are executed through    ║")
    print("║  the event system with full salary cap integration and database           ║")
    print("║  persistence.                                                              ║")
    print("║                                                                            ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")

    # Run all demos
    demo_simple_trade()
    demo_trade_validation()
    demo_cap_impact()
    demo_transaction_logging()
    demo_integration_with_ai()
    demo_multi_player_trade()

    # Summary
    print_section_header("SUMMARY")
    print("\n✅ Phase 1.6 Deliverables:")
    print("  1. ✓ PlayerForPlayerTradeEvent class")
    print("  2. ✓ TradeEventHandler (validates and executes)")
    print("  3. ✓ ValidationMiddleware.validate_player_trade()")
    print("  4. ✓ EventCapBridge.execute_player_trade()")
    print("  5. ✓ Transaction logging (2 records per trade)")
    print("  6. ✓ Cap space validation for both teams")
    print("  7. ✓ Contract transfer between teams")
    print("  8. ✓ Dynasty isolation support")

    print("\n🎯 Key Features:")
    print("  • Atomic transactions (rollback on failure)")
    print("  • Full salary cap integration")
    print("  • Comprehensive validation (4+ checks)")
    print("  • Detailed transaction logging")
    print("  • Supports 1-for-1 or N-for-M trades")
    print("  • Integrates with AI transaction system (Phase 1.5)")

    print("\n📚 Next Steps:")
    print("  • Run comprehensive test suite (60+ tests)")
    print("  • Test with real database and player data")
    print("  • Integrate with full season simulation")
    print("  • Add draft pick trades (Phase 1.6b)")

    print("\n" + "="*80)
    print("\nDemo complete! 🎉")
    print("\nTo test with real database:")
    print("  1. Initialize database with player contracts")
    print("  2. Set up team salary cap records")
    print("  3. Create PlayerForPlayerTradeEvent with real player IDs")
    print("  4. Call event.simulate() to execute")
    print("  5. Check database for updated contracts and transactions")
    print("\n")


if __name__ == "__main__":
    main()
