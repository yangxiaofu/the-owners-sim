"""
Database inspection script for regular season game debugging.

This script directly queries the database to see what game events exist,
helping diagnose why regular season games aren't being simulated.
"""
import sqlite3
import json
import sys
from pathlib import Path

def inspect_game_database(db_path: str = "data/database/nfl_simulation.db"):
    """
    Inspect game events in the database.

    Args:
        db_path: Path to SQLite database
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        print("\n" + "=" * 80)
        print("DATABASE INSPECTION: Game Events")
        print("=" * 80)
        print(f"Database: {db_path}\n")

        # 1. Count total events by type
        print("[1] Event Type Summary")
        print("-" * 80)
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM events
            GROUP BY event_type
            ORDER BY count DESC
        """)

        for row in cursor.fetchall():
            print(f"  {row['event_type']:<20} {row['count']:>8} events")

        # 2. Game ID prefix analysis
        print(f"\n[2] Game ID Prefix Analysis")
        print("-" * 80)
        cursor.execute("""
            SELECT
                CASE
                    WHEN game_id LIKE 'preseason_%' THEN 'preseason_' || substr(game_id, 11, 4)
                    WHEN game_id LIKE 'game_%' THEN 'game_' || substr(game_id, 6, 4)
                    WHEN game_id LIKE 'playoff_%' THEN 'playoff_' || substr(game_id, 9, 4)
                    ELSE 'unknown'
                END as prefix,
                dynasty_id,
                COUNT(*) as count
            FROM events
            WHERE event_type = 'GAME'
            GROUP BY prefix, dynasty_id
            ORDER BY prefix, dynasty_id
        """)

        print(f"{'Prefix':<20} {'Dynasty ID':<30} {'Count':>8}")
        print("-" * 80)
        for row in cursor.fetchall():
            print(f"{row['prefix']:<20} {row['dynasty_id']:<30} {row['count']:>8}")

        # 3. Dynasty-specific game counts
        print(f"\n[3] Games Per Dynasty")
        print("-" * 80)
        cursor.execute("""
            SELECT
                dynasty_id,
                COUNT(CASE WHEN game_id LIKE 'preseason_%' THEN 1 END) as preseason,
                COUNT(CASE WHEN game_id LIKE 'game_%' THEN 1 END) as regular,
                COUNT(CASE WHEN game_id LIKE 'playoff_%' THEN 1 END) as playoff,
                COUNT(*) as total
            FROM events
            WHERE event_type = 'GAME'
            GROUP BY dynasty_id
        """)

        print(f"{'Dynasty ID':<30} {'Preseason':>10} {'Regular':>10} {'Playoff':>10} {'Total':>10}")
        print("-" * 80)
        for row in cursor.fetchall():
            print(f"{row['dynasty_id']:<30} {row['preseason']:>10} {row['regular']:>10} "
                  f"{row['playoff']:>10} {row['total']:>10}")

        # 4. Sample regular season games
        print(f"\n[4] Sample Regular Season Game Events")
        print("-" * 80)
        cursor.execute("""
            SELECT game_id, dynasty_id, data
            FROM events
            WHERE event_type = 'GAME'
            AND game_id LIKE 'game_%'
            LIMIT 5
        """)

        for row in cursor.fetchall():
            game_id = row['game_id']
            dynasty_id = row['dynasty_id']
            data = json.loads(row['data'])
            params = data.get('parameters', {})

            print(f"\nGame ID: {game_id}")
            print(f"  Dynasty: {dynasty_id}")
            print(f"  Season: {params.get('season')}")
            print(f"  Week: {params.get('week')}")
            print(f"  Game Date: {params.get('game_date')}")
            print(f"  Season Type: {params.get('season_type')}")
            print(f"  Home Team: {params.get('home_team_id')}")
            print(f"  Away Team: {params.get('away_team_id')}")
            print(f"  Has Results: {data.get('results') is not None}")

        # 5. Check for simulated vs unsimulated games
        print(f"\n[5] Simulation Status (Regular Season)")
        print("-" * 80)
        cursor.execute("""
            SELECT
                dynasty_id,
                COUNT(CASE WHEN json_extract(data, '$.results') IS NULL THEN 1 END) as not_simulated,
                COUNT(CASE WHEN json_extract(data, '$.results') IS NOT NULL THEN 1 END) as simulated
            FROM events
            WHERE event_type = 'GAME'
            AND game_id LIKE 'game_%'
            GROUP BY dynasty_id
        """)

        print(f"{'Dynasty ID':<30} {'Not Simulated':>15} {'Simulated':>15}")
        print("-" * 80)
        for row in cursor.fetchall():
            print(f"{row['dynasty_id']:<30} {row['not_simulated']:>15} {row['simulated']:>15}")

        # 6. Date range of games
        print(f"\n[6] Date Range of Regular Season Games")
        print("-" * 80)
        cursor.execute("""
            SELECT
                dynasty_id,
                MIN(json_extract(data, '$.parameters.game_date')) as first_game,
                MAX(json_extract(data, '$.parameters.game_date')) as last_game
            FROM events
            WHERE event_type = 'GAME'
            AND game_id LIKE 'game_%'
            GROUP BY dynasty_id
        """)

        print(f"{'Dynasty ID':<30} {'First Game':<15} {'Last Game':<15}")
        print("-" * 80)
        for row in cursor.fetchall():
            print(f"{row['dynasty_id']:<30} {row['first_game']:<15} {row['last_game']:<15}")

        print("\n" + "=" * 80)
        print("INSPECTION COMPLETE")
        print("=" * 80 + "\n")

    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

    return True


if __name__ == "__main__":
    # Get database path from command line or use default
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/database/nfl_simulation.db"

    # Run inspection
    success = inspect_game_database(db_path)

    sys.exit(0 if success else 1)
