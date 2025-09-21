#!/usr/bin/env python3
"""
Dynasty Calendar Management Demo

Demonstrates the complete event-driven dynasty management workflow using
the enhanced calendar system with structured metadata APIs.

This demo shows:
1. Creating a dynasty calendar with seasonal events
2. Executing game simulations from events
3. Tracking dynasty progress and standings
4. Persistent state across game sessions
"""

import sys
import os
from datetime import date, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.append('src')

from src.calendar.calendar_manager import CalendarManager
from src.calendar.event_factory import EventFactory
from src.calendar.simulation_executor import SimulationExecutor


def create_demo_season(calendar_manager: CalendarManager, dynasty_id: str, season: int = 2024):
    """
    Create a demo season with game events for dynasty management.

    Args:
        calendar_manager: CalendarManager instance
        dynasty_id: Dynasty identifier
        season: Season year

    Returns:
        int: Number of events created
    """
    print(f"\n🏈 Creating {season} Season Events for Dynasty: {dynasty_id}")

    # Sample NFL week 1 matchups (simplified for demo)
    week_1_games = [
        {"away_team": 7, "home_team": 9, "name": "Week 1: Browns @ Texans"},  # Cleveland @ Houston
        {"away_team": 22, "home_team": 23, "name": "Week 1: Lions @ Packers"},  # Detroit @ Green Bay
        {"away_team": 19, "home_team": 18, "name": "Week 1: Eagles @ Giants"},  # Philadelphia @ New York Giants
        {"away_team": 14, "home_team": 15, "name": "Week 1: Chiefs @ Raiders"},  # Kansas City @ Las Vegas
    ]

    week_2_games = [
        {"away_team": 9, "home_team": 7, "name": "Week 2: Texans @ Browns"},  # Houston @ Cleveland
        {"away_team": 23, "home_team": 22, "name": "Week 2: Packers @ Lions"},  # Green Bay @ Detroit
        {"away_team": 18, "home_team": 19, "name": "Week 2: Giants @ Eagles"},  # New York Giants @ Philadelphia
        {"away_team": 15, "home_team": 14, "name": "Week 2: Raiders @ Chiefs"},  # Las Vegas @ Kansas City
    ]

    events_created = 0

    # Create Week 1 games (September 8, 2024)
    week_1_date = date(2024, 9, 8)
    for game in week_1_games:
        success = calendar_manager.schedule_game(
            name=game["name"],
            event_date=week_1_date,
            away_team_id=game["away_team"],
            home_team_id=game["home_team"],
            week=1,
            season=season,
            dynasty_id=dynasty_id,
            overtime_type="regular_season"
        )

        if success:
            events_created += 1
            print(f"  ✅ Scheduled: {game['name']}")
        else:
            print(f"  ❌ Failed to schedule: {game['name']}")

    # Create Week 2 games (September 15, 2024)
    week_2_date = date(2024, 9, 15)
    for game in week_2_games:
        success = calendar_manager.schedule_game(
            name=game["name"],
            event_date=week_2_date,
            away_team_id=game["away_team"],
            home_team_id=game["home_team"],
            week=2,
            season=season,
            dynasty_id=dynasty_id,
            overtime_type="regular_season"
        )

        if success:
            events_created += 1
            print(f"  ✅ Scheduled: {game['name']}")
        else:
            print(f"  ❌ Failed to schedule: {game['name']}")

    # Add other event types for future expansion

    # Draft event (April 25, 2024)
    draft_event = EventFactory.create_draft_event(
        season=season,
        dynasty_id=dynasty_id,
        draft_date=date(2024, 4, 25)
    )

    if calendar_manager.schedule_event(draft_event):
        events_created += 1
        print(f"  ✅ Scheduled: {season} NFL Draft")

    # Scouting event (October 1, 2024)
    scouting_event = EventFactory.create_scouting_event(
        name="College QB Scouting - Week 5",
        event_date=date(2024, 10, 1),
        scout_team_id=7,  # Cleveland Browns
        scouting_type="college_quarterback",
        dynasty_id=dynasty_id,
        targets=["Caleb Williams", "Drake Maye", "Jayden Daniels"],
        budget=75000
    )

    if calendar_manager.schedule_event(scouting_event):
        events_created += 1
        print(f"  ✅ Scheduled: College QB Scouting")

    print(f"\n📊 Season Creation Summary:")
    print(f"   Events Created: {events_created}")
    print(f"   Dynasty ID: {dynasty_id}")
    print(f"   Season: {season}")

    return events_created


def demonstrate_dynasty_simulation(calendar_manager: CalendarManager, dynasty_id: str):
    """
    Demonstrate dynasty simulation workflow.

    Args:
        calendar_manager: CalendarManager instance
        dynasty_id: Dynasty identifier
    """
    print(f"\n🎮 Dynasty Simulation Demo: {dynasty_id}")

    # Create simulation executor
    executor = SimulationExecutor(calendar_manager)

    # Show initial dynasty status
    status = executor.get_execution_status(dynasty_id)
    print(f"\n📈 Initial Dynasty Status:")
    print(f"   Current Date: {status['current_date']}")
    print(f"   Upcoming Events: {len(status['upcoming_events'])}")

    if status['upcoming_events']:
        print(f"   Next Event: {status['upcoming_events'][0]['name']} on {status['upcoming_events'][0]['date']}")

    # Show dynasty summary
    summary = status['dynasty_summary']
    if 'error' not in summary:
        print(f"   Total Games: {summary['total_games']}")
        print(f"   Completed Games: {summary['completed_games']}")
        print(f"   Record: {summary['record']['wins']}-{summary['record']['losses']}-{summary['record']['ties']}")

    # Set calendar to game day
    game_date = date(2024, 9, 8)  # Week 1
    calendar_manager.set_date(game_date)
    print(f"\n📅 Set calendar to game day: {game_date}")

    # Execute today's simulations
    print(f"\n⚡ Executing simulations for {game_date}...")
    day_results = executor.execute_daily_simulations(game_date, dynasty_id)

    print(f"\n🏁 Daily Simulation Results:")
    print(f"   Date: {day_results['date']}")
    print(f"   Events Found: {day_results['events_found']}")
    print(f"   Events Executed: {day_results['events_executed']}")

    # Show individual game results
    for result in day_results['results']:
        print(f"\n   🏈 {result['event_name']}:")
        print(f"      Status: {result['status']}")

        if result['status'] == 'success' and 'result' in result:
            sim_result = result['result']
            if 'simulation_data' in sim_result:
                sim_data = sim_result['simulation_data']
                if 'final_score' in sim_data:
                    print(f"      Final Score: {sim_data['final_score']}")
                if 'winner_id' in sim_data and sim_data['winner_id']:
                    print(f"      Winner: Team {sim_data['winner_id']}")
                if 'total_plays' in sim_data:
                    print(f"      Total Plays: {sim_data['total_plays']}")

    return day_results


def demonstrate_dynasty_persistence(calendar_manager: CalendarManager, dynasty_id: str):
    """
    Demonstrate how dynasty state persists across sessions.

    Args:
        calendar_manager: CalendarManager instance
        dynasty_id: Dynasty identifier
    """
    print(f"\n💾 Dynasty Persistence Demo")

    # Show current calendar state
    summary = calendar_manager.get_calendar_summary()
    print(f"\n📊 Calendar State:")
    print(f"   Current Date: {summary['current_date']}")
    print(f"   Total Events: {summary['total_events']}")
    print(f"   Dates with Events: {summary['dates_with_events']}")

    # Get dynasty games
    completed_games = calendar_manager.get_game_events_for_dynasty(
        dynasty_id=dynasty_id,
        status="completed"
    )

    upcoming_games = calendar_manager.get_upcoming_games(dynasty_id, limit=3)

    print(f"\n🏆 Dynasty Game Summary:")
    print(f"   Completed Games: {len(completed_games)}")
    print(f"   Upcoming Games: {len(upcoming_games)}")

    if completed_games:
        print(f"\n   Recent Completed Games:")
        for game in completed_games[:3]:  # Show last 3
            result = game.get_simulation_result()
            if result and 'final_score' in result:
                print(f"      {game.name}: {result['final_score']}")

    if upcoming_games:
        print(f"\n   Next Upcoming Games:")
        for game in upcoming_games:
            print(f"      {game.name} on {game.event_date}")

    # Demonstrate save/load by creating a new calendar manager
    print(f"\n🔄 Testing Persistence - Creating New Calendar Manager...")

    # Create new calendar manager with same database
    new_calendar = CalendarManager(
        start_date=date(2024, 9, 1),
        database_path="data/database/nfl_simulation.db"
    )

    # Verify events are still there
    new_completed_games = new_calendar.get_game_events_for_dynasty(
        dynasty_id=dynasty_id,
        status="completed"
    )

    new_upcoming_games = new_calendar.get_upcoming_games(dynasty_id, limit=3)

    print(f"   ✅ Events Persisted:")
    print(f"      Completed Games: {len(new_completed_games)}")
    print(f"      Upcoming Games: {len(new_upcoming_games)}")

    if len(new_completed_games) == len(completed_games):
        print(f"   ✅ All completed games successfully persisted!")
    else:
        print(f"   ⚠️  Persistence issue: {len(completed_games)} vs {len(new_completed_games)}")


def main():
    """
    Main demo function showing complete dynasty calendar workflow.
    """
    print("=" * 80)
    print("🏈 DYNASTY CALENDAR MANAGEMENT DEMO 🏈")
    print("=" * 80)

    print("\nThis demo showcases the event-driven dynasty management system:")
    print("• Structured event creation with metadata APIs")
    print("• Integration with FullGameSimulator")
    print("• Persistent dynasty state across sessions")
    print("• Dynasty-specific filtering and tracking")

    # Initialize dynasty
    dynasty_id = "eagles_dynasty_demo"
    start_date = date(2024, 9, 1)

    print(f"\n🏛️  Initializing Dynasty: {dynasty_id}")
    print(f"📅 Start Date: {start_date}")

    # Create calendar manager
    calendar_manager = CalendarManager(
        start_date=start_date,
        database_path="data/database/nfl_simulation.db"
    )

    print(f"✅ Calendar Manager initialized")

    # Check if dynasty already has events
    existing_games = calendar_manager.get_game_events_for_dynasty(dynasty_id)

    if existing_games:
        print(f"\n📋 Found existing dynasty with {len(existing_games)} games")
        print("🔄 Automatically continuing with existing dynasty for demo purposes")

    # Create season events if none exist
    if not existing_games:
        events_created = create_demo_season(calendar_manager, dynasty_id, 2024)
    else:
        print(f"\n📅 Using existing {len(existing_games)} game events")
        events_created = len(existing_games)

    if events_created == 0:
        print("❌ No events to demonstrate with. Exiting.")
        return

    # Demonstrate simulation workflow
    simulation_results = demonstrate_dynasty_simulation(calendar_manager, dynasty_id)

    # Demonstrate persistence
    demonstrate_dynasty_persistence(calendar_manager, dynasty_id)

    # Show final summary
    print(f"\n" + "=" * 80)
    print("🎉 DEMO COMPLETED SUCCESSFULLY! 🎉")
    print("=" * 80)

    print(f"\nWhat was demonstrated:")
    print(f"✅ Event-driven dynasty management")
    print(f"✅ Structured metadata with type-safe APIs")
    print(f"✅ Game simulation integration")
    print(f"✅ Database persistence across sessions")
    print(f"✅ Dynasty-specific filtering and queries")

    executor = SimulationExecutor(calendar_manager)
    final_status = executor.get_execution_status(dynasty_id)

    print(f"\n📊 Final Dynasty Status:")
    summary = final_status['dynasty_summary']
    if 'error' not in summary:
        print(f"   Dynasty: {dynasty_id}")
        print(f"   Total Games: {summary['total_games']}")
        print(f"   Completed: {summary['completed_games']}")
        print(f"   Upcoming: {summary['upcoming_games']}")
        record = summary['record']
        print(f"   Record: {record['wins']}-{record['losses']}-{record['ties']}")

    print(f"\n💡 Next Steps:")
    print(f"   • Advance calendar and simulate more games")
    print(f"   • Add scouting and draft simulations")
    print(f"   • Implement dynasty team management")
    print(f"   • Create season-long simulation loops")

    print(f"\n👋 Demo complete! All dynasty data saved to database.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()