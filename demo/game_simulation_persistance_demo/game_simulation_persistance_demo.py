#!/usr/bin/env python3
"""
Game Simulation Persistence Demo

Demonstrates:
1. Creating a game event (Cleveland Browns vs Minnesota Vikings)
2. Storing the event in an isolated demo database
3. Retrieving the event using Events API
4. Simulating the game
5. Displaying results with box scores

This demo uses its own isolated database: demo/game_simulation_persistance_demo/data/demo_events.db
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from datetime import datetime
from events import EventDatabaseAPI, GameEvent
from constants.team_ids import TeamIDs
from game_management.box_score_generator import BoxScoreGenerator
from game_management.player_stats_query_service import PlayerStatsQueryService

# Import new workflow system
from workflows import SimulationWorkflow


def print_header(title: str, width: int = 80):
    """Print formatted header."""
    print(f"\n{'='*width}")
    print(f"{title.center(width)}")
    print(f"{'='*width}\n")


def print_section(title: str, width: int = 80):
    """Print formatted section header."""
    print(f"\n{'─'*width}")
    print(f"🔹 {title}")
    print(f"{'─'*width}")


def display_box_score_section(section):
    """Display a single box score section."""
    if not section.rows:
        return

    print(f"\n{section.title}")
    print("─" * 80)

    # Print headers
    print("  ".join(f"{h:12}" for h in section.headers))
    print("─" * 80)

    # Print rows
    for row in section.rows:
        print("  ".join(f"{cell:12}" for cell in row))

    # Print footnotes if any
    if section.footnotes:
        print()
        for note in section.footnotes:
            print(f"  {note}")


def display_team_box_score(box_score):
    """Display complete box score for a team."""
    print(f"\n{'='*80}")
    print(f"{box_score.team.full_name} Box Score".center(80))
    print(f"{'='*80}")

    # Display each section
    for section in box_score.sections:
        display_box_score_section(section)

    # Display team totals
    if box_score.team_totals:
        print(f"\n{'─'*80}")
        print("TEAM TOTALS")
        print(f"{'─'*80}")
        for key, value in box_score.team_totals.items():
            print(f"  {key}: {value}")


def display_team_statistics(team_name: str, team_stats):
    """Display team-level statistics."""
    print(f"\n{'='*80}")
    print(f"{team_name} Team Statistics".center(80))
    print(f"{'='*80}")

    if not team_stats:
        print("  No statistics available")
        return

    # Display as dictionary if that's what we have
    if isinstance(team_stats, dict):
        for key, value in team_stats.items():
            formatted_key = key.replace('_', ' ').title()
            print(f"  {formatted_key}: {value}")
    else:
        # Display as object attributes
        stats_attrs = [attr for attr in dir(team_stats) if not attr.startswith('_')]
        for attr in stats_attrs:
            value = getattr(team_stats, attr, None)
            if value is not None and not callable(value):
                formatted_key = attr.replace('_', ' ').title()
                print(f"  {formatted_key}: {value}")


def display_complete_passing_stats(player_stats, team_name: str):
    """Display complete passing statistics for all QBs with LIVE data."""
    # Filter players with passing attempts (NOW AVAILABLE from live stats!)
    passers = []
    for player in player_stats:
        attempts = getattr(player, 'passing_attempts', 0)
        if attempts > 0:
            passers.append(player)

    if not passers:
        return

    print(f"\n{'='*80}")
    print(f"{team_name} - PASSING".center(80))
    print(f"{'='*80}")
    print(f"{'Player':<20} {'C/Att':<10} {'Yards':<7} {'TD':<5} {'INT':<5} {'Sacks':<7} {'Rate':<6} {'Cmp%':<6}")
    print("─" * 80)

    for player in passers:
        name = getattr(player, 'player_name', 'Unknown')
        completions = getattr(player, 'passing_completions', 0)
        attempts = getattr(player, 'passing_attempts', 0)
        yards = getattr(player, 'passing_yards', 0)
        tds = getattr(player, 'passing_tds', 0)
        ints = getattr(player, 'interceptions_thrown', 0)
        sacks = getattr(player, 'sacks_taken', 0)

        # Calculate stats
        comp_att = f"{completions}/{attempts}"
        comp_pct = f"{(completions/attempts*100):.1f}%" if attempts > 0 else "0.0%"

        # Calculate NFL passer rating
        if attempts > 0:
            a = min(max(((completions / attempts) - 0.3) * 5, 0), 2.375)
            b = min(max(((yards / attempts) - 3) * 0.25, 0), 2.375)
            c = min(max((tds / attempts) * 20, 0), 2.375)
            d = min(max(2.375 - ((ints / attempts) * 25), 0), 2.375)
            rating = ((a + b + c + d) / 6) * 100
        else:
            rating = 0.0

        sacks_str = f"{sacks}" if sacks > 0 else "0"
        rating_str = f"{rating:.1f}"

        print(f"{name:<20} {comp_att:<10} {yards:<7} {tds:<5} {ints:<5} {sacks_str:<7} {rating_str:<6} {comp_pct:<6}")


def display_complete_rushing_stats(player_stats, team_name: str):
    """Display complete rushing statistics for all rushers with LIVE data."""
    # Filter players with rushing attempts (NOW AVAILABLE from live stats!)
    rushers = []
    for player in player_stats:
        attempts = getattr(player, 'rushing_attempts', 0)
        if attempts > 0:
            rushers.append(player)

    if not rushers:
        return

    # Sort by rushing yards (descending)
    rushers.sort(key=lambda p: getattr(p, 'rushing_yards', 0), reverse=True)

    print(f"\n{'='*80}")
    print(f"{team_name} - RUSHING".center(80))
    print(f"{'='*80}")
    print(f"{'Player':<25} {'Att':<6} {'Yards':<8} {'Avg':<6} {'TD':<6}")
    print("─" * 80)

    for player in rushers:
        name = getattr(player, 'player_name', 'Unknown')
        attempts = getattr(player, 'rushing_attempts', 0)
        yards = getattr(player, 'rushing_yards', 0)
        tds = getattr(player, 'rushing_tds', 0)

        avg = f"{yards/attempts:.1f}" if attempts > 0 else "0.0"
        print(f"{name:<25} {attempts:<6} {yards:<8} {avg:<6} {tds:<6}")


def display_complete_receiving_stats(player_stats, team_name: str):
    """Display complete receiving statistics for all receivers with LIVE data."""
    # Filter players with targets (NOW AVAILABLE from live stats!)
    receivers = []
    for player in player_stats:
        targets = getattr(player, 'targets', 0)
        receptions = getattr(player, 'receptions', 0)
        if targets > 0 or receptions > 0:
            receivers.append(player)

    if not receivers:
        return

    # Sort by receiving yards (descending)
    receivers.sort(key=lambda p: getattr(p, 'receiving_yards', 0), reverse=True)

    print(f"\n{'='*80}")
    print(f"{team_name} - RECEIVING".center(80))
    print(f"{'='*80}")
    print(f"{'Player':<25} {'Rec/Tgt':<10} {'Yards':<8} {'Avg':<6} {'TD':<6}")
    print("─" * 80)

    for player in receivers:
        name = getattr(player, 'player_name', 'Unknown')
        rec = getattr(player, 'receptions', 0)
        tgt = getattr(player, 'targets', 0)
        yards = getattr(player, 'receiving_yards', 0)
        tds = getattr(player, 'receiving_tds', 0)

        rec_tgt = f"{rec}/{tgt}"
        avg = f"{yards/rec:.1f}" if rec > 0 else "0.0"
        print(f"{name:<25} {rec_tgt:<10} {yards:<8} {avg:<6} {tds:<6}")


def display_complete_defensive_stats(player_stats, team_name: str):
    """Display complete defensive statistics for all defensive players."""
    # Filter players with any defensive stats (database uses 'pass_deflections' not 'passes_defended')
    defenders = []
    for player in player_stats:
        if isinstance(player, dict):
            tackles = player.get('tackles', 0)
            sacks = player.get('sacks', 0)
            ints = player.get('interceptions', 0)
            pd = player.get('pass_deflections', 0)  # Note: database uses this field name
            if tackles > 0 or sacks > 0 or ints > 0 or pd > 0:
                defenders.append(player)
        else:
            tackles = getattr(player, 'tackles', 0)
            sacks = getattr(player, 'sacks', 0)
            ints = getattr(player, 'interceptions', 0)
            pd = getattr(player, 'pass_deflections', 0)
            if tackles > 0 or sacks > 0 or ints > 0 or pd > 0:
                defenders.append(player)

    if not defenders:
        return

    # Sort by tackles descending
    defenders.sort(key=lambda p: (p.get('tackles', 0) if isinstance(p, dict) else getattr(p, 'tackles', 0)), reverse=True)

    print(f"\n{'='*80}")
    print(f"{team_name} - DEFENSE".center(80))
    print(f"{'='*80}")
    print(f"{'Player':<25} {'Tackles':<10} {'Sacks':<8} {'INT':<6} {'PD':<6}")
    print("─" * 80)

    for player in defenders:
        if isinstance(player, dict):
            name = player.get('player_name', 'Unknown')
            tackles = player.get('tackles', 0)
            sacks = player.get('sacks', 0)
            ints = player.get('interceptions', 0)
            pd = player.get('pass_deflections', 0)
        else:
            name = getattr(player, 'player_name', 'Unknown')
            tackles = getattr(player, 'tackles', 0)
            sacks = getattr(player, 'sacks', 0)
            ints = getattr(player, 'interceptions', 0)
            pd = getattr(player, 'pass_deflections', 0)

        sacks_str = f"{sacks:.1f}" if sacks > 0 else "0"
        print(f"{name:<25} {tackles:<10} {sacks_str:<8} {ints:<6} {pd:<6}")


def display_snap_counts(player_stats, team_name: str):
    """Display snap counts for all players who played with LIVE data."""
    # NOW AVAILABLE: offensive_snaps, defensive_snaps, total_snaps from live stats!
    # Filter players with any snaps
    offensive_players = []
    defensive_players = []

    for player in player_stats:
        off_snaps = getattr(player, 'offensive_snaps', 0)
        def_snaps = getattr(player, 'defensive_snaps', 0)
        total_snaps = getattr(player, 'total_snaps', 0)

        if total_snaps > 0:
            player_data = {
                'name': getattr(player, 'player_name', 'Unknown'),
                'position': getattr(player, 'position', 'UNK'),
                'offensive_snaps': off_snaps,
                'defensive_snaps': def_snaps,
                'total_snaps': total_snaps
            }

            if off_snaps > 0:
                offensive_players.append(player_data)
            if def_snaps > 0:
                defensive_players.append(player_data)

    if not offensive_players and not defensive_players:
        return

    # Sort by snap count
    offensive_players.sort(key=lambda p: p['offensive_snaps'], reverse=True)
    defensive_players.sort(key=lambda p: p['defensive_snaps'], reverse=True)

    print(f"\n{'='*80}")
    print(f"{team_name} - SNAP COUNTS".center(80))
    print(f"{'='*80}")

    if offensive_players:
        print(f"\nOFFENSE:")
        print("─" * 80)
        print(f"{'Player':<25} {'Position':<10} {'Snaps':<8}")
        print("─" * 80)
        for player in offensive_players:
            print(f"{player['name']:<25} {player['position']:<10} {player['offensive_snaps']:<8}")

    if defensive_players:
        print(f"\nDEFENSE:")
        print("─" * 80)
        print(f"{'Player':<25} {'Position':<10} {'Snaps':<8}")
        print("─" * 80)
        for player in defensive_players:
            print(f"{player['name']:<25} {player['position']:<10} {player['defensive_snaps']:<8}")


def initialize_database_schema(db_path: str):
    """Initialize database schema if tables don't exist."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if games table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
    if cursor.fetchone() is None:
        print("   📋 Creating required tables...")

        # Create games table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                game_type TEXT DEFAULT 'regular',
                home_team_id INTEGER NOT NULL,
                away_team_id INTEGER NOT NULL,
                home_score INTEGER NOT NULL,
                away_score INTEGER NOT NULL,
                total_plays INTEGER,
                game_duration_minutes INTEGER,
                overtime_periods INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

        # Create player_game_stats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_game_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                game_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                position TEXT NOT NULL,
                passing_yards INTEGER DEFAULT 0,
                passing_tds INTEGER DEFAULT 0,
                passing_completions INTEGER DEFAULT 0,
                passing_attempts INTEGER DEFAULT 0,
                rushing_yards INTEGER DEFAULT 0,
                rushing_tds INTEGER DEFAULT 0,
                rushing_attempts INTEGER DEFAULT 0,
                receiving_yards INTEGER DEFAULT 0,
                receiving_tds INTEGER DEFAULT 0,
                receptions INTEGER DEFAULT 0,
                targets INTEGER DEFAULT 0,
                tackles_total INTEGER DEFAULT 0,
                sacks REAL DEFAULT 0,
                interceptions INTEGER DEFAULT 0,
                field_goals_made INTEGER DEFAULT 0,
                field_goals_attempted INTEGER DEFAULT 0,
                extra_points_made INTEGER DEFAULT 0,
                extra_points_attempted INTEGER DEFAULT 0,
                offensive_snaps INTEGER DEFAULT 0,
                defensive_snaps INTEGER DEFAULT 0,
                total_snaps INTEGER DEFAULT 0,
                FOREIGN KEY (game_id) REFERENCES games(game_id)
            )
        """)

        # Create standings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS standings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                season INTEGER NOT NULL,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,
                points_for INTEGER DEFAULT 0,
                points_against INTEGER DEFAULT 0,
                division_wins INTEGER DEFAULT 0,
                division_losses INTEGER DEFAULT 0,
                conference_wins INTEGER DEFAULT 0,
                conference_losses INTEGER DEFAULT 0,
                home_wins INTEGER DEFAULT 0,
                home_losses INTEGER DEFAULT 0,
                away_wins INTEGER DEFAULT 0,
                away_losses INTEGER DEFAULT 0,
                current_streak TEXT,
                division_rank INTEGER,
                UNIQUE(dynasty_id, team_id, season)
            )
        """)

        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_dynasty ON games(dynasty_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_game ON player_game_stats(game_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_standings_dynasty ON standings(dynasty_id)")

        conn.commit()
        print("   ✅ Tables created successfully")
    else:
        print("   ✅ Tables already exist")

    conn.close()


def main():
    """Main demo execution."""
    print_header("GAME SIMULATION PERSISTENCE DEMO", 80)
    print("Demonstrating event storage, retrieval, and game simulation with box scores")
    print("Teams: Cleveland Browns @ Minnesota Vikings")

    # ========================================
    # STEP 1: Initialize Isolated Database
    # ========================================
    print_section("Step 1: Initialize Isolated Demo Database")

    # Use demo-specific database (isolated from production)
    demo_db_path = "demo/game_simulation_persistance_demo/data/demo_events.db"
    event_db = EventDatabaseAPI(demo_db_path)

    print(f"✅ Database initialized: {demo_db_path}")
    print(f"   This database is isolated to this demo only")

    # Initialize persistence tables if needed
    initialize_database_schema(demo_db_path)

    # Show database stats
    stats = event_db.get_statistics()
    print(f"   Current database stats:")
    print(f"   - Total events: {stats.get('total_events', 0)}")
    print(f"   - Unique games: {stats.get('unique_games', 0)}")

    # ========================================
    # STEP 2: Create Game Event
    # ========================================
    print_section("Step 2: Create Game Event")

    game_event = GameEvent(
        away_team_id=TeamIDs.CLEVELAND_BROWNS,
        home_team_id=TeamIDs.MINNESOTA_VIKINGS,
        game_date=datetime(2024, 12, 1, 13, 0),  # Sunday 1pm ET
        week=13,
        season=2024,
        season_type="regular_season"
    )

    print(f"✅ GameEvent created:")
    print(f"   Event ID: {game_event.event_id}")
    print(f"   Game ID: {game_event.get_game_id()}")
    print(f"   Matchup: {game_event.get_matchup_description()}")
    print(f"   Event Type: {game_event.get_event_type()}")

    # ========================================
    # STEP 3: Store Event in Database
    # ========================================
    print_section("Step 3: Store Event in Database")

    event_db.insert_event(game_event)
    print(f"✅ Event stored in database")
    print(f"   Database: {demo_db_path}")
    print(f"   Game ID: {game_event.get_game_id()}")

    # ========================================
    # STEP 4: Retrieve Event from Database
    # ========================================
    print_section("Step 4: Retrieve Event Using Events API")

    game_id = game_event.get_game_id()
    stored_events = event_db.get_events_by_game_id(game_id)

    print(f"✅ Retrieved {len(stored_events)} event(s) for game_id: {game_id}")

    for i, event_data in enumerate(stored_events, 1):
        print(f"\n   Event {i}:")
        print(f"   - Event ID: {event_data['event_id']}")
        print(f"   - Event Type: {event_data['event_type']}")
        print(f"   - Timestamp: {event_data['timestamp']}")

    # Reconstruct GameEvent from database
    print(f"\n🔄 Reconstructing GameEvent from database...")
    retrieved_game = GameEvent.from_database(stored_events[0])
    print(f"✅ Event reconstructed successfully")

    # ========================================
    # STEP 5: Execute Complete 3-Stage Workflow
    # ========================================
    print_header("EXECUTING 3-STAGE SIMULATION WORKFLOW", 80)
    print(f"Matchup: {retrieved_game.get_matchup_description()}")

    # Create workflow optimized for demo with persistence enabled
    workflow = SimulationWorkflow.for_demo(
        database_path=demo_db_path,
        dynasty_id="demo_dynasty"
    )

    print(f"\n🔧 Workflow Configuration:")
    print(f"   Persistence: {'ENABLED' if workflow.is_persistence_enabled() else 'DISABLED'}")
    print(f"   Database: {workflow.get_database_path()}")
    print(f"   Dynasty: {workflow.get_dynasty_id()}")

    # Execute complete 3-stage workflow
    workflow_result = workflow.execute(retrieved_game)

    # ========================================
    # STEP 6: Display Workflow Results
    # ========================================
    print_section("Step 6: Workflow Results Summary")

    if workflow_result.was_successful():
        print(f"✅ Complete workflow successful")

        # Game scores
        scores = workflow_result.get_game_score()
        winner = workflow_result.get_game_winner()
        print(f"\n📊 Final Score:")
        print(f"   Cleveland Browns: {scores['away_score']}")
        print(f"   Minnesota Vikings: {scores['home_score']}")
        print(f"   Winner: {winner.title()}")

        # Game statistics
        print(f"\n📈 Game Statistics:")
        print(f"   Total Plays: {workflow_result.get_total_plays()}")
        print(f"   Game Duration: {workflow_result.get_game_duration()} minutes")
        print(f"   Player Stats Collected: {len(workflow_result.player_stats)}")

        # Persistence results
        if workflow_result.persistence_result:
            print(f"\n💾 Persistence Results:")
            print(f"   Status: {workflow_result.persistence_result.overall_status.value}")
            print(f"   Records Persisted: {workflow_result.persistence_result.total_records_persisted}")
            print(f"   Processing Time: {workflow_result.persistence_result.total_processing_time_ms:.2f}ms")

    else:
        print(f"❌ Workflow failed")
        errors = workflow_result.get_error_summary()
        if errors['simulation_error']:
            print(f"   Simulation Error: {errors['simulation_error']}")
        if errors['persistence_errors']:
            print(f"   Persistence Errors: {len(errors['persistence_errors'])}")
        return

    # ========================================
    # STEP 7: Display Detailed Statistics
    # ========================================
    print_header("DETAILED STATISTICS", 80)

    # Access player stats from workflow result
    all_player_stats = workflow_result.player_stats
    print(f"\n✅ Player statistics from workflow result")
    print(f"   Total players with stats: {len(all_player_stats)}")

    # Filter player stats by team using workflow result methods
    away_player_stats = workflow_result.get_player_stats_by_team(TeamIDs.CLEVELAND_BROWNS)
    home_player_stats = workflow_result.get_player_stats_by_team(TeamIDs.MINNESOTA_VIKINGS)

    print(f"   Cleveland Browns players: {len(away_player_stats)}")
    print(f"   Minnesota Vikings players: {len(home_player_stats)}")

    # ========================================
    # Cleveland Browns Complete Box Score
    # ========================================
    print_header("CLEVELAND BROWNS - COMPLETE BOX SCORE", 80)

    if away_player_stats:
        display_complete_passing_stats(away_player_stats, "Cleveland Browns")
        display_complete_rushing_stats(away_player_stats, "Cleveland Browns")
        display_complete_receiving_stats(away_player_stats, "Cleveland Browns")
        display_complete_defensive_stats(away_player_stats, "Cleveland Browns")
        display_snap_counts(away_player_stats, "Cleveland Browns")
    else:
        print("  No player statistics available")

    # ========================================
    # Minnesota Vikings Complete Box Score
    # ========================================
    print_header("MINNESOTA VIKINGS - COMPLETE BOX SCORE", 80)

    if home_player_stats:
        display_complete_passing_stats(home_player_stats, "Minnesota Vikings")
        display_complete_rushing_stats(home_player_stats, "Minnesota Vikings")
        display_complete_receiving_stats(home_player_stats, "Minnesota Vikings")
        display_complete_defensive_stats(home_player_stats, "Minnesota Vikings")
        display_snap_counts(home_player_stats, "Minnesota Vikings")
    else:
        print("  No player statistics available")

    # ========================================
    # STEP 8: Final Summary
    # ========================================
    print_header("DEMO COMPLETE", 80)

    print("✨ Successfully demonstrated:")
    print("  ✅ Event creation (Browns vs Vikings)")
    print("  ✅ Event storage in isolated database")
    print("  ✅ Event retrieval using Events API")
    print("  ✅ 3-Stage Simulation Workflow (NEW)")
    print("     • Stage 1: Game simulation execution")
    print("     • Stage 2: Player statistics gathering")
    print("     • Stage 3: Complete data persistence")
    print("  ✅ Workflow result management")
    print("  ✅ Box score generation")
    print("  ✅ Toggleable persistence support")

    print(f"\n📁 Demo Database Location:")
    print(f"   {demo_db_path}")
    print(f"   (Isolated - no impact on production databases)")

    # Final database stats
    final_stats = event_db.get_statistics()
    print(f"\n📊 Final Database Stats:")
    print(f"   Total Events: {final_stats.get('total_events', 0)}")
    print(f"   Unique Games: {final_stats.get('unique_games', 0)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
