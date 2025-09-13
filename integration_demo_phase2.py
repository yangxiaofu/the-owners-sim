#!/usr/bin/env python3
"""
Phase 2 Integration Demo

Demonstrates the complete workflow from Phase 1 data components
to Phase 2 template system, creating a basic NFL schedule.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scheduling.data.team_data import TeamDataManager
from scheduling.data.standings import StandingsProvider
from scheduling.data.rivalries import RivalryDetector
from scheduling.template.basic_scheduler import BasicScheduler
from scheduling.template.schedule_template import SeasonSchedule
from scheduling.template.time_slots import TimeSlot


def main():
    print("🏈 NFL Schedule Generator - Phase 2 Integration Demo")
    print("=" * 60)
    
    # Phase 1: Initialize data components
    print("\n📊 Phase 1: Loading Data Components")
    print("-" * 30)
    
    team_manager = TeamDataManager()
    standings = StandingsProvider()
    rivalry_detector = RivalryDetector()
    
    print(f"✅ Teams loaded: {len(team_manager)} teams")
    print(f"✅ Standings loaded: {len(standings.standings)} team standings")
    print(f"✅ Rivalry detector initialized")
    
    # Demonstrate Phase 1 functionality
    lions = team_manager.get_team(22)
    print(f"\n🦁 Example Team: {lions.full_name}")
    print(f"   Division: {lions.division}")
    print(f"   Rivals: {lions.division_opponents}")
    print(f"   Division Place: {standings.get_division_place(22)}")
    
    # Check rivalries
    packers_rivalry = rivalry_detector.are_rivals(22, 23)  # Lions vs Packers
    print(f"   Lions vs Packers rivalry: {packers_rivalry}")
    
    print("\n🏗️  Phase 2: Template System")
    print("-" * 30)
    
    # Create basic scheduler
    scheduler = BasicScheduler()
    print("✅ Scheduler initialized")
    
    # Generate simple test matchups (not NFL-accurate, just for demo)
    print("📅 Generating test matchups...")
    test_matchups = [
        (22, 23),  # Lions @ Packers
        (23, 22),  # Packers @ Lions  
        (6, 21),   # Bears @ Vikings
        (21, 6),   # Vikings @ Bears
        (17, 18),  # Cowboys @ Giants
        (18, 17),  # Giants @ Cowboys
        (14, 16),  # Chiefs @ Chargers
        (16, 14),  # Chargers @ Chiefs
        (31, 29),  # 49ers @ Seahawks
        (29, 31),  # Seahawks @ 49ers
    ]
    
    print(f"✅ Created {len(test_matchups)} test matchups")
    
    # Identify primetime-worthy games
    primetime_worthy = scheduler.get_primetime_worthy_matchups(test_matchups)
    print(f"⭐ Primetime worthy games: {len(primetime_worthy)}")
    for home, away in primetime_worthy:
        home_team = team_manager.get_team(home)
        away_team = team_manager.get_team(away)
        print(f"   {away_team.full_name} @ {home_team.full_name}")
    
    # Create schedule and assign games
    print(f"\n📋 Creating Season Schedule...")
    schedule = scheduler.schedule_matchups(test_matchups, year=2024)
    
    print(f"✅ Schedule created: {schedule}")
    print(f"   Total slots: {schedule.get_total_slots()}")
    print(f"   Assigned games: {len(schedule.get_assigned_games())}")
    print(f"   Empty slots: {len(schedule.get_empty_slots())}")
    print(f"   Primetime games: {len(schedule.get_primetime_games())}")
    
    # Show some example games
    print(f"\n📺 Sample Scheduled Games")
    print("-" * 30)
    
    assigned_games = schedule.get_assigned_games()[:5]  # First 5 games
    for game in assigned_games:
        home_team = team_manager.get_team(game.home_team_id)
        away_team = team_manager.get_team(game.away_team_id)
        slot_type = "PRIMETIME" if game.is_primetime else "REGULAR"
        print(f"   Week {game.week:2d} {game.time_slot.value:8s} ({slot_type:9s}): "
              f"{away_team.full_name} @ {home_team.full_name}")
    
    # Show team schedule for Lions
    print(f"\n🦁 {lions.full_name} Schedule")
    print("-" * 30)
    
    lions_schedule = schedule.get_team_schedule(22)
    for game in lions_schedule:
        if game.home_team_id == 22:  # Home game
            opponent = team_manager.get_team(game.away_team_id)
            location = "vs"
        else:  # Away game
            opponent = team_manager.get_team(game.home_team_id)
            location = "@"
        
        slot_type = "PRIMETIME" if game.is_primetime else "REGULAR"
        print(f"   Week {game.week:2d} {game.time_slot.value:8s} ({slot_type:9s}): "
              f"{location} {opponent.full_name}")
    
    # Validate schedule
    print(f"\n✅ Schedule Validation")
    print("-" * 30)
    
    is_valid, errors = schedule.validate()
    print(f"Schedule valid: {is_valid}")
    if errors:
        print("Issues found:")
        for error in errors[:3]:  # Show first 3 errors
            print(f"   ⚠️  {error}")
        if len(errors) > 3:
            print(f"   ... and {len(errors) - 3} more issues")
    else:
        print("✅ No validation issues found!")
    
    # Show time slot distribution
    print(f"\n⏰ Time Slot Distribution")
    print("-" * 30)
    
    slot_counts = {}
    for game in schedule.get_assigned_games():
        slot = game.time_slot.value
        slot_counts[slot] = slot_counts.get(slot, 0) + 1
    
    for slot_type, count in sorted(slot_counts.items()):
        print(f"   {slot_type:8s}: {count:2d} games")
    
    print(f"\n🎉 Integration Demo Complete!")
    print(f"Successfully demonstrated Phase 1 → Phase 2 integration")
    print(f"YAGNI approach: Simple, functional, and ready for next phase")


if __name__ == "__main__":
    main()