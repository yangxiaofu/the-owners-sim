#!/usr/bin/env python3
"""
Diagnostic script to check what games exist for August 5, 2026
"""
import sqlite3
import json
from datetime import datetime
import sys

DB_PATH = "data/database/nfl_simulation.db"
TARGET_DATE = "2026-08-05"

def check_games(dynasty_id):
    """Check games and database state for the given dynasty."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print(f"\n{'='*80}")
        print(f"CHECKING GAMES FOR {TARGET_DATE} (Dynasty: {dynasty_id})")
        print(f"{'='*80}\n")

        # Check dynasty state
        print("[1] Dynasty State:")
        cursor.execute("""
            SELECT current_date, current_phase, season
            FROM dynasty_state
            WHERE dynasty_id = ?
        """, (dynasty_id,))

        state = cursor.fetchone()
        if state:
            print(f"  Current date: {state[0]}")
            print(f"  Current phase: {state[1]}")
            print(f"  Season: {state[2]}")
        else:
            print(f"  ❌ No dynasty state found for {dynasty_id}")
            return

        print(f"\n[2] All games for {TARGET_DATE}:")
        cursor.execute("""
            SELECT event_id, event_type, dynasty_id, data
            FROM events
            WHERE dynasty_id = ?
            AND json_extract(data, '$.parameters.game_date') LIKE ?
        """, (dynasty_id, f"{TARGET_DATE}%"))

        games = cursor.fetchall()
        print(f"  Found {len(games)} games")

        for i, (event_id, event_type, dynasty, data) in enumerate(games, 1):
            print(f"\n  Game {i}:")
            print(f"    Event ID: {event_id}")
            print(f"    Event Type: {event_type}")
            print(f"    Dynasty: {dynasty}")
            # Parse JSON to get matchup
            params = json.loads(data).get('parameters', {})
            print(f"    Season: {params.get('season', 'N/A')}")
            print(f"    Season Type: {params.get('season_type', 'N/A')}")
            print(f"    Week: {params.get('week', 'N/A')}")
            print(f"    Matchup: {params.get('away_team_id', '?')} @ {params.get('home_team_id', '?')}")
            print(f"    Status: {params.get('status', 'SCHEDULED')}")

        print(f"\n[3] Preseason games for 2026:")
        cursor.execute("""
            SELECT COUNT(*)
            FROM events
            WHERE dynasty_id = ?
            AND event_type = 'GAME'
            AND json_extract(data, '$.parameters.season') = 2026
            AND json_extract(data, '$.parameters.season_type') = 'preseason'
        """, (dynasty_id,))

        count = cursor.fetchone()[0]
        print(f"  Total preseason games scheduled: {count}")

        print(f"\n[4] Regular season games for 2026:")
        cursor.execute("""
            SELECT COUNT(*)
            FROM events
            WHERE dynasty_id = ?
            AND event_type = 'GAME'
            AND json_extract(data, '$.parameters.season') = 2026
            AND json_extract(data, '$.parameters.season_type') = 'regular_season'
        """, (dynasty_id,))

        count = cursor.fetchone()[0]
        print(f"  Total regular season games scheduled: {count}")

        print(f"\n[5] PRESEASON_START milestone:")
        cursor.execute("""
            SELECT data
            FROM events
            WHERE dynasty_id = ?
            AND event_type = 'MILESTONE'
            AND json_extract(data, '$.parameters.milestone_type') = 'PRESEASON_START'
        """, (dynasty_id,))

        milestone = cursor.fetchone()
        if milestone:
            milestone_data = json.loads(milestone[0])
            params = milestone_data.get('parameters', {})
            print(f"  Found PRESEASON_START milestone")
            print(f"  Date: {params.get('game_date', 'N/A')}")
            print(f"  Season: {params.get('season', 'N/A')}")
        else:
            print(f"  ❌ No PRESEASON_START milestone found!")

        conn.close()
        print(f"\n{'='*80}\n")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        dynasty_id = sys.argv[1]
    else:
        # Try to get the most recent dynasty
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT dynasty_id FROM dynasty_state ORDER BY rowid DESC LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            if result:
                dynasty_id = result[0]
                print(f"Using most recent dynasty: {dynasty_id}")
            else:
                print("No dynasties found in database. Please provide dynasty_id as argument.")
                print(f"Usage: python {sys.argv[0]} <dynasty_id>")
                sys.exit(1)
        except Exception as e:
            print(f"Error finding dynasty: {e}")
            print(f"Usage: python {sys.argv[0]} <dynasty_id>")
            sys.exit(1)

    check_games(dynasty_id)
