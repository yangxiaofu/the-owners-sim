"""
Test script for SeasonStatsAggregator

Demonstrates usage and validates functionality.
"""

import sys
import sqlite3
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from statistics.season_stats_aggregator import SeasonStatsAggregator
from database.connection import DatabaseConnection


def test_aggregator():
    """Test the season stats aggregator"""

    db_path = "data/database/nfl_simulation.db"

    # Initialize aggregator
    print("Initializing SeasonStatsAggregator...")
    aggregator = SeasonStatsAggregator(database_path=db_path)
    print("✓ Aggregator initialized")

    # Check if table was created
    print("\nChecking player_season_stats table...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_season_stats'")
    table_exists = cursor.fetchone()
    if table_exists:
        print("✓ player_season_stats table exists")

        # Check indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='player_season_stats'")
        indexes = cursor.fetchall()
        print(f"✓ Found {len(indexes)} indexes on player_season_stats table")
        for idx in indexes:
            print(f"  - {idx[0]}")
    else:
        print("✗ player_season_stats table not found")
        return

    # Check if there are any games in the database
    cursor.execute("SELECT DISTINCT dynasty_id, season FROM games LIMIT 5")
    dynasties_seasons = cursor.fetchall()

    if not dynasties_seasons:
        print("\nNo games found in database. Cannot test aggregation.")
        print("Run a simulation first to populate game data.")
        conn.close()
        return

    print(f"\nFound {len(dynasties_seasons)} dynasty/season combinations in database:")
    for dynasty_id, season in dynasties_seasons:
        print(f"  - Dynasty: {dynasty_id}, Season: {season}")

    # Test backfill on first dynasty/season
    test_dynasty_id, test_season = dynasties_seasons[0]

    print(f"\nTesting backfill for dynasty='{test_dynasty_id}', season={test_season}...")
    try:
        rows_affected = aggregator.backfill_season(
            dynasty_id=test_dynasty_id,
            season=test_season,
            season_type="regular_season"
        )
        print(f"✓ Backfill successful: {rows_affected} player records created/updated")

        # Query some results
        cursor.execute("""
            SELECT player_name, position, team_id, games_played,
                   passing_yards, rushing_yards, receiving_yards,
                   tackles_total, sacks, interceptions
            FROM player_season_stats
            WHERE dynasty_id = ? AND season = ? AND season_type = 'regular_season'
            ORDER BY (passing_yards + rushing_yards + receiving_yards) DESC
            LIMIT 5
        """, (test_dynasty_id, test_season))

        results = cursor.fetchall()
        if results:
            print("\nTop 5 players by total yards:")
            print(f"{'Player':<30} {'Pos':<5} {'Team':<5} {'GP':<4} {'PassYd':<8} {'RushYd':<8} {'RecYd':<8} {'Tkl':<6} {'Sk':<6} {'Int':<5}")
            print("-" * 120)
            for row in results:
                print(f"{row[0]:<30} {row[1]:<5} {row[2]:<5} {row[3]:<4} {row[4]:<8} {row[5]:<8} {row[6]:<8} {row[7]:<6} {row[8]:<6} {row[9]:<5}")

        # Test season leaders query
        print("\n\nTesting season leaders query (passing yards)...")
        leaders = aggregator.get_season_leaders(
            dynasty_id=test_dynasty_id,
            season=test_season,
            stat_category="passing_yards",
            season_type="regular_season",
            limit=5
        )

        if leaders:
            print(f"\nTop 5 passing leaders:")
            print(f"{'Player':<30} {'Pos':<5} {'GP':<4} {'Att':<6} {'Comp':<6} {'Yards':<8} {'TD':<5} {'Rating':<8}")
            print("-" * 90)
            for player in leaders:
                print(f"{player['player_name']:<30} {player['position']:<5} {player['games_played']:<4} "
                      f"{player['passing_attempts']:<6} {player['passing_completions']:<6} "
                      f"{player['passing_yards']:<8} {player['passing_tds']:<5} {player['passer_rating']:<8.1f}")

        # Test update_after_game
        print("\n\nTesting update_after_game...")
        cursor.execute("""
            SELECT game_id FROM games
            WHERE dynasty_id = ? AND season = ?
            LIMIT 1
        """, (test_dynasty_id, test_season))

        game_result = cursor.fetchone()
        if game_result:
            test_game_id = game_result[0]
            rows_updated = aggregator.update_after_game(
                game_id=test_game_id,
                dynasty_id=test_dynasty_id,
                season=test_season,
                season_type="regular_season"
            )
            print(f"✓ update_after_game successful: {rows_updated} records updated")

        print("\n✓ All tests passed!")

    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()

    conn.close()


if __name__ == "__main__":
    print("=" * 80)
    print("SeasonStatsAggregator Test Script")
    print("=" * 80)
    test_aggregator()
