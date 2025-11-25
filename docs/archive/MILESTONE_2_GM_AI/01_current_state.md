# Current State Analysis: GM AI Systems

**Date**: 2025-11-16
**Purpose**: Comprehensive audit of existing GM decision-making systems

## Executive Finding

**The Owners Sim has a robust GM archetype infrastructure, but it's only used by the trade system. Free agency, draft, and roster cuts ignore GM personalities entirely.**

---

## 1. GM Archetype Infrastructure (PRODUCTION READY)

### 1.1 Core Components

**Location**: `src/team_management/`

| File | Purpose | Status |
|------|---------|--------|
| `gm_archetype.py` | GMArchetype dataclass with 13 traits | ✅ Production |
| `gm_archetype_factory.py` | Factory pattern for loading GM profiles | ✅ Production |
| `src/config/gm_archetypes/base_archetypes.json` | 7 base GM templates | ✅ Production |
| `src/config/gm_profiles/team_*.json` | 32 team-specific profiles | ✅ Production |

### 1.2 GMArchetype Traits (13 Total)

All traits use **0.0-1.0 continuous scales**:

| Trait | Description | Example Impact |
|-------|-------------|----------------|
| `risk_tolerance` | Willingness to gamble on unproven players | Low=safe picks, High=high-ceiling rookies |
| `win_now_mentality` | Championship urgency vs rebuild focus | High=overpay veterans, Low=stockpile picks |
| `draft_pick_value` | How much GM values picks vs proven players | High=trade down, Low=trade up |
| `cap_management` | Financial discipline | Low=restructure often, High=stay under cap |
| `trade_frequency` | Base likelihood of making trades | Multiplier for daily trade evaluation |
| `veteran_preference` | Youth focus vs veteran focus | High=sign 30+ FAs, Low=draft young |
| `star_chasing` | Tendency to pursue superstar players | High=overpay elite FAs, Low=build through draft |
| `loyalty` | Tendency to keep existing players | High=re-sign own, Low=let FAs walk |
| `desperation_threshold` | Performance level triggering desperate moves | 0.3=panic after 1 bad season, 0.7=patient rebuild |
| `patience_years` | Years willing to commit to rebuild (1-10) | Used for long-term planning |
| `deadline_activity` | Trade deadline aggressiveness | Multiplier for Week 9 trade probability |
| `premium_position_focus` | Prioritization of QB/Edge/OT | High=overpay elite positions, Low=balanced roster |
| `situational_awareness` | Ability to read team context | (Future use - not currently implemented) |

### 1.3 Base Archetypes (7 Templates)

**Location**: `src/config/gm_archetypes/base_archetypes.json`

1. **Win Now** (`win_now_mentality=0.9`, `draft_pick_value=0.3`)
2. **Rebuilder** (`win_now_mentality=0.2`, `draft_pick_value=0.9`)
3. **Balanced** (all traits=0.5)
4. **Draft Hoarder** (`draft_pick_value=0.9`, `trade_frequency=0.7`)
5. **Star Chaser** (`star_chasing=0.9`, `cap_management=0.3`)
6. **Loyal** (`loyalty=0.9`, `trade_frequency=0.2`)
7. **Aggressive** (`risk_tolerance=0.8`, `trade_frequency=0.8`)

### 1.4 Team-Specific GM Profiles (32 Teams)

**Example**: Detroit Lions (`src/config/gm_profiles/team_09_detroit_lions.json`)
```json
{
  "team_id": 9,
  "base_archetype": "Draft Hoarder",
  "customizations": {
    "win_now_mentality": 0.6
  },
  "notes": "Values draft picks highly, now transitioning to competitive phase"
}
```

**How It Works**:
1. Load base archetype ("Draft Hoarder" has `draft_pick_value=0.9`)
2. Apply team-specific customizations (`win_now_mentality` overridden to 0.6)
3. Result: Lions value picks but are more aggressive than pure Draft Hoarder

**VERDICT**: GM archetype system is **production-ready** with 32 unique team profiles.

---

## 2. Trade System (FULL GM INTEGRATION)

### 2.1 Architecture

**Central Orchestrator**: `TransactionAIManager` (`src/transactions/transaction_ai_manager.py`)

**Component Stack**:
```
TransactionAIManager (uses GMArchetype)
    ↓
TradeProposalGenerator (uses GMArchetype + TeamContext)
    ↓
TradeEvaluator (uses GMArchetype)
    ↓
PersonalityModifiers (applies 11 trait-based multipliers)
```

### 2.2 GM Integration Points

#### A. Daily Trade Probability (`TransactionAIManager._should_evaluate_today()`)

**Code Location**: `src/transactions/transaction_ai_manager.py:289-303`

```python
def _should_evaluate_today(self, team_id: int, gm: GMArchetype) -> bool:
    """Determine if team should evaluate trades today."""
    base_probability = 0.05  # 5% per day
    gm_multiplier = gm.trade_frequency  # 0.0-1.0 trait

    final_probability = base_probability * gm_multiplier
    # Example: trade_frequency=0.5 → 2.5% chance per day

    return random.random() < final_probability
```

**Impact**: Teams with `trade_frequency=0.8` make ~3x more trades than teams with `trade_frequency=0.3`.

#### B. Trade Proposal Generation

**Code Location**: `src/transactions/trade_proposal_generator.py:45-120`

- Accepts `gm_archetype` parameter
- Uses GM traits to filter trade targets
- Constructs packages based on GM philosophy
- Passes GM to `TradeEvaluator` for acceptance/rejection

#### C. Trade Evaluation (`PersonalityModifiers`)

**Code Location**: `src/transactions/personality_modifiers.py`

**11 Trait-Based Modifiers**:

| Modifier Method | Trait Used | Asset Type | Multiplier Range |
|----------------|------------|------------|------------------|
| `apply_risk_tolerance_modifier()` | `risk_tolerance` | Young players (<25) | 0.8x - 1.2x |
| `apply_win_now_modifier()` | `win_now_mentality` | Proven players (85+ OVR) | 1.0x - 1.4x |
| `apply_draft_pick_value_modifier()` | `draft_pick_value` | Draft picks | 0.7x - 1.5x |
| `apply_cap_management_modifier()` | `cap_management` | Expensive contracts | 0.6x - 1.0x |
| `apply_star_chasing_modifier()` | `star_chasing` | Elite players (90+ OVR) | 1.0x - 1.5x |
| `apply_loyalty_modifier()` | `loyalty` | Own players | 1.0x - 1.4x |
| `apply_veteran_preference_modifier()` | `veteran_preference` | Veterans (30+ age) | 0.8x - 1.2x |
| `apply_premium_position_modifier()` | `premium_position_focus` | QB/Edge/LT | 1.0x - 1.3x |
| `apply_team_performance_modifier()` | `win_now_mentality` | Context-dependent | 0.9x - 1.2x |
| `apply_deadline_modifier()` | `deadline_activity` | Week 9 only | 1.0x - 1.5x |
| `apply_desperation_modifier()` | `desperation_threshold` | Losing teams | 1.0x - 1.3x |

**Example Calculation**:

```python
# Scenario: Lions evaluating trade for 27-year-old 88 OVR WR ($12M/year)
# Lions GM: win_now_mentality=0.6, star_chasing=0.4, cap_management=0.6

base_value = 100  # Baseline trade value

# Apply modifiers:
value *= 1.2  # win_now_modifier (0.6 trait → 1.2x for proven player)
value *= 1.0  # star_chasing_modifier (0.4 trait → 1.0x, not elite)
value *= 0.92 # cap_management_modifier (0.6 trait → 0.92x for $12M contract)

final_value = 110.4  # Lions value this player 10% higher than objective value
```

#### D. GM Philosophy Filtering

**Code Location**: `src/transactions/transaction_ai_manager.py:305-385`

**6 Personality-Based Filters** (remove conflicting proposals):

1. **Star Chasing Filter** (`star_chasing < 0.4`):
   - Removes trades acquiring elite players (90+ OVR) if GM doesn't chase stars

2. **Veteran Preference Filter** (`veteran_preference < 0.4`):
   - Removes trades acquiring 30+ year old players if GM prefers youth

3. **Draft Pick Value Filter** (`draft_pick_value > 0.7`):
   - Removes trades giving up draft picks if GM values picks highly

4. **Cap Management Filter** (`cap_management > 0.7`):
   - Removes trades acquiring expensive contracts if GM is cap-conscious

5. **Loyalty Filter** (`loyalty > 0.7`):
   - Removes trades trading away long-tenured players if GM is loyal

6. **Win-Now vs Rebuild Filter**:
   - Win-Now (`win_now_mentality > 0.7`): Remove trades acquiring picks for proven players
   - Rebuild (`win_now_mentality < 0.3`): Remove trades giving up picks for veterans

**Impact**: A "Draft Hoarder" GM will NEVER propose trades giving up 1st round picks.

### 2.3 Trade System Verdict

**FULL GM INTEGRATION** - Trade decisions are deeply influenced by GM personality:
- 11 trait-based value modifiers
- 6 philosophy filters
- Probability system based on `trade_frequency` trait
- Result: Trades feel realistic, each GM behaves distinctly

---

## 3. Free Agency System (ZERO GM INTEGRATION)

### 3.1 Architecture

**Central Orchestrator**: `OffseasonController` (`src/offseason/offseason_controller.py`)

**Sub-Manager**: `FreeAgencyManager` (`src/offseason/free_agency_manager.py`)

**Decision Flow**:
```
FreeAgencyManager
    ↓
TeamNeedsAnalyzer (objective needs analysis only)
    ↓
MarketValueCalculator (objective contract values only)
    ↓
Sign based on needs + value (NO GM PERSONALITY)
```

### 3.2 GM Integration Points

**CRITICAL FINDING**: I searched for GMArchetype usage in offseason system:

```bash
grep -r "GMArchetype\|gm_archetype\|from team_management.gm" src/offseason/
# RESULT: NO MATCHES
```

**Imports Check**:
- `OffseasonController`: Does NOT import GMArchetype
- `FreeAgencyManager`: Does NOT import GMArchetype
- `DraftManager`: Does NOT import GMArchetype
- `RosterManager`: Does NOT import GMArchetype

### 3.3 Current Free Agency Logic

**Code Location**: `FreeAgencyManager.simulate_free_agency_day()` (line 195-240)

```python
def simulate_free_agency_day(self, current_date: date) -> List[Dict]:
    """Simulate one day of free agency for all AI teams."""

    for team_id in range(1, 33):
        # 1. Analyze team needs (objective)
        needs = self.team_needs_analyzer.analyze_team_needs(team_id)

        # 2. Get available free agents
        free_agents = self._get_available_free_agents()

        # 3. Find best FA for highest need (objective)
        best_fa = self._find_best_fa_for_need(free_agents, needs[0])

        # 4. Calculate market value (objective)
        market_value = self.market_value_calculator.calculate(best_fa)

        # 5. Sign if cap space available (NO GM PERSONALITY)
        if team_cap_space >= market_value['aav']:
            self._sign_free_agent(team_id, best_fa, market_value)
```

**What's Missing**:
- NO GM trait modifiers on contract value perception
- NO win-now vs rebuild differentiation
- NO veteran preference consideration
- NO risk tolerance for injury-prone players
- NO star chasing premium for elite free agents
- NO cap management discipline differences

**Example Inconsistency**:

| Team | GM Profile | Current FA Behavior | Expected FA Behavior |
|------|-----------|-------------------|---------------------|
| Lions | Win-Now (0.6), Draft Hoarder | Signs $15M WR if cap space | Should overpay ($17-18M) for proven starter |
| Browns | Rebuilder (0.8), Cap-Conscious | Signs $15M WR if cap space | Should only sign value deals ($12-13M max) |

**Result**: Both teams offer identical $15M contract (generic behavior).

### 3.4 Free Agency Verdict

**ZERO GM INTEGRATION** - Free agency decisions ignore GM personality:
- All 32 teams behave identically
- No differentiation between win-now and rebuild teams
- No risk tolerance, loyalty, or cap management effects
- Result: Free agency feels generic and cookie-cutter

---

## 4. Draft System (NOT IMPLEMENTED)

### 4.1 Architecture

**Sub-Manager**: `DraftManager` (`src/offseason/draft_manager.py`)

**Status**: **STUB ONLY** - Awaiting Phase 3 implementation

### 4.2 Current Implementation

**Code Location**: `DraftManager.simulate_draft()` (line 163-183)

```python
def simulate_draft(self) -> List[DraftPick]:
    """Simulate the entire NFL draft (all 7 rounds)."""
    raise NotImplementedError(
        "Full draft simulation not yet implemented. "
        "Use simulate_draft_round() for individual rounds."
    )
```

**What Exists**:
- Draft order calculation (complete, working)
- Draft board sorting by overall rating (basic, working)
- Round-by-round simulation (returns empty list)

**What Doesn't Exist**:
- AI decision-making for draft selections
- Draft prospect evaluation system
- Trade up/down logic
- Reach/value picking decisions
- GM personality integration

### 4.3 Draft Verdict

**NOT IMPLEMENTED** - Draft AI is stub only:
- Cannot simulate AI team draft selections
- No GM personality consideration
- Awaiting Phase 3 development

---

## 5. Roster Cuts System (ZERO GM INTEGRATION)

### 5.1 Architecture

**Sub-Manager**: `RosterManager` (`src/offseason/roster_manager.py`)

**Current Logic**: Value-based scoring system (objective)

### 5.2 Current Roster Cut Logic

**Code Location**: `RosterManager.execute_roster_cuts()` (line 105-215)

```python
def execute_roster_cuts(self, team_id: int) -> List[Dict]:
    """Cut roster from 90 to 53 players."""

    # 1. Score all players by value (objective)
    player_scores = self._calculate_player_values(team_id)

    # 2. Sort by value descending
    ranked_players = sorted(player_scores, key=lambda x: x['value'], reverse=True)

    # 3. Keep top 53 (NO GM PERSONALITY)
    keepers = ranked_players[:53]
    cuts = ranked_players[53:]

    return cuts
```

**Value Scoring** (objective formula):
```python
value = (overall_rating * 0.4) +
        (depth_chart_position * 0.3) +
        (age_factor * 0.2) +
        (contract_factor * 0.1)
```

**What's Missing**:
- NO loyalty modifier for long-tenured players
- NO cap management consideration (might cut expensive vets)
- NO veteran preference (youth vs experience tradeoff)
- NO risk tolerance (keep high-ceiling backups vs safe depth)

**Example Inconsistency**:

| Team | GM Profile | Current Behavior | Expected Behavior |
|------|-----------|------------------|-------------------|
| Patriots | Loyal GM (0.9) | Cuts veteran backup if value score low | Should keep veteran (loyalty premium) |
| Raiders | Cap-Conscious (0.8) | Keeps expensive veteran if value score high | Should cut to save cap space |

**Result**: All teams use identical value formula (no personality differentiation).

### 5.3 Roster Cuts Verdict

**ZERO GM INTEGRATION** - Roster decisions ignore GM personality:
- All 32 teams use identical value scoring
- No loyalty, cap management, or veteran preference effects
- Result: Roster cuts feel mechanical and personality-agnostic

---

## 6. Shared Utilities

### 6.1 TeamNeedsAnalyzer (USED BY ALL SYSTEMS)

**Location**: `src/offseason/team_needs_analyzer.py`

**Purpose**: Objective position-based needs analysis

**Users**:
- ✅ `TransactionAIManager` (trades)
- ✅ `TradeProposalGenerator` (trades)
- ✅ `FreeAgencyManager` (free agency)
- ✅ `DraftManager` (draft)

**What It Does**:
```python
def analyze_team_needs(self, team_id: int) -> List[PositionNeed]:
    """Analyze roster depth and identify position needs."""

    # Returns:
    # [
    #   PositionNeed(position="QB", urgency="CRITICAL", tier=1),
    #   PositionNeed(position="WR", urgency="HIGH", tier=2),
    #   PositionNeed(position="RB", urgency="MEDIUM", tier=3)
    # ]
```

**Urgency Levels**: CRITICAL, HIGH, MEDIUM, LOW, NONE

**Personality Integration**: **NONE** - This is objective analysis only.

**VERDICT**: TeamNeedsAnalyzer is a **shared utility** but does NOT incorporate GM traits.

### 6.2 MarketValueCalculator (USED BY FREE AGENCY)

**Location**: `src/offseason/market_value_calculator.py`

**Purpose**: Objective contract value estimation

**What It Does**:
```python
def calculate_contract_value(self, player: Player) -> Dict:
    """Calculate fair market value for player."""

    # Returns:
    # {
    #   'aav': 15000000,  # Annual average value
    #   'years': 4,
    #   'total': 60000000,
    #   'guaranteed': 40000000
    # }
```

**Personality Integration**: **NONE** - This is objective valuation only.

**VERDICT**: MarketValueCalculator provides baseline, but needs GM modifiers.

---

## 7. Integration Summary

### 7.1 Current GM Integration by System

| System | GM Archetype Integration | Shared Logic | Status |
|--------|-------------------------|--------------|--------|
| **Trade System** | ✅ FULL (11 modifiers + 6 filters) | TeamNeedsAnalyzer | ✅ Production Ready |
| **Free Agency** | ❌ NONE | TeamNeedsAnalyzer, MarketValueCalculator | ✅ Phase 2 Complete (No Personality) |
| **Draft System** | ❌ NONE | TeamNeedsAnalyzer | ❌ Stub Only |
| **Roster Cuts** | ❌ NONE | TeamNeedsAnalyzer | ✅ Phase 2 Complete (No Personality) |

### 7.2 Architectural Gaps

**CRITICAL GAP**: The trade system demonstrates that GM personality integration works and creates realistic behavior, but this pattern has NOT been extended to offseason systems.

**Impact**:
- Trades feel realistic (Lions behave differently than Browns)
- Free agency feels generic (all teams behave identically)
- Draft doesn't exist yet
- Roster cuts feel mechanical (identical value scoring)

**Root Cause**: Offseason Phase 2 focused on infrastructure (30-day FA simulation, 90→53 cuts, etc.) but deferred GM personality integration to future work.

---

## 8. Database Schema

### 8.1 Relevant Tables

**`player_transactions`** - Logs all transactions (trades, signings, cuts, tags)
```sql
CREATE TABLE player_transactions (
    transaction_id INTEGER PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    transaction_type TEXT, -- 'TRADE', 'UFA_SIGNING', 'RELEASE', etc.
    from_team_id INTEGER,
    to_team_id INTEGER,
    transaction_date DATE,
    details TEXT  -- JSON with transaction specifics
);
```

**`player_contracts`** - Contract details
```sql
CREATE TABLE player_contracts (
    contract_id INTEGER PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    aav INTEGER,
    years INTEGER,
    total_value INTEGER,
    guaranteed INTEGER,
    signing_bonus INTEGER,
    contract_type TEXT  -- 'VETERAN', 'ROOKIE', 'FRANCHISE_TAG', etc.
);
```

**NO TABLE FOR**:
- GM profiles (stored in JSON config files, not database)
- GM decision history (no audit log of personality-driven decisions)
- AI transaction proposals/suggestions (no pending review system)

### 8.2 Implications

**Current State**:
- GM archetypes live in config files (not database)
- No historical tracking of GM decision-making patterns
- No way to analyze "Did this GM behave consistently with their archetype?"

**Future Consideration**:
- Could add `gm_decisions` audit table to track personality-driven choices
- Would enable validation: "Win-Now GMs should overpay 80% of the time in FA"

---

## 9. Key Findings

### 9.1 What We Have (GOOD)
1. ✅ Production-ready GM archetype infrastructure (32 team profiles, 13 traits)
2. ✅ Proven PersonalityModifiers pattern (11 trait modifiers in trade system)
3. ✅ Shared utilities (TeamNeedsAnalyzer, MarketValueCalculator, TeamContext)
4. ✅ Working offseason systems (FA, roster cuts) - just missing personality

### 9.2 What We're Missing (GAPS)
1. ❌ GM personality integration in free agency (all teams behave identically)
2. ❌ GM personality integration in draft (system not implemented)
3. ❌ GM personality integration in roster cuts (mechanical value scoring)
4. ❌ Unified GM decision-making framework across all contexts

### 9.3 Architectural Opportunities
1. **Low-Hanging Fruit**: Extend PersonalityModifiers to FA/Cuts (2-3 days work)
2. **High Impact**: Free agency personality integration (most visible to users)
3. **Future Work**: Draft personality integration (depends on draft AI implementation)
4. **Nice-to-Have**: Unified GMDecisionEngine refactor (architectural cleanup)

---

## 10. Recommendations

### 10.1 Immediate Priority (Phase 1)
**Integrate GM personalities into Free Agency** - Highest impact, proven pattern

**Why**:
- Free agency is most visible offseason activity
- Infrastructure exists (FreeAgencyManager works, just needs GM traits)
- Can reuse PersonalityModifiers pattern from trade system
- Low risk, high reward

**Effort**: 2 days

### 10.2 Medium Priority (Phase 2)
**Integrate GM personalities into Draft** - Core offseason activity

**Why**:
- Draft is critical roster-building mechanism
- Sets foundation for multi-year dynasty simulation
- Requires draft AI implementation (currently stub)

**Effort**: 2-3 days

### 10.3 Lower Priority (Phase 3)
**Integrate GM personalities into Roster Cuts** - Refinement/polish

**Why**:
- Roster cuts less visible than FA/draft
- Current value scoring is reasonable (just lacks personality)
- Can leverage FA personality modifiers (cap_management, loyalty)

**Effort**: 1 day

### 10.4 Optional (Phase 4)
**Refactor to Unified GMDecisionEngine** - Architectural improvement

**Why**:
- Cleaner architecture
- Single source of truth for GM decisions
- Easier to maintain consistency across contexts

**Why Not**:
- Major refactor risk
- Breaks existing tests
- Incremental extension pattern is lower risk

**Effort**: 2-3 days

---

## Next Steps

See **02_architecture.md** for detailed design of unified GM brain system.
