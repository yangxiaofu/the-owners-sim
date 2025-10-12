#!/usr/bin/env python3
"""
Playoff Duplicate Inspector

Analyzes a database to detect and report duplicate playoff games.

Usage:
    PYTHONPATH=src python demo/playoff_tester_demo/inspect_playoff_duplicates.py [database_path] [dynasty_id] [season]

If no arguments provided, prompts for manual input.
"""

import sys
import sqlite3
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))


def inspect_playoff_duplicates(database_path: str, dynasty_id: str, season: int) -> Dict[str, Any]:
    """
    Inspect database for duplicate playoff games.

    Args:
        database_path: Path to SQLite database
        dynasty_id: Dynasty identifier
        season: Season year

    Returns:
        Dictionary with inspection results
    """
    print(f"\n{'='*80}")
    print(f"PLAYOFF DUPLICATE INSPECTOR")
    print(f"{'='*80}")
    print(f"Database: {database_path}")
    print(f"Dynasty: {dynasty_id}")
    print(f"Season: {season}")
    print(f"{'='*80}\n")

    # Connect to database
    try:
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return {"error": str(e)}

    results = {
        "database_path": database_path,
        "dynasty_id": dynasty_id,
        "season": season,
        "total_playoff_events": 0,
        "unique_games": 0,
        "duplicate_games": [],
        "games_by_round": {},
        "events": []
    }

    try:
        # Query all playoff events for this dynasty and season
        query = """
            SELECT
                event_id,
                game_id,
                event_type,
                dynasty_id,
                timestamp,
                data
            FROM events
            WHERE dynasty_id = ?
            AND event_type = 'GAME'
            AND game_id LIKE 'playoff_%'
            ORDER BY game_id, timestamp
        """

        cursor.execute(query, (dynasty_id,))
        rows = cursor.fetchall()

        results["total_playoff_events"] = len(rows)

        print(f"📊 Found {len(rows)} total playoff events\n")

        if len(rows) == 0:
            print("⚠️  No playoff events found for this dynasty/season")
            return results

        # Group by game_id
        games_dict: Dict[str, List[Dict[str, Any]]] = {}

        for row in rows:
            event_data = {
                "event_id": row["event_id"],
                "game_id": row["game_id"],
                "event_type": row["event_type"],
                "dynasty_id": row["dynasty_id"],
                "timestamp": row["timestamp"],
                "data": row["data"]
            }

            game_id = row["game_id"]

            if game_id not in games_dict:
                games_dict[game_id] = []

            games_dict[game_id].append(event_data)
            results["events"].append(event_data)

        # Analyze for duplicates
        results["unique_games"] = len(games_dict)

        print(f"🎯 Unique game_ids: {len(games_dict)}\n")

        # Count by round
        round_counts = {
            "wild_card": 0,
            "divisional": 0,
            "conference": 0,
            "super_bowl": 0
        }

        # Check for duplicates
        print("📋 Game Analysis:\n")
        print(f"{'Game ID':<40} {'Count':<10} {'Status'}")
        print(f"{'-'*40} {'-'*10} {'-'*30}")

        for game_id, events in sorted(games_dict.items()):
            count = len(events)

            # Detect round
            round_name = "unknown"
            for r in ["wild_card", "divisional", "conference", "super_bowl"]:
                if r in game_id:
                    round_name = r
                    round_counts[r] += 1
                    break

            # Determine status
            if count == 1:
                status = "✅ OK"
            else:
                status = f"❌ DUPLICATE ({count} events)"
                results["duplicate_games"].append({
                    "game_id": game_id,
                    "count": count,
                    "round": round_name,
                    "event_ids": [e["event_id"] for e in events]
                })

            print(f"{game_id:<40} {count:<10} {status}")

        results["games_by_round"] = round_counts

        print(f"\n{'='*80}")
        print("ROUND BREAKDOWN")
        print(f"{'='*80}")
        for round_name, count in round_counts.items():
            expected = {"wild_card": 6, "divisional": 4, "conference": 2, "super_bowl": 1}.get(round_name, 0)
            status = "✅" if count == expected else "⚠️"
            print(f"{status} {round_name.title():<20} {count:>3} games (expected: {expected})")

        # Show duplicate details if any
        if results["duplicate_games"]:
            print(f"\n{'='*80}")
            print("DUPLICATE DETAILS")
            print(f"{'='*80}\n")

            for dup in results["duplicate_games"]:
                print(f"🔴 Game: {dup['game_id']}")
                print(f"   Count: {dup['count']}")
                print(f"   Round: {dup['round']}")
                print(f"   Event IDs:")

                # Get details for each event
                for event_id in dup["event_ids"]:
                    cursor.execute("""
                        SELECT event_id, timestamp
                        FROM events
                        WHERE event_id = ?
                    """, (event_id,))

                    event_row = cursor.fetchone()
                    if event_row:
                        print(f"     - {event_row['event_id']}")
                        print(f"       Game Date: {event_row['timestamp']}")
                print()

        # Final summary
        print(f"{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Total playoff events: {results['total_playoff_events']}")
        print(f"Unique games: {results['unique_games']}")
        print(f"Duplicates found: {len(results['duplicate_games'])}")

        if len(results["duplicate_games"]) == 0:
            print("\n✅ No duplicates detected!")
        else:
            print(f"\n❌ Found {len(results['duplicate_games'])} duplicate game(s)")
            print("   This indicates a bug in dynasty isolation or event scheduling.")

        print(f"{'='*80}\n")

    except Exception as e:
        print(f"❌ Error during inspection: {e}")
        import traceback
        traceback.print_exc()
        results["error"] = str(e)

    finally:
        conn.close()

    return results


def main():
    """Main entry point for script."""

    # Parse command line arguments
    if len(sys.argv) >= 4:
        database_path = sys.argv[1]
        dynasty_id = sys.argv[2]
        season = int(sys.argv[3])
    else:
        # Interactive mode
        print("\n🔍 Playoff Duplicate Inspector - Interactive Mode\n")

        database_path = input("Enter database path (default: data/database/nfl_simulation.db): ").strip()
        if not database_path:
            database_path = "data/database/nfl_simulation.db"

        dynasty_id = input("Enter dynasty_id (default: default_dynasty): ").strip()
        if not dynasty_id:
            dynasty_id = "default_dynasty"

        season_input = input("Enter season (default: 2025): ").strip()
        if not season_input:
            season = 2025
        else:
            season = int(season_input)

    # Check if database exists
    if not Path(database_path).exists():
        print(f"\n❌ Database not found: {database_path}")
        print("Please provide a valid database path.")
        sys.exit(1)

    # Run inspection
    results = inspect_playoff_duplicates(database_path, dynasty_id, season)

    # Exit with appropriate code
    if "error" in results:
        sys.exit(1)
    elif results.get("duplicate_games"):
        sys.exit(1)  # Exit with error if duplicates found
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
