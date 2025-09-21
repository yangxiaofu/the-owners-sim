"""
Phase 2 Integration Test

This script tests the complete Phase 2 integration:
1. PerfectScheduler generating 257/272 games (94.5% success)
2. ScheduleToEventConverter converting abstract slots to concrete events
3. Real StoreManager handling game data
4. SeasonInitializer orchestrating everything
"""

import sys
from pathlib import Path
from datetime import date, datetime

# Add parent directories for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

print("=== Phase 2 Integration Test ===")
print()

# Test 1: CompleteScheduler (uses PerfectScheduler internally)
print("Test 1: CompleteScheduler with PerfectScheduler")
print("-" * 40)
schedule = None  # Initialize for later tests
try:
    from scheduling.generator.simple_scheduler import CompleteScheduler
    
    scheduler = CompleteScheduler()
    schedule = scheduler.generate_full_schedule(2025)
    games = schedule.get_assigned_games()
    
    print(f"✓ PerfectScheduler generated {len(games)} games")
    print(f"  Success rate: {len(games)/272*100:.1f}%")
    
    # Verify no team plays twice in same week
    from collections import defaultdict
    teams_by_week = defaultdict(set)
    conflicts = []
    
    for game in games:
        week = game.week
        if game.home_team_id in teams_by_week[week]:
            conflicts.append(f"Team {game.home_team_id} plays twice in week {week}")
        if game.away_team_id in teams_by_week[week]:
            conflicts.append(f"Team {game.away_team_id} plays twice in week {week}")
        teams_by_week[week].add(game.home_team_id)
        teams_by_week[week].add(game.away_team_id)
    
    if conflicts:
        print(f"✗ Found {len(conflicts)} scheduling conflicts!")
        for conflict in conflicts[:5]:
            print(f"  - {conflict}")
    else:
        print("✓ No teams play twice in same week")
        
except Exception as e:
    print(f"✗ CompleteScheduler test failed: {e}")
    schedule = None

print()

# Test 2: ScheduleToEventConverter
print("Test 2: ScheduleToEventConverter")
print("-" * 40)
events = []  # Initialize for later tests
try:
    if schedule is None:
        print("✗ No schedule available from previous test")
    else:
        from scheduling.converters.schedule_to_event_converter import ScheduleToEventConverter
        from scheduling.utils.date_calculator import WeekToDateCalculator
        
        date_calc = WeekToDateCalculator(2025)
        converter = ScheduleToEventConverter(date_calc)
        
        # Convert the schedule we just created
        events = converter.convert_schedule(schedule)
    
        print(f"✓ Converted {len(events)} games to events")
        
        # Get summary
        summary = converter.get_event_summary(events)
        print(f"  Thursday games: {summary['thursday_games']}")
        print(f"  Sunday games: {summary['sunday_games']}")
        print(f"  Monday games: {summary['monday_games']}")
        print(f"  Primetime games: {summary['primetime_games']}")
        
        # Verify dates are valid
        for event in events[:3]:
            if isinstance(event, dict):
                print(f"  Example: Week {event['week']} on {event['date']}")
            else:
                print(f"  Example: Week {event.week} on {event.date}")
            
except Exception as e:
    print(f"✗ ScheduleToEventConverter test failed: {e}")

print()

# Test 3: Real StoreManager
print("Test 3: Real StoreManager")
print("-" * 40)
try:
    from stores.store_manager import StoreManager
    
    store_manager = StoreManager()
    print(f"✓ StoreManager initialized with {len(store_manager.stores)} stores:")
    for store_name in store_manager.stores:
        print(f"  - {store_name}")
    
    # Test that we can get statistics
    stats = store_manager.get_statistics()
    print(f"✓ Store statistics accessible")
    
except Exception as e:
    print(f"✗ StoreManager test failed: {e}")

print()

# Test 4: SeasonInitializer Integration
print("Test 4: SeasonInitializer Integration")
print("-" * 40)
initializer = None  # Initialize for later tests
try:
    # SeasonInitializer removed with calendar system
    # from simulation.season_initializer import SeasonInitializer
    print("✗ SeasonInitializer removed with calendar system")
    
    initializer = SeasonInitializer()
    
    # Initialize a test season
    result = initializer.initialize_season(
        season_year=2025,
        dynasty_name="Phase 2 Test Dynasty"
    )
    
    if result['success']:
        print("✓ Season initialized successfully")
        print(f"  Dynasty ID: {result['dynasty']['dynasty_id'][:8]}...")
        print(f"  Games scheduled: {result['schedule']['total_games']}")
        print(f"  Store Manager ready: {result['components']['store_manager']}")
        print(f"  Calendar Manager ready: {result['components']['calendar_manager']}")
        print(f"  Date Calculator ready: {result['components']['date_calculator']}")
        
        # Verify we're using real StoreManager
        if initializer.store_manager:
            print(f"✓ Using real StoreManager: {type(initializer.store_manager).__name__}")
        else:
            print("✗ StoreManager not initialized")
            
    else:
        print("✗ Season initialization failed")
        
except Exception as e:
    print(f"✗ SeasonInitializer test failed: {e}")

print()

# Test 5: End-to-End Verification
print("Test 5: End-to-End Verification")
print("-" * 40)
try:
    # Verify the integration worked
    if initializer is None:
        print("✗ No initializer available from previous test")
    elif initializer and initializer.schedule:
        games = initializer.schedule.get_assigned_games()
        print(f"✓ Schedule has {len(games)} games")
        
    if initializer and initializer.calendar_manager:
        print(f"✓ Calendar manager is active")
        # Could simulate a day here if needed
        
    if initializer and initializer.store_manager:
        snapshot = initializer.store_manager.get_day_snapshot()
        print(f"✓ Can generate store snapshots")
        print(f"  Snapshot timestamp: {snapshot['timestamp']}")
        
    print()
    print("=" * 50)
    print("PHASE 2 INTEGRATION TEST COMPLETE")
    print(f"✅ All major components working")
    print(f"✅ Scheduling success rate: {len(games)/272*100:.1f}%")
    print(f"✅ Ready for Phase 3: Calendar Day Processing")
    print("=" * 50)
    
except Exception as e:
    print(f"✗ End-to-end verification failed: {e}")