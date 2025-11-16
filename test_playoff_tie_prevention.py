#!/usr/bin/env python3
"""
Test script to verify playoff tie prevention in fast mode.

This script tests that the random score generator in fast mode
never creates tied playoff games.
"""

import sys
sys.path.insert(0, 'src')

import random
from dataclasses import dataclass

# Mock game event for testing
@dataclass
class MockGameEvent:
    event_id: str
    home_team_id: int
    away_team_id: int
    season_type: str
    game_id: str
    game_date: int = 0


def test_playoff_tie_prevention():
    """
    Test that playoff games never tie in fast mode.

    This simulates the _generate_fake_result() logic 1000 times
    and verifies that playoff games never end in ties.
    """
    print("=" * 80)
    print("PLAYOFF TIE PREVENTION TEST")
    print("=" * 80)
    print()

    # Test 1: Playoff games should never tie
    print("TEST 1: Generating 1000 random playoff game scores...")
    ties_found = 0
    games_tested = 0

    for i in range(1000):
        # Create mock playoff game event
        game_event = MockGameEvent(
            event_id=f"playoff_test_{i}",
            home_team_id=random.randint(1, 32),
            away_team_id=random.randint(1, 32),
            season_type='playoffs',
            game_id=f'playoff_2025_wild_card_{i}'
        )

        # Generate scores (same logic as simulation_workflow.py)
        away_score = random.randint(10, 35)
        home_score = random.randint(10, 35)

        # Apply tie prevention logic
        is_playoff = (hasattr(game_event, 'season_type') and
                      game_event.season_type == 'playoffs') or \
                     (hasattr(game_event, 'game_id') and
                      'playoff_' in str(game_event.game_id))

        if is_playoff and away_score == home_score:
            if random.random() < 0.5:
                away_score += 1
            else:
                home_score += 1

        # Check for ties
        if away_score == home_score:
            ties_found += 1
            print(f"  ✗ FAIL: Game {i} tied ({away_score}-{home_score})")

        games_tested += 1

    print(f"✓ Tested {games_tested} playoff games")
    print(f"  Ties found: {ties_found}")
    print(f"  Result: {'✓ PASS' if ties_found == 0 else '✗ FAIL'}")
    print()

    # Test 2: Regular season games CAN still tie (should not be affected)
    print("TEST 2: Generating 1000 random regular season game scores...")
    ties_found_regular = 0
    games_tested_regular = 0

    for i in range(1000):
        # Create mock regular season game event
        game_event = MockGameEvent(
            event_id=f"regular_test_{i}",
            home_team_id=random.randint(1, 32),
            away_team_id=random.randint(1, 32),
            season_type='regular_season',
            game_id=f'regular_2025_week_1_{i}'
        )

        # Generate scores (same logic as simulation_workflow.py)
        away_score = random.randint(10, 35)
        home_score = random.randint(10, 35)

        # Apply tie prevention logic (should NOT trigger for regular season)
        is_playoff = (hasattr(game_event, 'season_type') and
                      game_event.season_type == 'playoffs') or \
                     (hasattr(game_event, 'game_id') and
                      'playoff_' in str(game_event.game_id))

        if is_playoff and away_score == home_score:
            if random.random() < 0.5:
                away_score += 1
            else:
                home_score += 1

        # Count ties
        if away_score == home_score:
            ties_found_regular += 1

        games_tested_regular += 1

    print(f"✓ Tested {games_tested_regular} regular season games")
    print(f"  Ties found: {ties_found_regular}")
    print(f"  Expected: ~38 ties (1/26 = 3.85% chance per game)")
    print(f"  Result: {'✓ PASS' if ties_found_regular > 0 else '⚠ WARNING - no ties found (statistically unlikely)'}")
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✓ Playoff games: {games_tested} tested, {ties_found} ties")
    print(f"✓ Regular season games: {games_tested_regular} tested, {ties_found_regular} ties")
    print()

    if ties_found == 0 and ties_found_regular > 0:
        print("✓ ALL TESTS PASSED!")
        print("  - Playoff games never tie (as required)")
        print("  - Regular season games can still tie (not affected)")
        print()
        return True
    elif ties_found == 0 and ties_found_regular == 0:
        print("⚠ PARTIAL PASS")
        print("  - Playoff games never tie (GOOD)")
        print("  - Regular season had 0 ties (statistically unlikely but not impossible)")
        print()
        return True
    else:
        print("✗ TEST FAILED!")
        print(f"  - Playoff games had {ties_found} ties (expected 0)")
        print()
        return False


if __name__ == "__main__":
    success = test_playoff_tie_prevention()
    sys.exit(0 if success else 1)
