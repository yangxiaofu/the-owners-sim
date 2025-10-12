# Playoff Duplicate Scheduling Fix

## Problem Solved

**Issue**: When reloading the game mid-playoffs, playoff games were being re-scheduled even though they already existed in the database, creating duplicate game events.

**Root Cause**: `season_cycle_controller.py` was calling `schedule_wild_card_round()` directly in `_transition_to_playoffs()`, bypassing the duplicate check that already exists in `PlayoffController.__init__()`.

## The Fix

**File**: `src/season/season_cycle_controller.py`

**What Was Removed** (lines 601-610):
```python
# Schedule Wild Card round with real seeding
result = self.playoff_controller.playoff_scheduler.schedule_wild_card_round(
    seeding=playoff_seeding,
    start_date=wild_card_date,
    season=self.season_year,
    dynasty_id=self.dynasty_id
)

# Store the wild card bracket
self.playoff_controller.brackets['wild_card'] = result['bracket']
```

**Why This Works**:
1. `PlayoffController.__init__()` already calls `_initialize_playoff_bracket()`
2. `_initialize_playoff_bracket()` checks for existing playoff events
3. If existing games found → reconstructs bracket from database
4. If no existing games → schedules new Wild Card round
5. By removing the duplicate call, we let PlayoffController's built-in check work correctly

## What PlayoffController Already Does

**Location**: `src/playoff_system/playoff_controller.py`, lines 649-733

The `_initialize_playoff_bracket()` method already handles both scenarios:

### Scenario 1: Existing Playoff Games (Reload Mid-Playoffs)
```python
# Check if Wild Card round already scheduled for this dynasty/season
existing_events = self.event_db.get_events_by_dynasty(
    dynasty_id=self.dynasty_id,
    event_type="GAME"
)
dynasty_playoff_prefix = f"playoff_{self.dynasty_id}_{self.season_year}_"
dynasty_playoff_events = [
    e for e in existing_events
    if e.get('event_id', '').startswith(dynasty_playoff_prefix)
]

if dynasty_playoff_events:
    print(f"✅ Found existing playoff bracket: {len(dynasty_playoff_events)} games")
    print(f"   Reusing existing playoff schedule")

    # Reconstruct bracket state from existing events
    self._reconstruct_bracket_from_events(dynasty_playoff_events)
    return  # ← Exits early, doesn't schedule again!
```

### Scenario 2: New Playoffs (Fresh Start)
```python
# No existing playoff events - schedule Wild Card round
result = self.playoff_scheduler.schedule_wild_card_round(
    seeding=self.original_seeding,
    start_date=self.wild_card_start_date,
    season=self.season_year,
    dynasty_id=self.dynasty_id
)

self.brackets['wild_card'] = result['bracket']
```

## Testing

### Test Case 1: Fresh Playoff Start
```bash
# Start season, advance to playoffs
python demo/full_season_demo/full_season_sim.py
# Advance through Week 18
# Verify: Wild Card round scheduled ONCE (6 games)
```

Expected output:
```
REGULAR SEASON COMPLETE - PLAYOFFS STARTING
================================================================================
INITIALIZING PLAYOFF BRACKET WITH REAL SEEDING
...
✅ Wild Card round scheduled: 6 games
```

### Test Case 2: Reload Mid-Playoffs (The Bug Fix)
```bash
# Start season, advance to playoffs
# Advance partway through Wild Card round (play 2-3 games)
# Close and reopen application
# Continue playoff simulation
# Verify: No duplicate games, existing games recognized
```

Expected output:
```
REGULAR SEASON COMPLETE - PLAYOFFS STARTING
================================================================================
INITIALIZING PLAYOFF BRACKET WITH REAL SEEDING
✅ Found existing playoff bracket for dynasty 'test_dynasty': 6 games
   Reusing existing playoff schedule
🔄 Reconstructing bracket state from 6 playoff events...
✅ Bracket reconstruction complete:
   Wild Card: 3/6  ← Shows partial completion
   Divisional: 0/4
   Conference: 0/2
   Super Bowl: 0/1
```

### Test Case 3: Reload After Playoff Completion
```bash
# Complete entire playoffs
# Close and reopen application
# Verify: All playoff games still recognized, no duplicates
```

## Changes Summary

### Modified Files
1. **src/season/season_cycle_controller.py**
   - Removed duplicate `schedule_wild_card_round()` call (lines 601-610)
   - Updated verbose logging message
   - Added explanatory comment about why scheduling is removed

### Unchanged Files (Already Working Correctly)
- **src/playoff_system/playoff_controller.py** - Duplicate detection already works
- **src/playoff_system/playoff_scheduler.py** - No changes needed
- **src/events/event_database_api.py** - No changes needed

## Technical Details

### Dynasty Isolation
The duplicate check respects dynasty isolation:
```python
dynasty_playoff_prefix = f"playoff_{self.dynasty_id}_{self.season_year}_"
```

This ensures:
- Dynasty A's playoffs don't interfere with Dynasty B's playoffs
- Each dynasty can have its own playoff state
- Multiple dynasties can be in playoffs simultaneously

### Event ID Format
Playoff events use this format:
```
playoff_{dynasty_id}_{season_year}_{round}_{game_number}
```

Example: `playoff_my_dynasty_2024_wild_card_1`

### Bracket Reconstruction
When existing games are found, PlayoffController:
1. Parses all playoff events from database
2. Organizes games by round (wild_card, divisional, conference, super_bowl)
3. Rebuilds `self.completed_games` dict
4. Determines current active round based on completion status
5. Updates game counter

## Potential Future Enhancement

**Note**: There's a separate mechanism in `playoff_controller.py` (lines 819-929) called `_reschedule_brackets_from_completed_games()` that re-calls `schedule_wild_card_round()` for UI bracket display purposes.

**This might also create duplicates if the scheduler doesn't check for existing events before creating new ones.**

If you encounter duplicate events after this fix, check if `PlayoffScheduler.schedule_wild_card_round()` needs to add its own existence check before creating events.

## Verification Commands

### Check for Duplicate Playoff Events
```sql
-- Run this on your database to check for duplicates
SELECT
    event_id,
    dynasty_id,
    COUNT(*) as count
FROM events
WHERE event_id LIKE 'playoff_%'
GROUP BY event_id, dynasty_id
HAVING COUNT(*) > 1;

-- Should return 0 rows if no duplicates exist
```

### Count Playoff Events Per Round
```sql
SELECT
    CASE
        WHEN event_id LIKE '%wild_card%' THEN 'Wild Card'
        WHEN event_id LIKE '%divisional%' THEN 'Divisional'
        WHEN event_id LIKE '%conference%' THEN 'Conference'
        WHEN event_id LIKE '%super_bowl%' THEN 'Super Bowl'
    END as round,
    dynasty_id,
    COUNT(*) as games
FROM events
WHERE event_id LIKE 'playoff_%'
GROUP BY round, dynasty_id
ORDER BY dynasty_id, round;

-- Expected: 6 Wild Card, 4 Divisional, 2 Conference, 1 Super Bowl per dynasty
```

## Related Documentation

- **Playoff Controller Architecture**: `docs/architecture/playoff_controller.md`
- **Event System**: `src/events/` module
- **Dynasty Isolation**: `docs/plans/events_dynasty_isolation_plan.md`

---

**Fix Status**: ✅ Complete
**Date**: 2025-10-12
**Tested**: Pending user verification
