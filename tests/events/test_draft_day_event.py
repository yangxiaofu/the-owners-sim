"""
Tests for DraftDayEvent - Dynamic User Team ID Support

Test coverage for Step 1.2: Add Dynamic User Team ID Support
Tests the @property user_team_id that dynamically fetches from dynasties table
when not explicitly provided at initialization.

Test Cases:
1. Explicit user_team_id provided (should return cached value)
2. Dynamic lookup from dynasties table (when None provided)
3. Error handling when dynasty not found
4. Error handling when team_id is None in dynasties table

All tests follow AAA pattern (Arrange, Act, Assert).
"""

import pytest
import sqlite3
import tempfile
from datetime import datetime

from events.draft_day_event import DraftDayEvent
from calendar.date_models import Date


@pytest.fixture
def test_db():
    """
    Create temporary test database with dynasties table.

    Creates a minimal schema with:
    - dynasties: Main dynasty records with team_id
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # Create dynasties table
    conn.execute('''
        CREATE TABLE dynasties (
            dynasty_id TEXT PRIMARY KEY,
            dynasty_name TEXT NOT NULL,
            owner_name TEXT,
            team_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    import os
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def sample_dynasty(test_db):
    """
    Insert a sample dynasty with team_id=7 (Denver Broncos).

    Returns:
        tuple: (db_path, dynasty_id, team_id)
    """
    conn = sqlite3.connect(test_db)

    conn.execute('''
        INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id)
        VALUES (?, ?, ?, ?)
    ''', ("test_dynasty", "Test Dynasty", "Test User", 7))

    conn.commit()
    conn.close()

    return test_db, "test_dynasty", 7


def test_explicit_user_team_id_returns_cached_value(test_db):
    """
    Test 1: When user_team_id is explicitly provided, property returns that value.

    Verifies that:
    - Property returns the cached value without querying database
    - No database errors even if dynasty doesn't exist
    """
    # Arrange
    event = DraftDayEvent(
        season_year=2025,
        event_date=Date(2025, 4, 24),
        dynasty_id="nonexistent_dynasty",
        database_path=test_db,
        user_team_id=22,  # Philadelphia Eagles (explicit)
        verbose=False
    )

    # Act
    result = event.user_team_id

    # Assert
    assert result == 22, "Should return explicitly provided user_team_id"


def test_dynamic_lookup_from_dynasties_table(sample_dynasty):
    """
    Test 2: When user_team_id is None, property fetches from dynasties table.

    Verifies that:
    - Property queries database when _user_team_id is None
    - Correct team_id is returned from dynasty record
    """
    # Arrange
    db_path, dynasty_id, expected_team_id = sample_dynasty

    event = DraftDayEvent(
        season_year=2025,
        event_date=Date(2025, 4, 24),
        dynasty_id=dynasty_id,
        database_path=db_path,
        user_team_id=None,  # Trigger dynamic lookup
        verbose=False
    )

    # Act
    result = event.user_team_id

    # Assert
    assert result == expected_team_id, f"Should fetch team_id={expected_team_id} from dynasties table"


def test_error_when_dynasty_not_found(test_db):
    """
    Test 3: When dynasty doesn't exist, property raises ValueError.

    Verifies that:
    - Appropriate error message is raised
    - Error message includes dynasty_id for debugging
    """
    # Arrange
    event = DraftDayEvent(
        season_year=2025,
        event_date=Date(2025, 4, 24),
        dynasty_id="nonexistent_dynasty",
        database_path=test_db,
        user_team_id=None,  # Trigger dynamic lookup
        verbose=False
    )

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        _ = event.user_team_id

    assert "nonexistent_dynasty" in str(exc_info.value)
    assert "No user_team_id found" in str(exc_info.value)


def test_error_when_team_id_is_none_in_database(test_db):
    """
    Test 4: When dynasty exists but team_id is NULL, property raises ValueError.

    Verifies that:
    - Error is raised when team_id is None (commissioner mode)
    - Error message is descriptive
    """
    # Arrange - Insert dynasty with NULL team_id
    conn = sqlite3.connect(test_db)
    conn.execute('''
        INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id)
        VALUES (?, ?, ?, ?)
    ''', ("commissioner_dynasty", "Commissioner Dynasty", "Admin", None))
    conn.commit()
    conn.close()

    event = DraftDayEvent(
        season_year=2025,
        event_date=Date(2025, 4, 24),
        dynasty_id="commissioner_dynasty",
        database_path=test_db,
        user_team_id=None,
        verbose=False
    )

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        _ = event.user_team_id

    assert "commissioner_dynasty" in str(exc_info.value)
    assert "No user_team_id found" in str(exc_info.value)


def test_caching_behavior(sample_dynasty):
    """
    Test 5: Verify that explicit user_team_id is cached and not overridden.

    Verifies that:
    - Once _user_team_id is set, it's never replaced by database lookup
    - Property doesn't make unnecessary database queries
    """
    # Arrange
    db_path, dynasty_id, db_team_id = sample_dynasty

    event = DraftDayEvent(
        season_year=2025,
        event_date=Date(2025, 4, 24),
        dynasty_id=dynasty_id,
        database_path=db_path,
        user_team_id=15,  # Different from database value (7)
        verbose=False
    )

    # Act - Access property multiple times
    result1 = event.user_team_id
    result2 = event.user_team_id

    # Assert - Always returns cached value, not database value
    assert result1 == 15, "First access should return cached value"
    assert result2 == 15, "Second access should return same cached value"
    assert result1 != db_team_id, "Should not fetch from database when cached value exists"


def test_repr_does_not_trigger_database_query(test_db):
    """
    Test 6: Verify that __repr__ uses _user_team_id to avoid triggering database queries.

    Verifies that:
    - __repr__ can be called without database errors
    - __repr__ shows the raw _user_team_id value (None if not set)
    """
    # Arrange
    event = DraftDayEvent(
        season_year=2025,
        event_date=Date(2025, 4, 24),
        dynasty_id="nonexistent_dynasty",
        database_path=test_db,
        user_team_id=None,
        verbose=False
    )

    # Act - Call __repr__ (should not trigger database query or raise error)
    repr_str = repr(event)

    # Assert
    assert "DraftDayEvent" in repr_str
    assert "season=2025" in repr_str
    assert "nonexistent_dynasty" in repr_str
    assert "user_team=None" in repr_str  # Shows None, doesn't try to fetch
