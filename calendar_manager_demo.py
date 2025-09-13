#!/usr/bin/env python3
"""
Calendar Manager Demo

Demonstrates the calendar-based daily simulation system with various event types.
Shows event scheduling, conflict detection, and day-by-day simulation execution.
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from datetime import datetime, date, timedelta
from simulation.calendar_manager import CalendarManager, ConflictResolution
from simulation.events import (
    TrainingEvent, ScoutingEvent, 
    RestDayEvent, AdministrativeEvent
)
# Import GameSimulationEvent separately to handle import dependencies
try:
    from simulation.events.game_simulation_event import GameSimulationEvent
    GAME_SIMULATION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  GameSimulationEvent not available: {e}")
    print("   Demo will run with placeholder events only")
    GAME_SIMULATION_AVAILABLE = False
    # Create a mock GameSimulationEvent for demo purposes
    class GameSimulationEvent(TrainingEvent):
        def __init__(self, date, away_team_id, home_team_id, week=1):
            super().__init__(date, away_team_id, f"Mock game vs team {home_team_id}")
            self.away_team_id = away_team_id
            self.home_team_id = home_team_id
            self.week = week
from constants.team_ids import TeamIDs


def demo_basic_calendar_functionality():
    """Demonstrate basic calendar manager operations"""
    print("=" * 60)
    print("CALENDAR MANAGER DEMO - Basic Functionality")
    print("=" * 60)
    
    # Initialize calendar manager
    start_date = date(2024, 9, 1)  # Start of NFL season
    calendar = CalendarManager(start_date)
    print(f"📅 Initialized calendar starting {start_date}")
    print()
    
    # Create various event types
    events = [
        # NFL Games
        GameSimulationEvent(
            date=datetime(2024, 9, 8),  # Week 1 Sunday
            away_team_id=TeamIDs.DETROIT_LIONS,  # Detroit (22)
            home_team_id=TeamIDs.GREEN_BAY_PACKERS,  # Green Bay (12) 
            week=1
        ),
        GameSimulationEvent(
            date=datetime(2024, 9, 15),  # Week 2 Sunday
            away_team_id=TeamIDs.GREEN_BAY_PACKERS,
            home_team_id=TeamIDs.CHICAGO_BEARS,  # Chicago (6)
            week=2
        ),
        
        # Training events
        TrainingEvent(
            date=datetime(2024, 9, 3),  # Tuesday practice
            team_id=TeamIDs.DETROIT_LIONS,
            training_type="practice"
        ),
        TrainingEvent(
            date=datetime(2024, 9, 4),  # Wednesday practice
            team_id=TeamIDs.DETROIT_LIONS,
            training_type="walkthrough"
        ),
        
        # Scouting events
        ScoutingEvent(
            date=datetime(2024, 9, 5),  # Thursday scouting
            team_id=TeamIDs.GREEN_BAY_PACKERS,
            scouting_target="college_prospects"
        ),
        ScoutingEvent(
            date=datetime(2024, 9, 12),  # Following Thursday
            team_id=TeamIDs.CHICAGO_BEARS,
            scouting_target="opponent_analysis"
        ),
        
        # Rest and administrative days
        RestDayEvent(
            date=datetime(2024, 9, 6),  # Friday rest
            team_id=TeamIDs.DETROIT_LIONS,
            rest_type="recovery_day"
        ),
        AdministrativeEvent(
            date=datetime(2024, 9, 9),  # Monday after game
            team_id=TeamIDs.GREEN_BAY_PACKERS,
            admin_type="contract_negotiations"
        )
    ]
    
    # Schedule all events
    print("📋 Scheduling events:")
    for event in events:
        success, message = calendar.schedule_event(event)
        status = "✅" if success else "❌"
        print(f"{status} {event.event_name}: {message}")
    
    print(f"\n📊 Calendar Statistics:")
    stats = calendar.get_calendar_stats()
    print(f"   Total Events: {stats.total_events}")
    print(f"   Date Range: {stats.date_range}")
    print(f"   Teams Involved: {len(stats.teams_with_events)} teams")
    print(f"   Total Hours: {stats.total_scheduled_hours:.1f} hours")
    print(f"   Events by Type:")
    for event_type, count in stats.events_by_type.items():
        print(f"     - {event_type.value}: {count}")
    print()
    
    return calendar


def demo_conflict_detection():
    """Demonstrate conflict detection and resolution"""
    print("=" * 60) 
    print("CONFLICT DETECTION DEMO")
    print("=" * 60)
    
    calendar = CalendarManager(date(2024, 9, 1), ConflictResolution.REJECT)
    
    # Schedule initial event
    training1 = TrainingEvent(
        date=datetime(2024, 9, 10),
        team_id=TeamIDs.DETROIT_LIONS,
        training_type="practice"
    )
    success, msg = calendar.schedule_event(training1)
    print(f"✅ Scheduled: {training1.event_name}")
    
    # Try to schedule conflicting event (same team, same day)
    training2 = TrainingEvent(
        date=datetime(2024, 9, 10),
        team_id=TeamIDs.DETROIT_LIONS,
        training_type="film_study"
    )
    success, msg = calendar.schedule_event(training2)
    status = "✅" if success else "❌"
    print(f"{status} Conflict test: {msg}")
    
    # Schedule non-conflicting event (different team, same day)
    training3 = TrainingEvent(
        date=datetime(2024, 9, 10),
        team_id=TeamIDs.GREEN_BAY_PACKERS,
        training_type="practice"
    )
    success, msg = calendar.schedule_event(training3)
    print(f"✅ Non-conflict: {training3.event_name}")
    
    print(f"\n📅 Events scheduled for 2024-09-10:")
    events_that_day = calendar.get_events_for_date(date(2024, 9, 10))
    for event in events_that_day:
        print(f"   - {event.event_name}")
    print()


def demo_daily_simulation():
    """Demonstrate day-by-day simulation execution"""
    print("=" * 60)
    print("DAILY SIMULATION DEMO")
    print("=" * 60)
    
    calendar = demo_basic_calendar_functionality()
    
    # Simulate specific days with different event types
    test_dates = [
        date(2024, 9, 3),   # Training day
        date(2024, 9, 5),   # Scouting day
        date(2024, 9, 8),   # Game day - This will run actual game simulation!
        date(2024, 9, 12),  # Mixed activity day
    ]
    
    for test_date in test_dates:
        print(f"🗓️  Simulating {test_date}")
        print("-" * 40)
        
        events_today = calendar.get_events_for_date(test_date)
        if not events_today:
            print("   No events scheduled")
            continue
        
        print(f"   Events scheduled: {len(events_today)}")
        for event in events_today:
            print(f"   - {event.event_name}")
        
        # Execute daily simulation
        day_result = calendar.simulate_day(test_date)
        
        print(f"\n   📈 Day Results:")
        print(f"      Events executed: {day_result.events_executed}")
        print(f"      Success rate: {day_result.success_rate:.1%}")
        print(f"      Total duration: {day_result.total_duration_hours:.1f} hours")
        print(f"      Teams involved: {len(day_result.teams_involved)}")
        
        if day_result.errors:
            print(f"      ⚠️ Errors: {len(day_result.errors)}")
            for error in day_result.errors[:2]:  # Show first 2 errors
                print(f"         - {error}")
        
        print()


def demo_multi_day_progression():
    """Demonstrate advancing through multiple days"""
    print("=" * 60)
    print("MULTI-DAY SIMULATION DEMO")
    print("=" * 60)
    
    calendar = CalendarManager(date(2024, 9, 1))
    
    # Schedule a week of activities for one team
    team_id = TeamIDs.DETROIT_LIONS
    base_date = datetime(2024, 9, 2)
    
    weekly_schedule = [
        ("Monday", TrainingEvent(base_date, team_id, "practice")),
        ("Tuesday", TrainingEvent(base_date + timedelta(days=1), team_id, "walkthrough")),
        ("Wednesday", RestDayEvent(base_date + timedelta(days=2), team_id, "recovery")),
        ("Thursday", ScoutingEvent(base_date + timedelta(days=3), team_id, "opponent_prep")),
        ("Friday", TrainingEvent(base_date + timedelta(days=4), team_id, "light_practice")),
        ("Saturday", RestDayEvent(base_date + timedelta(days=5), team_id, "game_prep")),
        ("Sunday", GameSimulationEvent(
            base_date + timedelta(days=6), 
            away_team_id=TeamIDs.GREEN_BAY_PACKERS, 
            home_team_id=team_id, 
            week=1
        ))
    ]
    
    print("📅 Scheduling week of activities:")
    for day_name, event in weekly_schedule:
        success, msg = calendar.schedule_event(event)
        print(f"   {day_name}: {event.event_name}")
    
    print(f"\n🏃 Running simulation from {base_date.date()} to {(base_date + timedelta(days=6)).date()}")
    
    # Simulate the entire week
    results = calendar.advance_to_date((base_date + timedelta(days=6)).date())
    
    print(f"\n📊 Week Summary:")
    total_events = sum(r.events_executed for r in results)
    successful_events = sum(r.successful_events for r in results)
    total_hours = sum(r.total_duration_hours for r in results)
    
    print(f"   Days simulated: {len(results)}")
    print(f"   Total events: {total_events}")
    print(f"   Success rate: {successful_events/total_events:.1%}" if total_events > 0 else "   No events")
    print(f"   Total activity time: {total_hours:.1f} hours")
    
    print(f"\n📅 Daily breakdown:")
    for i, (day_name, _) in enumerate(weekly_schedule):
        if i < len(results):
            result = results[i]
            print(f"   {day_name}: {result.events_executed} events, {result.total_duration_hours:.1f}h")


def demo_team_scheduling():
    """Demonstrate team availability and scheduling helpers"""
    print("=" * 60)
    print("TEAM SCHEDULING DEMO")
    print("=" * 60)
    
    calendar = CalendarManager(date(2024, 9, 1))
    
    # Schedule some events for Detroit Lions
    lions_events = [
        TrainingEvent(datetime(2024, 9, 5), TeamIDs.DETROIT_LIONS, "practice"),
        GameSimulationEvent(datetime(2024, 9, 8), TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS, 1),
        RestDayEvent(datetime(2024, 9, 9), TeamIDs.DETROIT_LIONS, "recovery")
    ]
    
    for event in lions_events:
        calendar.schedule_event(event)
    
    print("🦁 Detroit Lions scheduled events:")
    lions_schedule = calendar.get_team_schedule(TeamIDs.DETROIT_LIONS)
    for date_key, events in lions_schedule.items():
        print(f"   {date_key}: {[e.event_name for e in events]}")
    
    # Check team availability
    test_dates = [date(2024, 9, 5), date(2024, 9, 7), date(2024, 9, 8)]
    print(f"\n📋 Detroit Lions availability check:")
    for check_date in test_dates:
        available = calendar.is_team_available(TeamIDs.DETROIT_LIONS, check_date)
        status = "Available" if available else "Busy"
        print(f"   {check_date}: {status}")
    
    # Find available dates
    print(f"\n🔍 Finding available dates for Detroit Lions:")
    available_dates = calendar.get_available_dates([TeamIDs.DETROIT_LIONS], 1, date(2024, 9, 10), 10)
    for avail_date in available_dates[:5]:  # Show first 5
        print(f"   Available: {avail_date}")


def main():
    """Run all calendar manager demonstrations"""
    print("🏈 NFL CALENDAR MANAGER DEMONSTRATION")
    print("Showcasing day-by-day simulation with polymorphic events")
    print()
    
    try:
        # Run all demonstration functions
        demo_basic_calendar_functionality()
        print("\n" + "="*60 + "\n")
        
        demo_conflict_detection()
        print("\n" + "="*60 + "\n")
        
        demo_daily_simulation()
        print("\n" + "="*60 + "\n")
        
        demo_multi_day_progression()
        print("\n" + "="*60 + "\n")
        
        demo_team_scheduling()
        
        print("\n" + "=" * 60)
        print("✅ CALENDAR MANAGER DEMO COMPLETED SUCCESSFULLY!")
        print("The calendar system is ready for day-by-day simulation.")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()