"""
Team Needs Analyzer Demo

Interactive terminal demonstration of the TeamNeedsAnalyzer system.
Uses real NFL player data from JSON files via database initialization.

Run with: PYTHONPATH=src python demo_team_needs_analyzer.py
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from offseason.team_needs_analyzer import TeamNeedsAnalyzer, NeedUrgency
from database.connection import DatabaseConnection
from database.player_roster_api import PlayerRosterAPI
from depth_chart.depth_chart_api import DepthChartAPI
from salary_cap.cap_database_api import CapDatabaseAPI
import sqlite3
from datetime import date


def setup_test_dynasty(db_path, dynasty_id, team_id=7):
    """
    Initialize test dynasty with real player data from JSON.

    Args:
        db_path: Database path
        dynasty_id: Dynasty identifier
        team_id: Team to initialize (default 7 = Cleveland Browns)

    Returns:
        Number of players loaded
    """
    print("\n🔧 Setting up test dynasty...")

    # Initialize database schema first (will create all tables)
    print("   Initializing database schema...")

    # Create database connection and initialize ALL tables
    db_conn = DatabaseConnection(db_path)
    db_conn.initialize_database()  # Creates ALL tables including dynasties

    # Now ensure dynasty exists (table is guaranteed to exist)
    db_conn.ensure_dynasty_exists(dynasty_id)

    # Initialize CapDatabaseAPI (runs salary cap migrations)
    cap_init = CapDatabaseAPI(db_path)

    # Initialize rosters from JSON
    player_api = PlayerRosterAPI(db_path)

    # Check if already initialized
    if player_api.dynasty_has_rosters(dynasty_id):
        print(f"   Dynasty '{dynasty_id}' already initialized in database")

        # Get roster count
        roster_count = player_api.get_roster_count(dynasty_id, team_id)
        print(f"   Team {team_id} roster: {roster_count} players")

        return roster_count

    # Initialize from JSON (loads all 32 teams + free agents)
    print(f"   Loading rosters from JSON files...")
    total_players = player_api.initialize_dynasty_rosters(dynasty_id, season=2025)
    print(f"   ✅ Loaded {total_players} total players (all 32 teams)")

    # Auto-generate depth charts (with retry logic for database locks)
    print(f"   Generating depth charts...")
    import time

    # Add delay to ensure database writes complete
    time.sleep(0.5)

    max_retries = 5
    for attempt in range(max_retries):
        try:
            depth_chart_api = DepthChartAPI(db_path)
            depth_chart_api.auto_generate_depth_chart(dynasty_id, team_id)
            print(f"   ✅ Depth chart generated for team {team_id}")
            break
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"   Database locked, retrying... (attempt {attempt + 1}/{max_retries - 1})")
                time.sleep(1.0)  # Longer wait between retries
            else:
                print(f"   ⚠️  Warning: Could not generate depth chart, will try later")
                break

    return total_players


def create_sample_expiring_contracts(db_path, dynasty_id, team_id, season):
    """
    Create some expiring contracts for testing.

    Args:
        db_path: Database path
        dynasty_id: Dynasty identifier
        team_id: Team ID
        season: Season year
    """
    print("\n📋 Creating sample expiring contracts...")

    import time

    # Add retry logic for database locks
    max_retries = 3
    for attempt in range(max_retries):
        try:
            cap_api = CapDatabaseAPI(db_path)
            player_api = PlayerRosterAPI(db_path)
            break
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"   Database locked, retrying... (attempt {attempt + 1})")
                time.sleep(0.5)
            else:
                print(f"   ⚠️  Warning: Could not create expiring contracts")
                return

    # Get team roster
    roster = player_api.get_team_roster(dynasty_id, team_id)

    # Find a few players to give expiring contracts
    # We'll pick: LT, RB1, and a backup WR
    positions_to_expire = {
        'left_tackle': 1,
        'running_back': 1,
        'wide_receiver': 1
    }

    expired_count = 0

    for player in roster:
        import json
        positions = json.loads(player['positions'])

        if not positions:
            continue

        primary_position = positions[0]

        if primary_position in positions_to_expire and positions_to_expire[primary_position] > 0:
            # Create an expiring contract
            player_id = player['player_id']

            # Insert a contract that expires this season
            try:
                cap_api.insert_contract(
                    player_id=player_id,
                    team_id=team_id,
                    dynasty_id=dynasty_id,
                    start_year=season - 2,  # 3-year contract ending this year
                    end_year=season,
                    contract_years=3,
                    contract_type='VETERAN',
                    total_value=15_000_000
                )

                print(f"   Created expiring contract for {player['first_name']} {player['last_name']} ({primary_position})")
                positions_to_expire[primary_position] -= 1
                expired_count += 1

            except Exception as e:
                # Contract may already exist - skip
                pass

    print(f"   ✅ Created {expired_count} expiring contracts")


def display_team_needs(analyzer, team_id, season, team_name="Team"):
    """
    Display team needs analysis in formatted terminal output.

    Args:
        analyzer: TeamNeedsAnalyzer instance
        team_id: Team ID
        season: Season year
        team_name: Team name for display
    """
    print("\n" + "=" * 70)
    print(f"TEAM NEEDS ANALYZER - {team_name} (Team {team_id})")
    print(f"Dynasty: {analyzer.dynasty_id} | Season: {season}")
    print("=" * 70)

    # Get all needs
    all_needs = analyzer.analyze_team_needs(team_id, season, include_future_contracts=True)

    # Group by urgency
    critical_needs = [n for n in all_needs if n['urgency'] == NeedUrgency.CRITICAL]
    high_needs = [n for n in all_needs if n['urgency'] == NeedUrgency.HIGH]
    medium_needs = [n for n in all_needs if n['urgency'] == NeedUrgency.MEDIUM]
    low_needs = [n for n in all_needs if n['urgency'] == NeedUrgency.LOW]

    # Display by urgency level
    if critical_needs:
        print(f"\n🔴 CRITICAL NEEDS ({len(critical_needs)}):")
        for i, need in enumerate(critical_needs, 1):
            print(f"  {i}. {need['position'].upper().replace('_', ' ')}")
            print(f"     Starter: {need['starter_overall']} overall")
            print(f"     Depth: {need['depth_count']} backups (avg {need['avg_depth_overall']:.0f} OVR)")
            if need['starter_leaving']:
                print(f"     ⚠️  Contract expiring!")
            print(f"     Reason: {need['reason']}")
            print()

    if high_needs:
        print(f"\n🟠 HIGH NEEDS ({len(high_needs)}):")
        for i, need in enumerate(high_needs, 1):
            print(f"  {len(critical_needs) + i}. {need['position'].upper().replace('_', ' ')}")
            print(f"     Starter: {need['starter_overall']} overall")
            print(f"     Depth: {need['depth_count']} backups (avg {need['avg_depth_overall']:.0f} OVR)")
            if need['starter_leaving']:
                print(f"     ⚠️  Contract expiring!")
            print(f"     Reason: {need['reason']}")
            print()

    if medium_needs:
        print(f"\n🟡 MEDIUM NEEDS ({len(medium_needs)}):")
        for i, need in enumerate(medium_needs, 1):
            offset = len(critical_needs) + len(high_needs)
            print(f"  {offset + i}. {need['position'].upper().replace('_', ' ')}")
            print(f"     Starter: {need['starter_overall']} overall | Depth: {need['depth_count']} backups")
            print(f"     Reason: {need['reason']}")
            print()

    if low_needs:
        print(f"\n🟢 LOW PRIORITY NEEDS ({len(low_needs)}):")
        positions = ", ".join([n['position'].replace('_', ' ').title() for n in low_needs[:5]])
        if len(low_needs) > 5:
            positions += f" (+{len(low_needs) - 5} more)"
        print(f"  {positions}")
        print()

    # Display strong positions (no needs)
    depth_chart_api = DepthChartAPI(analyzer.database_path)
    full_depth = depth_chart_api.get_full_depth_chart(analyzer.dynasty_id, team_id)

    # Find positions with good starters and depth
    strong_positions = []
    for position, players in full_depth.items():
        if not players:
            continue

        players_sorted = sorted(players, key=lambda p: p['depth_order'])
        starter = next((p for p in players_sorted if p['depth_order'] == 1), None)

        if starter and starter['overall'] >= 85:
            strong_positions.append((position, starter['overall']))

    if strong_positions:
        print(f"\n✅ STRONG POSITIONS ({len(strong_positions)}):")
        strong_positions.sort(key=lambda x: x[1], reverse=True)
        for position, overall in strong_positions[:5]:
            print(f"  - {position.upper().replace('_', ' ')}: {overall} OVR starter")

    print("\n" + "=" * 70)


def interactive_menu():
    """Run interactive team needs analyzer demo."""
    db_path = "data/database/nfl_simulation.db"
    dynasty_id = "team_needs_demo"
    season = 2025

    # Team ID to name mapping
    team_names = {
        1: "Buffalo Bills",
        2: "Miami Dolphins",
        3: "New England Patriots",
        4: "New York Jets",
        5: "Baltimore Ravens",
        6: "Cincinnati Bengals",
        7: "Cleveland Browns",
        8: "Pittsburgh Steelers",
        9: "Houston Texans",
        10: "Indianapolis Colts",
        11: "Jacksonville Jaguars",
        12: "Tennessee Titans",
        13: "Denver Broncos",
        14: "Kansas City Chiefs",
        15: "Las Vegas Raiders",
        16: "Los Angeles Chargers",
        17: "Dallas Cowboys",
        18: "New York Giants",
        19: "Philadelphia Eagles",
        20: "Washington Commanders",
        21: "Chicago Bears",
        22: "Detroit Lions",
        23: "Green Bay Packers",
        24: "Minnesota Vikings",
        25: "Atlanta Falcons",
        26: "Carolina Panthers",
        27: "New Orleans Saints",
        28: "Tampa Bay Buccaneers",
        29: "Arizona Cardinals",
        30: "Los Angeles Rams",
        31: "San Francisco 49ers",
        32: "Seattle Seahawks"
    }

    print("\n" + "=" * 70)
    print("TEAM NEEDS ANALYZER - Interactive Demo")
    print("=" * 70)

    # Initialize with Cleveland Browns by default
    default_team = 7
    setup_test_dynasty(db_path, dynasty_id, default_team)

    # Create some expiring contracts for demo purposes
    create_sample_expiring_contracts(db_path, dynasty_id, default_team, season)

    # Create analyzer
    analyzer = TeamNeedsAnalyzer(db_path, dynasty_id)

    # Show Cleveland Browns by default
    display_team_needs(analyzer, default_team, season, team_names[default_team])

    # Interactive loop
    while True:
        print("\nOptions:")
        print("  1. Analyze another team")
        print("  2. Compare top 5 needs for all teams")
        print("  3. Exit")

        choice = input("\nEnter choice (1-3): ").strip()

        if choice == "1":
            print("\nAvailable teams:")
            print("  1-32: NFL teams (e.g., 7 = Cleveland Browns, 22 = Detroit Lions)")

            team_input = input("\nEnter team ID (1-32): ").strip()

            try:
                team_id = int(team_input)
                if 1 <= team_id <= 32:
                    team_name = team_names.get(team_id, f"Team {team_id}")

                    # Generate depth chart if not exists
                    depth_chart_api = DepthChartAPI(db_path)
                    depth_chart_api.auto_generate_depth_chart(dynasty_id, team_id)

                    display_team_needs(analyzer, team_id, season, team_name)
                else:
                    print("❌ Invalid team ID. Must be 1-32.")
            except ValueError:
                print("❌ Invalid input. Please enter a number.")

        elif choice == "2":
            print("\n" + "=" * 70)
            print("TOP 5 NEEDS COMPARISON - All NFL Teams")
            print("=" * 70)

            for team_id in range(1, 33):
                team_name = team_names.get(team_id, f"Team {team_id}")

                # Generate depth chart if needed
                depth_chart_api = DepthChartAPI(db_path)
                try:
                    depth_chart_api.auto_generate_depth_chart(dynasty_id, team_id)
                except:
                    pass

                # Get top 5 needs
                top_needs = analyzer.get_top_needs(team_id, season, limit=5)

                print(f"\n{team_name} (Team {team_id}):")
                if top_needs:
                    for i, need in enumerate(top_needs, 1):
                        urgency_icon = {
                            5: "🔴",
                            4: "🟠",
                            3: "🟡",
                            2: "🟢",
                            1: "✅"
                        }[need['urgency_score']]

                        print(f"  {urgency_icon} {i}. {need['position'].replace('_', ' ').title()} ({need['starter_overall']} OVR)")
                else:
                    print("  ✅ No significant needs - roster looks strong!")

            print("\n" + "=" * 70)

        elif choice == "3":
            print("\n✅ Exiting Team Needs Analyzer demo")
            break

        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    interactive_menu()
