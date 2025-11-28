# Milestone 3: Player Progression & Regression

## Goal

Implement realistic player development throughout their careers: young players improve, prime players stabilize, veterans decline. Progression considers position-specific peak ages, individual potential, and performance-based adjustments.

---

## Current State Assessment

### What Already Exists (Reusable)

| Component | Location | Status | Reusability |
|-----------|----------|--------|-------------|
| Age-Weighted Development | `src/game_cycle/services/training_camp_service.py` | Complete | 100% - Core algorithm ready |
| Position Attributes Map | `training_camp_service.py:88-115` | Complete | 100% - All 25 positions |
| DevelopmentProfile Model | `src/player_generation/models/generated_player.py:68-99` | Defined | 90% - Needs population |
| Peak Age Ranges | `src/config/archetypes/*.json` (45 files) | Complete | 80% - Has peak_age_range |
| Age Curve Constants | `src/transactions/transaction_constants.py:223-245` | Complete | 60% - Trade-focused |
| Archetype Registry | `src/player_generation/archetypes/archetype_registry.py` | Complete | 100% - Lookup ready |

### What Needs Enhancement

| Gap | Current State | Required State |
|-----|---------------|----------------|
| Growth Phase | Not modeled (only decline) | Young players should improve toward potential |
| Individual Potential | No ceiling per player | Each player has max achievable rating |
| Position Peak Ages | Generic (YOUNG/PRIME/VETERAN) | Position-specific (RB peaks at 25, QB at 30) |
| Development Tracking | Annual only (Training Camp) | Multi-season career arc history |
| Archetype Integration | `development_curve` field unused | Use "early"/"normal"/"late" in calculations |

---

## Season Flow Integration

```
REGULAR SEASON (Week 1-18)
    → In-season performance tracking (stats affect progression)

PLAYOFFS
    → No progression changes

OFFSEASON
    ┌─────────────────────────────────────────────────────┐
    │ TRAINING CAMP (existing stage)                      │
    │   → Age progression applied                         │
    │   → Development algorithm calculates changes        │
    │   → Database updated atomically                     │
    │   → Depth charts regenerated                        │
    └─────────────────────────────────────────────────────┘
            ↓
NEXT SEASON (Year + 1)
```

---

## Tollgates

### Tollgate 1: Position-Specific Peak Ages ✅ COMPLETE
**Goal**: Replace generic age categories with position-specific peak windows from archetypes.

**What exists**:
- `AgeCurveParameters` in `transaction_constants.py` (peak_start, peak_end, decline_rate)
- `peak_age_range` in all 45 archetype JSON files

**Tasks**:
- [x] Create `PositionPeakAges` constants class consolidating peak ages by position group
- [x] Modify `AgeWeightedDevelopment.get_age_category()` to accept position parameter
- [x] Use archetype `peak_age_range` when available (player-level lookup)
- [x] Fall back to position group defaults when archetype unknown

**Files modified**:
- `src/game_cycle/services/training_camp_service.py` - Added `PositionPeakAges` class, modified `get_age_category()`
- `src/transactions/transaction_constants.py` - Added KICKER/PUNTER to `AgeCurveParameters`
- `tests/game_cycle/services/test_training_camp_progression.py` - 34 unit tests

**Acceptance Criteria**:
- [x] RB age 28 is VETERAN (peak 23-27)
- [x] QB age 28 is PRIME (peak 27-32)
- [x] Unit tests validate position-specific categorization (34 tests passing)

---

### Tollgate 2: Growth Phase Modeling ✅ COMPLETE
**Goal**: Young players improve toward their potential during growth phase (pre-peak).

**What exists**:
- `DevelopmentProfile.is_in_growth_phase()` method
- Generic +1 to +5 improvement range in training camp

**Tasks**:
- [x] Add `growth_rate` and `regression_rate` fields to `AgeCurveParameters` for each position
- [x] Calculate expected growth based on distance from peak with 50% cap:
  ```python
  if age < peak_start:
      years_to_peak = peak_start - age
      distance_multiplier = 1.0 + min(0.5, 0.1 * years_to_peak)  # +10%/year, capped at 50%
      effective_growth = growth_rate * distance_multiplier
  ```
- [x] Add `get_growth_rates()` method to `PositionPeakAges`
- [x] Add `_rate_to_range()` helper method for converting float rates to random ranges
- [x] Update `AgeWeightedDevelopment.calculate_changes()` with position-specific growth logic

**Growth Rates (points/year)**:
| Position | Pre-Peak Growth | Peak Stability | Post-Peak Decline |
|----------|-----------------|----------------|-------------------|
| QB | +1.5 | ±0.5 | -1.5 |
| RB | +2.5 | ±0.5 | -3.0 |
| WR | +2.0 | ±0.5 | -2.0 |
| TE | +1.5 | ±0.5 | -1.5 |
| OL | +1.5 | ±0.5 | -1.5 |
| DL | +2.0 | ±0.5 | -2.0 |
| LB | +2.0 | ±0.5 | -2.0 |
| DB | +2.0 | ±0.5 | -2.5 |
| K | +1.0 | ±0.3 | -0.5 |
| P | +1.0 | ±0.3 | -0.5 |

**Files modified**:
- `src/transactions/transaction_constants.py` - Added `growth_rate` and `regression_rate` to all `AgeCurveParameters`
- `src/game_cycle/services/training_camp_service.py` - Added `get_growth_rates()`, `_rate_to_range()`, updated `calculate_changes()`
- `tests/game_cycle/services/test_training_camp_progression.py` - Added 17 new tests (51 total)

**Acceptance Criteria**:
- [x] 22-year-old RB improves more than 25-year-old RB
- [x] Growth rate decreases as player approaches peak age
- [x] Post-peak decline is faster than pre-peak growth
- [x] All 51 tests passing

---

### Tollgate 3: Individual Player Potential ✅ COMPLETE
**Goal**: Each player has a potential ceiling that limits maximum overall rating.

**What exists**:
- `DevelopmentProfile` dataclass with `growth_rate`/`decline_rate` fields (unpopulated)
- Archetype `overall_range` defines generation bounds
- `draft_prospects` table already has `potential` column

**Tasks**:
- [x] Add `potential` field to `GeneratedPlayer` model
- [x] Add `_calculate_potential()` method to `PlayerGenerator`
- [x] Store potential in attributes JSON (no database schema migration needed)
- [x] Bound growth calculations by potential ceiling in `calculate_changes()`
- [x] Update `_process_single_player()` to extract and pass potential
- [x] Create migration script for existing players

**Potential Generation Formula**:
```python
def _calculate_potential(self, true_overall: int, archetype: PlayerArchetype, age: int) -> int:
    # Age factor: younger players have more growth room
    peak_start = archetype.peak_age_range[0] if archetype.peak_age_range else 27
    if age >= peak_start:
        random_bonus = random.randint(0, 3)  # At/past peak
    else:
        years_to_peak = peak_start - age
        random_bonus = random.randint(3, 8 + min(years_to_peak, 5))  # Pre-peak

    potential = min(99, true_overall + random_bonus)
    min_potential = min(99, archetype_max - 10)
    return max(potential, min_potential, true_overall)
```

**Files modified**:
- `src/player_generation/models/generated_player.py` - Added `potential: int = 0` field
- `src/player_generation/generators/player_generator.py` - Added `_calculate_potential()` method
- `src/game_cycle/services/training_camp_service.py` - Updated `DevelopmentAlgorithm` protocol, `calculate_changes()`, `_process_single_player()`
- `src/database/migrations/004_populate_player_potential.py` - NEW migration script
- `tests/game_cycle/services/test_training_camp_progression.py` - Added 8 new tests (59 total)

**Acceptance Criteria**:
- [x] All new generated players have a `potential` field
- [x] Player attributes never exceed their individual potential during training camp
- [x] Existing players get retroactive potential (via migration script)
- [x] Training camp respects potential ceiling when calculating improvements
- [x] Potential stored in attributes JSON (no database schema migration)
- [x] All 59 tests passing (8 new Tollgate 3 tests + 51 existing)

---

### Tollgate 4: Development Curve Integration ✅ COMPLETE
**Goal**: Use archetype's `development_curve` ("early"/"normal"/"late") to modify progression speed.

**What exists**:
- All 45 archetypes have `development_curve` field
- `DevelopmentProfile.development_curve` field
- `archetype_id` already stored in `players.attributes` JSON

**Tasks**:
- [x] Define curve modifiers:
  ```python
  class DevelopmentCurveModifiers:
      EARLY = {"growth": 1.25, "decline": 1.0}   # Fast bloom, normal fade
      NORMAL = {"growth": 1.0, "decline": 1.0}   # Standard trajectory
      LATE = {"growth": 0.75, "decline": 0.80}   # Slow bloom, extended career
  ```
- [x] Add `_get_archetype_development_curve()` lookup method
- [x] Modify `calculate_changes()` to apply curve modifier to base growth/regression rates
- [x] Update `_process_single_player()` to pass `archetype_id` to `calculate_changes()`
- [x] Handle unknown archetypes gracefully (default to "normal")

**Files modified**:
- `src/transactions/transaction_constants.py` - Added `DevelopmentCurveModifiers` class
- `src/game_cycle/services/training_camp_service.py` - Added `_get_archetype_development_curve()`, updated `calculate_changes()` with curve modifiers, updated caller
- `tests/game_cycle/services/test_training_camp_progression.py` - Added 22 new tests (81 total)

**Acceptance Criteria**:
- [x] "Early" developer (+25% growth) reaches peak faster but declines at normal rate
- [x] "Late" developer (-25% growth, -20% decline) has extended growth window
- [x] Players without archetype use "normal" curve
- [x] All 81 tests passing (22 new Tollgate 4 tests + 59 existing)

---

### Tollgate 5: Attribute-Specific Progression
**Goal**: Different attributes progress/regress at different rates based on type (physical vs mental).

**What exists**:
- `POSITION_ATTRIBUTES` mapping in training camp service
- Current system applies uniform random changes to all attributes

**Tasks**:
- [ ] Categorize attributes by type:
  ```python
  ATTRIBUTE_CATEGORIES = {
      "physical": ["speed", "strength", "agility", "stamina"],       # Decline faster
      "technique": ["technique", "route_running", "blocking"],       # Peak-stable
      "mental": ["awareness", "composure", "discipline", "vision"],  # Improve longer
  }
  ```
- [ ] Apply category-specific aging curves:
  - Physical: Decline starts at peak_start (not peak_end)
  - Technique: Stable through peak, gradual decline after
  - Mental: Can improve until 35+, very slow decline
- [ ] Weight attribute changes by category in overall recalculation

**Example Decay Rates**:
| Category | Pre-Peak | Peak | Post-Peak |
|----------|----------|------|-----------|
| Physical | +2.0 | 0 | -2.5 |
| Technique | +1.5 | ±0.5 | -1.0 |
| Mental | +1.0 | +0.5 | -0.5 |

**Files to modify**:
- `src/game_cycle/services/training_camp_service.py`

**Acceptance Criteria**:
- [ ] 32-year-old QB loses speed but gains/maintains awareness
- [ ] Physical attributes decline faster than mental attributes
- [ ] Technique attributes remain stable longest

---

### Tollgate 6: Career History Tracking
**Goal**: Track year-over-year progression for analytics and UI display.

**What exists**:
- `PlayerDevelopmentResult` dataclass captures single-year changes
- No persistence of historical progression

**Tasks**:
- [ ] Create `player_progression_history` database table:
  ```sql
  CREATE TABLE player_progression_history (
      id INTEGER PRIMARY KEY,
      dynasty_id TEXT NOT NULL,
      player_id INTEGER NOT NULL,
      season INTEGER NOT NULL,
      age INTEGER NOT NULL,
      overall_before INTEGER,
      overall_after INTEGER,
      overall_change INTEGER,
      attribute_changes TEXT,  -- JSON
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(dynasty_id, player_id, season)
  );
  ```
- [ ] Modify `TrainingCampService._persist_attribute_changes()` to also insert history
- [ ] Add API method to retrieve player career arc: `get_player_progression_history(player_id)`
- [ ] UI: Show career progression chart in player detail (optional enhancement)

**Files to modify**:
- Database schema (new table)
- `src/game_cycle/services/training_camp_service.py`
- `src/database/` (new API method if applicable)

**Acceptance Criteria**:
- [ ] History record created for every player each training camp
- [ ] Can query 5-year progression trend for any player
- [ ] History survives database migrations

---

### Tollgate 7: UI Integration & Polish
**Goal**: Surface progression information to users in existing views.

**What exists**:
- `game_cycle_ui/views/training_camp_view.py` shows top gainers/decliners
- Player views in roster management

**Tasks**:
- [ ] Training Camp View enhancements:
  - Add "By Position" breakdown tab
  - Show potential vs current overall
  - Highlight "breakout" players (exceeded expected growth)
  - Flag "bust" players (declined when should grow)
- [ ] Player Detail View additions:
  - Show development curve type (Early/Normal/Late Bloomer)
  - Show peak age window
  - Show potential ceiling
  - Career arc mini-chart (if history exists)
- [ ] Roster View column additions:
  - Add sortable "Potential" column
  - Add "Dev Type" indicator

**Files to modify**:
- `game_cycle_ui/views/training_camp_view.py`
- `game_cycle_ui/views/roster_view.py` (or equivalent)
- Player detail components

**Acceptance Criteria**:
- [ ] User can see player potential in roster view
- [ ] Training camp results show position breakdown
- [ ] Development type visible on player cards

---

## Dependency Flow

```
Tollgate 1: Position Peak Ages  ──┐
                                  ├──► Tollgate 5: Attribute-Specific
Tollgate 2: Growth Phase  ────────┤
                                  │
Tollgate 3: Player Potential  ────┤
                                  ├──► Tollgate 6: Career History
Tollgate 4: Development Curves  ──┘
                                           │
                                           ▼
                                  Tollgate 7: UI Integration
```

**Recommended Order**: 1 → 2 → 3 → 4 → 5 → 6 → 7

---

## Code Reuse Summary

### Direct Reuse (No Changes)
- `AgeCategory` enum
- `AttributeChange` dataclass
- `PlayerDevelopmentResult` dataclass
- `POSITION_ATTRIBUTES` mapping (25 positions)
- `DevelopmentAlgorithm` protocol
- Archetype JSON files (45 files)

### Enhance/Extend
- `AgeWeightedDevelopment` class → add position-aware peaks, growth phase
- `AgeCurveParameters` constants → add growth_rate, use for progression
- `DevelopmentProfile` model → populate on generation, use in calculations
- `TrainingCampService` → add history tracking, potential ceiling logic

### Build New
- `PositionPeakAges` constants (consolidate from archetypes + AgeCurveParameters)
- `player_progression_history` database table
- `get_player_progression_history()` API method
- Attribute category decay rates
- Potential generation formula
- UI enhancements for progression display

---

## Out of Scope (Future Milestones)

- Performance-based progression (stats affect growth) → Milestone 2: Statistics
- Injury impact on progression → Milestone 3: Injuries
- Training facility bonuses → Future enhancement
- Player personality affecting development → Future enhancement
- Coaching staff impact on development → Future enhancement

---

## Files Involved

### Backend (`src/`)
- `game_cycle/services/training_camp_service.py` - Main progression logic
- `transactions/transaction_constants.py` - Age curve parameters
- `player_generation/models/generated_player.py` - DevelopmentProfile model
- `player_generation/generators/player_generator.py` - Potential generation
- `player_generation/archetypes/archetype_registry.py` - Archetype lookup
- `config/archetypes/*.json` - Peak ages, development curves (45 files)

### UI (`game_cycle_ui/`)
- `views/training_camp_view.py` - Progression results display
- `views/roster_view.py` - Potential column
- Player detail components

### Database
- `data/database/game_cycle/game_cycle.db` - Players table, new history table

---

## Success Criteria

**Milestone is COMPLETE when:**
1. Position-specific peak ages affect progression (QB peaks later than RB)
2. Young players improve toward their potential ceiling
3. Each player has an individual potential rating
4. Archetype development curves modify progression speed
5. Physical attributes decline faster than mental attributes
6. Career progression history is tracked in database
7. UI shows potential and development type for players
8. Multi-year dynasties show realistic career arcs

---

## Testing Strategy

### Unit Tests
- `tests/game_cycle/test_training_camp_progression.py`
  - Test position-specific age categorization
  - Test growth phase calculations
  - Test potential ceiling enforcement
  - Test development curve modifiers
  - Test attribute category decay rates

### Integration Tests
- Run 10-year dynasty simulation
- Verify realistic career arcs:
  - RBs should peak around 25-27, decline by 30
  - QBs should peak around 28-32, productive until 38
  - Elite players should reach 90+ if potential allows
  - Average players should stabilize in 70s

### Validation Script
- `scripts/validate_player_progression.py`
  - Analyze progression distribution by position
  - Flag unrealistic outliers (e.g., 35-year-old RB improving)
  - Generate progression report with charts