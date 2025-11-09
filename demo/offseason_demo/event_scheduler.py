"""
Event Scheduler for Offseason Demo

This module schedules all NFL offseason events for the UI demo.
Provides comprehensive offseason timeline with deadlines, windows, and milestones.

Usage:
    from event_scheduler import schedule_offseason_events

    event_ids = schedule_offseason_events(
        database_path="data/database/nfl_simulation.db",
        dynasty_id="ui_offseason_demo",
        season_year=2024
    )

    print(f"Scheduled {len(event_ids)} offseason events")
"""

from typing import List, Dict, Any
import logging
from datetime import datetime

from events.deadline_event import DeadlineEvent, DeadlineType
from events.window_event import WindowEvent, WindowName
from events.milestone_event import MilestoneEvent, MilestoneType
from events.event_database_api import EventDatabaseAPI
from src.calendar.date_models import Date


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def schedule_offseason_events(
    database_path: str,
    dynasty_id: str = "ui_offseason_demo",
    season_year: int = 2024
) -> List[int]:
    """
    Schedule all NFL offseason events for the UI demo.

    Creates a complete offseason timeline with all major deadlines,
    windows, and milestones from February through September.

    Args:
        database_path: Path to database file
        dynasty_id: Dynasty context for isolation (default: "ui_offseason_demo")
        season_year: Season year (offseason is year+1) (default: 2024)

    Returns:
        List of event IDs created

    Raises:
        Exception: If database operations fail

    Example:
        >>> event_ids = schedule_offseason_events(
        ...     database_path="data/database/nfl_simulation.db",
        ...     dynasty_id="my_dynasty",
        ...     season_year=2024
        ... )
        >>> print(f"Created {len(event_ids)} events")
        Created 15 events
    """
    logger.info(f"Scheduling offseason events for dynasty: {dynasty_id}, season: {season_year}")

    # Initialize database API
    event_db = EventDatabaseAPI(database_path)

    # Offseason is the year after the season
    offseason_year = season_year + 1

    # Track created events
    created_events = []
    event_count = 0

    try:
        # ============================================================
        # FEBRUARY 2025 - Post-Season Period
        # ============================================================

        # Super Bowl (Feb 9, 2025)
        super_bowl_event = MilestoneEvent(
            milestone_type=MilestoneType.SUPER_BOWL,
            description=f"Super Bowl LIX marks the end of the {season_year} NFL season",
            season_year=season_year,
            event_date=Date(offseason_year, 2, 9),
            dynasty_id=dynasty_id,
            metadata={"location": "TBD", "participants": "TBD"}
        )
        event_db.insert_event(super_bowl_event)
        created_events.append(super_bowl_event.event_id)
        event_count += 1
        logger.info(f"✓ Created Super Bowl milestone: {super_bowl_event.event_date}")

        # ============================================================
        # MARCH 2025 - Free Agency Period Begins
        # ============================================================

        # NFL Combine Results Released (March 1, 2025)
        combine_milestone = MilestoneEvent(
            milestone_type=MilestoneType.COMBINE_END,
            description="NFL Combine results and measurements released for draft prospects",
            season_year=season_year,
            event_date=Date(offseason_year, 3, 1),
            dynasty_id=dynasty_id,
            metadata={"location": "Indianapolis, IN"}
        )
        event_db.insert_event(combine_milestone)
        created_events.append(combine_milestone.event_id)
        event_count += 1
        logger.info(f"✓ Created Combine milestone: {combine_milestone.event_date}")

        # Franchise Tag Deadline (March 5, 2025)
        franchise_tag_deadline = DeadlineEvent(
            deadline_type=DeadlineType.FRANCHISE_TAG,
            description="Deadline for teams to designate franchise tag players",
            season_year=season_year,
            event_date=Date(offseason_year, 3, 5),
            dynasty_id=dynasty_id,
            database_path=database_path
        )
        event_db.insert_event(franchise_tag_deadline)
        created_events.append(franchise_tag_deadline.event_id)
        event_count += 1
        logger.info(f"✓ Created Franchise Tag deadline: {franchise_tag_deadline.event_date}")

        # Legal Tampering Period Start (March 11, 2025)
        legal_tampering_start = WindowEvent(
            window_name=WindowName.LEGAL_TAMPERING,
            window_type="START",
            description="Teams may begin negotiating with pending free agents (48-hour window)",
            season_year=season_year,
            event_date=Date(offseason_year, 3, 11),
            dynasty_id=dynasty_id
        )
        event_db.insert_event(legal_tampering_start)
        created_events.append(legal_tampering_start.event_id)
        event_count += 1
        logger.info(f"✓ Created Legal Tampering START: {legal_tampering_start.event_date}")

        # Legal Tampering Period End (March 13, 2025 - 4:00 PM ET)
        legal_tampering_end = WindowEvent(
            window_name=WindowName.LEGAL_TAMPERING,
            window_type="END",
            description="Legal tampering period ends at 4:00 PM ET",
            season_year=season_year,
            event_date=Date(offseason_year, 3, 13),
            dynasty_id=dynasty_id
        )
        event_db.insert_event(legal_tampering_end)
        created_events.append(legal_tampering_end.event_id)
        event_count += 1
        logger.info(f"✓ Created Legal Tampering END: {legal_tampering_end.event_date}")

        # Free Agency Opens (March 13, 2025 - 4:00 PM ET)
        free_agency_opens = DeadlineEvent(
            deadline_type="FREE_AGENCY_OPEN",
            description="NFL Free Agency officially opens at 4:00 PM ET - contracts can be signed",
            season_year=season_year,
            event_date=Date(offseason_year, 3, 13),
            dynasty_id=dynasty_id,
            database_path=database_path
        )
        event_db.insert_event(free_agency_opens)
        created_events.append(free_agency_opens.event_id)
        event_count += 1
        logger.info(f"✓ Created Free Agency Open deadline: {free_agency_opens.event_date}")

        # Free Agency Period Window Start (March 13, 2025)
        free_agency_start = WindowEvent(
            window_name=WindowName.FREE_AGENCY,
            window_type="START",
            description="Free Agency period begins - teams can sign unrestricted free agents",
            season_year=season_year,
            event_date=Date(offseason_year, 3, 13),
            dynasty_id=dynasty_id
        )
        event_db.insert_event(free_agency_start)
        created_events.append(free_agency_start.event_id)
        event_count += 1
        logger.info(f"✓ Created Free Agency Window START: {free_agency_start.event_date}")

        # ============================================================
        # APRIL 2025 - NFL Draft
        # ============================================================

        # Draft Starts (April 24, 2025)
        draft_start = DeadlineEvent(
            deadline_type="DRAFT_START",
            description="NFL Draft begins - Round 1",
            season_year=season_year,
            event_date=Date(offseason_year, 4, 24),
            dynasty_id=dynasty_id,
            database_path=database_path
        )
        event_db.insert_event(draft_start)
        created_events.append(draft_start.event_id)
        event_count += 1
        logger.info(f"✓ Created Draft Start deadline: {draft_start.event_date}")

        # Draft Ends (April 27, 2025)
        draft_end = DeadlineEvent(
            deadline_type="DRAFT_END",
            description="NFL Draft concludes - Rounds 4-7 complete",
            season_year=season_year,
            event_date=Date(offseason_year, 4, 27),
            dynasty_id=dynasty_id,
            database_path=database_path
        )
        event_db.insert_event(draft_end)
        created_events.append(draft_end.event_id)
        event_count += 1
        logger.info(f"✓ Created Draft End deadline: {draft_end.event_date}")

        # ============================================================
        # MAY 2025 - OTAs Begin
        # ============================================================

        # OTAs Begin (May 20, 2025)
        otas_begin = MilestoneEvent(
            milestone_type="OTAS_BEGIN",
            description="Organized Team Activities (OTAs) begin - voluntary offseason workouts",
            season_year=season_year,
            event_date=Date(offseason_year, 5, 20),
            dynasty_id=dynasty_id,
            metadata={"phase": "Phase 3", "duration_weeks": 4}
        )
        event_db.insert_event(otas_begin)
        created_events.append(otas_begin.event_id)
        event_count += 1
        logger.info(f"✓ Created OTAs Begin milestone: {otas_begin.event_date}")

        # ============================================================
        # JULY 2025 - Training Camp
        # ============================================================

        # Training Camp Opens (July 23, 2025)
        training_camp_opens = MilestoneEvent(
            milestone_type="TRAINING_CAMP_OPEN",
            description="NFL Training Camps open league-wide",
            season_year=season_year,
            event_date=Date(offseason_year, 7, 23),
            dynasty_id=dynasty_id,
            metadata={"camp_duration_weeks": 5}
        )
        event_db.insert_event(training_camp_opens)
        created_events.append(training_camp_opens.event_id)
        event_count += 1
        logger.info(f"✓ Created Training Camp milestone: {training_camp_opens.event_date}")

        # ============================================================
        # AUGUST 2025 - Roster Cuts
        # ============================================================

        # Roster Cuts to 53 (August 26, 2025)
        roster_cuts = DeadlineEvent(
            deadline_type=DeadlineType.FINAL_ROSTER_CUTS,
            description="Final roster cuts to 53 players - 4:00 PM ET deadline",
            season_year=season_year,
            event_date=Date(offseason_year, 8, 26),
            dynasty_id=dynasty_id,
            database_path=database_path
        )
        event_db.insert_event(roster_cuts)
        created_events.append(roster_cuts.event_id)
        event_count += 1
        logger.info(f"✓ Created Roster Cuts deadline: {roster_cuts.event_date}")

        # ============================================================
        # SEPTEMBER 2025 - Season Begins
        # ============================================================

        # Season Begins (September 5, 2025)
        season_begins = MilestoneEvent(
            milestone_type="SEASON_START",
            description=f"{offseason_year} NFL Regular Season begins (Week 1)",
            season_year=season_year + 1,  # Next season starts
            event_date=Date(offseason_year, 9, 5),
            dynasty_id=dynasty_id,
            metadata={"week": 1, "season": offseason_year}
        )
        event_db.insert_event(season_begins)
        created_events.append(season_begins.event_id)
        event_count += 1
        logger.info(f"✓ Created Season Start milestone: {season_begins.event_date}")

        # Free Agency Period Window End (September 5, 2025)
        free_agency_end = WindowEvent(
            window_name=WindowName.FREE_AGENCY,
            window_type="END",
            description="Offseason Free Agency period ends with regular season start",
            season_year=season_year,
            event_date=Date(offseason_year, 9, 5),
            dynasty_id=dynasty_id
        )
        event_db.insert_event(free_agency_end)
        created_events.append(free_agency_end.event_id)
        event_count += 1
        logger.info(f"✓ Created Free Agency Window END: {free_agency_end.event_date}")

        # ============================================================
        # Summary
        # ============================================================

        logger.info(f"\n{'='*60}")
        logger.info(f"Successfully scheduled {event_count} offseason events")
        logger.info(f"Dynasty ID: {dynasty_id}")
        logger.info(f"Season Year: {season_year}")
        logger.info(f"Offseason Year: {offseason_year}")
        logger.info(f"Database: {database_path}")
        logger.info(f"{'='*60}\n")

        # Print event breakdown
        logger.info("Event Breakdown:")
        logger.info(f"  - Deadline Events: 6")
        logger.info(f"  - Window Events: 4")
        logger.info(f"  - Milestone Events: 5")
        logger.info(f"  - Total: {event_count}")

        return created_events

    except Exception as e:
        logger.error(f"Error scheduling offseason events: {e}")
        logger.error(f"Successfully created {len(created_events)} events before failure")
        raise


def get_event_calendar_summary(
    database_path: str,
    dynasty_id: str = "ui_offseason_demo",
    season_year: int = 2024
) -> Dict[str, Any]:
    """
    Get a summary of scheduled offseason events.

    Useful for verification and debugging.

    Args:
        database_path: Path to database file
        dynasty_id: Dynasty context
        season_year: Season year

    Returns:
        Dictionary with event counts and details

    Example:
        >>> summary = get_event_calendar_summary("data/database/nfl_simulation.db")
        >>> print(f"Total events: {summary['total_events']}")
        >>> print(f"Deadlines: {summary['deadline_count']}")
    """
    event_db = EventDatabaseAPI(database_path)

    # Get all events for this dynasty
    all_events = event_db.get_events_by_dynasty(dynasty_id=dynasty_id)

    # Count by type
    deadline_count = len([e for e in all_events if e['event_type'] == 'DEADLINE'])
    window_count = len([e for e in all_events if e['event_type'] == 'WINDOW'])
    milestone_count = len([e for e in all_events if e['event_type'] == 'MILESTONE'])

    # Get date range
    if all_events:
        dates = [e['timestamp'] for e in all_events]
        earliest = min(dates)
        latest = max(dates)
    else:
        earliest = None
        latest = None

    return {
        'total_events': len(all_events),
        'deadline_count': deadline_count,
        'window_count': window_count,
        'milestone_count': milestone_count,
        'earliest_date': earliest,
        'latest_date': latest,
        'dynasty_id': dynasty_id,
        'season_year': season_year,
        'database_path': database_path
    }


def clear_offseason_events(
    database_path: str,
    dynasty_id: str = "ui_offseason_demo"
) -> int:
    """
    Clear all offseason events for a specific dynasty.

    WARNING: This will delete all events for the specified dynasty.
    Use with caution.

    Args:
        database_path: Path to database file
        dynasty_id: Dynasty context to clear

    Returns:
        Number of events deleted

    Example:
        >>> deleted = clear_offseason_events("data/database/nfl_simulation.db")
        >>> print(f"Deleted {deleted} events")
    """
    import sqlite3

    logger.warning(f"Clearing all events for dynasty: {dynasty_id}")

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            'DELETE FROM events WHERE dynasty_id = ?',
            (dynasty_id,)
        )
        deleted_count = cursor.rowcount
        conn.commit()

        logger.info(f"Deleted {deleted_count} events for dynasty: {dynasty_id}")
        return deleted_count

    except Exception as e:
        conn.rollback()
        logger.error(f"Error clearing events: {e}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    """
    Command-line usage for testing and verification.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Schedule NFL offseason events")
    parser.add_argument(
        '--database',
        default='data/database/nfl_simulation.db',
        help='Path to database file'
    )
    parser.add_argument(
        '--dynasty',
        default='ui_offseason_demo',
        help='Dynasty ID'
    )
    parser.add_argument(
        '--season',
        type=int,
        default=2024,
        help='Season year'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing events before scheduling'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary of scheduled events'
    )

    args = parser.parse_args()

    # Clear existing events if requested
    if args.clear:
        deleted = clear_offseason_events(args.database, args.dynasty)
        print(f"\nCleared {deleted} existing events")

    # Schedule events
    if not args.summary:
        print(f"\nScheduling offseason events...")
        print(f"Database: {args.database}")
        print(f"Dynasty: {args.dynasty}")
        print(f"Season: {args.season}")
        print("")

        event_ids = schedule_offseason_events(
            database_path=args.database,
            dynasty_id=args.dynasty,
            season_year=args.season
        )

        print(f"\n✅ Successfully scheduled {len(event_ids)} events")

    # Show summary
    if args.summary or not args.clear:
        print("\nEvent Calendar Summary:")
        print("=" * 60)
        summary = get_event_calendar_summary(
            database_path=args.database,
            dynasty_id=args.dynasty,
            season_year=args.season
        )

        print(f"Total Events: {summary['total_events']}")
        print(f"  - Deadline Events: {summary['deadline_count']}")
        print(f"  - Window Events: {summary['window_count']}")
        print(f"  - Milestone Events: {summary['milestone_count']}")
        print(f"\nDate Range:")
        if summary['earliest_date']:
            print(f"  Earliest: {summary['earliest_date'].strftime('%Y-%m-%d')}")
            print(f"  Latest: {summary['latest_date'].strftime('%Y-%m-%d')}")
        else:
            print(f"  No events found")
        print("=" * 60)
