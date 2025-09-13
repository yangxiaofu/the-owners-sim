#!/usr/bin/env python3
"""
Result Processing Demo

Comprehensive demonstration of the result processing system showing different
simulation modes, processing strategies, and season state management capabilities.
"""

from datetime import date, datetime, timedelta
from typing import Dict, Any
import logging

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.simulation.calendar_manager import CalendarManager
from src.simulation.processing_strategies import ProcessingStrategyFactory, SimulationMode
from src.simulation.events.game_simulation_event import GameSimulationEvent
from src.simulation.events.placeholder_events import (
    TrainingEvent, ScoutingEvent, RestDayEvent, AdministrativeEvent
)


def create_sample_schedule(calendar_manager: CalendarManager, start_date: date) -> None:
    """Create a sample week schedule with mixed event types"""
    
    # Monday: Team 22 (Lions) vs Team 5 (Bears) game
    game_event = GameSimulationEvent(
        date=datetime.combine(start_date, datetime.min.time()),
        away_team_id=22,  # Lions
        home_team_id=5,   # Bears
        week=1
    )
    calendar_manager.schedule_event(game_event)
    
    # Tuesday: Training for both teams
    training_1 = TrainingEvent(
        date=datetime.combine(start_date + timedelta(days=1), datetime.min.time()),
        team_id=22,  # Lions
        training_type="practice"
    )
    training_2 = TrainingEvent(
        date=datetime.combine(start_date + timedelta(days=1), datetime.min.time().replace(hour=10)),
        team_id=5,   # Bears
        training_type="practice"
    )
    calendar_manager.schedule_event(training_1)
    calendar_manager.schedule_event(training_2)
    
    # Wednesday: Scouting activities
    scouting = ScoutingEvent(
        date=datetime.combine(start_date + timedelta(days=2), datetime.min.time()),
        team_id=22,  # Lions
        scouting_target="college_prospects"
    )
    calendar_manager.schedule_event(scouting)
    
    # Thursday: Rest day for Team 22
    rest_day = RestDayEvent(
        date=datetime.combine(start_date + timedelta(days=3), datetime.min.time()),
        team_id=22,  # Lions
        rest_type="recovery_day"
    )
    calendar_manager.schedule_event(rest_day)
    
    # Friday: Administrative activities
    admin_event = AdministrativeEvent(
        date=datetime.combine(start_date + timedelta(days=4), datetime.min.time()),
        team_id=22,  # Lions
        admin_type="contract_negotiations"
    )
    calendar_manager.schedule_event(admin_event)
    
    # Weekend: Another game
    weekend_game = GameSimulationEvent(
        date=datetime.combine(start_date + timedelta(days=5), datetime.min.time()),
        away_team_id=5,  # Bears
        home_team_id=12, # Packers
        week=1
    )
    calendar_manager.schedule_event(weekend_game)


def demonstrate_simulation_mode(mode: SimulationMode, start_date: date) -> Dict[str, Any]:
    """Demonstrate a specific simulation mode and return results"""
    
    print(f"\n{'='*60}")
    print(f"DEMONSTRATING: {mode.value.upper().replace('_', ' ')}")
    print(f"{'='*60}")
    
    # Get strategy profile
    profile = ProcessingStrategyFactory.get_strategy_profile(mode)
    print(f"Strategy: {profile.name}")
    print(f"Description: {profile.description}")
    print(f"Processing Strategy: {profile.processing_strategy.value}")
    print(f"Season Tracking: {'Enabled' if profile.season_tracking_enabled else 'Disabled'}")
    
    # Create calendar manager with mode-specific configuration
    calendar_config = ProcessingStrategyFactory.create_calendar_manager_config(
        mode=mode, 
        start_date=start_date, 
        season_year=2024
    )
    
    calendar_manager = CalendarManager(**calendar_config)
    
    # Create sample schedule
    create_sample_schedule(calendar_manager, start_date)
    
    # Show initial state
    initial_stats = calendar_manager.get_calendar_stats()
    print(f"\nScheduled Events: {initial_stats.total_events}")
    print(f"Teams Involved: {len(initial_stats.teams_with_events)}")
    print(f"Date Range: {initial_stats.date_range}")
    
    # Simulate the week
    print(f"\nSimulating week from {start_date} to {start_date + timedelta(days=6)}...")
    simulation_results = calendar_manager.advance_to_date(start_date + timedelta(days=6))
    
    # Show results
    total_events = sum(day.events_executed for day in simulation_results)
    successful_events = sum(day.successful_events for day in simulation_results)
    total_processing = sum(len(day.processing_results) for day in simulation_results)
    
    print(f"\nSIMULATION RESULTS:")
    print(f"- Days Simulated: {len(simulation_results)}")
    print(f"- Total Events Executed: {total_events}")
    print(f"- Successful Events: {successful_events}/{total_events} ({100*successful_events/max(1,total_events):.1f}%)")
    print(f"- Processing Results Generated: {total_processing}")
    
    # Show processing-specific results
    if calendar_manager.enable_result_processing:
        processing_summary = calendar_manager.get_processing_summary()
        print(f"\nPROCESSING SUMMARY:")
        print(f"- Processing Strategy: {processing_summary['processing_strategy']}")
        print(f"- Season Year: {processing_summary['season_year']}")
        
        if 'season_state' in processing_summary:
            season_state = processing_summary['season_state']
            print(f"- Season Week: {season_state['current_week']}")
            print(f"- Season Phase: {season_state['season_phase']}")
            print(f"- Teams Tracked: {season_state['teams_tracked']}")
            print(f"- Players Tracked: {season_state['players_tracked']}")
            print(f"- Processing Events: {season_state['processing_events']}")
        
        if 'processor_statistics' in processing_summary:
            print(f"\nPROCESSOR STATISTICS:")
            for proc_stats in processing_summary['processor_statistics']:
                print(f"- {proc_stats['processor_type']}: {proc_stats['results_processed']} results, {proc_stats['success_rate']:.1%} success")
        
        # Show season state details if available
        season_manager = calendar_manager.get_season_state_manager()
        if season_manager:
            standings = season_manager.get_team_standings()[:5]  # Top 5 teams
            print(f"\nTOP 5 TEAM STANDINGS:")
            for i, team in enumerate(standings, 1):
                record = f"{team.wins}-{team.losses}"
                if team.ties > 0:
                    record += f"-{team.ties}"
                print(f"  {i}. Team {team.team_id}: {record} ({team.get_win_percentage():.3f})")
    else:
        print(f"\nResult processing disabled for this mode - focusing on raw event execution")
    
    # Show daily breakdown
    print(f"\nDAILY BREAKDOWN:")
    for day_result in simulation_results:
        processing_info = ""
        if day_result.processing_results:
            successful_processing = sum(1 for p in day_result.processing_results if p.processed_successfully)
            processing_info = f", {successful_processing}/{len(day_result.processing_results)} processed"
        
        print(f"  {day_result.date}: {day_result.successful_events}/{day_result.events_executed} events{processing_info}")
    
    # Return summary data
    final_stats = calendar_manager.get_calendar_stats()
    return {
        "mode": mode.value,
        "profile_name": profile.name,
        "total_events": total_events,
        "successful_events": successful_events, 
        "processing_results": total_processing,
        "processing_enabled": calendar_manager.enable_result_processing,
        "final_stats": {
            "total_processed_results": final_stats.total_processed_results,
            "processing_success_rate": final_stats.processing_success_rate
        }
    }


def run_comparison_demo():
    """Run a comparison of different simulation modes"""
    
    print(f"{'='*80}")
    print(f"RESULT PROCESSING SYSTEM DEMONSTRATION")
    print(f"{'='*80}")
    print(f"")
    print(f"This demo showcases the flexible result processing system with different")
    print(f"simulation modes optimized for various use cases.")
    print(f"")
    
    # Show available modes
    available_modes = ProcessingStrategyFactory.get_available_modes()
    print(f"AVAILABLE SIMULATION MODES:")
    for mode, description in available_modes.items():
        print(f"  • {mode.value}: {description}")
    
    # Demo each mode
    start_date = date(2024, 9, 1)  # September 1, 2024
    results = []
    
    # Demo key modes that show different capabilities
    demo_modes = [
        SimulationMode.LIGHTWEIGHT,      # Minimal processing
        SimulationMode.QUICK_STATS,      # Stats only
        SimulationMode.SEASON_SIMULATION, # Full features
        SimulationMode.DEVELOPMENT_FOCUS, # Development emphasis
        SimulationMode.ANALYTICS_MODE     # Analytics emphasis
    ]
    
    for mode in demo_modes:
        mode_result = demonstrate_simulation_mode(mode, start_date)
        results.append(mode_result)
        
        # Add separator between modes
        if mode != demo_modes[-1]:
            print(f"\n{'-'*60}")
            print("Continuing to next mode...")
            print()
    
    # Summary comparison
    print(f"\n{'='*60}")
    print(f"COMPARISON SUMMARY")
    print(f"{'='*60}")
    
    print(f"{'Mode':<20} {'Events':<8} {'Success':<8} {'Processing':<12} {'Proc Success':<12}")
    print(f"{'-'*20} {'-'*8} {'-'*8} {'-'*12} {'-'*12}")
    
    for result in results:
        mode_name = result['mode'][:18]  # Truncate for display
        events = f"{result['successful_events']}/{result['total_events']}"
        success_rate = f"{100*result['successful_events']/max(1,result['total_events']):.0f}%"
        processing_count = str(result['processing_results'])
        
        if result['processing_enabled'] and result['final_stats']['total_processed_results'] > 0:
            proc_success = f"{100*result['final_stats']['processing_success_rate']:.0f}%"
        else:
            proc_success = "N/A"
        
        print(f"{mode_name:<20} {events:<8} {success_rate:<8} {processing_count:<12} {proc_success:<12}")
    
    print(f"\nKEY OBSERVATIONS:")
    print(f"• Lightweight mode: Minimal overhead, no season progression tracking")
    print(f"• Quick Stats mode: Collects statistics without complex state changes")  
    print(f"• Season Simulation mode: Full features with comprehensive tracking")
    print(f"• Development Focus: Emphasizes player/team development over standings")
    print(f"• Analytics Mode: Enhanced data collection with reduced narrative events")
    
    print(f"\nThe system successfully demonstrates flexible processing strategies")
    print(f"that can be tailored to different simulation needs and performance requirements.")


def demonstrate_custom_configuration():
    """Demonstrate creating custom processing configurations"""
    
    print(f"\n{'='*60}")
    print(f"CUSTOM CONFIGURATION DEMONSTRATION")
    print(f"{'='*60}")
    
    # Create a custom profile focused on injury tracking
    injury_focused_profile = ProcessingStrategyFactory.create_custom_profile(
        name="Injury Focus Mode",
        description="Custom mode emphasizing injury tracking and recovery",
        enable_player_development=True,
        enable_injury_tracking=True,
        enable_chemistry_changes=False,  # Disable chemistry for focus
        enable_narrative_events=False,   # Reduce narrative noise
        max_side_effects_per_result=5,
        enable_verbose_logging=True
    )
    
    print(f"Created Custom Profile:")
    print(f"  Name: {injury_focused_profile.name}")
    print(f"  Description: {injury_focused_profile.description}")
    print(f"  Player Development: {injury_focused_profile.enable_player_development}")
    print(f"  Injury Tracking: {injury_focused_profile.enable_injury_tracking}")
    print(f"  Chemistry Changes: {injury_focused_profile.enable_chemistry_changes}")
    print(f"  Narrative Events: {injury_focused_profile.enable_narrative_events}")
    print(f"  Max Side Effects: {injury_focused_profile.max_side_effects_per_result}")
    
    # Show how this would be used
    processor_config = injury_focused_profile.to_processor_config()
    print(f"\nGenerated ProcessorConfig:")
    print(f"  Strategy: {processor_config.strategy.value}")
    print(f"  Process Injuries: {processor_config.process_injuries}")
    print(f"  Update Chemistry: {processor_config.update_chemistry}")
    print(f"  Enable Side Effects: {processor_config.enable_side_effects}")
    print(f"  Verbose Logging: {processor_config.verbose_logging}")
    
    print(f"\nThis demonstrates how users can create tailored configurations")
    print(f"for specific simulation requirements or research needs.")


def main():
    """Main demo function"""
    
    print("Starting Result Processing System Demo...")
    print("This will demonstrate different simulation modes and their capabilities.")
    print()
    
    try:
        # Run the main comparison demo
        run_comparison_demo()
        
        # Show custom configuration capabilities  
        demonstrate_custom_configuration()
        
        print(f"\n{'='*80}")
        print(f"DEMO COMPLETED SUCCESSFULLY")
        print(f"{'='*80}")
        print(f"")
        print(f"The result processing system provides:")
        print(f"• Flexible processing strategies for different use cases")
        print(f"• Comprehensive season state management")
        print(f"• Event-specific result processors with rich metadata")
        print(f"• Configurable performance and feature trade-offs")
        print(f"• Easy-to-use factory patterns for common scenarios")
        print(f"")
        print(f"This enables users to tailor the simulation engine to their specific")
        print(f"needs while maintaining consistent interfaces and robust processing.")
        
    except Exception as e:
        print(f"Demo encountered an error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()