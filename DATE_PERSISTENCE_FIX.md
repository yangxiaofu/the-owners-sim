# Date Persistence Fix - Summary

## Problem
When loading a saved dynasty, the simulation date was resetting to the default value (September 5) instead of loading the saved date from the database.

## Root Cause Analysis

The issue was caused by an **initialization order problem** in `SimulationController`:

### Original Flow (BROKEN):
1. `__init__()` creates `SimulationDataModel`
2. `_init_season_controller()` runs **FIRST**
   - Queries `dynasty_state` from database
   - Gets saved date (e.g., Oct 8)
   - Creates `SeasonCycleController` with saved date
   - Calendar initializes with saved date
3. `_load_state()` runs **AFTER**
   - Calls `initialize_state()` which queries database AGAIN
   - Sets `self.current_date_str`
   - **BUT** this could be different from calendar date if state doesn't exist

### The Race Condition:
- If `dynasty_state` didn't exist when `_load_state()` ran, it would create a NEW state with Sept 5
- This caused `self.current_date_str` (displayed in UI) to be Sept 5
- While the calendar internal date might be different
- Two separate state initialization paths competed for dynasty_state creation

## Solution

### 1. Fix Initialization Order (`ui/controllers/simulation_controller.py`)
**Changed:**
- `_load_state()` now runs **BEFORE** `_init_season_controller()`
- Ensures `self.current_date_str` is set FIRST from database
- Then `_init_season_controller()` uses `self.current_date_str` to initialize calendar
- **Single source of truth**: `self.current_date_str` is established once, then used everywhere

**Before:**
```python
def __init__(...):
    self.state_model = SimulationDataModel(...)
    self._init_season_controller()  # Queries DB, creates calendar
    self._load_state()              # Queries DB again, sets current_date_str
```

**After:**
```python
def __init__(...):
    self.state_model = SimulationDataModel(...)
    self._load_state()              # Queries DB, sets current_date_str
    self._init_season_controller()  # Uses current_date_str for calendar
```

### 2. Simplify `_init_season_controller()`
**Changed:**
- Removed duplicate database query
- Now uses `self.current_date_str` (already loaded by `_load_state()`)
- Ensures calendar and controller state are synchronized

**Before:**
```python
def _init_season_controller(self):
    state = self.state_model.get_state()  # Query DB again
    if state:
        start_date = Date.from_string(state['current_date'])
    else:
        start_date = Date(self.season, 9, 5)  # Default
```

**After:**
```python
def _init_season_controller(self):
    # Use already-loaded date from _load_state()
    start_date = Date.from_string(self.current_date_str)
```

### 3. Add Debug Logging (`ui/domain_models/simulation_data_model.py`)
**Added:**
- Comprehensive logging in `initialize_state()`
- Shows when state is found vs created
- Helps diagnose future issues

### 4. Add Dynasty State Validation (`ui/controllers/dynasty_controller.py`)
**Added:**
- After creating a new dynasty, verify `dynasty_state` exists
- If missing (schedule generation failed), create fallback state
- Prevents orphaned dynasties without proper state initialization

**New Step 6 in `create_dynasty()`:**
```python
# Verify dynasty_state was created by schedule generation
state = dynasty_state_api.get_current_state(dynasty_id, season)
if not state:
    # Create fallback dynasty_state
    dynasty_state_api.initialize_state(
        dynasty_id=dynasty_id,
        season=season,
        start_date=f"{season}-09-04",
        ...
    )
```

## Files Modified

1. **ui/controllers/simulation_controller.py**
   - Fixed initialization order
   - Added debug logging
   - Simplified `_init_season_controller()`

2. **ui/domain_models/simulation_data_model.py**
   - Added comprehensive debug logging in `initialize_state()`
   - Better error handling and warnings

3. **ui/controllers/dynasty_controller.py**
   - Added dynasty_state validation after creation
   - Ensures fallback state if schedule generation fails

## Testing

The fix ensures:
1. ✅ Dynasty state is loaded from database correctly
2. ✅ Calendar is initialized with correct date
3. ✅ UI displays correct date (no mismatch between calendar and controller)
4. ✅ Date updates persist correctly to database
5. ✅ New dynasties have proper state initialization

## Debug Output

When the application starts, you'll see:
```
[DEBUG SimulationDataModel] initialize_state() called for dynasty 'first', season 2025
[DEBUG SimulationDataModel] Found existing state:
  current_date: 2025-10-08
  current_phase: regular_season
  current_week: 1

[DEBUG SimulationController] After _load_state():
  current_date_str: 2025-10-08
  current_phase: regular_season
  current_week: 1

[DEBUG SimulationController] Creating SeasonCycleController with start_date: 2025-10-08
```

This confirms the date is loaded and used correctly throughout initialization.

## Future Improvements

Consider removing debug logging once the fix is verified stable, or make it toggleable via a configuration flag.
