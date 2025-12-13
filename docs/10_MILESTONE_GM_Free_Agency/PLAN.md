# Milestone 10: GM-Driven Free Agency with Owner Oversight

## Executive Summary

**Objective:** Transform the free agency system from direct owner control to a GM-driven model where the General Manager proposes signings based on their archetype personality, while the owner provides strategic guidance and retains approval authority.

**Vision:** Create an authentic front office experience where:
- Owner sets the strategic vision (philosophy, budget priorities, positional needs)
- GM independently identifies and proposes free agent targets based on their archetype
- Owner receives real-time proposals during FA waves for approval/rejection
- GM's signing decisions are tracked historically for future hiring evaluations
- Owner-GM relationship dynamics affect proposal quality and GM retention

**Key Differentiators from Current System:**
- **From**: Owner directly makes all FA offers
- **To**: GM proposes, Owner approves (delegation with oversight)

**Pattern:** Follows Milestone 09 (Draft Direction) hybrid approach pattern

---

## User Stories

### Pre-Free Agency Phase

**US-1: Set FA Strategy**
> As an Owner, I want to set my free agency philosophy (aggressive/balanced/conservative) and budget priorities before FA begins, so my GM understands my strategic vision.

**Acceptance Criteria:**
- Pre-FA dialog appears before Legal Tampering wave
- Configure FA philosophy: Aggressive (star-chasing), Balanced (best value), Conservative (depth/low-risk)
- Set budget caps by position group (QB, OL, DL, Secondary, Skill positions, etc.)
- Specify priority positions to target
- Settings passed ephemerally to GM proposal engine (no database persistence)

**US-2: Review GM Profile**
> As an Owner, I want to see my GM's archetype traits and historical FA performance before setting guidance, so I can align my expectations with their tendencies.

**Acceptance Criteria:**
- Display GM archetype traits (risk_tolerance, cap_management, star_chasing, veteran_preference)
- Show historical metrics if GM has FA history:
  - Contract Efficiency score (avg AAV vs player performance)
  - Roster Fit Accuracy (% of signings that filled actual needs)
  - Signing Success Rate (approved/proposed ratio, player outcomes)
- Highlight archetype-driven tendencies (e.g., "This GM tends to overpay for veterans")

---

### During Free Agency Waves

**US-3: Receive GM Proposals**
> As an Owner, during FA waves, I want to receive real-time notifications when my GM identifies a signing target, so I can review and approve/reject immediately.

**Acceptance Criteria:**
- GM analyzes available players each wave turn
- Generates proposals based on: archetype + owner guidance + team needs + cap space
- Owner receives modal notification with:
  - Player details (position, age, overall rating, stats)
  - Proposed contract terms (AAV, years, guaranteed, signing bonus)
  - GM's reasoning/pitch (why this player, why these terms)
  - Archetype rationale (how this fits GM's philosophy)
  - Cap impact preview
  - Owner actions: Approve / Reject / Counter-offer

**US-4: Approve Signings**
> As an Owner, I want to approve GM proposals I agree with, so the signing proceeds immediately and my GM feels trusted.

**Acceptance Criteria:**
- Click "Approve" → Offer submitted to player using FAWaveExecutor
- GM relationship score increases slightly (+1-2 points)
- Proposal outcome visible in wave results (signed/rejected by player)
- Transaction logged with `gm_proposed=True` flag

**US-5: Reject Signings**
> As an Owner, I want to reject GM proposals I disagree with, understanding this may affect our relationship, so I maintain control over major roster decisions.

**Acceptance Criteria:**
- Click "Reject" → Offer NOT submitted, cap space preserved
- Optional: Provide rejection reason (dropdown: "Too expensive", "Wrong position", "Player age concerns", "Not a scheme fit", "Other")
- GM morale decreases (-3 to -10 points depending on relationship health)
- Warning shown if rejection rate is high (>50% in last 10 proposals)
- GM frustration tracked (consecutive rejections trigger stronger penalties)

**US-6: Counter-offer**
> As an Owner, I want to suggest alternative contract terms for a GM proposal, giving my GM a chance to negotiate or find a middle ground.

**Acceptance Criteria:**
- Click "Counter-offer" → Edit contract fields (AAV, years, guaranteed)
- GM evaluates counter based on archetype:
  - High cap_management GM likely accepts lower AAV
  - High risk_tolerance GM may push back on reduced guarantees
  - High loyalty GM may accept if it keeps player
- Counter-negotiation dialog shows GM's response:
  - "Acceptable" → Submit revised offer
  - "Push back" → GM explains why original terms needed
  - "Compromise" → GM suggests middle ground
- Outcome affects relationship moderately (±0 to +5 depending on resolution)

---

### Post-Free Agency Phase

**US-7: Review GM Performance**
> As an Owner, after FA concludes, I want to see a summary of my GM's FA performance, so I can evaluate their decision-making quality.

**Acceptance Criteria:**
- Post-FA summary dialog shows:
  - Proposals made vs approved (approval rate %)
  - Total cap spent vs budget guidance
  - Position targets filled (actual needs addressed)
  - Contract efficiency preview (vs market value)
  - Owner-GM relationship health (morale score, frustration level)
- Metrics saved to `gm_transaction_history` for long-term tracking

**US-8: Historical GM Records**
> As an Owner, when hiring a new GM in future seasons, I want to review their historical FA performance from prior teams, so I can make informed hiring decisions.

**Acceptance Criteria:**
- GM hiring screen shows FA history metrics:
  - Contract Efficiency Score (0-100 scale, higher = better value signings)
  - Roster Fit Accuracy (% of signings that filled team needs)
  - Signing Success Rate (% of proposals approved, player performance outcomes)
  - Archetype consistency (does history match stated archetype?)
- Compare multiple GM candidates side-by-side
- Filter history by season, team, FA wave type

---

## Current State Analysis

### Existing Free Agency System (Milestone 8: FA Depth)

**Architecture:**
- **Wave-based system** (`src/game_cycle/services/fa_wave_service.py`)
  - Legal Tampering (3 days, no signings)
  - Wave 1: Elite tier (7 days)
  - Wave 2: Quality tier (7 days)
  - Wave 3: Depth tier (7 days)
  - Post-Draft: Remaining FAs (7 days)
- **FAWaveExecutor** (`src/game_cycle/services/fa_wave_executor.py`)
  - Orchestrates offer submissions, AI turns, wave advancement
  - Returns structured `WaveExecutionResult` dataclass
- **Owner-controlled offers**: User directly submits offers via UI
- **AI offers**: Simple generation for CPU teams (no archetype consideration)

**Current Flow:**
1. User opens FA view for current wave
2. Views available players filtered by tier
3. Manually submits offers (AAV, years, guaranteed, bonus)
4. Clicks "Process Day" or "Process Wave"
5. FAWaveExecutor handles offer resolution, AI offers, signings

**Gaps:**
- No GM personality influence on signing decisions
- No owner strategic guidance mechanism
- No approval workflow for signings
- No GM performance tracking
- AI offers are simplistic (not archetype-driven)

---

## Technical Architecture

### Integration with Existing FA System

**New Flow (Milestone 10):**
```
1. [NEW] Pre-FA guidance dialog appears before Legal Tampering
2. User sets FAGuidance (philosophy, budgets, priorities)
3. User opens FreeAgencyView (sees wave info, available players)
4. User submits offers manually (backward compatibility)
5. User clicks "Process Day" or "Process Wave"
6. FreeAgencyUIController.execute() called
7. BackendStageController.execute_current_stage()
8. OffseasonHandler.handle_free_agency()
9. FAWaveExecutor.execute(...)
   → [NEW] After AI turn, GMFAProposalEngine.generate_proposals()
   → [NEW] Proposals added to handler_data["gm_proposals"]
10. Results returned to UI
11. [NEW] FreeAgencyView detects gm_proposals in results
12. [NEW] GMProposalNotificationDialog appears
13. User approves/rejects/counters each proposal
14. [NEW] Approved proposals → FAWaveExecutor.submit_offer()
15. [NEW] Rejections → GMRelationship.adjust_morale()
16. [NEW] All proposals logged to gm_transaction_history
```

### Data Models

**1. FAGuidance (Ephemeral)**
```python
@dataclass
class FAGuidance:
    """
    Owner's strategic guidance for free agency.

    Ephemeral context - passed UI → Handler → Service.
    Not persisted to database (cleared after FA completion).
    """
    philosophy: FAPhilosophy = FAPhilosophy.BALANCED
    budget_by_position_group: Dict[str, int] = field(default_factory=dict)
    priority_positions: List[str] = field(default_factory=list)
    max_contract_years: int = 5
    max_guaranteed_percent: float = 0.75
```

**2. GMProposal**
```python
@dataclass
class GMProposal:
    """GM's free agent signing proposal for owner approval."""
    proposal_id: str  # UUID
    player_id: int
    player_name: str
    position: str
    age: int
    overall_rating: int

    # Contract terms
    aav: int
    years: int
    guaranteed: int
    signing_bonus: int

    # GM reasoning
    pitch: str
    archetype_rationale: str
    need_addressed: str

    # Context
    cap_impact: int
    remaining_cap_after: int
    tier: str
```

**3. GMRelationship**
```python
@dataclass
class GMRelationship:
    """Tracks owner-GM relationship state during current season."""
    dynasty_id: str
    season: int
    team_id: int
    gm_name: str

    morale: int = 75  # 0-100 scale
    consecutive_rejections: int = 0
    total_proposals: int = 0
    total_approvals: int = 0

    @property
    def approval_rate(self) -> float:
        return self.total_approvals / self.total_proposals if self.total_proposals > 0 else 1.0

    @property
    def morale_tier(self) -> str:
        if self.morale >= 90: return "Excellent"
        elif self.morale >= 70: return "Good"
        elif self.morale >= 50: return "Strained"
        elif self.morale >= 30: return "Poor"
        else: return "Critical"

    @property
    def at_risk_of_leaving(self) -> bool:
        return self.morale < 30
```

---

## Implementation Plan

### Phase 1: MVP - Pre-FA Guidance + Basic Proposals (Week 1-2)

**Objective:** Core proposal flow working end-to-end

**Tasks:**
1. **Data Models** (Day 1-2)
   - Create `FAGuidance` dataclass (src/game_cycle/models/fa_guidance.py)
   - Create `GMProposal` dataclass (src/game_cycle/models/gm_proposal.py)
   - Add `FAPhilosophy` enum

2. **Pre-FA Guidance Dialog** (Day 3-4)
   - Create `FAGuidanceDialog` (game_cycle_ui/dialogs/fa_guidance_dialog.py)
   - Simple form: philosophy dropdown, 3 priority position selects
   - Skip button (use defaults)
   - Trigger before Legal Tampering wave in OffseasonHandler

3. **Basic Proposal Engine** (Day 5-7)
   - Create `GMFAProposalEngine` (src/game_cycle/services/gm_fa_proposal_engine.py)
   - Implement simple scoring: base rating + priority bonus + archetype modifier
   - Generate 1 proposal per wave turn
   - Mock contract terms (market value × random factor)

4. **Proposal Notification Dialog** (Day 8-10)
   - Create `GMProposalNotificationDialog` (game_cycle_ui/dialogs/gm_proposal_notification.py)
   - Display player info, contract terms, GM pitch
   - Approve/Reject buttons only (no counter-offer yet)
   - Wire to FreeAgencyView result handling

5. **Integration** (Day 11-14)
   - Modify OffseasonHandler.handle_free_agency() to:
     - Accept FAGuidance from context
     - Call GMFAProposalEngine after AI turn
     - Return proposals in handler_data
   - Modify FreeAgencyUIController to:
     - Store FAGuidance (ephemeral)
     - Detect gm_proposals in result
     - Show notification dialog
   - Test end-to-end: set guidance → process wave → see proposal → approve → offer submitted

**Testing:**
- Unit test FAGuidance validation
- Unit test GMProposal dataclass
- Unit test basic proposal scoring
- Integration test: guidance → proposal → approval → offer

**Deliverable:** Owner can set philosophy + priorities, GM generates 1 proposal per wave, owner can approve/reject

---

### Phase 2: GM Record Tracking + Morale System (Week 3-4)

**Objective:** Track proposals, calculate metrics, implement relationship dynamics

**Tasks:**
1. **Database Schema** (Day 1-2)
   - Add `gm_transaction_history` table
   - Add `gm_relationships` table
   - Create migration script

2. **GMRecordTracker Service** (Day 3-5)
   - Create `GMRecordTracker` (src/persistence/gm_record_tracker.py)
   - Implement log_proposal()
   - Implement update_signing_outcome()
   - Implement get_gm_history()

3. **GMRelationship Model** (Day 6-7)
   - Create `GMRelationship` dataclass
   - Implement adjust_morale()
   - Implement record_approval() / record_rejection()
   - Implement persistence save/load

4. **Integrate Tracking** (Day 8-10)
   - Modify GMProposalNotificationDialog:
     - Call GMRecordTracker.log_proposal() on approve/reject
     - Call GMRelationship.adjust_morale() based on action
   - Modify FAWaveExecutor:
     - Call GMRecordTracker.update_signing_outcome() after wave resolution

5. **Morale Effects on Proposals** (Day 11-14)
   - Modify GMFAProposalEngine:
     - Accept GMRelationship as parameter
     - Adjust proposal frequency based on morale tier
     - Adjust pitch detail/tone based on morale

**Deliverable:** Proposals logged to database, morale affects proposal frequency/quality

---

### Phase 3: Counter-offers + Performance Metrics (Week 5-6)

**Objective:** Full negotiation flow, contract efficiency calculations

**Tasks:**
1. **Counter-offer Dialog** (Day 1-3)
   - Create `CounterOfferDialog`
   - Editable fields: AAV, years, guaranteed, signing bonus
   - Cap impact preview

2. **GM Counter Evaluation** (Day 4-6)
   - Implement _evaluate_counter_offer() logic
   - Archetype-based acceptance/compromise/pushback

3. **Counter-offer Flow** (Day 7-9)
   - Wire Counter-offer button to dialog
   - Handle GM responses
   - Update morale based on outcome

4. **Performance Metrics** (Day 10-14)
   - Implement calculate_season_performance()
   - Contract Efficiency formula
   - Roster Fit Accuracy formula
   - Signing Success Rate formula

**Deliverable:** Full negotiation flow, performance metrics calculated post-season

---

## Database Schema

```sql
-- Track all GM proposals and outcomes
CREATE TABLE gm_transaction_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    gm_name TEXT NOT NULL,
    team_id INTEGER NOT NULL,

    transaction_type TEXT NOT NULL,  -- 'FA_PROPOSAL', 'TRADE_PROPOSAL', 'DRAFT_PICK'
    transaction_date TEXT NOT NULL,

    -- FA-specific fields
    player_id INTEGER,
    player_name TEXT,
    position TEXT,
    player_age INTEGER,
    player_rating INTEGER,

    proposed_aav INTEGER,
    proposed_years INTEGER,
    proposed_guaranteed INTEGER,
    proposal_reasoning TEXT,

    -- Outcome
    owner_approved BOOLEAN NOT NULL,
    rejection_reason TEXT,
    player_signed BOOLEAN,
    final_aav INTEGER,
    final_years INTEGER,

    -- Performance tracking (updated end-of-season)
    contract_efficiency_score REAL,
    roster_fit_score REAL,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
);

-- Track GM relationship state
CREATE TABLE gm_relationships (
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    gm_name TEXT NOT NULL,

    morale INTEGER NOT NULL DEFAULT 75,
    consecutive_rejections INTEGER NOT NULL DEFAULT 0,
    total_proposals INTEGER NOT NULL DEFAULT 0,
    total_approvals INTEGER NOT NULL DEFAULT 0,
    at_risk_of_leaving BOOLEAN NOT NULL DEFAULT 0,

    PRIMARY KEY (dynasty_id, season, team_id),
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
);
```

---

## Key Services

### GMFAProposalEngine

**Purpose:** Generate GM free agent proposals based on archetype + guidance

**Key Methods:**
- `generate_proposals(team_id, available_players, cap_space, wave) -> List[GMProposal]`
- `_score_candidate(player, needs, cap_space) -> float`
- `_create_proposal(player, score, needs, cap_space) -> GMProposal`

**Scoring Formula:**
```
score = base_value
      + archetype_fit_bonus
      + priority_position_bonus
      + age_fit_bonus
      + scheme_fit_bonus
```

**Archetype Influence:**
| Trait | Effect |
|-------|--------|
| `risk_tolerance: 0.8` | 5-year deals, high guarantees |
| `cap_management: 0.9` | Short contracts, low guarantees |
| `star_chasing: 0.9` | Focus elite tier, top AAV |
| `veteran_preference: 0.8` | Prefer 30+ age players |

---

### GMRecordTracker

**Purpose:** Track GM transaction history for performance evaluation

**Key Methods:**
- `log_proposal(proposal, approved, rejection_reason) -> int`
- `update_signing_outcome(player_id, season, signed, final_aav, final_years)`
- `calculate_season_performance(gm_name, season) -> Dict[str, float]`
- `get_gm_history(gm_name) -> List[Dict]`

**Performance Metrics:**
1. **Contract Efficiency (0-100):** (Player Performance / AAV) × Scale Factor
2. **Roster Fit Accuracy (0-100):** % of signings that filled actual needs
3. **Signing Success Rate (0-100):** (Approvals / Proposals) × (Signings / Approvals) × 100

---

## File Structure

### New Files

```
docs/10_MILESTONE_GM_Free_Agency/
  PLAN.md

src/game_cycle/models/
  fa_guidance.py
  gm_proposal.py
  gm_relationship.py

src/game_cycle/services/
  gm_fa_proposal_engine.py

src/persistence/
  gm_record_tracker.py

game_cycle_ui/dialogs/
  fa_guidance_dialog.py
  gm_proposal_notification.py
  counter_offer_dialog.py
  reject_reason_dialog.py
  gm_hiring_dialog.py

tests/game_cycle/services/
  test_gm_fa_proposal_engine.py

tests/persistence/
  test_gm_record_tracker.py
```

### Modified Files

```
src/game_cycle/handlers/offseason.py
  - Load GMRelationship at FA start
  - Extract FAGuidance from context
  - Call GMFAProposalEngine after AI turn
  - Return gm_proposals in handler_data

src/game_cycle/database/schema.sql
  - Add gm_transaction_history table
  - Add gm_relationships table

game_cycle_ui/controllers/free_agency_controller.py
  - Add fa_guidance attribute
  - Add gm_relationship attribute
  - Handle gm_proposals in results

game_cycle_ui/views/free_agency_view.py
  - Add signal: gm_proposals_received(list)
  - Detect gm_proposals in result
```

---

## Testing Strategy

**Unit Tests (40+ tests):**
- GMFAProposalEngine scoring logic (15 tests)
- GMRecordTracker CRUD operations (10 tests)
- GMRelationship morale calculations (8 tests)
- Data model validation (7 tests)

**Integration Tests (12 tests):**
- End-to-end FA flow (guidance → proposal → approval → signing)
- Morale system effects on proposal frequency
- Performance metrics calculation
- GM resignation trigger

**UI Tests (8 tests):**
- Dialog display and interaction
- Signal/slot connections
- Data binding correctness

---

## Success Metrics

**Feature Adoption:**
- 80%+ users set FA guidance at least once per season
- 60%+ users approve at least 1 GM proposal per FA period
- < 5% users consistently reject all proposals

**Engagement:**
- Average 2-3 proposals generated per FA wave
- Average approval rate: 50-70%
- Counter-offer used in 20-30% of proposals

**Data Quality:**
- 95%+ proposals logged correctly
- 90%+ signing outcomes updated correctly
- 100% performance metrics calculable for completed seasons

---

## Risks & Mitigation

**Risk 1: Proposal Quality Inconsistency**
- Mitigation: Extensive testing, iterative tuning of weights

**Risk 2: Morale System Too Punishing**
- Mitigation: Generous thresholds, gradual penalties, warning messages

**Risk 3: Performance Metrics Inaccurate**
- Mitigation: Multiple metric dimensions, placeholder scores when data insufficient

**Risk 4: Backward Compatibility**
- Mitigation: FAGuidance optional, manual offers still work, proposals additive

**Risk 5: UI Complexity**
- Mitigation: Clear instructions, breadcrumb navigation, cancel always available

---

## Dependencies

**Required:**
- Milestone 8: FA Depth (wave system, FAWaveExecutor)
- GMArchetype system (src/team_management/gm_archetype.py)
- Game Cycle architecture

**Optional:**
- Milestone 9: Draft Direction (pattern reference)
- Milestone 6: Trade System (consistency)

---

## Rollback Plan

**Emergency Disable:**
- Add config flag `ENABLE_GM_PROPOSALS = False`
- Reverts to manual offer-only flow
- No database rollback needed

**Partial Disable:**
- `ENABLE_COUNTER_OFFERS = False`
- `ENABLE_MORALE_SYSTEM = False`
- `ENABLE_PRE_FA_GUIDANCE = False`

---

## Summary

Milestone 10 transforms Free Agency from direct control to GM-Owner collaboration. Key innovations:

1. **Archetype-Driven Proposals:** GM personality influences targets and terms
2. **Real-Time Approval:** Owner stays engaged without micromanaging
3. **Historical Accountability:** GM decisions tracked for future hiring
4. **Dynamic Relationships:** Morale system adds consequence to interactions

**Implementation:** 4 phases over 6-8 weeks
**Pattern:** Follows Draft Direction hybrid guidance model
**Impact:** Completes Owner delegation vision - hire GM, set strategy, approve moves
