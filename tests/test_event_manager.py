#!/usr/bin/env python3
"""
Event Manager Tests

Test suite for the EventManager component.
Tests business logic, validation, caching, and error handling.
"""

import sys
import unittest
import tempfile
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from calendar.event_manager import EventManager, EventManagerStats
from calendar.event import Event


class TestEventManager(unittest.TestCase):
    """Test cases for EventManager."""

    def setUp(self):
        """Set up test fixtures with temporary database."""
        # Create temporary database file
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_events.db")

        # Initialize EventManager
        self.event_manager = EventManager(self.db_path, enable_cache=True)

        # Test events
        self.test_event1 = Event(
            name="Business Meeting",
            event_date=date(2024, 9, 15),
            event_id="meeting-001",
            metadata={"attendees": 5, "location": "Conference Room A"}
        )

        self.test_event2 = Event(
            name="Team Standup",
            event_date=date(2024, 9, 16),
            event_id="standup-001",
            metadata={"duration": 30}
        )

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            os.rmdir(self.temp_dir)
        except Exception:
            pass

    def test_save_event_success(self):
        """Test successful event saving."""
        success, error_msg = self.event_manager.save_event(self.test_event1)

        self.assertTrue(success)
        self.assertIsNone(error_msg)

        # Verify event was saved
        retrieved_event = self.event_manager.get_event_by_id(self.test_event1.event_id)
        self.assertIsNotNone(retrieved_event)
        self.assertEqual(retrieved_event.name, self.test_event1.name)

    def test_save_duplicate_event(self):
        """Test saving duplicate event fails."""
        # Save first event
        success1, _ = self.event_manager.save_event(self.test_event1)
        self.assertTrue(success1)

        # Try to save duplicate
        success2, error_msg = self.event_manager.save_event(self.test_event1)
        self.assertFalse(success2)
        self.assertIsNotNone(error_msg)
        self.assertIn("already exists", error_msg)

    def test_event_validation_empty_name(self):
        """Test validation rejects empty event names."""
        invalid_event = Event(
            name="",  # Empty name
            event_date=date(2024, 9, 15),
            event_id="invalid-001"
        )

        success, error_msg = self.event_manager.save_event(invalid_event)
        self.assertFalse(success)
        self.assertIn("name is required", error_msg)

    def test_event_validation_empty_id(self):
        """Test validation rejects empty event IDs."""
        invalid_event = Event(
            name="Valid Name",
            event_date=date(2024, 9, 15),
            event_id=""  # Empty ID
        )

        success, error_msg = self.event_manager.save_event(invalid_event)
        self.assertFalse(success)
        self.assertIn("ID is required", error_msg)

    def test_event_validation_far_past_date(self):
        """Test validation rejects dates too far in the past."""
        old_date = date.today() - timedelta(days=365 * 6)  # 6 years ago
        invalid_event = Event(
            name="Old Event",
            event_date=old_date,
            event_id="old-001"
        )

        success, error_msg = self.event_manager.save_event(invalid_event)
        self.assertFalse(success)
        self.assertIn("5 years in the past", error_msg)

    def test_event_validation_far_future_date(self):
        """Test validation rejects dates too far in the future."""
        future_date = date.today() + timedelta(days=365 * 11)  # 11 years ahead
        invalid_event = Event(
            name="Future Event",
            event_date=future_date,
            event_id="future-001"
        )

        success, error_msg = self.event_manager.save_event(invalid_event)
        self.assertFalse(success)
        self.assertIn("10 years in the future", error_msg)

    def test_get_events_by_date(self):
        """Test retrieving events by date."""
        # Save events on different dates
        self.event_manager.save_event(self.test_event1)  # Sept 15
        self.event_manager.save_event(self.test_event2)  # Sept 16

        # Get events for Sept 15
        events_sept_15 = self.event_manager.get_events_by_date(date(2024, 9, 15))
        self.assertEqual(len(events_sept_15), 1)
        self.assertEqual(events_sept_15[0].event_id, self.test_event1.event_id)

        # Get events for date with no events
        events_empty = self.event_manager.get_events_by_date(date(2024, 9, 17))
        self.assertEqual(len(events_empty), 0)

    def test_get_events_between(self):
        """Test retrieving events in date range."""
        # Save events
        self.event_manager.save_event(self.test_event1)  # Sept 15
        self.event_manager.save_event(self.test_event2)  # Sept 16

        # Add event outside range
        event3 = Event(
            name="Outside Range",
            event_date=date(2024, 9, 20),
            event_id="outside-001"
        )
        self.event_manager.save_event(event3)

        # Get events in range
        events_in_range = self.event_manager.get_events_between(
            date(2024, 9, 15), date(2024, 9, 16)
        )

        self.assertEqual(len(events_in_range), 2)
        event_ids = {event.event_id for event in events_in_range}
        self.assertEqual(event_ids, {"meeting-001", "standup-001"})

    def test_get_events_between_invalid_range(self):
        """Test invalid date range returns empty list."""
        start_date = date(2024, 9, 16)
        end_date = date(2024, 9, 15)  # End before start

        events = self.event_manager.get_events_between(start_date, end_date)
        self.assertEqual(len(events), 0)

    def test_delete_event_success(self):
        """Test successful event deletion."""
        # Save event
        self.event_manager.save_event(self.test_event1)

        # Verify it exists
        self.assertTrue(self.event_manager.event_exists(self.test_event1.event_id))

        # Delete event
        success, error_msg = self.event_manager.delete_event(self.test_event1.event_id)
        self.assertTrue(success)
        self.assertIsNone(error_msg)

        # Verify it's gone
        self.assertFalse(self.event_manager.event_exists(self.test_event1.event_id))

    def test_delete_nonexistent_event(self):
        """Test deleting non-existent event fails gracefully."""
        success, error_msg = self.event_manager.delete_event("non-existent-id")
        self.assertFalse(success)
        self.assertIn("not found", error_msg)

    def test_update_event_success(self):
        """Test successful event update."""
        # Save original event
        self.event_manager.save_event(self.test_event1)

        # Create updated version
        updated_event = Event(
            name="Updated Meeting",
            event_date=date(2024, 9, 17),
            event_id=self.test_event1.event_id,  # Same ID
            metadata={"attendees": 8, "location": "Conference Room B"}
        )

        # Update event
        success, error_msg = self.event_manager.update_event(updated_event)
        self.assertTrue(success)
        self.assertIsNone(error_msg)

        # Verify update
        retrieved_event = self.event_manager.get_event_by_id(self.test_event1.event_id)
        self.assertEqual(retrieved_event.name, "Updated Meeting")
        self.assertEqual(retrieved_event.event_date, date(2024, 9, 17))
        self.assertEqual(retrieved_event.metadata["attendees"], 8)

    def test_update_nonexistent_event(self):
        """Test updating non-existent event fails."""
        success, error_msg = self.event_manager.update_event(self.test_event1)
        self.assertFalse(success)
        self.assertIn("not found", error_msg)

    def test_caching_functionality(self):
        """Test that caching works correctly."""
        # Save event
        self.event_manager.save_event(self.test_event1)

        # First retrieval should miss cache
        initial_stats = self.event_manager.get_manager_stats()
        initial_cache_hits = initial_stats.cache_hit_rate

        # Get event (should cache it)
        event1 = self.event_manager.get_event_by_id(self.test_event1.event_id)
        self.assertIsNotNone(event1)

        # Get same event again (should hit cache)
        event2 = self.event_manager.get_event_by_id(self.test_event1.event_id)
        self.assertIsNotNone(event2)

        # Check cache hit rate improved
        final_stats = self.event_manager.get_manager_stats()
        self.assertGreaterEqual(final_stats.cache_hit_rate, initial_cache_hits)

    def test_cache_disabled(self):
        """Test EventManager with caching disabled."""
        # Create EventManager with caching disabled
        no_cache_manager = EventManager(self.db_path, enable_cache=False)

        # Save and retrieve event
        no_cache_manager.save_event(self.test_event1)
        retrieved_event = no_cache_manager.get_event_by_id(self.test_event1.event_id)

        self.assertIsNotNone(retrieved_event)

        # Stats should show no cached events
        stats = no_cache_manager.get_manager_stats()
        self.assertEqual(stats.cached_events, 0)

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Save and cache some events
        self.event_manager.save_event(self.test_event1)
        self.event_manager.get_event_by_id(self.test_event1.event_id)  # Cache it

        # Verify cache has content
        stats_before = self.event_manager.get_manager_stats()
        self.assertGreater(stats_before.cached_events, 0)

        # Clear cache
        cleared_count = self.event_manager.clear_cache()
        self.assertGreater(cleared_count, 0)

        # Verify cache is empty
        stats_after = self.event_manager.get_manager_stats()
        self.assertEqual(stats_after.cached_events, 0)

    def test_clear_all_events(self):
        """Test clearing all events."""
        # Save multiple events
        self.event_manager.save_event(self.test_event1)
        self.event_manager.save_event(self.test_event2)
        self.assertEqual(self.event_manager.get_events_count(), 2)

        # Clear all events
        cleared_count = self.event_manager.clear_all_events()
        self.assertEqual(cleared_count, 2)
        self.assertEqual(self.event_manager.get_events_count(), 0)

    def test_get_manager_stats(self):
        """Test getting manager statistics."""
        # Initial stats
        stats = self.event_manager.get_manager_stats()
        self.assertIsInstance(stats, EventManagerStats)
        self.assertEqual(stats.total_events, 0)

        # Add event and check stats
        self.event_manager.save_event(self.test_event1)
        stats = self.event_manager.get_manager_stats()
        self.assertEqual(stats.total_events, 1)
        self.assertEqual(stats.dates_with_events, 1)

    def test_get_events_count(self):
        """Test getting total events count."""
        self.assertEqual(self.event_manager.get_events_count(), 0)

        self.event_manager.save_event(self.test_event1)
        self.assertEqual(self.event_manager.get_events_count(), 1)

        self.event_manager.save_event(self.test_event2)
        self.assertEqual(self.event_manager.get_events_count(), 2)

    def test_get_dates_with_events(self):
        """Test getting dates that have events."""
        # Initially empty
        dates = self.event_manager.get_dates_with_events()
        self.assertEqual(len(dates), 0)

        # Add events
        self.event_manager.save_event(self.test_event1)  # Sept 15
        self.event_manager.save_event(self.test_event2)  # Sept 16

        dates = self.event_manager.get_dates_with_events()
        self.assertEqual(len(dates), 2)
        self.assertIn(date(2024, 9, 15), dates)
        self.assertIn(date(2024, 9, 16), dates)

    def test_string_representations(self):
        """Test string representations of EventManager."""
        str_repr = str(self.event_manager)
        self.assertIn("EventManager", str_repr)
        self.assertIn("events", str_repr)
        self.assertIn("cache", str_repr)

        repr_str = repr(self.event_manager)
        self.assertIn("EventManager", repr_str)
        self.assertIn("total_events", repr_str)


class TestEventManagerCaching(unittest.TestCase):
    """Specific tests for caching behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_cache.db")
        self.event_manager = EventManager(self.db_path, enable_cache=True, cache_size_limit=3)

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            os.rmdir(self.temp_dir)
        except Exception:
            pass

    def test_cache_size_limit(self):
        """Test that cache respects size limits."""
        # Create events beyond cache limit
        events = []
        for i in range(5):  # More than cache limit of 3
            event = Event(
                name=f"Event {i}",
                event_date=date(2024, 9, 15 + i),
                event_id=f"event-{i}"
            )
            events.append(event)
            self.event_manager.save_event(event)

        # Access all events to populate cache
        for event in events:
            self.event_manager.get_event_by_id(event.event_id)

        # Cache should not exceed limit
        stats = self.event_manager.get_manager_stats()
        self.assertLessEqual(stats.cached_events, 3)

    def test_cache_eviction(self):
        """Test that cache eviction works when size limit is reached."""
        # Fill cache to limit
        events = []
        for i in range(3):
            event = Event(
                name=f"Event {i}",
                event_date=date(2024, 9, 15 + i),
                event_id=f"event-{i}"
            )
            events.append(event)
            self.event_manager.save_event(event)
            self.event_manager.get_event_by_id(event.event_id)  # Cache it

        # Verify cache is at limit
        stats = self.event_manager.get_manager_stats()
        self.assertEqual(stats.cached_events, 3)

        # Add one more event (should trigger eviction)
        new_event = Event(
            name="New Event",
            event_date=date(2024, 9, 20),
            event_id="new-event"
        )
        self.event_manager.save_event(new_event)
        self.event_manager.get_event_by_id(new_event.event_id)

        # Cache should still be at or below limit
        stats = self.event_manager.get_manager_stats()
        self.assertLessEqual(stats.cached_events, 3)


class TestEventManagerErrorHandling(unittest.TestCase):
    """Test error handling in EventManager."""

    def test_invalid_metadata_validation(self):
        """Test validation of non-serializable metadata."""
        # Create event with non-serializable metadata
        invalid_event = Event(
            name="Invalid Metadata Event",
            event_date=date(2024, 9, 15),
            event_id="invalid-metadata"
        )

        # Add non-serializable object to metadata
        invalid_event.metadata = {"function": lambda x: x}  # Functions aren't JSON serializable

        # Create temporary EventManager
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_error.db")

        try:
            event_manager = EventManager(db_path)
            success, error_msg = event_manager.save_event(invalid_event)

            self.assertFalse(success)
            self.assertIn("JSON-serializable", error_msg)

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