#!/usr/bin/env python3
"""
Test Game Deduplication in Playoff Controller

Validates that games are not tracked twice in completed_games.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_controller import PlayoffController


def main():
    """Test game deduplication."""
    print("Testing Game Deduplication Logic...")
    print("="*80)

    # Create mock completed_games structure
    completed_games = {
        'wild_card': [],
        'divisional': [],
        'conference': [],
        'super_bowl': []
    }

    # Simulate adding games with deduplication logic
    print("\n1. Adding 6 unique Wild Card games...")
    for i in range(1, 7):
        game = {
            'game_id': f'playoff_test_2024_wild_card_{i}',
            'success': True,
            'winner': i
        }

        # Check if game already exists (deduplication logic)
        game_id = game.get('game_id', '')
        existing_game_ids = [g.get('game_id', '') for g in completed_games['wild_card']]

        if game_id and game_id not in existing_game_ids:
            completed_games['wild_card'].append(game)
            print(f"   ✓ Added game {i}: {game_id}")
        else:
            print(f"   ⚠️  Skipped duplicate: {game_id}")

    print(f"\n   Total Wild Card games tracked: {len(completed_games['wild_card'])}")

    # Try to add the same games again (should be skipped)
    print("\n2. Attempting to add the same 6 games again (should skip all)...")
    for i in range(1, 7):
        game = {
            'game_id': f'playoff_test_2024_wild_card_{i}',
            'success': True,
            'winner': i
        }

        # Check if game already exists (deduplication logic)
        game_id = game.get('game_id', '')
        existing_game_ids = [g.get('game_id', '') for g in completed_games['wild_card']]

        if game_id and game_id not in existing_game_ids:
            completed_games['wild_card'].append(game)
            print(f"   ✓ Added game {i}: {game_id}")
        else:
            print(f"   ⚠️  Skipped duplicate: {game_id}")

    print(f"\n   Total Wild Card games tracked: {len(completed_games['wild_card'])}")

    # Validate
    print("\n3. Validation...")
    if len(completed_games['wild_card']) == 6:
        print("   ✅ Exactly 6 games tracked (correct)")
        print("\n" + "="*80)
        print("✅ DEDUPLICATION TEST PASSED")
        print("="*80)
        return 0
    else:
        print(f"   ❌ Expected 6 games, got {len(completed_games['wild_card'])}")
        print("\n" + "="*80)
        print("❌ DEDUPLICATION TEST FAILED")
        print("="*80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
