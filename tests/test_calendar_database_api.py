#!/usr/bin/env python3
"""
Calendar Database API Tests

Test suite for the CalendarDatabaseAPI component.
Tests database operations, schema creation, and error handling.
"""

import sys
import unittest
import tempfile
import os
from datetime import date, datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from calendar.calendar_database_api import CalendarDatabaseAPI
from calendar.event import Event


class TestCalendarDatabaseAPI(unittest.TestCase):
    """Test cases for CalendarDatabaseAPI."""

    def setUp(self):
        """Set up test fixtures with temporary database."""
        # Create temporary database file
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_calendar.db")

        # Initialize API
        self.db_api = CalendarDatabaseAPI(self.db_path)

        # Test events
        self.test_event1 = Event(
            name="Test Event 1",
            event_date=date(2024, 9, 15),
            event_id="test-event-1",
            metadata={"type": "test", "priority": "high"}
        )

        self.test_event2 = Event(
            name="Test Event 2",
            event_date=date(2024, 9, 16),
            event_id="test-event-2",
            metadata={"type": "meeting"}
        )

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary database
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            os.rmdir(self.temp_dir)
        except Exception:
            pass  # Ignore cleanup errors

    def test_schema_initialization(self):
        """Test that database schema is created correctly."""
        # Schema should be created during initialization
        # Test by trying to insert an event
        success = self.db_api.insert_event(self.test_event1)
        self.assertTrue(success)

    def test_insert_event_success(self):
        """Test successful event insertion."""
        success = self.db_api.insert_event(self.test_event1)
        self.assertTrue(success)

        # Verify event was inserted
        retrieved_event = self.db_api.fetch_event_by_id(self.test_event1.event_id)
        self.assertIsNotNone(retrieved_event)
        self.assertEqual(retrieved_event.name, self.test_event1.name)
        self.assertEqual(retrieved_event.event_date, self.test_event1.event_date)
        self.assertEqual(retrieved_event.metadata, self.test_event1.metadata)

    def test_insert_duplicate_event(self):
        """Test that duplicate events are rejected."""
        # Insert first event
        success1 = self.db_api.insert_event(self.test_event1)
        self.assertTrue(success1)

        # Try to insert same event again
        success2 = self.db_api.insert_event(self.test_event1)
        self.assertFalse(success2)

    def test_fetch_events_by_date(self):
        """Test fetching events by date."""
        # Insert events on different dates
        self.db_api.insert_event(self.test_event1)
        self.db_api.insert_event(self.test_event2)

        # Fetch events for first date
        events_sept_15 = self.db_api.fetch_events_by_date(date(2024, 9, 15))
        self.assertEqual(len(events_sept_15), 1)
        self.assertEqual(events_sept_15[0].event_id, self.test_event1.event_id)

        # Fetch events for second date
        events_sept_16 = self.db_api.fetch_events_by_date(date(2024, 9, 16))
        self.assertEqual(len(events_sept_16), 1)
        self.assertEqual(events_sept_16[0].event_id, self.test_event2.event_id)

        # Fetch events for date with no events
        events_empty = self.db_api.fetch_events_by_date(date(2024, 9, 17))
        self.assertEqual(len(events_empty), 0)

    def test_fetch_events_between(self):
        """Test fetching events in date range."""
        # Insert events
        self.db_api.insert_event(self.test_event1)  # Sept 15
        self.db_api.insert_event(self.test_event2)  # Sept 16

        # Add event outside range
        event3 = Event(
            name="Outside Range",
            event_date=date(2024, 9, 20),
            event_id="test-event-3"
        )
        self.db_api.insert_event(event3)

        # Fetch events in range
        events_in_range = self.db_api.fetch_events_between(
            date(2024, 9, 15), date(2024, 9, 16)
        )

        self.assertEqual(len(events_in_range), 2)
        event_ids = {event.event_id for event in events_in_range}
        self.assertEqual(event_ids, {"test-event-1", "test-event-2"})

    def test_fetch_event_by_id(self):
        """Test fetching single event by ID."""
        # Insert event
        self.db_api.insert_event(self.test_event1)

        # Fetch by ID
        retrieved_event = self.db_api.fetch_event_by_id(self.test_event1.event_id)
        self.assertIsNotNone(retrieved_event)
        self.assertEqual(retrieved_event.event_id, self.test_event1.event_id)

        # Fetch non-existent event
        non_existent = self.db_api.fetch_event_by_id("non-existent-id")
        self.assertIsNone(non_existent)

    def test_update_event(self):
        """Test updating an existing event."""
        # Insert original event
        self.db_api.insert_event(self.test_event1)

        # Create updated version
        updated_event = Event(
            name="Updated Event Name",
            event_date=date(2024, 9, 17),
            event_id=self.test_event1.event_id,  # Same ID
            metadata={"type": "updated", "status": "completed"}
        )

        # Update event
        success = self.db_api.update_event(updated_event)
        self.assertTrue(success)

        # Verify update
        retrieved_event = self.db_api.fetch_event_by_id(self.test_event1.event_id)
        self.assertEqual(retrieved_event.name, "Updated Event Name")
        self.assertEqual(retrieved_event.event_date, date(2024, 9, 17))
        self.assertEqual(retrieved_event.metadata["type"], "updated")

    def test_update_nonexistent_event(self):
        """Test updating an event that doesn't exist."""
        success = self.db_api.update_event(self.test_event1)
        self.assertFalse(success)

    def test_delete_event(self):
        """Test deleting an event."""
        # Insert event
        self.db_api.insert_event(self.test_event1)

        # Verify it exists
        self.assertTrue(self.db_api.event_exists(self.test_event1.event_id))

        # Delete event
        success = self.db_api.delete_event(self.test_event1.event_id)
        self.assertTrue(success)

        # Verify it's gone
        self.assertFalse(self.db_api.event_exists(self.test_event1.event_id))

    def test_delete_nonexistent_event(self):
        """Test deleting an event that doesn't exist."""
        success = self.db_api.delete_event("non-existent-id")
        self.assertFalse(success)

    def test_event_exists(self):
        """Test checking if events exist."""
        # Event doesn't exist initially
        self.assertFalse(self.db_api.event_exists(self.test_event1.event_id))

        # Insert event
        self.db_api.insert_event(self.test_event1)

        # Event exists now
        self.assertTrue(self.db_api.event_exists(self.test_event1.event_id))

    def test_get_events_count(self):
        """Test getting total event count."""
        # Initially empty
        self.assertEqual(self.db_api.get_events_count(), 0)

        # Insert events
        self.db_api.insert_event(self.test_event1)
        self.assertEqual(self.db_api.get_events_count(), 1)

        self.db_api.insert_event(self.test_event2)
        self.assertEqual(self.db_api.get_events_count(), 2)

    def test_get_dates_with_events(self):
        """Test getting dates that have events."""
        # Initially empty
        dates = self.db_api.get_dates_with_events()
        self.assertEqual(len(dates), 0)

        # Insert events on different dates
        self.db_api.insert_event(self.test_event1)  # Sept 15
        self.db_api.insert_event(self.test_event2)  # Sept 16

        # Add another event on same date as first
        event3 = Event(
            name="Same Date Event",
            event_date=date(2024, 9, 15),
            event_id="test-event-3"
        )
        self.db_api.insert_event(event3)

        # Get dates with events
        dates = self.db_api.get_dates_with_events()
        self.assertEqual(len(dates), 2)  # Two unique dates
        self.assertIn(date(2024, 9, 15), dates)
        self.assertIn(date(2024, 9, 16), dates)

    def test_clear_all_events(self):
        """Test clearing all events."""
        # Insert events
        self.db_api.insert_event(self.test_event1)
        self.db_api.insert_event(self.test_event2)
        self.assertEqual(self.db_api.get_events_count(), 2)

        # Clear all events
        cleared_count = self.db_api.clear_all_events()
        self.assertEqual(cleared_count, 2)
        self.assertEqual(self.db_api.get_events_count(), 0)

    def test_metadata_serialization(self):
        """Test that metadata is properly serialized/deserialized."""
        # Event with complex metadata
        complex_metadata = {
            "strings": "text",
            "numbers": 42,
            "booleans": True,
            "lists": [1, 2, 3],
            "nested": {"key": "value"}
        }

        event = Event(
            name="Complex Metadata Event",
            event_date=date(2024, 9, 15),
            event_id="complex-metadata",
            metadata=complex_metadata
        )

        # Insert and retrieve
        self.db_api.insert_event(event)
        retrieved_event = self.db_api.fetch_event_by_id(event.event_id)

        # Verify metadata integrity
        self.assertEqual(retrieved_event.metadata, complex_metadata)

    def test_empty_metadata(self):
        """Test handling of events with no metadata."""
        event = Event(
            name="No Metadata Event",
            event_date=date(2024, 9, 15),
            event_id="no-metadata"
        )

        # Insert and retrieve
        self.db_api.insert_event(event)
        retrieved_event = self.db_api.fetch_event_by_id(event.event_id)

        # Should have empty metadata dict
        self.assertEqual(retrieved_event.metadata, {})

    def test_string_representation(self):
        """Test string representations of the API."""
        str_repr = str(self.db_api)
        self.assertIn("CalendarDatabaseAPI", str_repr)
        self.assertIn("events in database", str_repr)

        repr_str = repr(self.db_api)
        self.assertIn("CalendarDatabaseAPI", repr_str)
        self.assertIn("db_path", repr_str)


class TestCalendarDatabaseAPIErrorHandling(unittest.TestCase):
    """Test error handling in CalendarDatabaseAPI."""

    def test_invalid_database_path(self):
        """Test handling of invalid database paths."""
        # This should still work as SQLite creates the file
        invalid_path = "/invalid/path/that/does/not/exist/test.db"

        # Should raise an error due to invalid directory
        with self.assertRaises(Exception):
            CalendarDatabaseAPI(invalid_path)

    def test_corrupted_metadata_handling(self):
        """Test handling of corrupted JSON metadata."""
        # This is hard to test directly since we control the metadata,
        # but we can test the _row_to_event method behavior
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")

        try:
            db_api = CalendarDatabaseAPI(db_path)

            # Test with invalid row data
            invalid_row = ("test-id", "Test Event", "invalid-date", "invalid-json")
            result = db_api._row_to_event(invalid_row)
            self.assertIsNone(result)

        finally:
            try:
                os.remove(db_path)
                os.rmdir(temp_dir)
            except Exception:
                pass


def main():
    """Run all tests."""
    unittest.main(verbosity=2, buffer=True)


if __name__ == '__main__':
    main()