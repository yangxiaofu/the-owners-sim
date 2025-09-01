# Situational Context Enhancement Plan

## Overview
Implement comprehensive situational context population across all play types to fix missing data (Down: 0, Distance: 0, Field Position: 0, etc.) in PlayResult objects.

## Problem Analysis
All 5 play types (pass, run, punt, kick, kickoff) return minimal PlayResult objects without proper situational context:
- Missing down, distance, field_position from FieldState
- Missing quarter, game_clock timing information  
- Missing derived context flags (big_play, red_zone_play, etc.)

## Implementation Phases

### Phase 1: Foundation Enhancement
**Target**: `src/game_engine/field/field_state.py`
- Add `quarter: int = 1` field
- Add `game_clock: int = 900` field (15 minutes in seconds)
- Add getter methods for timing context

### Phase 2: Base Class Helper
**Target**: `src/game_engine/plays/play_types.py`
- Create `_populate_situational_context()` helper method
- Centralize logic to avoid code duplication across play types
- Handle all context flags and calculations

### Phase 3: Play Type Integration
**Targets**: All play simulation files
- `src/game_engine/plays/pass_play.py`
- `src/game_engine/plays/run_play.py` 
- `src/game_engine/plays/punt_play.py`
- `src/game_engine/plays/kick_play.py`
- `src/game_engine/plays/kickoff_play.py`

**Changes**: Add helper method call before returning PlayResult

### Phase 4: Comprehensive Testing
**Target**: `test_situational_context_all_plays.py`
- Test all 5 play types with various field positions
- Verify timing context population
- Validate situational flags (red_zone, goal_line, etc.)

## Expected Output After Implementation

```
=== PASS PLAY ===
Khalil Mack throws 15-yard pass to Davante Adams, tackled by Roquan Smith

-- SITUATIONAL CONTEXT ---
Down: 2
Distance: 7
Field Position: 32
Quarter: 2
Game Clock: 423
Big Play (20+): No
Explosive Play (40+): No
Red Zone Play: No
Goal Line Play: No

=== KICK PLAY ===
Field goal good

-- SITUATIONAL CONTEXT ---
Down: 4
Distance: 12
Field Position: 67
Quarter: 4
Game Clock: 180
Big Play (20+): No
Explosive Play (40+): No
Red Zone Play: Yes
Goal Line Play: No
```

## Technical Implementation Details

### FieldState Enhancement
```python
@dataclass
class FieldState:
    def __init__(self):
        self.down = 1
        self.yards_to_go = 10
        self.field_position = 25
        self.quarter = 1                    # NEW
        self.game_clock = 900              # NEW (15 min)
        self.possession_team_id: Optional[int] = None
```

### Base PlayType Helper
```python
def _populate_situational_context(self, play_result: PlayResult, field_state: FieldState):
    """Populate comprehensive situational context from field state"""
    play_result.down = field_state.down
    play_result.distance = field_state.yards_to_go
    play_result.field_position = field_state.field_position
    play_result.quarter = field_state.quarter
    play_result.game_clock = field_state.game_clock
    
    # Derived context flags
    play_result.big_play = play_result.yards_gained >= 20
    play_result.explosive_play = play_result.yards_gained >= 40
    play_result.red_zone_play = field_state.field_position >= 80
    play_result.goal_line_play = field_state.field_position >= 90
    play_result.two_minute_drill = field_state.game_clock <= 120
```

## Success Criteria
- ✅ All play types show proper situational context
- ✅ No more zeros in Down/Distance/Field Position
- ✅ Timing information correctly populated
- ✅ Situational flags accurately calculated
- ✅ Single helper method eliminates code duplication
- ✅ Comprehensive test coverage for all scenarios

## Rollback Plan
If issues arise, the changes are minimal and isolated:
1. Revert FieldState class changes
2. Remove helper method from PlayType base class
3. Remove helper calls from individual play types