#!/usr/bin/env python3
"""
Test script for OffseasonEventScheduler

This script demonstrates the OffseasonEventScheduler in action.
Note: Run with PYTHONPATH=src
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    # Direct imports to test the scheduler
    from calendar.date_models import Date
    from offseason.offseason_event_scheduler import OffseasonEventScheduler
    # Import from file directly to avoid circular import in __init__
    from events.event_database_api import EventDatabaseAPI

    print("=" * 60)
    print("OFFSEASON EVENT SCHEDULER TEST")
    print("=" * 60)
    print()

    # Create scheduler
    print("1. Creating OffseasonEventScheduler...")
    scheduler = OffseasonEventScheduler()
    print("   ✅ Scheduler created")
    print()

    # Create in-memory database
    print("2. Creating in-memory event database...")
    event_db = EventDatabaseAPI(':memory:')
    print(f"   ✅ Database created at: {event_db.db_path}")
    print()

    # Schedule offseason events
    print("3. Scheduling offseason events...")
    super_bowl_date = Date(2025, 2, 9)  # Example: February 9, 2025
    print(f"   Super Bowl Date: {super_bowl_date}")
    print(f"   Season Year: 2024")
    print(f"   Dynasty ID: test_dynasty")
    print()

    try:
        result = scheduler.schedule_offseason_events(
            super_bowl_date=super_bowl_date,
            season_year=2024,
            dynasty_id='test_dynasty',
            event_db=event_db
        )

        print("4. ✅ SCHEDULING SUCCESSFUL!")
        print()
        print("   Results:")
        print(f"   - Total Events Scheduled: {result['total_events']}")
        print(f"   - Deadline Events: {result['deadline_events']}")
        print(f"   - Window Events: {result['window_events']}")
        print(f"   - Milestone Events: {result['milestone_events']}")
        print(f"   - Season Year: {result['season_year']}")
        print(f"   - Dynasty ID: {result['dynasty_id']}")
        print()

        # Verify in database
        final_count = event_db.count_events()
        print(f"5. Database verification:")
        print(f"   - Events in database: {final_count}")
        print()

        # Show event breakdown by type
        stats = event_db.get_statistics()
        print(f"6. Event type breakdown:")
        for event_type, count in sorted(stats['events_by_type'].items()):
            print(f"   - {event_type}: {count}")
        print()

        print("=" * 60)
        print("✅ TEST COMPLETE - Implementation Successful!")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
