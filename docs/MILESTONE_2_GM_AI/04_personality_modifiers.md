# Personality Modifiers Specification

**Purpose**: Detailed specifications for all GM trait-based modifiers across trades, free agency, draft, and roster cuts

---

## Overview

The `PersonalityModifiers` class applies GM personality traits to transaction evaluations, converting objective values into subjective GM perceptions.

**Formula Pattern**:
```
Modified Value = Objective Value × Trait Multiplier
```

**Trait Multiplier Calculation**:
```python
# Linear scaling from trait value (0.0-1.0) to multiplier range
multiplier = min_multiplier + (trait_value * (max_multiplier - min_multiplier))
```

**Example**:
```python
# win_now_mentality trait, range 1.0x-1.4x
trait_value = 0.8  # Win-Now GM
multiplier = 1.0 + (0.8 * 0.4) = 1.32x

# Applying to $15M AAV contract
modified_aav = $15M × 1.32 = $19.8M (GM willing to overpay)
```

---

## Existing Trade Modifiers (Reference)

**Location**: `src/transactions/personality_modifiers.py`

These modifiers are **production-ready** and serve as reference patterns for new modifiers.

| Modifier | Trait Used | Multiplier Range | Applies To |
|----------|------------|------------------|------------|
| `apply_risk_tolerance_modifier()` | `risk_tolerance` | 0.8x - 1.2x | Young players (<25) |
| `apply_win_now_modifier()` | `win_now_mentality` | 1.0x - 1.4x | Proven players (85+ OVR) |
| `apply_draft_pick_value_modifier()` | `draft_pick_value` | 0.7x - 1.5x | Draft picks |
| `apply_cap_management_modifier()` | `cap_management` | 0.6x - 1.0x | Expensive contracts (>$10M) |
| `apply_star_chasing_modifier()` | `star_chasing` | 1.0x - 1.5x | Elite players (90+ OVR) |
| `apply_loyalty_modifier()` | `loyalty` | 1.0x - 1.4x | Own players (tenure bonus) |
| `apply_veteran_preference_modifier()` | `veteran_preference` | 0.8x - 1.2x | Veterans (30+ age) |
| `apply_premium_position_modifier()` | `premium_position_focus` | 1.0x - 1.3x | QB/Edge/LT |
| `apply_team_performance_modifier()` | `win_now_mentality` | 0.9x - 1.2x | Context-dependent |
| `apply_deadline_modifier()` | `deadline_activity` | 1.0x - 1.5x | Week 9 trades only |
| `apply_desperation_modifier()` | `desperation_threshold` | 1.0x - 1.3x | Losing teams |

---

## NEW: Free Agency Modifiers

**Method Signature**:
```python
@staticmethod
def apply_free_agency_modifier(
    player: Player,
    market_value: Dict,  # {'aav': X, 'years': Y, 'total': Z, 'guaranteed': W}
    gm: GMArchetype,
    team_context: TeamContext
) -> Dict:
    """Apply GM personality modifiers to free agent contract value."""
```

### Modifier 1: Win-Now Premium (Proven Starters)

**Trait**: `gm.win_now_mentality` (0.0-1.0)

**Applies To**: Proven starters (80+ OVR)

**Multiplier Range**: 1.0x - 1.4x

**Logic**:
```python
if player.overall >= 80:
    # Only apply premium if GM has win-now mentality
    if gm.win_now_mentality > 0.5:
        multiplier = 1.0 + ((gm.win_now_mentality - 0.5) * 0.8)
        # Examples:
        # win_now=0.5 → 1.0x (no premium)
        # win_now=0.7 → 1.16x
        # win_now=0.9 → 1.32x
        # win_now=1.0 → 1.4x
        market_value['aav'] *= multiplier
```

**Rationale**: Win-Now GMs overpay for proven starters who can contribute immediately.

**Example**:
```python
# 85 OVR WR, objective market value: $15M AAV
gm = GMArchetype(win_now_mentality=0.9)
# Modified AAV: $15M × 1.32 = $19.8M
```

### Modifier 2: Cap Management Discipline (Expensive Contracts)

**Trait**: `gm.cap_management` (0.0-1.0)

**Applies To**: Non-elite players (<85 OVR) with contracts

**Multiplier Range**: 0.6x - 1.0x (inverse scale)

**Logic**:
```python
if player.overall < 85:
    # Higher cap_management trait = lower perceived value for expensive contracts
    multiplier = 1.0 - (gm.cap_management * 0.4)
    # Examples:
    # cap_management=0.0 → 1.0x (no discount)
    # cap_management=0.5 → 0.8x
    # cap_management=0.9 → 0.64x
    # cap_management=1.0 → 0.6x
    market_value['aav'] *= multiplier
```

**Rationale**: Cap-conscious GMs discount non-elite players to preserve cap flexibility.

**Example**:
```python
# 82 OVR WR, objective market value: $15M AAV
gm = GMArchetype(cap_management=0.9)
# Modified AAV: $15M × 0.64 = $9.6M (only signs if bargain)
```

### Modifier 3: Veteran Preference (Age Factor)

**Trait**: `gm.veteran_preference` (0.0-1.0)

**Applies To**: Veterans (30+ age)

**Multiplier Range**: 0.8x - 1.2x (bidirectional)

**Logic**:
```python
if player.age >= 30:
    if gm.veteran_preference > 0.5:
        # Veteran-preferring GM: boost value
        multiplier = 1.0 + ((gm.veteran_preference - 0.5) * 0.4)
        # Examples: 0.5→1.0x, 0.7→1.08x, 1.0→1.2x
    else:
        # Youth-focused GM: discount value
        multiplier = 1.0 - ((0.5 - gm.veteran_preference) * 0.4)
        # Examples: 0.5→1.0x, 0.3→0.92x, 0.0→0.8x

    market_value['aav'] *= multiplier
```

**Rationale**: Veteran-preferring GMs value experience, youth-focused GMs prefer developmental players.

**Example**:
```python
# 32-year-old 88 OVR LB, objective market value: $12M AAV

# Veteran-preferring GM (veteran_preference=0.9)
# Modified AAV: $12M × 1.16 = $13.92M

# Youth-focused GM (veteran_preference=0.2)
# Modified AAV: $12M × 0.88 = $10.56M
```

### Modifier 4: Star Chasing Premium (Elite Free Agents)

**Trait**: `gm.star_chasing` (0.0-1.0)

**Applies To**: Elite free agents (90+ OVR)

**Multiplier Range**: 1.0x - 1.5x

**Logic**:
```python
if player.overall >= 90:
    multiplier = 1.0 + (gm.star_chasing * 0.5)
    # Examples:
    # star_chasing=0.0 → 1.0x (no premium)
    # star_chasing=0.5 → 1.25x
    # star_chasing=1.0 → 1.5x
    market_value['aav'] *= multiplier
```

**Rationale**: Star-chasing GMs overpay for marquee names, regardless of team needs.

**Example**:
```python
# 92 OVR DE, objective market value: $22M AAV
gm = GMArchetype(star_chasing=1.0)
# Modified AAV: $22M × 1.5 = $33M (willing to break the bank)
```

### Modifier 5: Risk Tolerance (Injury-Prone Players)

**Trait**: `gm.risk_tolerance` (0.0-1.0)

**Applies To**: Injury-prone players

**Multiplier Range**: 0.7x - 1.0x (inverse scale for risk-averse)

**Logic**:
```python
if player.injury_prone:  # Assuming injury_prone attribute exists
    if gm.risk_tolerance < 0.5:
        # Risk-averse GM: discount injury-prone players
        multiplier = 1.0 - ((0.5 - gm.risk_tolerance) * 0.6)
        # Examples:
        # risk_tolerance=0.5 → 1.0x (neutral)
        # risk_tolerance=0.3 → 0.88x
        # risk_tolerance=0.0 → 0.7x
        market_value['aav'] *= multiplier
    # Else: No modifier (risk-tolerant GMs don't discount)
```

**Rationale**: Risk-averse GMs avoid injury-prone players, risk-tolerant GMs don't care.

**Example**:
```python
# 86 OVR RB (injury-prone), objective market value: $14M AAV

# Risk-averse GM (risk_tolerance=0.2)
# Modified AAV: $14M × 0.82 = $11.48M

# Risk-tolerant GM (risk_tolerance=0.8)
# Modified AAV: $14M × 1.0 = $14M (no discount)
```

### Combined Example (All Modifiers)

```python
# Player: 31-year-old 84 OVR WR (injury-prone), Market Value: $13M AAV
# GM: win_now_mentality=0.8, cap_management=0.3, veteran_preference=0.7,
#     star_chasing=0.4, risk_tolerance=0.3

modified_value = 13_000_000

# Modifier 1: Win-Now Premium (84 OVR ≥ 80)
modified_value *= 1.24  # $16.12M

# Modifier 2: Cap Management (84 < 85, not elite)
modified_value *= 0.88  # $14.19M

# Modifier 3: Veteran Preference (31 years ≥ 30)
modified_value *= 1.08  # $15.32M

# Modifier 4: Star Chasing (84 < 90, not elite)
# Not applied

# Modifier 5: Risk Tolerance (injury-prone)
modified_value *= 0.88  # $13.48M

# Final perceived value: $13.48M (vs objective $13M)
# GM willing to pay slightly more due to win-now + veteran preference,
# offset by cap management + risk aversion
```

---

## NEW: Draft Modifiers

**Method Signature**:
```python
@staticmethod
def apply_draft_modifier(
    prospect: Player,
    draft_position: int,  # Pick number (1-262)
    gm: GMArchetype,
    team_context: TeamContext
) -> float:
    """Apply GM personality modifiers to draft prospect value.

    Returns:
        Modified prospect value (0.0-100.0 scale, based on overall rating)
    """
```

### Modifier 1: Risk Tolerance (High-Ceiling vs High-Floor)

**Trait**: `gm.risk_tolerance` (0.0-1.0)

**Applies To**: High-ceiling prospects (potential - overall > 10)

**Multiplier Range**: 0.9x - 1.2x (bidirectional)

**Logic**:
```python
ceiling = prospect.potential
floor = prospect.overall
upside = ceiling - floor

if upside > 10:  # High-ceiling prospect
    if gm.risk_tolerance > 0.5:
        # Risk-tolerant: boost high-ceiling prospects
        multiplier = 1.0 + ((gm.risk_tolerance - 0.5) * 0.4)
        # Examples: 0.5→1.0x, 0.7→1.08x, 1.0→1.2x
    else:
        # Risk-averse: discount high-ceiling prospects
        multiplier = 1.0 - ((0.5 - gm.risk_tolerance) * 0.2)
        # Examples: 0.5→1.0x, 0.3→0.96x, 0.0→0.9x

    base_value *= multiplier
```

**Rationale**: Risk-tolerant GMs draft for upside, risk-averse GMs draft for floor.

**Example**:
```python
# Prospect A: 70 OVR, 90 POT (upside=20, high ceiling)
# Prospect B: 78 OVR, 82 POT (upside=4, high floor)

# Risk-tolerant GM (risk_tolerance=0.9):
# Prospect A: 70 × 1.16 = 81.2 (prefers upside)
# Prospect B: 78 × 1.0 = 78.0 (no modifier)
# Picks: Prospect A

# Risk-averse GM (risk_tolerance=0.1):
# Prospect A: 70 × 0.92 = 64.4 (avoids risk)
# Prospect B: 78 × 1.0 = 78.0 (no modifier)
# Picks: Prospect B
```

### Modifier 2: Win-Now Mentality (Polished vs Raw)

**Trait**: `gm.win_now_mentality` (0.0-1.0)

**Applies To**: Older prospects (23+ age, polished/pro-ready)

**Multiplier Range**: 1.0x - 1.3x

**Logic**:
```python
if prospect.age >= 23:  # Older, pro-ready prospect
    multiplier = 1.0 + (gm.win_now_mentality * 0.3)
    # Examples:
    # win_now=0.0 → 1.0x (no premium)
    # win_now=0.5 → 1.15x
    # win_now=1.0 → 1.3x
    base_value *= multiplier
```

**Rationale**: Win-Now GMs value immediate contributors over developmental projects.

**Example**:
```python
# Prospect C: 24-year-old 76 OVR LB (polished, pro-ready)
# Prospect D: 20-year-old 70 OVR LB (raw, developmental)

# Win-Now GM (win_now_mentality=0.9):
# Prospect C: 76 × 1.27 = 96.5
# Prospect D: 70 × 1.0 = 70.0
# Picks: Prospect C

# Rebuilder GM (win_now_mentality=0.2):
# Prospect C: 76 × 1.06 = 80.6
# Prospect D: 70 × 1.0 = 70.0 (but might prefer if upside modifier applies)
# Picks: Prospect C (but margin is smaller)
```

### Modifier 3: Premium Position Focus

**Trait**: `gm.premium_position_focus` (0.0-1.0)

**Applies To**: Premium positions (QB, Edge, LT)

**Multiplier Range**: 1.0x - 1.3x

**Logic**:
```python
if prospect.position in ['QB', 'EDGE', 'LT']:
    multiplier = 1.0 + (gm.premium_position_focus * 0.3)
    # Examples:
    # premium_position_focus=0.0 → 1.0x
    # premium_position_focus=0.5 → 1.15x
    # premium_position_focus=1.0 → 1.3x
    base_value *= multiplier
```

**Rationale**: GMs with high premium position focus prioritize QB/Edge/LT over all else.

**Example**:
```python
# Prospect E: 80 OVR QB
# Prospect F: 82 OVR RB

# Premium Position Focus GM (premium_position_focus=1.0):
# Prospect E: 80 × 1.3 = 104.0
# Prospect F: 82 × 1.0 = 82.0
# Picks: Prospect E (QB)

# Balanced GM (premium_position_focus=0.5):
# Prospect E: 80 × 1.15 = 92.0
# Prospect F: 82 × 1.0 = 82.0
# Picks: Prospect E (QB, but closer)
```

### Modifier 4: Veteran Preference (Older Prospects)

**Trait**: `gm.veteran_preference` (0.0-1.0)

**Applies To**: Older prospects (24+ age)

**Multiplier Range**: 1.0x - 1.2x

**Logic**:
```python
if prospect.age >= 24:  # Older prospect
    multiplier = 1.0 + (gm.veteran_preference * 0.2)
    # Examples:
    # veteran_preference=0.0 → 1.0x
    # veteran_preference=0.5 → 1.1x
    # veteran_preference=1.0 → 1.2x
    base_value *= multiplier
```

**Rationale**: Veteran-preferring GMs value older, experienced prospects.

**Example**:
```python
# Prospect G: 25-year-old 74 OVR TE
# Prospect H: 21-year-old 74 OVR TE

# Veteran Preference GM (veteran_preference=0.9):
# Prospect G: 74 × 1.18 = 87.3
# Prospect H: 74 × 1.0 = 74.0
# Picks: Prospect G

# Youth-Focused GM (veteran_preference=0.2):
# Prospect G: 74 × 1.04 = 77.0
# Prospect H: 74 × 1.0 = 74.0
# Picks: Prospect G (but margin is smaller)
```

### Modifier 5: Draft Pick Value (BPA vs Need)

**Trait**: `gm.draft_pick_value` (0.0-1.0)

**Applies To**: Best Player Available (BPA) logic

**Multiplier Range**: N/A (affects selection logic, not value multiplier)

**Logic**:
```python
# This modifier affects SELECTION LOGIC, not value perception
# High draft_pick_value = BPA (best available player)
# Low draft_pick_value = Need-based drafting

if gm.draft_pick_value > 0.7:
    # BPA approach: Value prospects by pure talent, ignore needs
    # No need modifier applied
    pass
else:
    # Need-based approach: Boost value if prospect fills critical need
    if prospect.position == team_needs[0].position:
        # Critical need boost
        base_value *= 1.5
    elif prospect.position in [need.position for need in team_needs[:3]]:
        # Top-3 need boost
        base_value *= 1.2
```

**Rationale**: GMs with high draft_pick_value always draft BPA, low draft_pick_value draft for needs.

**Example**:
```python
# Team needs: [QB=CRITICAL, WR=HIGH, RB=MEDIUM]
# Prospect I: 85 OVR WR
# Prospect J: 88 OVR CB

# BPA GM (draft_pick_value=0.9):
# Prospect I: 85 × 1.0 = 85.0 (no need boost)
# Prospect J: 88 × 1.0 = 88.0 (no need boost)
# Picks: Prospect J (highest talent)

# Need-Based GM (draft_pick_value=0.3):
# Prospect I: 85 × 1.2 = 102.0 (top-3 need boost)
# Prospect J: 88 × 1.0 = 88.0 (not a need)
# Picks: Prospect I (fills need)
```

### Modifier 6: Situational Awareness (Team Context)

**Trait**: `gm.situational_awareness` (0.0-1.0)

**Applies To**: All prospects (modulates all other modifiers)

**Multiplier Range**: N/A (meta-modifier)

**Logic**:
```python
# Future use - currently not implemented
# Would modulate strength of other modifiers based on team context
# Example: Contender with 11-5 record increases win_now modifier strength
```

**Status**: Reserved for future implementation.

---

## NEW: Roster Cut Modifiers

**Method Signature**:
```python
@staticmethod
def apply_roster_cut_modifier(
    player: Player,
    objective_value: float,  # 0-100 score from value calculation
    gm: GMArchetype,
    team_context: TeamContext
) -> float:
    """Apply GM personality modifiers to roster cut decision.

    Returns:
        Modified player value (higher = more likely to keep)
    """
```

### Modifier 1: Loyalty (Tenure Bonus)

**Trait**: `gm.loyalty` (0.0-1.0)

**Applies To**: Long-tenured players (5+ years with team)

**Multiplier Range**: 1.0x - 1.4x

**Logic**:
```python
years_with_team = player.years_with_team

if years_with_team >= 5:
    multiplier = 1.0 + (gm.loyalty * 0.4)
    # Examples:
    # loyalty=0.0 → 1.0x (no bonus)
    # loyalty=0.5 → 1.2x
    # loyalty=1.0 → 1.4x
    modified_value *= multiplier
```

**Rationale**: Loyal GMs keep long-tenured players, even if objective value is lower.

**Example**:
```python
# Player A: 8-year veteran, objective value = 60
# Player B: 2-year player, objective value = 65

# Loyal GM (loyalty=0.9):
# Player A: 60 × 1.36 = 81.6
# Player B: 65 × 1.0 = 65.0
# Keeps: Player A (loyalty wins)

# Ruthless GM (loyalty=0.1):
# Player A: 60 × 1.04 = 62.4
# Player B: 65 × 1.0 = 65.0
# Keeps: Player B (higher value)
```

### Modifier 2: Cap Management (Expensive Player Discount)

**Trait**: `gm.cap_management` (0.0-1.0)

**Applies To**: Expensive players (>$5M cap hit)

**Multiplier Range**: 0.8x - 1.0x (inverse scale)

**Logic**:
```python
if player.cap_hit > 5_000_000:
    if gm.cap_management > 0.7:  # Cap-conscious GM
        multiplier = 0.8  # Discount expensive players
        modified_value *= multiplier
    # Else: No modifier (cap-flexible GMs don't discount)
```

**Rationale**: Cap-conscious GMs cut expensive backups to create cap space.

**Example**:
```python
# Player C: $8M cap hit, objective value = 70
# Player D: $2M cap hit, objective value = 68

# Cap-Conscious GM (cap_management=0.9):
# Player C: 70 × 0.8 = 56.0 (expensive discount)
# Player D: 68 × 1.0 = 68.0
# Keeps: Player D (saves $6M)

# Cap-Flexible GM (cap_management=0.3):
# Player C: 70 × 1.0 = 70.0 (no discount)
# Player D: 68 × 1.0 = 68.0
# Keeps: Player C (higher value)
```

### Modifier 3: Veteran Preference (Age Factor)

**Trait**: `gm.veteran_preference` (0.0-1.0)

**Applies To**: Veterans (30+ age)

**Multiplier Range**: 0.8x - 1.2x (bidirectional)

**Logic**:
```python
if player.age >= 30:
    if gm.veteran_preference > 0.5:
        # Veteran-preferring: boost value
        multiplier = 1.0 + ((gm.veteran_preference - 0.5) * 0.4)
    else:
        # Youth-focused: discount value
        multiplier = 1.0 - ((0.5 - gm.veteran_preference) * 0.4)

    modified_value *= multiplier
```

**Rationale**: Veteran-preferring GMs keep older players, youth-focused GMs give opportunities to young players.

**Example**:
```python
# Player E: 32-year-old, objective value = 72
# Player F: 24-year-old, objective value = 70

# Veteran Preference GM (veteran_preference=0.9):
# Player E: 72 × 1.16 = 83.5
# Player F: 70 × 1.0 = 70.0
# Keeps: Player E

# Youth-Focused GM (veteran_preference=0.2):
# Player E: 72 × 0.88 = 63.4
# Player F: 70 × 1.0 = 70.0
# Keeps: Player F (youth opportunity)
```

### Combined Example (All Modifiers)

```python
# Player: 31-year-old, 7-year veteran, $7M cap hit, objective value = 68

# GM: loyalty=0.8, cap_management=0.9, veteran_preference=0.6

modified_value = 68

# Modifier 1: Loyalty (7 years ≥ 5)
modified_value *= 1.32  # 89.76

# Modifier 2: Cap Management ($7M > $5M, cap_management=0.9)
modified_value *= 0.8   # 71.81

# Modifier 3: Veteran Preference (31 ≥ 30, veteran_preference=0.6)
modified_value *= 1.04  # 74.68

# Final value: 74.68 (vs objective 68)
# Loyalty + veteran preference offset cap management discount
# GM keeps player despite expensive contract
```

---

## Multiplier Range Summary

### Free Agency Modifiers

| Modifier | Trait | Applies To | Min | Max | Direction |
|----------|-------|------------|-----|-----|-----------|
| Win-Now Premium | `win_now_mentality` | 80+ OVR players | 1.0x | 1.4x | Up |
| Cap Management | `cap_management` | <85 OVR players | 0.6x | 1.0x | Down |
| Veteran Preference | `veteran_preference` | 30+ age | 0.8x | 1.2x | Bidirectional |
| Star Chasing | `star_chasing` | 90+ OVR players | 1.0x | 1.5x | Up |
| Risk Tolerance | `risk_tolerance` | Injury-prone | 0.7x | 1.0x | Down (for risk-averse) |

### Draft Modifiers

| Modifier | Trait | Applies To | Min | Max | Direction |
|----------|-------|------------|-----|-----|-----------|
| Risk Tolerance | `risk_tolerance` | High-ceiling prospects | 0.9x | 1.2x | Bidirectional |
| Win-Now Mentality | `win_now_mentality` | 23+ age prospects | 1.0x | 1.3x | Up |
| Premium Position Focus | `premium_position_focus` | QB/Edge/LT | 1.0x | 1.3x | Up |
| Veteran Preference | `veteran_preference` | 24+ age prospects | 1.0x | 1.2x | Up |
| Draft Pick Value | `draft_pick_value` | Need-based boost | 1.0x | 1.5x | Up (for needs) |

### Roster Cut Modifiers

| Modifier | Trait | Applies To | Min | Max | Direction |
|----------|-------|------------|-----|-----|-----------|
| Loyalty | `loyalty` | 5+ year tenure | 1.0x | 1.4x | Up |
| Cap Management | `cap_management` | >$5M cap hit | 0.8x | 1.0x | Down (for cap-conscious) |
| Veteran Preference | `veteran_preference` | 30+ age | 0.8x | 1.2x | Bidirectional |

---

## Design Principles

### 1. Conservative Multiplier Ranges

**Start conservative** (1.0x-1.3x), widen if behaviors too similar.

**Rationale**: Easier to increase ranges than reduce after unrealistic behaviors observed.

### 2. Bidirectional Modifiers

**Some traits boost OR discount** based on threshold (typically 0.5).

**Example**: `veteran_preference > 0.5` boosts veterans, `veteran_preference < 0.5` discounts them.

**Rationale**: Captures both ends of spectrum (veteran-focused vs youth-focused).

### 3. Inverse Modifiers

**Some traits apply inverse scaling** (higher trait = lower multiplier).

**Example**: `cap_management=1.0` → 0.6x multiplier (maximum discount for expensive players).

**Rationale**: Models risk aversion and conservative decision-making.

### 4. Threshold-Based Application

**Most modifiers only apply if condition met** (age, OVR, tenure thresholds).

**Example**: Star chasing modifier only applies if `player.overall >= 90`.

**Rationale**: Prevents modifier spam, focuses on relevant scenarios.

### 5. Additive vs Multiplicative

**All modifiers are MULTIPLICATIVE** (not additive).

**Rationale**: Compounding effects feel more realistic (e.g., 20% boost + 10% boost = 32% total, not 30%).

---

## Validation Criteria

### Free Agency

- Win-Now GMs should pay ≥15% more AAV than Rebuilders
- Cap-Conscious GMs should sign ≥20% fewer expensive contracts (>$15M AAV)
- Star Chasers should sign ≥30% more elite free agents (90+ OVR)

### Draft

- Risk-Tolerant GMs should draft ≥30% more high-ceiling prospects (upside >10)
- Win-Now GMs should draft older prospects (avg age ≥22.5 vs Rebuilders ≤21.5)
- Premium Position Focus GMs should draft ≥40% more QB/Edge/LT

### Roster Cuts

- Loyal GMs should keep ≥20% more long-tenured players (5+ years)
- Cap-Conscious GMs should cut ≥15% more expensive players (>$5M cap hit)
- Youth-Focused GMs should cut ≥10% more 30+ year old players

---

## Tuning Process

1. **Implement modifiers with initial ranges** (conservative)
2. **Run 32-team validation** (measure variance by GM archetype)
3. **If variance < 15%**: Widen multiplier ranges (increase max, decrease min)
4. **If unrealistic behaviors**: Narrow multiplier ranges, add caps
5. **Iterate until 20-30% variance** achieved

---

## Next Steps

See **05_testing_strategy.md** for comprehensive validation approach.
