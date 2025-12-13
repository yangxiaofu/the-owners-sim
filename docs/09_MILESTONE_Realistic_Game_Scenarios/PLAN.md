# Milestone 9: Realistic Game Scenarios

## Goal

Make NFL game simulation feel more realistic and varied through dynamic game management, situational awareness, and performance variance. Games should have flow, momentum, and unpredictability that mirrors real NFL football.

**Status:** ✅ COMPLETE

**Dependencies:**
- Milestone 2: Statistics & Record Keeping ✅ COMPLETE
- Milestone 3: Player Progression & Regression ✅ COMPLETE

---

## Vision Statement

Currently, games simulate correctly but feel static: teams don't manage the clock, prevent defense never triggers, two-minute drill lacks urgency, and every game follows predictable patterns. This milestone makes games **feel alive** through:

- **Clock management** - Timeouts, spike plays, hurry-up offense
- **Situational adaptation** - Teams adjust strategy based on score/time
- **Momentum swings** - Recent plays affect outcomes
- **Clutch performance** - Players perform differently under pressure
- **Environmental impact** - Weather, crowd noise, primetime matter
- **Unpredictability** - Execution variance, hot/cold streaks

---

## Current State Assessment

### What Already Exists (Reusable)

| Component | Location | Status | Reusability |
|-----------|----------|--------|-------------|
| GameContext Tracking | `src/play_engine/play_calling/game_situation_analyzer.py` | Complete | 100% - All context captured |
| GamePhase Enum | `game_situation_analyzer.py:25-32` | Complete | 100% - TWO_MINUTE_WARNING, FINAL_MINUTE defined |
| GameScript Enum | `game_situation_analyzer.py:34-40` | Complete | 100% - CONTROL_GAME, DESPERATION, etc. |
| Fourth Down Matrix | `src/play_engine/play_calling/fourth_down_matrix.py` | Complete | 100% - Data-driven decisions |
| Coaching Personality | `src/play_engine/play_calling/coach_archetype.py` | Complete | 100% - 40+ traits |
| HeadCoach Override | `src/play_engine/play_calling/head_coach.py` | Complete | 90% - Has override thresholds |
| OffensiveCoordinator | `src/play_engine/play_calling/offensive_coordinator.py` | Complete | 80% - Has situation methods |
| DefensiveCoordinator | `src/play_engine/play_calling/defensive_coordinator.py` | Complete | 80% - Has prevent_defense_usage trait |
| Play-by-Play Engine | `src/play_engine/simulation/` | Complete | 100% - Pass/run simulation |
| Box Score Tracking | `src/game_management/box_score_generator.py` | Complete | 100% - Stats persistence |

### What Needs Enhancement

| Gap | Current State | Required State |
|-----|---------------|----------------|
| Clock Management | No timeout tracking | Track timeouts, model play duration, timeout decisions |
| Two-Minute Drill | Aggression trait only | Spike plays, hurry-up tempo, out-of-bounds awareness |
| Game Script Execution | Script identified but not enforced | Play calling frequencies change based on script |
| Prevent Defense | Trait exists (0.0-1.0) | Trigger logic, formation changes, personnel adjustments |
| Momentum Tracking | No system | Track recent plays, apply outcome modifiers |
| Environmental Modifiers | Weather tracked, not applied | Weather/crowd/primetime affect accuracy, pressure |
| Clutch Performance | No differentiation | Players perform differently in high-leverage moments |
| Execution Variance | Static success rates | Hot/cold streaks, poor execution on high-% plays |

---

## Tollgates

### Tollgate 1: Clock Management Foundation ⏹ NOT STARTED

**Goal:** Games track timeouts, play duration, and model realistic clock consumption.

See full implementation details in the complete PLAN.md file.

**Acceptance Criteria:**
- [x] GameState tracks home_timeouts and away_timeouts (0-3)
- [x] Timeouts reset to 3 at halftime (start of Q3)
- [x] Play duration calculated based on play type and tempo
- [x] Clock stops for incomplete passes, out-of-bounds, timeouts
- [x] HeadCoach.should_call_timeout() returns True/False based on situation
- [x] Box scores persist timeout counts

**Tests:** ~20 new tests

---

### Tollgate 2: Two-Minute Drill Execution ⏹ NOT STARTED

**Goal:** Two-minute offense operates with urgency: spike plays, hurry-up tempo, out-of-bounds awareness.

**Acceptance Criteria:**
- [x] Spike plays execute when appropriate (trailing, clock running, <2 min)
- [x] Offensive tempo changes to "two_minute" in final 2 minutes when trailing
- [x] Hurry-up tempo reduces play duration by 40-50%
- [x] Sideline routes prioritized in two-minute drill (2x weight)
- [x] Out-of-bounds probability increases on sideline routes (35%)
- [x] Teams preserve timeouts in two-minute situations

**Tests:** ~18 new tests

---

### Tollgate 3: Game Script Enforcement ⏹ NOT STARTED

**Goal:** Teams adjust play calling frequency based on game script (control_game, desperation, etc.).

**Acceptance Criteria:**
- [x] CONTROL_GAME script results in 70-80% run plays
- [x] DESPERATION script results in 90-95% pass plays
- [x] Formation frequencies change based on script (shotgun 2x in DESPERATION)
- [x] Coach with high game_script_adherence follows script more closely
- [x] Defensive adjustments respond to opponent script (prevent vs desperation)
- [x] Tempo changes based on script (slow for CONTROL_GAME, fast for DESPERATION)

**Tests:** ~22 new tests

---

### Tollgate 4: Prevent Defense Implementation ⏹ NOT STARTED

**Goal:** Defensive formations and play calling adapt when protecting a lead in late-game situations.

**Acceptance Criteria:**
- [x] Prevent defense triggers in 4th quarter, ≤2 min, winning by 1-7 points
- [x] Prevent defense uses 3 rushers, 6 DBs, zone coverage
- [x] Prevent defense increases short pass completion rate by 20-30%
- [x] Prevent defense decreases deep pass completion rate by 40-50%
- [x] Prevent defense decreases sack rate by 50-60%
- [x] DC with low prevent_defense_usage (<0.3) never uses prevent
- [x] HC can override to exit prevent if not working

**Tests:** ~16 new tests

---

### Tollgate 5: Momentum & Flow System ⏹ NOT STARTED

**Goal:** Games have momentum swings where recent plays affect subsequent outcomes.

**Acceptance Criteria:**
- [x] MomentumTracker initializes with neutral momentum (0)
- [x] Touchdown events add +8 momentum for scoring team
- [x] Turnover events add +10 momentum for defensive team
- [x] Momentum decays by 10% per play (recency bias)
- [x] Momentum clamped to -20 to +20 range
- [x] Positive momentum increases completion rate by up to 5%
- [x] Negative momentum increases failure rates by up to 5%
- [x] HC makes more aggressive decisions with positive momentum
- [x] Momentum level displayed in game summary

**Tests:** ~20 new tests

---

### Tollgate 6: Environmental & Situational Modifiers ⏹ NOT STARTED

**Goal:** Weather, crowd noise, primetime, and clutch situations affect play outcomes.

**Acceptance Criteria:**
- [x] Rain reduces pass accuracy by 10%, deep passes by 15%
- [x] Snow reduces pass accuracy by 15%, deep passes by 25%
- [x] Wind reduces deep pass accuracy by 30%, FG accuracy by 20%
- [x] Crowd noise increases away team false starts by 30%
- [x] Dome stadiums amplify crowd noise effects by 20%
- [x] Clutch situations identified in 4th quarter, close games, final 2 minutes
- [x] Players with high composure (90+) get up to +10% in extreme clutch
- [x] Players with low composure (<60) get -15% in extreme clutch
- [x] Primetime games have 15% higher variance in outcomes

**Tests:** ~24 new tests

---

### Tollgate 7: Variance & Unpredictability ⏹ NOT STARTED

**Goal:** Add execution variance so games don't always follow expected scripts - hot/cold streaks, poor execution.

**Acceptance Criteria:**
- [x] PlayerPerformanceTracker tracks hot/cold streaks for all players
- [x] 4-5 consecutive successes triggers "ON_FIRE" state (+15% performance)
- [x] 4-5 consecutive failures triggers "ICE_COLD" state (-15% performance)
- [x] Execution variance adds ±5-12% randomness to success rates
- [x] Complex plays have higher variance (±12%) than simple plays (±5%)
- [x] Random events occur at realistic rates (blocked punt 0.8% per drive)
- [x] Player streaks reset each game (no carryover)
- [x] Variance can cause 90% plays to fail, 10% plays to succeed

**Tests:** ~18 new tests

---

## Dependency Flow

```
Tollgate 1: Clock Management  ──┐
                                ├──► Tollgate 2: Two-Minute Drill
                                │
Tollgate 3: Game Script  ───────┤
                                ├──► Tollgate 5: Momentum & Flow
Tollgate 4: Prevent Defense  ───┤
                                │
                                ├──► Tollgate 6: Environmental Modifiers
                                │
                                └──► Tollgate 7: Variance & Unpredictability
```

**Recommended Order**: 1 → 2 → 3 → 4 → 5 → 6 → 7

**Parallel Opportunities:**
- Tollgates 3 & 4 can be developed in parallel (offensive vs defensive adjustments)
- Tollgates 6 & 7 can be developed in parallel (external vs internal variance)

---

## Success Criteria

**Milestone is COMPLETE when:**

1. **Clock Management Works:**
   - Timeouts tracked (0-3 per half), reset at halftime
   - Play duration varies by type (run vs pass vs incomplete)
   - Teams use timeouts strategically in two-minute drill

2. **Two-Minute Drill Feels Urgent:**
   - Spike plays stop clock (use a down)
   - Hurry-up tempo reduces play duration by 40-50%
   - Sideline routes prioritized, out-of-bounds probability increases

3. **Game Scripts Enforced:**
   - Teams up 21+ run 70-80% of plays (CONTROL_GAME)
   - Teams down 21+ pass 90-95% of plays (DESPERATION)
   - Formation frequencies change based on script

4. **Prevent Defense Activates:**
   - Triggers in 4th quarter, ≤2 min, winning by 1-7 points
   - Short passes easier (+25%), deep passes harder (-40%)
   - Sack rate plummets (-60%)

5. **Momentum Impacts Games:**
   - Touchdowns, turnovers, big plays shift momentum
   - Positive momentum increases success rates by up to 5%
   - Coaches make more aggressive decisions with momentum

6. **Environment Matters:**
   - Rain reduces pass accuracy by 10%
   - Crowd noise increases away false starts by 30%
   - Players with high composure excel in clutch (+10%)

7. **Games Are Unpredictable:**
   - Player hot/cold streaks emerge (4+ consecutive successes = ON_FIRE)
   - Execution variance means 90% plays can fail
   - Rare events occur (blocked punts, muffed returns)

---

## Testing Strategy

### Unit Tests (~138 new tests total)

- **Tollgate 1:** Clock Management (~20 tests)
- **Tollgate 2:** Two-Minute Drill (~18 tests)
- **Tollgate 3:** Game Script Enforcement (~22 tests)
- **Tollgate 4:** Prevent Defense (~16 tests)
- **Tollgate 5:** Momentum & Flow (~20 tests)
- **Tollgate 6:** Environmental Modifiers (~24 tests)
- **Tollgate 7:** Variance & Unpredictability (~18 tests)

### Validation Script

**New File:** `scripts/validate_realistic_scenarios.py`

Validates:
- Two-minute drill completion rate vs normal rate
- Game script enforcement (70-80% run for CONTROL_GAME, 90-95% pass for DESPERATION)
- Prevent defense triggers in eligible situations
- Momentum swings correlate with big plays
- Weather reduces pass accuracy by expected amounts
- Clutch situations identified correctly
- Player hot streaks emerge at realistic rates

---

## Files Involved

### New Files Created

**Game Management:**
- `src/game_management/momentum_tracker.py`
- `src/game_management/player_performance_tracker.py`
- `src/game_management/random_events.py`

**Play Engine Mechanics:**
- `src/play_engine/mechanics/play_duration.py`
- `src/play_engine/mechanics/game_script_modifiers.py`
- `src/play_engine/mechanics/weather_effects.py`
- `src/play_engine/mechanics/crowd_effects.py`
- `src/play_engine/mechanics/clutch_modifiers.py`
- `src/play_engine/mechanics/primetime_effects.py`
- `src/play_engine/simulation/execution_variance.py`

**Tests:** ~138 new test files

### Modified Files

**Core Systems:**
- `src/game_management/game_loop_controller.py` - Timeout tracking, momentum
- `src/play_engine/play_calling/head_coach.py` - Timeout decisions, momentum
- `src/play_engine/play_calling/offensive_coordinator.py` - Spike, tempo, script
- `src/play_engine/play_calling/defensive_coordinator.py` - Prevent, script reaction
- `src/play_engine/simulation/pass_plays.py` - All modifiers
- `src/play_engine/simulation/run_plays.py` - All modifiers
- `src/game_cycle/database/schema.sql` - Timeout columns

---

## Performance Considerations

**Estimated Performance Impact:** <5% slower game simulation

**Computational Impact:**
- Momentum tracking: Minimal (simple arithmetic)
- Clock management: Minimal (integer operations)
- Player performance tracking: Moderate (dictionary lookups)
- Environmental modifiers: Minimal (pre-calculated multipliers)
- Execution variance: Minimal (one random.gauss() call per play)

---

## Notes for Implementation

1. **Start with Clock Management** - Foundation for two-minute drill
2. **Test incrementally** - Each tollgate should have passing tests before moving to next
3. **Use existing traits** - Many coach traits already exist
4. **Preserve backward compatibility** - All modifiers optional (default to 1.0)
5. **Balance realism vs performance** - Simple modifiers are effective
6. **Validate with real NFL data** - Compare to NFL averages