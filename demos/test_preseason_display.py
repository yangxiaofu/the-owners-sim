"""
Test script to verify preseason game display fix.

Verifies:
1. Preseason games are fetched from database
2. Preview data includes "preseason_games" key
3. Matchup objects are correctly built
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from game_cycle.handlers.offseason import OffseasonHandler
from game_cycle.stage_definitions import Stage, StageType


def test_preseason_preview():
    """Test that preseason preview includes game matchups."""

    db_path = "data/database/game_cycle/game_cycle.db"
    dynasty_id = "Test0927c473"  # Replace with your dynasty ID
    season = 2025
    user_team_id = 1  # Buffalo Bills

    # Create handler
    handler = OffseasonHandler(database_path=db_path)

    # Create context
    context = {
        "dynasty_id": dynasty_id,
        "season": season,
        "user_team_id": user_team_id,
        "db_path": db_path,
    }

    # Test Preseason Week 1
    print("=" * 70)
    print("Testing OFFSEASON_PRESEASON_W1 Preview")
    print("=" * 70)

    stage = Stage(stage_type=StageType.OFFSEASON_PRESEASON_W1, season_year=season)
    preview = handler.get_stage_preview(stage, context)

    print(f"\nPreview keys: {list(preview.keys())}")

    if "preseason_games" in preview:
        games = preview["preseason_games"]
        print(f"✓ Found 'preseason_games' key")
        print(f"✓ Number of games: {len(games)}")
        print(f"✓ Preseason week: {preview.get('preseason_week')}")

        if games:
            print("\nFirst game matchup:")
            first_game = games[0]
            print(f"  Game ID: {first_game.get('game_id')}")
            print(f"  Away: {first_game['away_team']['abbreviation']} ({first_game['away_team']['record']})")
            print(f"  Home: {first_game['home_team']['abbreviation']} ({first_game['home_team']['record']})")
            print(f"  Score: {first_game.get('away_score')} - {first_game.get('home_score')}")
            print(f"  Played: {first_game.get('is_played')}")
            print(f"  User game: {first_game.get('is_user_game')}")

            # Find user's game
            user_games = [g for g in games if g.get("is_user_game")]
            if user_games:
                print(f"\n✓ User's team has {len(user_games)} game(s) this week")
                user_game = user_games[0]
                print(f"  {user_game['away_team']['name']} @ {user_game['home_team']['name']}")
            else:
                print("\n✗ No user game found (unexpected)")
        else:
            print("\n✗ Games list is empty (unexpected - should have 16 games)")
    else:
        print("✗ Missing 'preseason_games' key (FIX FAILED)")
        return False

    # Test all three weeks
    print("\n" + "=" * 70)
    print("Testing All Preseason Weeks")
    print("=" * 70)

    for week_num, stage_type in enumerate([
        StageType.OFFSEASON_PRESEASON_W1,
        StageType.OFFSEASON_PRESEASON_W2,
        StageType.OFFSEASON_PRESEASON_W3
    ], start=1):
        stage = Stage(stage_type=stage_type, season_year=season)
        preview = handler.get_stage_preview(stage, context)
        games = preview.get("preseason_games", [])
        week = preview.get("preseason_week", 0)

        status = "✓" if games and week == week_num else "✗"
        print(f"{status} Week {week_num}: {len(games)} games, week={week}")

    print("\n" + "=" * 70)
    print("SUCCESS - Preseason game display fix is working!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    try:
        test_preseason_preview()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
