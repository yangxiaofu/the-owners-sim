# Trade System - Implementation Plan

## Overview

A comprehensive trade system for The Owners Sim that enables player and draft pick trading between teams, with multi-round counter-offer negotiation, AI GM decision-making, and full salary cap compliance.

## Design Decisions (User-Confirmed)

| Decision | Choice |
|----------|--------|
| Trade Windows | Preseason + Regular Season (Weeks 1-9) + Offseason |
| Trade Deadline | Week 9 (NFL standard) |
| Assets | Players + Draft Picks (current + 2 future years) |
| User Control | Full UI - propose, review, negotiate |
| Negotiation | Multi-round counter-offers (up to 3 rounds) |

## Progress Summary

| Tollgate | Status | Tests |
|----------|--------|-------|
| 1. Database Schema & TradeService Foundation | ✅ COMPLETE | 28/28 |
| 2. Single-Player Trade Execution | ✅ COMPLETE | 9/9 |
| 3. AI Trade Decision & Counter-Offers | ✅ COMPLETE | 12/12 |
| 4. Draft Pick Trading | ✅ COMPLETE | 13/13 |
| 5. Trade Stage Integration | ✅ COMPLETE | - |
| 6. Trade UI - Propose & Review | ✅ COMPLETE | TradingView (read-only history) |
| 7. Main Window Integration & Polish | ✅ COMPLETE | Deadline indicator + read-only TradingView |

**Total Tests: 62 passing** (TradeService comprehensive coverage)

### 🎉 MILESTONE COMPLETE

All 7 tollgates implemented:
- AI GM-managed trades (user does not directly propose)
- AI evaluation with accept/reject/counter decisions
- Draft pick trading with ownership tracking
- Trade deadline countdown in status bar (weeks 7-9)
- TradingView shows trade history (read-only)
- Offseason trading stage integration

**Note:** User-initiated trades deferred to #27 (Front Office Direction) where Owner directs GM.

---

## Current State Assessment

### What Already Exists (80% Reusable)

| Component | File | Status | Reusability |
|-----------|------|--------|-------------|
| Trade Value Calculator | `src/transactions/trade_value_calculator.py` | ✅ Complete | 100% - Jimmy Johnson chart, player valuation |
| Trade Evaluator | `src/transactions/trade_evaluator.py` | ✅ Complete | 100% - GM decision-making with confidence |
| Trade Proposal Generator | `src/transactions/trade_proposal_generator.py` | ✅ Complete | 95% - AI proposal generation |
| Data Models | `src/transactions/models.py` | ✅ Complete | 100% - TradeProposal, TradeDecision, TradeAsset, DraftPick |
| Personality Modifiers | `src/transactions/personality_modifiers.py` | ✅ Complete | 100% - All trait modifiers |
| Transaction Constants | `src/transactions/transaction_constants.py` | ✅ Complete | 100% - TRADE_DEADLINE_WEEK=9 |
| Trade Events | `src/events/trade_events.py` | ⚠️ Partial | PlayerForPlayerTradeEvent works, DraftTradeEvent placeholder |

### What Needs to Be Built

| Component | Description | Complexity |
|-----------|-------------|------------|
| `TradeService` | Game Cycle service orchestrator | Medium |
| `CounterOfferGenerator` | Multi-round negotiation logic | Medium |
| Database tables | `trades`, `draft_pick_ownership` | Low |
| Trade stage definitions | Add to `StageType` enum | Low |
| Trade UI views | 3 views (propose, review, history) | High |

---

## Trade Windows Architecture

```
PRESEASON
    → Trading enabled

REGULAR SEASON (Week 1-9)
    → Trading enabled
    → Trade deadline: After Week 9

REGULAR SEASON (Week 10-18)
    → No trades allowed

PLAYOFFS
    → No trades allowed

OFFSEASON
    → OFFSEASON_FRANCHISE_TAG
    → OFFSEASON_RE-SIGNING
    → OFFSEASON_FREE_AGENCY
    → OFFSEASON_TRADING ← NEW (after FA, before Draft)
    → OFFSEASON_DRAFT
    → OFFSEASON_ROSTER_CUTS
    → OFFSEASON_WAIVER_WIRE
    → OFFSEASON_TRAINING_CAMP
```

---

## Tollgate 1: Database Schema & TradeService Foundation ✅ COMPLETE

**Goal**: Create database tables for trade persistence and `TradeService` class following game cycle service patterns.

### 1.1 Database Schema Additions

**File:** `src/game_cycle/database/schema.sql`

```sql
-- Trade tracking table
CREATE TABLE IF NOT EXISTS trades (
    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    trade_date TEXT NOT NULL,
    team1_id INTEGER NOT NULL,
    team2_id INTEGER NOT NULL,
    team1_assets TEXT NOT NULL,  -- JSON array of TradeAsset
    team2_assets TEXT NOT NULL,  -- JSON array of TradeAsset
    team1_total_value REAL NOT NULL,
    team2_total_value REAL NOT NULL,
    value_ratio REAL NOT NULL,
    fairness_rating TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'rejected', 'countered')),
    initiating_team_id INTEGER NOT NULL,
    rounds_negotiated INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
);

-- Draft pick ownership tracking
CREATE TABLE IF NOT EXISTS draft_pick_ownership (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL CHECK(round BETWEEN 1 AND 7),
    original_team_id INTEGER NOT NULL,
    current_team_id INTEGER NOT NULL,
    acquired_via_trade_id INTEGER,
    UNIQUE(dynasty_id, season, round, original_team_id),
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    FOREIGN KEY (acquired_via_trade_id) REFERENCES trades(trade_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_trades_dynasty_season
    ON trades(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_trades_teams
    ON trades(dynasty_id, team1_id, team2_id);
CREATE INDEX IF NOT EXISTS idx_pick_ownership_team
    ON draft_pick_ownership(dynasty_id, current_team_id, season);
```

### 1.2 TradeService Foundation

**New File:** `src/game_cycle/services/trade_service.py`

```python
class TradeService:
    """Manages all trade-related operations for the game cycle."""

    # Trade window constants
    TRADE_DEADLINE_WEEK = 9  # After Week 9, no more trades

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._transaction_logger = TransactionLogger(db_path)

        # Lazy-loaded calculators
        self._value_calculator = None
        self._needs_analyzer = None

    def is_trade_window_open(self, week: int, phase: str) -> bool:
        """Check if trades are allowed in current phase/week."""
        if phase == "playoffs":
            return False
        if phase == "regular_season" and week > self.TRADE_DEADLINE_WEEK:
            return False
        if phase in ["preseason", "offseason_trading", "regular_season"]:
            return True
        return False

    def get_tradeable_players(self, team_id: int) -> List[Dict]:
        """Get players on a team's roster who can be traded."""
        # Query roster, exclude injured/IR, ensure contract exists

    def get_tradeable_picks(self, team_id: int, max_future_years: int = 2) -> List[Dict]:
        """Get draft picks owned by team (current + future years)."""
        # Query draft_pick_ownership table
```

### 1.3 Acceptance Criteria
- [x] `trades` table created with dynasty isolation
- [x] `draft_pick_ownership` table created
- [x] TradeService initializes with dynasty context
- [x] `is_trade_window_open()` returns True for Weeks 1-9 regular season
- [x] `is_trade_window_open()` returns False for Weeks 10-18
- [x] `is_trade_window_open()` returns False for playoffs
- [x] `get_tradeable_players()` returns roster with contract info
- [x] `get_tradeable_picks()` returns owned picks

**Tests:** 28 passing
- `tests/game_cycle/services/test_trade_service.py`
- `tests/game_cycle/database/test_trade_schema.py`

---

## Tollgate 2: Single-Player Trade Execution ✅ COMPLETE

**Goal**: Enable executing trades for players (no picks yet) and persisting to database.

### 2.1 Trade Proposal

**File:** `src/game_cycle/services/trade_service.py`

```python
def propose_trade(
    self,
    team1_id: int,
    team1_assets: List[Dict],  # [{type: 'player', player_id: 123}, ...]
    team2_id: int,
    team2_assets: List[Dict]
) -> TradeProposal:
    """Create a trade proposal with value calculations."""
    # 1. Convert dicts to TradeAsset objects
    # 2. Calculate values using TradeValueCalculator
    # 3. Determine fairness rating
    # 4. Return populated TradeProposal
```

### 2.2 Trade Execution

```python
def execute_trade(self, proposal: TradeProposal) -> Dict[str, Any]:
    """Execute an accepted trade."""
    # 1. Validate trade is still valid (players still on teams)
    # 2. Update players.team_id for both sides
    # 3. Transfer contracts to new teams
    # 4. Record in trades table
    # 5. Log transactions for audit trail
    # 6. Return success/error status

def _transfer_player_contract(
    self,
    player_id: int,
    from_team_id: int,
    to_team_id: int
) -> None:
    """Transfer a player's contract to new team."""
    # Update player_contracts.team_id
    # Handle any dead money implications
```

### 2.3 Trade History

```python
def get_trade_history(
    self,
    team_id: Optional[int] = None,
    season: Optional[int] = None
) -> List[Dict]:
    """Get completed trades, optionally filtered."""
```

### 2.4 Acceptance Criteria
- [x] Can propose player-for-player trade
- [x] Can execute accepted trade (player rosters update)
- [x] Contracts transfer to new team
- [x] Trade recorded in `trades` table with status='accepted'
- [x] Transaction logged in `player_transactions` table (with graceful fallback)
- [x] Trade history retrievable by team/season

**Tests:** 9 passing
- `tests/game_cycle/services/test_trade_service.py` (extended)

---

## Tollgate 3: AI Trade Decision & Counter-Offers ✅ COMPLETE

**Goal**: AI teams can evaluate proposals and generate counter-offers using existing evaluator.

### 3.1 AI Trade Evaluation

**File:** `src/game_cycle/services/trade_service.py`

```python
def evaluate_ai_trade(
    self,
    proposal: TradeProposal,
    ai_team_id: int
) -> TradeDecision:
    """Have AI team evaluate a trade proposal."""
    # 1. Get GMArchetype for AI team
    # 2. Build TeamContext from standings/cap
    # 3. Call existing TradeEvaluator.evaluate_proposal()
    # 4. Return decision with reasoning
```

### 3.2 Counter-Offer Generator

**New File:** `src/game_cycle/services/counter_offer_generator.py`

```python
class CounterOfferGenerator:
    """Generates counter-offers to bridge value gaps in trade negotiations."""

    def __init__(self, trade_service: TradeService):
        self._trade_service = trade_service
        self._value_calculator = TradeValueCalculator(...)

    def generate_counter(
        self,
        original_proposal: TradeProposal,
        decision: TradeDecision,
        countering_team_id: int
    ) -> Optional[TradeProposal]:
        """Generate a counter-offer that bridges the value gap."""
        # 1. Calculate value gap from perceived_value_ratio
        # 2. Find assets to add/remove to reach acceptance threshold
        # 3. Generate new TradeProposal with adjusted assets
        # 4. Return None if gap unbridgeable

    def _find_bridging_assets(
        self,
        team_id: int,
        value_needed: float,
        excluded_player_ids: List[int]
    ) -> List[TradeAsset]:
        """Find assets that can bridge the value gap."""
```

### 3.3 Multi-Round Negotiation

```python
def negotiate_trade(
    self,
    initial_proposal: TradeProposal,
    max_rounds: int = 3
) -> NegotiationResult:
    """Conduct multi-round trade negotiation."""
    # Loop: propose -> evaluate -> counter (if applicable)
    # Track all proposals in history
    # Return final NegotiationResult with:
    #   - success: bool
    #   - final_proposal: TradeProposal (if accepted)
    #   - rounds_taken: int
    #   - termination_reason: ACCEPTED, REJECTED, MAX_ROUNDS, STALEMATE
    #   - history: List[TradeProposal]
```

### 3.4 Acceptance Criteria
- [x] AI evaluates proposals using personality traits (via TradeEvaluator)
- [x] AI returns ACCEPT/REJECT/COUNTER based on value ratio
- [x] Counter-offers handled via existing NegotiatorEngine
- [x] Negotiation terminates after max rounds (NegotiatorEngine.MAX_ROUNDS=4)
- [x] `NegotiationResult` captures full history (existing model)
- [x] Stalemate detection when gap unbridgeable (NegotiatorEngine)

**Implementation Note:** Tollgate 3 was primarily an integration task since TradeEvaluator and NegotiatorEngine already exist in `src/transactions/`. Added wrapper methods to TradeService with SoC using StandingsAPI.

**Tests:** 12 passing (3 context, 2 archetype, 5 evaluation, 2 assets)
- `tests/game_cycle/services/test_trade_service.py` (extended)

---

## Tollgate 4: Draft Pick Trading ✅ COMPLETE

**Goal**: Enable trading draft picks alongside or instead of players.

### 4.1 Implementation Summary

**Extended:** `src/game_cycle/services/trade_service.py`

```python
# New methods added:
def _build_pick_assets(pick_ids: List[int], acquiring_team: int) -> List[TradeAsset]
    """Build TradeAsset list from draft pick IDs with calculated values."""

def _get_pick_details(pick_id: int) -> Optional[Dict[str, Any]]
    """Get draft pick details by pick ownership ID."""

def _transfer_draft_pick(conn, pick_id: int, to_team_id: int, trade_id: int) -> Dict
    """Transfer draft pick ownership to new team."""

# Extended methods:
def propose_trade(..., team1_pick_ids: List[int], team2_pick_ids: List[int])
    """Now accepts optional pick parameters alongside players."""

def execute_trade(...)
    """Now handles both player and pick transfers."""

def _validate_trade_assets(...)
    """Now validates both player team membership and pick ownership."""

def _asset_to_dict(...)
    """Now serializes both player and pick assets."""

def _get_tradeable_assets_for_negotiation(team_id, include_picks=True)
    """Now includes draft picks in negotiation asset pool."""
```

### 4.2 Acceptance Criteria
- [x] Can query team's owned picks (current + 2 future years) - via `get_tradeable_picks()`
- [x] Can propose trade with picks only
- [x] Can propose trade with players + picks
- [x] Pick ownership transfers on trade execution
- [x] Future picks valued with 5% annual discount (via `TradeValueCalculator`)
- [x] `draft_pick_ownership` table updated with trade_id on transfer
- [x] AI negotiation includes picks in asset pool

**Tests:** 13 passing (4 proposal + 4 execution + 3 validation + 2 negotiation)
- `tests/game_cycle/services/test_trade_service.py` (extended)

---

## Tollgate 5: Trade Stage Integration ✅ COMPLETE

**Goal**: Add trade stages to game cycle for all trading windows.

### 5.1 Implementation Summary

**Files Modified:**
- `src/game_cycle/stage_definitions.py` - Added `OFFSEASON_TRADING` stage
- `src/game_cycle/handlers/offseason.py` - Added trading execution methods

**Key Changes:**
- Added `OFFSEASON_TRADING = auto()` to `StageType` enum (after FREE_AGENCY, before DRAFT)
- Updated `OFFSEASON_STAGES` list with new stage
- Updated `week_number` property for correct offseason ordering
- Added `_execute_trading()` method to `OffseasonHandler`
- Added `_get_trading_preview()` for UI data
- Added `_process_ai_trades()` helper with 50% AI trade probability

### 5.2 Acceptance Criteria
- [x] `OFFSEASON_TRADING` stage appears after Free Agency, before Draft
- [x] AI teams make trade proposals during trading stages (~50% per team)
- [x] Trade deadline enforced (no trades after Week 9 regular season)
- [x] OffseasonHandler routes to `_execute_trading()` method
- [x] User can skip trading stage (no trades required to advance)

**Tests:** 19 passing
- `tests/game_cycle/handlers/test_trading_stage_integration.py`

---

## Tollgate 6: Trade UI - Propose & Review 🔶 PARTIAL

**Goal**: Create UI for user to propose trades and review AI offers.

### 6.1 TradingView ✅ COMPLETE

**New File:** `game_cycle_ui/views/trading_view.py`

Created a trading stage view with:
- Summary panel (cap space, tradeable players/picks count, trades this season)
- User's tradeable players table (name, position, age, OVR, trade value)
- User's draft picks table (year, round, original team, trade value)
- Trade history table (league-wide, date, teams, summary)
- "Propose Trade" button (emits `propose_trade_requested` signal)

**Integrated into:** `game_cycle_ui/views/offseason_view.py`
- Added TradingView to stacked widget (index 3)
- Added OFFSEASON_TRADING case in `set_stage()`
- Added `propose_trade_requested` signal forwarding
- Added cap validation handler

### 6.2 Trade Proposal Dialog ⏹ NOT STARTED

**Pending File:** `game_cycle_ui/dialogs/trade_proposal_dialog.py`

Needs to be created for:
- Team selector dropdown
- Two-panel asset selection (user assets | target team assets)
- Live trade value calculation
- Fairness indicator (color-coded)
- Submit/Cancel buttons

### 6.3 Counter-Offer Dialog ⏹ NOT STARTED

**Pending File:** `game_cycle_ui/dialogs/counter_offer_dialog.py`

Needs to be created for reviewing AI counter-offers.

### 6.4 Acceptance Criteria
- [x] TradingView displays during OFFSEASON_TRADING stage
- [x] User can see their tradeable players and picks
- [x] Trade history shows completed trades
- [ ] User can select assets from their roster to trade
- [ ] User can select target team and their desired assets
- [ ] Trade value displays in real-time as assets selected
- [ ] Fairness indicator color-coded
- [ ] Counter-offer dialog allows asset adjustment

**Current State:** TradingView shows data but "Propose Trade" button needs dialog implementation

---

## Tollgate 7: Main Window Integration & Polish 🔶 PARTIAL

**Goal**: Integrate trade views into main window with notifications and polish UX.

### 7.1 Offseason Integration ✅ COMPLETE

TradingView automatically displays when game reaches OFFSEASON_TRADING stage:
- Integrated into OffseasonView stacked widget
- `set_stage()` populates trading preview data
- Cap validation connected
- Process button advances to next stage

### 7.2 Pending Items

**Trade Center Toolbar Button** ⏹ NOT STARTED
- Add "Trade Center" button to toolbar for quick access during regular season

**Trade Notifications** ⏹ NOT STARTED
- Toast notifications for trade proposals received
- Notifications for trade completions

**Trade Deadline Countdown** ⏹ NOT STARTED
- Show countdown during Weeks 7-9 regular season

**Validation UI** ⏹ NOT STARTED
- Roster size validation (can't trade below 45 players)
- Cap compliance validation
- Position minimums check

### 7.3 Acceptance Criteria
- [x] Offseason trading stage integrated with offseason view
- [x] TradingView shows during OFFSEASON_TRADING stage
- [x] AI trades execute when stage is processed
- [ ] Trade Center accessible during trade windows (toolbar)
- [ ] "Trade Center" button in toolbar
- [ ] Notifications appear for trade activity
- [ ] Trade deadline countdown visible in Week 8-9
- [ ] Full trading flow works end-to-end (needs proposal dialog)
- [ ] Validation prevents invalid trades

**Current State:** Basic trading stage works but user cannot yet initiate trades (needs dialog)

---

## Dependency Flow

```
Tollgate 1: Database Schema ───────┐
                                   │
Tollgate 2: Player Trading ────────┼──► Tollgate 5: Stage Integration
                                   │
Tollgate 3: AI Counter-Offers ─────┤           │
                                   │           ▼
Tollgate 4: Draft Pick Trading ────┘   Tollgate 6: Trade UI
                                               │
                                               ▼
                                       Tollgate 7: Main Window
```

**Recommended Order**: 1 → 2 → 3 → 4 → 5 → 6 → 7

---

## Code Reuse Summary

### Direct Reuse (No Changes Needed)
- `TradeValueCalculator` - Complete player/pick valuation with Jimmy Johnson chart
- `TradeEvaluator` - GM decision logic with personality modifiers
- `PersonalityModifiers` - All trait modifiers (star_chasing, draft_pick_value, etc.)
- `GMArchetype` - 12 personality traits for AI GMs
- `TradeAsset`, `DraftPick`, `TradeProposal`, `TradeDecision` - Data models
- `TransactionProbability.TRADE_DEADLINE_WEEK` - Constants

### Enhance/Extend
- `TradeProposalGenerator` - Add draft pick proposals to AI logic
- `NegotiationResult` - Populate with multi-round logic
- `StageType` - Add OFFSEASON_TRADING

### Build New
- `TradeService` - Game cycle orchestrator
- `CounterOfferGenerator` - Counter-offer generation logic
- `TradeHandler` - Stage handler
- `DraftPickAPI` - Pick ownership queries
- Trade UI views (3 views + 1 dialog)
- Database tables (trades, draft_pick_ownership)

---

## Files Summary

### New Files to Create
| File | Purpose |
|------|---------|
| `src/game_cycle/services/trade_service.py` | Main trade orchestration service |
| `src/game_cycle/services/counter_offer_generator.py` | Counter-offer logic |
| `src/game_cycle/database/draft_pick_api.py` | Pick ownership queries |
| `src/game_cycle/handlers/trade_handler.py` | Trade stage handler |
| `game_cycle_ui/views/trade_proposal_view.py` | UI for proposing trades |
| `game_cycle_ui/views/trade_review_view.py` | UI for reviewing AI offers |
| `game_cycle_ui/views/trade_history_view.py` | UI for trade history |
| `game_cycle_ui/dialogs/counter_offer_dialog.py` | Counter-offer dialog |
| `tests/game_cycle/services/test_trade_service.py` | Service tests |
| `tests/game_cycle/services/test_counter_offers.py` | Counter-offer tests |
| `tests/game_cycle/services/test_draft_pick_trading.py` | Pick trading tests |
| `tests/game_cycle/handlers/test_trade_handler.py` | Handler tests |
| `tests/game_cycle/database/test_trade_schema.py` | Schema tests |

### Files to Modify
| File | Changes |
|------|---------|
| `src/game_cycle/database/schema.sql` | Add trades and draft_pick_ownership tables |
| `src/game_cycle/stage_definitions.py` | Add OFFSEASON_TRADING stage |
| `src/game_cycle/stage_controller.py` | Add trade handler routing |
| `src/game_cycle/services/__init__.py` | Export TradeService |
| `src/game_cycle/handlers/__init__.py` | Export TradeHandler |
| `src/transactions/trade_proposal_generator.py` | Add draft pick proposals |
| `game_cycle_ui/main_window.py` | Add trade views and connections |
| `game_cycle_ui/views/__init__.py` | Export trade views |

---

## Success Criteria

**Milestone is COMPLETE when:**
1. Users can propose trades to AI teams during trade windows
2. AI teams generate and send trade proposals to user
3. Multi-round counter-offer negotiation works (up to 3 rounds)
4. Draft picks can be traded (current year + 2 future years)
5. Trade deadline enforced (no trades after Week 9)
6. Offseason trading stage works in game cycle flow
7. Trade history persists and displays correctly
8. All AI trades logged in transaction history
9. All 120 tests passing

---

## Testing Strategy

### Unit Tests (~120 total)
- `tests/game_cycle/services/test_trade_service.py` - Core service (35 tests)
- `tests/game_cycle/services/test_counter_offers.py` - Negotiation logic (25 tests)
- `tests/game_cycle/services/test_draft_pick_trading.py` - Pick trades (20 tests)
- `tests/game_cycle/handlers/test_trade_handler.py` - Stage handler (15 tests)
- `tests/game_cycle/database/test_trade_schema.py` - Schema (10 tests)
- UI integration tests (15 tests)

### Integration Tests
- Full season with mid-season trade (user proposes, AI accepts)
- AI-initiated trade with counter-offer negotiation
- Draft pick trade affecting draft order
- Trade deadline enforcement

### Validation Script
`scripts/validate_trade_system.py`
- Simulate 18-week season with AI trades
- Analyze trade value fairness distribution
- Flag unrealistic trades (90+ OVR player for 7th round pick)
- Generate trade activity report

---

## NFL Trade Reference Data

### Trade Deadline
- NFL trade deadline: Tuesday after Week 9
- No trades allowed from Week 10 through end of season
- Players acquired must clear waivers (24 hours)

### Trade Compensation
- Jimmy Johnson Draft Value Chart widely used
- 1st overall pick = 3000 points
- End of 1st round = ~590 points
- 2nd round starts at ~580 points
- 7th round pick = ~2-10 points

### Trade Frequency
- Average NFL trades per season: 20-30 league-wide
- Deadline day often has 5-10 trades
- Most trades involve mid-tier players or draft picks
- Star player trades rare (1-2 per season)
