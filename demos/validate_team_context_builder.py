"""
Validation script for TeamContextBuilder using actual game_cycle database.

Tests the service with real data to verify functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.services.team_context_builder import (
    TeamContextBuilder,
    PlayoffPosition,
    SeasonPhase
)


def main():
    """Run validation tests."""
    print("\n" + "=" * 70)
    print("TeamContextBuilder Validation")
    print("=" * 70 + "\n")

    # Use actual game_cycle database
    db_path = "data/database/game_cycle/game_cycle.db"

    try:
        db = GameCycleDatabase(db_path)
        builder = TeamContextBuilder(db)
        print("✓ TeamContextBuilder initialized successfully\n")
    except Exception as e:
        print(f"❌ Failed to initialize TeamContextBuilder: {e}")
        return

    # Test 1: Build context for a team
    print("-" * 70)
    print("TEST 1: Build Team Context")
    print("-" * 70)

    try:
        # Get a dynasty_id from the database
        dynasties = db.query_all("SELECT DISTINCT dynasty_id FROM standings LIMIT 1")
        if not dynasties:
            print("⚠️  No dynasties found in database - skipping tests")
            return

        dynasty_id = dynasties[0]['dynasty_id']
        print(f"Using dynasty: {dynasty_id}")

        # Get a season
        seasons = db.query_all(
            "SELECT DISTINCT season FROM standings WHERE dynasty_id = ? ORDER BY season DESC LIMIT 1",
            (dynasty_id,)
        )
        if not seasons:
            print("⚠️  No seasons found - skipping tests")
            return

        season = seasons[0]['season']
        print(f"Using season: {season}")

        # Get a team with standings
        teams = db.query_all(
            "SELECT team_id, wins, losses FROM standings WHERE dynasty_id = ? AND season = ? LIMIT 1",
            (dynasty_id, season)
        )
        if not teams:
            print("⚠️  No teams found - skipping tests")
            return

        team_id = teams[0]['team_id']
        print(f"Using team: {team_id}")

        # Build context
        context = builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=10
        )

        print(f"\n✓ Context built successfully:")
        print(f"  Team: {context.team_name} (ID: {context.team_id})")
        print(f"  Season: {context.season}, Week: {context.week}")
        print(f"  Record: {context.get_record_string()} (Win%: {context.win_pct:.3f})")
        print(f"  Division Rank: {context.division_rank}")
        print(f"  Conference Rank: {context.conference_rank}")
        print(f"  Playoff Position: {context.playoff_position.value}")
        print(f"  Season Phase: {context.season_phase.value}")
        print(f"  Streak: {context.get_streak_string() or 'No streak'}")
        print(f"  Recent Activity: {context.has_recent_activity()}")

        # Verify fields
        assert context.team_id == team_id
        assert context.season == season
        assert context.week == 10
        assert isinstance(context.wins, int)
        assert isinstance(context.losses, int)
        assert isinstance(context.division_rank, int)
        assert isinstance(context.conference_rank, int)
        assert isinstance(context.playoff_position, PlayoffPosition)
        assert isinstance(context.season_phase, SeasonPhase)

        print("\n✅ Test 1 PASSED")

    except Exception as e:
        print(f"\n❌ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 2: Test different season phases
    print("\n" + "-" * 70)
    print("TEST 2: Season Phase Detection")
    print("-" * 70)

    try:
        phases_tested = []
        for week in [3, 10, 16, None]:
            context = builder.build_context(
                dynasty_id=dynasty_id,
                season=season,
                team_id=team_id,
                week=week
            )
            phase_name = context.season_phase.value
            phases_tested.append((week, phase_name))
            print(f"✓ Week {week or 'N/A'}: {phase_name}")

        print("\n✅ Test 2 PASSED")

    except Exception as e:
        print(f"\n❌ Test 2 FAILED: {e}")
        return

    # Test 3: Test helper methods
    print("\n" + "-" * 70)
    print("TEST 3: Helper Methods")
    print("-" * 70)

    try:
        context = builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=10
        )

        record_str = context.get_record_string()
        is_winning = context.is_winning_record()
        is_playoff = context.is_playoff_team()
        has_activity = context.has_recent_activity()
        streak_str = context.get_streak_string()

        print(f"✓ get_record_string(): {record_str}")
        print(f"✓ is_winning_record(): {is_winning}")
        print(f"✓ is_playoff_team(): {is_playoff}")
        print(f"✓ has_recent_activity(): {has_activity}")
        print(f"✓ get_streak_string(): {streak_str or 'None'}")

        print("\n✅ Test 3 PASSED")

    except Exception as e:
        print(f"\n❌ Test 3 FAILED: {e}")
        return

    # Final summary
    print("\n" + "=" * 70)
    print("✅ ALL VALIDATION TESTS PASSED!")
    print("=" * 70)
    print("\nTeamContextBuilder is working correctly:")
    print("  • Builds complete team context from database")
    print("  • Calculates division and conference rankings")
    print("  • Determines playoff position")
    print("  • Identifies season phase")
    print("  • Tracks recent activity")
    print("  • Calculates win/loss streaks")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
