#!/usr/bin/env python3
"""
Calendar System Tests

Basic unit tests for the new calendar system MVP.
Tests the core functionality of CalendarManager, Event, and EventStore.
"""

import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from calendar.calendar_manager import CalendarManager
from calendar.event import Event
from calendar.event_store import EventStore


class TestEvent(unittest.TestCase):
    """Test cases for the Event class."""

    def test_event_creation_with_date(self):
        """Test creating an event with a date."""
        test_date = date(2024, 9, 15)
        event = Event(name="Test Event", event_date=test_date)

        self.assertEqual(event.name, "Test Event")
        self.assertEqual(event.event_date, test_date)
        self.assertIsNotNone(event.event_id)
        self.assertEqual(event.metadata, {})

    def test_event_creation_with_datetime(self):
        """Test creating an event with a datetime (should convert to date)."""
        test_datetime = datetime(2024, 9, 15, 14, 30)
        event = Event(name="DateTime Event", event_date=test_datetime)

        self.assertEqual(event.name, "DateTime Event")
        self.assertEqual(event.event_date, test_datetime.date())
        self.assertIsInstance(event.event_date, date)

    def test_event_with_custom_id(self):
        """Test creating an event with a custom ID."""
        custom_id = "custom-event-123"
        event = Event(name="Custom ID Event", event_date=date(2024, 9, 15), event_id=custom_id)

        self.assertEqual(event.event_id, custom_id)

    def test_event_with_metadata(self):
        """Test creating an event with metadata."""
        metadata = {"team": "Lions", "week": 1}
        event = Event(name="Game Event", event_date=date(2024, 9, 15), metadata=metadata)

        self.assertEqual(event.metadata, metadata)

    def test_event_equality(self):
        """Test event equality based on ID."""
        event1 = Event(name="Event 1", event_date=date(2024, 9, 15), event_id="same-id")
        event2 = Event(name="Event 2", event_date=date(2024, 9, 16), event_id="same-id")
        event3 = Event(name="Event 3", event_date=date(2024, 9, 15), event_id="different-id")

        self.assertEqual(event1, event2)  # Same ID
        self.assertNotEqual(event1, event3)  # Different ID

    def test_event_string_representation(self):
        """Test string representation of events."""
        event = Event(name="Test Event", event_date=date(2024, 9, 15))

        str_repr = str(event)
        self.assertIn("Test Event", str_repr)
        self.assertIn("2024-09-15", str_repr)


class TestEventStore(unittest.TestCase):
    """Test cases for the EventStore class."""

    def setUp(self):
        """Set up test fixtures."""
        self.store = EventStore()
        self.test_date = date(2024, 9, 15)
        self.test_event = Event(name="Test Event", event_date=self.test_date)

    def test_event_store_initialization(self):
        """Test event store initialization."""
        self.assertEqual(len(self.store), 0)
        self.assertEqual(str(self.store), "EventStore(0 events across 0 dates)")

    def test_event_store_length(self):
        """Test event store length operator."""
        self.assertEqual(len(self.store), 0)

        # Length will be tested when add_event is implemented
        # For now, just verify the method exists
        self.assertTrue(hasattr(self.store, '__len__'))

    def test_event_store_contains(self):
        """Test event store contains operator."""
        # Contains will be tested when add_event is implemented
        # For now, just verify the method exists
        self.assertTrue(hasattr(self.store, '__contains__'))

    def test_event_store_methods_exist(self):
        """Test that all required methods exist in EventStore."""
        required_methods = [
            'add_event', 'get_events_by_date', 'get_events_in_range',
            'remove_event', 'get_event_by_id', 'has_event',
            'get_all_events', 'get_events_count', 'get_dates_with_events',
            'clear', 'get_statistics'
        ]

        for method_name in required_methods:
            self.assertTrue(hasattr(self.store, method_name),
                           f"EventStore missing method: {method_name}")


class TestCalendarManager(unittest.TestCase):
    """Test cases for the CalendarManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.start_date = date(2024, 9, 1)
        self.calendar = CalendarManager(self.start_date)

    def test_calendar_initialization_with_date(self):
        """Test calendar initialization with a date."""
        self.assertEqual(self.calendar.start_date, self.start_date)
        self.assertEqual(self.calendar.current_date, self.start_date)
        self.assertIsInstance(self.calendar.event_store, EventStore)

    def test_calendar_initialization_with_datetime(self):
        """Test calendar initialization with a datetime."""
        start_datetime = datetime(2024, 9, 1, 14, 30)
        calendar = CalendarManager(start_datetime)

        self.assertEqual(calendar.start_date, start_datetime.date())
        self.assertEqual(calendar.current_date, start_datetime.date())

    def test_calendar_methods_exist(self):
        """Test that all required methods exist in CalendarManager."""
        required_methods = [
            'get_current_date', 'advance_date', 'set_date',
            'schedule_event', 'get_events_for_date', 'get_events_between',
            'remove_event', 'get_event_by_id', 'has_events_on_date',
            'get_next_event_date', 'get_previous_event_date',
            'get_calendar_summary', 'clear_calendar', 'reset_to_date'
        ]

        for method_name in required_methods:
            self.assertTrue(hasattr(self.calendar, method_name),
                           f"CalendarManager missing method: {method_name}")

    def test_calendar_string_representation(self):
        """Test string representation of calendar manager."""
        str_repr = str(self.calendar)
        self.assertIn("CalendarManager", str_repr)
        self.assertIn("2024-09-01", str_repr)
        self.assertIn("events=0", str_repr)

    def test_convert_to_date_helper(self):
        """Test the _convert_to_date helper method."""
        test_date = date(2024, 9, 15)
        test_datetime = datetime(2024, 9, 15, 14, 30)

        # Test with date (should return same)
        result_date = self.calendar._convert_to_date(test_date)
        self.assertEqual(result_date, test_date)
        self.assertIsInstance(result_date, date)

        # Test with datetime (should convert to date)
        result_datetime = self.calendar._convert_to_date(test_datetime)
        self.assertEqual(result_datetime, test_datetime.date())
        self.assertIsInstance(result_datetime, date)


class TestCalendarIntegration(unittest.TestCase):
    """Integration tests for the calendar system."""

    def setUp(self):
        """Set up test fixtures."""
        self.calendar = CalendarManager(date(2024, 9, 1))
        self.test_event = Event(name="Integration Test Event", event_date=date(2024, 9, 15))

    def test_calendar_and_event_integration(self):
        """Test that calendar and event classes work together."""
        # Test that we can create events and access calendar
        self.assertIsNotNone(self.test_event)
        self.assertIsNotNone(self.calendar)

        # Test that event store is accessible
        self.assertIsInstance(self.calendar.event_store, EventStore)

    def test_system_imports(self):
        """Test that all system imports work correctly."""
        # This test verifies that the module structure is correct
        from calendar import CalendarManager as CM
        from calendar import Event as E
        from calendar import EventStore as ES

        self.assertEqual(CM, CalendarManager)
        self.assertEqual(E, Event)
        self.assertEqual(ES, EventStore)


def main():
    """Run all tests."""
    unittest.main(verbosity=2, buffer=True)


if __name__ == '__main__':
    main()