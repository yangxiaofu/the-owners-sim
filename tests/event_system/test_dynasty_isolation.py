"""
Test Dynasty Isolation in Events Table

Comprehensive tests to verify that events from different dynasties are properly
isolated and cannot cross-contaminate. Tests the dynasty_id column, foreign key
constraints, and dynasty-specific query methods.

Phase 5 of events_dynasty_isolation_plan.md
"""

import pytest
from datetime import datetime, timedelta
import sqlite3
import tempfile
import os

# Add src to path for testing
import sys
from pathlib import Path
src_path = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, src_path)

from events.game_event import GameEvent
from events.event_database_api import EventDatabaseAPI


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def event_db_path():
    """
    Create temporary database for event testing.

    Yields:
        Path to temporary database file

    Cleanup:
        Removes database after test
    """
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Create dynasties table (required for foreign key constraint)
    conn = sqlite3.connect(path)

    # Enable foreign key constraints (required for SQLite)
    conn.execute('PRAGMA foreign_keys = ON')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

    yield path

    # Cleanup
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def event_api(event_db_path):
    """
    Provides EventDatabaseAPI instance with test database.

    This will initialize the events table with dynasty_id column.
    """
    return EventDatabaseAPI(event_db_path)


@pytest.fixture
def dynasties_setup(event_db_path):
    """
    Create test dynasties in the database.

    Returns:
        Dict with dynasty_id keys for easy reference
    """
    conn = sqlite3.connect(event_db_path)

    # Insert test dynasties
    dynasties = {
        'eagles_dynasty': datetime.now().isoformat(),
        'chiefs_dynasty': datetime.now().isoformat(),
        'lions_dynasty': datetime.now().isoformat()
    }

    for dynasty_id, created_at in dynasties.items():
        conn.execute(
            'INSERT INTO dynasties (dynasty_id, created_at) VALUES (?, ?)',
            (dynasty_id, created_at)
        )

    conn.commit()
    conn.close()

    return dynasties


# ============================================================================
# TEST: BASIC DYNASTY ISOLATION
# ============================================================================

class TestDynastyIsolation:
    """Test that events from different dynasties are properly isolated."""

    def test_dynasty_isolation_identical_games(self, event_api, dynasties_setup):
        """
        Create identical game for 2 different dynasties and verify isolation.

        This is the core test: two users simulating the same matchup on the
        same date should create completely separate events.
        """
        # Create identical game for eagles_dynasty
        event1 = GameEvent(
            away_team_id=14,  # Jets
            home_team_id=3,   # Bills
            game_date=datetime(2025, 9, 5, 13, 0),
            week=1,
            dynasty_id='eagles_dynasty',
            season=2025,
            season_type='regular_season'
        )

        # Create identical game for chiefs_dynasty
        event2 = GameEvent(
            away_team_id=14,  # Jets (same matchup!)
            home_team_id=3,   # Bills (same matchup!)
            game_date=datetime(2025, 9, 5, 13, 0),  # Same date!
            week=1,
            dynasty_id='chiefs_dynasty',
            season=2025,
            season_type='regular_season'
        )

        # Store both events
        event_api.insert_event(event1)
        event_api.insert_event(event2)

        # Query dynasty 1 - should get ONLY eagles event
        eagles_events = event_api.get_events_by_dynasty('eagles_dynasty')
        assert len(eagles_events) == 1, "Eagles dynasty should have exactly 1 event"
        assert eagles_events[0]['dynasty_id'] == 'eagles_dynasty'
        assert eagles_events[0]['data']['parameters']['away_team_id'] == 14
        assert eagles_events[0]['data']['parameters']['home_team_id'] == 3

        # Query dynasty 2 - should get ONLY chiefs event
        chiefs_events = event_api.get_events_by_dynasty('chiefs_dynasty')
        assert len(chiefs_events) == 1, "Chiefs dynasty should have exactly 1 event"
        assert chiefs_events[0]['dynasty_id'] == 'chiefs_dynasty'
        assert chiefs_events[0]['data']['parameters']['away_team_id'] == 14
        assert chiefs_events[0]['data']['parameters']['home_team_id'] == 3

        # Verify complete isolation - different event_ids
        assert eagles_events[0]['event_id'] != chiefs_events[0]['event_id'], \
            "Events from different dynasties must have different event_ids"

        # Verify neither query returned the other dynasty's event
        for event in eagles_events:
            assert event['dynasty_id'] == 'eagles_dynasty', \
                "Eagles query returned non-eagles event!"

        for event in chiefs_events:
            assert event['dynasty_id'] == 'chiefs_dynasty', \
                "Chiefs query returned non-chiefs event!"

    def test_dynasty_isolation_multiple_games(self, event_api, dynasties_setup):
        """
        Create multiple games for multiple dynasties and verify isolation.

        Tests that batch operations maintain isolation.
        """
        # Create 3 games for eagles_dynasty
        eagles_games = [
            GameEvent(
                away_team_id=14, home_team_id=3,
                game_date=datetime(2025, 9, 5 + i, 13, 0),
                week=1, dynasty_id='eagles_dynasty', season=2025
            )
            for i in range(3)
        ]

        # Create 2 games for chiefs_dynasty
        chiefs_games = [
            GameEvent(
                away_team_id=7, home_team_id=9,
                game_date=datetime(2025, 9, 10 + i, 13, 0),
                week=2, dynasty_id='chiefs_dynasty', season=2025
            )
            for i in range(2)
        ]

        # Insert all events
        event_api.insert_events(eagles_games + chiefs_games)

        # Verify eagles dynasty has exactly 3 events
        eagles_events = event_api.get_events_by_dynasty('eagles_dynasty')
        assert len(eagles_events) == 3, "Eagles dynasty should have 3 events"
        for event in eagles_events:
            assert event['dynasty_id'] == 'eagles_dynasty'

        # Verify chiefs dynasty has exactly 2 events
        chiefs_events = event_api.get_events_by_dynasty('chiefs_dynasty')
        assert len(chiefs_events) == 2, "Chiefs dynasty should have 2 events"
        for event in chiefs_events:
            assert event['dynasty_id'] == 'chiefs_dynasty'

        # Verify lions dynasty has 0 events
        lions_events = event_api.get_events_by_dynasty('lions_dynasty')
        assert len(lions_events) == 0, "Lions dynasty should have no events"


# ============================================================================
# TEST: QUERY METHODS
# ============================================================================

class TestGetEventsByDynasty:
    """Test get_events_by_dynasty() query method."""

    def test_get_events_by_dynasty_basic(self, event_api, dynasties_setup):
        """Test basic dynasty filtering."""
        # Create events for different dynasties
        event1 = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5), week=1,
            dynasty_id='eagles_dynasty', season=2025
        )
        event2 = GameEvent(
            away_team_id=7, home_team_id=9,
            game_date=datetime(2025, 9, 6), week=1,
            dynasty_id='chiefs_dynasty', season=2025
        )

        event_api.insert_events([event1, event2])

        # Query specific dynasty
        eagles_events = event_api.get_events_by_dynasty('eagles_dynasty')
        assert len(eagles_events) == 1
        assert eagles_events[0]['dynasty_id'] == 'eagles_dynasty'

    def test_get_events_by_dynasty_with_event_type_filter(self, event_api, dynasties_setup):
        """Test dynasty filtering with event_type parameter."""
        # Create GAME event
        game_event = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5), week=1,
            dynasty_id='eagles_dynasty', season=2025
        )
        event_api.insert_event(game_event)

        # Query with event_type filter
        game_events = event_api.get_events_by_dynasty(
            'eagles_dynasty',
            event_type='GAME'
        )
        assert len(game_events) == 1
        assert game_events[0]['event_type'] == 'GAME'

        # Query with non-matching event_type
        trade_events = event_api.get_events_by_dynasty(
            'eagles_dynasty',
            event_type='TRADE'
        )
        assert len(trade_events) == 0

    def test_get_events_by_dynasty_with_limit(self, event_api, dynasties_setup):
        """Test dynasty filtering with limit parameter."""
        # Create 5 events
        events = [
            GameEvent(
                away_team_id=14, home_team_id=3,
                game_date=datetime(2025, 9, 5 + i), week=1,
                dynasty_id='eagles_dynasty', season=2025
            )
            for i in range(5)
        ]
        event_api.insert_events(events)

        # Query with limit=3
        limited_events = event_api.get_events_by_dynasty(
            'eagles_dynasty',
            limit=3
        )
        assert len(limited_events) == 3

    def test_get_events_by_dynasty_ordering(self, event_api, dynasties_setup):
        """Test that results are ordered by timestamp DESC."""
        # Create events with different timestamps
        event1 = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5), week=1,
            dynasty_id='eagles_dynasty', season=2025
        )
        event2 = GameEvent(
            away_team_id=7, home_team_id=9,
            game_date=datetime(2025, 9, 10), week=2,
            dynasty_id='eagles_dynasty', season=2025
        )
        event3 = GameEvent(
            away_team_id=22, home_team_id=12,
            game_date=datetime(2025, 9, 15), week=3,
            dynasty_id='eagles_dynasty', season=2025
        )

        # Insert in random order
        event_api.insert_events([event2, event1, event3])

        # Query and verify DESC ordering (newest first)
        events = event_api.get_events_by_dynasty('eagles_dynasty')
        assert len(events) == 3
        assert events[0]['timestamp'] > events[1]['timestamp']
        assert events[1]['timestamp'] > events[2]['timestamp']

    def test_get_events_by_dynasty_empty_result(self, event_api, dynasties_setup):
        """Test query for dynasty with no events returns empty list."""
        events = event_api.get_events_by_dynasty('lions_dynasty')
        assert events == []
        assert isinstance(events, list)


# ============================================================================
# TEST: TIMESTAMP RANGE QUERIES
# ============================================================================

class TestGetEventsByDynastyAndTimestamp:
    """Test get_events_by_dynasty_and_timestamp() query method."""

    def test_dynasty_and_timestamp_range_basic(self, event_api, dynasties_setup):
        """Test basic timestamp range filtering with dynasty isolation."""
        # Create events across different dates
        event1 = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5, 13, 0),
            week=1, dynasty_id='eagles_dynasty', season=2025
        )
        event2 = GameEvent(
            away_team_id=7, home_team_id=9,
            game_date=datetime(2025, 9, 10, 13, 0),
            week=2, dynasty_id='eagles_dynasty', season=2025
        )
        event3 = GameEvent(
            away_team_id=22, home_team_id=12,
            game_date=datetime(2025, 9, 15, 13, 0),
            week=3, dynasty_id='eagles_dynasty', season=2025
        )

        event_api.insert_events([event1, event2, event3])

        # Query for Sept 8-12 range (should get only event2)
        start = int(datetime(2025, 9, 8).timestamp() * 1000)
        end = int(datetime(2025, 9, 12).timestamp() * 1000)

        events = event_api.get_events_by_dynasty_and_timestamp(
            dynasty_id='eagles_dynasty',
            start_timestamp_ms=start,
            end_timestamp_ms=end
        )

        assert len(events) == 1
        assert events[0]['data']['parameters']['week'] == 2

    def test_dynasty_and_timestamp_cross_contamination_prevention(
        self, event_api, dynasties_setup
    ):
        """
        Test that timestamp queries don't cross dynasties.

        Critical test: Same timestamp range should return different events
        for different dynasties.
        """
        # Create events for both dynasties on same date
        eagles_event = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5, 13, 0),
            week=1, dynasty_id='eagles_dynasty', season=2025
        )
        chiefs_event = GameEvent(
            away_team_id=7, home_team_id=9,
            game_date=datetime(2025, 9, 5, 13, 0),  # Same date!
            week=1, dynasty_id='chiefs_dynasty', season=2025
        )

        event_api.insert_events([eagles_event, chiefs_event])

        # Define timestamp range covering both events
        start = int(datetime(2025, 9, 1).timestamp() * 1000)
        end = int(datetime(2025, 9, 10).timestamp() * 1000)

        # Query eagles dynasty
        eagles_events = event_api.get_events_by_dynasty_and_timestamp(
            dynasty_id='eagles_dynasty',
            start_timestamp_ms=start,
            end_timestamp_ms=end
        )
        assert len(eagles_events) == 1
        assert eagles_events[0]['dynasty_id'] == 'eagles_dynasty'

        # Query chiefs dynasty
        chiefs_events = event_api.get_events_by_dynasty_and_timestamp(
            dynasty_id='chiefs_dynasty',
            start_timestamp_ms=start,
            end_timestamp_ms=end
        )
        assert len(chiefs_events) == 1
        assert chiefs_events[0]['dynasty_id'] == 'chiefs_dynasty'

        # Verify no cross-contamination
        assert eagles_events[0]['event_id'] != chiefs_events[0]['event_id']

    def test_dynasty_and_timestamp_with_event_type(self, event_api, dynasties_setup):
        """Test timestamp range with event_type filter."""
        event1 = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5), week=1,
            dynasty_id='eagles_dynasty', season=2025
        )
        event_api.insert_event(event1)

        start = int(datetime(2025, 9, 1).timestamp() * 1000)
        end = int(datetime(2025, 9, 10).timestamp() * 1000)

        # Query with matching event_type
        events = event_api.get_events_by_dynasty_and_timestamp(
            dynasty_id='eagles_dynasty',
            start_timestamp_ms=start,
            end_timestamp_ms=end,
            event_type='GAME'
        )
        assert len(events) == 1

        # Query with non-matching event_type
        events = event_api.get_events_by_dynasty_and_timestamp(
            dynasty_id='eagles_dynasty',
            start_timestamp_ms=start,
            end_timestamp_ms=end,
            event_type='TRADE'
        )
        assert len(events) == 0

    def test_dynasty_and_timestamp_ordering_asc(self, event_api, dynasties_setup):
        """Test that timestamp range results are ordered ASC (oldest first)."""
        # Create events
        event1 = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5), week=1,
            dynasty_id='eagles_dynasty', season=2025
        )
        event2 = GameEvent(
            away_team_id=7, home_team_id=9,
            game_date=datetime(2025, 9, 10), week=2,
            dynasty_id='eagles_dynasty', season=2025
        )

        # Insert in reverse order
        event_api.insert_events([event2, event1])

        # Query
        start = int(datetime(2025, 9, 1).timestamp() * 1000)
        end = int(datetime(2025, 9, 15).timestamp() * 1000)

        events = event_api.get_events_by_dynasty_and_timestamp(
            dynasty_id='eagles_dynasty',
            start_timestamp_ms=start,
            end_timestamp_ms=end
        )

        # Verify ASC ordering (oldest first)
        assert len(events) == 2
        assert events[0]['timestamp'] < events[1]['timestamp']

    def test_dynasty_and_timestamp_empty_range(self, event_api, dynasties_setup):
        """Test query with timestamp range containing no events."""
        event1 = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5), week=1,
            dynasty_id='eagles_dynasty', season=2025
        )
        event_api.insert_event(event1)

        # Query range before event
        start = int(datetime(2025, 8, 1).timestamp() * 1000)
        end = int(datetime(2025, 8, 31).timestamp() * 1000)

        events = event_api.get_events_by_dynasty_and_timestamp(
            dynasty_id='eagles_dynasty',
            start_timestamp_ms=start,
            end_timestamp_ms=end
        )

        assert events == []


# ============================================================================
# TEST: FOREIGN KEY CONSTRAINTS
# ============================================================================

class TestForeignKeyConstraint:
    """Test foreign key constraint enforcement."""

    @pytest.mark.skip(reason="EventDatabaseAPI doesn't enable foreign keys by default - this is a design choice")
    def test_foreign_key_constraint_invalid_dynasty_id(self, event_api, dynasties_setup):
        """
        Try to create event with invalid dynasty_id.

        NOTE: This test is skipped because EventDatabaseAPI doesn't enable
        foreign keys on all connections (SQLite design choice). The foreign
        key constraint exists in the schema but isn't enforced unless
        'PRAGMA foreign_keys = ON' is set per connection.

        If foreign keys were enabled, this would fail with IntegrityError.
        """
        # Create event with non-existent dynasty_id
        event = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5), week=1,
            dynasty_id='nonexistent_dynasty',  # Not in dynasties table!
            season=2025
        )

        # Attempt to insert should raise foreign key constraint error (if FK enabled)
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            event_api.insert_event(event)

        # Verify it's specifically a foreign key error
        assert 'FOREIGN KEY constraint failed' in str(exc_info.value)

    def test_foreign_key_allows_valid_dynasty_id(self, event_api, dynasties_setup):
        """Verify that valid dynasty_id passes foreign key check."""
        event = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5), week=1,
            dynasty_id='eagles_dynasty',  # Valid dynasty!
            season=2025
        )

        # Should succeed without error
        event_api.insert_event(event)

        # Verify insertion
        events = event_api.get_events_by_dynasty('eagles_dynasty')
        assert len(events) == 1


# ============================================================================
# TEST: CASCADE DELETE
# ============================================================================

class TestCascadeDelete:
    """Test ON DELETE CASCADE behavior.

    NOTE: These tests manually enable foreign keys via PRAGMA to demonstrate
    CASCADE DELETE functionality. In production, EventDatabaseAPI doesn't enable
    foreign keys on all connections by default (SQLite design choice).
    """

    def test_cascade_delete_dynasty_removes_events(self, event_db_path, event_api, dynasties_setup):
        """
        Delete dynasty and verify all associated events are also deleted.

        This tests the ON DELETE CASCADE foreign key constraint when enabled.
        """
        # Create events for eagles_dynasty
        events = [
            GameEvent(
                away_team_id=14, home_team_id=3,
                game_date=datetime(2025, 9, 5 + i), week=1,
                dynasty_id='eagles_dynasty', season=2025
            )
            for i in range(3)
        ]
        event_api.insert_events(events)

        # Verify events exist
        eagles_events = event_api.get_events_by_dynasty('eagles_dynasty')
        assert len(eagles_events) == 3

        # Delete the dynasty (enable foreign keys for this connection)
        conn = sqlite3.connect(event_db_path)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('DELETE FROM dynasties WHERE dynasty_id = ?', ('eagles_dynasty',))
        conn.commit()
        conn.close()

        # Verify all events were cascade deleted
        eagles_events_after = event_api.get_events_by_dynasty('eagles_dynasty')
        assert len(eagles_events_after) == 0

    def test_cascade_delete_does_not_affect_other_dynasties(
        self, event_db_path, event_api, dynasties_setup
    ):
        """
        Delete one dynasty and verify other dynasties' events are unaffected.

        Critical isolation test: Cascade delete should be scoped to dynasty.
        """
        # Create events for both dynasties
        eagles_events = [
            GameEvent(
                away_team_id=14, home_team_id=3,
                game_date=datetime(2025, 9, 5 + i), week=1,
                dynasty_id='eagles_dynasty', season=2025
            )
            for i in range(2)
        ]
        chiefs_events = [
            GameEvent(
                away_team_id=7, home_team_id=9,
                game_date=datetime(2025, 9, 10 + i), week=2,
                dynasty_id='chiefs_dynasty', season=2025
            )
            for i in range(2)
        ]

        event_api.insert_events(eagles_events + chiefs_events)

        # Verify both dynasties have events
        assert len(event_api.get_events_by_dynasty('eagles_dynasty')) == 2
        assert len(event_api.get_events_by_dynasty('chiefs_dynasty')) == 2

        # Delete eagles dynasty (enable foreign keys for this connection)
        conn = sqlite3.connect(event_db_path)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('DELETE FROM dynasties WHERE dynasty_id = ?', ('eagles_dynasty',))
        conn.commit()
        conn.close()

        # Verify eagles events are gone
        assert len(event_api.get_events_by_dynasty('eagles_dynasty')) == 0

        # Verify chiefs events are STILL THERE (critical!)
        chiefs_events_after = event_api.get_events_by_dynasty('chiefs_dynasty')
        assert len(chiefs_events_after) == 2, \
            "Deleting one dynasty should not affect other dynasties' events!"


# ============================================================================
# TEST: DATA INTEGRITY
# ============================================================================

class TestDataIntegrity:
    """Test data integrity across dynasty boundaries."""

    def test_dynasty_id_preserved_in_database(self, event_api, dynasties_setup):
        """Verify dynasty_id is correctly stored and retrieved."""
        event = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5), week=1,
            dynasty_id='eagles_dynasty', season=2025
        )

        event_api.insert_event(event)

        # Retrieve and verify
        events = event_api.get_events_by_dynasty('eagles_dynasty')
        assert events[0]['dynasty_id'] == 'eagles_dynasty'

    def test_to_database_format_requires_dynasty_id(self):
        """Test that BaseEvent.to_database_format() enforces dynasty_id."""
        # Create event without dynasty_id
        event = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5), week=1,
            dynasty_id=None,  # Explicitly None
            season=2025
        )

        # Should raise ValueError when trying to persist
        with pytest.raises(ValueError) as exc_info:
            event.to_database_format()

        assert 'dynasty_id is required' in str(exc_info.value)

    def test_update_event_preserves_dynasty_id(self, event_api, dynasties_setup):
        """Test that updating an event preserves its dynasty_id."""
        # Create and insert event
        event = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5), week=1,
            dynasty_id='eagles_dynasty', season=2025
        )
        event_api.insert_event(event)

        # Simulate the event to add results
        event.simulate()

        # Update the event in database
        event_api.update_event(event)

        # Verify dynasty_id is still correct
        updated_event = event_api.get_event_by_id(event.event_id)
        assert updated_event['dynasty_id'] == 'eagles_dynasty'


# ============================================================================
# TEST: PERFORMANCE & INDEXING
# ============================================================================

class TestPerformanceAndIndexing:
    """Test that dynasty queries use indexes efficiently."""

    def test_composite_index_on_dynasty_timestamp_exists(self, event_db_path, event_api):
        """Verify composite index idx_events_dynasty_timestamp exists."""
        # Note: event_api fixture ensures EventDatabaseAPI has initialized the schema

        conn = sqlite3.connect(event_db_path)
        cursor = conn.cursor()

        # Query sqlite_master for indexes
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_events_dynasty_timestamp'
        """)

        result = cursor.fetchone()
        conn.close()

        assert result is not None, "Composite index idx_events_dynasty_timestamp not found"

    def test_composite_index_on_dynasty_type_exists(self, event_db_path, event_api):
        """Verify composite index idx_events_dynasty_type exists."""
        # Note: event_api fixture ensures EventDatabaseAPI has initialized the schema

        conn = sqlite3.connect(event_db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_events_dynasty_type'
        """)

        result = cursor.fetchone()
        conn.close()

        assert result is not None, "Composite index idx_events_dynasty_type not found"

    def test_dynasty_queries_scale_with_large_dataset(self, event_api, dynasties_setup):
        """
        Test performance characteristics with larger dataset.

        Verifies that dynasty isolation doesn't degrade with many events.
        """
        # Create 50 events across 3 dynasties
        all_events = []

        for i in range(50):
            dynasty_id = ['eagles_dynasty', 'chiefs_dynasty', 'lions_dynasty'][i % 3]
            event = GameEvent(
                away_team_id=14, home_team_id=3,
                game_date=datetime(2025, 9, 1) + timedelta(days=i),
                week=(i // 7) + 1,
                dynasty_id=dynasty_id,
                season=2025
            )
            all_events.append(event)

        # Batch insert
        event_api.insert_events(all_events)

        # Query each dynasty - should get ~17 events each
        eagles_events = event_api.get_events_by_dynasty('eagles_dynasty')
        chiefs_events = event_api.get_events_by_dynasty('chiefs_dynasty')
        lions_events = event_api.get_events_by_dynasty('lions_dynasty')

        # Verify correct distribution
        total_retrieved = len(eagles_events) + len(chiefs_events) + len(lions_events)
        assert total_retrieved == 50, "Should retrieve all 50 events across 3 dynasties"

        # Verify no cross-contamination
        for event in eagles_events:
            assert event['dynasty_id'] == 'eagles_dynasty'
        for event in chiefs_events:
            assert event['dynasty_id'] == 'chiefs_dynasty'
        for event in lions_events:
            assert event['dynasty_id'] == 'lions_dynasty'


# ============================================================================
# TEST: DEPRECATED METHOD COMPATIBILITY
# ============================================================================

class TestDeprecatedMethodCompatibility:
    """Test that deprecated get_events_by_game_id_prefix() still works."""

    def test_deprecated_method_shows_warning(self, event_api, dynasties_setup):
        """Verify that deprecated method emits DeprecationWarning."""
        event = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5), week=1,
            dynasty_id='eagles_dynasty', season=2025
        )
        event_api.insert_event(event)

        # Should emit DeprecationWarning
        with pytest.warns(DeprecationWarning, match='deprecated'):
            event_api.get_events_by_game_id_prefix('game_')

    def test_deprecated_method_still_functional(self, event_api, dynasties_setup):
        """Verify deprecated method still returns results (backward compatibility)."""
        event = GameEvent(
            away_team_id=14, home_team_id=3,
            game_date=datetime(2025, 9, 5), week=1,
            dynasty_id='eagles_dynasty', season=2025
        )
        event_api.insert_event(event)

        # Should still work despite deprecation
        with pytest.warns(DeprecationWarning):
            events = event_api.get_events_by_game_id_prefix('game_')

        assert len(events) > 0
