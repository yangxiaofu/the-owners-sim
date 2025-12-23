#!/usr/bin/env python3
"""
Fix script: Generate and sign UDFAs for existing save.

This script fixes saves where the draft completed but UDFA signings
didn't happen due to lack of undrafted prospects.

Usage:
    PYTHONPATH=src python scripts/fix_udfa_signings.py
"""

import sqlite3
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def get_active_dynasty(db_path: str) -> tuple:
    """Get the active dynasty_id and season from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get most recent dynasty
    cursor.execute("""
        SELECT dynasty_id, current_season
        FROM dynasties
        ORDER BY created_at DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if row:
        return row[0], row[1]
    return None, None


def get_roster_counts(db_path: str, dynasty_id: str) -> dict:
    """Get current roster count for each team."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT team_id, COUNT(*) as count
        FROM players
        WHERE dynasty_id = ? AND team_id IS NOT NULL
        GROUP BY team_id
    """, (dynasty_id,))

    counts = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    # Ensure all 32 teams have entry
    for team_id in range(1, 33):
        if team_id not in counts:
            counts[team_id] = 0

    return counts


def main():
    # Database path
    db_path = "data/database/game_cycle/game_cycle.db"

    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        return 1

    # Get active dynasty
    dynasty_id, season = get_active_dynasty(db_path)
    if not dynasty_id:
        print("ERROR: No dynasty found in database")
        return 1

    print(f"Found dynasty: {dynasty_id}, season: {season}")

    # Get current roster counts
    roster_counts = get_roster_counts(db_path, dynasty_id)
    total_players = sum(roster_counts.values())
    min_roster = min(roster_counts.values())
    max_roster = max(roster_counts.values())

    print(f"Current roster status:")
    print(f"  Total players across all teams: {total_players}")
    print(f"  Min roster size: {min_roster}")
    print(f"  Max roster size: {max_roster}")

    # Calculate how many UDFAs needed
    target_size = 90
    total_needed = sum(max(0, target_size - count) for count in roster_counts.values())

    if total_needed == 0:
        print("\nAll teams already at 90+ players. No UDFA signings needed.")
        return 0

    print(f"\nNeed to sign ~{total_needed} UDFAs to fill all teams to {target_size}")

    # Confirm with user
    response = input("\nProceed with UDFA generation and signing? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return 0

    # Import services
    from game_cycle.database.draft_class_api import DraftClassAPI
    from game_cycle.services.draft_service import DraftService

    # Step 1: Generate UDFA prospects
    print("\n[Step 1] Generating UDFA prospects...")
    draft_api = DraftClassAPI(db_path)

    try:
        udfa_count = draft_api.generate_udfa_prospects(
            dynasty_id=dynasty_id,
            season=season,
            count=total_needed + 200  # Extra buffer
        )
        print(f"  Generated {udfa_count} UDFA prospects")
    except Exception as e:
        print(f"  ERROR generating prospects: {e}")
        return 1

    # Step 2: Execute UDFA signings
    print("\n[Step 2] Signing UDFAs to all teams...")
    draft_service = DraftService(db_path, dynasty_id, season)

    try:
        results = draft_service.execute_udfa_signings(target_roster_size=target_size)
        total_signed = sum(len(players) for players in results.values())
        teams_signed = len(results)

        print(f"  Signed {total_signed} UDFAs across {teams_signed} teams")
    except Exception as e:
        print(f"  ERROR signing UDFAs: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Final status
    print("\n[Step 3] Final roster status:")
    final_counts = get_roster_counts(db_path, dynasty_id)
    for team_id in sorted(final_counts.keys()):
        old_count = roster_counts.get(team_id, 0)
        new_count = final_counts[team_id]
        if new_count != old_count:
            print(f"  Team {team_id:2d}: {old_count} -> {new_count} (+{new_count - old_count})")

    total_final = sum(final_counts.values())
    print(f"\nTotal players: {total_players} -> {total_final}")
    print("\nUDFA signings complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
