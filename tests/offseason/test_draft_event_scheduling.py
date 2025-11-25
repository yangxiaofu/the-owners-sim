"""Test that DraftDayEvent is scheduled correctly during offseason."""

import pytest
import tempfile
import os
from src.offseason.offseason_event_scheduler import OffseasonEventScheduler
from src.calendar.date_models import Date
from events.event_database_api import EventDatabaseAPI


def test_draft_day_event_scheduled():
    """Verify DraftDayEvent is created in database with dynamic date."""
    # Create temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        db_path = tmp_file.name

    try:
        # Setup
        event_db = EventDatabaseAPI(db_path)
        scheduler = OffseasonEventScheduler()

        super_bowl_date = Date(2025, 2, 9)
        season_year = 2025
        dynasty_id = "test_dynasty"

        # Execute
        result = scheduler.schedule_offseason_events(
            super_bowl_date=super_bowl_date,
            season_year=season_year,
            dynasty_id=dynasty_id,
            event_db=event_db
        )

        # Verify: Query for DRAFT_DAY event using direct SQL connection
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
            SELECT event_type, timestamp, data
            FROM events
            WHERE event_type = 'DRAFT_DAY' AND dynasty_id = ?
        """
        row = cursor.execute(query, (dynasty_id,)).fetchone()
        conn.close()

        assert row is not None, "DraftDayEvent not found in database"
        assert row[0] == "DRAFT_DAY", f"Expected event_type DRAFT_DAY, got {row[0]}"

        # Convert timestamp to date (timestamp is in milliseconds)
        event_date_ts = row[1] / 1000  # Convert ms to seconds
        event_datetime = datetime.fromtimestamp(event_date_ts)
        event_date_str = event_datetime.strftime("%Y-%m-%d")

        # 2026 (season_year + 1) draft should be calculated dynamically
        # April 30, 2026 is Thursday (last Thursday), but our algorithm uses April 23
        # because of the year >= 2020 rule to avoid May spillover
        expected_date = "2026-04-23"  # Avoids April 30 per 2020+ rule
        assert event_date_str == expected_date, f"Expected draft date {expected_date}, got {event_date_str}"

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)


def test_draft_date_is_dynamic_per_year():
    """Verify draft date changes correctly for different season years."""
    # Create temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        db_path = tmp_file.name

    try:
        # Test multiple years
        test_cases = [
            # (season_year, expected_draft_date)
            (2020, "2021-04-29"),  # Last Thursday April 2021
            (2024, "2025-04-24"),  # Last Thursday April 2025
            (2025, "2026-04-23"),  # April 30 is Thursday but avoided (>= 2020 rule)
        ]

        for season_year, expected_date in test_cases:
            # Recreate database for each test
            event_db = EventDatabaseAPI(db_path)

            # Clear events table using direct SQL connection
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM events")
            conn.commit()
            conn.close()

            scheduler = OffseasonEventScheduler()
            super_bowl_date = Date(season_year, 2, 9)
            dynasty_id = f"test_dynasty_{season_year}"

            # Schedule events
            scheduler.schedule_offseason_events(
                super_bowl_date=super_bowl_date,
                season_year=season_year,
                dynasty_id=dynasty_id,
                event_db=event_db
            )

            # Query for draft event using direct SQL connection
            import sqlite3
            from datetime import datetime
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            query = """
                SELECT timestamp
                FROM events
                WHERE event_type = 'DRAFT_DAY' AND dynasty_id = ?
            """
            row = cursor.execute(query, (dynasty_id,)).fetchone()
            conn.close()

            assert row is not None, f"DraftDayEvent not found for season_year {season_year}"

            # Convert timestamp to date (timestamp is in milliseconds)
            event_date_ts = row[0] / 1000  # Convert ms to seconds
            event_datetime = datetime.fromtimestamp(event_date_ts)
            event_date_str = event_datetime.strftime("%Y-%m-%d")

            assert event_date_str == expected_date, (
                f"Season {season_year}: Expected draft date {expected_date}, got {event_date_str}"
            )

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)


def test_draft_event_is_interactive():
    """Verify DraftDayEvent is created (not basic MilestoneEvent)."""
    # Create temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        db_path = tmp_file.name

    try:
        event_db = EventDatabaseAPI(db_path)
        scheduler = OffseasonEventScheduler()

        super_bowl_date = Date(2025, 2, 9)
        season_year = 2025
        dynasty_id = "test_dynasty"

        # Schedule events
        scheduler.schedule_offseason_events(
            super_bowl_date=super_bowl_date,
            season_year=season_year,
            dynasty_id=dynasty_id,
            event_db=event_db
        )

        # Query for event type using direct SQL connection (check for April events by timestamp)
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
            SELECT event_type, timestamp
            FROM events
            WHERE dynasty_id = ?
        """
        rows = cursor.execute(query, (dynasty_id,)).fetchall()
        conn.close()

        # Filter for April events (month == 4)
        april_events = []
        for row in rows:
            ts = row[1] / 1000  # Convert ms to seconds
            dt = datetime.fromtimestamp(ts)
            if dt.month == 4:
                april_events.append(row[0])

        # Should have DRAFT_DAY (interactive) not DRAFT (milestone)
        assert "DRAFT_DAY" in april_events, f"Expected DRAFT_DAY event in April, got types: {april_events}"
        assert "DRAFT" not in april_events, f"Should not have basic DRAFT milestone, got types: {april_events}"

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)


def test_draft_event_counts_toward_total():
    """Verify draft event is counted in total events returned."""
    # Create temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        db_path = tmp_file.name

    try:
        event_db = EventDatabaseAPI(db_path)
        scheduler = OffseasonEventScheduler()

        super_bowl_date = Date(2025, 2, 9)
        season_year = 2025
        dynasty_id = "test_dynasty"

        # Schedule events
        result = scheduler.schedule_offseason_events(
            super_bowl_date=super_bowl_date,
            season_year=season_year,
            dynasty_id=dynasty_id,
            event_db=event_db
        )

        # Verify result structure
        assert "total_events" in result
        assert "milestone_events" in result

        # Count actual events in database using direct SQL connection
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = "SELECT COUNT(*) FROM events WHERE dynasty_id = ?"
        actual_count = cursor.execute(query, (dynasty_id,)).fetchone()[0]

        assert result["total_events"] == actual_count, (
            f"Expected total_events {result['total_events']} to match database count {actual_count}"
        )

        # Draft should be counted as milestone event
        milestone_query = """
            SELECT COUNT(*) FROM events
            WHERE dynasty_id = ? AND event_type = 'DRAFT_DAY'
        """
        draft_count = cursor.execute(milestone_query, (dynasty_id,)).fetchone()[0]
        conn.close()

        assert draft_count == 1, f"Expected 1 draft event, found {draft_count}"

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)
