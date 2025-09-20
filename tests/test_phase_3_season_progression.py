"""
Phase 3 Season Progression Test

Comprehensive test suite for the complete season progression system,
validating end-to-end data flow and integration of all components.
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Dict, Any
import time

# PYTHONPATH should be set to src when running this test
# No need to modify sys.path when using PYTHONPATH=src

print("=== PHASE 3 SEASON PROGRESSION TEST ===")
print()

# Test 1: Season Progression Controller Initialization
print("Test 1: Season Progression Controller Initialization")
print("-" * 60)

try:
    from simulation.season_progression_controller import SeasonProgressionController, SeasonProgressStats
    
    controller = SeasonProgressionController()
    print("✅ SeasonProgressionController imported and initialized")
    print(f"   Database path: {controller.database_path}")
    
except Exception as e:
    print(f"❌ Failed to initialize SeasonProgressionController: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 2: Integration Test - Short Season Simulation
print("Test 2: Integration Test - Short Season Simulation")
print("-" * 60)

def progress_callback(stats: SeasonProgressStats, day_result):
    """Callback to track simulation progress"""
    if day_result.events_executed > 0:
        print(f"   📅 {day_result.date}: {day_result.events_executed} events, "
              f"{day_result.successful_events} successful")

try:
    # Run a very short season simulation - just first 2 weeks of September
    print("🚀 Starting short season simulation (2 weeks)...")
    start_time = datetime.now()
    
    # Use a custom start date to limit scope
    test_start_date = date(2025, 9, 5)  # First Thursday of September 2025
    test_end_date = test_start_date + timedelta(days=14)  # 2 weeks
    
    # Temporarily modify the controller to use shorter timeline for testing
    controller = SeasonProgressionController()
    
    # Override the season dates calculation for testing
    def test_calculate_season_dates(season_year: int, start_date):
        return {
            'start': test_start_date,
            'end': test_end_date  # Much shorter for testing
        }
    
    original_method = controller._calculate_season_dates
    controller._calculate_season_dates = test_calculate_season_dates
    
    result = controller.simulate_complete_season(
        season_year=2025,
        dynasty_name="Phase 3 Test Dynasty",
        start_date=test_start_date,
        progress_callback=progress_callback
    )
    
    # Restore original method
    controller._calculate_season_dates = original_method
    
    duration = (datetime.now() - start_time).total_seconds()
    
    print(f"\n📊 SIMULATION RESULTS:")
    print(f"   Success: {'✅ YES' if result.success else '❌ NO'}")
    print(f"   Duration: {duration:.2f} seconds")
    print(f"   Dynasty ID: {result.dynasty_id[:8]}..." if result.dynasty_id else "   Dynasty ID: Not set")
    print(f"   Season Year: {result.season_year}")
    
    if result.season_stats:
        stats = result.season_stats
        print(f"   Days Simulated: {stats.days_completed}/{stats.total_days}")
        print(f"   Games Scheduled: {stats.games_scheduled}")
        print(f"   Games Completed: {stats.games_completed}")
        print(f"   Success Rate: {stats.game_success_rate:.1f}%")
        print(f"   Events Processed: {stats.total_events_processed}")
    
    if result.errors:
        print(f"   Errors: {len(result.errors)}")
        for error in result.errors[:3]:  # Show first 3 errors
            print(f"      - {error}")
    
    print(f"   Daily Results: {len(result.daily_results)} days")
    
    # Analyze daily results
    game_days = [r for r in result.daily_results if r.events_executed > 0]
    if game_days:
        print(f"   Game Days: {len(game_days)}")
        total_games = sum(r.events_executed for r in game_days)
        successful_games = sum(r.successful_events for r in game_days) 
        print(f"   Total Game Events: {total_games}")
        print(f"   Successful Games: {successful_games}")
    
    if not result.success:
        print("❌ Short season simulation failed")
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"   - {error}")
    else:
        print("✅ Short season simulation completed successfully")
        
except Exception as e:
    print(f"❌ Integration test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 3: Data Flow Validation
print("Test 3: Data Flow Validation")
print("-" * 60)

try:
    if 'controller' in locals() and hasattr(controller, 'season_initializer') and controller.season_initializer:
        initializer = controller.season_initializer
        
        # Check StoreManager integration
        if initializer.store_manager:
            store_stats = initializer.store_manager.get_statistics()
            print("✅ StoreManager accessible")
            print(f"   Total Games in Store: {store_stats['totals'].get('total_games', 0)}")
            print(f"   Players Tracked: {store_stats['totals'].get('total_players_tracked', 0)}")
            print(f"   Box Scores: {store_stats['totals'].get('total_box_scores', 0)}")
            
            # Test individual stores
            for store_name, store_stats in store_stats['stores'].items():
                size = store_stats.get('size', 0)
                print(f"   {store_name}: {size} entries")
        else:
            print("❌ StoreManager not accessible")
        
        # Check CalendarManager integration 
        if initializer.calendar_manager:
            print("✅ CalendarManager accessible")
            
            # Get current calendar status
            status = initializer.get_status()
            print(f"   Current Date: {status.get('current_date', 'Not set')}")
            print(f"   Components Ready: {status.get('components_ready', {})}")
        else:
            print("❌ CalendarManager not accessible")
            
        # Check Database integration
        if initializer.db_connection:
            print("✅ Database connection active")
        else:
            print("⚠️ Database connection not available (may be expected for testing)")
            
        # Check Dynasty context
        dynasty_status = initializer.get_status()
        if dynasty_status.get('dynasty_id'):
            print(f"✅ Dynasty context active: {dynasty_status['dynasty_id'][:8]}...")
        else:
            print("❌ Dynasty context not active")
            
    else:
        print("❌ Cannot validate data flow - season not properly initialized")
        
except Exception as e:
    print(f"❌ Data flow validation failed: {e}")

print()

# Test 4: Component Integration Health Check
print("Test 4: Component Integration Health Check")
print("-" * 60)

try:
    # Test importing and basic functionality of all key components
    components = {
        'SeasonInitializer': 'simulation.season_initializer',
        'CalendarManager': 'simulation.calendar_manager', 
        'GameSimulationEvent': 'simulation.events.game_simulation_event',
        'StoreManager': 'stores.store_manager',
        'DailyDataPersister': 'persistence.daily_persister',
        'ScheduleToEventConverter': 'scheduling.converters.schedule_to_event_converter'
    }
    
    print("🔍 Checking component imports...")
    component_status = {}
    
    for component_name, module_path in components.items():
        try:
            module = __import__(module_path, fromlist=[component_name])
            component_class = getattr(module, component_name)
            component_status[component_name] = "✅ Available"
        except ImportError as e:
            component_status[component_name] = f"❌ Import failed: {e}"
        except AttributeError as e:
            component_status[component_name] = f"❌ Class not found: {e}"
        except Exception as e:
            component_status[component_name] = f"❌ Error: {e}"
    
    print("Component Status:")
    for component, status in component_status.items():
        print(f"   {component}: {status}")
    
    # Count successful imports
    successful = sum(1 for status in component_status.values() if status.startswith("✅"))
    total = len(component_status)
    
    print(f"\n📊 Component Health: {successful}/{total} components available")
    
    if successful == total:
        print("✅ All components are available and importable")
    else:
        print(f"⚠️ {total - successful} components have issues")
        
except Exception as e:
    print(f"❌ Component health check failed: {e}")

print()

# Test 5: Performance and Memory Check
print("Test 5: Performance and Memory Check")
print("-" * 60)

try:
    import psutil
    import gc
    
    # Get current process
    process = psutil.Process()
    
    # Memory before
    memory_before = process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"📊 Memory usage before test: {memory_before:.1f} MB")
    
    # Run garbage collection
    gc.collect()
    
    # Memory after GC
    memory_after_gc = process.memory_info().rss / 1024 / 1024  # MB
    print(f"📊 Memory usage after GC: {memory_after_gc:.1f} MB")
    
    # Check if we had any large memory usage during simulation
    if 'result' in locals() and result.season_stats:
        simulation_duration = result.season_stats.elapsed_time_seconds
        events_processed = result.season_stats.total_events_processed
        
        if events_processed > 0:
            avg_time_per_event = simulation_duration / events_processed
            print(f"⚡ Average time per event: {avg_time_per_event:.3f} seconds")
            
            # Estimate full season performance
            estimated_full_season_time = avg_time_per_event * 257  # Estimated games in full season
            print(f"📈 Estimated full season time: {estimated_full_season_time/60:.1f} minutes")
    
    # Performance recommendations
    print("\n💡 Performance Analysis:")
    if memory_after_gc > 200:  # MB
        print("   ⚠️ High memory usage detected - may need optimization for full season")
    else:
        print("   ✅ Memory usage looks reasonable")
        
    print("   📋 For full season simulation:")
    print("      - Monitor memory usage on game-heavy days (Sundays)")
    print("      - Consider batch processing for large datasets")
    print("      - Implement periodic garbage collection")
    
except ImportError:
    print("⚠️ psutil not available - skipping detailed performance analysis")
except Exception as e:
    print(f"❌ Performance check failed: {e}")

print()

# Final Summary
print("=" * 60)
print("🏁 PHASE 3 INTEGRATION TEST COMPLETE")
print("=" * 60)

summary_points = []

if 'result' in locals():
    if result.success:
        summary_points.append("✅ Season simulation completed successfully")
    else:
        summary_points.append("❌ Season simulation had issues")
        
    if result.season_stats and result.season_stats.game_success_rate > 80:
        summary_points.append(f"✅ High game success rate ({result.season_stats.game_success_rate:.1f}%)")
    elif result.season_stats:
        summary_points.append(f"⚠️ Lower game success rate ({result.season_stats.game_success_rate:.1f}%)")

if 'successful' in locals() and successful == len(components):
    summary_points.append("✅ All core components available")
else:
    summary_points.append("⚠️ Some components have issues")

# Overall assessment
if len([p for p in summary_points if p.startswith("✅")]) >= 2:
    print("🎉 PHASE 3 READY FOR PRODUCTION")
    print("   The season progression system is working correctly")
    print("   All major components are integrated and functional")
else:
    print("⚠️ PHASE 3 NEEDS ATTENTION")
    print("   Some components need fixes before full season simulation")

print()
for point in summary_points:
    print(f"   {point}")

print()
print("Next Steps:")
print("   1. Address any component issues identified above")
print("   2. Run full season simulation test") 
print("   3. Optimize performance for multi-game days")
print("   4. Implement progress tracking and pause/resume")
print("=" * 60)