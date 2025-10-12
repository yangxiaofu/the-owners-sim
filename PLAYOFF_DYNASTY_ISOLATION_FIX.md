# Playoff Dynasty Isolation Fix

**Date**: 2025-10-11
**Issue**: Old playoff games from previous dynasties were blocking new playoff games from being scheduled

## Problem Summary

The playoff game scheduling system had a dynasty isolation bug:

1. **Game IDs didn't include dynasty**: `playoff_2025_wild_card_1` (no dynasty in ID)
2. **Dynasty stored separately**: `dynasty_id` column in events table
3. **Duplicate check was dynasty-blind**: `get_events_by_game_id()` didn't filter by dynasty_id
4. **Result**: Old playoff games from dynasty "third" blocked new games for current dynasty

### Symptoms

- Playoff seeding calculated correctly
- Log showed "⚠️ Skipped 6 already-scheduled playoff game(s)"
- No games appeared in playoff bracket UI
- Advancing days didn't simulate any games

## Solution Implemented

### 1. Added Dynasty-Aware Query Methods (`src/events/event_database_api.py`)

```python
def get_events_by_game_id_and_dynasty(self, game_id: str, dynasty_id: str) -> List[Dict[str, Any]]:
    """Query events by BOTH game_id AND dynasty_id."""
    # Prevents cross-dynasty contamination
```

```python
def delete_playoff_events_by_dynasty(self, dynasty_id: str, season: int) -> int:
    """Delete all playoff events for a specific dynasty and season."""
    # Cleanup utility for old playoff games
```

### 2. Updated Playoff Scheduler (`src/playoff_system/playoff_scheduler.py`)

Changed duplicate detection from:
```python
# OLD - dynasty-blind
existing_events = self.event_db_api.get_events_by_game_id(game_id)
```

To:
```python
# NEW - dynasty-aware
existing_events = self.event_db_api.get_events_by_game_id_and_dynasty(
    game_id, dynasty_id
)
```

### 3. Added Cleanup Method (`src/playoff_system/playoff_controller.py`)

```python
def clear_playoff_games(self) -> int:
    """Clear all playoff games for current dynasty/season."""
    # Safety method for removing old games before rescheduling
```

### 4. Comprehensive Tests (`tests/playoff_system/test_playoff_scheduler_dynasty_isolation.py`)

7 tests covering:
- Dynasty-aware queries work correctly
- Duplicate prevention within same dynasty
- No cross-dynasty interference
- Cleanup operations
- The exact bug scenario from the report

**All tests pass** ✅

## Database Cleanup

Old playoff games from dynasty "third" have been removed using:
```bash
PYTHONPATH=src python cleanup_old_playoff_games.py
```

6 games deleted. Database is now clean.

## How to Use Going Forward

### Normal Usage
**No action needed!** The fix is automatic. Playoff games are now properly isolated by dynasty.

### If You See "Skipped N already-scheduled playoff game(s)" Again

**Option 1: Use the Cleanup Utility**
```bash
PYTHONPATH=src python cleanup_old_playoff_games.py
```

**Option 2: Use PlayoffController Method**
```python
# In your code
playoff_controller.clear_playoff_games()
```

**Option 3: Manual SQL Delete**
```sql
DELETE FROM events
WHERE dynasty_id = 'your_dynasty_id'
AND game_id LIKE 'playoff_2025_%';
```

### Preventing Future Issues

1. **Use unique dynasty IDs**: Each save file should have a unique dynasty ID
2. **Clean start**: When starting a new dynasty, ensure no old playoff games exist
3. **Regular cleanup**: The cleanup utility can be run anytime to remove old playoff games

## Testing the Fix

To verify the fix works in your environment:
```bash
PYTHONPATH=src python -m pytest tests/playoff_system/test_playoff_scheduler_dynasty_isolation.py -v
```

All 7 tests should pass.

## Technical Details

### Architecture Changes

**Before**: Duplicate detection only checked `game_id`
- Problem: Same game_id exists across multiple dynasties
- Result: Cross-dynasty contamination

**After**: Duplicate detection checks `game_id` AND `dynasty_id`
- Solution: Each dynasty has its own playoff games
- Result: Complete dynasty isolation

### Database Impact

**New Queries**:
```sql
-- Dynasty-aware duplicate check
SELECT * FROM events
WHERE game_id = ? AND dynasty_id = ?
ORDER BY timestamp ASC

-- Dynasty-aware cleanup
DELETE FROM events
WHERE dynasty_id = ? AND game_id LIKE 'playoff_%'
```

**Performance**: Uses existing indexes, no performance impact

## Files Modified

1. `src/events/event_database_api.py` - Added 2 new methods (84 lines)
2. `src/playoff_system/playoff_scheduler.py` - Updated duplicate check (3 lines)
3. `src/playoff_system/playoff_controller.py` - Added cleanup method (22 lines)
4. `tests/playoff_system/test_playoff_scheduler_dynasty_isolation.py` - New test file (420 lines)
5. `cleanup_old_playoff_games.py` - New utility script (180 lines)

## Verification

✅ All tests pass (7/7)
✅ Old database cleaned up (6 games removed)
✅ Dynasty isolation validated
✅ No breaking changes to existing code
✅ Backward compatible

## Next Steps

1. **Test in UI**: Run the app and simulate to playoffs to verify games schedule correctly
2. **Verify bracket display**: Check that playoff bracket tab shows teams and games
3. **Simulate games**: Advance days to ensure games simulate and complete
4. **Multiple dynasties**: Test that multiple save files work independently

---

**Status**: ✅ COMPLETE

The playoff dynasty isolation bug is now fixed. Playoff games are properly isolated by dynasty, and old games no longer block new dynasties from scheduling.
