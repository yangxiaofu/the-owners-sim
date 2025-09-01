# Kickoff Algorithm Implementation Plan

## Overview

This document outlines the implementation of a comprehensive kickoff and return system using the **Hybrid Matchup-Outcome Algorithm**. The implementation follows the architectural patterns established in `pass_play.py` and `run_play.py` while incorporating the 2025 NFL Dynamic Kickoff rules.

## Background Research

### NFL 2025 Dynamic Kickoff Rules Summary

**Key Rule Changes:**
- **Landing Zone**: Area between goal line and 20-yard line where kicks must be returned
- **Player Alignment**: Coverage team lines up at receiving team's 40-yard line, cannot move until ball hits ground/player
- **Return Team Setup**: Max 2 returners in landing zone, 9 players in 30-35 yard setup zone
- **Touchback Rules**:
  - End zone kicks downed = 35-yard line (2025 rule change)
  - Landing zone kicks into end zone = 20-yard line  
  - Short kicks/out of bounds = 40-yard line

**Statistics:**
- 2024 kickoff return rate: 32.8% (up from 21.8% in 2023)
- Average return yards: ~22.5 yards
- Mandatory returns for landing zone kicks

## Algorithm Design: Hybrid Matchup-Outcome System

### Core Concept

Combine the established matchup philosophy from existing play types with NFL's dynamic kickoff rules to create realistic, balanced kickoff simulation.

### Architecture Components

#### 1. KickoffGameBalance Configuration Class

```python
class KickoffGameBalance:
    # === CORE EFFECTIVENESS CALCULATION ===
    KICKER_EFFECTIVENESS_WEIGHT = 0.3      # Kicker leg strength/accuracy
    COVERAGE_EFFECTIVENESS_WEIGHT = 0.4     # Coverage team speed/tackling  
    RETURNER_EFFECTIVENESS_WEIGHT = 0.3     # Returner speed/vision/elusiveness
    
    # === 2025 NFL DYNAMIC KICKOFF RULES ===
    END_ZONE_TOUCHBACK_LINE = 35           # New 2025 rule
    LANDING_ZONE_TOUCHBACK_LINE = 20       # Landing zone -> end zone
    SHORT_KICK_TOUCHBACK_LINE = 40         # Short kicks/out of bounds
    
    # === STATISTICAL BASELINES ===
    BASE_RETURN_RATE = 0.33                # 2024 season average
    AVERAGE_RETURN_YARDS = 22.5            # NFL average under new rules
    TOUCHBACK_RATE = 0.40                  # Estimated touchback rate
    
    # === COVERAGE TIMING ===
    COVERAGE_ARRIVAL_TIME = 4.2            # Seconds for coverage to arrive
    KICK_HANG_TIME_FACTOR = 0.8            # Hang time affects return opportunity
```

#### 2. Kickoff Strategy Matrices

```python
KICKOFF_STRATEGY_MATRICES = {
    "deep_kick": {
        "target_zone": "end_zone",
        "base_touchback_chance": 0.45,
        "base_return_yards": 22.0,
        "kicker_attributes": ["leg_strength", "accuracy"],
        "returner_attributes": ["speed", "vision", "elusiveness"],
        "coverage_effectiveness": 1.0,
        "hang_time": 4.5,
        "variance": 0.8
    },
    "landing_zone_kick": {
        "target_zone": "landing_zone", 
        "base_touchback_chance": 0.10,  # Most go to end zone after landing
        "base_return_yards": 25.0,      # Slightly better field position
        "kicker_attributes": ["accuracy", "technique"],
        "returner_attributes": ["acceleration", "vision"],
        "coverage_effectiveness": 0.9,  # Less time for coverage
        "hang_time": 4.2,
        "variance": 1.0
    },
    "short_kick": {
        "target_zone": "short_zone",    # Beyond landing zone
        "base_touchback_chance": 0.0,   # No touchbacks
        "base_return_yards": 35.0,      # Great field position
        "kicker_attributes": ["accuracy", "technique"],
        "returner_attributes": ["hands", "acceleration"],
        "coverage_effectiveness": 0.7,  # Coverage gets there faster
        "hang_time": 3.8,
        "variance": 1.2
    },
    "squib_kick": {
        "target_zone": "squib_zone",
        "base_touchback_chance": 0.0,
        "base_return_yards": 15.0,      # Poor return yards but predictable
        "kicker_attributes": ["technique", "accuracy"], 
        "returner_attributes": ["hands", "vision"],
        "coverage_effectiveness": 1.3,  # Coverage advantage
        "hang_time": 2.5,               # Low kick, fast coverage
        "variance": 0.6
    },
    "onside_kick": {
        "target_zone": "onside_zone",
        "base_recovery_chance": 0.12,   # NFL onside success rate
        "base_return_yards": 45.0,      # If recovered by return team
        "kicker_attributes": ["technique", "accuracy"],
        "returner_attributes": ["hands", "awareness"],
        "coverage_effectiveness": 0.3,  # Coverage team tries to recover
        "hang_time": 2.0,
        "variance": 1.5
    }
}
```

#### 3. Main Simulation Flow

```python
class KickoffPlay(PlayType):
    def simulate(self, personnel, field_state: FieldState) -> PlayResult:
        # Step 1: Determine kickoff strategy based on game situation
        kick_strategy = self._determine_kick_strategy(field_state, personnel)
        
        # Step 2: Simulate kick placement and landing
        kick_result = self._simulate_kick_placement(personnel.kicker, kick_strategy)
        
        # Step 3: Apply 2025 NFL Dynamic Kickoff Rules
        if kick_result.zone == "end_zone" and kick_result.outcome == "downed":
            return PlayResult("touchback", 0, touchback_line=35)
        elif kick_result.zone == "out_of_bounds" or kick_result.zone == "short_zone":
            return PlayResult("touchback", 0, touchback_line=40)
        elif kick_result.zone == "landing_zone" and kick_result.goes_to_end_zone:
            return PlayResult("touchback", 0, touchback_line=20)
            
        # Step 4: Simulate mandatory return (if in landing zone)
        return_result = self._simulate_return_attempt(
            personnel.returner, personnel.coverage_team, kick_result, kick_strategy
        )
        
        return return_result
```

## Implementation Details

### 1. NFL Rule Compliance

**Landing Zone Logic:**
- Kicks hitting 0-20 yard area MUST be returned (no fair catch)
- Kicks going into end zone after hitting landing zone can be downed for 20-yard touchback
- Direct end zone kicks downed = 35-yard touchback (2025 rule)

**Player Movement Restrictions:**
- Coverage team cannot move until ball hits ground or player in landing zone
- This affects coverage timing calculations in the algorithm

**Special Situations:**
- Onside kicks allowed when trailing (2025 rule expansion)
- Out of bounds kicks = 40-yard touchback penalty
- Weather effects on kick trajectory and hang time

### 2. Effectiveness Calculations

**Coverage vs Return Matchup:**
```python
def _calculate_return_effectiveness(self, coverage_team, returner, kick_strategy):
    # Similar to O-line vs D-line effectiveness in run_play.py
    coverage_rating = self._get_coverage_team_rating(coverage_team)
    returner_rating = self._get_returner_effectiveness(returner, kick_strategy)
    
    coverage_effectiveness = coverage_rating * kick_strategy["coverage_effectiveness"]
    
    # Apply hang time factor - more time = better coverage
    hang_time_factor = kick_strategy["hang_time"] / KickoffGameBalance.COVERAGE_ARRIVAL_TIME
    coverage_effectiveness *= hang_time_factor
    
    # Calculate net return effectiveness
    net_effectiveness = returner_rating / (coverage_effectiveness + 20)  # Avoid division by zero
    
    return net_effectiveness
```

### 3. Situational Decision Making

**Game Context Strategy Selection:**
- **Normal situations**: Deep kick (aim for touchback)
- **Need field position**: Landing zone kick (force return, better coverage)
- **Prevent big return**: Squib kick (sacrifice field position for safety)
- **Trailing late in game**: Onside kick (recovery attempt)

**Score/Time Modifiers:**
- Large leads favor safe kicks (touchbacks)
- Close games favor coverage opportunities
- End of half situations affect risk tolerance

## Integration Points

### 1. PlayFactory Update

```python
# Add to play_factory.py
elif play_type == "kickoff":
    return KickoffPlay()
```

### 2. GameOrchestrator Integration

```python
# Add to game_orchestrator.py after scores
if scoring_play:
    # Kickoff by non-scoring team
    kickoff_result = self._simulate_kickoff(receiving_team, kicking_team)
    field_state.update_field_position(kickoff_result.final_position)
```

### 3. Field State Handling

- Add kickoff-specific field position updates
- Handle possession changes after kickoff
- Track touchback scenarios properly

## Testing & Balance Validation

### 1. NFL Statistical Validation

**Target Metrics:**
- Touchback rate: ~40% (varies by strategy)
- Average return yards: 22-25 yards
- Return rate: ~33% (mandatory returns + voluntary returns)
- Onside recovery rate: ~12%

**Test Scenarios:**
- Various game situations (score, time, field position)
- Different team skill levels (elite vs average special teams)
- Weather effects (when implemented)

### 2. Balance Testing

```python
# Test framework integration
def test_kickoff_balance():
    # Run 1000 kickoffs with average teams
    # Validate against NFL statistics
    assert abs(average_return_yards - 22.5) < 2.0
    assert abs(touchback_rate - 0.40) < 0.05
    assert abs(return_rate - 0.33) < 0.05
```

## Future Enhancements

### 1. Weather System Integration
- Wind effects on kick trajectory
- Rain effects on ball handling
- Temperature effects on ball flight

### 2. Advanced Personnel Modeling
- Individual kicker/returner attributes
- Special teams unit ratings
- Coaching strategy preferences

### 3. Advanced Situations
- Surprise onside kicks
- Coffin corner kicks (rare but strategic)
- Injury considerations during returns

## File Structure

```
src/game_engine/plays/
├── kickoff_play.py          # NEW - Main kickoff implementation
├── play_factory.py          # MODIFY - Add kickoff support
└── play_types.py            # No changes needed

src/game_engine/core/
└── game_orchestrator.py     # MODIFY - Add kickoff calls after scores

docs/plans/
└── kickoff_algorithm_plan.md # NEW - This document
```

## Conclusion

This implementation provides a realistic, balanced kickoff system that:

1. **Follows NFL rules accurately** (2025 Dynamic Kickoff)
2. **Maintains architectural consistency** with existing play types
3. **Provides configurable balance** through the GameBalance pattern
4. **Handles special situations** (onside kicks, weather, game context)
5. **Integrates cleanly** with existing game simulation framework

The hybrid approach balances realism with gameplay by using effectiveness calculations similar to the existing pass/run systems while incorporating the specific zone-based rules of modern NFL kickoffs.