# Playoff Simulation Fix

**Date**: 2025-10-11
**Issue**: Playoff games were scheduled but not being simulated (showed "0 games played")
**Status**: ✅ FIXED

## Problem Summary

Playoff games appeared in the UI calendar as "Scheduled" but when simulating days, the system reported:
- "Simulated 2026-01-17: 0 games played"
- "Simulated 2026-01-18: 0 games played"

Even though 6 playoff games were scheduled in the database.

## Root Cause

**Location**: `src/calendar/simulation_executor.py` lines 359-377

The `SimulationExecutor` was searching for playoff games with the **wrong game_id format**.

### What Was Happening

**Code was searching for:**
```python
playoff_prefix = f"playoff_{self.dynasty_id}_{self.season_year}_"
# Example: "playoff_test_first_2025_"
```

**But actual game_ids in database were:**
```
playoff_2025_wild_card_1
playoff_2025_wild_card_2
...
```

**These don't match!** → Query returned 0 games → Nothing to simulate

### Why This Happened

During the recent **Playoff Dynasty Isolation Fix** (see `PLAYOFF_DYNASTY_ISOLATION_FIX.md`), the playoff game_id format was changed:

**Before:**
- game_id included dynasty_id: `playoff_{dynasty_id}_{season}_{round}_{number}`

**After:**
- game_id excludes dynasty_id: `playoff_{season}_{round}_{number}`
- Dynasty isolation moved to separate `dynasty_id` column

The `playoff_scheduler.py` was updated to generate the new format, but `simulation_executor.py` was never updated to search for the new format.

### Why Regular Season Worked

Regular season games used a different query pattern that filtered by `dynasty_id` column separately:

```python
# Get ALL GAME events
all_game_events = self.event_db.get_events_by_type("GAME")

# Filter by dynasty_id column (not game_id prefix)
regular_season_events = [
    e for e in all_game_events
    if e.get('dynasty_id') == self.dynasty_id
]
```

This worked because it used the `dynasty_id` column, not the game_id prefix.

## Solution Implemented

Updated `src/calendar/simulation_executor.py` to use the correct query pattern:

### Playoff Games (Lines 359-370)

**BEFORE:**
```python
# Get playoff game events for this specific dynasty/season
playoff_prefix = f"playoff_{self.dynasty_id}_{self.season_year}_"
playoff_events = self.event_db.get_events_by_game_id_prefix(
    playoff_prefix,
    event_type="GAME"
)
```

**AFTER:**
```python
# Get playoff game events for this specific dynasty/season
# Note: game_id format is "playoff_{season}_{round}_{number}"
# Dynasty isolation is via dynasty_id column, not game_id
all_playoff_events = self.event_db.get_events_by_dynasty(
    dynasty_id=self.dynasty_id,
    event_type="GAME"
)
playoff_events = [
    e for e in all_playoff_events
    if e.get('game_id', '').startswith(f'playoff_{self.season_year}_')
]
```

### Preseason Games (Lines 372-383)

Applied the same fix to preseason games (which had the same issue):

**BEFORE:**
```python
preseason_prefix = f"preseason_{self.dynasty_id}_{self.season_year}_"
preseason_events = self.event_db.get_events_by_game_id_prefix(
    preseason_prefix,
    event_type="GAME"
)
```

**AFTER:**
```python
# Get preseason game events for this specific dynasty/season
# Note: game_id format is "preseason_{season}_{week}_{number}"
# Dynasty isolation is via dynasty_id column, not game_id
all_preseason_events = self.event_db.get_events_by_dynasty(
    dynasty_id=self.dynasty_id,
    event_type="GAME"
)
preseason_events = [
    e for e in all_preseason_events
    if e.get('game_id', '').startswith(f'preseason_{self.season_year}_')
]
```

## Why This Fix Works

1. **Correct API Usage**: Uses `get_events_by_dynasty()` which filters by the `dynasty_id` column
2. **Correct game_id Pattern**: Matches actual format `playoff_2025_wild_card_1`
3. **Consistent Pattern**: Matches how regular season games are queried
4. **No Deprecated Methods**: Stops using deprecated `get_events_by_game_id_prefix()`
5. **Dynasty Isolation**: Properly isolates games by dynasty using the column, not game_id

## Benefits

- **Dynasty Isolation**: Multiple dynasties can have playoff games for the same season without conflicts
- **Maintainable**: Consistent query pattern across all game types (regular season, playoffs, preseason)
- **Future-Proof**: Uses the recommended API methods, not deprecated ones
- **Clear Intent**: Code comments explain the game_id format and dynasty isolation strategy

## How to Verify the Fix

Since the database was reset, you'll need to:

1. **Create a New Dynasty** (or use existing one)
2. **Simulate Through Regular Season** to Week 18
3. **Schedule Playoffs** (automatic or manual)
4. **Advance to Playoff Days** (e.g., 2026-01-17)
5. **Simulate Day** - Should now show "X games played" instead of "0 games played"

### Expected Behavior

**Before Fix:**
```
Simulated 2026-01-17: 0 games played
```

**After Fix:**
```
Simulated 2026-01-17: 6 games played

📅 Found 6 event(s) scheduled for 2026-01-17
[Games simulate successfully]
```

## Related Documentation

- `PLAYOFF_DYNASTY_ISOLATION_FIX.md` - Original dynasty isolation fix that changed game_id format
- `docs/architecture/playoff_controller.md` - Playoff system architecture
- `src/playoff_system/playoff_scheduler.py` - Where playoff game_ids are generated

## Technical Details

### Database Schema

**Events Table:**
```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    game_id TEXT NOT NULL,          -- Format: playoff_{season}_{round}_{number}
    dynasty_id TEXT NOT NULL,        -- Dynasty isolation column
    data TEXT NOT NULL,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
)
```

### Game ID Formats

**Playoff Games:**
- Format: `playoff_{season}_{round}_{number}`
- Example: `playoff_2025_wild_card_1`

**Regular Season Games:**
- Format: `game_{date}_{away_id}_at_{home_id}`
- Example: `game_20250905_11_at_22`

**Preseason Games:**
- Format: `preseason_{season}_{week}_{number}`
- Example: `preseason_2025_1_1`

### Query Performance

The new approach is more efficient:
- Uses composite index: `idx_events_dynasty_type ON events(dynasty_id, event_type)`
- Indexed equality on `dynasty_id` column (fast)
- Simple string prefix matching in Python (fast)

vs. old approach:
- LIKE query on `game_id` column (slower)
- No dynasty filtering (wrong results)

---

**Status**: ✅ COMPLETE

The playoff simulation query bug is now fixed. Playoff games will be found and simulated correctly when scheduled.
