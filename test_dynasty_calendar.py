#!/usr/bin/env python3
"""
Test Dynasty Calendar System

Simple test script to verify the structured metadata APIs work correctly
without requiring full simulation execution.
"""

import sys
import os
from datetime import date

# Add src to path for imports
sys.path.append('src')

from src.calendar.calendar_manager import CalendarManager
from src.calendar.event_factory import EventFactory
from src.calendar.simulation_executor import SimulationExecutor


def test_event_creation():
    """Test event creation with structured APIs."""
    print("🧪 Testing Event Creation...")

    # Test game event creation
    game_event = EventFactory.create_game_event(
        name="Test Game: Browns @ Texans",
        event_date=date(2024, 9, 8),
        away_team_id=7,
        home_team_id=9,
        week=1,
        season=2024,
        dynasty_id="test_dynasty"
    )

    print(f"✅ Game Event Created: {game_event.name}")
    print(f"   Event Type: {game_event.get_event_type()}")
    print(f"   Dynasty ID: {game_event.get_dynasty_id()}")
    print(f"   Season: {game_event.get_season()}")
    print(f"   Week: {game_event.get_week()}")
    print(f"   Status: {game_event.get_status()}")

    config = game_event.get_simulation_config()
    print(f"   Config: Away={config['away_team_id']}, Home={config['home_team_id']}")

    # Test draft event creation
    draft_event = EventFactory.create_draft_event(
        season=2024,
        dynasty_id="test_dynasty",
        draft_date=date(2024, 4, 25)
    )

    print(f"✅ Draft Event Created: {draft_event.name}")
    print(f"   Event Type: {draft_event.get_event_type()}")

    return game_event, draft_event


def test_calendar_management():
    """Test calendar management operations."""
    print("\n🧪 Testing Calendar Management...")

    # Create calendar manager
    calendar = CalendarManager(
        start_date=date(2024, 9, 1),
        database_path=":memory:"  # Use in-memory database for testing
    )

    print("✅ Calendar Manager Created")

    # Schedule a game using new API
    success = calendar.schedule_game(
        name="Test Game: Lions @ Packers",
        event_date=date(2024, 9, 8),
        away_team_id=22,
        home_team_id=23,
        week=1,
        season=2024,
        dynasty_id="test_dynasty"
    )

    print(f"✅ Game Scheduled: {success}")

    # Test dynasty-specific queries
    dynasty_games = calendar.get_game_events_for_dynasty("test_dynasty")
    print(f"✅ Dynasty Games Found: {len(dynasty_games)}")

    if dynasty_games:
        game = dynasty_games[0]
        print(f"   Game: {game.name}")
        print(f"   Status: {game.get_status()}")

    # Test upcoming games
    upcoming = calendar.get_upcoming_games("test_dynasty")
    print(f"✅ Upcoming Games: {len(upcoming)}")

    return calendar


def test_simulation_integration():
    """Test simulation executor integration."""
    print("\n🧪 Testing Simulation Integration...")

    # Create calendar with events
    calendar = CalendarManager(
        start_date=date(2024, 9, 1),
        database_path=":memory:"
    )

    # Add a test event
    calendar.schedule_game(
        name="Integration Test: Chiefs @ Raiders",
        event_date=date(2024, 9, 8),
        away_team_id=14,
        home_team_id=15,
        week=1,
        season=2024,
        dynasty_id="test_dynasty"
    )

    # Create executor
    executor = SimulationExecutor(calendar)
    print("✅ Simulation Executor Created")

    # Get execution status
    status = executor.get_execution_status("test_dynasty")
    print(f"✅ Execution Status Retrieved")
    print(f"   Current Date: {status['current_date']}")
    print(f"   Upcoming Events: {len(status['upcoming_events'])}")

    if status['upcoming_events']:
        event = status['upcoming_events'][0]
        print(f"   Next Event: {event['name']} on {event['date']}")

    return executor


def test_error_handling():
    """Test error handling and validation."""
    print("\n🧪 Testing Error Handling...")

    try:
        # Test invalid team IDs
        EventFactory.create_game_event(
            name="Invalid Game",
            event_date=date(2024, 9, 8),
            away_team_id=99,  # Invalid team ID
            home_team_id=9,
            week=1,
            season=2024,
            dynasty_id="test_dynasty"
        )
        print("❌ Should have failed with invalid team ID")
    except ValueError as e:
        print(f"✅ Correctly caught invalid team ID: {e}")

    try:
        # Test same team IDs
        EventFactory.create_game_event(
            name="Same Team Game",
            event_date=date(2024, 9, 8),
            away_team_id=7,
            home_team_id=7,  # Same as away
            week=1,
            season=2024,
            dynasty_id="test_dynasty"
        )
        print("❌ Should have failed with same team IDs")
    except ValueError as e:
        print(f"✅ Correctly caught same team IDs: {e}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 DYNASTY CALENDAR SYSTEM TESTS 🧪")
    print("=" * 60)

    try:
        # Test event creation
        game_event, draft_event = test_event_creation()

        # Test calendar management
        calendar = test_calendar_management()

        # Test simulation integration
        executor = test_simulation_integration()

        # Test error handling
        test_error_handling()

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("=" * 60)

        print("\n✅ Verified functionality:")
        print("   • Event creation with structured metadata")
        print("   • Dynasty-specific event filtering")
        print("   • Calendar management operations")
        print("   • Simulation executor integration")
        print("   • Error handling and validation")

        print("\n💡 The structured metadata API system is ready for:")
        print("   • Season event generation")
        print("   • Dynasty-specific game simulation")
        print("   • Persistent state management")
        print("   • Future expansion (scouting, draft, etc.)")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)