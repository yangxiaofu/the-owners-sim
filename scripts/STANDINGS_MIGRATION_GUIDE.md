# Standings Migration Guide: season_type Column

## What This Migration Does

Adds `season_type` column to the `standings` table, enabling separate tracking of:
- **Regular season records** (e.g., 14-3)
- **Playoff records** (e.g., 2-1)

This prevents playoff games from incorrectly updating regular season standings.

## Quick Fix for Your Error

You're getting this error when transitioning to playoffs:
```
Error transitioning to playoffs: no such column: season_type
```

**Solution**: Run the migration on your simulation database.

### Option 1: If you know your database path

```bash
python scripts/run_standings_migration.py path/to/your/database.db
```

### Option 2: Migrate all databases (safest)

```bash
python scripts/run_standings_migration.py data/database/*.db
```

### Option 3: Find and migrate your active database

```bash
# Find databases with standings data
find data -name "*.db" -type f -exec sqlite3 {} "SELECT COUNT(*) FROM standings" \; 2>/dev/null

# Then run migration on the one with data
python scripts/run_standings_migration.py path/to/found/database.db
```

## What Was Already Migrated

I just ran the migration on all databases in `data/database/`:

- ✅ **test_contract_init.db**: Successfully migrated (32 standings records)
- ⏭️ **calendar_demo_events.db**: No standings table (empty)
- ⏭️ **debug_events.db**: No standings table (empty)
- ⏭️ **demo_regular_season.db**: No standings table (empty)
- ⏭️ **interactive_demo.db**: No standings table (empty)
- ⏭️ **mock_test.db**: No standings table (empty)

## If Your Database Wasn't Migrated Yet

If you're using a different database file (e.g., created by the UI or a demo script), you need to run the migration on it:

```bash
# Example: If you're using the full season demo
python scripts/run_standings_migration.py path/to/your/database.db
```

## Verification

After running the migration, verify it worked:

```bash
sqlite3 your_database.db "PRAGMA table_info(standings)" | grep season_type
```

Expected output:
```
34|season_type|TEXT|1|'regular_season'|0
```

## Testing the Fix

After migration, try your simulation again:

```bash
# Resume your season simulation (whatever command you were using)
# The playoff transition should now work correctly
```

## What Changed in the Database

### New Column
- **standings.season_type**: `TEXT NOT NULL DEFAULT 'regular_season'`
  - Values: `'regular_season'` or `'playoffs'`
  - All existing records set to `'regular_season'`

### New Indexes
- `idx_standings_unique`: Now includes season_type for proper record separation
- `idx_standings_season_type`: Fast filtering by season_type
- `idx_standings_team_season_type`: Fast team + season_type queries

### New Behavior
- Regular season games update `season_type = 'regular_season'` records
- Playoff games create/update `season_type = 'playoffs'` records
- Each team can have TWO standing records per season (one for each type)

## Example: How Records Are Now Stored

Before migration (WRONG - playoff games update regular season record):
```sql
team_id=22, season=2025, wins=16, losses=4  -- Combined regular+playoff
```

After migration (CORRECT - separate records):
```sql
team_id=22, season=2025, season_type='regular_season', wins=14, losses=3
team_id=22, season=2025, season_type='playoffs', wins=2, losses=1
```

## Querying Separated Records

```sql
-- Get regular season standings only
SELECT * FROM standings
WHERE dynasty_id = 'my_dynasty'
  AND season = 2025
  AND season_type = 'regular_season';

-- Get playoff standings only
SELECT * FROM standings
WHERE dynasty_id = 'my_dynasty'
  AND season = 2025
  AND season_type = 'playoffs';
```

## Code Changes

The following files were updated to support season_type:

1. **src/database/migrations/003_add_season_type_to_standings.sql** (NEW)
   - Migration SQL script

2. **src/stores/standings_store.py** (UPDATED)
   - Auto-detects season_type from GameResult
   - Uses composite keys: `f"{team_id}_{season_type}"`
   - All methods accept optional `season_type` parameter

3. **src/database/api.py** (UPDATED)
   - `get_standings()` accepts `season_type` parameter
   - `get_team_standing()` accepts `season_type` parameter
   - All SQL queries filter by season_type

4. **tests/stores/test_standings_season_type_separation.py** (NEW)
   - Comprehensive test suite validating record separation

## Troubleshooting

### Error: "no such column: season_type"
- **Cause**: Migration hasn't been run on your active database
- **Fix**: Run `python scripts/run_standings_migration.py your_database.db`

### Error: "duplicate column name: season_type"
- **Cause**: Migration already applied
- **Status**: ✅ This is fine! Your database is already up-to-date

### Playoff records still combining with regular season
- **Cause**: Using old database without migration
- **Fix**: Run the migration on your active database

### How do I find my active database?
Look for the database path in your simulation output or check:
- `data/database/nfl_simulation.db` (default)
- Demo-specific paths (e.g., `demo/*/data/*.db`)
- UI-created databases (check your UI settings)

## Rollback (If Needed)

The migration file includes rollback instructions. To revert:

```sql
BEGIN TRANSACTION;
DROP INDEX IF EXISTS idx_standings_unique;
DROP INDEX IF EXISTS idx_standings_season_type;
DROP INDEX IF EXISTS idx_standings_team_season_type;
CREATE UNIQUE INDEX idx_standings_unique ON standings(dynasty_id, team_id, season);
-- Note: SQLite doesn't support DROP COLUMN, so you'd need to recreate the table
COMMIT;
```

## Related Files

- Migration: `src/database/migrations/003_add_season_type_to_standings.sql`
- Runner: `scripts/run_standings_migration.py`
- Tests: `tests/stores/test_standings_season_type_separation.py`
- Schema Docs: `docs/schema/database_schema.md`

## Support

If you continue to have issues:
1. Verify the migration ran successfully (check output for ✅)
2. Check your database has the season_type column (see Verification section)
3. Ensure you're using the correct database file
4. Run the unit tests: `pytest tests/stores/test_standings_season_type_separation.py`

---

**Migration Status**: ✅ Complete (Migration 003)
**Date**: 2025-10-12
