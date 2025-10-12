# Playoff Duplication Test Demo

## Overview

This demo tests that playoff initialization doesn't create duplicate games when the PlayoffController is initialized multiple times (e.g., after app restart or reload mid-playoffs).

## The Bug

**Problem**: When you reload the app mid-playoffs, playoff games were being re-scheduled even though they already existed in the database, creating duplicate game events.

**Root Cause**: The `PlayoffController._initialize_playoff_bracket()` method was checking for existing games using **event_id** (a UUID) instead of **game_id** (the structured playoff identifier).

```python
# BEFORE (WRONG):
dynasty_playoff_prefix = f"playoff_{self.dynasty_id}_{self.season_year}_"
dynasty_playoff_events = [
    e for e in existing_events
    if e.get('event_id', '').startswith(dynasty_playoff_prefix)  # ← Checks UUID!
]

# AFTER (CORRECT):
playoff_game_prefix = f"playoff_{self.season_year}_"
dynasty_playoff_events = [
    e for e in existing_events
    if e.get('game_id', '').startswith(playoff_game_prefix)  # ← Checks game_id!
]
```

## Files in This Demo

1. **`playoff_duplication_test.py`** - Main test script that demonstrates the fix
2. **`mock_standings_generator.py`** - Generates fake regular season standings
3. **`verify_duplicates.py`** - SQL queries to check for duplicate games
4. **`README.md`** - This file

## Running the Test

### Quick Test
```bash
PYTHONPATH=src python demo/playoff_tester_demo/playoff_duplication_test.py
```

### Expected Output (After Fix)
```
================================================================================
🧪 PLAYOFF DUPLICATION TEST
================================================================================

[1/7] Creating test database...
     ✅ Database created

[2/7] Generating mock standings...
     ✅ Generated 32 team standings

[3/7] Calculating playoff seeding...
     ✅ Seeding calculated (AFC: 7 seeds, NFC: 7 seeds)

[4/7] Initializing PlayoffController #1...
     ✅ PlayoffController #1 initialized
     📊 Playoff games in database: 6

[5/7] Destroying PlayoffController #1...
     ✅ Controller destroyed

[6/7] Initializing PlayoffController #2 (simulating reload)...
     ✅ PlayoffController #2 initialized
     📊 Playoff games in database: 6

[7/7] Checking for duplicates...
     📊 Playoff games in database: 6

================================================================================
TEST RESULTS
================================================================================

Playoff games after 1st init: 6
Playoff games after 2nd init: 6
Duplicates found: 0

Games by round:
  wild_card   : 6
  divisional  : 0
  conference  : 0
  super_bowl  : 0

================================================================================
✅ TEST PASSED: No duplicates detected!
   Playoff initialization is idempotent.
================================================================================
```

## What the Test Does

1. **Creates a test database** with a mock dynasty
2. **Generates fake standings** for all 32 NFL teams
3. **Calculates playoff seeding** using the mock standings
4. **Initializes PlayoffController #1** → Schedules 6 Wild Card games
5. **Destroys the controller** (simulates app close)
6. **Initializes PlayoffController #2** → Should find existing 6 games
7. **Verifies no duplicates** were created

## Testing Against Real Database

You can also test against your actual game database:

```bash
# First, backup your database!
cp your_database.db your_database.db.backup

# Run the test with custom database
python demo/playoff_tester_demo/playoff_duplication_test.py --database your_database.db --dynasty your_dynasty_id
```

Or use the verification script directly:

```bash
PYTHONPATH=src python demo/playoff_tester_demo/verify_duplicates.py your_database.db your_dynasty_id 2024
```

## Understanding the Fix

### Before the Fix

1. User starts season simulation
2. Advances to playoffs → PlayoffController schedules 6 games
3. User closes app mid-playoffs
4. User reopens app → PlayoffController initializes
5. Check for existing games FAILS (wrong ID check)
6. Schedules 6 MORE games → **12 total (duplicates!)**

### After the Fix

1. User starts season simulation
2. Advances to playoffs → PlayoffController schedules 6 games
3. User closes app mid-playoffs
4. User reopens app → PlayoffController initializes
5. Check for existing games SUCCEEDS (correct game_id check)
6. Reuses existing 6 games → **6 total (correct!)**

## Key Concepts

### event_id vs game_id

- **event_id**: Unique identifier for the event itself (UUID4)
  - Example: `"3e4b8c2a-1234-5678-9abc-def123456789"`
  - Generated automatically for every event
  - Not useful for finding duplicate games

- **game_id**: Structured identifier for the game
  - Example: `"playoff_2024_wild_card_1"`
  - Format: `playoff_{season}_{round}_{game_number}`
  - Used to identify and prevent duplicate scheduling

### Dynasty Isolation

The fix maintains dynasty isolation by:
1. Querying events using `get_events_by_dynasty(dynasty_id)` first
2. Then filtering by `game_id` prefix within that dynasty's events
3. This prevents one dynasty's playoffs from affecting another

## Troubleshooting

### Test fails with "6 expected, got 12"

This means the duplicate check isn't working. Verify:
1. The fix was applied to `playoff_controller.py`
2. The check uses `game_id` not `event_id`
3. The pattern matches the actual game_id format

### Test fails with import errors

Make sure you run with `PYTHONPATH=src`:
```bash
PYTHONPATH=src python demo/playoff_tester_demo/playoff_duplication_test.py
```

### Test passes but real app still has duplicates

Check if:
1. You're using the updated `playoff_controller.py`
2. Your database was created before the fix (may have existing duplicates)
3. There are other code paths that schedule playoffs

## Related Files

- **`src/playoff_system/playoff_controller.py`** - Contains the fix (line 672-678)
- **`src/playoff_system/playoff_scheduler.py`** - Has backup duplicate prevention
- **`src/events/event_database_api.py`** - Database query methods
- **`PLAYOFF_DUPLICATE_FIX.md`** - Detailed fix documentation (root directory)

## Success Criteria

The test passes if:
- ✅ PlayoffController #1 schedules 6 games
- ✅ PlayoffController #2 finds existing 6 games (doesn't schedule new ones)
- ✅ Total games in database = 6 (not 12)
- ✅ No duplicate game_ids detected
- ✅ Games correctly identified by round (6 wild_card, 0 others)

---

**Status**: ✅ Fix Applied and Tested
**Date**: 2025-10-12
**Bug**: Duplicate playoff games on reload
**Fix**: Check game_id instead of event_id for existing games
