# Fix Down Progression After Scoring Plays

## Problem Description

**Error**: `NFL.DOWN.005 - Down progression incorrect - expected 2 | Field: new_down | Current: 1 | Expected: 2`

**Root Cause**: After any scoring play (touchdown, field goal, safety), the game state is not properly reset. The field position stays at the scoring location (e.g., 100-yard line for touchdown) instead of resetting to the kickoff return position (~25-yard line), causing incorrect down progression validation.

## Technical Analysis

### Current Broken Flow:
1. **Touchdown Play**: Awards touchdown, field_position = 100 ✅
2. **Next Play**: Still at field_position = 100, down = 1 ❌
3. **After 1-yard gain**: Expects down = 2, but calculator returns down = 1 ❌
4. **Validator**: Correctly rejects with NFL.DOWN.005 error ❌

### Expected Correct Flow:
1. **Touchdown Play**: Awards touchdown, field_position = 100 ✅  
2. **Kickoff Reset**: Field resets to ~25-yard line, down = 1, yards_to_go = 10 ✅
3. **Next Play**: Normal progression from 25-yard line ✅
4. **After 1-yard gain**: down = 2, field_position = 26 ✅

## Root Cause Analysis

### Issue 1: Application Order Problem
In `transition_applicator.py`, the sequence is:
```python
# 1. Apply basic field changes (keeps field_position = 100)
field_changes = self._apply_basic_field_changes(context)

# 2. Apply scoring changes  
# 3. Handle special situations (tries to reset field_position = 25)
special_changes = self._apply_special_situation_changes(context)
```

**Problem**: Basic field changes override the kickoff position reset.

### Issue 2: Kickoff Detection Failure
The kickoff detection only looks at the current play (`play_result.is_score`) but fails to detect when the **next** play needs kickoff field reset.

## Solution Implementation

### Phase 1: Modify Transition Applicator
**File**: `src/game_engine/state_transitions/applicators/transition_applicator.py`

**Changes**:
1. Add `_needs_post_score_kickoff_reset()` method to detect post-scoring scenarios
2. Reorder application sequence to handle kickoffs BEFORE basic field changes  
3. Skip basic field updates when kickoff reset is required

### Phase 2: Enhance Special Situations Calculator  
**File**: `src/game_engine/state_transitions/calculators/special_situations_calculator.py`

**Changes**:
1. Add `_needs_post_score_kickoff_reset()` method to detect game state requiring kickoff
2. Check for field_position >= 90 + down = 1 combination (indicates post-scoring state)
3. Add `_calculate_kickoff_reset()` method for state-based kickoff calculation

### Phase 3: Add Game State Coordination
**File**: `src/game_engine/core/game_state_manager.py`

**Changes**:
1. Add `_post_score_kickoff_pending` flag tracking
2. Add `_kickoff_receiving_team` tracking  
3. Modify `process_play_result()` to set flags after scoring plays

## Scoring Types Covered

### Touchdowns (Most Common)
- **Sequence**: TD (6 pts) + Extra Point (1 pt) → Kickoff → Reset to ~25-yard line
- **Extra Point**: Handled automatically within touchdown play, no separate state transition

### Field Goals
- **Sequence**: FG (3 pts) → Kickoff → Reset to ~25-yard line  
- **Simpler**: No conversion attempt, direct to kickoff

### Safeties
- **Sequence**: Safety (2 pts) → Safety Kick → Reset to ~20-yard line
- **Special**: Uses safety kick instead of normal kickoff

## Implementation Order

1. ✅ **Analysis Complete**: Root cause identified
2. 🔄 **Phase 1**: Modify transition applicator application sequence
3. ⏳ **Phase 2**: Add post-score detection in special situations calculator
4. ⏳ **Phase 3**: Add state coordination in game state manager
5. ⏳ **Testing**: Verify fix resolves NFL.DOWN.005 errors

## Expected Outcome

After implementation:
- **Any Score** → **Kickoff** → **Field Reset** → **Normal Down Progression**
- Resolves NFL.DOWN.005 validation errors for all scoring scenarios
- Maintains proper game flow: 1st → 2nd → 3rd → 4th down progression

## Files Modified

1. `src/game_engine/state_transitions/applicators/transition_applicator.py`
2. `src/game_engine/state_transitions/calculators/special_situations_calculator.py`  
3. `src/game_engine/core/game_state_manager.py`

## Testing Strategy

1. **Touchdown Scenario**: Verify field reset from 100 to ~25 after TD + extra point
2. **Field Goal Scenario**: Verify field reset after successful field goal
3. **Safety Scenario**: Verify proper safety kick handling
4. **Down Progression**: Confirm 1st → 2nd → 3rd progression works after all scoring types