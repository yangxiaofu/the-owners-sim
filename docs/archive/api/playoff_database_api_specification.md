# PlayoffDatabaseAPI Specification

**Version**: 1.0.0
**Created**: November 2025
**Status**: Production Ready

## Overview

PlayoffDatabaseAPI provides modular, transaction-aware operations for managing NFL playoff data across three database tables: `events`, `playoff_brackets`, and `playoff_seedings`.

### Key Features

- **Transaction-Aware Design**: All methods accept optional `connection` parameter for atomic multi-operation commits
- **Dynasty Isolation**: Complete separation of playoff data between different dynasties
- **Dual Mode Support**: Auto-commit mode (standalone) or transaction mode (shared connection)
- **Comprehensive Cleanup**: Single method deletes from 3 tables atomically
- **Existence Checks**: Helper methods to verify bracket/seeding data presence

### Use Cases

1. **Season Transition**: Clear previous season's playoff data before starting new season
2. **Dynasty Initialization**: Clean playoff data when preparing multi-year simulation
3. **Offseason-to-Preseason Transition**: Remove completed playoffs during phase transition
4. **Data Integrity**: Check playoff data existence before operations

---

## Architecture

### Design Pattern
- **Single Responsibility**: Owns ALL playoff database operations
- **Dependency Injection**: Injected into services via constructor
- **Lazy Initialization**: Services use property pattern for on-demand creation
- **Transaction Participant**: Integrates with existing transaction management

### Integration Points

**Consumers:**
- `DynastyInitializationService` (prepare_next_season workflow)
- `OffseasonToPreseasonHandler` (offseason → preseason transition)

**Database Tables:**
- `events` (playoff GameEvents with `game_id` pattern)
- `playoff_brackets` (bracket structure data)
- `playoff_seedings` (AFC/NFC seeding records)

---

## API Reference

### Constructor

```python
PlayoffDatabaseAPI(db_path: str = "data/database/nfl_simulation.db")
```

**Parameters:**
- `db_path` (str): Path to SQLite database file

**Example:**
```python
from database.playoff_database_api import PlayoffDatabaseAPI

api = PlayoffDatabaseAPI("data/database/nfl_simulation.db")
```

---

### clear_playoff_data()

Clear all playoff data for a specific dynasty and season.

```python
clear_playoff_data(
    dynasty_id: str,
    season: int,
    connection: Optional[sqlite3.Connection] = None
) -> Dict[str, int]
```

**Parameters:**
- `dynasty_id` (str): Dynasty identifier
- `season` (int): Season year to clear (e.g., 2024)
- `connection` (Optional[sqlite3.Connection]): Shared connection for transaction mode

**Returns:**
Dict with deletion counts:
```python
{
    'events_deleted': int,        # Playoff GameEvents deleted
    'brackets_deleted': int,      # Bracket records deleted
    'seedings_deleted': int,      # Seeding records deleted
    'total_deleted': int          # Sum of all deletions
}
```

**Behavior:**
- **Auto-commit mode** (`connection=None`): Creates connection, executes deletes, commits, closes
- **Transaction mode** (`connection` provided): Uses shared connection, no commit (caller controls transaction)

**SQL Operations:**
1. DELETE FROM events WHERE dynasty_id = ? AND game_id LIKE 'playoff_{season}_%'
2. DELETE FROM playoff_brackets WHERE dynasty_id = ? AND season = ?
3. DELETE FROM playoff_seedings WHERE dynasty_id = ? AND season = ?

**Examples:**

Auto-commit mode (standalone):
```python
result = api.clear_playoff_data(
    dynasty_id="eagles_dynasty",
    season=2024
)
print(f"Deleted {result['total_deleted']} playoff records")
# Output: Deleted 17 playoff records
```

Transaction mode (shared connection):
```python
conn = db.get_connection()
try:
    # Step 1: Clear playoffs
    result = api.clear_playoff_data(
        dynasty_id="eagles_dynasty",
        season=2024,
        connection=conn
    )

    # Step 2: Other operations...
    # ...

    conn.commit()
except Exception as e:
    conn.rollback()
    raise
finally:
    conn.close()
```

---

### bracket_exists()

Check if playoff bracket exists for a dynasty/season.

```python
bracket_exists(
    dynasty_id: str,
    season: int,
    connection: Optional[sqlite3.Connection] = None
) -> bool
```

**Parameters:**
- `dynasty_id` (str): Dynasty identifier
- `season` (int): Season year
- `connection` (Optional[sqlite3.Connection]): Shared connection (optional)

**Returns:**
- `True` if bracket exists
- `False` if no bracket found

**Example:**
```python
if api.bracket_exists("eagles_dynasty", 2024):
    print("Playoffs already initialized")
else:
    print("No playoff bracket yet")
```

---

### seeding_exists()

Check if playoff seedings exist for a dynasty/season.

```python
seeding_exists(
    dynasty_id: str,
    season: int,
    connection: Optional[sqlite3.Connection] = None
) -> bool
```

**Parameters:**
- `dynasty_id` (str): Dynasty identifier
- `season` (int): Season year
- `connection` (Optional[sqlite3.Connection]): Shared connection (optional)

**Returns:**
- `True` if seedings exist (1 or more records)
- `False` if no seedings found

**Example:**
```python
if api.seeding_exists("eagles_dynasty", 2024):
    print("Playoff seedings determined")
else:
    print("Seedings not yet calculated")
```

---

## Integration Guide

### DynastyInitializationService Integration

```python
class DynastyInitializationService:
    def __init__(
        self,
        db_path: str,
        playoff_database_api: Optional[PlayoffDatabaseAPI] = None,
        # ... other dependencies ...
    ):
        self._playoff_db_api = playoff_database_api

    @property
    def playoff_db_api(self) -> PlayoffDatabaseAPI:
        if self._playoff_db_api is None:
            self._playoff_db_api = PlayoffDatabaseAPI(self.db_path)
        return self._playoff_db_api

    def prepare_next_season(self, dynasty_id, current_season, next_season):
        conn = self.db_connection.get_connection()
        try:
            # Clear playoff data from completed season
            result = self.playoff_db_api.clear_playoff_data(
                dynasty_id=dynasty_id,
                season=current_season,
                connection=conn
            )

            # Other operations...

            conn.commit()
        except:
            conn.rollback()
            raise
```

### OffseasonToPreseasonHandler Integration

```python
class OffseasonToPreseasonHandler:
    def __init__(
        self,
        # ... other params ...
        playoff_database_api: Optional[PlayoffDatabaseAPI] = None,
    ):
        self._playoff_db_api = playoff_database_api

    @property
    def playoff_db_api(self) -> PlayoffDatabaseAPI:
        if self._playoff_db_api is None:
            self._playoff_db_api = PlayoffDatabaseAPI(self._db_path)
        return self._playoff_db_api

    def execute(self, effective_year):
        old_season = effective_year - 1

        # Step 1: Clear playoff data
        playoff_result = self.playoff_db_api.clear_playoff_data(
            dynasty_id=self._dynasty_id,
            season=old_season,
            connection=None  # Auto-commit mode
        )

        # Continue with other transition steps...
```

---

## Database Schema

### events table
```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    game_id TEXT,           -- Pattern: 'playoff_{season}_{round}_{number}'
    event_type TEXT,        -- 'GAME' for playoff games
    game_date TEXT,
    -- ... other columns ...
);
```

**Playoff GameEvent Patterns:**
- `playoff_2024_wild_card_1`
- `playoff_2024_divisional_1`
- `playoff_2024_conference_1`
- `playoff_2024_super_bowl`

### playoff_brackets table
```sql
CREATE TABLE playoff_brackets (
    id INTEGER PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    bracket_data TEXT,      -- JSON bracket structure
    -- ... other columns ...
);
```

### playoff_seedings table
```sql
CREATE TABLE playoff_seedings (
    id INTEGER PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    conference TEXT NOT NULL,  -- 'AFC' or 'NFC'
    seed_number INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    -- ... other columns ...
);
```

**Typical Seeding Record Count:**
- 12 total (6 AFC + 6 NFC seeds per season)

---

## Error Handling

### Database Connection Errors
```python
try:
    result = api.clear_playoff_data("dynasty", 2024)
except Exception as e:
    logger.error(f"Failed to clear playoff data: {e}")
    # Handle error...
```

### Transaction Rollback
```python
conn = db.get_connection()
try:
    api.clear_playoff_data("dynasty", 2024, connection=conn)
    # More operations...
    conn.commit()
except Exception as e:
    conn.rollback()
    logger.error(f"Transaction failed, rolled back: {e}")
    raise
```

---

## Testing

### Test Coverage
- **20 comprehensive tests** in `tests/database/test_playoff_database_api.py`
- 100% pass rate (20/20)
- Covers auto-commit, transaction mode, dynasty isolation, season isolation

### Running Tests
```bash
python -m pytest tests/database/test_playoff_database_api.py -v
```

### Test Categories
- **clear_playoff_data**: 6 tests (auto-commit, transaction, edge cases, isolation)
- **bracket_exists**: 4 tests (true/false, dynasty/season isolation)
- **seeding_exists**: 5 tests (true/false, single record, isolation)
- **Integration**: 5 tests (consistency, rollback, idempotency)

---

## Performance Considerations

### Deletion Performance
- **Typical Counts**: 4 events + 1 bracket + 12 seedings = 17 records
- **Execution Time**: <10ms for typical playoff data
- **Index Usage**: Queries use indexed columns (dynasty_id, season, game_id pattern)

### Transaction Overhead
- **Auto-commit mode**: 1 connection lifecycle (open → execute → commit → close)
- **Transaction mode**: 0 connection overhead (uses shared connection)

---

## Migration Guide

### From Scattered SQL to PlayoffDatabaseAPI

**Before (scattered in 4 locations):**
```python
cursor.execute("DELETE FROM events WHERE dynasty_id = ? AND game_id LIKE ?", ...)
cursor.execute("DELETE FROM playoff_brackets WHERE dynasty_id = ? AND season = ?", ...)
cursor.execute("DELETE FROM playoff_seedings WHERE dynasty_id = ? AND season = ?", ...)
deleted_count = cursor.rowcount  # Only last query count!
```

**After (centralized):**
```python
result = self.playoff_db_api.clear_playoff_data(dynasty_id, season, connection)
total_deleted = result['total_deleted']  # Accurate total across all tables
```

**Benefits:**
- ✅ Single source of truth
- ✅ Accurate deletion counts
- ✅ Transaction-aware design
- ✅ Testable in isolation
- ✅ Reusable across codebase

---

## Changelog

### Version 1.0.0 (November 2025)
- Initial release
- Methods: `clear_playoff_data()`, `bracket_exists()`, `seeding_exists()`
- Transaction-aware design
- Integrated into DynastyInitializationService and OffseasonToPreseasonHandler
- 20 comprehensive tests (100% pass rate)

---

## Related Documentation

- `docs/schema/database_schema.md` - Database schema v2.0.0
- `docs/architecture/transaction_context.md` - Transaction management patterns
- `CLAUDE.md` - Project architecture overview
- `docs/MILESTONE_1/README.md` - Multi-year season cycle roadmap

---

## Support

For issues or questions about PlayoffDatabaseAPI:
1. Check test examples in `tests/database/test_playoff_database_api.py`
2. Review integration examples in DynastyInitializationService
3. Consult this specification document

**Implementation File**: `src/database/playoff_database_api.py` (200 LOC)
**Test File**: `tests/database/test_playoff_database_api.py` (27 KB, 20 tests)
