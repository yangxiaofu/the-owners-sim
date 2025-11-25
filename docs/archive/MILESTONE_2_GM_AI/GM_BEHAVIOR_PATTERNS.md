# GM Behavior Patterns Documentation

**Version**: 1.0.0
**Last Updated**: 2025-11-22
**Status**: Phase 3 Complete (All 3 offseason systems integrated)

---

## Table of Contents

1. [Overview](#overview)
2. [GM Personality Traits](#gm-personality-traits)
3. [Cross-Context Behavior Patterns](#cross-context-behavior-patterns)
4. [System-Specific Modifiers](#system-specific-modifiers)
5. [Validation Results](#validation-results)
6. [Testing](#testing)

---

## Overview

The GM AI system uses **13 personality traits** to create realistic, consistent decision-making patterns across all offseason contexts:

1. **Free Agency** (Phase 2 Complete)
2. **Draft** (Phase 2 Complete)
3. **Roster Cuts** (Phase 3 Complete)

Each GM archetype exhibits **coherent behavior** across all systems, ensuring realistic franchise management.

---

## GM Personality Traits

### Core Traits

| Trait | Range | Description | Primary Impact |
|-------|-------|-------------|----------------|
| `win_now_mentality` | 0.0-1.0 | Urgency to win immediately | FA spending, draft polish preference |
| `risk_tolerance` | 0.0-1.0 | Willingness to gamble on upside | Draft ceiling preference |
| `loyalty` | 0.0-1.0 | Value of team continuity | Roster cut tenure bonus |
| `cap_management` | 0.0-1.0 | Financial discipline | FA spending limits, roster cut expensive player cuts |
| `veteran_preference` | 0.0-1.0 | Preference for experience | FA age preference, draft age preference, roster cuts age preference |
| `star_chasing` | 0.0-1.0 | Desire for elite talent | FA elite player premiums |
| `draft_pick_value` | 0.0-1.0 | Value of draft picks vs trades | Draft BPA vs needs |
| `trade_frequency` | 0.0-1.0 | Willingness to make trades | *(Future integration)* |
| `desperation_threshold` | 0.0-1.0 | Threshold for panic moves | *(Future integration)* |
| `patience_years` | 1-7 | Years willing to rebuild | Long-term strategy |
| `deadline_activity` | 0.0-1.0 | Trade deadline aggressiveness | *(Future integration)* |
| `premium_position_focus` | 0.0-1.0 | Focus on QB/Edge/LT | Draft premium position preference |

---

## Cross-Context Behavior Patterns

### Win-Now GM Archetype

**Personality Traits**:
- `win_now_mentality`: 0.9 (HIGH)
- `veteran_preference`: 0.9 (HIGH)
- `risk_tolerance`: 0.2 (LOW)
- `cap_management`: 0.3 (LOW)

**Behavioral Signature**:

| System | Behavior |
|--------|----------|
| **Free Agency** | Pays premium for proven veterans (28-32 age) |
| **Draft** | Prefers polished, high-floor prospects (age 23-24) |
| **Roster Cuts** | Keeps older veterans over younger players |

**Validation**: ✅ Win-Now GMs consistently prefer experience across all contexts

---

### Rebuilder GM Archetype

**Personality Traits**:
- `win_now_mentality`: 0.1 (LOW)
- `veteran_preference`: 0.1 (LOW)
- `risk_tolerance`: 0.8 (HIGH)
- `cap_management`: 0.7 (HIGH)

**Behavioral Signature**:

| System | Behavior |
|--------|----------|
| **Free Agency** | Avoids expensive veterans, signs cheap young FAs |
| **Draft** | Tolerates high-ceiling raw prospects (age 20-21) |
| **Roster Cuts** | Keeps young players over veterans |

**Validation**: ✅ Rebuilder GMs consistently prioritize youth/upside

---

### Loyal GM Archetype

**Personality Traits**:
- `loyalty`: 0.95 (VERY HIGH)
- `win_now_mentality`: 0.6 (MODERATE)
- `cap_management`: 0.6 (MODERATE)

**Behavioral Signature**:

| System | Behavior |
|--------|----------|
| **Free Agency** | Prefers re-signing own FAs over external signings |
| **Draft** | Prefer team culture fits (need-based drafting) |
| **Roster Cuts** | Keeps long-tenured players (5+ years) despite lower talent |

**Validation**: ✅ Loyal GMs value continuity, keep long-tenured players 40%+ more

---

### Ruthless GM Archetype

**Personality Traits**:
- `loyalty`: 0.1 (VERY LOW)
- `cap_management`: 0.9 (VERY HIGH)
- `win_now_mentality`: 0.7 (HIGH)

**Behavioral Signature**:

| System | Behavior |
|--------|----------|
| **Free Agency** | Avoids overpaying, values cap efficiency |
| **Draft** | Value-based, not need-based (BPA approach) |
| **Roster Cuts** | Cuts expensive players ruthlessly (>$5M cap hit) |

**Validation**: ✅ Ruthless GMs cut expensive players 35%+ more

---

### Risk-Tolerant GM Archetype

**Personality Traits**:
- `risk_tolerance`: 0.95 (VERY HIGH)
- `win_now_mentality`: 0.5 (MODERATE)
- `star_chasing`: 0.7 (HIGH)

**Behavioral Signature**:

| System | Behavior |
|--------|----------|
| **Free Agency** | Pays premium for elite talent (90+ OVR) |
| **Draft** | Drafts high-ceiling boom/bust prospects (ceiling - overall > 10) |
| **Roster Cuts** | Tolerates higher cap hits for upside players |

**Validation**: ✅ Risk-Tolerant GMs draft 400% more high-ceiling prospects

---

### Conservative GM Archetype

**Personality Traits**:
- `risk_tolerance`: 0.1 (VERY LOW)
- `cap_management`: 0.8 (HIGH)
- `veteran_preference`: 0.7 (HIGH)

**Behavioral Signature**:

| System | Behavior |
|--------|----------|
| **Free Agency** | Pays 34% less than Win-Now GMs |
| **Draft** | Drafts safe, high-floor prospects (ceiling - overall ≤ 5) |
| **Roster Cuts** | Prioritizes cap efficiency, cuts risky players |

**Validation**: ✅ Conservative GMs draft 100% more high-floor prospects

---

## System-Specific Modifiers

### Free Agency Modifiers

| Modifier | Trait | Formula | Range |
|----------|-------|---------|-------|
| **Win-Now Premium** | `win_now_mentality` | Base AAV × (1.0 + trait × 0.25) | 1.0x - 1.25x |
| **Star Chaser Premium** | `star_chasing` | Elite players (90+ OVR) × (1.0 + trait × 0.20) | 1.0x - 1.20x |
| **Cap Management Discount** | `cap_management` | Base AAV × (1.0 - trait × 0.15) | 0.85x - 1.0x |

**Validation**: 52.4% AAV variance between Win-Now and Rebuilder GMs ✅

---

### Draft Modifiers

| Modifier | Trait | Formula | Range |
|----------|-------|---------|-------|
| **Risk Tolerance (Ceiling)** | `risk_tolerance` | Upside × (0.6 + trait × 0.8) | 0.6x - 1.4x |
| **Risk Tolerance (Floor)** | `risk_tolerance` | Floor penalty × (trait - 0.5) | -20 to +20 |
| **Win-Now Age Penalty** | `win_now_mentality` | Age <23: penalty × trait | 0 to -10 |
| **Veteran Pref Age Bonus** | `veteran_preference` | Age >22: bonus × trait | 0 to +5 |

**Validation**: 400% ceiling variance between Risk-Tolerant and Conservative GMs ✅

---

### Roster Cuts Modifiers

| Modifier | Trait | Formula | Range |
|----------|-------|---------|-------|
| **Loyalty (Tenure)** | `loyalty` | 5+ years tenure × (1.0 + trait × 0.4) | 1.0x - 1.4x |
| **Cap Management (Expensive)** | `cap_management` | >$5M cap hit × 0.8 | 0.8x discount |
| **Veteran Pref (Age)** | `veteran_preference` | Age 30+ × (1.0 ± (trait - 0.5) × 0.4) | 0.8x - 1.2x |

**Validation**: 44% tenure variance between Loyal and Ruthless GMs ✅

---

## Validation Results

### Individual System Validations

| System | Test Script | Criteria | Status |
|--------|-------------|----------|--------|
| **Free Agency** | `validate_fa_gm_behavior.py` | ≥20% AAV variance | ✅ PASS (52.4%) |
| **Draft** | `validate_draft_gm_behavior.py` | ≥30% ceiling variance | ✅ PASS (400%) |
| **Roster Cuts** | `validate_roster_cuts_gm_behavior.py` | ≥20% tenure variance | ✅ PASS (44%) |

### Cross-Context Consistency

| Test | Description | Status |
|------|-------------|--------|
| **Win-Now Polished Preference** | Win-Now GMs prefer polished prospects (Draft + Cuts) | ✅ PASS |
| **Rebuilder Youth Tolerance** | Rebuilder GMs tolerate high-ceiling prospects | ✅ PASS |
| **GM Modifier Variance** | Different GMs value same prospect differently | ✅ PASS (0.7% variance) |

### Comprehensive Validation Suite

**Command**: `python scripts/run_all_gm_validations.py`

**Results**: 3/3 validations passed (100%)
**Runtime**: 1.77 seconds

---

## Testing

### Unit Tests

**Location**: `tests/transactions/test_personality_modifiers.py`

- **Free Agency**: 15 unit tests
- **Draft**: 25 unit tests
- **Roster Cuts**: 10 unit tests

**Total**: 50 unit tests ✅

### Integration Tests

**Location**: `tests/offseason/`

- `test_free_agency_gm_integration.py`: 10 tests
- `test_draft_gm_integration.py`: 5 tests
- `test_roster_cuts_gm_integration.py`: 5 tests
- `test_gm_draft_consistency.py`: 3 tests

**Total**: 23 integration tests ✅

### Validation Scripts

- `scripts/validate_fa_gm_behavior.py`
- `scripts/validate_draft_gm_behavior.py`
- `scripts/validate_roster_cuts_gm_behavior.py`
- `scripts/run_all_gm_validations.py` (aggregator)

**Total**: 4 validation scripts ✅

---

## Key Insights

### 1. Trait Stacking is Multiplicative

All GM modifiers use **multiplicative stacking**, not additive. This ensures bounded variance and prevents unrealistic extremes.

**Example**:
```python
# Loyalty modifier (1.0x - 1.4x)
modified_value = objective_value × (1.0 + loyalty × 0.4)

# Cap management discount (0.8x)
if cap_hit > $5M and cap_management > 0.7:
    modified_value × 0.8
```

### 2. User Team Uses Objective Evaluation

**Player Agency**: User teams NEVER use GM personality modifiers. This preserves player control.

```python
if gm is not None and team_context is not None:
    # AI team: Use GM modifiers
    value = PersonalityModifiers.apply_draft_modifier(...)
else:
    # User team: Objective evaluation
    value = objective_value + need_bonuses
```

### 3. Backward Compatibility Maintained

All modifier methods accept optional `gm` and `team_context` parameters:
- If provided → Phase 2B (GM modifiers)
- If None → Phase 2A (objective evaluation)

This allows gradual rollout without breaking existing systems.

---

## Future Development

### Phase 4: Trade System Integration

**Planned Modifiers**:
- `trade_frequency`: Affects willingness to make trades
- `draft_pick_value`: Adjusts trade value of draft picks
- `desperation_threshold`: Triggers panic trades near deadline

### Phase 5: Deadline Activity

**Planned Modifiers**:
- `deadline_activity`: Adjusts trade aggressiveness at deadline
- `win_now_mentality`: Amplifies deadline urgency for contenders
- `patience_years`: Affects long-term vs short-term trades

---

## Appendix

### Complete GM Archetype Examples

#### Kansas City Chiefs (Win-Now)

```python
GMArchetype(
    name="Kansas City Chiefs",
    risk_tolerance=0.4,
    win_now_mentality=0.9,      # Mahomes window
    draft_pick_value=0.4,
    cap_management=0.3,          # Aggressive spending
    trade_frequency=0.7,
    veteran_preference=0.8,       # Proven talent
    star_chasing=0.7,
    loyalty=0.6,
    desperation_threshold=0.7,
    patience_years=2,
    deadline_activity=0.8,
    premium_position_focus=0.6
)
```

#### Arizona Cardinals (Rebuilder)

```python
GMArchetype(
    name="Arizona Cardinals",
    risk_tolerance=0.8,           # Swing for upside
    win_now_mentality=0.2,
    draft_pick_value=0.9,         # Accumulate picks
    cap_management=0.8,           # Preserve cap space
    trade_frequency=0.5,
    veteran_preference=0.2,       # Youth focus
    star_chasing=0.3,
    loyalty=0.5,
    desperation_threshold=0.3,
    patience_years=5,
    deadline_activity=0.2,
    premium_position_focus=0.5
)
```

---

**End of Documentation**
