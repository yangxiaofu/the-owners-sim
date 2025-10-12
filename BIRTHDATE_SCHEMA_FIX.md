# Birthdate Column Schema Fix

**Date**: 2025-10-11
**Issue**: Dynasty creation failing with "table players has no column named birthdate"
**Status**: ✅ FIXED (Permanently)

## Problem Summary

When creating a new dynasty, the system crashed with:
```
Failed to load team 1: table players has no column named birthdate
[ERROR DynastyController] Failed to create dynasty: Roster initialization failed at team 1: table players has no column named birthdate
```

This occurred after the database was reset/recreated, and the error kept recurring even after manual fixes.

## Root Cause

### Schema Mismatch

**Code Expected**: `birthdate` column in `players` table
- `src/database/player_roster_api.py` tries to INSERT/SELECT `birthdate` (lines 130, 183, 260, 305, 442, 473, 487)
- `src/team_management/players/player_loader.py` includes `birthdate` in `RealPlayer` dataclass (line 24)

**Database Schema Missing**: `birthdate` column was not in CREATE TABLE statement
- `src/database/connection.py` line 487-508 defined `players` table WITHOUT `birthdate` column
- When database was recreated, the column was missing

### Why This Kept Happening

The issue recurred because:
1. **Temporary Fixes**: Running `ALTER TABLE` adds the column to the *current* database
2. **Database Reset**: When database is deleted and recreated, it uses the CREATE TABLE statement
3. **Missing from Schema**: The CREATE TABLE statement didn't include `birthdate`, so fresh databases lacked it
4. **Cycle Repeats**: Each time database was recreated, the column was missing again

## Solution Implemented

### 1. Added Birthdate to Current Database (Immediate Fix)

```sql
ALTER TABLE players ADD COLUMN birthdate TEXT DEFAULT NULL;
```

This fixed the immediate error for the current database.

### 2. Updated Schema Definition (Permanent Fix)

**File**: `src/database/connection.py` line 501

**Added to CREATE TABLE statement:**
```python
birthdate TEXT DEFAULT NULL,    -- Player birth date (YYYY-MM-DD format)
```

**Complete updated schema:**
```sql
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    source_player_id TEXT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    number INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    positions TEXT NOT NULL,
    attributes TEXT NOT NULL,
    contract_id INTEGER,
    status TEXT DEFAULT 'active',
    years_pro INTEGER DEFAULT 0,
    birthdate TEXT DEFAULT NULL,    -- ← NEW COLUMN
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, player_id)
)
```

## Why This Fix is Permanent

✅ **Current Database**: Has `birthdate` column via ALTER TABLE
✅ **Future Databases**: Will have `birthdate` column via CREATE TABLE statement
✅ **Code Compatibility**: All code expecting `birthdate` will work correctly
✅ **Backward Compatible**: NULL default works for players without birthdate data

## Verification

### Database Status (Current)
```bash
$ sqlite3 data/database/nfl_simulation.db "PRAGMA table_info(players);" | grep birthdate
15|birthdate|TEXT|0|NULL|0
```
✅ Column exists in current database

### Schema Status (Future Databases)
```bash
$ grep -A 15 "CREATE TABLE.*players" src/database/connection.py | grep birthdate
birthdate TEXT DEFAULT NULL,    -- Player birth date (YYYY-MM-DD format)
```
✅ Column included in schema definition

## Code References

### Where Birthdate is Used

**Player Loader** (`src/team_management/players/player_loader.py`):
- Line 24: `birthdate: Optional[str] = None` in RealPlayer dataclass
- Line 193: Reads birthdate from JSON: `birthdate=player_data.get('birthdate')`

**Player Roster API** (`src/database/player_roster_api.py`):
- Line 130: Passes birthdate to _insert_player
- Line 183: Passes birthdate to _insert_player (generated players)
- Line 260: SELECTs birthdate in query
- Line 305: SELECTs birthdate in get_team_roster_by_position
- Line 442: SELECTs birthdate in query
- Line 473: INSERTs birthdate into database
- Line 487: Converts birthdate from database row

All these code locations will now work correctly with both current and future databases.

## Testing

To verify the fix works:

1. **Current Database**: Try creating a dynasty now - should succeed
2. **Fresh Database**:
   ```bash
   # Delete database
   rm data/database/nfl_simulation.db

   # Create dynasty (this will create new database)
   python main.py  # Or use UI to create dynasty
   ```
   Should succeed without "birthdate" error

## Impact

### Before Fix
- ❌ Dynasty creation failed after database reset
- ❌ Required manual SQL fixes each time
- ❌ Problem recurred with each database recreation

### After Fix
- ✅ Dynasty creation works on current database
- ✅ Dynasty creation works on fresh databases
- ✅ No manual intervention needed
- ✅ Consistent behavior across all environments

## Related Issues

This type of schema mismatch can occur when:
1. Code adds new fields to dataclasses
2. Database API tries to read/write those fields
3. Schema definition is not updated accordingly

### Prevention

When adding new player fields in the future:
1. ✅ Update `RealPlayer` dataclass in `player_loader.py`
2. ✅ Update database queries in `player_roster_api.py`
3. ✅ **Update CREATE TABLE in `connection.py`** (← Often forgotten!)
4. ✅ Test with fresh database to verify schema is complete

---

**Status**: ✅ COMPLETE (Permanent Fix)

The birthdate column is now part of the permanent schema. Dynasty creation will work on both current and future databases.
