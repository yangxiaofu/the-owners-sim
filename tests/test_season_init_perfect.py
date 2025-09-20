#!/usr/bin/env python
"""
Test Season Initialization with Perfect Scheduler

Verifies that SeasonInitializer can successfully initialize
a complete 272-game NFL season using the PerfectScheduler.
"""

import sys
from pathlib import Path
from datetime import date

# Add parent directories for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simulation.season_initializer import SeasonInitializer


def test_perfect_season_initialization():
    """Test that we can initialize a full 272-game season."""
    print("\n" + "=" * 60)
    print("🏈 TESTING PERFECT SEASON INITIALIZATION")
    print("=" * 60)
    
    # Create initializer
    initializer = SeasonInitializer()
    
    # Initialize 2025 season
    result = initializer.initialize_season(
        season_year=2025,
        dynasty_name="Test Dynasty",
        start_date=None  # Let it calculate the proper NFL start
    )
    
    # Check results
    print("\n📊 INITIALIZATION RESULTS:")
    print("-" * 40)
    
    # Check schedule
    if 'schedule' in result:
        schedule_info = result['schedule']
        total_games = schedule_info.get('total_games', 0)
        print(f"✅ Total games scheduled: {total_games}")
        
        if total_games == 272:
            print("   🎯 PERFECT! All 272 games scheduled!")
        else:
            print(f"   ⚠️  Expected 272 games, got {total_games}")
    
    # Check dynasty
    if 'dynasty' in result:
        dynasty_info = result['dynasty']
        print(f"✅ Dynasty ID: {dynasty_info.get('dynasty_id', 'N/A')[:8]}...")
        print(f"✅ Season Year: {dynasty_info.get('season_year', 'N/A')}")
    
    # Check dates
    if 'dates' in result:
        date_info = result['dates']
        print(f"✅ Season Start: {date_info.get('season_start', 'N/A')}")
        print(f"✅ First Game: {date_info.get('first_game', 'N/A')}")
    
    # Check components
    if 'components' in result:
        components = result['components']
        print("\n📦 COMPONENTS STATUS:")
        for comp, ready in components.items():
            status = "✅" if ready else "❌"
            print(f"   {status} {comp}: {ready}")
    
    # Verify the schedule details if available
    if initializer.schedule:
        print("\n🔍 SCHEDULE VALIDATION:")
        print("-" * 40)
        
        # Get all assigned games
        assigned_games = initializer.schedule.get_assigned_games()
        print(f"Assigned games: {len(assigned_games)}")
        
        # Count games per team
        team_game_counts = {}
        for game in assigned_games:
            team_game_counts[game.home_team_id] = team_game_counts.get(game.home_team_id, 0) + 1
            team_game_counts[game.away_team_id] = team_game_counts.get(game.away_team_id, 0) + 1
        
        # Check each team has 17 games
        all_teams_have_17 = True
        for team_id in range(1, 33):
            count = team_game_counts.get(team_id, 0)
            if count != 17:
                print(f"   ⚠️  Team {team_id}: {count} games (expected 17)")
                all_teams_have_17 = False
        
        if all_teams_have_17:
            print("   🎯 PERFECT! All 32 teams have exactly 17 games!")
        
        # Check primetime games
        primetime_games = initializer.schedule.get_primetime_games()
        print(f"\nPrimetime games: {len(primetime_games)}")
        
        # Show some sample games
        print("\n📅 SAMPLE GAMES (First 5):")
        for i, game in enumerate(assigned_games[:5]):
            print(f"   Week {game.week} {game.time_slot.value}: Team {game.away_team_id} @ Team {game.home_team_id}")
    
    # Final summary
    print("\n" + "=" * 60)
    if result.get('success'):
        total_games = result.get('schedule', {}).get('total_games', 0)
        if total_games == 272:
            print("🎉 SUCCESS! Perfect 272-game season initialized!")
        else:
            print(f"⚠️  Partial success: {total_games}/272 games scheduled")
    else:
        print("❌ Season initialization failed")
    print("=" * 60)
    
    return result


def test_schedule_generation_only():
    """Test just the schedule generation without full initialization."""
    print("\n" + "=" * 60)
    print("🏈 TESTING SCHEDULE GENERATION ONLY")
    print("=" * 60)
    
    from scheduling.generator.simple_scheduler import CompleteScheduler
    
    scheduler = CompleteScheduler()
    schedule = scheduler.generate_full_schedule(2025)
    
    # Check results
    assigned_games = schedule.get_assigned_games()
    print(f"\n✅ Generated {len(assigned_games)} games")
    
    # Validate
    is_valid, errors = schedule.validate()
    if is_valid:
        print("✅ Schedule validation passed!")
    else:
        print(f"⚠️  Schedule validation found {len(errors)} issues")
        for error in errors[:5]:
            print(f"   - {error}")
    
    # Count games per team
    team_counts = {}
    for game in assigned_games:
        team_counts[game.home_team_id] = team_counts.get(game.home_team_id, 0) + 1
        team_counts[game.away_team_id] = team_counts.get(game.away_team_id, 0) + 1
    
    # Check each team
    all_correct = True
    for team_id in range(1, 33):
        count = team_counts.get(team_id, 0)
        if count != 17:
            print(f"Team {team_id}: {count} games")
            all_correct = False
    
    if all_correct:
        print("🎯 PERFECT! All teams have exactly 17 games!")
    
    return len(assigned_games) == 272


if __name__ == "__main__":
    # Test schedule generation alone first
    print("\n🔧 Phase 1: Testing Schedule Generation")
    schedule_success = test_schedule_generation_only()
    
    # Then test full season initialization
    print("\n🔧 Phase 2: Testing Full Season Initialization")
    result = test_perfect_season_initialization()
    
    # Final status
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULTS")
    print("=" * 60)
    print(f"Schedule Generation: {'✅ PASS' if schedule_success else '❌ FAIL'}")
    
    total_games = 0
    if result and 'schedule' in result:
        total_games = result['schedule'].get('total_games', 0)
    
    init_success = total_games == 272
    print(f"Season Initialization: {'✅ PASS' if init_success else '❌ FAIL'} ({total_games}/272 games)")
    print("=" * 60)