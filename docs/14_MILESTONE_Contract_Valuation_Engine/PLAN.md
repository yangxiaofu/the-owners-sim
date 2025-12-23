# Milestone 14: Contract Valuation Engine

## Executive Summary

**Objective:** Create a sophisticated, extensible contract valuation system that generates realistic contract offers based on player performance, GM personality, and owner pressure dynamics.

**Vision:** Transform contract generation from simple rating-based calculations to a multi-factor valuation system where:
- Player stats, grades, and market comparables all contribute to value
- GM archetype determines how these factors are weighted (analytics-focused vs. scout-focused)
- Owner pressure (job security, win-now urgency) dynamically adjusts offers
- Full audit trail enables benchmarking against real NFL contracts

**Key Differentiators from Current System:**
- **From**: `MarketValueCalculator` uses only overall rating + position + age
- **To**: Multi-factor engine with stats, scouting grades, market comparables, and personality-driven weighting

**Pattern:** Factor-based composition with Strategy pattern for GM influence and Chain of Responsibility for pressure modifiers.

---

## User Stories

### Contract Valuation

**US-1: Stats-Based Valuation**
> As a simulation engine, I want contract values to reflect actual player production stats (yards, TDs, tackles), so contracts feel earned based on performance.

**Acceptance Criteria:**
- Position-specific stat benchmarks (QB: yards, TDs, passer rating; RB: yards, YPC, etc.)
- Stats converted to percentile rank against league
- Percentile mapped to AAV range for position
- Full breakdown available for debugging

**US-2: Scouting Grade Valuation**
> As a simulation engine, I want contract values to incorporate scouting grades (technique, football IQ, potential), so "eye test" factors matter.

**Acceptance Criteria:**
- Scouting grades include: technique, football_iq, athleticism, potential
- Potential weighted higher for younger players
- Lower confidence than stats (more subjective)
- Breakdown shows grade contributions

**US-3: Market Comparable Valuation**
> As a simulation engine, I want contracts to reflect recent signings at the position, so market dynamics feel realistic.

**Acceptance Criteria:**
- Reference recent contracts at same position
- Adjust for tier (elite vs. average starter vs. backup)
- Cap inflation adjustment year-over-year
- Breakdown shows comparable contracts used

---

### GM Influence

**US-4: Analytics-Heavy GM**
> As an Owner, I want my analytics-focused GM to weight stats heavily when valuing players, so their personality affects contract strategy.

**Acceptance Criteria:**
- Analytics GM: 50% stats, 15% scouting, 20% market, 15% rating
- Produces different valuations than scout-focused GM
- GM style visible in proposal rationale
- Consistent behavior across FA, re-signing, trades

**US-5: Scout-Focused GM**
> As an Owner, I want my scout-focused GM to trust their eye test over raw stats, so traditional GMs behave differently.

**Acceptance Criteria:**
- Scout GM: 15% stats, 50% scouting, 20% market, 15% rating
- Values "upside" and "intangibles" more heavily
- May overpay for players with high potential grades
- Rationale explains scouting-based reasoning

**US-6: GM Style Spectrum**
> As a system, I want GM valuation style to be a continuous spectrum (not just 2 types), so GMs feel unique.

**Acceptance Criteria:**
- GMArchetype includes `analytics_preference` (0.0-1.0) and `scouting_preference` (0.0-1.0)
- Weight calculator interpolates between base styles
- 4+ distinct styles: Analytics-Heavy, Scout-Focused, Balanced, Market-Driven
- Custom traits create unique GM personalities

---

### Owner Pressure

**US-7: Job Security Pressure**
> As a system, I want desperate GMs (hot seat) to overpay for proven talent, so job pressure affects decisions.

**Acceptance Criteria:**
- Job security calculated from: tenure, playoff appearances, recent win%, owner patience
- High pressure (>0.7): +10-15% overpay, higher guarantees
- Low pressure (<0.3): Patient, value-focused deals
- Pressure level visible in proposal breakdown

**US-8: Win-Now Urgency**
> As a system, I want teams in championship windows to pay premium for immediate contributors, so contenders behave differently than rebuilders.

**Acceptance Criteria:**
- Win-now teams prefer veterans, pay for proven production
- Rebuilding teams value youth and potential
- Modifier stacks with job security pressure
- Owner philosophy (from Milestone 13) feeds into this

**US-9: Budget Constraints**
> As a system, I want owner spending philosophy to constrain GM offers, so cheap owners produce different teams.

**Acceptance Criteria:**
- Aggressive owner: +15% budget flexibility
- Conservative owner: -10% budget constraint
- Constraint applied after GM valuation
- Cannot exceed owner-set maximums (max_contract_years, max_guaranteed_percent)

---

### Benchmarking

**US-10: Benchmark Against NFL**
> As a developer, I want to compare generated contracts to real NFL contracts, so I can tune the system for realism.

**Acceptance Criteria:**
- Load real NFL contract data (position, AAV, years, guaranteed)
- Run valuation engine with test player profiles
- Compare output to actual contracts
- Generate deviation report (% difference from reality)

**US-11: Audit Trail**
> As a developer, I want full breakdown of every valuation, so I can debug and tune factor weights.

**Acceptance Criteria:**
- Every ValuationResult includes raw factor results
- Factor contributions (weighted) visible
- GM style and pressure level recorded
- Export to JSON for analysis

---

## Technical Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ContractValuationEngine                              │
│                         (Orchestrator / Facade)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐           │
│  │  ValueFactors   │   │  GMInfluence    │   │ OwnerPressure   │           │
│  │  (Base Value)   │──▶│  (Weighting)    │──▶│  (Modifiers)    │──▶ OFFER  │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘           │
│          │                     │                     │                      │
│          ▼                     ▼                     ▼                      │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                    ValuationBreakdown                        │           │
│  │  (Audit trail for testing/benchmarking)                      │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Factor-based Composition** - Each value input (stats, grades, market) is a pluggable "factor"
2. **Strategy Pattern** - GM influence implemented as interchangeable weighting strategies
3. **Chain of Responsibility** - Pressure modifiers applied sequentially
4. **Full Audit Trail** - Every calculation step recorded for benchmarking
5. **Open/Closed Principle** - Add new factors without modifying existing code

### File Structure

```
src/contract_valuation/
├── __init__.py
├── engine.py                    # ContractValuationEngine (orchestrator)
├── models.py                    # ValuationResult, FactorResult, ContractOffer
├── context.py                   # ValuationContext, OwnerContext
│
├── factors/                     # Pluggable value factors
│   ├── __init__.py
│   ├── base.py                  # Abstract ValueFactor interface
│   ├── stats_factor.py          # Stats-based valuation
│   ├── rating_factor.py         # Overall rating valuation
│   ├── scouting_factor.py       # Scouting grades valuation
│   ├── market_factor.py         # Comparable contracts
│   └── age_factor.py            # Age curve adjustments
│
├── gm_influence/                # GM personality weighting
│   ├── __init__.py
│   ├── base.py                  # Abstract GMInfluenceStrategy
│   ├── weight_calculator.py     # Factor weight determination
│   └── styles.py                # GMStyle enum and base weights
│
├── owner_pressure/              # Owner/situational modifiers
│   ├── __init__.py
│   ├── base.py                  # Abstract PressureModifier
│   ├── job_security.py          # GM job security pressure
│   ├── win_now.py               # Championship window pressure
│   └── budget_stance.py         # Owner spending philosophy
│
├── benchmarks/                  # Position market data
│   ├── __init__.py
│   ├── position_benchmarks.py   # Position-specific stat benchmarks
│   ├── market_rates.py          # Current market AAV by position/tier
│   └── nfl_contracts.json       # Real NFL contract data for validation
│
└── testing/                     # Benchmarking & validation
    ├── __init__.py
    ├── test_harness.py          # BenchmarkHarness class
    ├── benchmark_cases.py       # Test case definitions
    └── report_generator.py      # Deviation reports
```

---

## Data Models

### Core Models

```python
# src/contract_valuation/models.py

@dataclass
class FactorResult:
    """Result from a single valuation factor."""
    name: str                     # Factor identifier (e.g., "stats_based")
    raw_value: float              # Unweighted value estimate (AAV in dollars)
    confidence: float             # 0.0-1.0, reliability of estimate
    breakdown: Dict[str, Any]     # Detailed calculation steps

@dataclass
class FactorWeights:
    """How much each factor contributes to final valuation."""
    stats_weight: float           # Weight for stats-based factor
    scouting_weight: float        # Weight for scouting grades factor
    market_weight: float          # Weight for market comparables
    rating_weight: float          # Weight for overall rating
    # Sum must equal 1.0

@dataclass
class ContractOffer:
    """Generated contract offer."""
    aav: int                      # Annual average value
    years: int                    # Contract length
    total_value: int              # Total contract value
    guaranteed: int               # Total guaranteed money
    signing_bonus: int            # Upfront signing bonus
    guaranteed_pct: float         # Guaranteed percentage

@dataclass
class ValuationResult:
    """Complete valuation with full audit trail."""
    offer: ContractOffer

    # Breakdown for debugging/benchmarking
    factor_contributions: Dict[str, float]  # Factor name → weighted contribution
    gm_style: str                           # GM style name
    gm_style_description: str               # Human-readable description
    pressure_level: float                   # 0.0-1.0
    pressure_adjustment: str                # Description of adjustment

    # Full audit trail
    raw_factor_results: List[FactorResult]
    weights_used: FactorWeights

    def to_benchmark_format(self) -> Dict[str, Any]:
        """Export for benchmark comparison."""

@dataclass
class ValuationContext:
    """Market context for valuation."""
    salary_cap: int               # Current year salary cap
    season: int                   # Current season year
    position_market_rates: Dict[str, int]  # Position → average AAV

@dataclass
class OwnerContext:
    """Owner/situational context."""
    job_security: "JobSecurityContext"
    owner_philosophy: str         # "aggressive", "balanced", "conservative"
    win_now_mode: bool            # Is team in championship window?
    max_contract_years: int       # Owner constraint
    max_guaranteed_pct: float     # Owner constraint
```

### GM Archetype Extensions

```python
# Updates to src/team_management/gm_archetype.py

@dataclass
class GMArchetype:
    # ... existing traits ...

    # NEW: Valuation style traits
    analytics_preference: float = 0.5
    """How much GM trusts stats/analytics (0.0 = ignores, 1.0 = primary driver)"""

    scouting_preference: float = 0.5
    """How much GM trusts scouting reports (0.0 = ignores, 1.0 = primary driver)"""

    market_awareness: float = 0.5
    """How much GM tracks market rates (0.0 = ignores market, 1.0 = market-driven)"""
```

---

## Tollgate Plan

### Progress Summary

| Tollgate | Status | Tests | Description |
|----------|--------|-------|-------------|
| T1 | ✅ COMPLETE | 12 | Core Models & Interfaces |
| T2 | ✅ COMPLETE | 60 | Value Factors Implementation |
| T3 | ✅ COMPLETE | 16 | GM Influence System |
| T4 | ✅ COMPLETE | 46 | Owner Pressure Modifiers |
| T5 | ✅ COMPLETE | 20 | Valuation Engine Orchestrator |
| T6 | ✅ COMPLETE | 24 | Position Benchmarks & Market Data |
| T7 | ✅ COMPLETE | 12 | Benchmark Harness & Calibration |
| T8 | ✅ COMPLETE | 7 | Service Integration (GMProposal) |
| T9 | ✅ COMPLETE | 22 | UI Integration (ValuationBreakdownWidget) |

**Total Tests Passing: 219**

---

### Tollgate 1: Core Models & Interfaces

**Objective:** Establish data models and abstract interfaces for the valuation system.

**Tasks:**
1. Create `src/contract_valuation/` package structure
2. Implement core dataclasses in `models.py`
3. Create abstract `ValueFactor` base class
4. Create abstract `PressureModifier` base class
5. Add new traits to `GMArchetype`
6. Write unit tests for model validation

**Files:**
- `src/contract_valuation/__init__.py`
- `src/contract_valuation/models.py`
- `src/contract_valuation/context.py`
- `src/contract_valuation/factors/base.py`
- `src/contract_valuation/owner_pressure/base.py`
- `src/team_management/gm_archetype.py` (modify)
- `tests/contract_valuation/test_models.py`

**Acceptance Criteria:**
- [x] All dataclasses have proper validation
- [x] FactorWeights validates sum equals 1.0
- [x] ValuationResult.to_benchmark_format() works
- [x] GMArchetype includes new valuation traits (analytics_preference, scouting_preference, market_awareness)
- [x] Abstract base classes define clear interfaces
- [x] Unit tests pass (20/20 tests passing)

**Completed Files:**
- `src/contract_valuation/__init__.py` - Package exports
- `src/contract_valuation/models.py` - FactorResult, FactorWeights, ContractOffer, ValuationResult
- `src/contract_valuation/context.py` - JobSecurityContext, ValuationContext, OwnerContext
- `src/contract_valuation/factors/base.py` - Abstract ValueFactor base class
- `src/contract_valuation/owner_pressure/base.py` - Abstract PressureModifier base class
- `src/contract_valuation/gm_influence/styles.py` - GMStyle enum
- `src/team_management/gm_archetype.py` - Added 3 new traits
- `src/config/gm_archetypes/base_archetypes.json` - Added trait values for 7 archetypes
- `tests/contract_valuation/test_models.py` - 12 unit tests
- `tests/contract_valuation/test_context.py` - 8 unit tests

---

### Tollgate 2: Value Factors Implementation

**Objective:** Implement the pluggable value factors.

**Tasks:**
1. Implement `StatsFactor` with position-specific stat benchmarks
2. Implement `RatingFactor` based on overall rating
3. Implement `ScoutingFactor` with grade weighting
4. Implement `MarketFactor` with comparable contracts
5. Implement `AgeFactor` for age curve adjustments
6. Write unit tests for each factor

**Files:**
- `src/contract_valuation/factors/stats_factor.py`
- `src/contract_valuation/factors/rating_factor.py`
- `src/contract_valuation/factors/scouting_factor.py`
- `src/contract_valuation/factors/market_factor.py`
- `src/contract_valuation/factors/age_factor.py`
- `tests/contract_valuation/factors/test_stats_factor.py`
- `tests/contract_valuation/factors/test_rating_factor.py`
- `tests/contract_valuation/factors/test_scouting_factor.py`
- `tests/contract_valuation/factors/test_market_factor.py`
- `tests/contract_valuation/factors/test_age_factor.py`

**Factor Specifications:**

**StatsFactor:**
```python
# Position-specific key stats
QB_STATS = ["pass_yards", "pass_tds", "interceptions", "passer_rating", "completion_pct"]
RB_STATS = ["rush_yards", "rush_tds", "ypc", "receptions", "fumbles"]
WR_STATS = ["rec_yards", "receptions", "rec_tds", "ypr", "catch_pct"]
# ... etc for all positions
```

**ScoutingFactor:**
```python
# Grade categories and weights
GRADE_WEIGHTS = {
    "technique": 0.25,
    "football_iq": 0.25,
    "athleticism": 0.20,
    "potential": 0.30,  # Higher for younger players
}
```

**Acceptance Criteria:**
- [ ] StatsFactor produces position-appropriate valuations
- [ ] RatingFactor maps 0-100 overall to AAV range
- [ ] ScoutingFactor weights potential higher for young players
- [ ] MarketFactor references comparable tier contracts
- [ ] AgeFactor applies decline curve for older players
- [ ] Each factor includes detailed breakdown
- [ ] Unit tests pass (target: 40 tests)

---

### Tollgate 3: GM Influence System

**Objective:** Implement GM personality-based factor weighting.

**Tasks:**
1. Define `GMStyle` enum with 4+ styles
2. Create base weight configurations per style
3. Implement `GMWeightCalculator` with interpolation
4. Add style rationale generation
5. Write unit tests for weight calculation

**Files:**
- `src/contract_valuation/gm_influence/styles.py`
- `src/contract_valuation/gm_influence/weight_calculator.py`
- `tests/contract_valuation/gm_influence/test_weight_calculator.py`

**GM Styles:**

| Style | Stats | Scouting | Market | Rating | Description |
|-------|-------|----------|--------|--------|-------------|
| ANALYTICS_HEAVY | 0.50 | 0.15 | 0.20 | 0.15 | Trusts the numbers |
| SCOUT_FOCUSED | 0.15 | 0.50 | 0.20 | 0.15 | Eye test over stats |
| BALANCED | 0.30 | 0.25 | 0.25 | 0.20 | Uses all inputs |
| MARKET_DRIVEN | 0.15 | 0.15 | 0.55 | 0.15 | Follows market rates |

**Acceptance Criteria:**
- [ ] 4 distinct GM styles with different weight distributions
- [ ] Weight calculator interpolates from archetype traits
- [ ] Same player gets different valuations from different GM styles
- [ ] Style name and description available for UI
- [ ] Unit tests pass (target: 15 tests)

---

### Tollgate 4: Owner Pressure Modifiers

**Objective:** Implement situational pressure modifiers.

**Tasks:**
1. Implement `JobSecurityModifier` with pressure calculation
2. Implement `WinNowModifier` for championship urgency
3. Implement `BudgetStanceModifier` for owner philosophy
4. Create modifier chain application
5. Write unit tests for pressure effects

**Files:**
- `src/contract_valuation/owner_pressure/job_security.py`
- `src/contract_valuation/owner_pressure/win_now.py`
- `src/contract_valuation/owner_pressure/budget_stance.py`
- `tests/contract_valuation/owner_pressure/test_job_security.py`
- `tests/contract_valuation/owner_pressure/test_win_now.py`
- `tests/contract_valuation/owner_pressure/test_budget_stance.py`

**Pressure Effects:**

| Pressure Level | AAV Adjustment | Guarantee Adjustment | Description |
|----------------|----------------|---------------------|-------------|
| < 0.3 (Secure) | -3% to 0% | -5% | Patient, value deals |
| 0.3-0.7 (Normal) | 0% | 0% | Standard negotiation |
| > 0.7 (Hot Seat) | +10% to +15% | +10% to +15% | Desperate, must win now |

**Acceptance Criteria:**
- [ ] Job security calculated from tenure, wins, playoffs
- [ ] High pressure GMs overpay by 10-15%
- [ ] Secure GMs get 3-5% discounts
- [ ] Win-now mode affects veteran preference
- [ ] Budget stance applies owner constraints
- [ ] Modifiers stack appropriately
- [ ] Unit tests pass (target: 25 tests)

---

### Tollgate 5: Valuation Engine Orchestrator

**Objective:** Implement the main engine that ties everything together.

**Tasks:**
1. Create `ContractValuationEngine` class
2. Implement factor aggregation with weights
3. Implement pressure modifier chain
4. Implement contract structure determination (years, guarantees)
5. Generate complete `ValuationResult` with audit trail
6. Write integration tests

**Files:**
- `src/contract_valuation/engine.py`
- `tests/contract_valuation/test_engine.py`

**Engine Flow:**
```
1. Calculate each factor's raw value
2. Get GM-determined weights
3. Weighted aggregation → base AAV
4. Apply pressure modifiers → adjusted AAV
5. Determine contract structure (years, guarantees)
6. Build ValuationResult with full breakdown
```

**Acceptance Criteria:**
- [ ] Engine accepts pluggable factors list
- [ ] Factors calculated in parallel (no dependencies)
- [ ] Weights applied correctly
- [ ] Pressure modifiers applied sequentially
- [ ] Contract structure (years, guarantees) reflects age and pressure
- [ ] Full audit trail in result
- [ ] Integration tests pass (target: 20 tests)

---

### Tollgate 6: Position Benchmarks & Market Data

**Objective:** Create position-specific benchmarks for realistic valuations.

**Tasks:**
1. Define stat benchmarks per position (25th, 50th, 75th, 90th percentiles)
2. Define current market AAV rates by position and tier
3. Create benchmark lookup utilities
4. Load real NFL contract data for validation
5. Write unit tests for benchmark accuracy

**Files:**
- `src/contract_valuation/benchmarks/position_benchmarks.py`
- `src/contract_valuation/benchmarks/market_rates.py`
- `src/contract_valuation/benchmarks/nfl_contracts.json`
- `tests/contract_valuation/benchmarks/test_position_benchmarks.py`

**Market Rate Data (2024-2025 approximations):**

| Position | Backup | Starter | Quality | Elite |
|----------|--------|---------|---------|-------|
| QB | $3M | $15M | $35M | $50M+ |
| EDGE | $3M | $10M | $18M | $28M+ |
| WR | $2M | $8M | $18M | $28M+ |
| CB | $2M | $8M | $15M | $22M+ |
| OT | $2M | $10M | $18M | $25M+ |
| RB | $1M | $4M | $8M | $14M+ |
| ... | ... | ... | ... | ... |

**Acceptance Criteria:**
- [ ] All 25 positions have stat benchmarks
- [ ] All positions have market rate tiers
- [ ] Percentile lookup works correctly
- [ ] Market rates reflect 2024-2025 NFL reality
- [ ] NFL contract JSON loads successfully
- [ ] Unit tests pass (target: 15 tests)

---

### Tollgate 7: Benchmark Harness & Testing

**Objective:** Create comprehensive testing framework for validation.

**Tasks:**
1. Create `BenchmarkHarness` class
2. Define benchmark test cases
3. Implement comparison against NFL contracts
4. Generate deviation reports
5. Create CI-friendly test runner

**Files:**
- `src/contract_valuation/testing/test_harness.py`
- `src/contract_valuation/testing/benchmark_cases.py`
- `src/contract_valuation/testing/report_generator.py`
- `tests/contract_valuation/test_benchmark_harness.py`

**Benchmark Case Categories:**
1. **Elite Players** - Top 10 at position (should produce top-tier AAVs)
2. **Average Starters** - 75-84 overall (should produce mid-tier AAVs)
3. **Backups** - 65-74 overall (should produce backup-level AAVs)
4. **Age Extremes** - Young prospects vs. 33+ veterans
5. **GM Style Variance** - Same player, different GM styles
6. **Pressure Scenarios** - Desperate GM vs. secure GM

**Acceptance Criteria:**
- [ ] Harness loads and runs benchmark cases
- [ ] Results compared to expected ranges
- [ ] Deviation report shows % difference from target
- [ ] Average deviation < 15% for realistic cases
- [ ] Edge cases (age, pressure) behave correctly
- [ ] Report exportable to JSON/CSV
- [ ] Unit tests pass (target: 15 tests)

---

### Tollgate 8: Service Integration

**Objective:** Integrate valuation engine into existing services.

**Tasks:**
1. Update `ResigningService` to use valuation engine
2. Update `FreeAgencyService` to use valuation engine
3. Update `GMFAProposalEngine` to use valuation engine
4. Update `TradeService` for player valuation in trades
5. Write integration tests

**Files:**
- `src/game_cycle/services/resigning_service.py` (modify)
- `src/game_cycle/services/free_agency_service.py` (modify)
- `src/game_cycle/services/gm_fa_proposal_engine.py` (modify)
- `src/game_cycle/services/trade_service.py` (modify)
- `tests/game_cycle/services/test_valuation_integration.py`

**Integration Points:**
```python
# Example: GMFAProposalEngine update
class GMFAProposalEngine:
    def __init__(
        self,
        gm_archetype: GMArchetype,
        fa_guidance: FAGuidance,
        valuation_engine: ContractValuationEngine,  # NEW
    ):
        self._engine = valuation_engine

    def _create_proposal(self, player, ...):
        # Use engine instead of simple calculation
        result = self._engine.valuate(
            player=player,
            gm_archetype=self.gm,
            owner_context=self._build_owner_context(),
            market_context=self._market_context,
        )
        return self._result_to_proposal(result)
```

**Acceptance Criteria:**
- [ ] ResigningService produces engine-based valuations
- [ ] FreeAgencyService produces engine-based valuations
- [ ] GMFAProposalEngine uses engine for offers
- [ ] TradeService uses engine for player valuation
- [ ] Existing tests still pass
- [ ] Integration tests verify end-to-end flow
- [ ] Unit tests pass (target: 20 tests)

---

### Tollgate 9: UI Integration (Optional)

**Objective:** Surface valuation breakdown in UI for transparency.

**Tasks:**
1. Add valuation breakdown to contract proposal dialogs
2. Show GM style influence explanation
3. Show pressure level indicator
4. Add "How is this valued?" tooltip/expansion

**Files:**
- `game_cycle_ui/dialogs/signing_dialog.py` (modify)
- `game_cycle_ui/dialogs/contract_details_dialog.py` (modify)
- `game_cycle_ui/widgets/valuation_breakdown_widget.py` (new)

**Acceptance Criteria:**
- [ ] Proposal dialogs show valuation breakdown
- [ ] GM style explanation visible
- [ ] Pressure level visible with explanation
- [ ] Factor contributions shown as breakdown
- [ ] Expandable detail for full audit trail

---

## Testing Strategy

### Test Categories

| Category | Count | Description |
|----------|-------|-------------|
| Unit Tests - Models | 20 | Dataclass validation, serialization |
| Unit Tests - Factors | 40 | Each factor's calculation logic |
| Unit Tests - GM Influence | 15 | Weight calculation, style mapping |
| Unit Tests - Pressure | 25 | Modifier effects, stacking |
| Integration Tests - Engine | 20 | Full engine orchestration |
| Benchmark Tests | 15 | Comparison to NFL contracts |
| Service Integration | 20 | Existing service updates |
| **Total** | **155** | |

### Benchmark Validation Targets

| Metric | Target | Description |
|--------|--------|-------------|
| Elite Player AAV | ±10% | Top-tier players match market |
| Average Starter AAV | ±15% | Mid-tier players match market |
| Contract Years | ±1 year | Length matches age/position |
| Guaranteed % | ±10% | Guarantees match tier |
| GM Style Variance | 10-20% | Different GMs produce different values |
| Pressure Effect | 10-15% | Hot seat causes visible overpay |

---

## Dependencies

**Required:**
- Milestone 4: Statistics (player stats data)
- Milestone 13: Owner Review (owner directives, job security)
- GMArchetype system (`src/team_management/gm_archetype.py`)

**Optional:**
- Milestone 7: Advanced Analytics (enhanced scouting grades)
- Milestone 10: Awards System (awards factor for valuation)

---

## Extension Points

The architecture supports easy addition of new factors:

### Adding a New Factor

```python
# src/contract_valuation/factors/injury_risk_factor.py

class InjuryRiskFactor(ValueFactor):
    """Adjusts value based on injury history."""

    @property
    def factor_name(self) -> str:
        return "injury_risk"

    def calculate(self, player, context) -> FactorResult:
        injury_history = player.get("injury_history", [])
        games_missed = sum(i.get("games_missed", 0) for i in injury_history)

        # Calculate risk discount
        if games_missed > 16:
            multiplier = 0.75  # 25% discount
        elif games_missed > 8:
            multiplier = 0.90  # 10% discount
        else:
            multiplier = 1.0

        return FactorResult(
            name=self.factor_name,
            raw_value=multiplier,  # This is a multiplier factor
            confidence=0.70,
            breakdown={"games_missed_3yr": games_missed, "multiplier": multiplier}
        )

# Register in engine:
engine = ContractValuationEngine(
    factors=[..., InjuryRiskFactor()],  # Just add to list
    ...
)
```

### Future Factor Ideas
- **Awards Factor** - MVP, All-Pro boost value
- **Clutch Factor** - Playoff performance premium
- **Leadership Factor** - Captain/team chemistry value
- **Scheme Fit Factor** - How well player fits team's scheme
- **Media/Marketing Factor** - Jersey sales, market size

---

## Success Metrics

- [ ] Valuation engine produces realistic NFL-comparable contracts
- [ ] Different GM styles produce measurably different valuations (10-20% variance)
- [ ] Pressure effects visible (hot seat GMs overpay by 10-15%)
- [ ] Full audit trail available for every valuation
- [ ] Benchmark harness validates against real NFL contracts
- [ ] Average deviation from NFL benchmarks < 15%
- [ ] All 155 tests passing
- [ ] Existing FA/re-signing/trade flows use new engine

---

## Summary

Milestone 14 transforms contract generation from a simple rating lookup to a sophisticated multi-factor valuation system. Key innovations:

1. **Factor-Based Architecture** - Stats, scouting, market, and rating factors each contribute independently
2. **GM Personality-Driven Weighting** - Analytics GMs vs. scout GMs produce different valuations
3. **Dynamic Owner Pressure** - Job security and win-now urgency affect contract aggressiveness
4. **Full Audit Trail** - Every valuation includes complete breakdown for debugging and benchmarking
5. **Extensible Design** - New factors can be added without modifying existing code

This creates a more realistic simulation where:
- Player performance drives contract value
- GM personality affects team-building strategy
- Owner pressure creates realistic desperation behavior
- Contracts can be validated against real NFL data
