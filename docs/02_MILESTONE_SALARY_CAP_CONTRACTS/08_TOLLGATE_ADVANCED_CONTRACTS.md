# Tollgate 8: Advanced Contract Realism

## Goal
Implement NFL-realistic contract features including void years, contract extensions, incentive triggers, free agency bidding, and more. This tollgate builds upon the existing contract infrastructure to add advanced cap manipulation mechanics used by real NFL teams.

---

## Current State (Foundation)

### What Already Exists

**Database Schema (`002_salary_cap_schema.sql`):**
- `player_contracts` table: start_year, end_year, contract_years, signing_bonus, guarantees, contract_type
- `contract_year_details` table: per-year base_salary, roster_bonus, workout_bonus, option_bonus, ltbe_incentives, nltbe_incentives, guarantee_type
- `dead_money`, `cap_transactions`, `franchise_tags` tables

**Python Layer:**
- `ContractManager` can create contracts with year-by-year `base_salaries` list (escalating supported)
- `CapCalculator` handles proration, dead money calculations
- `TagManager` exists but `_get_top_position_salaries()` returns hardcoded values

**JSON Format (Preserved - Backward Compatible):**
```json
"contract": {
  "contract_years": 6,
  "annual_salary": 55000000,
  "signing_bonus": 56754000,
  "guaranteed_money": 147000000,
  "cap_hit_2025": 41300000
}
```

### What's Missing
1. Franchise tag calculation from actual DB salaries (not hardcoded)
2. Contract extensions (extend existing deals mid-term)
3. Void year mechanics (spread bonus into fake years)
4. Incentive triggers tied to game stats
5. Auto-escalation clauses
6. Free agency bidding/offer sheets
7. Option year mechanics
8. Injury settlement system

---

## Implementation Phases

### Phase 1: Franchise Tag Auto-Calculation (MVP)

**Goal:** Calculate franchise/transition tags from actual top-5/top-10 position salaries.

**Current Problem:** `TagManager._get_top_position_salaries()` returns hardcoded salary values instead of querying the database for actual cap hits at each position.

#### Schema Changes
```sql
-- Add position to player_contracts for efficient queries
ALTER TABLE player_contracts ADD COLUMN position TEXT;

-- Index for position salary lookups
CREATE INDEX idx_contracts_position_season
ON player_contracts(position, start_year, end_year, is_active);
```

#### Files to Modify
| File | Changes |
|------|---------|
| `src/salary_cap/tag_manager.py` | Fix `_get_top_position_salaries()` to query actual cap hits |
| `src/salary_cap/contract_initializer.py` | Populate position field from player JSON data |

#### Implementation Details
```python
# tag_manager.py - _get_top_position_salaries()
def _get_top_position_salaries(
    self,
    position: str,
    season: int,
    dynasty_id: str,
    top_n: int
) -> List[int]:
    """
    Query actual top N cap hits for position from contract_year_details.
    """
    query = '''
        SELECT cyd.total_cap_hit
        FROM contract_year_details cyd
        JOIN player_contracts pc ON cyd.contract_id = pc.contract_id
        WHERE pc.position = ?
          AND cyd.season_year = ?
          AND pc.dynasty_id = ?
          AND pc.is_active = TRUE
        ORDER BY cyd.total_cap_hit DESC
        LIMIT ?
    '''
    # Execute and return list of cap hits
```

#### AI Support
Add `AITagDecisionService` class:
```python
class AITagDecisionService:
    def should_apply_tag(self, player_info: dict, team_cap: dict) -> Optional[str]:
        """
        Decide if AI should franchise tag a player.
        Returns: None, "EXCLUSIVE", or "NON_EXCLUSIVE"

        Logic:
        - Tag if overall >= 85 and age <= 30
        - Tag QBs more aggressively
        - Consider cap space (tag must fit under cap)
        """
```

#### Success Criteria
- [ ] Franchise tag salary calculated from actual top-5 position salaries in database
- [ ] Transition tag calculated from actual top-10 position salaries
- [ ] Consecutive tag escalators work (120%, 144%)
- [ ] AI teams make intelligent tag decisions

---

### Phase 2: Contract Extensions (MVP)

**Goal:** Extend existing contracts mid-term (convert salary to bonus, add years).

#### Schema Changes
```sql
-- Track extension history on contracts
ALTER TABLE player_contracts ADD COLUMN original_contract_id INTEGER;
ALTER TABLE player_contracts ADD COLUMN is_extension BOOLEAN DEFAULT FALSE;
ALTER TABLE player_contracts ADD COLUMN extension_date DATE;

-- Extension audit trail
CREATE TABLE contract_extensions (
    extension_id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_contract_id INTEGER NOT NULL,
    new_contract_id INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,
    extension_date DATE NOT NULL,
    years_added INTEGER NOT NULL,
    new_money_added INTEGER NOT NULL,
    signing_bonus_added INTEGER NOT NULL,
    cap_savings_year1 INTEGER DEFAULT 0,
    FOREIGN KEY (original_contract_id) REFERENCES player_contracts(contract_id),
    FOREIGN KEY (new_contract_id) REFERENCES player_contracts(contract_id)
);
```

#### Files to Create/Modify
| File | Changes |
|------|---------|
| `src/salary_cap/contract_manager.py` | Add `extend_contract()` method |
| `src/salary_cap/extension_calculator.py` (NEW) | Extension term calculations |
| `src/game_cycle/services/resigning_service.py` | Add extension option to UI workflow |

#### Implementation Details
```python
# contract_manager.py
def extend_contract(
    self,
    contract_id: int,
    years_to_add: int,
    new_money: int,
    signing_bonus: int,
    new_base_salaries: List[int],
    new_guaranteed_amounts: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Extend existing contract by adding years and restructuring.

    Process:
    1. Get current contract and remaining years
    2. Calculate new signing bonus proration across all years (existing + new)
    3. Create new contract record with is_extension=True
    4. Void old contract, link via original_contract_id
    5. Log extension in contract_extensions table

    Returns:
        Dict with new_contract_id, cap_savings, cap_projections
    """
```

```python
# extension_calculator.py (NEW)
class ExtensionCalculator:
    def calculate_extension_terms(
        self,
        current_contract: dict,
        years_to_add: int,
        new_aav: int
    ) -> Dict[str, Any]:
        """
        Calculate optimal extension structure.

        Returns: {
            'total_new_money': int,
            'signing_bonus': int,
            'base_salaries': List[int],
            'cap_savings_year1': int,
            'cap_projections': Dict[int, int]
        }
        """

    def calculate_restructure_into_extension(
        self,
        contract_id: int,
        salary_to_convert: int,
        years_to_add: int
    ) -> Dict[str, Any]:
        """
        Combine restructure + extension in one operation.
        """
```

#### AI Support
```python
class AIExtensionDecisionService:
    def should_offer_extension(self, player_info: dict, contract: dict, cap_projection: dict) -> bool:
        """
        AI decides when to extend players.

        Triggers:
        - Player entering final year of contract
        - Elite player (overall >= 88) with 2+ years left
        - QB with favorable cap structure opportunity
        """
```

#### Success Criteria
- [ ] Can extend existing contracts mid-term
- [ ] Signing bonus properly re-prorated across all years (existing + new)
- [ ] Cap savings calculated and displayed
- [ ] Extension history tracked in audit table
- [ ] AI teams offer extensions to key players

---

### Phase 3: Void Year Mechanics

**Goal:** Spread signing bonus proration into void years beyond contract term.

#### Schema Changes
```sql
ALTER TABLE contract_year_details ADD COLUMN is_void_year BOOLEAN DEFAULT FALSE;
```

#### Key NFL Rules
- Maximum 5 years proration (real + void combined)
- When void year reached, contract auto-terminates
- Remaining proration accelerates as dead money

#### Files to Modify
| File | Changes |
|------|---------|
| `src/salary_cap/cap_calculator.py` | Add `calculate_void_year_proration()` |
| `src/salary_cap/contract_manager.py` | Support void years in contract creation |

#### Implementation Details
```python
# cap_calculator.py
def calculate_void_year_proration(
    self,
    signing_bonus: int,
    real_contract_years: int,
    void_years: int
) -> Tuple[int, int]:
    """
    Calculate proration with void years.

    NFL Rule: Max 5 years proration (real + void combined)

    Example:
        $50M bonus, 3 real years, 2 void years
        Proration = $50M / 5 = $10M/year

    Returns: (annual_proration, total_proration_years)
    """
    total_years = min(real_contract_years + void_years, 5)
    return signing_bonus // total_years, total_years

def process_void_year_expiration(self, contract_id: int, season: int):
    """
    When contract reaches void year:
    1. Check if is_void_year = True for current season
    2. Void the contract
    3. Accelerate remaining proration as dead money
    """
```

#### Success Criteria
- [ ] Can create contracts with void years
- [ ] Proration correctly spreads across real + void years (max 5)
- [ ] Void year expiration triggers automatic contract termination
- [ ] Dead money correctly accelerates remaining bonus
- [ ] AI uses void years strategically for cap manipulation

---

### Phase 4: Incentive Triggers (LTBE/NLTBE)

**Goal:** Tie incentives to actual game performance.

#### Schema Changes
```sql
CREATE TABLE contract_incentives (
    incentive_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,
    season_year INTEGER NOT NULL,

    -- Incentive definition
    incentive_type TEXT NOT NULL CHECK(incentive_type IN ('LTBE', 'NLTBE')),
    category TEXT NOT NULL,  -- 'STATS', 'AWARDS', 'PLAYTIME', 'TEAM_PERFORMANCE'
    trigger_condition TEXT NOT NULL,  -- JSON: {"stat": "passing_yards", "threshold": 4000}
    amount INTEGER NOT NULL,

    -- Status
    is_triggered BOOLEAN DEFAULT FALSE,
    triggered_date DATE,
    actual_value TEXT,  -- JSON: {"passing_yards": 4523}

    FOREIGN KEY (contract_id) REFERENCES player_contracts(contract_id)
);

CREATE INDEX idx_incentives_contract ON contract_incentives(contract_id);
CREATE INDEX idx_incentives_season ON contract_incentives(season_year, dynasty_id);
```

#### Incentive Categories
| Category | Examples |
|----------|----------|
| STATS | passing_yards, rushing_yards, touchdowns, sacks, interceptions |
| PLAYTIME | games_played, games_started, snap_percentage |
| AWARDS | pro_bowl, all_pro |
| TEAM_PERFORMANCE | playoff_appearance, division_winner, super_bowl |

#### Files to Create
| File | Purpose |
|------|---------|
| `src/salary_cap/incentive_processor.py` (NEW) | Evaluate incentives at season end |

#### Implementation Details
```python
class IncentiveProcessor:
    def evaluate_season_end_incentives(self, season: int, dynasty_id: str):
        """
        Called at end of regular season.

        Process:
        1. Query all incentives for season
        2. For each incentive, check trigger condition against stats
        3. Mark triggered incentives
        4. Adjust cap:
           - LTBE triggered: Already counted, no change
           - LTBE not triggered: Credit back to next year
           - NLTBE triggered: Charge to next year cap
           - NLTBE not triggered: No change
        """
```

#### Success Criteria
- [ ] Can define incentives on contracts (LTBE/NLTBE)
- [ ] Incentives evaluated against actual game stats
- [ ] Cap adjustments applied correctly at season end
- [ ] Triggered incentives logged with actual values

---

### Phase 5: Auto-Escalation Clauses

**Goal:** Automatic salary increases based on performance/playtime.

#### Schema Changes
```sql
CREATE TABLE contract_escalators (
    escalator_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,
    trigger_year INTEGER NOT NULL,  -- When escalator can trigger

    -- Escalator definition
    escalator_type TEXT NOT NULL,  -- 'PLAYTIME', 'PERFORMANCE', 'PRO_BOWL'
    trigger_condition TEXT NOT NULL,  -- JSON: {"snap_percentage": 80}
    salary_increase INTEGER NOT NULL,  -- Dollar amount to add
    applies_to_year INTEGER NOT NULL,  -- Which contract year gets increase

    -- Status
    is_triggered BOOLEAN DEFAULT FALSE,
    triggered_date DATE,

    FOREIGN KEY (contract_id) REFERENCES player_contracts(contract_id)
);
```

#### Files to Create
| File | Purpose |
|------|---------|
| `src/salary_cap/escalator_processor.py` (NEW) | Process escalators during offseason |

#### Implementation Details
```python
class EscalatorProcessor:
    def process_offseason_escalators(self, season: int, dynasty_id: str):
        """
        Called during offseason.

        For each escalator where trigger_year = season:
        1. Evaluate trigger condition
        2. If triggered, update contract_year_details for applies_to_year
        3. Recalculate total cap hit for affected year
        """
```

#### Success Criteria
- [ ] Can define escalators on contracts
- [ ] Escalators evaluated during offseason
- [ ] Triggered escalators update future year salaries
- [ ] Cap projections reflect potential escalators

---

### Phase 6: Free Agency Bidding/Offer Sheets

**Goal:** Multi-team bidding system with competing offers.

#### Schema Changes
```sql
CREATE TABLE free_agent_offers (
    offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    player_id INTEGER NOT NULL,

    -- Offering team
    team_id INTEGER NOT NULL,
    offer_date DATE NOT NULL,

    -- Contract terms
    contract_years INTEGER NOT NULL,
    total_value INTEGER NOT NULL,
    signing_bonus INTEGER NOT NULL,
    guaranteed_money INTEGER NOT NULL,
    aav INTEGER NOT NULL,

    -- Offer status
    status TEXT DEFAULT 'PENDING' CHECK(status IN (
        'PENDING', 'ACCEPTED', 'REJECTED', 'WITHDRAWN', 'MATCHED'
    )),
    response_deadline DATE,

    -- For RFA offer sheets
    is_offer_sheet BOOLEAN DEFAULT FALSE,
    original_team_id INTEGER,  -- Team with matching rights

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_offers_player ON free_agent_offers(player_id, season);
CREATE INDEX idx_offers_team ON free_agent_offers(team_id, season);
```

#### Files to Create/Modify
| File | Purpose |
|------|---------|
| `src/game_cycle/services/free_agency_bidding_service.py` (NEW) | Offer submission, evaluation |
| `src/game_cycle/services/free_agency_service.py` | Integrate bidding workflow |

#### Implementation Details
```python
class FreeAgencyBiddingService:
    def submit_offer(
        self,
        player_id: int,
        team_id: int,
        contract_terms: dict
    ) -> int:
        """Submit offer to free agent. Returns offer_id."""

    def get_player_offers(self, player_id: int) -> List[dict]:
        """Get all pending offers for a player."""

    def evaluate_offers(self, player_id: int) -> int:
        """
        AI evaluates all offers for a player.

        Decision factors:
        1. Total money (weight: 40%)
        2. Guaranteed money (weight: 30%)
        3. Team competitiveness (weight: 15%)
        4. Role/playing time (weight: 15%)

        Returns: winning offer_id
        """

    def process_fa_period(self, dynasty_id: str, season: int):
        """
        Run complete FA period simulation.

        Phases:
        1. Legal tampering (top FAs only)
        2. FA opens - all teams submit initial offers
        3. Bidding rounds (3-5 rounds)
        4. Players make decisions
        5. Contracts finalized
        """
```

#### Success Criteria
- [ ] Multiple teams can submit offers to same player
- [ ] Player evaluates all offers and chooses best fit
- [ ] RFA offer sheets work with matching rights
- [ ] Bidding rounds create realistic market dynamics
- [ ] User can compete with AI teams for free agents

---

### Phase 7: Option Year Mechanics

**Goal:** Team/player options to void remaining years.

#### Schema Changes
```sql
ALTER TABLE contract_year_details ADD COLUMN option_type TEXT
    CHECK(option_type IN ('TEAM', 'PLAYER', 'MUTUAL', 'VESTING') OR option_type IS NULL);
ALTER TABLE contract_year_details ADD COLUMN option_deadline DATE;
ALTER TABLE contract_year_details ADD COLUMN option_exercised BOOLEAN;
ALTER TABLE contract_year_details ADD COLUMN vesting_condition TEXT;  -- JSON for vesting options
```

#### Option Types
| Type | Description |
|------|-------------|
| TEAM | Team can decline, player becomes free agent |
| PLAYER | Player can decline, becomes free agent |
| MUTUAL | Either party can decline |
| VESTING | Auto-exercises based on conditions (games played, etc.) |

#### Files to Create
| File | Purpose |
|------|---------|
| `src/salary_cap/option_processor.py` (NEW) | Process options before FA period |

#### Implementation Details
```python
class OptionYearProcessor:
    def process_team_options(self, season: int, dynasty_id: str):
        """
        Process team options before FA period.

        For each contract with team option:
        1. AI evaluates: exercise if player value > salary
        2. If declined, void remaining years (may create dead money)
        """

    def process_vesting_options(self, season: int, dynasty_id: str):
        """
        Auto-vest options based on conditions.

        Common vesting conditions:
        - Games played >= X
        - Snap percentage >= Y%
        - Pro Bowl selection
        """
```

#### Success Criteria
- [ ] Can define option years on contracts
- [ ] Team options evaluated by AI during offseason
- [ ] Player options respected (player makes decision)
- [ ] Vesting options auto-trigger based on conditions
- [ ] Declining options creates appropriate cap impact

---

### Phase 8: Injury Settlement System

**Goal:** Contract termination with offset clauses for injured players.

#### Schema Changes
```sql
CREATE TABLE injury_settlements (
    settlement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,

    settlement_date DATE NOT NULL,
    settlement_amount INTEGER NOT NULL,  -- Lump sum paid
    remaining_guaranteed INTEGER NOT NULL,  -- What was owed
    offset_language BOOLEAN DEFAULT TRUE,  -- Can team offset with new signing?

    -- Cap impact
    dead_money_year1 INTEGER NOT NULL,
    dead_money_year2 INTEGER DEFAULT 0,

    FOREIGN KEY (contract_id) REFERENCES player_contracts(contract_id)
);
```

#### Implementation Details
```python
class InjurySettlementService:
    def calculate_settlement(
        self,
        contract_id: int,
        injury_date: str
    ) -> Dict[str, Any]:
        """
        Calculate settlement terms for injured player.

        Returns: {
            'remaining_guaranteed': int,
            'settlement_amount': int,  # Usually less than guaranteed
            'dead_money_year1': int,
            'dead_money_year2': int,
            'cap_savings': int
        }
        """

    def execute_settlement(
        self,
        contract_id: int,
        settlement_amount: int
    ) -> None:
        """
        Execute injury settlement.
        1. Void contract
        2. Pay settlement
        3. Record dead money
        4. Release player to free agency
        """
```

#### Success Criteria
- [ ] Can initiate injury settlement for player
- [ ] Settlement amount negotiable (fraction of guaranteed)
- [ ] Dead money calculated correctly
- [ ] Offset language tracked (affects dead money if player signs elsewhere)
- [ ] Player released to free agency after settlement

---

## Dependency Graph

```
Phase 1 (Tag Fix) ────────────────────────────────────────┐
                                                          │
Phase 2 (Extensions) ──→ Phase 3 (Void Years)             │
         │                      │                         │
         v                      v                         │
Phase 4 (Incentives) ──→ Phase 7 (Options)               │
         │                                                │
         v                                                │
Phase 5 (Escalators)                                      │
         │                                                │
         v                                                │
Phase 6 (FA Bidding) ──→ Phase 8 (Injury Settlements) ◄──┘
```

**Phases 1-2 (MVP):** No dependencies, start immediately
**Phase 3:** Depends on Phase 2 (extensions use void years)
**Phase 4:** Needs StatsAPI integration (already exists)
**Phase 6:** Independent but benefits from all prior phases

---

## JSON Backward Compatibility

**Strategy: Database is Source of Truth**

| Layer | Behavior |
|-------|----------|
| JSON Files | Unchanged - flat `annual_salary` format preserved |
| `ContractInitializer` | Converts flat JSON → rich database schema at dynasty init |
| Runtime | All advanced features database-only |
| Save/Load | Dynasty state saved in database, JSON is initialization data only |

**No JSON schema changes required.** All advanced contract features live in the database.

---

## Files Summary

### Existing Files to Modify
| File | Changes |
|------|---------|
| `src/salary_cap/tag_manager.py` | Fix `_get_top_position_salaries()` with DB query |
| `src/salary_cap/contract_manager.py` | Add `extend_contract()`, void year support |
| `src/salary_cap/cap_calculator.py` | Void year proration, incentive adjustments |
| `src/salary_cap/contract_initializer.py` | Populate position field |
| `src/game_cycle/services/free_agency_service.py` | Integrate bidding |

### New Files to Create
| File | Purpose |
|------|---------|
| `src/salary_cap/extension_calculator.py` | Extension term calculations |
| `src/salary_cap/incentive_processor.py` | Evaluate incentives at season end |
| `src/salary_cap/escalator_processor.py` | Process escalators during offseason |
| `src/salary_cap/option_processor.py` | Process option years |
| `src/salary_cap/injury_settlement_service.py` | Injury settlement workflow |
| `src/game_cycle/services/free_agency_bidding_service.py` | Offer submission/evaluation |
| `src/database/migrations/008_advanced_contracts.sql` | All schema changes |

---

## Success Criteria (Tollgate Complete)

**Tollgate 8 is COMPLETE when:**
1. Franchise tags calculated from actual database salaries
2. Can extend existing contracts mid-term with proper proration
3. Void years spread bonus and auto-terminate correctly
4. Incentives (LTBE/NLTBE) tied to actual game stats
5. Escalators trigger based on performance conditions
6. Free agency has multi-team bidding with offer sheets
7. Option years work (team, player, vesting)
8. Injury settlements available for career-ending injuries
9. AI teams use all advanced features intelligently
10. All features maintain dynasty isolation
