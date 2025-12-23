# Owner-GM Offseason Flow - Tollgate Plan

> **Vision:** The Owner sets direction at the start of the offseason, then the GM automates decisions with approval checkpoints. This delivers the "You are the Owner" fantasy without tedious transaction-by-transaction management.

## Progress Summary

| Tollgate | Status | Description |
|----------|--------|-------------|
| T1 | ✅ COMPLETE | Owner Review UI (OffseasonDirectiveDialog) |
| T2 | ✅ COMPLETE | Directive Data Model (schema, API, dataclass) |
| T3 | ✅ COMPLETE | GM Proposal System (ProposalAPI, PersistentGMProposal) |
| T4 | ✅ COMPLETE | Approval UI (ProposalReviewDialog, widgets) |
| T5 | ✅ COMPLETE | Franchise Tag Integration |
| T6 | ✅ COMPLETE | Re-signing Integration |
| T7 | ✅ COMPLETE | Free Agency Integration |
| T8 | ✅ COMPLETE | Trade Integration |
| T9 | ✅ COMPLETE | Draft Integration |
| T10 | ✅ COMPLETE | Roster Cuts Integration |
| T11 | ✅ COMPLETE | Waiver Wire Integration |
| T12 | ✅ COMPLETE | End-to-End Testing |

---

## Overview

This milestone unifies elements from multiple planned features (#25 Owner Communication Portal, #29 Front Office Direction, #30 Season Goals, #37 GM Behaviors) into a cohesive offseason experience.

**Key Principles:**
1. Owner is NOT the GM — you set direction, not execute transactions
2. GM proposes, Owner approves — every significant move requires sign-off
3. Automation with oversight — skip the tedium, keep the control
4. Trust GM mode — hands-off option for experienced players

---

## Offseason Stage Mapping

| Stage | Approval Required | Owner Interaction |
|-------|-------------------|-------------------|
| OFFSEASON_HONORS | No | View-only (awards presentation) |
| OFFSEASON_FRANCHISE_TAG | Yes | Approve/reject tag candidate |
| OFFSEASON_RESIGNING | Yes | Approve/reject extension proposals |
| OFFSEASON_FREE_AGENCY | Yes | Approve/reject signing proposals (batched by wave) |
| OFFSEASON_TRADING | Yes | Approve/reject trade proposals |
| OFFSEASON_DRAFT | Yes | Approve/reject draft picks (per-pick or per-round) |
| OFFSEASON_ROSTER_CUTS | Yes | Approve/reject cut proposals |
| OFFSEASON_WAIVER_WIRE | Yes | Approve/reject waiver claims |
| OFFSEASON_TRAINING_CAMP | No | View-only (progression results) |
| OFFSEASON_PRESEASON | No | View-only (game results) |

---

## Tollgate 1: Owner Review UI ✅ COMPLETE

**Goal:** Create the dialog where Owner sets offseason direction and priorities.

**Implementation:**
- `game_cycle_ui/dialogs/offseason_directive_dialog.py` - Main dialog
- `game_cycle_ui/views/owner_view.py` - Owner tab with 3 sections (Summary, Staff, Directives)
- `game_cycle_ui/main_window.py` - Signal handling and stage integration
- Tests at `tests/test_game_cycle/ui/test_offseason_directive_dialog.py`

### Deliverables

1. **OffseasonDirectiveDialog** (`game_cycle_ui/dialogs/offseason_directive_dialog.py`)
   - Team Philosophy selector (Win-Now / Maintain / Rebuild)
   - Budget Stance selector (Aggressive / Moderate / Conservative)
   - Position Priorities list (drag-to-reorder or numbered selection)
   - Protected Players multi-select (players GM should not trade)
   - Expendable Players multi-select (players GM can actively shop)
   - Notes text area (free-form instructions to GM)
   - Trust GM checkbox (skip approval gates)

2. **UI Components**
   ```
   ┌─────────────────────────────────────────────────────────────────┐
   │  OFFSEASON DIRECTION - {SEASON}                                 │
   ├─────────────────────────────────────────────────────────────────┤
   │                                                                 │
   │  TEAM PHILOSOPHY                                                │
   │  ○ Win-Now   ○ Maintain   ○ Rebuild                             │
   │                                                                 │
   │  SPENDING APPROACH                                              │
   │  ○ Aggressive   ○ Moderate   ○ Conservative                     │
   │                                                                 │
   │  POSITION NEEDS (select up to 5)                                │
   │  ┌─────────────────────────────────┐                            │
   │  │ [ ] QB    [ ] RB    [ ] WR      │                            │
   │  │ [ ] TE    [ ] OL    [ ] DL      │                            │
   │  │ [ ] EDGE  [ ] LB    [ ] CB      │                            │
   │  │ [ ] S     [ ] K     [ ] P       │                            │
   │  └─────────────────────────────────┘                            │
   │                                                                 │
   │  PROTECTED PLAYERS (will not be traded)                         │
   │  [Dropdown/Search] [+Add]                                       │
   │  [Player 1] [x]  [Player 2] [x]                                 │
   │                                                                 │
   │  EXPENDABLE PLAYERS (open to trading)                           │
   │  [Dropdown/Search] [+Add]                                       │
   │  [Player 3] [x]                                                 │
   │                                                                 │
   │  NOTES TO GM                                                    │
   │  ┌─────────────────────────────────────────────────────────┐   │
   │  │                                                          │   │
   │  └─────────────────────────────────────────────────────────┘   │
   │                                                                 │
   │  [ ] Trust GM (auto-approve all proposals)                      │
   │                                                                 │
   │         [Cancel]                    [Set Direction →]           │
   │                                                                 │
   └─────────────────────────────────────────────────────────────────┘
   ```

3. **Integration Point**
   - Dialog launches automatically when entering `OFFSEASON_HONORS` stage
   - Or accessible via menu: "Set Offseason Direction"

### Implementation Steps

1. Create `OffseasonDirectiveDialog` class extending `QDialog`
2. Add radio button groups for Philosophy and Budget
3. Add checkbox grid for Position Needs with max selection logic
4. Add player search/select widgets for Protected/Expendable lists
5. Add text area for notes
6. Add Trust GM checkbox
7. Wire up OK/Cancel buttons
8. Emit signal with directive data on accept

### Acceptance Criteria

- [ ] Dialog renders correctly with all components
- [ ] Philosophy and Budget are mutually exclusive radio selections
- [ ] Position Needs allows 0-5 selections
- [ ] Protected/Expendable players are selectable from current roster
- [ ] Same player cannot be in both Protected and Expendable
- [ ] Notes field accepts multi-line text
- [ ] Trust GM checkbox toggles correctly
- [ ] Cancel closes dialog without saving
- [ ] Set Direction emits directive and closes dialog

---

## Tollgate 2: Directive Data Model ✅ COMPLETE

**Goal:** Create database schema and dataclasses for storing owner directives.

**Implementation:**
- `src/game_cycle/models/owner_directives.py` - OwnerDirectives dataclass
- `src/game_cycle/database/owner_directives_api.py` - OwnerDirectivesAPI
- Schema in `src/game_cycle/database/full_schema.sql` (owner_directives table)
- `src/game_cycle/services/owner_service.py` - Service layer integration

### Deliverables

1. **Database Schema** (`src/game_cycle/database/schema/offseason_directives.sql`)
   ```sql
   CREATE TABLE IF NOT EXISTS offseason_directives (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       dynasty_id TEXT NOT NULL,
       season INTEGER NOT NULL,
       philosophy TEXT NOT NULL CHECK (philosophy IN ('WIN_NOW', 'MAINTAIN', 'REBUILD')),
       budget_stance TEXT NOT NULL CHECK (budget_stance IN ('AGGRESSIVE', 'MODERATE', 'CONSERVATIVE')),
       position_priorities TEXT,  -- JSON array: ["EDGE", "WR", "CB"]
       protected_player_ids TEXT, -- JSON array of player IDs
       expendable_player_ids TEXT, -- JSON array of player IDs
       notes TEXT,
       trust_gm INTEGER DEFAULT 0, -- Boolean: 0 = require approval, 1 = auto-approve
       created_at TEXT DEFAULT CURRENT_TIMESTAMP,
       updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
       UNIQUE(dynasty_id, season)
   );
   ```

2. **Enums** (`src/game_cycle/models/directive_enums.py`)
   ```python
   from enum import Enum

   class TeamPhilosophy(Enum):
       WIN_NOW = "WIN_NOW"
       MAINTAIN = "MAINTAIN"
       REBUILD = "REBUILD"

   class BudgetStance(Enum):
       AGGRESSIVE = "AGGRESSIVE"
       MODERATE = "MODERATE"
       CONSERVATIVE = "CONSERVATIVE"
   ```

3. **Dataclass** (`src/game_cycle/models/offseason_directive.py`)
   ```python
   from dataclasses import dataclass, field
   from typing import List, Optional
   from .directive_enums import TeamPhilosophy, BudgetStance

   @dataclass
   class OffseasonDirective:
       dynasty_id: str
       season: int
       philosophy: TeamPhilosophy
       budget_stance: BudgetStance
       position_priorities: List[str] = field(default_factory=list)
       protected_player_ids: List[str] = field(default_factory=list)
       expendable_player_ids: List[str] = field(default_factory=list)
       notes: str = ""
       trust_gm: bool = False
       id: Optional[int] = None
   ```

4. **API Class** (`src/game_cycle/database/directive_api.py`)
   ```python
   class DirectiveAPI:
       def __init__(self, conn: sqlite3.Connection, dynasty_id: str):
           self.conn = conn
           self.dynasty_id = dynasty_id

       def save_directive(self, directive: OffseasonDirective) -> int: ...
       def get_directive(self, season: int) -> Optional[OffseasonDirective]: ...
       def get_current_directive(self) -> Optional[OffseasonDirective]: ...
       def update_directive(self, directive: OffseasonDirective) -> bool: ...
       def delete_directive(self, season: int) -> bool: ...
   ```

### Implementation Steps

1. Create enum file with TeamPhilosophy and BudgetStance
2. Create OffseasonDirective dataclass
3. Add SQL schema to game_cycle database initialization
4. Create DirectiveAPI with CRUD operations
5. Add JSON serialization helpers for list fields
6. Write unit tests for API

### Acceptance Criteria

- [ ] Schema creates table in game_cycle.db
- [ ] Enums serialize/deserialize correctly
- [ ] DirectiveAPI.save_directive() persists data
- [ ] DirectiveAPI.get_directive() retrieves by season
- [ ] DirectiveAPI.get_current_directive() gets latest
- [ ] Duplicate dynasty_id+season fails gracefully (upsert)
- [ ] List fields serialize as JSON arrays
- [ ] Unit tests pass (target: 10+ tests)

---

## Tollgate 3: GM Proposal System ✅ COMPLETE

**Goal:** Create the data model and API for GM proposals that require owner approval.

**Implementation:**
- `src/game_cycle/models/proposal_enums.py` - ProposalType, ProposalStatus enums
- `src/game_cycle/models/persistent_gm_proposal.py` - PersistentGMProposal dataclass
- `src/game_cycle/database/proposal_api.py` - ProposalAPI with CRUD operations
- Schema in `src/game_cycle/database/full_schema.sql` (gm_proposals table)

### Deliverables

1. **Database Schema** (`src/game_cycle/database/schema/gm_proposals.sql`)
   ```sql
   CREATE TABLE IF NOT EXISTS gm_proposals (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       proposal_id TEXT UNIQUE NOT NULL,
       dynasty_id TEXT NOT NULL,
       season INTEGER NOT NULL,
       stage TEXT NOT NULL,
       proposal_type TEXT NOT NULL CHECK (proposal_type IN (
           'FRANCHISE_TAG', 'EXTENSION', 'SIGNING', 'TRADE',
           'DRAFT_PICK', 'CUT', 'WAIVER_CLAIM'
       )),
       subject_player_id TEXT,
       details TEXT NOT NULL, -- JSON object with type-specific data
       gm_reasoning TEXT NOT NULL,
       confidence REAL DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
       status TEXT DEFAULT 'PENDING' CHECK (status IN (
           'PENDING', 'APPROVED', 'REJECTED', 'MODIFIED', 'EXPIRED'
       )),
       owner_notes TEXT,
       priority INTEGER DEFAULT 0, -- For ordering proposals
       created_at TEXT DEFAULT CURRENT_TIMESTAMP,
       resolved_at TEXT,
       FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
   );

   CREATE INDEX idx_proposals_dynasty_status ON gm_proposals(dynasty_id, status);
   CREATE INDEX idx_proposals_stage ON gm_proposals(dynasty_id, stage, status);
   ```

2. **Enums** (`src/game_cycle/models/proposal_enums.py`)
   ```python
   from enum import Enum

   class ProposalType(Enum):
       FRANCHISE_TAG = "FRANCHISE_TAG"
       EXTENSION = "EXTENSION"
       SIGNING = "SIGNING"
       TRADE = "TRADE"
       DRAFT_PICK = "DRAFT_PICK"
       CUT = "CUT"
       WAIVER_CLAIM = "WAIVER_CLAIM"

   class ProposalStatus(Enum):
       PENDING = "PENDING"
       APPROVED = "APPROVED"
       REJECTED = "REJECTED"
       MODIFIED = "MODIFIED"
       EXPIRED = "EXPIRED"
   ```

3. **Dataclass** (`src/game_cycle/models/gm_proposal.py`)
   ```python
   from dataclasses import dataclass, field
   from typing import Dict, Optional, Any
   from datetime import datetime
   from .proposal_enums import ProposalType, ProposalStatus
   from game_cycle.stage_definitions import StageType

   @dataclass
   class GMProposal:
       dynasty_id: str
       season: int
       stage: StageType
       proposal_type: ProposalType
       details: Dict[str, Any]
       gm_reasoning: str
       proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
       subject_player_id: Optional[str] = None
       confidence: float = 0.5
       status: ProposalStatus = ProposalStatus.PENDING
       owner_notes: Optional[str] = None
       priority: int = 0
       created_at: Optional[datetime] = None
       resolved_at: Optional[datetime] = None
       id: Optional[int] = None
   ```

4. **Detail Schemas by Type**
   ```python
   # FRANCHISE_TAG details
   {
       "player_name": str,
       "position": str,
       "tag_type": "exclusive" | "non_exclusive",
       "tag_amount": int,
       "cap_impact": int
   }

   # EXTENSION details
   {
       "player_name": str,
       "position": str,
       "current_contract": {"years": int, "total": int, "aav": int},
       "proposed_contract": {"years": int, "total": int, "guaranteed": int, "aav": int},
       "market_comparison": str
   }

   # SIGNING details
   {
       "player_name": str,
       "position": str,
       "age": int,
       "overall_rating": int,
       "contract": {"years": int, "total": int, "guaranteed": int, "aav": int},
       "cap_space_before": int,
       "cap_space_after": int,
       "competing_offers": int
   }

   # TRADE details
   {
       "trade_partner": str,
       "sending": [{"type": "player" | "pick", "name": str, "value": int}],
       "receiving": [{"type": "player" | "pick", "name": str, "value": int}],
       "value_differential": int,
       "cap_impact": int
   }

   # DRAFT_PICK details
   {
       "round": int,
       "pick": int,
       "overall": int,
       "player_name": str,
       "position": str,
       "college": str,
       "projected_rating": int,
       "draft_grade": str,  # "A+", "A", "B+", etc.
       "alternatives": [{"name": str, "position": str, "rating": int}]
   }

   # CUT details
   {
       "player_name": str,
       "position": str,
       "age": int,
       "overall_rating": int,
       "cap_savings": int,
       "dead_money": int,
       "replacement_options": str
   }

   # WAIVER_CLAIM details
   {
       "player_name": str,
       "position": str,
       "age": int,
       "overall_rating": int,
       "waiver_priority": int,
       "contract_remaining": {"years": int, "total": int}
   }
   ```

5. **API Class** (`src/game_cycle/database/proposal_api.py`)
   ```python
   class ProposalAPI:
       def __init__(self, conn: sqlite3.Connection, dynasty_id: str):
           self.conn = conn
           self.dynasty_id = dynasty_id

       def create_proposal(self, proposal: GMProposal) -> str: ...
       def get_proposal(self, proposal_id: str) -> Optional[GMProposal]: ...
       def get_pending_proposals(self, stage: StageType = None) -> List[GMProposal]: ...
       def get_proposals_by_status(self, status: ProposalStatus) -> List[GMProposal]: ...
       def update_status(self, proposal_id: str, status: ProposalStatus,
                        owner_notes: str = None) -> bool: ...
       def approve_proposal(self, proposal_id: str) -> bool: ...
       def reject_proposal(self, proposal_id: str, notes: str = None) -> bool: ...
       def expire_pending_proposals(self, stage: StageType) -> int: ...
       def get_proposal_history(self, season: int) -> List[GMProposal]: ...
   ```

### Implementation Steps

1. Create enum file with ProposalType and ProposalStatus
2. Create GMProposal dataclass
3. Add SQL schema to game_cycle database initialization
4. Create ProposalAPI with CRUD operations
5. Add JSON serialization for details field
6. Implement status transition logic
7. Write unit tests for API

### Acceptance Criteria

- [ ] Schema creates table with all constraints
- [ ] GMProposal dataclass handles all proposal types
- [ ] Details schema validates per proposal type
- [ ] ProposalAPI.create_proposal() generates unique ID
- [ ] ProposalAPI.get_pending_proposals() filters correctly
- [ ] ProposalAPI.approve_proposal() updates status and timestamp
- [ ] ProposalAPI.reject_proposal() captures owner notes
- [ ] ProposalAPI.expire_pending_proposals() handles stage transitions
- [ ] Unit tests pass (target: 15+ tests)

---

## Tollgate 4: Approval UI ✅ COMPLETE

**Goal:** Create the dialog for reviewing and acting on GM proposals.

**Implementation:**
- `game_cycle_ui/dialogs/gm_proposal_notification.py` - ProposalReviewDialog
- `game_cycle_ui/widgets/gm_proposal_widget.py` - Proposal display widgets
- Integration in `game_cycle_ui/views/franchise_tag_view.py` and `resigning_view.py`

### Deliverables

1. **ProposalReviewDialog** (`game_cycle_ui/dialogs/proposal_review_dialog.py`)
   ```
   ┌─────────────────────────────────────────────────────────────────┐
   │  GM PROPOSAL - {STAGE_NAME}                          [1 of 5]   │
   ├─────────────────────────────────────────────────────────────────┤
   │                                                                 │
   │  {PROPOSAL_TYPE_HEADER}                                         │
   │  ┌─────────────────────────────────────────────────────────┐   │
   │  │  {Proposal-specific content rendered here}               │   │
   │  │  - Player info, contract details, trade package, etc.    │   │
   │  └─────────────────────────────────────────────────────────┘   │
   │                                                                 │
   │  GM REASONING                                                   │
   │  ┌─────────────────────────────────────────────────────────┐   │
   │  │  "{gm_reasoning text}"                                   │   │
   │  └─────────────────────────────────────────────────────────┘   │
   │                                                                 │
   │  GM CONFIDENCE: ████████░░ {confidence}%                        │
   │                                                                 │
   │  {Context panel: cap space, roster needs, etc.}                 │
   │                                                                 │
   │  ┌─────────────────────────────────────────────────────────┐   │
   │  │ [Approve] [Reject] [Modify] [Alternatives] [Skip]        │   │
   │  └─────────────────────────────────────────────────────────┘   │
   │                                                                 │
   │  [ ] Apply to all similar proposals                             │
   │                                                                 │
   │  [← Previous]                              [Next →] [Done]      │
   │                                                                 │
   └─────────────────────────────────────────────────────────────────┘
   ```

2. **Proposal Content Renderers** (one per proposal type)
   - `FranchiseTagProposalWidget`
   - `ExtensionProposalWidget`
   - `SigningProposalWidget`
   - `TradeProposalWidget`
   - `DraftPickProposalWidget`
   - `CutProposalWidget`
   - `WaiverClaimProposalWidget`

3. **Batch Approval Dialog** (`game_cycle_ui/dialogs/batch_approval_dialog.py`)
   ```
   ┌─────────────────────────────────────────────────────────────────┐
   │  BATCH APPROVAL - ROSTER CUTS                                   │
   ├─────────────────────────────────────────────────────────────────┤
   │                                                                 │
   │  GM proposes cutting 7 players to reach 53-man roster:          │
   │                                                                 │
   │  ┌─────────────────────────────────────────────────────────┐   │
   │  │ [x] WR James Wilson (68 OVR) - Save $1.2M               │   │
   │  │ [x] CB Marcus Brown (65 OVR) - Save $900K               │   │
   │  │ [x] LB Derek Johnson (63 OVR) - Save $850K              │   │
   │  │ [x] RB Tyler Adams (61 OVR) - Save $780K                │   │
   │  │ [x] OL Chris Martinez (60 OVR) - Save $750K             │   │
   │  │ [x] DT Kevin Lee (59 OVR) - Save $720K                  │   │
   │  │ [x] S Andre Thomas (58 OVR) - Save $700K                │   │
   │  └─────────────────────────────────────────────────────────┘   │
   │                                                                 │
   │  Total Cap Savings: $5.9M                                       │
   │                                                                 │
   │  [Select All] [Deselect All]                                    │
   │                                                                 │
   │         [Cancel]           [Approve Selected ({n})]             │
   │                                                                 │
   └─────────────────────────────────────────────────────────────────┘
   ```

4. **Rejection Notes Dialog**
   - Simple text input when owner rejects a proposal
   - Optional but helps GM generate better alternatives

### Implementation Steps

1. Create base `ProposalReviewDialog` with navigation
2. Implement proposal-specific content widgets
3. Add confidence meter widget (progress bar style)
4. Implement context panel showing cap/roster info
5. Wire up action buttons to ProposalAPI
6. Create `BatchApprovalDialog` for multi-proposal stages
7. Add rejection notes popup
8. Implement "Apply to all similar" checkbox logic

### Acceptance Criteria

- [ ] Dialog displays proposal details correctly for all types
- [ ] Navigation (Previous/Next) works for multiple proposals
- [ ] Approve updates proposal status to APPROVED
- [ ] Reject prompts for notes and updates to REJECTED
- [ ] Modify opens type-specific edit dialog
- [ ] Alternatives requests GM generate new options
- [ ] Skip leaves proposal PENDING
- [ ] Batch dialog shows checkbox list
- [ ] "Apply to all similar" bulk-approves/rejects

---

## Tollgate 5: Franchise Tag Integration ✅ COMPLETE

**Goal:** GM analyzes roster and proposes franchise tag candidate with reasoning.

**Implementation:**
- `src/game_cycle/services/proposal_generators/franchise_tag_generator.py` - FranchiseTagProposalGenerator
- Integration in `src/game_cycle/handlers/offseason.py` (_get_franchise_tag_preview)
- Tests at `tests/game_cycle/services/test_franchise_tag_generator.py`

### Deliverables

1. **FranchiseTagProposalGenerator** (`src/game_cycle/services/proposal_generators/franchise_tag_generator.py`)
   ```python
   class FranchiseTagProposalGenerator:
       def __init__(self, conn, dynasty_id, directive: OffseasonDirective):
           ...

       def generate_proposal(self) -> Optional[GMProposal]:
           """
           Analyze expiring contracts and generate tag proposal if warranted.

           Returns None if:
           - No valuable expiring contracts
           - Team already used tag
           - Cap situation prohibits tag
           """
           ...

       def _get_tag_candidates(self) -> List[TagCandidate]: ...
       def _score_candidate(self, player, directive) -> float: ...
       def _generate_reasoning(self, player, directive) -> str: ...
   ```

2. **Tag Candidate Scoring**
   - Base score from player overall rating
   - Bonus for matching position priorities
   - Penalty if player is expendable
   - Bonus if philosophy is WIN_NOW
   - Penalty if budget stance is CONSERVATIVE
   - Consider age and position value

3. **Reasoning Templates**
   ```
   WIN_NOW + High Value:
   "{player} is a {position} entering free agency at age {age}.
   At {overall} OVR, he's one of our best players. The {tag_type} tag
   costs ${amount}M but preserves our ability to negotiate long-term
   or trade him. Given your Win-Now directive, keeping our core together
   is essential."

   REBUILD + Trade Asset:
   "{player} has trade value as a {position}. Tagging him at ${amount}M
   lets us shop him before the deadline. If we can't find a deal, we can
   negotiate an extension or let him walk next year."

   No Tag Recommended:
   "After reviewing our expiring contracts, I don't recommend using the
   franchise tag this year. Our best candidates ({names}) either have
   prohibitive cap costs or don't fit our {philosophy} approach."
   ```

4. **Integration with Offseason Handler**
   - `offseason.py` calls generator when entering FRANCHISE_TAG stage
   - If proposal generated and not Trust GM, show approval dialog
   - If Trust GM, auto-approve
   - Execute tag via existing contract service

### Implementation Steps

1. Create FranchiseTagProposalGenerator class
2. Implement candidate identification from expiring contracts
3. Implement scoring algorithm using directive
4. Generate human-readable reasoning
5. Create GMProposal with FRANCHISE_TAG type
6. Integrate with offseason handler
7. Execute approved tag via ContractService

### Acceptance Criteria

- [ ] Generator identifies expiring contract players
- [ ] Scoring considers directive philosophy and priorities
- [ ] Protected players get higher scores
- [ ] Expendable players get lower scores
- [ ] Reasoning explains decision in context of directive
- [ ] Proposal creates valid GMProposal object
- [ ] Trust GM mode auto-approves
- [ ] Approval executes tag transaction
- [ ] Rejection skips tag for season

---

## Tollgate 6: Re-signing Integration ✅ COMPLETE

**Goal:** GM prioritizes contract extensions based on directive and presents batched proposals.

**Implementation:**
- `src/game_cycle/services/proposal_generators/resigning_generator.py` - ResigningProposalGenerator
- Integration in `src/game_cycle/handlers/offseason.py` (_get_resigning_preview)
- UI in `game_cycle_ui/views/resigning_view.py` (GM proposal section)

### Deliverables

1. **ResigningProposalGenerator** (`src/game_cycle/services/proposal_generators/resigning_generator.py`)
   ```python
   class ResigningProposalGenerator:
       def __init__(self, conn, dynasty_id, directive: OffseasonDirective):
           ...

       def generate_proposals(self) -> List[GMProposal]:
           """
           Generate extension proposals for expiring contracts.
           Prioritizes based on directive and player value.
           """
           ...

       def _get_extension_candidates(self) -> List[Player]: ...
       def _calculate_offer(self, player, directive) -> ContractTerms: ...
       def _generate_reasoning(self, player, offer, directive) -> str: ...
   ```

2. **Extension Prioritization**
   - Priority 1: Protected players with expiring deals
   - Priority 2: Position priorities with expiring deals
   - Priority 3: High-value players (80+ OVR)
   - Priority 4: Solid starters (70-79 OVR)
   - Exclude: Expendable players (unless WIN_NOW critical)

3. **Offer Calculation**
   - Base on market value from existing contract calculator
   - Adjust for directive:
     - AGGRESSIVE: +5-10% above market
     - MODERATE: market value
     - CONSERVATIVE: -5-10% below market
   - Consider player persona (Money First vs Legacy Builder)

4. **Batch Presentation**
   - Group proposals by priority tier
   - Show total cap commitment
   - Allow approve/reject per proposal
   - "Approve All" for tier

### Implementation Steps

1. Create ResigningProposalGenerator class
2. Implement candidate prioritization
3. Integrate with existing contract value calculator
4. Adjust offers based on directive
5. Generate reasoning for each proposal
6. Create batch of GMProposal objects
7. Integrate with offseason handler
8. Execute approved extensions via ResigningService

### Acceptance Criteria

- [ ] Generator identifies players in final contract year
- [ ] Protected players appear first
- [ ] Position priorities influence ordering
- [ ] Contract offers scale with budget stance
- [ ] Reasoning references directive context
- [ ] Multiple proposals created and navigable
- [ ] Batch approval works correctly
- [ ] Trust GM auto-approves all
- [ ] Approved extensions execute correctly

---

## Tollgate 7: Free Agency Integration ✅ COMPLETE

**Goal:** GM targets free agents matching needs and presents signing proposals by wave.

**Implementation:**
- `src/game_cycle/services/proposal_generators/fa_signing_generator.py` - FASigningProposalGenerator
- Integration in `src/game_cycle/handlers/offseason.py` (_execute_free_agency)
- UI in `game_cycle_ui/views/free_agency_view.py` (GM proposals section with approve/reject)
- Converts ephemeral GMProposal → PersistentGMProposal, persists to database
- Trust GM mode auto-approves proposals
- Approved proposals converted to FA offers and submitted

### Deliverables

1. **FASigningProposalGenerator** (`src/game_cycle/services/proposal_generators/fa_signing_generator.py`)
   ```python
   class FASigningProposalGenerator:
       def __init__(self, conn, dynasty_id, directive: OffseasonDirective, wave: FAWave):
           ...

       def generate_proposals(self, available_fas: List[Player]) -> List[GMProposal]:
           """
           Generate signing proposals for current FA wave.
           Targets players matching position priorities and budget.
           """
           ...

       def _filter_targets(self, players, directive) -> List[Player]: ...
       def _calculate_offer(self, player, directive) -> ContractTerms: ...
       def _estimate_signing_probability(self, player, offer) -> float: ...
   ```

2. **Target Filtering**
   - Position priority match
   - Budget stance determines quality tier:
     - AGGRESSIVE: Elite + Quality tiers
     - MODERATE: Quality + Depth tiers
     - CONSERVATIVE: Depth tier only
   - Philosophy affects contract length:
     - WIN_NOW: Longer deals for prime players
     - REBUILD: Short deals for veterans, long for young
     - MAINTAIN: Market-standard lengths

3. **Wave-Based Batching**
   - Wave 1 (Elite): 1-3 proposals max
   - Wave 2 (Quality): 2-5 proposals
   - Wave 3 (Depth): 3-7 proposals
   - Post-Draft: 1-3 proposals

4. **Competition Awareness**
   - Track competing offers from FAWaveService
   - Reasoning includes "3 other teams interested"
   - Confidence reflects signing probability

### Implementation Steps

1. Create FASigningProposalGenerator class
2. Integrate with existing FAWaveService
3. Implement target filtering by directive
4. Calculate offers using existing contract logic
5. Estimate signing probability
6. Generate reasoning with market context
7. Create proposals per wave
8. Integrate with offseason handler
9. Execute via existing FA signing flow

### Acceptance Criteria

- [ ] Generator targets position priorities
- [ ] Budget stance filters player tiers
- [ ] Philosophy affects contract lengths
- [ ] Proposals include competing offer count
- [ ] Confidence reflects signing probability
- [ ] Wave batching limits proposal count
- [ ] Trust GM auto-approves all waves
- [ ] Approved signings execute correctly
- [ ] Rejected players remain available

---

## Tollgate 8: Trade Integration ✅ COMPLETE

**Goal:** GM seeks trade partners and presents trade proposals with detailed analysis.

**Implementation:**
- `src/game_cycle/services/proposal_generators/trade_generator.py` - TradeProposalGenerator
- Integration in `src/game_cycle/handlers/offseason.py` (_get_trading_preview, _execute_trading)
- UI in `game_cycle_ui/views/trading_view.py` (GM proposals section with approve/reject)
- Signals in `game_cycle_ui/controllers/stage_controller.py` (trade_proposal_approved/rejected)

### Deliverables

1. **TradeProposalGenerator** (`src/game_cycle/services/proposal_generators/trade_generator.py`)
   ```python
   class TradeProposalGenerator:
       def __init__(self, conn, dynasty_id, directive: OffseasonDirective):
           ...

       def generate_proposals(self) -> List[GMProposal]:
           """
           Generate trade proposals based on directive.
           - WIN_NOW: Acquire talent, trade picks
           - REBUILD: Trade veterans for picks
           - MAINTAIN: Balanced value trades
           """
           ...

       def _identify_trade_targets(self, directive) -> List[TradeTarget]: ...
       def _identify_trade_chips(self, directive) -> List[TradeChip]: ...
       def _find_trade_partners(self, target_or_chip) -> List[Team]: ...
       def _construct_package(self, target, partner, directive) -> TradePackage: ...
   ```

2. **Trade Strategy by Philosophy**

   | Philosophy | Acquire | Trade Away |
   |------------|---------|------------|
   | WIN_NOW | Position needs, proven vets | Draft picks, young depth |
   | REBUILD | Draft picks, young players | Expensive veterans |
   | MAINTAIN | Value upgrades | Declining assets |

3. **Expendable Player Focus**
   - Expendable players actively shopped
   - Generate "best offer received" proposals
   - Include value analysis

4. **Trade Package Reasoning**
   ```
   "The {team} are willing to send {player} ({position}, {overall} OVR)
   for {our_package}. This addresses your #{priority_rank} need at {position}.
   Value analysis: We're giving up {our_value} value for {their_value}.
   {assessment}."
   ```

### Implementation Steps

1. Create TradeProposalGenerator class
2. Implement philosophy-based strategy
3. Integrate with existing TradeService for evaluation
4. Generate proposals for expendable players
5. Generate proposals for position needs
6. Include value analysis in reasoning
7. Integrate with offseason handler
8. Execute approved trades via TradeService

### Acceptance Criteria

- [ ] Philosophy drives trade strategy
- [ ] Expendable players are shopped
- [ ] Position needs targeted for acquisition
- [ ] Trade value analysis included
- [ ] Protected players never traded
- [ ] Reasoning explains trade rationale
- [ ] Trust GM auto-approves
- [ ] Approved trades execute correctly

---

## Tollgate 9: Draft Integration ✅ COMPLETE

**Goal:** GM builds draft board influenced by directive and proposes picks.

**Implementation:**
- `src/game_cycle/services/proposal_generators/draft_generator.py` - DraftProposalGenerator (508 lines)
- Integration in `src/game_cycle/handlers/offseason.py` (_get_draft_preview, _execute_draft, _get_approved_draft_pick)
- UI in `game_cycle_ui/views/draft_view.py` (GM recommendation panel with approve/reject/alternatives)
- Signals in `game_cycle_ui/views/offseason_view.py` and `game_cycle_ui/controllers/stage_controller.py`
- Uses existing DraftService._evaluate_prospect_with_direction() for evaluation

### Deliverables

1. **DraftProposalGenerator** (`src/game_cycle/services/proposal_generators/draft_generator.py`)
   ```python
   class DraftProposalGenerator:
       def __init__(self, conn, dynasty_id, directive: OffseasonDirective):
           ...

       def generate_proposal(self, pick_number: int, available_prospects: List[Prospect]) -> GMProposal:
           """
           Generate draft pick proposal for current selection.
           Considers BPA vs. need based on directive.
           """
           ...

       def _build_draft_board(self, directive) -> List[RankedProspect]: ...
       def _score_prospect(self, prospect, directive) -> float: ...
       def _get_alternatives(self, top_pick, available) -> List[Prospect]: ...
   ```

2. **Draft Board Weighting**
   - Base: Prospect overall rating
   - Need bonus: +10-20 for position priorities
   - BPA vs Need by philosophy:
     - WIN_NOW: 60% need, 40% BPA
     - MAINTAIN: 50% need, 50% BPA
     - REBUILD: 40% need, 60% BPA (talent over fit)

3. **Pick-by-Pick vs Round Mode**
   - Setting in directive: "Approve each pick" vs "Approve by round"
   - Round mode batches all picks in round

4. **Alternatives Display**
   - Show top 2-3 alternatives at each pick
   - Allow owner to request different player

### Implementation Steps

1. Create DraftProposalGenerator class
2. Implement draft board with directive weighting
3. Generate proposal per pick
4. Include alternatives in proposal
5. Support round-batch mode
6. Integrate with offseason handler
7. Execute picks via existing DraftService

### Acceptance Criteria

- [ ] Draft board weights by position priority
- [ ] Philosophy affects BPA vs need balance
- [ ] Proposal includes alternatives
- [ ] Pick-by-pick mode works
- [ ] Round-batch mode works
- [ ] Trust GM auto-drafts entire class
- [ ] Owner can request alternative player
- [ ] Approved picks execute correctly

---

## Tollgate 10: Roster Cuts Integration ✅ COMPLETE

**Goal:** GM proposes cuts to reach 53-man roster with cap analysis.

### Implementation Summary

**Status:** Complete
**File:** `src/game_cycle/services/proposal_generators/cuts_generator.py` (556 lines)

**Key Features:**
- **Priority Tiers:** TIER_MUST_CUT (1), TIER_PHILOSOPHY (2), TIER_DEPTH (3), TIER_CAP_RELIEF (4)
- **Cut Scoring:** Combines cap hit, overall rating, age, dead money ratio, and directive adjustments
- **Philosophy-Based Cuts:**
  - WIN_NOW: Preserves young talent (age < 27), cuts expensive depth
  - REBUILD: Cuts expensive veterans (age 30+), preserves young players
  - MAINTAIN: Balances dead money vs cap savings
- **Directive Integration:** Protected players never cut, expendable players prioritized
- **Trust GM:** Auto-approves all proposals when `trust_gm = True`
- **Cap Analysis:** Shows cap savings and dead money for each cut

**Integration Points:**
- `offseason.py::_get_roster_cuts_preview()` - Generates GM proposals during preview
- `offseason.py::_execute_roster_cuts()` - Executes approved proposals before manual cuts
- Uses existing `RosterCutsService` for actual cut execution with dead money calculation

### Deliverables

1. **RosterCutsProposalGenerator** (`src/game_cycle/services/proposal_generators/cuts_generator.py`)
   ```python
   class RosterCutsProposalGenerator:
       def __init__(self, conn, dynasty_id, directive: OffseasonDirective):
           ...

       def generate_proposals(self, current_roster_size: int) -> List[GMProposal]:
           """
           Generate cut proposals to reach 53-man roster.
           Prioritizes cuts by value, cap savings, and directive.
           """
           ...

       def _identify_cut_candidates(self) -> List[CutCandidate]: ...
       def _score_cut_priority(self, player, directive) -> float: ...
   ```

2. **Cut Prioritization**
   - Lowest OVR at position group
   - Highest cap savings with lowest dead money
   - Expendable players (if over-rostered)
   - Never cut protected players
   - Consider position depth

3. **Batch Presentation**
   - All cuts shown in single dialog
   - Checkbox selection (pre-checked recommended)
   - Total cap savings displayed
   - Dead money warnings

### Implementation Steps

1. Create RosterCutsProposalGenerator class
2. Implement cut candidate scoring
3. Generate batch proposals
4. Integrate with batch approval dialog
5. Execute cuts via existing RosterCutsService

### Acceptance Criteria

- [ ] Correct number of cuts proposed (roster - 53)
- [ ] Protected players never proposed
- [ ] Cap savings calculated correctly
- [ ] Dead money shown for each
- [ ] Batch approval works
- [ ] Trust GM auto-cuts all
- [ ] Owner can uncheck specific players
- [ ] Approved cuts execute correctly

---

## Tollgate 11: Waiver Wire Integration ✅ COMPLETE

**Goal:** GM identifies valuable waiver claims matching team needs.

### Implementation Summary

**Status:** Complete
**File:** `src/game_cycle/services/proposal_generators/waiver_generator.py` (574 lines)

**Key Features:**
- **Priority Tiers:** TIER_HIGH_PRIORITY (1), TIER_MEDIUM_PRIORITY (2), TIER_LOW_PRIORITY (3)
- **Quality Thresholds:** AGGRESSIVE (75+), MODERATE (70+), CONSERVATIVE (65+) based on budget_stance
- **Claim Success Probability:** Calculated from team's waiver priority (1=95%, 32=10%) and player competition
- **Philosophy-Based Claims:**
  - WIN_NOW: Proven veterans (age 26-30) who can contribute immediately
  - REBUILD: Young players with upside (age <27) for future development
  - MAINTAIN: Balanced approach (25-29), value claims maintaining competitiveness
- **Directive Integration:** Position priorities (+20 to 0 bonus), quality thresholds, age preferences
- **Trust GM:** Auto-approves all proposals when `trust_gm = True`
- **MAX_PROPOSALS:** Generates 0-5 waiver claims (filters by MIN_CLAIM_PROBABILITY 20%)

**Integration Points:**
- `offseason.py::_get_waiver_wire_preview()` - Generates GM proposals during preview (after line 1686)
- `offseason.py::_execute_waiver_wire()` - Executes approved proposals before manual claims (line 2041)
- Uses existing `WaiverService` for claim submission and priority-based awarding
- Uses existing `create_waiver_claim_details()` helper and `WaiverClaimProposalWidget` UI widget

### Deliverables

1. **WaiverProposalGenerator** (`src/game_cycle/services/proposal_generators/waiver_generator.py`)
   ```python
   class WaiverProposalGenerator:
       def __init__(self, conn, dynasty_id, directive: OffseasonDirective):
           ...

       def generate_proposals(self, available_players: List[Player]) -> List[GMProposal]:
           """
           Generate waiver claim proposals for newly available players.
           """
           ...

       def _filter_claim_candidates(self, players, directive) -> List[Player]: ...
       def _estimate_claim_success(self, player) -> float: ...
   ```

2. **Claim Filtering**
   - Position priorities get preference
   - Quality threshold by budget stance
   - Consider roster spots available
   - Factor in waiver priority

3. **Claim Success Probability**
   - Based on waiver order
   - Higher value = more competition

### Implementation Steps

1. Create WaiverProposalGenerator class
2. Implement candidate filtering
3. Calculate claim success probability
4. Generate proposals
5. Execute claims via WaiverService

### Acceptance Criteria

- [ ] Position priorities influence claims
- [ ] Claim probability estimated
- [ ] Reasoning explains fit
- [ ] Trust GM auto-claims
- [ ] Approved claims execute

---

## Tollgate 12: End-to-End Testing ✅ COMPLETE

**Status:** Complete
**File:** `tests/test_game_cycle/integration/test_owner_gm_offseason_flow.py` (682 lines)

**Goal:** Full offseason simulation with approval flow working correctly.

### Deliverables

1. **Integration Test Suite** (`tests/game_cycle/test_owner_gm_flow.py`)
   - Test complete offseason with owner approvals
   - Test complete offseason with Trust GM
   - Test mixed approval/rejection scenarios
   - Test directive changes mid-offseason

2. **Regression Tests**
   - Existing offseason services still work
   - Database integrity maintained
   - No orphaned proposals

3. **UI Automation Tests** (optional)
   - Dialog flow testing
   - Batch approval testing

4. **Performance Testing**
   - Proposal generation time
   - Database query efficiency

### Test Scenarios

1. **Happy Path - Full Control**
   - Set directive (WIN_NOW, AGGRESSIVE, [EDGE, CB])
   - Review and approve tag proposal
   - Review and approve 3 extensions
   - Review and approve 5 FA signings
   - Review and approve 1 trade
   - Review and approve 7 draft picks
   - Review and approve 7 cuts
   - Review and skip waiver claims
   - Verify all transactions executed

2. **Happy Path - Trust GM**
   - Set directive with Trust GM = true
   - Verify all stages auto-process
   - Verify no dialogs shown
   - Verify transactions match directive

3. **Rejection Handling**
   - Reject tag proposal
   - Verify no tag applied
   - Reject 2 of 5 extensions
   - Verify correct contracts created
   - Reject FA signing
   - Verify player goes elsewhere

4. **Directive Adherence**
   - Set REBUILD philosophy
   - Verify GM trades veterans
   - Verify GM drafts for ceiling
   - Verify conservative spending

### Implementation Summary

**Created 4 comprehensive integration test classes:**

1. **`TestOwnerGMFlowHappyPathFullControl`** - Manual approval workflow
   - Tests complete offseason with owner reviewing and approving all GM proposals
   - Validates proposal lifecycle: generated → approved → executed
   - Covers all 7 stages: Franchise Tag, Re-signing, FA, Trading, Draft, Cuts, Waiver Wire

2. **`TestOwnerGMFlowTrustGM`** - Auto-approval when Trust GM enabled
   - Sets `trust_gm = True` in owner directives
   - Verifies all proposals auto-approved without manual intervention
   - Confirms transactions execute correctly in Trust GM mode

3. **`TestOwnerGMFlowMixedApproval`** - Selective approval/rejection
   - Approves some proposals, rejects others
   - Verifies only approved proposals execute
   - Confirms rejected proposals remain in REJECTED status

4. **`TestOwnerGMFlowDirectiveChanges`** - Mid-offseason directive changes
   - Sets WIN_NOW directives for early stages
   - Switches to REBUILD directives mid-offseason
   - Validates later proposals reflect updated directives

**Test Infrastructure:**
- `game_cycle_db` fixture: Creates database with full schema and test season data
- `offseason_handler` fixture: Provides OffseasonHandler for testing
- `owner_directives` fixture: Creates sample directives for testing
- Helper functions for data setup and verification

**Key Features:**
- All tests handle missing data gracefully (appropriate for integration tests)
- Tests validate proposal status transitions (PENDING → APPROVED → EXECUTED)
- Tests confirm Trust GM mode auto-approval behavior
- Tests verify directive influence on GM proposal generation

**Test Results:** All 4 tests pass successfully

### Acceptance Criteria

- [✅] All integration tests pass (4/4 tests passing)
- [✅] Tests cover complete offseason workflow (7 stages tested)
- [✅] Trust GM mode tested (auto-approval validated)
- [✅] Manual approval tested (selective approval/rejection validated)
- [✅] Directive influence tested (WIN_NOW vs REBUILD strategies)
- [✅] Test infrastructure resilient (handles missing data gracefully)
- [✅] Proposal lifecycle validated (generation, approval, execution)

---

## File Structure

```
src/
├── game_cycle/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── directive_enums.py          # T2
│   │   ├── offseason_directive.py      # T2
│   │   ├── proposal_enums.py           # T3
│   │   └── gm_proposal.py              # T3
│   ├── database/
│   │   ├── schema/
│   │   │   ├── offseason_directives.sql # T2
│   │   │   └── gm_proposals.sql         # T3
│   │   ├── directive_api.py            # T2
│   │   └── proposal_api.py             # T3
│   └── services/
│       └── proposal_generators/
│           ├── __init__.py
│           ├── base_generator.py       # T5
│           ├── franchise_tag_generator.py  # T5
│           ├── resigning_generator.py      # T6
│           ├── fa_signing_generator.py     # T7
│           ├── trade_generator.py          # T8
│           ├── draft_generator.py          # T9
│           ├── cuts_generator.py           # T10
│           └── waiver_generator.py         # T11
├── game_cycle_ui/
│   └── dialogs/
│       ├── offseason_directive_dialog.py   # T1
│       ├── proposal_review_dialog.py       # T4
│       ├── batch_approval_dialog.py        # T4
│       └── proposal_widgets/               # T4
│           ├── __init__.py
│           ├── franchise_tag_widget.py
│           ├── extension_widget.py
│           ├── signing_widget.py
│           ├── trade_widget.py
│           ├── draft_pick_widget.py
│           ├── cut_widget.py
│           └── waiver_claim_widget.py
└── tests/
    └── game_cycle/
        ├── test_directive_api.py           # T2
        ├── test_proposal_api.py            # T3
        ├── test_franchise_tag_generator.py # T5
        ├── test_resigning_generator.py     # T6
        ├── test_fa_signing_generator.py    # T7
        ├── test_trade_generator.py         # T8
        ├── test_draft_generator.py         # T9
        ├── test_cuts_generator.py          # T10
        ├── test_waiver_generator.py        # T11
        └── test_owner_gm_flow.py           # T12
```

---

## Dependencies

### External (Already Complete)
- Salary Cap & Contracts (Milestone 2)
- Trade System (Milestone 6)
- Player Personas (Milestone 7)
- Free Agency Depth (Milestone 7, in progress)

### Internal (Build Order)
```
T1 (UI) ←── T2 (Data Model) ←── T3 (Proposal System) ←── T4 (Approval UI)
                                        │
    ┌───────────────────────────────────┼───────────────────────────────────┐
    ▼                   ▼               ▼               ▼                   ▼
   T5                  T6              T7              T8                  T9
(Franchise Tag)   (Re-signing)   (Free Agency)    (Trading)           (Draft)
                                        │
                        ┌───────────────┴───────────────┐
                        ▼                               ▼
                       T10                            T11
                  (Roster Cuts)                  (Waiver Wire)
                                        │
                                        ▼
                                       T12
                                  (Integration)
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Test Coverage | 80%+ for new code |
| Proposal Generation Time | <500ms per stage |
| User Testing Feedback | Positive on "feels like owning" |
| Bug Reports | <5 blocking issues at launch |
| Trust GM Accuracy | 90%+ matches directive intent |