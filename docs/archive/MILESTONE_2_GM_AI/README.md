# MILESTONE 2: Unified GM AI Infrastructure

**Status**: Planning Phase
**Goal**: Create a unified GM brain that oversees all roster-building transactions (trades, free agency, draft)
**Timeline**: 4 phases, ~5-6 days development
**Priority**: HIGH - Critical for realistic AI behavior and GM personality differentiation

## Executive Summary

Currently, The Owners Sim has **inconsistent GM AI integration** across transaction types:

- ✅ **Trade System**: FULL GM personality integration (11 trait modifiers, 6 filters)
- ❌ **Free Agency System**: ZERO GM personality integration (generic behavior)
- ❌ **Draft System**: Not implemented (stub only)
- ❌ **Roster Cuts**: ZERO GM personality integration (generic behavior)

**The Problem**: A "Win-Now" GM (e.g., Lions with `win_now_mentality=0.6`) will correctly value proven veterans in trades, but make free agency decisions identically to a rebuilding team. All 32 teams behave the same in offseason roster construction.

**The Solution**: Extend the proven `PersonalityModifiers` pattern from the trade system to all offseason decisions (free agency, draft, roster cuts), creating a unified GM decision-making framework.

## Current State Analysis

### What We Have
1. **Production-Ready GM Infrastructure**:
   - `GMArchetype` with 13 personality traits (0.0-1.0 scales)
   - 32 team-specific GM profiles (`src/config/gm_profiles/`)
   - 7 base archetypes (Win Now, Rebuilder, Draft Hoarder, etc.)
   - `GMArchetypeFactory` with team customizations

2. **Proven Personality Modifier System** (Trade System):
   - `PersonalityModifiers` class with 11 trait-based multipliers
   - 6 GM philosophy filters
   - Works in production, realistic AI behavior

3. **Shared Utilities**:
   - `TeamNeedsAnalyzer` - Used by all systems (objective needs analysis)
   - `MarketValueCalculator` - Contract value estimation
   - `TeamContext` - Shared context pattern

### What We're Missing
1. GM personality integration in `FreeAgencyManager`
2. GM personality integration in `DraftManager`
3. GM personality integration in `RosterManager`
4. Unified decision-making framework across all contexts

## Goals

### Primary Objectives
1. **Personality-Driven Free Agency**: Win-now GMs pay premiums for proven starters, rebuilders focus on value deals
2. **Personality-Driven Draft**: Risk-tolerant GMs draft high-ceiling rookies, conservative GMs prefer safe picks
3. **Personality-Driven Roster Cuts**: Loyal GMs keep veterans longer, cap-conscious GMs cut expensive backups
4. **Unified GM Framework**: Consistent personality application across trades, FA, draft, cuts

### Success Criteria
- [ ] All 32 teams exhibit distinct GM behaviors in free agency
- [ ] Draft boards reflect GM philosophies (not just positional needs)
- [ ] Roster cut decisions vary by GM loyalty and cap management traits
- [ ] Zero regression in existing trade system functionality
- [ ] 100% test coverage for new personality modifiers

## Implementation Phases

### Phase 1: Free Agency GM Integration (2 days) - **IN PROGRESS**
**Priority**: CRITICAL - Highest visibility, most frequent offseason activity
**Status**: Day 1 Complete ✅ | Day 2 Pending

**Deliverables**:
- [x] Extend `PersonalityModifiers` with `apply_free_agency_modifier()` ✅
- [x] Create `TeamContextService` for reusable context building ✅ (Architecture enhancement)
- [ ] Inject `GMArchetype` into `FreeAgencyManager` (Day 2 - pending)
- [x] Implement 5 trait modifiers for FA contract evaluation ✅:
  1. `win_now_mentality` → Premium for proven starters (1.0x - 1.4x)
  2. `cap_management` → Discount for expensive contracts (0.6x - 1.0x)
  3. `veteran_preference` → Preference for experience vs youth (0.8x - 1.2x)
  4. `risk_tolerance` → Willingness to sign injury-prone players (0.7x - 1.0x)
  5. `star_chasing` → Premium for elite free agents (1.0x - 1.5x)

**Testing**:
- [x] 15 unit tests for FA personality modifiers (100% coverage) ✅
- [x] 13 unit tests for TeamContextService (100% coverage) ✅
- [x] 5 integration tests for FreeAgencyManager (100% coverage) ✅
- [x] Win-Now vs Rebuilder variance: 58% (target: ≥20%) ✅
- [ ] Integration tests for 3 GM archetypes (Day 2 - pending)
- [ ] Validation: 10-team FA simulation (Day 2 - pending)

### Phase 2: Draft GM Integration (2-3 days)
**Priority**: HIGH - Core offseason activity, high strategic impact

**Deliverables**:
- Extend `PersonalityModifiers` with `apply_draft_modifier()`
- Inject `GMArchetype` into `DraftManager`
- Implement `DraftProspectEvaluator` with 6 trait modifiers:
  1. `risk_tolerance` → High-ceiling vs high-floor prospects
  2. `draft_pick_value` → Willingness to trade up/down
  3. `premium_position_focus` → QB/Edge/LT prioritization
  4. `win_now_mentality` → Polished rookies vs developmental projects
  5. `veteran_preference` → Older, pro-ready prospects vs young upside
  6. `star_chasing` → BPA vs need-based drafting

**Testing**:
- Unit tests for draft personality modifiers
- Mock draft simulation with 5 GM archetypes
- Validation: Draft board order varies by GM personality

### Phase 3: Roster Cuts GM Integration (1 day)
**Priority**: MEDIUM - Lower frequency, but important for cap management

**Deliverables**:
- Extend `PersonalityModifiers` with `apply_roster_cut_modifier()`
- Inject `GMArchetype` into `RosterManager`
- Implement 3 trait modifiers for cut decisions:
  1. `loyalty` → Retention value for long-tenured players
  2. `cap_management` → Willingness to absorb dead money
  3. `veteran_preference` → Keep veterans vs give youth opportunities

**Testing**:
- Unit tests for roster cut modifiers
- 90→53 roster cut simulation with 3 GM archetypes
- Validation: Cut lists differ by GM loyalty/cap traits

### Phase 4: Unified GM Framework (Optional - 1-2 days)
**Priority**: LOW - Nice-to-have, architectural cleanup

**Deliverables**:
- Create `GMDecisionEngine` base class (optional refactor)
- Consolidate personality modifier logic into unified interface
- Add cross-context consistency validation
- Document unified GM decision-making architecture

**Testing**:
- End-to-end tests across trades, FA, draft, cuts
- Validate personality consistency across all contexts

## Architecture Overview

### Design Principle: Extend, Don't Refactor

**Approach**: Add GM personality to existing systems, NOT major refactor.

**Key Components**:
1. **GMArchetype** (existing) - 13 personality traits per team
2. **PersonalityModifiers** (extend) - Add FA/Draft/Cuts modifiers to existing class
3. **Manager Injection** - Pass `gm_archetype` to OffseasonController → FreeAgencyManager/DraftManager/RosterManager
4. **Shared Utilities** (existing) - TeamNeedsAnalyzer, MarketValueCalculator, TeamContext

### Integration Pattern

```python
# BEFORE (Current State - No GM Integration)
FreeAgencyManager(database_path, dynasty_id)
    .simulate_free_agency()  # Generic behavior, all teams identical

# AFTER (Phase 1 - GM Integration)
gm = GMArchetypeFactory.create_for_team(team_id)
FreeAgencyManager(database_path, dynasty_id, gm_archetype=gm)
    .simulate_free_agency()  # Personality-driven, 32 distinct behaviors
```

### Personality Modifier Flow

```
TeamNeedsAnalyzer (objective)
    → Identifies position needs: QB=CRITICAL, WR=HIGH, etc.
    ↓
MarketValueCalculator (objective)
    → Estimates fair market value: $15M/year for 85 OVR WR
    ↓
PersonalityModifiers (subjective - NEW)
    → Applies GM trait multipliers:
      - Win-Now GM: 1.3x value (willing to overpay)
      - Rebuilder GM: 0.8x value (only signs value deals)
      - Result: Win-Now GM offers $19.5M, Rebuilder offers $12M
    ↓
FreeAgencyManager
    → Makes signing decision based on modified value
```

## Documentation Structure

- **README.md** (this file) - Overview and roadmap
- **01_current_state.md** - Detailed audit findings
- **02_architecture.md** - Unified GM brain design
- **03_implementation_plan.md** - Step-by-step development plan
- **04_personality_modifiers.md** - Trait modifier specifications
- **05_testing_strategy.md** - Validation and quality assurance

## Dependencies

### Prerequisites
- [x] GMArchetype system (exists)
- [x] GMArchetypeFactory (exists)
- [x] 32 team GM profiles (exists)
- [x] PersonalityModifiers class (exists)
- [x] TeamNeedsAnalyzer (exists)
- [x] MarketValueCalculator (exists)

### Blockers
- None identified

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Regression in trade system | Low | High | 100% test coverage, no changes to existing trade code |
| Incompatible GM traits across contexts | Medium | Medium | Cross-context validation tests, trait consistency checks |
| Performance degradation | Low | Low | Personality modifiers are simple multipliers (minimal overhead) |
| AI behavior too homogeneous | Medium | Medium | Wide trait ranges (0.0-1.0), validation with edge case GMs |

## Success Metrics

### Quantitative
- [ ] 32 distinct GM behaviors in free agency (measured by contract value variance)
- [ ] Draft board order differs by ≥30% between Win-Now and Rebuilder GMs
- [ ] Roster cut lists differ by ≥20% between Loyal and Cap-Conscious GMs
- [ ] Zero regression in trade system tests (100% pass rate maintained)
- [ ] 100% test coverage for new personality modifiers

### Qualitative
- [ ] AI free agency feels realistic (Win-Now teams overpay, Rebuilders bargain-hunt)
- [ ] Draft classes reflect GM philosophies (risk-takers draft high-ceiling, conservatives draft high-floor)
- [ ] Roster decisions make narrative sense (loyal GMs keep veterans, cap-conscious GMs cut expensive backups)

## Timeline

**Total Estimated Effort**: 5-6 development days

- **Week 1**: Phase 1 (Free Agency) - 2 days
- **Week 2**: Phase 2 (Draft) - 2-3 days
- **Week 3**: Phase 3 (Roster Cuts) - 1 day
- **Optional**: Phase 4 (Unified Framework) - 1-2 days

## Next Steps

1. Review this milestone plan
2. Begin Phase 1: Free Agency GM Integration
3. Create feature branch: `feature/milestone-2-gm-ai`
4. Implement `PersonalityModifiers.apply_free_agency_modifier()`
5. Add GM archetype injection to `FreeAgencyManager`
6. Write comprehensive tests
7. Validate with 10-team FA simulation
8. Iterate based on results

## Related Documentation

- **MILESTONE 1**: Multi-Year Season Cycle (`docs/MILESTONE_1/`) - Prerequisite for multi-season GM continuity
- **Offseason AI Manager Plan**: Phase 2 complete (`docs/plans/offseason_ai_manager_plan.md`)
- **Trade System**: PersonalityModifiers reference implementation (`src/transactions/personality_modifiers.py`)
- **GM Archetype System**: Team profiles (`src/config/gm_profiles/`) and base archetypes (`src/config/gm_archetypes/`)
