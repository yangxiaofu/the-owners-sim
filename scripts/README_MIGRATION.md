# Phase 1 Database Migration: Season Type Schema

## Overview

This migration adds support for separating regular season and playoff statistics in the database. It is part of the **Full Season Simulation** plan that enables seamless progression from regular season through playoffs to offseason.

## What's Changed

### Schema Changes

#### 1. `games` table
- **Added column**: `season_type TEXT NOT NULL DEFAULT 'regular_season'`
  - Values: `'regular_season'` | `'playoffs'`
  - Purpose: Distinguish between regular season and playoff games

- **Existing column**: `game_type TEXT DEFAULT 'regular'`
  - Values: `'regular'`, `'wildcard'`, `'divisional'`, `'conference'`, `'super_bowl'`
  - Purpose: Detailed game type tracking

#### 2. `player_game_stats` table
- **Added column**: `season_type TEXT NOT NULL DEFAULT 'regular_season'`
  - Values: `'regular_season'` | `'playoffs'`
  - Purpose: Enable filtering stats by season type

#### 3. Performance Indexes
- `idx_games_season_type` - Index on `games(dynasty_id, season, season_type)`
- `idx_games_type` - Index on `games(game_type)`
- `idx_stats_season_type` - Index on `player_game_stats(dynasty_id, season_type)`
- `idx_stats_player_type` - Index on `player_game_stats(player_id, season_type)`

## Migration Files

- **`migrate_season_type.sql`** - SQL migration script
- **`run_migration.py`** - Python migration runner with backup/verification
- **`test_schema_migration.py`** - Test suite for schema validation

## Running the Migration

### For New Databases

New databases automatically include the updated schema. No migration needed.

```bash
# New databases created via DatabaseConnection include season_type columns
python demo/interactive_season_sim/interactive_season_sim.py
```

### For Existing Databases

Use the migration runner to update existing databases:

```bash
# Migrate a specific database
python scripts/run_migration.py <path_to_database>

# Examples:
python scripts/run_migration.py data/database/nfl_simulation.db
python scripts/run_migration.py demo/interactive_season_sim/data/season_2024.db
```

### Migration Process

The migration runner:
1. Creates a backup (`.backup` extension)
2. Checks if migration is needed
3. Applies the migration SQL
4. Verifies the changes
5. Reports results

**Safe to run multiple times** - The migration is idempotent.

## Verification

### Test the Schema

Run the comprehensive test suite:

```bash
python scripts/test_schema_migration.py
```

This tests:
- Schema includes `season_type` columns
- Indexes are created
- Default values work correctly
- Query filtering works

### Manual Verification

Check your database directly:

```sql
-- Check games table structure
PRAGMA table_info(games);

-- Check player_game_stats table structure
PRAGMA table_info(player_game_stats);

-- Verify indexes exist
SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%season_type%';

-- View data distribution
SELECT season_type, COUNT(*) FROM games GROUP BY season_type;
SELECT season_type, COUNT(*) FROM player_game_stats GROUP BY season_type;
```

## Query Examples

### Regular Season Stats Only

```sql
-- Regular season passing leaders
SELECT
    player_name,
    SUM(passing_yards) as total_yards,
    SUM(passing_tds) as total_tds
FROM player_game_stats
WHERE dynasty_id = 'my_dynasty'
  AND season_type = 'regular_season'
  AND season = 2024
GROUP BY player_id
ORDER BY total_yards DESC
LIMIT 10;
```

### Playoff Stats Only

```sql
-- Playoff rushing leaders
SELECT
    player_name,
    SUM(rushing_yards) as playoff_rush_yards,
    SUM(rushing_tds) as playoff_tds
FROM player_game_stats
WHERE dynasty_id = 'my_dynasty'
  AND season_type = 'playoffs'
  AND season = 2024
GROUP BY player_id
ORDER BY playoff_rush_yards DESC
LIMIT 10;
```

### Combined Career Stats

```sql
-- Player career totals (all games)
SELECT
    season_type,
    SUM(passing_yards) as yards,
    SUM(passing_tds) as tds,
    COUNT(DISTINCT game_id) as games
FROM player_game_stats
WHERE dynasty_id = 'my_dynasty'
  AND player_id = 'QB_22_1'
GROUP BY season_type;
```

### Playoff Performance by Round

```sql
-- Playoff performance breakdown
SELECT
    g.game_type,
    SUM(pgs.passing_yards) as yards,
    SUM(pgs.passing_tds) as tds
FROM player_game_stats pgs
JOIN games g ON pgs.game_id = g.game_id
WHERE pgs.dynasty_id = 'my_dynasty'
  AND pgs.player_id = 'QB_22_1'
  AND pgs.season_type = 'playoffs'
GROUP BY g.game_type;
```

## Backward Compatibility

### Default Values

All new columns have sensible defaults:
- `season_type` defaults to `'regular_season'`
- `game_type` defaults to `'regular'`

This ensures:
- Existing code works without modification
- Queries without `season_type` filtering still work
- All existing games are marked as `'regular_season'`

### Existing Queries

Queries that don't filter by `season_type` will return all games (both regular season and playoff), maintaining backward compatibility.

```sql
-- Old query (still works, returns all games)
SELECT * FROM games WHERE dynasty_id = 'my_dynasty';

-- New query (filter by season type)
SELECT * FROM games WHERE dynasty_id = 'my_dynasty' AND season_type = 'regular_season';
```

## Troubleshooting

### Migration Fails

If migration fails:
1. Check the error message
2. Database is automatically restored from backup
3. Backup file: `<database_path>.backup`

### Column Already Exists Error

This is normal if the migration was already applied. The script detects this and reports success.

### Verification Fails

If verification fails after migration:
1. Database is restored from backup
2. Check database file permissions
3. Ensure database is not locked by another process

### Manual Rollback

If you need to manually restore from backup:

```bash
# Replace database with backup
cp <database_path>.backup <database_path>
```

## Testing

### Unit Tests

```bash
# Run all migration tests
python scripts/test_schema_migration.py
```

Expected output:
```
Tests passed: 4/4
✓ ALL TESTS PASSED
```

### Integration Tests

```bash
# Test on a real database
python scripts/run_migration.py demo/interactive_season_sim/data/season_2024.db

# Verify data integrity
sqlite3 demo/interactive_season_sim/data/season_2024.db "SELECT season_type, COUNT(*) FROM games GROUP BY season_type;"
```

## Performance Impact

The migration adds:
- **2 new columns** (minimal storage overhead)
- **4 new indexes** (improve query performance)

Expected performance improvements:
- Queries filtering by `season_type`: **2-10x faster** (indexed)
- Queries filtering by `game_type`: **2-5x faster** (indexed)
- No impact on queries that don't use these columns

## Next Steps

After migration:
1. Existing databases can now track playoff games separately
2. Ready for Phase 2: Core Controller Development
3. `FullSeasonController` can use `season_type` for stat separation

## Support

For issues or questions:
1. Check this README
2. Review `docs/plans/full_season_simulation_plan.md`
3. Run test suite: `python scripts/test_schema_migration.py`
4. Check database schema: `docs/schema/database_schema.md`

## Related Documentation

- [Full Season Simulation Plan](/docs/plans/full_season_simulation_plan.md) - Overall architecture
- [Database Schema Documentation](/docs/schema/database_schema.md) - Complete schema reference
- [Interactive Season Sim Guide](/demo/interactive_season_sim/QUICK_START.md) - User guide

---

**Migration Version**: 1.0
**Date**: October 3, 2025
**Status**: Production Ready
