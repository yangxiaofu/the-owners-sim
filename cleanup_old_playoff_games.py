"""
Cleanup Script: Remove Old Playoff Games

This script removes old playoff games from previous test runs that are
blocking new playoff games from being scheduled.

Usage:
    PYTHONPATH=src python cleanup_old_playoff_games.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from events.event_database_api import EventDatabaseAPI


def cleanup_old_playoff_games(db_path: str, dynasty_id: str, season: int):
    """
    Remove all playoff games for a specific dynasty and season.

    Args:
        db_path: Path to the database file
        dynasty_id: Dynasty ID to clean up
        season: Season year
    """
    print(f"\n{'='*80}")
    print(f"{'PLAYOFF CLEANUP UTILITY'.center(80)}")
    print(f"{'='*80}")
    print(f"Database: {db_path}")
    print(f"Dynasty: {dynasty_id}")
    print(f"Season: {season}")
    print(f"{'='*80}\n")

    # Initialize EventDatabaseAPI
    event_db = EventDatabaseAPI(db_path)

    # Check current playoff games
    print(f"Checking for existing playoff games...")
    all_playoff_events = [
        e for e in event_db.get_events_by_type("GAME")
        if e['game_id'].startswith(f'playoff_{season}_')
    ]

    dynasty_playoff_events = [
        e for e in all_playoff_events
        if e['dynasty_id'] == dynasty_id
    ]

    print(f"Found {len(all_playoff_events)} total playoff games for season {season}")
    print(f"Found {len(dynasty_playoff_events)} playoff games for dynasty '{dynasty_id}'")

    if len(dynasty_playoff_events) == 0:
        print(f"\n✅ No playoff games to clean up for dynasty '{dynasty_id}'")
        return

    # List games to be deleted
    print(f"\nPlayoff games to be deleted:")
    for i, event in enumerate(dynasty_playoff_events, 1):
        print(f"  {i}. {event['game_id']} (Event ID: {event['event_id']})")

    # Confirm deletion
    print(f"\n⚠️  WARNING: This will permanently delete {len(dynasty_playoff_events)} playoff games!")
    response = input("Continue? (yes/no): ")

    if response.lower() != 'yes':
        print(f"\n❌ Cleanup cancelled.")
        return

    # Perform deletion
    print(f"\nDeleting playoff games...")
    deleted_count = event_db.delete_playoff_events_by_dynasty(
        dynasty_id=dynasty_id,
        season=season
    )

    print(f"\n✅ Successfully deleted {deleted_count} playoff game(s)")
    print(f"{'='*80}\n")

    # Verify deletion
    remaining = event_db.get_events_by_dynasty(dynasty_id, event_type="GAME")
    remaining_playoff = [e for e in remaining if e['game_id'].startswith('playoff_')]

    if len(remaining_playoff) == 0:
        print(f"✓ Verified: No playoff games remain for dynasty '{dynasty_id}'")
    else:
        print(f"⚠️  Warning: {len(remaining_playoff)} playoff games still exist")


def cleanup_all_old_playoff_games(db_path: str, season: int):
    """
    Remove ALL playoff games for all dynasties for a specific season.

    This is useful for cleaning up test databases.

    Args:
        db_path: Path to the database file
        season: Season year
    """
    print(f"\n{'='*80}")
    print(f"{'CLEANUP ALL PLAYOFF GAMES'.center(80)}")
    print(f"{'='*80}")
    print(f"Database: {db_path}")
    print(f"Season: {season}")
    print(f"{'='*80}\n")

    event_db = EventDatabaseAPI(db_path)

    # Get all playoff events for this season
    all_events = event_db.get_events_by_type("GAME")
    playoff_events = [
        e for e in all_events
        if e['game_id'].startswith(f'playoff_{season}_')
    ]

    if len(playoff_events) == 0:
        print(f"✅ No playoff games found for season {season}")
        return

    # Group by dynasty
    dynasties = {}
    for event in playoff_events:
        dynasty_id = event['dynasty_id']
        if dynasty_id not in dynasties:
            dynasties[dynasty_id] = []
        dynasties[dynasty_id].append(event)

    print(f"Found {len(playoff_events)} playoff games across {len(dynasties)} dynasties:")
    for dynasty_id, events in dynasties.items():
        print(f"  - {dynasty_id}: {len(events)} games")

    print(f"\n⚠️  WARNING: This will permanently delete ALL {len(playoff_events)} playoff games!")
    response = input("Continue? (yes/no): ")

    if response.lower() != 'yes':
        print(f"\n❌ Cleanup cancelled.")
        return

    # Delete for each dynasty
    total_deleted = 0
    for dynasty_id in dynasties.keys():
        deleted = event_db.delete_playoff_events_by_dynasty(
            dynasty_id=dynasty_id,
            season=season
        )
        total_deleted += deleted
        print(f"  Deleted {deleted} games for dynasty '{dynasty_id}'")

    print(f"\n✅ Successfully deleted {total_deleted} playoff game(s)")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    # Default values
    DB_PATH = "data/database/nfl_simulation.db"
    SEASON = 2025

    print("\nPlayoff Cleanup Utility")
    print("=" * 80)
    print("\nOptions:")
    print("1. Clean up playoff games for specific dynasty")
    print("2. Clean up ALL playoff games for season (all dynasties)")
    print("3. Exit")

    choice = input("\nSelect option (1-3): ")

    if choice == "1":
        dynasty_id = input("Enter dynasty ID: ")
        cleanup_old_playoff_games(DB_PATH, dynasty_id, SEASON)

    elif choice == "2":
        cleanup_all_old_playoff_games(DB_PATH, SEASON)

    else:
        print("\n❌ Exiting...")
