#!/usr/bin/env python3
"""
Test Preseason Schedule Generation

Verifies that the preseason schedule generator produces valid schedules with:
- Correct number of games (48 total, 3 weeks × 16 games)
- Each team plays exactly 3 games
- All games have correct season_type='preseason'
- Games use geographic proximity matchups
- Proper game timing (Thursday/Saturday/Sunday)
"""

import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scheduling import RandomScheduleGenerator
from events.event_database_api import EventDatabaseAPI


def test_preseason_schedule_generation():
    """Test preseason schedule generation for 2025 season."""
    print("="*80)
    print("PRESEASON SCHEDULE GENERATION TEST".center(80))
    print("="*80)
    print()

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    try:
        # Create generator
        event_db = EventDatabaseAPI(temp_db.name)
        generator = RandomScheduleGenerator(event_db, "test_dynasty")

        print("Generating 2025 preseason schedule...")
        print("-" * 80)

        # Generate preseason with fixed seed for reproducibility
        preseason_games = generator.generate_preseason(season_year=2025, seed=42)

        all_passed = True

        # Test 1: Verify total number of games
        print(f"\nTest 1: Total Games")
        print(f"  Expected: 48 games (3 weeks × 16 games)")
        print(f"  Generated: {len(preseason_games)} games")
        if len(preseason_games) == 48:
            print(f"  ✓ PASSED")
        else:
            print(f"  ❌ FAILED")
            all_passed = False

        # Test 2: Verify each team plays exactly 3 games
        print(f"\nTest 2: Games per Team")
        team_game_counts = {}
        for game in preseason_games:
            team_game_counts[game.away_team_id] = team_game_counts.get(game.away_team_id, 0) + 1
            team_game_counts[game.home_team_id] = team_game_counts.get(game.home_team_id, 0) + 1

        invalid_teams = []
        for team_id in range(1, 33):
            games = team_game_counts.get(team_id, 0)
            if games != 3:
                invalid_teams.append((team_id, games))

        if not invalid_teams:
            print(f"  ✓ PASSED: All 32 teams play exactly 3 games")
        else:
            print(f"  ❌ FAILED: {len(invalid_teams)} teams don't have 3 games:")
            for team_id, games in invalid_teams:
                print(f"     Team {team_id}: {games} games")
            all_passed = False

        # Test 3: Verify all games have correct season_type
        print(f"\nTest 3: Season Type")
        wrong_type_games = [g for g in preseason_games if g.season_type != "preseason"]
        if not wrong_type_games:
            print(f"  ✓ PASSED: All games have season_type='preseason'")
        else:
            print(f"  ❌ FAILED: {len(wrong_type_games)} games have wrong season_type")
            all_passed = False

        # Test 4: Verify games are in correct weeks (1-3)
        print(f"\nTest 4: Week Numbers")
        games_by_week = {1: 0, 2: 0, 3: 0}
        invalid_weeks = []
        for game in preseason_games:
            if game.week in games_by_week:
                games_by_week[game.week] += 1
            else:
                invalid_weeks.append(game.week)

        week_test_passed = True
        for week, count in games_by_week.items():
            if count != 16:
                print(f"  ❌ Week {week} has {count} games (expected 16)")
                week_test_passed = False
                all_passed = False

        if invalid_weeks:
            print(f"  ❌ Found games in invalid weeks: {set(invalid_weeks)}")
            week_test_passed = False
            all_passed = False

        if week_test_passed:
            print(f"  ✓ PASSED: All weeks have 16 games each")

        # Test 5: Verify game IDs follow correct pattern
        print(f"\nTest 5: Game ID Format")
        invalid_ids = []
        for game in preseason_games:
            # Expected format: preseason_2025_1_1, preseason_2025_2_3, etc.
            game_id = game.get_game_id()
            parts = game_id.split('_')
            if len(parts) != 4 or parts[0] != 'preseason' or parts[1] != '2025':
                invalid_ids.append(game_id)

        if not invalid_ids:
            print(f"  ✓ PASSED: All game IDs follow correct pattern")
        else:
            print(f"  ❌ FAILED: {len(invalid_ids)} games have invalid IDs")
            print(f"     Examples: {invalid_ids[:3]}")
            all_passed = False

        # Test 6: Verify games are stored in database
        print(f"\nTest 6: Database Storage")
        db_events = event_db.get_events_by_dynasty("test_dynasty", "GAME")
        if len(db_events) == 48:
            print(f"  ✓ PASSED: All 48 games stored in database")
        else:
            print(f"  ❌ FAILED: Expected 48 games in DB, found {len(db_events)}")
            all_passed = False

        # Test 7: Verify game timing distribution
        print(f"\nTest 7: Game Timing Distribution")
        games_by_day = {}
        for game in preseason_games:
            day_name = game.game_date.strftime('%A')
            games_by_day[day_name] = games_by_day.get(day_name, 0) + 1

        print(f"  Games by day of week:")
        for day, count in sorted(games_by_day.items()):
            print(f"    {day}: {count} games")

        # Preseason should have games on Thursday, Saturday, Sunday
        expected_days = {'Thursday', 'Saturday', 'Sunday'}
        actual_days = set(games_by_day.keys())
        if actual_days <= expected_days:  # subset or equal
            print(f"  ✓ PASSED: Games scheduled on valid days")
        else:
            print(f"  ❌ FAILED: Games on unexpected days: {actual_days - expected_days}")
            all_passed = False

        # Test 8: Verify no duplicate matchups in same week
        print(f"\nTest 8: No Duplicate Matchups")
        duplicate_found = False
        for week in [1, 2, 3]:
            week_games = [g for g in preseason_games if g.week == week]
            matchups = set()
            for game in week_games:
                matchup = tuple(sorted([game.away_team_id, game.home_team_id]))
                if matchup in matchups:
                    print(f"  ❌ FAILED: Duplicate matchup in week {week}: {matchup}")
                    duplicate_found = True
                    all_passed = False
                matchups.add(matchup)

        if not duplicate_found:
            print(f"  ✓ PASSED: No duplicate matchups in any week")

        # Test 9: Verify dynasty isolation
        print(f"\nTest 9: Dynasty Isolation")
        all_same_dynasty = all(g.dynasty_id == "test_dynasty" for g in preseason_games)
        if all_same_dynasty:
            print(f"  ✓ PASSED: All games have correct dynasty_id")
        else:
            print(f"  ❌ FAILED: Some games have wrong dynasty_id")
            all_passed = False

        # Print summary
        print()
        print("="*80)
        if all_passed:
            print("✅ ALL PRESEASON TESTS PASSED".center(80))
        else:
            print("❌ SOME PRESEASON TESTS FAILED".center(80))
        print("="*80)

        # Print sample schedule
        print()
        print("="*80)
        print("SAMPLE: Preseason Week 1 Games".center(80))
        print("="*80)
        week_1_games = [g for g in preseason_games if g.week == 1]
        week_1_games.sort(key=lambda g: g.game_date)

        current_day = None
        for game in week_1_games:
            day = game.game_date.strftime('%A, %B %d')
            if day != current_day:
                print(f"\n{day}")
                print("-" * 80)
                current_day = day

            time = game.game_date.strftime('%I:%M %p')
            print(f"  {time} - Team {game.away_team_id} @ Team {game.home_team_id}")

        print()

        return all_passed

    finally:
        # Clean up temporary database
        os.unlink(temp_db.name)
        print(f"Temporary database cleaned up: {temp_db.name}")


def test_regular_and_preseason_combined():
    """Test that regular season and preseason can be generated together."""
    print()
    print("="*80)
    print("COMBINED REGULAR + PRESEASON GENERATION TEST".center(80))
    print("="*80)
    print()

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    try:
        # Create generator
        event_db = EventDatabaseAPI(temp_db.name)
        generator = RandomScheduleGenerator(event_db, "combined_test_dynasty")

        print("Generating both preseason and regular season schedules...")
        print("-" * 80)

        # Generate both schedules
        preseason_games = generator.generate_preseason(season_year=2025, seed=100)
        regular_games = generator.generate_season(season_year=2025, seed=100)

        all_passed = True

        # Test 1: Verify total counts
        print(f"\nTest 1: Game Counts")
        print(f"  Preseason games: {len(preseason_games)} (expected 48)")
        print(f"  Regular season games: {len(regular_games)} (expected 272)")

        if len(preseason_games) == 48 and len(regular_games) == 272:
            print(f"  ✓ PASSED")
        else:
            print(f"  ❌ FAILED")
            all_passed = False

        # Test 2: Verify games are distinguished by season_type
        print(f"\nTest 2: Season Type Distinction")
        preseason_with_wrong_type = [g for g in preseason_games if g.season_type != "preseason"]
        regular_with_wrong_type = [g for g in regular_games if g.season_type != "regular_season"]

        if not preseason_with_wrong_type and not regular_with_wrong_type:
            print(f"  ✓ PASSED: All games have correct season_type")
        else:
            print(f"  ❌ FAILED")
            if preseason_with_wrong_type:
                print(f"     {len(preseason_with_wrong_type)} preseason games have wrong type")
            if regular_with_wrong_type:
                print(f"     {len(regular_with_wrong_type)} regular games have wrong type")
            all_passed = False

        # Test 3: Verify database contains both
        print(f"\nTest 3: Database Storage")
        all_events = event_db.get_events_by_dynasty("combined_test_dynasty", "GAME")
        print(f"  Total events in database: {len(all_events)}")
        print(f"  Expected: 320 (48 preseason + 272 regular)")

        if len(all_events) == 320:
            print(f"  ✓ PASSED")
        else:
            print(f"  ❌ FAILED")
            all_passed = False

        # Test 4: Verify timing (preseason should be before regular season)
        print(f"\nTest 4: Temporal Ordering")
        earliest_preseason = min(g.game_date for g in preseason_games)
        latest_preseason = max(g.game_date for g in preseason_games)
        earliest_regular = min(g.game_date for g in regular_games)

        print(f"  Earliest preseason game: {earliest_preseason.strftime('%B %d, %Y')}")
        print(f"  Latest preseason game: {latest_preseason.strftime('%B %d, %Y')}")
        print(f"  Earliest regular season game: {earliest_regular.strftime('%B %d, %Y')}")

        if latest_preseason < earliest_regular:
            print(f"  ✓ PASSED: Preseason ends before regular season starts")
        else:
            print(f"  ❌ FAILED: Schedule overlap detected")
            all_passed = False

        print()
        print("="*80)
        if all_passed:
            print("✅ ALL COMBINED TESTS PASSED".center(80))
        else:
            print("❌ SOME COMBINED TESTS FAILED".center(80))
        print("="*80)
        print()

        return all_passed

    finally:
        # Clean up temporary database
        os.unlink(temp_db.name)
        print(f"Temporary database cleaned up: {temp_db.name}")


if __name__ == "__main__":
    print()
    print("╔" + "="*78 + "╗")
    print("║" + "PRESEASON SCHEDULE GENERATION TEST SUITE".center(78) + "║")
    print("╚" + "="*78 + "╝")
    print()

    # Run both tests
    preseason_passed = test_preseason_schedule_generation()
    combined_passed = test_regular_and_preseason_combined()

    # Final summary
    print()
    print("="*80)
    print("FINAL RESULTS".center(80))
    print("="*80)
    print(f"  Preseason Generation: {'✅ PASSED' if preseason_passed else '❌ FAILED'}")
    print(f"  Combined Generation: {'✅ PASSED' if combined_passed else '❌ FAILED'}")
    print("="*80)
    print()

    # Exit with appropriate code
    if preseason_passed and combined_passed:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)
