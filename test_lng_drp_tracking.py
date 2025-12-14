#!/usr/bin/env python3
"""
Test script to verify LNG (longest reception) and DRP (drops) tracking.
"""

import sys
import sqlite3
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from play_engine.simulation.stats import PlayerStats, PlayerStatsAccumulator
from constants.team_ids import TeamIDs


def test_player_stats_fields():
    """Test that PlayerStats has the new fields."""
    print("=" * 60)
    print("TEST 1: Verify PlayerStats has new fields")
    print("=" * 60)

    stats = PlayerStats(player_name="Test Player", player_number=1, position="WR")

    # Check receiving_long field exists
    assert hasattr(stats, 'receiving_long'), "PlayerStats missing 'receiving_long' field"
    assert stats.receiving_long == 0, "receiving_long should default to 0"
    print("✓ PlayerStats.receiving_long field exists and defaults to 0")

    # Check drops field exists
    assert hasattr(stats, 'drops'), "PlayerStats missing 'drops' field"
    assert stats.drops == 0, "drops should default to 0"
    print("✓ PlayerStats.drops field exists and defaults to 0")

    print()


def test_max_merge_logic():
    """Test that receiving_long uses MAX aggregation, not SUM."""
    print("=" * 60)
    print("TEST 2: Verify receiving_long uses MAX aggregation")
    print("=" * 60)

    accumulator = PlayerStatsAccumulator()

    # Create a fake player stats for multiple catches
    stats1 = PlayerStats(player_name="Test Receiver", player_number=11, position="WR")
    stats1.player_id = 1
    stats1.team_id = TeamIDs.DETROIT_LIONS
    stats1.receptions = 1
    stats1.receiving_yards = 5
    stats1.receiving_long = 5

    stats2 = PlayerStats(player_name="Test Receiver", player_number=11, position="WR")
    stats2.player_id = 1
    stats2.team_id = TeamIDs.DETROIT_LIONS
    stats2.receptions = 1
    stats2.receiving_yards = 22
    stats2.receiving_long = 22

    stats3 = PlayerStats(player_name="Test Receiver", player_number=11, position="WR")
    stats3.player_id = 1
    stats3.team_id = TeamIDs.DETROIT_LIONS
    stats3.receptions = 1
    stats3.receiving_yards = 12
    stats3.receiving_long = 12

    # Add all stats using the private _merge_player_stats method
    accumulator._merge_player_stats(stats1)
    accumulator._merge_player_stats(stats2)
    accumulator._merge_player_stats(stats3)

    # Get merged stats
    merged = accumulator.get_all_players_with_stats()
    receiver_stats = next(s for s in merged if s.player_name == "Test Receiver")

    # Verify receiving_long uses MAX (22), not SUM (39)
    assert receiver_stats.receiving_long == 22, f"Expected receiving_long=22 (MAX), got {receiver_stats.receiving_long}"
    assert receiver_stats.receiving_yards == 39, f"Expected receiving_yards=39 (SUM), got {receiver_stats.receiving_yards}"
    assert receiver_stats.receptions == 3, f"Expected receptions=3, got {receiver_stats.receptions}"

    print(f"✓ Receptions: {receiver_stats.receptions} (SUM)")
    print(f"✓ Receiving Yards: {receiver_stats.receiving_yards} (SUM)")
    print(f"✓ Longest Reception: {receiver_stats.receiving_long} (MAX)")
    print("✓ MAX aggregation working correctly!")
    print()


def test_database_columns():
    """Test that database has the required columns."""
    print("=" * 60)
    print("TEST 3: Verify database schema has columns")
    print("=" * 60)

    db_path = Path(__file__).parent / 'data/database/game_cycle/game_cycle.db'

    if not db_path.exists():
        print(f"⚠ Database not found at {db_path}")
        print("  Skipping database schema test")
        print()
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get column names from player_game_stats
    cursor.execute("PRAGMA table_info(player_game_stats)")
    columns = [row[1] for row in cursor.fetchall()]

    # Check for receiving_long column
    assert 'receiving_long' in columns, "Database missing 'receiving_long' column"
    print("✓ Database has 'receiving_long' column")

    # Check for receiving_drops column
    assert 'receiving_drops' in columns, "Database missing 'receiving_drops' column"
    print("✓ Database has 'receiving_drops' column")

    conn.close()
    print()


def test_aggregator_mapping():
    """Test that CentralizedStatsAggregator has the field mappings in code."""
    print("=" * 60)
    print("TEST 4: Verify stats aggregator mapping")
    print("=" * 60)

    # Read the aggregator source code to verify the mappings exist
    aggregator_path = Path(__file__).parent / 'src/game_management/centralized_stats_aggregator.py'
    with open(aggregator_path, 'r') as f:
        aggregator_code = f.read()

    # Check for receiving_long mapping
    assert 'receiving_long' in aggregator_code, "Aggregator code missing 'receiving_long' mapping"
    assert '"receiving_long"' in aggregator_code or "'receiving_long'" in aggregator_code, "Aggregator missing receiving_long dict key"
    print("✓ Aggregator has 'receiving_long' mapping in code")

    # Check for drops mapping
    assert '"drops"' in aggregator_code or "'drops'" in aggregator_code, "Aggregator missing drops dict key"
    print("✓ Aggregator has 'drops' mapping in code")

    print()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("LNG & DRP TRACKING VERIFICATION TESTS")
    print("=" * 60)
    print()

    try:
        test_player_stats_fields()
        test_max_merge_logic()
        test_database_columns()
        test_aggregator_mapping()

        print("=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print()
        print("Next Steps:")
        print("1. Run a full game simulation: python main2.py")
        print("2. Check box score dialog shows LNG and DRP columns")
        print("3. Verify realistic values (LNG ≤ total yards, DRP = 0-3)")
        print()

        return 0

    except Exception as e:
        print()
        print("=" * 60)
        print("TEST FAILED ✗")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
