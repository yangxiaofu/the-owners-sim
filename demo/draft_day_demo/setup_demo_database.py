"""
Database Setup Script for Draft Day Demo

Creates isolated SQLite database for draft day demonstration using production
schema and components. Generates 224 draft prospects using DraftClassAPI and
creates mock 2025 season standings for realistic draft order calculation.

This script provides a clean, isolated environment for testing draft functionality
without affecting the main simulation database.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from database.connection import DatabaseConnection
from database.draft_class_api import DraftClassAPI
from database.dynasty_database_api import DynastyDatabaseAPI


def setup_draft_demo_database(db_path: str, force: bool = False) -> bool:
    """
    Create and populate isolated SQLite database for draft day demo.

    Creates a complete, production-ready database with:
    - Dynasty record ("draft_day_demo")
    - 224 draft prospects for 2026 season (via DraftClassAPI)
    - Mock 2025 season standings for all 32 teams
    - Realistic win-loss records for draft order calculation

    This function uses production database schema and components to ensure
    the demo environment matches real simulation behavior.

    Args:
        db_path: Path to SQLite database file (e.g., "demo/draft_day_demo/draft_demo.db")
        force: If True, overwrite existing database. If False, raise error if exists.

    Returns:
        True if database setup successful, False otherwise

    Raises:
        FileExistsError: If database already exists and force=False

    Example:
        >>> # Create new database
        >>> success = setup_draft_demo_database("demo/draft_day_demo/draft_demo.db")
        >>> if success:
        ...     print("Database ready for draft simulation!")
        >>>
        >>> # Recreate existing database
        >>> success = setup_draft_demo_database("draft_demo.db", force=True)
    """
    try:
        # Ensure database directory exists
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if database already exists
        if db_file.exists() and not force:
            raise FileExistsError(
                f"Database already exists: {db_path}\n"
                f"Use force=True to overwrite or delete the file manually."
            )

        # Remove existing database if force=True
        if db_file.exists() and force:
            db_file.unlink()
            print(f"Removed existing database: {db_path}")

        print(f"\nCreating draft demo database: {db_path}")
        print("=" * 70)

        # Step 1: Initialize database with production schema
        print("\n[1/5] Initializing database schema...")
        db_conn = DatabaseConnection(db_path)
        db_conn.initialize_database()
        print("✓ Database schema created")

        # Step 2: Create dynasty record
        print("\n[2/5] Creating dynasty record...")
        dynasty_id = "draft_day_demo"
        dynasty_api = DynastyDatabaseAPI(db_path)

        # Create dynasty with no user team (league-wide simulation)
        success = dynasty_api.create_dynasty_record(
            dynasty_id=dynasty_id,
            dynasty_name="Draft Day Demo Dynasty",
            owner_name="Demo User",
            team_id=None  # No user team for demo
        )

        if not success:
            raise RuntimeError("Failed to create dynasty record")

        print(f"✓ Dynasty created: {dynasty_id}")

        # Step 3: Generate draft class using DraftClassAPI
        print("\n[3/5] Generating draft prospects (2026 draft class)...")
        draft_api = DraftClassAPI(db_path)

        # Generate 224 prospects (7 rounds × 32 teams)
        prospects_created = draft_api.generate_draft_class(
            dynasty_id=dynasty_id,
            season=2026
        )
        print(f"✓ {prospects_created} draft prospects generated")

        # Step 4: Create mock 2025 season standings
        print("\n[4/5] Creating mock 2025 season standings...")
        standings_created = _create_mock_standings(db_path, dynasty_id)
        print(f"✓ {standings_created} team standings records created")

        # Step 5: Generate draft order based on standings
        print("\n[5/5] Generating 2026 draft order...")
        draft_picks = _create_draft_order(db_path, dynasty_id)
        print(f"✓ {draft_picks} draft picks generated (7 rounds × 32 teams)")

        # Verify database setup
        print("\n" + "=" * 70)
        print("Database Setup Summary")
        print("=" * 70)

        with sqlite3.connect(db_path) as conn:
            # Count draft prospects
            cursor = conn.execute(
                "SELECT COUNT(*) FROM draft_prospects WHERE dynasty_id = ?",
                (dynasty_id,)
            )
            prospect_count = cursor.fetchone()[0]

            # Count standings
            cursor = conn.execute(
                "SELECT COUNT(*) FROM standings WHERE dynasty_id = ? AND season = 2025",
                (dynasty_id,)
            )
            standings_count = cursor.fetchone()[0]

            # Count draft picks
            cursor = conn.execute(
                "SELECT COUNT(*) FROM draft_order WHERE dynasty_id = ? AND season = 2026",
                (dynasty_id,)
            )
            draft_picks_count = cursor.fetchone()[0]

            # Get top 5 prospects
            cursor = conn.execute("""
                SELECT first_name, last_name, position, overall, college
                FROM draft_prospects
                WHERE dynasty_id = ?
                ORDER BY overall DESC
                LIMIT 5
            """, (dynasty_id,))
            top_prospects = cursor.fetchall()

        print(f"Dynasty ID: {dynasty_id}")
        print(f"Draft Prospects: {prospect_count}")
        print(f"Standings Records: {standings_count}")
        print(f"Draft Picks: {draft_picks_count}")
        print(f"\nTop 5 Prospects (by overall rating):")
        for i, (first, last, pos, ovr, college) in enumerate(top_prospects, 1):
            print(f"  {i}. {first} {last} ({pos}) - {ovr} OVR - {college}")

        print("\n" + "=" * 70)
        print("✓ Database setup complete!")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n✗ Error setting up database: {e}")
        import traceback
        traceback.print_exc()
        return False


def _create_mock_standings(db_path: str, dynasty_id: str) -> int:
    """
    Create mock 2025 season standings for all 32 NFL teams.

    Generates realistic win-loss records with linear distribution:
    - Worst team (pick #1): 2-15 record
    - Best team (pick #32): 14-3 record
    - Teams in between: Linear interpolation with fractional precision

    This creates proper draft order (worst team picks first) and realistic
    strength of schedule calculations.

    Args:
        db_path: Path to database
        dynasty_id: Dynasty identifier

    Returns:
        Number of standings records created (should be 32)
    """
    # Generate win-loss records with realistic distribution
    # Teams ordered by draft position (1 = worst record, 32 = best record)
    # Total games = 17 (current NFL season length)
    # Distribution spans 2-15 (worst) to 14-3 (best)

    # Pre-defined win distribution for realistic variety (32 teams, 2-14 wins)
    # Multiple teams can have same record (like real NFL)
    wins_distribution = [
        2, 3, 3, 4, 4, 5, 5, 6, 6, 7,      # Bottom 10 teams (2-7 wins)
        7, 8, 8, 8, 9, 9, 9, 10, 10, 10,   # Middle 10 teams (7-10 wins)
        11, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 14  # Top 12 teams (11-14 wins)
    ]

    standings_data = []

    for draft_position in range(1, 33):
        # Teams indexed 0-31, draft_position is 1-32
        wins = wins_distribution[draft_position - 1]
        losses = 17 - wins
        ties = 0

        # Calculate points (approximate based on wins)
        # Average NFL team scores ~21-24 points per game
        points_for = int(22 * 17 + (wins - 8.5) * 20)  # Better teams score more
        points_against = int(22 * 17 - (wins - 8.5) * 20)  # Better teams allow less

        # Simple home/away split (roughly 60-40 home advantage)
        home_games = 9
        away_games = 8
        home_wins = int(wins * 0.6)
        away_wins = wins - home_wins
        home_losses = home_games - home_wins
        away_losses = away_games - away_wins

        standings_data.append({
            'team_id': draft_position,  # Use draft position as team_id for simplicity
            'wins': wins,
            'losses': losses,
            'ties': ties,
            'points_for': points_for,
            'points_against': points_against,
            'home_wins': home_wins,
            'home_losses': home_losses,
            'away_wins': away_wins,
            'away_losses': away_losses
        })

    # Insert standings into database
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        for data in standings_data:
            conn.execute("""
                INSERT INTO standings (
                    dynasty_id, team_id, season, season_type,
                    wins, losses, ties,
                    division_wins, division_losses, division_ties,
                    conference_wins, conference_losses, conference_ties,
                    home_wins, home_losses, home_ties,
                    away_wins, away_losses, away_ties,
                    points_for, points_against, point_differential
                ) VALUES (?, ?, 2025, 'regular_season', ?, ?, ?, 0, 0, 0, 0, 0, 0, ?, ?, 0, ?, ?, 0, ?, ?, ?)
            """, (
                dynasty_id,
                data['team_id'],
                data['wins'],
                data['losses'],
                data['ties'],
                data['home_wins'],
                data['home_losses'],
                data['away_wins'],
                data['away_losses'],
                data['points_for'],
                data['points_against'],
                data['points_for'] - data['points_against']  # point_differential
            ))

        conn.commit()

    return len(standings_data)


def _create_draft_order(db_path: str, dynasty_id: str) -> int:
    """
    Generate 2026 draft order based on 2025 standings.

    Creates simple draft order where team_id = draft position:
    - Team 1 picks first (worst record: 2-15)
    - Team 32 picks last (best record: 14-3)
    - 7 rounds × 32 teams = 224 total picks

    Args:
        db_path: Path to database
        dynasty_id: Dynasty identifier

    Returns:
        Number of draft picks created (should be 224 = 7 rounds × 32 teams)
    """
    # Generate 7 rounds of draft picks
    NUM_ROUNDS = 7
    TEAMS_PER_ROUND = 32

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        overall_pick = 1

        for round_num in range(1, NUM_ROUNDS + 1):
            for pick_in_round in range(1, TEAMS_PER_ROUND + 1):
                # Team ID matches draft position (1 = worst, 32 = best)
                team_id = pick_in_round

                conn.execute("""
                    INSERT INTO draft_order (
                        dynasty_id, season, round_number, pick_in_round, overall_pick,
                        original_team_id, current_team_id, is_executed,
                        is_compensatory, comp_round_end, acquired_via_trade
                    ) VALUES (?, 2026, ?, ?, ?, ?, ?, 0, 0, 0, 0)
                """, (
                    dynasty_id,
                    round_num,
                    pick_in_round,
                    overall_pick,
                    team_id,
                    team_id
                ))

                overall_pick += 1

        conn.commit()

    return NUM_ROUNDS * TEAMS_PER_ROUND


if __name__ == "__main__":
    """
    Main entry point for database setup script.

    Usage:
        python setup_demo_database.py [db_path] [--force]

    Args:
        db_path: Optional path to database file (default: draft_demo.db in current directory)
        --force: Overwrite existing database without prompting

    Examples:
        # Create database in default location
        python setup_demo_database.py

        # Create database at custom path
        python setup_demo_database.py /tmp/my_draft.db

        # Recreate existing database (overwrite)
        python setup_demo_database.py --force

        # Custom path with force
        python setup_demo_database.py /tmp/my_draft.db --force
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Create isolated draft day demo database with 224 prospects and mock standings"
    )
    parser.add_argument(
        'db_path',
        nargs='?',
        default=str(Path(__file__).parent / "draft_demo.db"),
        help="Path to database file (default: draft_demo.db)"
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help="Overwrite existing database if it exists"
    )

    args = parser.parse_args()

    # Run setup
    success = setup_draft_demo_database(args.db_path, force=args.force)

    # Exit with appropriate status code
    sys.exit(0 if success else 1)
