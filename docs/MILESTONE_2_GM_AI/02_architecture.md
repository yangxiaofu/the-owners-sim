# Architecture: Unified GM Decision-Making System

**Purpose**: Design a unified GM brain that oversees all roster-building transactions (trades, free agency, draft, roster cuts)

**Design Principle**: **Extend, Don't Refactor** - Add GM personality to existing systems without major architectural changes

---

## 1. Design Philosophy

### 1.1 Core Principle

**"A GM's personality should influence ALL roster decisions consistently, regardless of transaction type."**

**Example**: A "Win-Now" GM should:
- ✅ Overpay for proven veterans in TRADES (currently works)
- ✅ Overpay for proven starters in FREE AGENCY (doesn't work yet)
- ✅ Draft polished, pro-ready rookies vs developmental projects (doesn't work yet)
- ✅ Keep expensive veterans on 53-man roster (doesn't work yet)

### 1.2 Why Extend (Not Refactor)

**Option A: Major Refactor** (NOT RECOMMENDED)
- Create centralized `GMDecisionEngine` class
- Refactor all systems to use unified interface
- **Pros**: Cleaner architecture, single source of truth
- **Cons**: High risk, breaks existing tests, 2-3 week effort

**Option B: Incremental Extension** (RECOMMENDED)
- Keep existing architecture (TransactionAIManager, OffseasonController, etc.)
- Add `gm_archetype` parameter injection to all managers
- Extend `PersonalityModifiers` to support all contexts
- **Pros**: Low risk, incremental changes, maintains backward compatibility
- **Cons**: Some code duplication, less elegant architecture

**Decision**: **Option B** - Proven pattern (trade system works), low risk, fast delivery.

---

## 2. Architectural Layers

### 2.1 Layer Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                           │
│  (OffseasonController, TransactionAIManager, SeasonCycleController) │
│                                                                 │
│  Responsibilities:                                              │
│  - Load GM archetypes via GMArchetypeFactory                    │
│  - Pass GM to decision managers                                 │
│  - Coordinate multi-phase workflows                             │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DECISION MANAGER LAYER                        │
│  (FreeAgencyManager, DraftManager, RosterManager, TradeEvaluator)│
│                                                                 │
│  Responsibilities:                                              │
│  - Accept GMArchetype as constructor parameter                  │
│  - Use TeamNeedsAnalyzer for objective needs                    │
│  - Use MarketValueCalculator for objective values               │
│  - Pass GM + objective values to PersonalityModifiers           │
│  - Make final decisions based on modified values                │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYSIS LAYER (OBJECTIVE)                    │
│         (TeamNeedsAnalyzer, MarketValueCalculator)              │
│                                                                 │
│  Responsibilities:                                              │
│  - Analyze roster composition (needs, depth, age)               │
│  - Calculate fair market value for players/prospects           │
│  - NO GM PERSONALITY (purely objective)                         │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                PERSONALITY MODIFIER LAYER (SUBJECTIVE)           │
│                  (PersonalityModifiers - EXTENDED)               │
│                                                                 │
│  Responsibilities:                                              │
│  - Apply GM trait-based multipliers (0.5x - 2.0x)               │
│  - Context-specific modifiers:                                  │
│    • apply_trade_modifier() [EXISTING]                          │
│    • apply_free_agency_modifier() [NEW]                         │
│    • apply_draft_modifier() [NEW]                               │
│    • apply_roster_cut_modifier() [NEW]                          │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                │
│      (GMArchetype, GMArchetypeFactory, TeamContext)             │
│                                                                 │
│  Responsibilities:                                              │
│  - Load GM profiles from config files                           │
│  - Provide GM trait values (0.0-1.0 scales)                     │
│  - Supply team context (record, cap space, roster composition)  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Information Flow

```
1. ORCHESTRATOR loads GM archetype
       ↓
2. DECISION MANAGER receives GM + objective analysis
       ↓
3. ANALYSIS LAYER provides objective values (needs, market value)
       ↓
4. PERSONALITY MODIFIERS apply GM trait multipliers
       ↓
5. DECISION MANAGER makes final decision based on modified values
       ↓
6. ORCHESTRATOR executes transaction (event system)
```

---

## 3. Component Design

### 3.1 GMArchetype (EXISTING - NO CHANGES)

**Location**: `src/team_management/gm_archetype.py`

**Purpose**: Data container for GM personality traits

```python
@dataclass
class GMArchetype:
    """General Manager personality archetype."""

    # 13 personality traits (all 0.0-1.0 continuous scales)
    risk_tolerance: float = 0.5
    win_now_mentality: float = 0.5
    draft_pick_value: float = 0.5
    cap_management: float = 0.5
    trade_frequency: float = 0.5
    veteran_preference: float = 0.5
    star_chasing: float = 0.5
    loyalty: float = 0.5
    desperation_threshold: float = 0.5
    patience_years: int = 5
    deadline_activity: float = 0.5
    premium_position_focus: float = 0.5
    situational_awareness: float = 0.5  # Future use

    # Metadata
    base_archetype_name: str = "Balanced"
    notes: str = ""
```

**NO CHANGES NEEDED** - This is production-ready.

### 3.2 GMArchetypeFactory (EXISTING - NO CHANGES)

**Location**: `src/team_management/gm_archetype_factory.py`

**Purpose**: Factory pattern for loading GM profiles

```python
class GMArchetypeFactory:
    """Factory for creating GMArchetype instances."""

    @staticmethod
    def create_for_team(team_id: int) -> GMArchetype:
        """Create GM archetype for specific team."""
        # 1. Load team profile (src/config/gm_profiles/team_XX_*.json)
        # 2. Load base archetype template
        # 3. Apply team-specific customizations
        # 4. Return GMArchetype instance
```

**NO CHANGES NEEDED** - This is production-ready.

### 3.3 PersonalityModifiers (EXTENDED)

**Location**: `src/transactions/personality_modifiers.py`

**Current State**: 11 trade-specific modifiers

**Extension Plan**: Add 3 new context-specific modifier methods

```python
class PersonalityModifiers:
    """GM personality-based value modifiers for all transaction types."""

    # ===== EXISTING TRADE MODIFIERS (NO CHANGES) =====

    @staticmethod
    def apply_trade_modifier(
        asset_value: float,
        asset_type: str,
        gm: GMArchetype,
        team_context: TeamContext
    ) -> float:
        """Apply GM personality modifiers to trade asset value."""
        # ... existing 11 modifiers ...
        return modified_value

    # ===== NEW FREE AGENCY MODIFIERS =====

    @staticmethod
    def apply_free_agency_modifier(
        player: Player,
        market_value: Dict,
        gm: GMArchetype,
        team_context: TeamContext
    ) -> Dict:
        """Apply GM personality modifiers to free agent contract value.

        Args:
            player: Free agent player object
            market_value: Objective market value dict {'aav': X, 'years': Y, ...}
            gm: GM archetype with personality traits
            team_context: Team situation (record, cap space, needs)

        Returns:
            Modified contract value dict with GM perception applied
        """
        modified_value = market_value.copy()

        # 1. Win-Now Modifier (proven starters)
        if gm.win_now_mentality > 0.5 and player.overall >= 80:
            multiplier = 1.0 + (gm.win_now_mentality - 0.5) * 0.8  # 1.0x - 1.4x
            modified_value['aav'] *= multiplier

        # 2. Cap Management Modifier (expensive contracts)
        if player.overall < 85:  # Non-elite player
            cap_discipline = gm.cap_management
            multiplier = 1.0 - (cap_discipline * 0.4)  # 1.0x - 0.6x
            modified_value['aav'] *= multiplier

        # 3. Veteran Preference Modifier (age factor)
        if player.age >= 30:
            if gm.veteran_preference > 0.5:
                multiplier = 1.0 + (gm.veteran_preference - 0.5) * 0.4  # 1.0x - 1.2x
            else:
                multiplier = 1.0 - ((0.5 - gm.veteran_preference) * 0.4)  # 0.8x - 1.0x
            modified_value['aav'] *= multiplier

        # 4. Star Chasing Modifier (elite free agents)
        if player.overall >= 90:
            multiplier = 1.0 + (gm.star_chasing * 0.5)  # 1.0x - 1.5x
            modified_value['aav'] *= multiplier

        # 5. Risk Tolerance Modifier (injury history)
        if player.injury_prone:
            if gm.risk_tolerance < 0.5:
                multiplier = 1.0 - ((0.5 - gm.risk_tolerance) * 0.6)  # 0.7x - 1.0x
                modified_value['aav'] *= multiplier

        return modified_value

    # ===== NEW DRAFT MODIFIERS =====

    @staticmethod
    def apply_draft_modifier(
        prospect: Player,
        draft_position: int,
        gm: GMArchetype,
        team_context: TeamContext
    ) -> float:
        """Apply GM personality modifiers to draft prospect value.

        Args:
            prospect: Draft prospect player object
            draft_position: Pick number (1-262)
            gm: GM archetype with personality traits
            team_context: Team situation

        Returns:
            Modified prospect value (0.0-100.0 scale)
        """
        base_value = prospect.overall  # Start with overall rating

        # 1. Risk Tolerance Modifier (ceiling vs floor)
        ceiling = prospect.potential  # Max potential rating
        floor = prospect.overall      # Current rating
        upside = ceiling - floor

        if upside > 10:  # High-ceiling prospect
            if gm.risk_tolerance > 0.5:
                multiplier = 1.0 + (gm.risk_tolerance - 0.5) * 0.4  # 1.0x - 1.2x
                base_value *= multiplier
            else:
                multiplier = 1.0 - ((0.5 - gm.risk_tolerance) * 0.2)  # 0.9x - 1.0x
                base_value *= multiplier

        # 2. Win-Now Modifier (polished vs raw)
        if prospect.age >= 23:  # Older, pro-ready prospect
            multiplier = 1.0 + (gm.win_now_mentality * 0.3)  # 1.0x - 1.3x
            base_value *= multiplier

        # 3. Premium Position Focus
        if prospect.position in ['QB', 'EDGE', 'LT']:
            multiplier = 1.0 + (gm.premium_position_focus * 0.3)  # 1.0x - 1.3x
            base_value *= multiplier

        # 4. Veteran Preference (age factor)
        if prospect.age >= 24:  # Older prospect
            multiplier = 1.0 + (gm.veteran_preference * 0.2)  # 1.0x - 1.2x
            base_value *= multiplier

        return base_value

    # ===== NEW ROSTER CUT MODIFIERS =====

    @staticmethod
    def apply_roster_cut_modifier(
        player: Player,
        objective_value: float,
        gm: GMArchetype,
        team_context: TeamContext
    ) -> float:
        """Apply GM personality modifiers to roster cut decision.

        Args:
            player: Player being evaluated for cut
            objective_value: Objective player value score (0-100)
            gm: GM archetype with personality traits
            team_context: Team situation

        Returns:
            Modified player value (higher = more likely to keep)
        """
        modified_value = objective_value

        # 1. Loyalty Modifier (tenure bonus)
        years_with_team = player.years_with_team
        if years_with_team >= 5:
            multiplier = 1.0 + (gm.loyalty * 0.4)  # 1.0x - 1.4x
            modified_value *= multiplier

        # 2. Cap Management Modifier (expensive contracts)
        if player.cap_hit > 5_000_000:  # Expensive player
            if gm.cap_management > 0.7:  # Cap-conscious
                multiplier = 0.8  # Discount expensive players
                modified_value *= multiplier

        # 3. Veteran Preference (age factor)
        if player.age >= 30:
            if gm.veteran_preference > 0.5:
                multiplier = 1.0 + (gm.veteran_preference - 0.5) * 0.4  # 1.0x - 1.2x
            else:
                multiplier = 1.0 - ((0.5 - gm.veteran_preference) * 0.4)  # 0.8x - 1.0x
            modified_value *= multiplier

        return modified_value
```

### 3.4 FreeAgencyManager (MODIFIED)

**Location**: `src/offseason/free_agency_manager.py`

**Changes Required**:

1. Add `gm_archetype` parameter to constructor
2. Use `PersonalityModifiers.apply_free_agency_modifier()` in signing decisions

```python
class FreeAgencyManager:
    """Manages free agency operations with GM personality integration."""

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        gm_archetype: Optional[GMArchetype] = None  # NEW PARAMETER
    ):
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.gm = gm_archetype  # Store GM archetype

        # Existing utilities
        self.team_needs_analyzer = TeamNeedsAnalyzer(database_path, dynasty_id)
        self.market_value_calculator = MarketValueCalculator()

    def simulate_free_agency_day(self, current_date: date) -> List[Dict]:
        """Simulate one day of free agency for all AI teams."""

        for team_id in range(1, 33):
            # 1. Load team-specific GM
            gm = GMArchetypeFactory.create_for_team(team_id)

            # 2. Analyze team needs (objective)
            needs = self.team_needs_analyzer.analyze_team_needs(team_id)

            # 3. Get available free agents
            free_agents = self._get_available_free_agents()

            # 4. Find best FA for highest need
            best_fa = self._find_best_fa_for_need(free_agents, needs[0])

            # 5. Calculate objective market value
            market_value = self.market_value_calculator.calculate(best_fa)

            # 6. Apply GM personality modifiers (NEW)
            team_context = self._get_team_context(team_id)
            modified_value = PersonalityModifiers.apply_free_agency_modifier(
                player=best_fa,
                market_value=market_value,
                gm=gm,
                team_context=team_context
            )

            # 7. Sign if willing to pay modified value
            if team_cap_space >= modified_value['aav']:
                self._sign_free_agent(team_id, best_fa, modified_value)
```

### 3.5 DraftManager (MODIFIED)

**Location**: `src/offseason/draft_manager.py`

**Changes Required**:

1. Implement `simulate_draft()` (currently NotImplementedError)
2. Add `gm_archetype` parameter to constructor
3. Use `PersonalityModifiers.apply_draft_modifier()` in prospect evaluation

```python
class DraftManager:
    """Manages draft operations with GM personality integration."""

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        gm_archetype: Optional[GMArchetype] = None  # NEW PARAMETER
    ):
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.gm = gm_archetype  # Store GM archetype

    def simulate_draft_round(
        self,
        round_number: int,
        draft_order: List[int]
    ) -> List[DraftPick]:
        """Simulate one round of the draft."""

        picks = []

        for pick_number, team_id in enumerate(draft_order, start=1):
            # 1. Load team-specific GM
            gm = GMArchetypeFactory.create_for_team(team_id)

            # 2. Get draft board (objective)
            prospects = self._get_available_prospects()

            # 3. Analyze team needs (objective)
            needs = self.team_needs_analyzer.analyze_team_needs(team_id)

            # 4. Apply GM personality modifiers (NEW)
            team_context = self._get_team_context(team_id)

            best_prospect = None
            best_value = 0

            for prospect in prospects:
                # Calculate modified value based on GM traits
                modified_value = PersonalityModifiers.apply_draft_modifier(
                    prospect=prospect,
                    draft_position=pick_number,
                    gm=gm,
                    team_context=team_context
                )

                # Boost value if prospect fills critical need
                if prospect.position == needs[0].position:
                    modified_value *= 1.3

                if modified_value > best_value:
                    best_value = modified_value
                    best_prospect = prospect

            # 5. Make selection
            pick = self._make_draft_selection(team_id, pick_number, best_prospect)
            picks.append(pick)

        return picks
```

### 3.6 RosterManager (MODIFIED)

**Location**: `src/offseason/roster_manager.py`

**Changes Required**:

1. Add `gm_archetype` parameter to constructor
2. Use `PersonalityModifiers.apply_roster_cut_modifier()` in cut decisions

```python
class RosterManager:
    """Manages roster operations with GM personality integration."""

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        gm_archetype: Optional[GMArchetype] = None  # NEW PARAMETER
    ):
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.gm = gm_archetype  # Store GM archetype

    def execute_roster_cuts(self, team_id: int) -> List[Dict]:
        """Cut roster from 90 to 53 players."""

        # 1. Load team-specific GM
        gm = GMArchetypeFactory.create_for_team(team_id)

        # 2. Calculate objective player values
        player_values = self._calculate_player_values(team_id)

        # 3. Apply GM personality modifiers (NEW)
        team_context = self._get_team_context(team_id)

        for player_value in player_values:
            player = player_value['player']
            objective_value = player_value['value']

            # Apply GM trait modifiers
            modified_value = PersonalityModifiers.apply_roster_cut_modifier(
                player=player,
                objective_value=objective_value,
                gm=gm,
                team_context=team_context
            )

            player_value['value'] = modified_value

        # 4. Sort by modified value
        ranked_players = sorted(player_values, key=lambda x: x['value'], reverse=True)

        # 5. Keep top 53 (based on GM-modified values)
        keepers = ranked_players[:53]
        cuts = ranked_players[53:]

        return cuts
```

---

## 4. Integration Patterns

### 4.1 Orchestrator Pattern (OffseasonController)

**Current State**: OffseasonController does NOT load GM archetypes

**New State**: Load GM and pass to all managers

```python
class OffseasonController:
    """Orchestrates full offseason with GM personality integration."""

    def simulate_ai_full_offseason(self, user_team_id: int) -> Dict:
        """Run complete AI offseason for all 31 non-user teams."""

        for team_id in range(1, 33):
            if team_id == user_team_id:
                continue  # Skip user team

            # 1. Load team-specific GM archetype (NEW)
            gm = GMArchetypeFactory.create_for_team(team_id)

            # 2. Franchise tag phase
            self._simulate_franchise_tags(team_id, gm)

            # 3. Free agency phase (pass GM)
            fa_manager = FreeAgencyManager(
                database_path=self.database_path,
                dynasty_id=self.dynasty_id,
                gm_archetype=gm  # NEW
            )
            fa_manager.simulate_free_agency()

            # 4. Draft phase (pass GM)
            draft_manager = DraftManager(
                database_path=self.database_path,
                dynasty_id=self.dynasty_id,
                gm_archetype=gm  # NEW
            )
            draft_manager.simulate_draft()

            # 5. Roster cuts phase (pass GM)
            roster_manager = RosterManager(
                database_path=self.database_path,
                dynasty_id=self.dynasty_id,
                gm_archetype=gm  # NEW
            )
            roster_manager.execute_roster_cuts(team_id)
```

### 4.2 Dependency Injection Pattern

**Key Principle**: GM archetype is injected at manager creation, NOT loaded within managers

**Why**:
- Single Responsibility Principle (managers don't manage GM loading)
- Easier testing (can inject mock GMs)
- Consistent pattern across all managers

**Example**:

```python
# GOOD: Orchestrator loads GM, injects into manager
gm = GMArchetypeFactory.create_for_team(team_id)
fa_manager = FreeAgencyManager(database_path, dynasty_id, gm_archetype=gm)

# BAD: Manager loads GM internally
fa_manager = FreeAgencyManager(database_path, dynasty_id, team_id=team_id)
fa_manager._load_gm_internally()  # Violates SRP
```

### 4.3 Optional GM Pattern (Backward Compatibility)

**Key Principle**: GM archetype is OPTIONAL parameter (None = no personality)

**Why**:
- Backward compatibility (existing code doesn't break)
- Testing flexibility (can test with/without GM)
- Graceful degradation (if GM load fails, use objective logic)

**Example**:

```python
def __init__(
    self,
    database_path: str,
    dynasty_id: str,
    gm_archetype: Optional[GMArchetype] = None
):
    self.gm = gm_archetype

def _evaluate_free_agent(self, player, market_value):
    if self.gm is not None:
        # Use GM personality modifiers
        return PersonalityModifiers.apply_free_agency_modifier(...)
    else:
        # Fall back to objective value
        return market_value
```

---

## 5. Cross-Context Consistency

### 5.1 Consistency Requirements

**Problem**: How do we ensure a "Win-Now" GM behaves consistently across trades, FA, draft, cuts?

**Solution**: Shared trait multiplier ranges

**Example**: `win_now_mentality` trait should have similar impact across all contexts

| Context | win_now_mentality Impact |
|---------|------------------------|
| Trades | 1.0x - 1.4x multiplier for proven players (85+ OVR) |
| Free Agency | 1.0x - 1.4x multiplier for proven starters (80+ OVR) |
| Draft | 1.0x - 1.3x multiplier for polished prospects (23+ age) |
| Roster Cuts | (Not directly applicable - loyalty/cap more relevant) |

### 5.2 Validation Tests

**Cross-Context Consistency Tests**:

1. **Win-Now GM Test**:
   - Should overpay for veterans in BOTH trades AND free agency
   - Should draft pro-ready rookies over high-ceiling projects
   - Multiplier ranges should be similar (±0.1x tolerance)

2. **Rebuilder GM Test**:
   - Should stockpile draft picks in trades
   - Should sign only value free agents (discounted contracts)
   - Should draft high-ceiling, developmental prospects

3. **Draft Hoarder GM Test**:
   - Should refuse to trade 1st round picks
   - Should assign high value to picks in trade evaluations
   - Should be willing to trade down in draft (acquire more picks)

---

## 6. Data Flow Diagrams

### 6.1 Free Agency Decision Flow

```
┌─────────────────────┐
│ OffseasonController │
└──────────┬──────────┘
           │ 1. Load GM archetype via GMArchetypeFactory
           ↓
┌─────────────────────┐
│ FreeAgencyManager   │
│ (receives GMArchetype)
└──────────┬──────────┘
           │ 2. Analyze team needs (objective)
           ↓
┌─────────────────────┐
│ TeamNeedsAnalyzer   │ → Returns: [QB=CRITICAL, WR=HIGH]
└──────────┬──────────┘
           │ 3. Calculate market value (objective)
           ↓
┌─────────────────────────┐
│ MarketValueCalculator   │ → Returns: $15M AAV for 85 OVR WR
└──────────┬──────────────┘
           │ 4. Apply GM personality modifiers
           ↓
┌─────────────────────────┐
│ PersonalityModifiers    │
│ .apply_free_agency_modifier()
│                         │ → Win-Now GM (0.7): $15M × 1.35 = $20.25M
│                         │ → Rebuilder GM (0.2): $15M × 0.85 = $12.75M
└──────────┬──────────────┘
           │ 5. Make signing decision
           ↓
┌─────────────────────┐
│ FreeAgencyManager   │
│ .sign_free_agent()  │ → Win-Now: Offers $20M (overpays)
└─────────────────────┘ → Rebuilder: Passes (too expensive)
```

### 6.2 Draft Decision Flow

```
┌─────────────────────┐
│ OffseasonController │
└──────────┬──────────┘
           │ 1. Load GM archetype via GMArchetypeFactory
           ↓
┌─────────────────────┐
│ DraftManager        │
│ (receives GMArchetype)
└──────────┬──────────┘
           │ 2. Get draft board (sorted by overall)
           ↓
┌─────────────────────┐
│ DraftManager        │ → Returns: [Prospect A: 78 OVR, Prospect B: 76 OVR]
│ .get_draft_board()  │
└──────────┬──────────┘
           │ 3. Apply GM personality modifiers to each prospect
           ↓
┌─────────────────────────┐
│ PersonalityModifiers    │
│ .apply_draft_modifier() │
│                         │ → Risk-Tolerant GM (0.8):
│                         │    - Prospect A (high floor): 78 × 0.95 = 74.1
│                         │    - Prospect B (high ceiling): 76 × 1.16 = 88.2
│                         │
│                         │ → Conservative GM (0.2):
│                         │    - Prospect A (high floor): 78 × 1.0 = 78.0
│                         │    - Prospect B (high ceiling): 76 × 0.96 = 72.96
└──────────┬──────────────┘
           │ 4. Select best prospect (by modified value)
           ↓
┌─────────────────────┐
│ DraftManager        │
│ .make_selection()   │ → Risk-Tolerant: Picks Prospect B (high ceiling)
└─────────────────────┘ → Conservative: Picks Prospect A (safe pick)
```

---

## 7. Testing Strategy

### 7.1 Unit Tests (Component Level)

**Test PersonalityModifiers in isolation**:

```python
def test_free_agency_modifier_win_now():
    """Win-Now GM should overpay for proven starters."""
    gm = GMArchetype(win_now_mentality=0.9)
    player = Player(overall=85, age=27)
    market_value = {'aav': 15_000_000}

    result = PersonalityModifiers.apply_free_agency_modifier(
        player, market_value, gm, team_context
    )

    assert result['aav'] > 15_000_000  # Should overpay
    assert result['aav'] <= 21_000_000  # Max 1.4x multiplier

def test_draft_modifier_risk_tolerance():
    """Risk-tolerant GM should value high-ceiling prospects."""
    gm = GMArchetype(risk_tolerance=0.9)
    prospect = Player(overall=70, potential=90)  # High ceiling

    result = PersonalityModifiers.apply_draft_modifier(
        prospect, draft_position=15, gm=gm, team_context
    )

    # Should boost value due to high risk tolerance + high ceiling
    assert result > 70  # Modified value > base overall
```

### 7.2 Integration Tests (System Level)

**Test full free agency simulation**:

```python
def test_free_agency_personality_differentiation():
    """Different GMs should make different FA decisions."""

    # Setup: Same FA market, different GMs
    fa_market = [...list of available free agents...]

    # Win-Now GM
    gm_win_now = GMArchetype(win_now_mentality=0.9, cap_management=0.3)
    fa_manager_win_now = FreeAgencyManager(..., gm_archetype=gm_win_now)
    signings_win_now = fa_manager_win_now.simulate_free_agency()

    # Rebuilder GM
    gm_rebuild = GMArchetype(win_now_mentality=0.2, cap_management=0.9)
    fa_manager_rebuild = FreeAgencyManager(..., gm_archetype=gm_rebuild)
    signings_rebuild = fa_manager_rebuild.simulate_free_agency()

    # Assertions:
    # 1. Win-Now should sign more expensive FAs
    assert avg_aav(signings_win_now) > avg_aav(signings_rebuild)

    # 2. Win-Now should sign more veterans
    assert avg_age(signings_win_now) > avg_age(signings_rebuild)

    # 3. Rebuilder should sign more value deals
    assert count_overpays(signings_rebuild) < count_overpays(signings_win_now)
```

### 7.3 Validation Tests (End-to-End)

**Test 32-team offseason simulation**:

```python
def test_gm_personality_consistency_across_contexts():
    """GM should behave consistently in trades, FA, draft."""

    team_id = 9  # Detroit Lions (Win-Now, Draft Hoarder)
    gm = GMArchetypeFactory.create_for_team(team_id)

    # Run full offseason
    controller = OffseasonController(...)
    results = controller.simulate_ai_full_offseason(user_team_id=1)

    lions_results = results[team_id]

    # Assertions:
    # 1. Should refuse to trade 1st round picks (draft_pick_value=0.9)
    assert count_first_round_picks_traded(lions_results['trades']) == 0

    # 2. Should overpay for proven starters in FA (win_now_mentality=0.6)
    assert avg_overpay_percentage(lions_results['fa_signings']) > 10%

    # 3. Should draft pro-ready rookies (win_now_mentality=0.6)
    assert avg_age(lions_results['draft_picks']) > 22.5
```

---

## 8. Migration Path

### 8.1 Backward Compatibility

**Goal**: Zero breaking changes to existing code

**Strategy**:
1. Make `gm_archetype` parameter OPTIONAL (default=None)
2. If None, fall back to objective logic (no personality)
3. Existing tests continue to pass (no GM injection)

### 8.2 Incremental Rollout

**Phase 1**: Free Agency (2 days)
- Extend PersonalityModifiers with FA modifiers
- Update FreeAgencyManager to accept GM
- Update OffseasonController to inject GM

**Phase 2**: Draft (2-3 days)
- Implement draft AI (currently stub)
- Extend PersonalityModifiers with draft modifiers
- Update DraftManager to accept GM

**Phase 3**: Roster Cuts (1 day)
- Extend PersonalityModifiers with cut modifiers
- Update RosterManager to accept GM

**Phase 4**: Validation (1 day)
- Run 32-team offseason simulations
- Validate personality differentiation
- Tune multiplier ranges if needed

---

## 9. Success Criteria

### 9.1 Functional Requirements

- [ ] FreeAgencyManager accepts GMArchetype parameter
- [ ] DraftManager accepts GMArchetype parameter
- [ ] RosterManager accepts GMArchetype parameter
- [ ] PersonalityModifiers has 3 new methods (FA, draft, cuts)
- [ ] OffseasonController injects GM to all managers

### 9.2 Behavioral Requirements

- [ ] Win-Now GMs overpay for veterans in FA (measured by AAV variance)
- [ ] Rebuilder GMs sign only value deals (measured by overpay %)
- [ ] Risk-tolerant GMs draft high-ceiling prospects (measured by potential)
- [ ] Conservative GMs draft safe picks (measured by floor ratings)
- [ ] Loyal GMs keep veterans in roster cuts (measured by tenure)

### 9.3 Quality Requirements

- [ ] 100% test coverage for new PersonalityModifiers methods
- [ ] Zero regression in existing trade system tests
- [ ] Cross-context consistency validated (Win-Now behaves similarly in FA and trades)
- [ ] 32-team offseason simulation produces distinct GM behaviors

---

## Next Steps

See **03_implementation_plan.md** for step-by-step development guide.
