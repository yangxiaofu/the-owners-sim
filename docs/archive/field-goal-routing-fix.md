# Field Goal Routing Logic Fix Plan

## Problem Statement

Field goal attempts from the goal line (field_pos = 100) are incorrectly being classified as extra points, causing a routing error in the score calculator that results in:

```
TypeError: ScoreTransition.__init__() got an unexpected keyword argument 'requires_extra_point'
```

## Root Cause Analysis

### Error Chain
1. **Field Goal from Goal Line**: Team attempts field goal from field_pos=100 (goal line)
2. **Wrong Classification**: `kick_play.py:183` incorrectly returns "extra_point" for field_pos >= 98
3. **Wrong Outcome**: PlayResult gets `outcome="extra_point"` instead of `outcome="field_goal"`
4. **Wrong Routing**: Score calculator routes to `_calculate_extra_point_score()` instead of `_calculate_field_goal_score()`
5. **Parameter Mismatch**: Extra point method uses invalid ScoreTransition parameters

### Faulty Logic
```python
# kick_play.py:182-184
if field_state.field_position >= 98 or distance <= 20:
    return "extra_point"  # ← WRONG for field goals from goal line!
```

## Solution Strategy: Option A (KISS + YAGNI)

**Add game context parameter to distinguish field goals from extra points.**

### Why Option A?
- **KISS**: Simplest solution - just pass context 
- **YAGNI**: Minimal code changes, addresses exact problem
- **Reliable**: No complex logic needed, explicit context
- **Maintainable**: Clear intent, easy to understand

### Implementation Approach

#### Phase 1: Fix Score Calculator Parameters (Immediate)
Fix the parameter mismatch in `_calculate_extra_point_score()` to prevent the TypeError:

```python
# Remove invalid parameters, use proper ScoreTransition fields
return ScoreTransition(
    score_occurred=True,
    score_type=ScoreType.EXTRA_POINT,  # Use enum, not string
    points_scored=points,
    scoring_team=self._convert_team_id_for_validator(scoring_team_id, game_state),
    new_home_score=points if self._is_home_team(scoring_team_id, game_state) and points > 0 else 0,
    new_away_score=points if not self._is_home_team(scoring_team_id, game_state) and points > 0 else 0
    # Remove: requires_extra_point, home_team_points, play_description, field_position
)
```

#### Phase 2: Add Context-Aware Kick Play
Modify kick play to accept context parameter:

```python
def simulate(self, personnel, field_state: FieldState, play_context: str = "field_goal") -> PlayResult:
    # Use play_context to override situation detection
    outcome, yards_gained = self._calculate_kick_outcome_from_matrix(
        offense_ratings, defense_ratings, personnel, field_state, play_context
    )
```

#### Phase 3: Update Play Factory
Ensure play factory passes correct context:
- Regular field goal attempts: `play_context="field_goal"`
- Post-touchdown conversions: `play_context="extra_point"`

## Test Plan

### Reproduction Test
```python
def test_field_goal_from_goal_line():
    """Reproduce the original error"""
    field_state = FieldState(field_position=100, down=2)
    kick_play = KickPlay()
    
    # This should NOT cause TypeError
    result = kick_play.simulate(personnel, field_state, "field_goal")
    assert result.outcome == "field_goal"  # Not "extra_point"
```

### Validation Tests
```python
def test_extra_point_after_touchdown():
    """Ensure extra points still work"""
    field_state = FieldState(field_position=98, down=1)
    result = kick_play.simulate(personnel, field_state, "extra_point") 
    assert result.outcome == "extra_point"

def test_field_goal_scoring_transition():
    """Ensure complete scoring flow works"""
    # Test that field goal creates valid ScoreTransition
    # No TypeError should occur
```

## Implementation Files

### Files to Modify
1. **`src/game_engine/plays/kick_play.py`**
   - Add `play_context` parameter to `simulate()`
   - Update `_determine_kick_situation()` to respect context
   - Modify `_calculate_kick_outcome_from_matrix()` signature

2. **`src/game_engine/state_transitions/calculators/score_calculator.py`**
   - Fix `_calculate_extra_point_score()` parameters
   - Fix `_calculate_safety_score()` parameters
   - Fix `_calculate_generic_score()` parameters

3. **`src/game_engine/plays/play_factory.py`** (if exists)
   - Pass correct context when creating kick plays

### Files to Test
- All scoring transitions work correctly
- Field goals from any position route correctly
- Extra points after touchdowns still work

## Success Criteria

✅ **Immediate Fix**: No more TypeError on field goal attempts from goal line
✅ **Correct Routing**: Field goals route to field goal scoring logic regardless of position
✅ **Preserved Functionality**: Extra points after touchdowns continue to work
✅ **Clean Parameters**: All ScoreTransition objects created with valid parameters only

## Timeline

- **Phase 1**: 30 minutes (parameter fix)
- **Phase 2**: 1 hour (context implementation)  
- **Phase 3**: 30 minutes (play factory updates)
- **Testing**: 1 hour (comprehensive validation)

**Total Estimated Time**: 3 hours

## Risk Assessment

**Low Risk**: 
- Minimal code changes
- Explicit context parameter makes intent clear
- Existing extra point logic preserved
- Easy to rollback if needed

**Mitigation**:
- Comprehensive test coverage before deployment
- Parameter validation in kick play
- Fallback to current logic if context not provided