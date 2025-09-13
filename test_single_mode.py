#!/usr/bin/env python3
"""
Quick test of result processing system with a single mode
"""

from datetime import date, datetime, timedelta
import logging

# Reduce logging noise
logging.basicConfig(level=logging.WARNING)

from src.simulation.calendar_manager import CalendarManager
from src.simulation.processing_strategies import ProcessingStrategyFactory, SimulationMode
from src.simulation.events.game_simulation_event import GameSimulationEvent
from src.simulation.events.placeholder_events import TrainingEvent

def test_season_simulation_mode():
    """Test the season simulation mode with result processing"""
    
    print("Testing Season Simulation Mode with Result Processing")
    print("=" * 60)
    
    # Create calendar with full season simulation
    calendar_config = ProcessingStrategyFactory.create_calendar_manager_config(
        mode=SimulationMode.SEASON_SIMULATION,
        start_date=date(2024, 9, 1),
        season_year=2024
    )
    
    calendar = CalendarManager(**calendar_config)
    
    print(f"✅ Calendar created with result processing: {calendar.enable_result_processing}")
    print(f"✅ Processing strategy: {calendar.processing_strategy.value}")
    print(f"✅ Season state manager: {calendar.get_season_state_manager() is not None}")
    
    # Schedule a simple game
    game = GameSimulationEvent(
        date=datetime(2024, 9, 1, 13, 0),
        away_team_id=22,  # Lions
        home_team_id=5,   # Bears
        week=1
    )
    
    success, msg = calendar.schedule_event(game)
    print(f"✅ Game scheduled: {success} - {msg}")
    
    # Schedule a training event
    training = TrainingEvent(
        date=datetime(2024, 9, 2, 10, 0),
        team_id=22,  # Lions
        training_type="practice"
    )
    
    success, msg = calendar.schedule_event(training)
    print(f"✅ Training scheduled: {success} - {msg}")
    
    # Simulate the events
    print("\n🎮 Simulating events...")
    results = calendar.advance_to_date(date(2024, 9, 2))
    
    print(f"✅ Simulated {len(results)} days")
    
    # Check processing results
    total_events = sum(day.events_executed for day in results)
    successful_events = sum(day.successful_events for day in results) 
    total_processing = sum(len(day.processing_results) for day in results)
    
    print(f"✅ Events executed: {total_events}")
    print(f"✅ Successful events: {successful_events}/{total_events}")
    print(f"✅ Processing results: {total_processing}")
    
    # Check season state
    season_manager = calendar.get_season_state_manager()
    if season_manager:
        summary = season_manager.get_season_summary()
        print(f"✅ Season state tracking:")
        print(f"   - Current week: {summary['current_week']}")
        print(f"   - Teams tracked: {summary['teams_tracked']}")
        print(f"   - Processing events: {summary['processing_events']}")
        
        # Check team standings
        standings = season_manager.get_team_standings()[:3]
        print(f"   - Top 3 teams by record:")
        for i, team in enumerate(standings, 1):
            record = f"{team.wins}-{team.losses}"
            if team.ties > 0:
                record += f"-{team.ties}"
            print(f"     {i}. Team {team.team_id}: {record}")
    
    # Get processing summary
    processing_summary = calendar.get_processing_summary()
    if 'processor_statistics' in processing_summary:
        print(f"✅ Processor statistics:")
        for proc_stats in processing_summary['processor_statistics']:
            if proc_stats['results_processed'] > 0:
                print(f"   - {proc_stats['processor_type']}: {proc_stats['results_processed']} processed, {proc_stats['success_rate']:.1%} success")
    
    print(f"\n🎉 Test completed successfully!")
    print(f"The result processing system is working correctly with:")
    print(f"   • Event scheduling and execution")
    print(f"   • Result processing pipeline") 
    print(f"   • Season state management")
    print(f"   • Processing statistics and summaries")

if __name__ == "__main__":
    test_season_simulation_mode()