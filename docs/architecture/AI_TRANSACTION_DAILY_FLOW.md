# AI Transaction Daily Flow

## Simple Overview

**Every day during the regular season, all 32 NFL teams evaluate potential trades automatically.**

The system uses:
- GM archetypes (risk-averse, aggressive, balanced, etc.)
- Team needs (CRITICAL, HIGH, MEDIUM positions)
- Trade value calculations (player ratings, age, contract)
- Probability system (most days return 0 trades - realistic NFL behavior)

---

## Daily Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User/UI advances day in season                              │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────────────────────────┐
│ 2. SeasonCycleController.advance_day()                         │
│    (src/season/season_cycle_controller.py:381)                 │
│                                                                 │
│    • Simulates games for the day                               │
│    • Updates standings                                         │
│    • Checks if REGULAR_SEASON phase                            │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────────────────────────┐
│ 3. _evaluate_ai_transactions() [REGULAR SEASON ONLY]           │
│    (src/season/season_cycle_controller.py:2890)                │
│                                                                 │
│    • Checks if trades allowed (before Week 9 deadline)         │
│    • Initializes TransactionAIManager (lazy init)              │
│    • Loops through all 32 teams                                │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────────────────────────┐
│ 4. FOR EACH TEAM (1-32):                                       │
│    TransactionAIManager.evaluate_daily_transactions()          │
│    (src/transactions/transaction_ai_manager.py:398)            │
│                                                                 │
│    STEP A: Assess team situation                               │
│      • Get team needs (TeamNeedsAnalyzer)                      │
│      • Get cap space (CapDatabaseAPI)                          │
│      • Get GM archetype (personality traits)                   │
│      • Get team record (wins, losses)                          │
│                                                                 │
│    STEP B: Probability check                                   │
│      • Base: 5% per day * GM trade_frequency                   │
│      • Modifiers:                                              │
│        - Playoff push: +50% if in wild card hunt (weeks 10+)   │
│        - Losing streak: +25% per game (3+ game streak)         │
│        - Trade cooldown: -80% for 7 days after trade           │
│        - Deadline proximity: +100% final 3 days before Week 9  │
│      • Most days → return [] (no trades)                       │
│                                                                 │
│    STEP C: Generate trade proposals [IF probability passed]    │
│      • TradeProposalGenerator.generate_trade_proposals()       │
│        (src/transactions/trade_proposal_generator.py:171)      │
│                                                                 │
│        1. Filter needs → CRITICAL and HIGH only                │
│        2. Scan all 32 teams for players matching needs         │
│        3. Calculate trade values for targets                   │
│        4. Identify surplus assets on own roster                │
│        5. Find fair-value combinations (0.80-1.20 ratio)       │
│        6. Validate cap compliance                              │
│        7. Sort by need urgency                                 │
│                                                                 │
│    STEP D: GM philosophy filtering                             │
│      • Star chasing: Filter by player overall rating           │
│      • Veteran preference: Filter by age                       │
│      • Cap management: Enforce cap consumption limits          │
│      • Win-now vs rebuild: Filter by team strategy             │
│                                                                 │
│    STEP E: Final validation                                    │
│      • Cap compliance: Both teams have space                   │
│      • Roster minimums: Both teams keep 53+ players            │
│      • No duplicate players                                    │
│      • Contract years remaining > 0                            │
│      • Fairness range: 0.80-1.20 ratio                         │
│                                                                 │
│    STEP F: Prioritization                                      │
│      • Sort by need urgency (CRITICAL > HIGH)                  │
│      • Then by fairness (closer to 1.0)                        │
│      • Then by simplicity (fewer assets)                       │
│      • Limit to max 2 proposals per team per day               │
│                                                                 │
│    RETURN: 0-2 trade proposals (most days: 0)                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────────────────────────┐
│ 5. Execute approved proposals                                  │
│    (season_cycle_controller.py:2930-2970)                      │
│                                                                 │
│    FOR EACH PROPOSAL:                                          │
│      • Get receiving team's GM archetype                       │
│      • Evaluate from receiving team's perspective              │
│        (TradeEvaluator.evaluate_proposal)                      │
│      • If ACCEPT:                                              │
│        - Update player rosters (swap players)                  │
│        - Log transaction to database                           │
│        - Record in trade history (for cooldown)                │
│      • If REJECT/COUNTER:                                      │
│        - Log rejection reason                                  │
│        - Move to next proposal                                 │
│                                                                 │
│    RETURN: List of executed trades                             │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────────────────────────┐
│ 6. Log to database                                             │
│    (src/persistence/transaction_logger.py)                     │
│                                                                 │
│    INSERT INTO player_transactions:                            │
│      • transaction_type: 'TRADE'                               │
│      • player_id, player_name, position                        │
│      • from_team_id → to_team_id                               │
│      • transaction_date                                        │
│      • details: JSON with trade assets, values                 │
│      • dynasty_id: for multi-save isolation                    │
│                                                                 │
│    Each player in trade gets separate transaction record       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. TransactionAIManager
**Location**: `src/transactions/transaction_ai_manager.py`

**Purpose**: Central orchestrator for AI-driven in-season transactions

**Key Responsibilities**:
- Probability system (5% base per day, modified by situation)
- Team assessment (needs, cap space, GM archetype, record)
- Cooldown tracking (7 days after trade before next evaluation)
- Performance metrics (evaluation count, proposal count, avg time)

**Key Method**: `evaluate_daily_transactions(team_id, current_date, season_phase, team_record, current_week)`
- Returns: List of 0-2 trade proposals (most days: empty list)

**Configuration**:
```python
BASE_EVALUATION_PROBABILITY = 0.05  # 5% per day baseline
MAX_TRANSACTIONS_PER_DAY = 2        # Maximum proposals per team per day
TRADE_COOLDOWN_DAYS = 7             # Days after trade before next evaluation
TRADE_DEADLINE_WEEK = 9             # NFL trade deadline (Week 9 Tuesday)

# Probability Modifiers
MODIFIER_PLAYOFF_PUSH = 1.5         # +50% if in wild card hunt (weeks 10+)
MODIFIER_LOSING_STREAK = 1.25       # +25% per game in 3+ game losing streak
MODIFIER_POST_TRADE_COOLDOWN = 0.2  # -80% for 7 days after trade
MODIFIER_DEADLINE_PROXIMITY = 2.0   # +100% in final 3 days before deadline
```

### 2. TradeProposalGenerator
**Location**: `src/transactions/trade_proposal_generator.py`

**Purpose**: Generates realistic trade proposals based on team needs

**Key Responsibilities**:
- Scan all 32 teams for players matching needs
- Calculate trade values using TradeValueCalculator
- Identify surplus assets on own roster
- Construct fair-value packages (0.80-1.20 ratio)
- Validate cap compliance

**Key Method**: `generate_trade_proposals(team_id, gm_archetype, team_context, needs, season)`
- Returns: List of 0-5 trade proposals

**Example Process**:
1. Filter needs → CRITICAL and HIGH only (e.g., "Need starting QB")
2. Scan league → Find QBs with OVR 82+ on other teams
3. Calculate values → QB worth 500 points, have CB worth 480 points
4. Construct proposal → Trade CB + 3rd round pick for QB (fair 1.04 ratio)
5. Validate cap → Both teams have $5M+ cap space after trade
6. Sort → CRITICAL needs first, then best fairness ratio

### 3. TradeEvaluator
**Location**: `src/transactions/trade_evaluator.py`

**Purpose**: Evaluates incoming trade offers from receiving team's perspective

**Key Responsibilities**:
- Calculate perceived value ratio (with GM personality modifiers)
- Determine decision: ACCEPT, REJECT, or COUNTER
- Generate reasoning and confidence score
- Apply GM archetype filters (star chasing, veteran preference, etc.)

**Decision Thresholds**:
```python
VERY_UNFAIR_THRESHOLD = 0.70      # Below this: REJECT
SLIGHTLY_UNFAIR_THRESHOLD = 0.85  # 0.70-0.85: Maybe REJECT (depends on GM)
FAIR_THRESHOLD = 1.15             # 0.85-1.15: ACCEPT (if needs match)
SLIGHTLY_UNFAIR_UPPER = 1.30      # 1.15-1.30: ACCEPT if desperate
# Above 1.30: ACCEPT immediately (getting great deal)
```

### 4. TeamNeedsAnalyzer
**Location**: `src/offseason/team_needs_analyzer.py`

**Purpose**: Analyzes team roster depth and identifies position needs

**Key Responsibilities**:
- Compare roster depth to position minimums
- Calculate urgency levels (CRITICAL, HIGH, MEDIUM, LOW, NONE)
- Identify surplus positions (trade candidates)

**Example Output**:
```python
[
    {
        "position": "quarterback",
        "urgency": NeedUrgency.CRITICAL,  # Only 1 QB on roster
        "urgency_score": 5,
        "current_depth": 1,
        "minimum_depth": 2,
        "deficit": 1
    },
    {
        "position": "wide_receiver",
        "urgency": NeedUrgency.HIGH,      # 4 WRs, need 5
        "urgency_score": 4,
        "current_depth": 4,
        "minimum_depth": 5,
        "deficit": 1
    }
]
```

### 5. GMArchetype
**Location**: `src/team_management/gm_archetype.py`

**Purpose**: Defines GM personality traits for realistic trade behavior

**Key Traits** (0.0-1.0 scale):
```python
@dataclass
class GMArchetype:
    name: str
    description: str

    # Trade behavior traits
    risk_tolerance: float       # 0.0=risk-averse, 1.0=aggressive
    win_now_mentality: float    # 0.0=rebuild, 1.0=championship push
    draft_pick_value: float     # 0.0=undervalue picks, 1.0=overvalue picks
    cap_management: float       # 0.0=reckless, 1.0=conservative
    trade_frequency: float      # 0.0=rarely trade, 1.0=active trader
    veteran_preference: float   # 0.0=prefer youth, 1.0=prefer veterans
    star_chasing: float         # 0.0=avoid big names, 1.0=chase stars
    loyalty: float              # 0.0=ruthless, 1.0=loyal to players
```

**Example Archetypes**:
```python
# Ultra-Conservative GM (Bill Belichick style)
GMArchetype(
    name="The Patriot Way",
    risk_tolerance=0.2,
    win_now_mentality=0.5,
    draft_pick_value=0.8,      # Values picks highly
    cap_management=0.9,        # Very conservative with cap
    trade_frequency=0.3,       # Rarely trades
    veteran_preference=0.7,    # Prefers proven veterans
    star_chasing=0.3,          # Avoids big contracts
    loyalty=0.8                # Loyal to team leaders
)

# Aggressive Win-Now GM (Los Angeles Rams style)
GMArchetype(
    name="All In",
    risk_tolerance=0.9,
    win_now_mentality=0.95,    # Championship or bust
    draft_pick_value=0.2,      # Willing to trade picks
    cap_management=0.3,        # Aggressive with cap
    trade_frequency=0.8,       # Active trader
    veteran_preference=0.8,    # Prefers proven talent
    star_chasing=0.9,          # Chase elite players
    loyalty=0.3                # Willing to trade anyone
)
```

---

## When Do AI Transactions Run?

### Phase Restrictions
**ONLY during REGULAR_SEASON phase**

- **Preseason**: No AI transactions (teams evaluating rosters)
- **Regular Season (Weeks 1-9)**: AI transactions active
- **Week 10 Tuesday+**: Trade deadline passed, no more trades
- **Playoffs**: No AI transactions (roster freeze)
- **Offseason**: No AI transactions (different transaction types: free agency, draft)

### Daily Probability

**Base Probability**: 5% per day * GM `trade_frequency` trait

Example: GM with `trade_frequency=0.5` → 2.5% chance per day
- Over 120 days: ~3 trade evaluations per season (realistic)

**Modifiers**:
1. **Playoff Push** (+50%): Weeks 10+ if win% between 0.40-0.60
2. **Losing Streak** (+25% per game): 3+ game losing streak
3. **Trade Cooldown** (-80%): 7 days after executing a trade
4. **Deadline Proximity** (+100%): Final 3 days before Week 10 Tuesday

**Example Calculation**:
```python
# Week 9, Tuesday (deadline day)
# Team: 5-7 record (0.417 win%, in playoff hunt)
# GM: trade_frequency=0.6
# Last trade: 10 days ago (no cooldown)

base_prob = 0.05 * 0.6 = 0.03 (3%)

modifiers:
  playoff_push: 1.5  (in hunt)
  deadline: 2.0      (Week 9)

final_prob = 0.03 * 1.5 * 2.0 = 0.09 (9% chance)

random.random() < 0.09  → If True, evaluate trades today
```

---

## Example Trade Proposal Structure

```python
TradeProposal(
    # Teams
    team1_id=7,              # Detroit Lions (proposing team)
    team2_id=23,             # New York Giants (receiving team)

    # Team 1 Assets (Lions send)
    team1_assets=[
        TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=12345,
            player_name="Jamaal Williams",
            position="running_back",
            overall_rating=78,
            age=28,
            years_pro=6,
            contract_years_remaining=2,
            annual_cap_hit=3_000_000,
            total_remaining_guaranteed=1_500_000,
            trade_value=250.0  # Calculated by TradeValueCalculator
        )
    ],
    team1_total_value=250.0,

    # Team 2 Assets (Giants send)
    team2_assets=[
        TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=67890,
            player_name="Dexter Lawrence",
            position="defensive_tackle",
            overall_rating=82,
            age=26,
            years_pro=4,
            contract_years_remaining=3,
            annual_cap_hit=4_500_000,
            total_remaining_guaranteed=6_000_000,
            trade_value=280.0
        )
    ],
    team2_total_value=280.0,

    # Trade Fairness
    value_ratio=0.893,       # 250/280 = 0.893 (team2 perspective)
    fairness_rating=FairnessRating.FAIR,  # 0.85-1.15 range

    # Validation
    passes_cap_validation=True,
    passes_roster_validation=True,
    team1_cap_space_after=15_000_000,
    team2_cap_space_after=12_000_000,

    # Metadata
    initiating_team_id=7,
    proposal_timestamp="2025-10-15 14:30:00"
)
```

---

## Trade Execution Example

### Step 1: Lions Propose Trade
```python
# Lions need DT (CRITICAL), have surplus RB
proposal = generate_trade_proposals(
    team_id=7,  # Lions
    needs=[{"position": "defensive_tackle", "urgency": NeedUrgency.CRITICAL}],
    # ... other params
)
# Returns: [TradeProposal(Lions RB → Giants DT)]
```

### Step 2: Giants Evaluate Offer
```python
decision = evaluate_trade_offer(
    team_id=23,  # Giants
    proposal=proposal,
    current_date="2025-10-15"
)

# Giants GM evaluation:
# - Perceived value ratio: 0.893 (slightly favors Giants)
# - Team needs: Giants need RB (HIGH urgency)
# - GM archetype: Balanced (0.5 risk tolerance)
#
# Decision: ACCEPT
# Reasoning: "Fair value trade that addresses our RB need.
#             Williams is a proven veteran who fits our timeline."
# Confidence: 0.75
```

### Step 3: Execute Trade
```python
# Update rosters
move_player(player_id=12345, from_team=7, to_team=23)  # Williams → Giants
move_player(player_id=67890, from_team=23, to_team=7)  # Lawrence → Lions

# Log transactions
log_transaction(
    dynasty_id="user_dynasty",
    season=2025,
    transaction_type="TRADE",
    player_id=12345,
    player_name="Jamaal Williams",
    from_team_id=7,
    to_team_id=23,
    transaction_date="2025-10-15",
    details={
        "trade_partner": "New York Giants",
        "assets_received": ["Dexter Lawrence"],
        "assets_sent": ["Jamaal Williams"],
        "value_ratio": 0.893
    }
)

log_transaction(
    # ... same for Dexter Lawrence
)

# Record in trade history (for cooldown)
record_trade_execution(team_id=7, current_date="2025-10-15")
record_trade_execution(team_id=23, current_date="2025-10-15")

# Both teams now in 7-day trade cooldown
```

### Step 4: Database Records
```sql
SELECT * FROM player_transactions
WHERE transaction_type = 'TRADE'
AND transaction_date = '2025-10-15';

-- Result:
-- transaction_id | dynasty_id    | season | transaction_type | player_id | player_name      | from_team_id | to_team_id | details
-- 1001           | user_dynasty  | 2025   | TRADE            | 12345     | Jamaal Williams  | 7            | 23         | {"trade_partner":"New York Giants",...}
-- 1002           | user_dynasty  | 2025   | TRADE            | 67890     | Dexter Lawrence  | 23           | 7          | {"trade_partner":"Detroit Lions",...}
```

---

## Why Most Days Return 0 Trades

**Realistic NFL Behavior**:
- NFL teams typically make 2-5 trades per season
- Most trades happen near trade deadline (Week 9)
- Trades require:
  - Matching needs between both teams
  - Fair value balance
  - Cap space availability
  - GM personalities aligned
  - Contract years remaining

**System Design**:
- Base 5% daily probability × 0.5 GM trait = 2.5% per day
- 120 regular season days × 2.5% = ~3 trade evaluations per team per season
- Each evaluation generates 0-2 proposals
- Each proposal has ~40-60% acceptance rate (GM filters)
- **Result**: ~1-3 trades executed per team per season (realistic)

**Trade Frequency Breakdown**:
```
32 teams × 120 days = 3,840 team-days per season

With 2.5% daily evaluation rate:
  3,840 × 0.025 = 96 trade evaluations per season

With 50% proposal generation rate (have needs + targets):
  96 × 0.5 = 48 proposals generated

With 50% acceptance rate (fair value + GM alignment):
  48 × 0.5 = 24 trades executed per season

Average: 24 trades / 32 teams = 0.75 trades per team per season

Real NFL average: ~60 trades per season = 1.875 trades per team
(Our system is slightly conservative but realistic)
```

---

## Code Locations Summary

| Component | File | Line(s) |
|-----------|------|---------|
| Daily AI transaction caller | `src/season/season_cycle_controller.py` | 381-480 (advance_day) |
| AI transaction evaluation | `src/season/season_cycle_controller.py` | 2890-2990 (_evaluate_ai_transactions) |
| Transaction AI manager | `src/transactions/transaction_ai_manager.py` | 398-490 (evaluate_daily_transactions) |
| Trade proposal generator | `src/transactions/trade_proposal_generator.py` | 171-263 (generate_trade_proposals) |
| Trade evaluator | `src/transactions/trade_evaluator.py` | Full file |
| Team needs analyzer | `src/offseason/team_needs_analyzer.py` | Full file |
| GM archetype definitions | `src/team_management/gm_archetype.py` | Full file |
| Transaction logger | `src/persistence/transaction_logger.py` | Full file |

---

## Summary

**AI transactions execute automatically every day during regular season (Weeks 1-9).**

**Flow**:
1. User advances day → season_cycle_controller.advance_day()
2. For each team (1-32) → evaluate_daily_transactions()
3. Probability check (5% base × modifiers) → Most days: skip
4. If evaluating → Generate 0-2 trade proposals
5. Apply GM filters → Validate cap/roster compliance
6. Send proposals to other teams → TradeEvaluator decides
7. If accepted → Execute trade, log to database, record in history
8. Both teams enter 7-day trade cooldown

**Result**: Realistic NFL trade behavior with 0.75-1.5 trades per team per season, concentrated near trade deadline.
