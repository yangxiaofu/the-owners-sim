#!/usr/bin/env python3
"""
Event System Test

Demonstrates the polymorphic event system with GameEvent and EventDatabaseAPI.

This test:
1. Creates a GameEvent wrapping FullGameSimulator
2. Stores it in the generic events table
3. Retrieves it using get_events_by_game_id()
4. Reconstructs and executes the event
"""

from datetime import datetime
from events import GameEvent, EventDatabaseAPI
from constants.team_ids import TeamIDs

def main():
    print("=" * 80)
    print("EVENT SYSTEM TEST")
    print("=" * 80)

    # Initialize Event Database API
    print("\n1️⃣  Initializing Event Database API...")
    event_db = EventDatabaseAPI("data/database/test_events.db")
    print(f"✅ Database initialized: {event_db}")

    # Create a GameEvent
    print("\n2️⃣  Creating GameEvent (wraps FullGameSimulator)...")
    game_event = GameEvent(
        away_team_id=TeamIDs.DETROIT_LIONS,
        home_team_id=TeamIDs.GREEN_BAY_PACKERS,
        game_date=datetime(2024, 12, 15, 13, 0),
        week=15,
        season=2024,
        season_type="regular_season"
    )
    print(f"✅ GameEvent created: {game_event}")
    print(f"   Event ID: {game_event.event_id}")
    print(f"   Game ID: {game_event.get_game_id()}")
    print(f"   Event Type: {game_event.get_event_type()}")

    # Validate preconditions
    print("\n3️⃣  Validating event preconditions...")
    is_valid, error_msg = game_event.validate_preconditions()
    if is_valid:
        print("✅ Event validation passed")
    else:
        print(f"❌ Event validation failed: {error_msg}")
        return

    # Store event in database BEFORE simulation
    print("\n4️⃣  Storing event in database (pre-simulation)...")
    event_db.insert_event(game_event)
    print("✅ Event stored in events table")

    # Retrieve event from database
    print("\n5️⃣  Retrieving events from database...")
    game_id = game_event.get_game_id()
    stored_events = event_db.get_events_by_game_id(game_id)
    print(f"✅ Retrieved {len(stored_events)} event(s) for game_id: {game_id}")

    for i, event_data in enumerate(stored_events, 1):
        print(f"\n   Event {i}:")
        print(f"   - Event ID: {event_data['event_id']}")
        print(f"   - Event Type: {event_data['event_type']}")
        print(f"   - Timestamp: {event_data['timestamp']}")
        print(f"   - Data: {event_data['data']}")

    # Reconstruct event from database
    print("\n6️⃣  Reconstructing GameEvent from database data...")
    reconstructed_event = GameEvent.from_database(stored_events[0])
    print(f"✅ Event reconstructed: {reconstructed_event}")

    # Execute the event (run game simulation)
    print("\n7️⃣  Executing event (running FullGameSimulator)...")
    print("=" * 80)
    result = reconstructed_event.simulate()
    print("=" * 80)

    # Display results
    print("\n8️⃣  Event Execution Results:")
    print(f"   Success: {result.success}")
    print(f"   Event Type: {result.event_type}")
    print(f"   Timestamp: {result.timestamp}")

    if result.success:
        print(f"\n   📊 Game Results:")
        print(f"   Away Team {result.data['away_team_id']}: {result.data['away_score']}")
        print(f"   Home Team {result.data['home_team_id']}: {result.data['home_score']}")
        if result.data.get('winner_name'):
            print(f"   🏆 Winner: {result.data['winner_name']}")
        print(f"   Total Plays: {result.data['total_plays']}")
        print(f"   Total Drives: {result.data['total_drives']}")
        print(f"   Game Duration: {result.data['game_duration_minutes']} minutes")
        print(f"   Simulation Time: {result.data['simulation_time']:.2f} seconds")
    else:
        print(f"   ❌ Error: {result.error_message}")

    # Database statistics
    print("\n9️⃣  Database Statistics:")
    stats = event_db.get_statistics()
    print(f"   Total Events: {stats['total_events']}")
    print(f"   Unique Games: {stats['unique_games']}")
    print(f"   Events by Type: {stats['events_by_type']}")

    print("\n" + "=" * 80)
    print("✅ EVENT SYSTEM TEST COMPLETE")
    print("=" * 80)

    print("\n💡 Key Takeaways:")
    print("   1. GameEvent implements BaseEvent interface")
    print("   2. Events stored in generic 'events' table")
    print("   3. Retrieved via get_events_by_game_id() - polymorphic!")
    print("   4. Reconstructed using from_database() factory method")
    print("   5. Executed via simulate() - runs FullGameSimulator")
    print("   6. Ready to add MediaEvent, TradeEvent, etc. using same pattern")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
