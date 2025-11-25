# Events Table Dynasty Isolation Migration Plan

**Version:** 1.0.0
**Created:** 2025-10-05
**Status:** Planning Complete - Implementation Pending
**Priority:** High (Architectural Consistency)

---

## Executive Summary

**Problem**: The `events` table is the only database table that lacks a `dynasty_id` column, violating the core architectural principle that "every table (except `dynasties`) includes a `dynasty_id` foreign key."

**Impact**:
- Dynasty cross-contamination (events from different dynasties are indistinguishable)
- Inconsistent query patterns across the codebase
- No referential integrity enforcement
- Poor query performance (string pattern matching vs indexed equality)
- Regular season games don't encode dynasty_id in game_id, causing isolation failures

**Solution**: Add `dynasty_id` column to events table, aligning with the pattern used in `games`, `player_game_stats`, `standings`, and all other core tables.

**Timeline**: 3 weeks
**Complexity**: Medium (database migration + API updates + 11 event types + multiple creation sites)

---

## Architecture Context

### Current Database Pattern

**Every table follows this pattern:**

```sql
CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    dynasty_id TEXT NOT NULL,  -- Isolation column
    season INTEGER NOT NULL,
    ...
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
)
```

**Except events table:**

```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    game_id TEXT NOT NULL,      -- Dynasty info sometimes encoded here (inconsistently)
    data TEXT NOT NULL
    -- Missing: dynasty_id column!
)
```

### Current Isolation Attempt (Broken)

The system attempts dynasty isolation by encoding `dynasty_id` in the `game_id` field:

**✅ Playoff Games** (works):
```python
# playoff_scheduler.py
game_id = f"playoff_{dynasty_id}_{season}_{round}_{game_number}"
# Example: "playoff_eagles_rebuild_2025_wildcard_1"
```

**❌ Regular Season Games** (broken):
```python
# game_event.py:85-86
date_str = self.game_date.strftime("%Y%m%d")
return f"game_{date_str}_{away_team_id}_at_{home_team_id}"
# Example: "game_20250905_14_at_3"  <-- NO DYNASTY_ID!
```

**Result**: Multiple dynasties simulating the same matchup create identical game_ids, causing events to be indistinguishable.

### Why Option 2 (Add Column) Beats Option 1 (Encode in game_id)

| Aspect | Option 1: Encode in game_id | Option 2: Add dynasty_id column |
|--------|----------------------------|----------------------------------|
| **Architectural consistency** | ❌ Violates "every table has dynasty_id" | ✅ Follows established pattern |
| **Query performance** | ❌ `LIKE 'prefix%'` (slow) | ✅ `= 'value'` (fast, indexed) |
| **Referential integrity** | ❌ No foreign key on substring | ✅ Foreign key with CASCADE |
| **Data integrity** | ❌ Typo in string = silent failure | ✅ Database enforces constraints |
| **Separation of concerns** | ❌ game_id does double-duty | ✅ Single responsibility |
| **Debugging** | ❌ Parse string to see dynasty | ✅ Direct column visibility |
| **Future flexibility** | ❌ Adding filters requires re-encoding | ✅ Just add columns |
| **Code clarity** | ❌ Must know format per event type | ✅ Simple `WHERE dynasty_id = ?` |

**Decision**: Option 2 is objectively superior for long-term architecture.

---

## Implementation Plan

### Phase 1: Database Schema Migration (Week 1, Days 1-2)

#### 1.1 Create Migration Script

**File**: `src/database/migrations/001_add_dynasty_id_to_events.py`

```python
"""
Migration: Add dynasty_id column to events table

Adds dynasty_id column with foreign key constraint for proper dynasty isolation.
This aligns the events table with the architectural pattern used in all other tables.
"""

import sqlite3
from pathlib import Path
from typing import Optional

class EventsDynastyIdMigration:
    """Migration to add dynasty_id column to events table."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def up(self):
        """Apply migration: add dynasty_id column."""
        conn = sqlite3.connect(self.db_path)

        try:
            # Step 1: Add dynasty_id column (nullable initially for migration)
            conn.execute('ALTER TABLE events ADD COLUMN dynasty_id TEXT')

            # Step 2: Populate dynasty_id for existing events
            self._migrate_existing_events(conn)

            # Step 3: Make dynasty_id NOT NULL (after population)
            # SQLite doesn't support ALTER COLUMN, so we recreate table
            conn.execute('''
                CREATE TABLE events_new (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    game_id TEXT NOT NULL,
                    dynasty_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
                )
            ''')

            # Copy data
            conn.execute('''
                INSERT INTO events_new
                SELECT event_id, event_type, timestamp, game_id, dynasty_id, data
                FROM events
            ''')

            # Drop old table and rename
            conn.execute('DROP TABLE events')
            conn.execute('ALTER TABLE events_new RENAME TO events')

            # Step 4: Recreate indexes
            conn.execute('CREATE INDEX idx_events_game_id ON events(game_id)')
            conn.execute('CREATE INDEX idx_events_timestamp ON events(timestamp)')
            conn.execute('CREATE INDEX idx_events_type ON events(event_type)')

            # Step 5: Create new composite index for dynasty-filtered queries
            conn.execute('CREATE INDEX idx_events_dynasty_timestamp ON events(dynasty_id, timestamp)')
            conn.execute('CREATE INDEX idx_events_dynasty_type ON events(dynasty_id, event_type)')

            conn.commit()
            print("✅ Migration completed successfully")

        except Exception as e:
            conn.rollback()
            print(f"❌ Migration failed: {e}")
            raise
        finally:
            conn.close()

    def _migrate_existing_events(self, conn: sqlite3.Connection):
        """
        Migrate existing events by inferring dynasty_id.

        Strategy:
        1. For playoff games with dynasty_id in game_id: extract it
        2. For other events: use dynasty_state table to infer from timestamp/season
        3. Default to 'default' if uncertain
        """
        cursor = conn.cursor()

        # Get all events
        cursor.execute('SELECT event_id, game_id, timestamp FROM events')
        events = cursor.fetchall()

        for event_id, game_id, timestamp_ms in events:
            dynasty_id = self._infer_dynasty_id(conn, game_id, timestamp_ms)

            cursor.execute(
                'UPDATE events SET dynasty_id = ? WHERE event_id = ?',
                (dynasty_id, event_id)
            )

        print(f"✅ Migrated {len(events)} existing events")

    def _infer_dynasty_id(
        self,
        conn: sqlite3.Connection,
        game_id: str,
        timestamp_ms: int
    ) -> str:
        """
        Infer dynasty_id from game_id or timestamp.

        Args:
            conn: Database connection
            game_id: Event game_id (may contain dynasty info)
            timestamp_ms: Event timestamp in milliseconds

        Returns:
            Inferred dynasty_id
        """
        # Case 1: Playoff games encode dynasty in game_id
        # Format: "playoff_{dynasty_id}_{season}_{round}_{game}"
        if game_id.startswith('playoff_'):
            parts = game_id.split('_')
            if len(parts) >= 3:
                # Extract dynasty_id (second part)
                return parts[1]

        # Case 2: Check dynasty_state table for active dynasty at this timestamp
        cursor = conn.cursor()

        # Convert timestamp to date
        from datetime import datetime
        event_date = datetime.fromtimestamp(timestamp_ms / 1000)
        date_str = event_date.strftime('%Y-%m-%d')

        cursor.execute('''
            SELECT dynasty_id FROM dynasty_state
            WHERE current_date = ?
            LIMIT 1
        ''', (date_str,))

        result = cursor.fetchone()
        if result:
            return result[0]

        # Case 3: Default fallback
        return 'default'

    def down(self):
        """Rollback migration: remove dynasty_id column."""
        conn = sqlite3.connect(self.db_path)

        try:
            # Recreate table without dynasty_id
            conn.execute('''
                CREATE TABLE events_rollback (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    game_id TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            ''')

            conn.execute('''
                INSERT INTO events_rollback
                SELECT event_id, event_type, timestamp, game_id, data
                FROM events
            ''')

            conn.execute('DROP TABLE events')
            conn.execute('ALTER TABLE events_rollback RENAME TO events')

            # Recreate original indexes
            conn.execute('CREATE INDEX idx_events_game_id ON events(game_id)')
            conn.execute('CREATE INDEX idx_events_timestamp ON events(timestamp)')
            conn.execute('CREATE INDEX idx_events_type ON events(event_type)')

            conn.commit()
            print("✅ Rollback completed successfully")

        except Exception as e:
            conn.rollback()
            print(f"❌ Rollback failed: {e}")
            raise
        finally:
            conn.close()

if __name__ == '__main__':
    # Run migration
    migration = EventsDynastyIdMigration('data/database/nfl_simulation.db')
    migration.up()
```

#### 1.2 Update DatabaseConnection

**File**: `src/database/connection.py`

**Location**: After line 420 (in `_create_tables` method)

**Change**:
```python
# OLD
conn.execute('''
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        game_id TEXT NOT NULL,
        data TEXT NOT NULL
    )
''')

# NEW
conn.execute('''
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        game_id TEXT NOT NULL,
        dynasty_id TEXT NOT NULL,
        data TEXT NOT NULL,
        FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
    )
''')

# Update indexes (after events table creation)
conn.execute('CREATE INDEX IF NOT EXISTS idx_events_game_id ON events(game_id)')
conn.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)')
conn.execute('CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)')
# NEW composite indexes for dynasty-filtered queries
conn.execute('CREATE INDEX IF NOT EXISTS idx_events_dynasty_timestamp ON events(dynasty_id, timestamp)')
conn.execute('CREATE INDEX IF NOT EXISTS idx_events_dynasty_type ON events(dynasty_id, event_type)')
```

---

### Phase 2: Event System API Updates (Week 1, Days 3-5)

#### 2.1 Update BaseEvent Interface

**File**: `src/events/base_event.py`

**Changes**:

1. Add `dynasty_id` to constructor:
```python
def __init__(
    self,
    event_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    dynasty_id: Optional[str] = None  # NEW
):
    """
    Initialize base event properties.

    Args:
        event_id: Unique identifier (generated if not provided)
        timestamp: Event timestamp (defaults to now)
        dynasty_id: Dynasty identifier for isolation (REQUIRED for persistence)
    """
    self.event_id = event_id or str(uuid.uuid4())
    self.timestamp = timestamp or datetime.now()
    self.dynasty_id = dynasty_id  # NEW
```

2. Update `to_database_format()`:
```python
def to_database_format(self) -> Dict[str, Any]:
    """
    Convert event to database storage format.

    Returns:
        Dict with event_id, event_type, timestamp, game_id, dynasty_id, data
    """
    if not self.dynasty_id:
        raise ValueError("dynasty_id is required for event persistence")

    return {
        'event_id': self.event_id,
        'event_type': self.get_event_type(),
        'timestamp': self.timestamp,
        'game_id': self.get_game_id(),
        'dynasty_id': self.dynasty_id,  # NEW
        'data': self._get_parameters()
    }
```

3. Update `from_database()` class method signature (if exists).

#### 2.2 Update EventDatabaseAPI

**File**: `src/events/event_database_api.py`

**Changes**:

1. **Update schema initialization** (line ~75):
```python
conn.execute('''
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        game_id TEXT NOT NULL,
        dynasty_id TEXT NOT NULL,  -- NEW
        data TEXT NOT NULL,
        FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
    )
''')

# Add new indexes
conn.execute('CREATE INDEX IF NOT EXISTS idx_events_dynasty_timestamp ON events(dynasty_id, timestamp)')
conn.execute('CREATE INDEX IF NOT EXISTS idx_events_dynasty_type ON events(dynasty_id, event_type)')
```

2. **Update insert_event()** (line ~124):
```python
conn.execute('''
    INSERT INTO events (event_id, event_type, timestamp, game_id, dynasty_id, data)
    VALUES (?, ?, ?, ?, ?, ?)
''', (
    event_data['event_id'],
    event_data['event_type'],
    int(event_data['timestamp'].timestamp() * 1000),
    event_data['game_id'],
    event_data['dynasty_id'],  # NEW
    json.dumps(event_data['data'])
))
```

3. **Add new query methods**:
```python
def get_events_by_dynasty(
    self,
    dynasty_id: str,
    event_type: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve all events for a specific dynasty.

    Primary query method for dynasty-isolated event retrieval.
    Uses indexed equality for fast performance.

    Args:
        dynasty_id: Dynasty identifier
        event_type: Optional filter by event type
        limit: Optional limit on results

    Returns:
        List of event dictionaries, ordered by timestamp DESC
    """
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        if event_type:
            query = '''
                SELECT * FROM events
                WHERE dynasty_id = ? AND event_type = ?
                ORDER BY timestamp DESC
            '''
            params = (dynasty_id, event_type)
        else:
            query = '''
                SELECT * FROM events
                WHERE dynasty_id = ?
                ORDER BY timestamp DESC
            '''
            params = (dynasty_id,)

        if limit:
            query += f' LIMIT {limit}'

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    finally:
        conn.close()

def get_events_by_dynasty_and_timestamp(
    self,
    dynasty_id: str,
    start_timestamp_ms: int,
    end_timestamp_ms: int,
    event_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve events for dynasty within timestamp range.

    Optimized for calendar queries with composite index on (dynasty_id, timestamp).

    Args:
        dynasty_id: Dynasty identifier
        start_timestamp_ms: Start of range (Unix ms)
        end_timestamp_ms: End of range (Unix ms)
        event_type: Optional filter by event type

    Returns:
        List of event dictionaries, ordered by timestamp ASC
    """
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        if event_type:
            cursor.execute('''
                SELECT * FROM events
                WHERE dynasty_id = ?
                  AND timestamp BETWEEN ? AND ?
                  AND event_type = ?
                ORDER BY timestamp ASC
            ''', (dynasty_id, start_timestamp_ms, end_timestamp_ms, event_type))
        else:
            cursor.execute('''
                SELECT * FROM events
                WHERE dynasty_id = ?
                  AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            ''', (dynasty_id, start_timestamp_ms, end_timestamp_ms))

        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    finally:
        conn.close()
```

4. **Deprecate old method**:
```python
def get_events_by_game_id_prefix(
    self,
    prefix: str,
    event_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    DEPRECATED: Use get_events_by_dynasty() instead.

    This method is kept for backward compatibility but should not be used
    in new code. Dynasty isolation is now handled via the dynasty_id column.
    """
    import warnings
    warnings.warn(
        "get_events_by_game_id_prefix() is deprecated. Use get_events_by_dynasty() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # Keep implementation for now, but log deprecation
    ...
```

#### 2.3 Update All Event Type Classes

**Files to update** (11 files):
- `src/events/game_event.py`
- `src/events/contract_events.py` (4 classes)
- `src/events/free_agency_events.py` (3 classes)
- `src/events/deadline_event.py`
- `src/events/window_event.py`
- `src/events/milestone_event.py`
- `src/events/roster_events.py` (3 classes)
- `src/events/draft_events.py` (3 classes)
- `src/events/scouting_event.py`

**Pattern for each class**:

```python
# Example: GameEvent
class GameEvent(BaseEvent):
    def __init__(
        self,
        away_team_id: int,
        home_team_id: int,
        game_date: datetime,
        week: int,
        dynasty_id: str,  # NEW - REQUIRED
        game_id: Optional[str] = None,
        event_id: Optional[str] = None,
        overtime_type: str = "regular_season",
        season: Optional[int] = None,
        season_type: str = "regular_season",
        game_type: str = "regular"
    ):
        # Call super with dynasty_id
        super().__init__(
            event_id=event_id,
            timestamp=game_date,
            dynasty_id=dynasty_id  # NEW
        )

        # ... rest of init ...
```

**Key points**:
- Add `dynasty_id: str` parameter to `__init__()`
- Pass `dynasty_id` to `super().__init__()`
- Remove dynasty_id encoding from `get_game_id()` methods (keep simple format)
- Update docstrings

---

### Phase 3: Event Creation Updates (Week 2, Days 1-3)

Update all sites that create events to pass `dynasty_id`:

#### 3.1 Playoff System

**File**: `src/playoff_system/playoff_scheduler.py`

**Line**: ~216 (GameEvent creation)

```python
# OLD
event = GameEvent(
    away_team_id=game.away_team_id,
    home_team_id=game.home_team_id,
    game_date=game_datetime,
    week=game.week,
    season_type="playoffs",
    game_type=game.round_name,
    overtime_type="playoffs",
    season=game.season,
    game_id=game_id
)

# NEW
event = GameEvent(
    away_team_id=game.away_team_id,
    home_team_id=game.home_team_id,
    game_date=game_datetime,
    week=game.week,
    dynasty_id=dynasty_id,  # NEW - already have this context
    season_type="playoffs",
    game_type=game.round_name,
    overtime_type="playoffs",
    season=game.season,
    game_id=game_id  # Can now use simple format without dynasty encoding
)
```

**Update `_generate_playoff_game_id()`** (line ~237):
```python
# OLD
return f"playoff_{dynasty_id}_{game.season}_{game.round_name}_{game.game_number}"

# NEW (simpler, dynasty_id is now a column)
return f"playoff_{game.season}_{game.round_name}_{game.game_number}"
```

#### 3.2 Offseason Scheduler

**File**: `src/offseason/offseason_event_scheduler.py`

Add `dynasty_id` parameter to all event creations (already has context).

#### 3.3 Calendar/Season Controllers

**File**: `src/calendar/simulation_executor.py`

If it creates events directly, update to pass dynasty_id.

**File**: `src/season/season_cycle_controller.py`

Update any event creation to include dynasty_id.

---

### Phase 4: UI Controller Updates (Week 2, Days 4-5)

#### 4.1 CalendarController

**File**: `ui/controllers/calendar_controller.py`

**Method**: `get_events_for_month()` (lines ~53-114)

**Replace entire method**:
```python
def get_events_for_month(
    self,
    year: int,
    month: int,
    event_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get filtered events for a specific month.

    Uses dynasty_id column for proper isolation (no string pattern matching).

    Args:
        year: Year to query
        month: Month to query (1-12)
        event_types: Optional list of event types to filter by

    Returns:
        List of event dictionaries matching the criteria, ordered by timestamp
    """
    # Calculate first and last day of month
    from datetime import datetime, timedelta

    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(seconds=1)

    # Convert datetime to milliseconds
    start_ms = int(first_day.timestamp() * 1000)
    end_ms = int(last_day.timestamp() * 1000)

    # Query using new dynasty-aware API
    if event_types:
        all_events = []
        for event_type in event_types:
            events = self.event_api.get_events_by_dynasty_and_timestamp(
                dynasty_id=self.dynasty_id,
                start_timestamp_ms=start_ms,
                end_timestamp_ms=end_ms,
                event_type=event_type
            )
            all_events.extend(events)
    else:
        all_events = self.event_api.get_events_by_dynasty_and_timestamp(
            dynasty_id=self.dynasty_id,
            start_timestamp_ms=start_ms,
            end_timestamp_ms=end_ms
        )

    return all_events
```

**Benefits**:
- ✅ No string pattern matching
- ✅ Indexed query (fast)
- ✅ Proper dynasty isolation
- ✅ Cleaner code

---

### Phase 5: Testing & Validation (Week 3)

#### 5.1 Unit Tests

**New file**: `tests/events/test_dynasty_isolation.py`

```python
"""
Test dynasty isolation in events table.

Verifies that events from different dynasties cannot cross-contaminate.
"""

import pytest
from datetime import datetime
from events.game_event import GameEvent
from events.event_database_api import EventDatabaseAPI

def test_dynasty_isolation():
    """Events from different dynasties are properly isolated."""
    api = EventDatabaseAPI(':memory:')

    # Create identical game for two different dynasties
    event1 = GameEvent(
        away_team_id=14,
        home_team_id=3,
        game_date=datetime(2025, 9, 5),
        week=1,
        dynasty_id='eagles_dynasty'
    )

    event2 = GameEvent(
        away_team_id=14,
        home_team_id=3,
        game_date=datetime(2025, 9, 5),
        week=1,
        dynasty_id='chiefs_dynasty'
    )

    # Store both
    api.insert_event(event1)
    api.insert_event(event2)

    # Query dynasty 1
    eagles_events = api.get_events_by_dynasty('eagles_dynasty')
    assert len(eagles_events) == 1
    assert eagles_events[0]['dynasty_id'] == 'eagles_dynasty'

    # Query dynasty 2
    chiefs_events = api.get_events_by_dynasty('chiefs_dynasty')
    assert len(chiefs_events) == 1
    assert chiefs_events[0]['dynasty_id'] == 'chiefs_dynasty'

    # Verify cross-contamination doesn't occur
    assert eagles_events[0]['event_id'] != chiefs_events[0]['event_id']

def test_cascade_delete():
    """Deleting dynasty removes all associated events."""
    # TODO: Implement cascade deletion test
    pass

def test_timestamp_range_with_dynasty():
    """Timestamp queries properly filter by dynasty."""
    # TODO: Implement timestamp filtering test
    pass
```

**Update existing tests**:
- `tests/events/test_event_database_api.py` - Add dynasty_id to all event creations
- `tests/events/test_game_event.py` - Add dynasty_id parameter
- All event type tests - Update constructors

#### 5.2 Integration Tests

Create comprehensive test suite that:
1. Creates 3 dynasties
2. Simulates games for each dynasty
3. Verifies events are isolated
4. Tests calendar queries don't cross-contaminate
5. Tests performance of indexed queries

#### 5.3 Migration Testing

**Test script**: `tests/database/test_migration.py`

```python
"""Test database migration for dynasty_id column."""

def test_migration_on_copy():
    """Test migration on copy of production database."""
    # Copy production database
    # Run migration
    # Verify all events have dynasty_id
    # Verify foreign keys work
    # Verify indexes created
    pass

def test_rollback():
    """Test rollback procedure."""
    # Run migration
    # Run rollback
    # Verify table schema restored
    pass
```

#### 5.4 Performance Testing

Compare query performance:

```python
# OLD: String pattern matching
SELECT * FROM events WHERE game_id LIKE 'playoff_dynasty_a_%'

# NEW: Indexed equality
SELECT * FROM events WHERE dynasty_id = 'dynasty_a'
```

Expect 5-10x performance improvement on large datasets.

---

### Phase 6: Documentation Updates (Week 3)

#### 6.1 Database Schema Doc

**File**: `docs/schema/database_schema.md`

**Update events table section** (~line 400+):

```markdown
### X. events

Generic event storage for all simulation events (games, deadlines, windows, etc.).

**Architecture**: Polymorphic event storage with dynasty isolation.

```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    game_id TEXT NOT NULL,
    dynasty_id TEXT NOT NULL,  -- Dynasty isolation
    data TEXT NOT NULL,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
)
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `event_id` | TEXT | PRIMARY KEY | Unique event identifier (UUID) |
| `event_type` | TEXT | NOT NULL | Event type ('GAME', 'DEADLINE', 'WINDOW', etc.) |
| `timestamp` | INTEGER | NOT NULL | Unix timestamp in milliseconds |
| `game_id` | TEXT | NOT NULL | Grouping identifier for related events |
| `dynasty_id` | TEXT | NOT NULL | Dynasty isolation (FK to dynasties) |
| `data` | TEXT | NOT NULL | JSON event data |

**Indexes**:
- `idx_events_game_id` - Game ID lookups
- `idx_events_timestamp` - Time-based queries
- `idx_events_type` - Event type filtering
- `idx_events_dynasty_timestamp` - Dynasty + time range queries (composite)
- `idx_events_dynasty_type` - Dynasty + type queries (composite)

**Query Examples**:
```sql
-- Get all events for a dynasty
SELECT * FROM events
WHERE dynasty_id = 'eagles_rebuild_2025'
ORDER BY timestamp DESC;

-- Get events in date range for dynasty
SELECT * FROM events
WHERE dynasty_id = 'eagles_rebuild_2025'
  AND timestamp BETWEEN 1725494400000 AND 1725580800000
ORDER BY timestamp ASC;

-- Get all game events for dynasty
SELECT * FROM events
WHERE dynasty_id = 'eagles_rebuild_2025'
  AND event_type = 'GAME'
ORDER BY timestamp DESC;
```
```

#### 6.2 Architecture Documentation

Update:
- `docs/architecture/event_cap_integration.md` - Add dynasty_id to event examples
- Any other docs that reference events table

#### 6.3 Code Comments

Add migration notes to key files:
- `src/events/base_event.py` - Note about dynasty_id requirement
- `src/events/event_database_api.py` - Document new query methods

---

## Migration Execution Checklist

### Pre-Migration Preparation

- [ ] **Backup production database** (`cp nfl_simulation.db nfl_simulation.db.backup`)
- [ ] **Test migration on database copy** (`cp nfl_simulation.db test_migration.db`)
- [ ] **Document current event count** (currently 272 events)
- [ ] **Review all event creation sites** (11 event types, 4-5 creation sites)
- [ ] **Prepare rollback procedure** (migration script has `down()` method)

### Phase 1: Database Migration

- [ ] Create migration script `src/database/migrations/001_add_dynasty_id_to_events.py`
- [ ] Test migration on copy: `python -m src.database.migrations.001_add_dynasty_id_to_events`
- [ ] Verify all 272 events have dynasty_id assigned
- [ ] Verify foreign key constraints work
- [ ] Verify new indexes created
- [ ] Update `src/database/connection.py` table creation
- [ ] Run migration on production database (with backup!)

### Phase 2: Event API Updates

- [ ] Update `src/events/base_event.py` - Add dynasty_id to constructor
- [ ] Update `src/events/event_database_api.py` - Add new query methods
- [ ] Update `src/events/game_event.py` - Add dynasty_id parameter
- [ ] Update `src/events/contract_events.py` - 4 event classes
- [ ] Update `src/events/free_agency_events.py` - 3 event classes
- [ ] Update `src/events/deadline_event.py`
- [ ] Update `src/events/window_event.py`
- [ ] Update `src/events/milestone_event.py`
- [ ] Update `src/events/roster_events.py` - 3 event classes
- [ ] Update `src/events/draft_events.py` - 3 event classes
- [ ] Update `src/events/scouting_event.py`

### Phase 3: Event Creation Sites

- [ ] Update `src/playoff_system/playoff_scheduler.py` - GameEvent creation
- [ ] Update `src/playoff_system/playoff_scheduler.py` - `_generate_playoff_game_id()`
- [ ] Update `src/offseason/offseason_event_scheduler.py` - All event creations
- [ ] Update `src/calendar/simulation_executor.py` - If creates events
- [ ] Update `src/season/season_cycle_controller.py` - Any event creation

### Phase 4: UI Controllers

- [ ] Update `ui/controllers/calendar_controller.py` - `get_events_for_month()`
- [ ] Update `ui/controllers/simulation_controller.py` - If creates events
- [ ] Test UI calendar view shows correct events
- [ ] Verify no cross-contamination in UI

### Phase 5: Testing

- [ ] Create `tests/events/test_dynasty_isolation.py`
- [ ] Update `tests/events/test_event_database_api.py`
- [ ] Update `tests/events/test_game_event.py`
- [ ] Update all other event type tests (11 files)
- [ ] Run full test suite: `python -m pytest tests/events/`
- [ ] Create integration test with multiple dynasties
- [ ] Performance test: compare old vs new query methods
- [ ] Manual testing: Create 2 dynasties, verify isolation

### Phase 6: Documentation

- [ ] Update `docs/schema/database_schema.md` - events table section
- [ ] Update `docs/architecture/event_cap_integration.md`
- [ ] Update `CHANGELOG.md` with migration notes
- [ ] Add migration notes to `src/events/base_event.py`
- [ ] Document new query methods in `EventDatabaseAPI`

### Post-Migration Validation

- [ ] All tests passing (`pytest tests/`)
- [ ] UI displays correct events for dynasty
- [ ] No performance regression (queries should be faster)
- [ ] No cross-contamination between dynasties
- [ ] Foreign key cascade delete works
- [ ] Can create new dynasties and events work correctly

---

## Rollback Plan

If migration fails or issues discovered:

### Immediate Rollback

1. **Restore database from backup**:
   ```bash
   cp nfl_simulation.db.backup nfl_simulation.db
   ```

2. **Revert code changes**:
   ```bash
   git revert <migration-commit-sha>
   ```

3. **Document failure**:
   - Add note to this plan document
   - Log specific error encountered
   - Identify root cause

### Planned Rollback (if needed after deployment)

1. **Run migration rollback script**:
   ```python
   migration = EventsDynastyIdMigration('data/database/nfl_simulation.db')
   migration.down()
   ```

2. **Revert code changes via git**

3. **Verify system operational with old schema**

---

## Success Criteria

**Database**:
- ✅ Events table has `dynasty_id TEXT NOT NULL` column
- ✅ Foreign key constraint: `FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE`
- ✅ Composite indexes created for performance
- ✅ All existing events have dynasty_id assigned correctly

**Code**:
- ✅ All 11 event types accept `dynasty_id` parameter
- ✅ EventDatabaseAPI has `get_events_by_dynasty()` and `get_events_by_dynasty_and_timestamp()` methods
- ✅ CalendarController uses new query methods
- ✅ All event creation sites pass dynasty_id

**Testing**:
- ✅ Unit tests pass for all event types
- ✅ Dynasty isolation test proves no cross-contamination
- ✅ Performance test shows query improvement
- ✅ UI manual testing confirms correct event display

**Documentation**:
- ✅ Database schema docs updated
- ✅ API documentation reflects new methods
- ✅ Migration notes in CHANGELOG

**Functional**:
- ✅ Can create multiple dynasties without event collision
- ✅ Calendar view shows only events for current dynasty
- ✅ Deleting dynasty cascades to delete all events
- ✅ Query performance improved (5-10x faster)

---

## Timeline Summary

| Phase | Duration | Tasks |
|-------|----------|-------|
| Phase 1 | 2 days | Database migration script + schema update |
| Phase 2 | 3 days | Event API updates (12 files: base + 11 event types) |
| Phase 3 | 3 days | Event creation sites (5 files) |
| Phase 4 | 2 days | UI controllers (2 files) |
| Phase 5 | 4 days | Testing + validation |
| Phase 6 | 1 day | Documentation |
| **Total** | **15 days** | **3 weeks** |

---

## Risk Assessment

### Low Risk
- ✅ Clear precedent to follow (games table already has dynasty_id)
- ✅ Well-defined scope (single table, clear pattern)
- ✅ Reversible (backup + rollback procedure)
- ✅ Non-breaking for existing functionality (additive change)

### Medium Risk
- ⚠️ Existing data migration (272 events need dynasty_id assigned)
  - **Mitigation**: Manual review of migrated events, test on copy first
- ⚠️ Multiple event creation sites (easy to miss one)
  - **Mitigation**: Comprehensive grep search, code review checklist
- ⚠️ 11 event types to update
  - **Mitigation**: Consistent pattern, thorough testing

### High Risk
- ❌ None identified

**Overall Risk**: **Low-Medium** with proper testing and phased approach.

---

## References

- **Database Schema**: `docs/schema/database_schema.md`
- **Event System**: `src/events/`
- **Calendar System**: `src/calendar/`
- **Playoff System**: `src/playoff_system/`
- **UI Controllers**: `ui/controllers/`

---

## Appendix: File Manifest

**Files to Create** (1):
- `src/database/migrations/001_add_dynasty_id_to_events.py`

**Files to Modify** (25):

*Database Layer* (1):
- `src/database/connection.py`

*Event System Core* (2):
- `src/events/base_event.py`
- `src/events/event_database_api.py`

*Event Types* (11):
- `src/events/game_event.py`
- `src/events/contract_events.py`
- `src/events/free_agency_events.py`
- `src/events/deadline_event.py`
- `src/events/window_event.py`
- `src/events/milestone_event.py`
- `src/events/roster_events.py`
- `src/events/draft_events.py`
- `src/events/scouting_event.py`
- (Note: contract_events.py has 4 classes, free_agency_events.py has 3, etc.)

*Event Creation Sites* (5):
- `src/playoff_system/playoff_scheduler.py`
- `src/playoff_system/playoff_controller.py`
- `src/offseason/offseason_event_scheduler.py`
- `src/calendar/simulation_executor.py`
- `src/season/season_cycle_controller.py`

*UI Controllers* (2):
- `ui/controllers/calendar_controller.py`
- `ui/controllers/simulation_controller.py`

*Documentation* (3):
- `docs/schema/database_schema.md`
- `docs/architecture/event_cap_integration.md`
- `CHANGELOG.md`

*Tests* (New):
- `tests/events/test_dynasty_isolation.py`
- `tests/database/test_migration.py`

---

**End of Plan**
