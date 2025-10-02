#!/usr/bin/env python3
"""
Hybrid Event Storage Test

Demonstrates the three-part event storage architecture:
1. Parameters: Input values for replay/scheduling
2. Results: Output after simulation (cached)
3. Metadata: Additional context

Tests two patterns:
- GameEvent: Parameterized event (schedule first, simulate later)
- ScoutingEvent: Result-based event (execute immediately, value in output)
"""

from datetime import datetime
from events import GameEvent, ScoutingEvent, EventDatabaseAPI
from constants.team_ids import TeamIDs
import json


def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def print_event_data(event_data, title="Event Data"):
    """Pretty print event data structure"""
    print(f"\n📋 {title}:")
    print(json.dumps(event_data, indent=2, default=str))


def test_parameterized_event_pattern():
    """Test Pattern 1: GameEvent - Schedule first, simulate later"""

    print_section("PATTERN 1: PARAMETERIZED EVENT (GameEvent)")

    # Initialize database
    event_db = EventDatabaseAPI("data/database/test_hybrid_events.db")

    # =========================================================================
    # STEP 1: Create and store event WITH PARAMETERS ONLY (scheduling)
    # =========================================================================
    print("\n1️⃣  Creating GameEvent with parameters only (scheduling)...")

    game = GameEvent(
        away_team_id=TeamIDs.DETROIT_LIONS,
        home_team_id=TeamIDs.GREEN_BAY_PACKERS,
        game_date=datetime(2024, 12, 25, 13, 0),
        week=17,
        season=2024
    )

    print(f"✅ GameEvent created: {game}")
    print(f"   Event ID: {game.event_id}")
    print(f"   Game ID: {game.get_game_id()}")

    # Store with parameters only
    event_db.insert_event(game)
    print("✅ Stored in database (parameters only, no results yet)")

    # Verify stored format
    stored = event_db.get_event_by_id(game.event_id)
    print_event_data(stored, "Stored Event (Parameters Only)")

    # =========================================================================
    # STEP 2: Retrieve and verify NO RESULTS yet
    # =========================================================================
    print("\n2️⃣  Retrieving event before simulation...")

    game_id = game.get_game_id()
    events = event_db.get_events_by_game_id(game_id)
    print(f"✅ Retrieved {len(events)} event(s)")

    print(f"\n📊 Data Structure Analysis:")
    print(f"   Parameters present: {'parameters' in events[0]['data']}")
    print(f"   Results present: {'results' in events[0]['data'] and events[0]['data']['results'] is not None}")
    print(f"   Metadata present: {'metadata' in events[0]['data']}")

    # =========================================================================
    # STEP 3: Simulate game (execute the event)
    # =========================================================================
    print("\n3️⃣  Simulating game...")

    # Reconstruct from database
    game_from_db = GameEvent.from_database(events[0])

    # Run simulation
    print("\n" + "-" * 80)
    result = game_from_db.simulate()
    print("-" * 80)

    print(f"\n✅ Simulation complete: {result.success}")
    print(f"   Away Score: {result.data['away_score']}")
    print(f"   Home Score: {result.data['home_score']}")

    # =========================================================================
    # STEP 4: Update event with results (caching)
    # =========================================================================
    print("\n4️⃣  Updating event with simulation results...")

    event_db.update_event(game_from_db)
    print("✅ Event updated with results")

    # Verify updated format
    updated = event_db.get_event_by_id(game.event_id)
    print_event_data(updated, "Updated Event (Parameters + Results)")

    print(f"\n📊 Data Structure Analysis After Simulation:")
    print(f"   Parameters present: {'parameters' in updated['data']}")
    print(f"   Results present: {'results' in updated['data'] and updated['data']['results'] is not None}")
    print(f"   Metadata present: {'metadata' in updated['data']}")

    # =========================================================================
    # STEP 5: Retrieve with cached results (no re-simulation needed)
    # =========================================================================
    print("\n5️⃣  Retrieving event with cached results...")

    events_after = event_db.get_events_by_game_id(game_id)
    game_with_results = GameEvent.from_database(events_after[0])

    print(f"✅ Event retrieved with historical results")
    print(f"   Can display scores without re-simulating")
    print(f"   Away Score: {events_after[0]['data']['results']['away_score']}")
    print(f"   Home Score: {events_after[0]['data']['results']['home_score']}")

    print("\n💡 Key Takeaway: GameEvent can be SCHEDULED (parameters only), then SIMULATED later and results CACHED")


def test_result_based_event_pattern():
    """Test Pattern 2: ScoutingEvent - Execute immediately, value in output"""

    print_section("PATTERN 2: RESULT-BASED EVENT (ScoutingEvent)")

    # Initialize database
    event_db = EventDatabaseAPI("data/database/test_hybrid_events.db")

    # =========================================================================
    # STEP 1: Create and EXECUTE immediately (results are the value)
    # =========================================================================
    print("\n1️⃣  Creating and executing ScoutingEvent...")

    scout = ScoutingEvent(
        scout_type="college",
        target_positions=["QB", "WR", "TE"],
        num_players=5
    )

    print(f"✅ ScoutingEvent created: {scout}")
    print(f"   Event ID: {scout.event_id}")

    # Execute immediately (generate reports)
    print("\n" + "-" * 80)
    result = scout.simulate()
    print("-" * 80)

    print(f"\n✅ Scouting complete: {result.success}")
    print(f"   Players evaluated: {result.data['total_evaluated']}")

    # =========================================================================
    # STEP 2: Store WITH RESULTS (parameters + results together)
    # =========================================================================
    print("\n2️⃣  Storing scouting event with results...")

    event_db.insert_event(scout)
    print("✅ Stored in database (parameters + results together)")

    # Verify stored format
    stored = event_db.get_event_by_id(scout.event_id)
    print_event_data(stored, "Stored Scouting Event (Parameters + Results)")

    print(f"\n📊 Data Structure Analysis:")
    print(f"   Parameters present: {'parameters' in stored['data']}")
    print(f"   Results present: {'results' in stored['data'] and stored['data']['results'] is not None}")
    print(f"   Metadata present: {'metadata' in stored['data']}")
    print(f"   Number of reports: {len(stored['data']['results']['scouting_reports'])}")

    # =========================================================================
    # STEP 3: Retrieve and display historical reports (no re-execution)
    # =========================================================================
    print("\n3️⃣  Retrieving historical scouting reports...")

    scouting_events = event_db.get_events_by_type("SCOUTING")
    print(f"✅ Retrieved {len(scouting_events)} scouting event(s)")

    for event_data in scouting_events:
        reports = event_data['data']['results']['scouting_reports']
        top_prospect = event_data['data']['results']['top_prospect']

        print(f"\n📋 Scouting Report Summary:")
        print(f"   Total Players: {len(reports)}")
        print(f"   Top Prospect: {top_prospect['name']} ({top_prospect['position']}) - Grade {top_prospect['grade']}")

        print(f"\n   Sample Reports:")
        for i, report in enumerate(reports[:3], 1):
            print(f"   {i}. {report['player_name']} - {report['position']} - {report['overall_grade']}")
            print(f"      Strengths: {', '.join(report['strengths'])}")
            print(f"      Projection: {report['draft_projection']}")

    print("\n💡 Key Takeaway: ScoutingEvent EXECUTES immediately, stores RESULTS as primary value, no replay needed")


def test_mixed_event_timeline():
    """Test Pattern 3: Mixed events in same timeline/context"""

    print_section("PATTERN 3: MIXED EVENT TIMELINE")

    event_db = EventDatabaseAPI("data/database/test_hybrid_events.db")

    # Create a context ID for season timeline
    season_id = "season_2024_week_17"

    # =========================================================================
    # Create multiple event types in same timeline
    # =========================================================================
    print("\n1️⃣  Creating mixed event timeline...")

    # Event 1: Game (parameterized)
    game1 = GameEvent(
        away_team_id=TeamIDs.DETROIT_LIONS,
        home_team_id=TeamIDs.GREEN_BAY_PACKERS,
        game_date=datetime(2024, 12, 25),
        week=17,
        game_id=season_id
    )

    # Event 2: Scouting (result-based)
    scout1 = ScoutingEvent(
        scout_type="pro",
        target_positions=["QB"],
        num_players=3,
        game_id=season_id
    )
    scout1.simulate()  # Execute immediately

    # Event 3: Another game
    game2 = GameEvent(
        away_team_id=TeamIDs.CHICAGO_BEARS,
        home_team_id=TeamIDs.MINNESOTA_VIKINGS,
        game_date=datetime(2024, 12, 26),
        week=17,
        game_id=season_id
    )

    # Store all events
    event_db.insert_events([game1, scout1, game2])
    print(f"✅ Stored 3 mixed events in timeline '{season_id}'")

    # =========================================================================
    # Retrieve ALL events polymorphically
    # =========================================================================
    print("\n2️⃣  Retrieving ALL events from timeline...")

    all_events = event_db.get_events_by_game_id(season_id)
    print(f"✅ Retrieved {len(all_events)} events (mixed types)")

    print(f"\n📊 Timeline Contents:")
    for i, event_data in enumerate(all_events, 1):
        event_type = event_data['event_type']
        timestamp = event_data['timestamp']

        if event_type == 'GAME':
            params = event_data['data']['parameters']
            has_results = event_data['data'].get('results') is not None
            print(f"   {i}. GAME: Team {params['away_team_id']} @ Team {params['home_team_id']}")
            print(f"      Date: {timestamp}")
            print(f"      Simulated: {has_results}")

        elif event_type == 'SCOUTING':
            params = event_data['data']['parameters']
            results = event_data['data']['results']
            print(f"   {i}. SCOUTING: {params['scout_type']}")
            print(f"      Date: {timestamp}")
            print(f"      Players evaluated: {results['total_players_evaluated']}")

    print("\n💡 Key Takeaway: Single call gets ALL event types - polymorphic retrieval!")

    # =========================================================================
    # Database statistics
    # =========================================================================
    print("\n3️⃣  Database Statistics:")

    stats = event_db.get_statistics()
    print(f"\n📈 Event Database Stats:")
    print(f"   Total Events: {stats['total_events']}")
    print(f"   Unique Contexts: {stats['unique_games']}")
    print(f"   Events by Type: {stats['events_by_type']}")


def main():
    print("=" * 80)
    print(" HYBRID EVENT STORAGE SYSTEM TEST")
    print(" Three-Part Architecture: Parameters + Results + Metadata")
    print("=" * 80)

    # Test parameterized events (GameEvent)
    test_parameterized_event_pattern()

    # Test result-based events (ScoutingEvent)
    test_result_based_event_pattern()

    # Test mixed events in same timeline
    test_mixed_event_timeline()

    print_section("✅ ALL TESTS COMPLETE")

    print("\n🎯 Summary of Hybrid Storage Architecture:")
    print("\n1. **Three-Part Structure**:")
    print("   - parameters: Input values for replay/scheduling")
    print("   - results: Output after execution (optional, cached)")
    print("   - metadata: Additional context")

    print("\n2. **Parameterized Events** (GameEvent):")
    print("   - Store parameters first (scheduling)")
    print("   - Simulate later")
    print("   - Cache results for display without re-simulation")

    print("\n3. **Result-Based Events** (ScoutingEvent):")
    print("   - Execute immediately")
    print("   - Store parameters + results together")
    print("   - Results ARE the value (no replay)")

    print("\n4. **Polymorphic Retrieval**:")
    print("   - Single database call gets all event types")
    print("   - Each event knows how to reconstruct itself")
    print("   - Flexible JSON storage supports both patterns")

    print("\n5. **Ready for Extension**:")
    print("   - MediaEvent, TradeEvent, InjuryEvent...")
    print("   - Each chooses its own parameter/result balance")
    print("   - All use same unified storage system")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
