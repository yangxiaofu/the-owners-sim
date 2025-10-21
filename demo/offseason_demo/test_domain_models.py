"""
Test Domain Models for Offseason Demo

Verification script to test all three domain models with demo database.
"""

import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import domain models from local module
from demo_domain_models import (
    OffseasonDemoDataModel,
    CalendarDemoDataModel,
    TeamDemoDataModel
)


def test_offseason_model():
    """Test OffseasonDemoDataModel."""
    print("\n" + "="*80)
    print("TESTING OFFSEASON DEMO DATA MODEL")
    print("="*80)

    # Initialize model
    model = OffseasonDemoDataModel(
        database_path="demo/offseason_demo/offseason_demo.db",
        dynasty_id="ui_offseason_demo",
        season_year=2025,
        user_team_id=22  # Detroit Lions
    )

    print("\n1. Current Phase:")
    print(f"   Phase: {model.get_current_phase()}")
    print(f"   Display Name: {model.get_current_phase_display_name()}")

    print("\n2. Current Date:")
    print(f"   Date: {model.get_current_date()}")

    print("\n3. Upcoming Deadlines (next 5):")
    deadlines = model.get_upcoming_deadlines(5)
    for i, deadline in enumerate(deadlines, 1):
        print(f"   {i}. {deadline['description']} - {deadline['date']} ({deadline['days_remaining']} days)")

    print("\n4. State Summary:")
    summary = model.get_state_summary()
    print(f"   Dynasty: {summary['dynasty_id']}")
    print(f"   Season: {summary['season_year']}")
    print(f"   Current Phase: {summary['current_phase_display']}")
    print(f"   Offseason Complete: {summary['offseason_complete']}")
    print(f"   Actions Taken: {summary['actions_taken']}")

    print("\n5. Offseason Complete Check:")
    print(f"   Complete: {model.is_offseason_complete()}")

    print("\n✓ OffseasonDemoDataModel tests passed!")


def test_calendar_model():
    """Test CalendarDemoDataModel."""
    print("\n" + "="*80)
    print("TESTING CALENDAR DEMO DATA MODEL")
    print("="*80)

    # Initialize model
    model = CalendarDemoDataModel(
        database_path="demo/offseason_demo/offseason_demo.db",
        dynasty_id="ui_offseason_demo",
        season=2025
    )

    print("\n1. Events for March 2025:")
    march_events = model.get_events_for_month(2025, 3)
    print(f"   Total events: {len(march_events)}")
    if march_events:
        print("   First 5 events:")
        for i, event in enumerate(march_events[:5], 1):
            event_type = event.get('event_type', 'N/A')
            game_id = event.get('game_id', 'N/A')
            print(f"   {i}. {event_type} - {game_id[:40]}...")

    print("\n2. All Offseason Events:")
    offseason_events = model.get_all_offseason_events()
    print(f"   Total offseason events: {len(offseason_events)}")

    # Group by event type
    from collections import defaultdict
    events_by_type = defaultdict(int)
    for event in offseason_events:
        events_by_type[event.get('event_type', 'UNKNOWN')] += 1

    print("   Events by type:")
    for event_type, count in sorted(events_by_type.items()):
        print(f"     {event_type}: {count}")

    print("\n3. Event Details Test:")
    if march_events:
        first_event_id = march_events[0].get('event_id')
        details = model.get_event_details(first_event_id)
        if details:
            print(f"   Event ID: {details.get('event_id')}")
            print(f"   Event Type: {details.get('event_type')}")
            print(f"   Game ID: {details.get('game_id', 'N/A')}")
        else:
            print("   No details found (may be from games table)")

    print("\n✓ CalendarDemoDataModel tests passed!")


def test_team_model():
    """Test TeamDemoDataModel."""
    print("\n" + "="*80)
    print("TESTING TEAM DEMO DATA MODEL")
    print("="*80)

    # Initialize model
    model = TeamDemoDataModel(
        database_path="demo/offseason_demo/offseason_demo.db",
        dynasty_id="ui_offseason_demo",
        season=2025
    )

    # Test with Detroit Lions (team_id=22)
    team_id = 22

    print(f"\n1. Team Info (Team #{team_id}):")
    team_info = model.get_team_info(team_id)
    print(f"   Name: {team_info['name']}")
    print(f"   Abbreviation: {team_info['abbreviation']}")
    print(f"   City: {team_info['city']}")
    print(f"   Division: {team_info['division']}")
    print(f"   Conference: {team_info['conference']}")

    print(f"\n2. Team Roster (Mock Data):")
    roster = model.get_team_roster(team_id)
    print(f"   Roster size: {len(roster)}")
    for player in roster:
        print(f"   - {player['name']} ({player['position']}) - #{player['jersey_number']}")

    print(f"\n3. Team Cap Space:")
    cap_space = model.get_team_cap_space(team_id)
    print(f"   Cap Limit: ${cap_space['cap_limit']:,}")
    print(f"   Cap Used: ${cap_space['cap_used']:,}")
    print(f"   Cap Space: ${cap_space['cap_space']:,}")
    print(f"   Top 51 Total: ${cap_space['top_51_total']:,}")
    print(f"   Contracts: {cap_space['contracts_count']}")

    print(f"\n4. Upcoming Free Agents:")
    ufas = model.get_team_upcoming_free_agents(team_id)
    print(f"   Total UFAs: {len(ufas)}")
    for ufa in ufas:
        print(f"   - {ufa['name']} ({ufa['position']}) - Priority: {ufa['priority']}")
        print(f"     Market Value: ${ufa['estimated_market_value']:,}")
        print(f"     Recommendation: {ufa['recommendation']}")

    print("\n✓ TeamDemoDataModel tests passed!")


def main():
    """Run all domain model tests."""
    print("\n" + "="*80)
    print("OFFSEASON DEMO DOMAIN MODELS - VERIFICATION TESTS")
    print("="*80)

    try:
        test_offseason_model()
        test_calendar_model()
        test_team_model()

        print("\n" + "="*80)
        print("✓ ALL DOMAIN MODEL TESTS PASSED!")
        print("="*80)
        print("\nDomain models are ready for UI integration:")
        print("  - OffseasonDemoDataModel: Offseason state and deadlines")
        print("  - CalendarDemoDataModel: Calendar events and scheduling")
        print("  - TeamDemoDataModel: Team info, roster, cap space")
        print("\n")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
