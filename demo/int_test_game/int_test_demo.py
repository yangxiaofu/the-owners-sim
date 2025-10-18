#!/usr/bin/env python3
"""
INT Test Demo

Quick single-game simulation to test QB interception tracking.
Uses the same workflow code as production season simulation.

Simulates 1 game, saves to database, then verifies INT data was persisted correctly.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import date

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from events.game_event import GameEvent
from workflows.simulation_workflow import SimulationWorkflow
from database.player_roster_api import PlayerRosterAPI
from database.connection import DatabaseConnection


def print_header(text):
    """Print section header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_result(label, value):
    """Print labeled result"""
    print(f"  {label:30s}: {value}")


def query_int_data(database_path, dynasty_id):
    """
    Query database for QB and DB interception data.

    Args:
        database_path: Path to database
        dynasty_id: Dynasty context

    Returns:
        Tuple of (qb_results, db_results)
    """
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query QB interceptions (passing_interceptions column)
    cursor.execute('''
        SELECT
            player_name,
            position,
            passing_attempts,
            passing_interceptions,
            interceptions
        FROM player_game_stats
        WHERE dynasty_id = ?
        AND passing_attempts > 0
        ORDER BY passing_attempts DESC
        LIMIT 10
    ''', (dynasty_id,))
    qb_results = cursor.fetchall()

    # Query DB interceptions (interceptions column)
    cursor.execute('''
        SELECT
            player_name,
            position,
            interceptions
        FROM player_game_stats
        WHERE dynasty_id = ?
        AND interceptions > 0
        ORDER BY interceptions DESC
    ''', (dynasty_id,))
    db_results = cursor.fetchall()

    # Get totals
    cursor.execute('''
        SELECT
            SUM(passing_interceptions) as qb_ints,
            SUM(interceptions) as db_ints,
            COUNT(DISTINCT game_id) as games
        FROM player_game_stats
        WHERE dynasty_id = ?
    ''', (dynasty_id,))
    totals = cursor.fetchone()

    conn.close()

    return qb_results, db_results, totals


def main():
    """Run INT test demo"""
    print_header("INT Test Demo - Single Game Simulation")

    # Configuration
    dynasty_id = "int_test"
    database_path = str(Path(__file__).parent / "data" / "int_test.db")
    away_team_id = 12  # Kansas City Chiefs
    home_team_id = 13  # Las Vegas Raiders

    print(f"\n  Configuration:")
    print_result("Dynasty ID", dynasty_id)
    print_result("Database", database_path)
    print_result("Away Team ID", f"{away_team_id} (Chiefs)")
    print_result("Home Team ID", f"{home_team_id} (Raiders)")

    # Create dynasty record (required for foreign key constraints)
    print_header("Creating Dynasty Record")
    try:
        db_conn = DatabaseConnection(database_path)
        # Check if dynasty exists
        existing = db_conn.execute_query(
            "SELECT dynasty_id FROM dynasties WHERE dynasty_id = ?",
            (dynasty_id,)
        )
        if not existing:
            print("  Creating dynasty record in database...")
            db_conn.execute_update(
                """INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id)
                   VALUES (?, ?, ?, ?)""",
                (dynasty_id, "INT Test Dynasty", "Test User", None)
            )
            print(f"✅ Dynasty '{dynasty_id}' created")
        else:
            print(f"✅ Dynasty '{dynasty_id}' already exists")
    except Exception as e:
        print(f"❌ Failed to create dynasty: {e}")
        return

    # Initialize dynasty rosters (one-time setup)
    print_header("Initializing Dynasty Rosters")
    try:
        roster_api = PlayerRosterAPI(database_path)
        if not roster_api.dynasty_has_rosters(dynasty_id):
            print("  Loading rosters from JSON files...")
            player_count = roster_api.initialize_dynasty_rosters(dynasty_id, season=2024)
            print(f"✅ Loaded {player_count} players into database")
        else:
            print("✅ Rosters already exist in database")

        # Verify rosters were loaded for our test teams
        print("\n  Verifying rosters for test teams...")
        for team_id, team_name in [(away_team_id, "Chiefs"), (home_team_id, "Raiders")]:
            roster = db_conn.execute_query(
                "SELECT COUNT(*) as count FROM players WHERE dynasty_id = ? AND team_id = ?",
                (dynasty_id, team_id)
            )
            player_count = roster[0]['count'] if roster else 0
            if player_count > 0:
                print(f"  ✅ Team {team_id} ({team_name}): {player_count} players")
            else:
                print(f"  ❌ Team {team_id} ({team_name}): NO PLAYERS FOUND!")
                print(f"     This will cause simulation to fail.")

                # Check if ANY players exist for this dynasty
                all_players = db_conn.execute_query(
                    "SELECT COUNT(*) as count FROM players WHERE dynasty_id = ?",
                    (dynasty_id,)
                )
                total_count = all_players[0]['count'] if all_players else 0
                print(f"     Total players for dynasty '{dynasty_id}': {total_count}")
                return

    except Exception as e:
        print(f"❌ Failed to initialize rosters: {e}")
        import traceback
        traceback.print_exc()
        return

    # Create workflow (same as production code)
    print_header("Creating Simulation Workflow")
    workflow = SimulationWorkflow(
        enable_persistence=True,
        database_path=database_path,
        dynasty_id=dynasty_id,
        verbose_logging=True
    )
    print("✅ Workflow created successfully")

    # Create game event
    print_header("Creating Game Event")
    game_date = date(2024, 9, 8)  # Mock date: September 8, 2024 (Sunday Week 1)

    game_event = GameEvent(
        event_id=f"int_test_game_{away_team_id}_at_{home_team_id}",
        away_team_id=away_team_id,
        home_team_id=home_team_id,
        week=1,
        season=2024,
        game_date=game_date,
        dynasty_id=dynasty_id
    )
    print(f"✅ Game event created: {game_event.event_id}")
    print_result("Game Date", f"{game_date.strftime('%Y-%m-%d')}")

    # Execute simulation
    print_header("Executing Game Simulation")
    print("\n🔴 Watch for INT DEBUG messages below:\n")

    result = workflow.execute(game_event)

    print(f"\n✅ Simulation completed")
    print_result("Game ID", result.game_id if result.success else "N/A")
    print_result("Success", result.success)
    print_result("Away Score", result.away_score if result.success else "N/A")
    print_result("Home Score", result.home_score if result.success else "N/A")

    # Query database to verify INT data
    print_header("Querying Database for INT Data")

    try:
        qb_results, db_results, totals = query_int_data(database_path, dynasty_id)

        # Print totals
        print("\n📊 Summary:")
        print_result("Total Games", totals['games'])
        print_result("QB INTs (passing_interceptions)", totals['qb_ints'])
        print_result("DB INTs (interceptions)", totals['db_ints'])

        # Print QB data
        print("\n📋 QB Stats (Top 10 by attempts):")
        print(f"  {'Player':<25s} {'Pos':<12s} {'Att':>5s} {'QB_INT':>7s} {'DB_INT':>7s}")
        print("  " + "-" * 70)
        for row in qb_results:
            print(f"  {row['player_name']:<25s} {row['position']:<12s} "
                  f"{row['passing_attempts']:>5d} {row['passing_interceptions']:>7d} "
                  f"{row['interceptions']:>7d}")

        # Print DB data
        if db_results:
            print("\n🛡️  DB Interceptions:")
            print(f"  {'Player':<25s} {'Pos':<12s} {'INT':>5s}")
            print("  " + "-" * 50)
            for row in db_results:
                print(f"  {row['player_name']:<25s} {row['position']:<12s} "
                      f"{row['interceptions']:>5d}")
        else:
            print("\n⚠️  No defensive interceptions recorded")

        # Verification
        print_header("Verification Results")

        qb_ints_found = totals['qb_ints'] > 0
        db_ints_found = totals['db_ints'] > 0

        if qb_ints_found:
            print(f"✅ PASS: QB interceptions recorded in passing_interceptions column ({totals['qb_ints']} total)")
        else:
            print("❌ FAIL: NO QB interceptions found in passing_interceptions column")
            print("   This means interceptions_thrown is still not being saved!")

        if db_ints_found:
            print(f"✅ INFO: DB interceptions recorded in interceptions column ({totals['db_ints']} total)")
        else:
            print("⚠️  INFO: No defensive interceptions in this game")

        # Final status
        print("\n" + "=" * 80)
        if qb_ints_found:
            print("✅ TEST PASSED: QB INT tracking is working!")
        else:
            print("❌ TEST FAILED: QB INT tracking is still broken")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error querying database: {e}")
        import traceback
        traceback.print_exc()

    # Instructions for manual verification
    print("\n💡 Manual Verification:")
    print(f"   sqlite3 {database_path}")
    print(f"   SELECT player_name, passing_attempts, passing_interceptions FROM player_game_stats WHERE dynasty_id='{dynasty_id}' AND passing_attempts > 0;")


if __name__ == "__main__":
    main()
