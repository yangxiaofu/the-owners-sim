# Milestone 2: Salary Cap & Contracts

## Goal
Implement NFL salary cap enforcement and contract management so that roster decisions have financial consequences. Teams must operate within cap constraints during free agency, re-signing, and roster cuts.

---

## Current State (from Milestone 1)

**What exists:**
- Players have `salary` and `contract_years` fields
- Free agency signing (no cap check)
- Re-signing flow (no cap check)
- Roster cuts with dead money display
- Basic contract data in player JSON files

**What's missing:**
- No cap enforcement (can sign anyone)
- No cap space tracking
- No contract structure (just flat salary)
- No franchise/transition tags
- No cap rollover between seasons

---

## NFL Salary Cap Basics (Simplified)

| Concept | Real NFL | Our Implementation |
|---------|----------|-------------------|
| Salary Cap | ~$255M (2024) | Configurable, start at $250M |
| Cap Floor | 89% of cap | Skip for now |
| Dead Money | Guaranteed $ when cut | Remaining guarantees on cut |
| Rollover | Unused cap carries over | Yes, with cap |
| Franchise Tag | 1 per team, top-5 avg salary | Simplified version |

---

## Tollgates

### Tollgate 1: Cap Space Tracking ✅ COMPLETE
- [x] Calculate team cap usage from roster salaries
- [x] Display cap space in UI (Team Info panel)
- [x] Cap space updates when roster changes
- [x] Show cap breakdown: Active roster, Dead money, Available
- [x] **Bonus:** Projected cap space display in Free Agency (updates dynamically as user clicks Sign/Unsign)
- [x] **Bonus:** Centralized theme config (`src/config/ui_theme.json`) for color management

**Success:** UI shows accurate cap space that updates in real-time

---

### Tollgate 2: Contract Structure ✅ COMPLETE
- [x] Contract model: base salary, signing bonus, guarantees, years
- [x] Signing bonus prorates across contract years
- [x] Cap hit = base salary + prorated bonus
- [x] Database schema for contracts table
- [x] **UI:** ContractDetailsDialog shows year-by-year breakdown with dead money projections
- [x] **Integration:** "View" button in Roster Cuts view opens contract details

**Success:** Can view contract details for any player showing cap hit breakdown

---

### Tollgate 3: Cap-Enforced Free Agency ✅ COMPLETE
- [x] Cannot sign player if cap hit exceeds available space (`free_agency_service.py:259`)
- [x] Show "Cannot Afford" indicator in free agency UI (`free_agency_view.py:390-398`)
  - Red AAV text for unaffordable players
  - "Can't Afford" status text in red
  - Disabled Sign button with grayed-out style
  - Tooltip showing required cap vs available cap
  - Dynamic refresh when signing/unsigning changes projected cap
- [x] AI teams respect cap when signing (`free_agency_service.py:388-406`)
- [x] Contract offers based on player value + cap space (`MarketValueCalculator`)

**Success:** Signing blocked when team is over cap; AI makes cap-conscious decisions

---

### Tollgate 4: Cap-Enforced Re-signing ✅ COMPLETE
- [x] Re-sign offers respect remaining cap space (`resign_player()` checks AAV vs cap space)
- [x] Can restructure existing contracts (`ContractManager.restructure_contract()` - backend only)
- [x] Show projected cap hit for re-sign offers (UI shows estimated cap hit)
- [x] Warning when re-signing would put team over cap (UI shows "Can't Afford" + disabled button)
- [x] **Transaction Logging:** All re-signings and releases logged to `player_transactions` table
- [x] **Transaction UI Filter:** Transactions tab with filter dropdown (All/Draft/FA/Tags/Releases/Cuts/Waivers)
- [x] **Bug Fix:** `player_name` data structure mismatch between `get_expiring_contracts()` and `resign_player()`

**Success:** Re-signing respects cap; UI shows affordability indicators ✅

**Implementation:**
- `resigning_service.py:247-260`: Cap validation before contract creation
- `resigning_view.py:371-489`: Affordability tracking with visual indicators

---

### Tollgate 5: Dead Money & Cuts ✅ COMPLETE
- [x] Cutting player accelerates remaining guarantees (`_calculate_cut_cap_impact`)
- [x] Dead money hits current year cap (tracked in `waiver_wire` table)
- [x] Post-June 1 cut option (spread dead money over 2 years)
  - Service: `roster_cuts_service.py:cut_player(use_june_1=True)` splits dead money
  - UI: "June 1" button alongside "Cut" in roster cuts view
  - Handler: Supports both legacy (list of IDs) and new format (list of dicts with `use_june_1`)
- [x] UI shows dead money impact before confirming cut (Roster Cuts view)

**Success:** Cuts show accurate dead money; can choose cut timing ✅

---

### Tollgate 6: Franchise & Transition Tags ✅ COMPLETE
- [x] One franchise tag per team per year (`FranchiseTagService` enforces)
- [x] Tag salary = average of top 5 at position (`TagManager.calculate_franchise_tag_salary`)
- [x] Transition tag = average of top 10 at position (`TagManager.calculate_transition_tag_salary`)
- [x] Tagged players cannot hit free agency (excluded from FA pool)
- [x] Tag salary counts against cap (`CapHelper.validate_franchise_tag`)
- [x] AI teams apply tags (`process_ai_tags()`)

**Success:** Can apply franchise tag during re-signing phase ✅

---

### Tollgate 7: Season Rollover ✅ COMPLETE
- [x] Unused cap space rolls to next season (`CapHelper.calculate_season_rollover()`)
- [x] ~~Cap rollover has maximum (e.g., 30% of cap)~~ Unlimited rollover (real NFL rules)
- [x] New season cap = Base cap + Rollover (`CapHelper.apply_rollover_to_new_season()`)
- [x] Display rollover amount in offseason summary (purple "Cap Rollover" label in Re-signing & Free Agency views)

**Success:** Cap correctly carries over between seasons ✅

**Implementation:**
- `cap_helper.py:492-557`: `calculate_season_rollover()` and `apply_rollover_to_new_season()` methods
- `cap_database_api.py`: `update_team_carryover()` updates `carryover_from_previous` column
- `season_init_service.py:99-104, 275-320`: "Apply Cap Rollover" step in pipeline, processes all 32 teams
- `resigning_view.py:129-143, 400-401`: Cap Rollover display in Re-signing Summary panel
- `free_agency_view.py:142-156, 292-294`: Cap Rollover display in Free Agency Summary panel

---

## Scope

### In Scope
- Salary cap enforcement on all transactions
- Contract structure (base, bonus, guarantees)
- Dead money on cuts
- Franchise/Transition tags
- Cap rollover
- Cap space UI display
- AI cap management

### Out of Scope (Future Milestones)
- Contract extensions mid-season
- Holdouts
- Incentive-based contracts (Pro Bowl bonuses, etc.)
- Tender offers for RFAs
- Compensatory draft picks
- LTIR (Long-Term Injured Reserve) cap relief
- Void years
- Trade cap implications (handled in Trade milestone)

---

## Data Model

### contracts table (new)
```sql
CREATE TABLE contracts (
    id INTEGER PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER,

    -- Contract terms
    total_years INTEGER NOT NULL,
    years_remaining INTEGER NOT NULL,
    total_value INTEGER NOT NULL,  -- Total contract value

    -- Annual breakdown
    base_salary INTEGER NOT NULL,  -- Current year base
    signing_bonus INTEGER DEFAULT 0,  -- Total signing bonus
    signing_bonus_remaining INTEGER DEFAULT 0,  -- Prorated amount left
    guaranteed_money INTEGER DEFAULT 0,  -- Total guarantees
    guaranteed_remaining INTEGER DEFAULT 0,  -- Guarantees left

    -- Cap calculations
    cap_hit INTEGER NOT NULL,  -- Current year cap hit
    dead_money INTEGER DEFAULT 0,  -- If cut today

    -- Status
    is_franchise_tagged BOOLEAN DEFAULT 0,
    is_transition_tagged BOOLEAN DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
```

### team_cap_summary table (new)
```sql
CREATE TABLE team_cap_summary (
    id INTEGER PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,

    -- Cap figures
    cap_limit INTEGER NOT NULL,  -- Total cap for this team/season
    cap_used INTEGER DEFAULT 0,  -- Current cap usage
    cap_available INTEGER DEFAULT 0,  -- Remaining space
    dead_money INTEGER DEFAULT 0,  -- Dead cap
    rollover_from_previous INTEGER DEFAULT 0,  -- Carried over

    -- Tags
    franchise_tag_used BOOLEAN DEFAULT 0,
    transition_tag_used BOOLEAN DEFAULT 0,

    UNIQUE(dynasty_id, team_id, season)
);
```

---

## Files to Create/Modify

### New Files
- `src/salary_cap/cap_calculator.py` - Cap calculations
- `src/salary_cap/contract_service.py` - Contract operations
- `src/salary_cap/tag_service.py` - Franchise/transition tags
- `src/database/contracts_api.py` - Contract database operations
- `game_cycle_ui/views/cap_space_widget.py` - Cap display component

### Modify
- `src/game_cycle/handlers/offseason.py` - Add cap enforcement
- `src/game_cycle/services/free_agency_service.py` - Cap-aware signing
- `game_cycle_ui/views/free_agency_view.py` - Show affordability
- `game_cycle_ui/views/team_info_panel.py` - Add cap display

---

## Success Criteria

**Milestone is COMPLETE when:**
1. Cap space displays accurately for all teams
2. Cannot sign players when over cap
3. AI teams make cap-conscious decisions
4. Cutting players creates appropriate dead money
5. Franchise tag works during re-signing
6. Cap rolls over correctly between seasons
7. Can play multiple seasons without cap issues breaking the game