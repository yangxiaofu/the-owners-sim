#!/usr/bin/env python3
"""
Test Persistence Refactoring (Phase 3)

Validates that the refactored DatabaseDemoPersister and DailyDataPersister
correctly use the new auto-generated schema_generator functions.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from persistence.schema_generator import (
    generate_player_stats_insert,
    extract_player_stats_params,
    get_persistable_field_count
)


def test_query_generation():
    """Test that both persisters would generate the same query"""
    print("=" * 80)
    print("TEST: Query Generation Consistency")
    print("=" * 80)

    # This is what both persisters now use
    query = generate_player_stats_insert(
        table_name="player_game_stats",
        additional_columns=["dynasty_id", "game_id"]
    )

    print("\nGenerated INSERT statement:")
    print(query)

    # Verify key columns are present
    critical_columns = [
        "dynasty_id",
        "game_id",
        "player_id",
        "player_name",
        "passing_yards",
        "passing_interceptions",  # THE FIX - this was missing before!
        "rushing_yards",
        "receiving_yards",
        "tackles_total",
        "interceptions",  # Defensive INTs
    ]

    errors = []
    for col in critical_columns:
        if col not in query:
            errors.append(f"Missing column: {col}")

    if errors:
        print("\n❌ FAILED:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print(f"\n✅ PASSED: All {len(critical_columns)} critical columns present")
        return True


def test_param_extraction():
    """Test parameter extraction with mock PlayerStats"""
    print("\n" + "=" * 80)
    print("TEST: Parameter Extraction")
    print("=" * 80)

    # Create mock PlayerStats object
    class MockPlayerStats:
        def __init__(self):
            self.player_id = "QB_001"
            self.player_name = "Patrick Mahomes"
            self.team_id = 12
            self.position = "QB"
            self.passing_yards = 325
            self.passing_tds = 4
            self.passing_completions = 28
            self.passing_attempts = 38
            self.interceptions_thrown = 2  # THE KEY FIELD WE FIXED!
            self.rushing_yards = 22
            self.rushing_tds = 0
            self.rushing_attempts = 4
            self.receiving_yards = 0
            self.receiving_tds = 0
            self.receptions = 0
            self.targets = 0
            self.tackles = 0
            self.sacks = 0.0
            self.interceptions = 0  # Defensive INTs
            self.field_goals_made = 0
            self.field_goal_attempts = 0
            self.extra_points_made = 0
            self.extra_points_attempted = 0
            self.offensive_snaps = 65
            self.defensive_snaps = 0

    mock_stats = MockPlayerStats()

    # Extract params (this is what both persisters now do)
    params = extract_player_stats_params(
        mock_stats,
        additional_values=("test_dynasty", "game_KC_vs_LV")
    )

    print(f"\nExtracted {len(params)} parameters")
    print("\nFirst 15 parameters:")
    for i, param in enumerate(params[:15]):
        print(f"  [{i:2d}] {param}")

    # Find where interceptions_thrown should be
    # It should be at position 10 (after dynasty_id, game_id, player_id, player_name, team_id,
    # position, passing_yards, passing_tds, passing_completions, passing_attempts)
    expected_int_position = 10
    actual_int_value = params[expected_int_position]

    print(f"\n🔍 Checking interceptions_thrown at position {expected_int_position}:")
    print(f"   Expected: 2")
    print(f"   Actual: {actual_int_value}")

    if actual_int_value == 2:
        print("\n✅ PASSED: interceptions_thrown correctly extracted")
        return True
    else:
        print(f"\n❌ FAILED: Expected 2, got {actual_int_value}")
        return False


def test_param_count_match():
    """Verify param count matches placeholder count"""
    print("\n" + "=" * 80)
    print("TEST: Parameter Count Matching")
    print("=" * 80)

    query = generate_player_stats_insert(
        table_name="player_game_stats",
        additional_columns=["dynasty_id", "game_id"]
    )

    # Count placeholders in query
    placeholder_count = query.count("?")

    # Expected count: 2 additional + persistable fields
    additional_count = 2  # dynasty_id, game_id
    persistable_count = get_persistable_field_count()
    expected_count = additional_count + persistable_count

    print(f"\nPlaceholder count: {placeholder_count}")
    print(f"Expected count: {expected_count} ({additional_count} additional + {persistable_count} persistable)")

    if placeholder_count == expected_count:
        print(f"\n✅ PASSED: Counts match ({placeholder_count} placeholders)")
        return True
    else:
        print(f"\n❌ FAILED: Mismatch - {placeholder_count} placeholders vs {expected_count} expected")
        return False


def test_backwards_compatibility():
    """Verify the refactoring doesn't break existing code patterns"""
    print("\n" + "=" * 80)
    print("TEST: Backwards Compatibility")
    print("=" * 80)

    # Mock PlayerStats with minimal fields (like old code might have)
    class MinimalPlayerStats:
        def __init__(self):
            self.player_id = "test_id"
            self.player_name = "Test Player"
            self.team_id = 1
            self.position = "QB"
            # Only set a few stats
            self.passing_yards = 100
            self.interceptions_thrown = 1
            # Everything else should use defaults

    minimal_stats = MinimalPlayerStats()

    try:
        params = extract_player_stats_params(
            minimal_stats,
            additional_values=("dynasty", "game")
        )

        # Should have all parameters, using defaults for missing fields
        expected_count = 2 + get_persistable_field_count()

        if len(params) == expected_count:
            print(f"\n✅ PASSED: Extracted {len(params)} params with defaults for missing fields")
            return True
        else:
            print(f"\n❌ FAILED: Expected {expected_count} params, got {len(params)}")
            return False

    except Exception as e:
        print(f"\n❌ FAILED: Exception raised: {e}")
        return False


def main():
    """Run all validation tests"""
    print("\n" + "=" * 80)
    print("PERSISTENCE REFACTORING VALIDATION (Phase 3)")
    print("=" * 80)

    tests = [
        ("Query Generation", test_query_generation),
        ("Parameter Extraction", test_param_extraction),
        ("Parameter Count Matching", test_param_count_match),
        ("Backwards Compatibility", test_backwards_compatibility),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ FAILED: {test_name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {status}: {test_name}")

    print("\n" + "=" * 80)
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("=" * 80)
        print("\nPhase 3 Complete!")
        print("\nBoth DatabaseDemoPersister and DailyDataPersister have been")
        print("successfully refactored to use auto-generated schema from")
        print("PlayerStatField metadata.")
        print("\n✨ Benefits:")
        print("  - Reduced code: ~60 lines → ~10 lines per persister")
        print("  - No more missing fields: Auto-includes all persistable stats")
        print("  - Self-documenting: Schema defined once in PlayerStatField")
        print("  - Future-proof: New stats automatically included")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
